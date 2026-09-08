import copy
import importlib.util
import json
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("qualify-codex-integration.py")
SPEC = importlib.util.spec_from_file_location("codex_integration_probe", SCRIPT)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class CodexIntegrationProbeTest(unittest.TestCase):
    def setUp(self):
        self.result = {
            "calculation": 42,
            "patchResult": "Success. Updated the following files:\nA proof.txt\n",
            "command": {"output": probe.PROOF, "exit_code": 0,
                        "wall_time_seconds": 0.01, "chunk_id": "fixture-chunk"},
        }

    def request(self, result=None):
        return {"input": [{
            "type": "custom_tool_call_output", "call_id": probe.CALL_ID,
            # This is the content-item encoding used by the pinned upstream
            # code_mode_can_return_exec_command_output integration test.
            "output": [
                {"type": "input_text", "text": "Script completed\nWall time 0.1 seconds\nOutput:\n"},
                {"type": "input_text", "text": json.dumps(self.result if result is None else result)},
            ],
        }]}

    def test_completed_structured_result_is_accepted(self):
        probe.tool_output(self.request())

    def test_nonzero_command_status_cannot_pass_with_correct_stdout(self):
        result = copy.deepcopy(self.result)
        result["command"]["exit_code"] = 1
        with self.assertRaises(ValueError):
            probe.tool_output(self.request(result))

    def test_arithmetic_prefix_is_not_the_expected_value(self):
        result = copy.deepcopy(self.result)
        result["calculation"] = 420
        with self.assertRaises(ValueError):
            probe.tool_output(self.request(result))

    def test_echoed_marker_does_not_replace_command_readback(self):
        result = copy.deepcopy(self.result)
        result["patchResult"] = probe.PROOF
        result["command"]["output"] = "cat: proof.txt: read error\n"
        with self.assertRaises(ValueError):
            probe.tool_output(self.request(result))

    def test_running_session_is_not_a_completed_command(self):
        result = copy.deepcopy(self.result)
        result["command"]["session_id"] = 17
        with self.assertRaises(ValueError):
            probe.tool_output(self.request(result))

    def test_diagnostic_text_is_not_a_structured_result(self):
        request = self.request()
        request["input"][0]["output"] = 'error while evaluating "calculation":42 ' + probe.PROOF
        with self.assertRaises(ValueError):
            probe.tool_output(request)

    def test_duplicate_call_results_are_rejected(self):
        request = self.request()
        request["input"].append(copy.deepcopy(request["input"][0]))
        with self.assertRaises(ValueError):
            probe.tool_output(request)

    def test_multiple_result_objects_are_rejected(self):
        request = self.request()
        other = copy.deepcopy(self.result)
        other["command"]["exit_code"] = 1
        request["input"][0]["output"].append({"type": "input_text", "text": json.dumps(other)})
        with self.assertRaises(ValueError):
            probe.tool_output(request)

    def test_unrelated_call_result_is_rejected(self):
        request = self.request()
        request["input"][0]["call_id"] = "another-call"
        with self.assertRaises(ValueError):
            probe.tool_output(request)

    def test_boolean_command_status_is_not_an_exit_code(self):
        result = copy.deepcopy(self.result)
        result["command"]["exit_code"] = False
        with self.assertRaises(ValueError):
            probe.tool_output(self.request(result))

    def test_classic_responses_exec_has_no_namespace(self):
        self.assertIsNone(probe.advertised_exec({"tools": [
            {"type": "custom", "name": "exec"},
            {"type": "function", "name": "apply_patch"},
        ]}))

    def test_responses_lite_exec_preserves_functions_namespace(self):
        self.assertEqual(probe.advertised_exec({"tools": [{
            "type": "namespace", "name": "functions", "tools": [
                {"type": "function", "name": "apply_patch"},
                {"type": "custom", "name": "exec"},
            ],
        }]}), "functions")

    def test_similarly_named_or_typed_tools_do_not_advertise_code_mode(self):
        for tool in (
            {"type": "function", "name": "exec"},
            {"type": "custom", "name": "exec_command"},
            {"type": "namespace", "name": "other", "tools": [
                {"type": "custom", "name": "exec"}]},
        ):
            with self.subTest(tool=tool), self.assertRaises(ValueError):
                probe.advertised_exec({"tools": [tool]})

    def test_missing_exec_is_rejected(self):
        with self.assertRaises(ValueError):
            probe.advertised_exec({"tools": []})

    def test_ambiguous_exec_advertisements_are_rejected(self):
        direct = {"type": "custom", "name": "exec"}
        nested = {"type": "namespace", "name": "functions", "tools": [direct]}
        for tools in ([direct, direct], [direct, nested], [nested, nested]):
            with self.subTest(tools=tools), self.assertRaises(ValueError):
                probe.advertised_exec({"tools": tools})


if __name__ == "__main__":
    unittest.main()
