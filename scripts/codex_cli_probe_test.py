import errno
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


PROBE = Path(__file__).resolve().parents[1] / "language-ports/codex-cli/probe.c"
FIXTURE = r'''
#define _GNU_SOURCE
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    const char *home = getenv("HOME");
    if (!home || strncmp(home, "/tmp/codex-cli-qualify-", 23) ||
        strcmp(home, getenv("CODEX_HOME")) || getenv("CODEX_API_KEY") || getenv("OPENAI_API_KEY"))
        return 92;
    if (strstr(argv[0], "hang")) for (;;) pause();
    if (strstr(argv[0], "signal")) raise(SIGTERM);
    int bad = strstr(argv[0], "bad") != NULL;
    if (argc > 1) {
        if (strstr(argv[0], "wrong")) {
            puts("unrelated output");
            return !strcmp(argv[1], "login") ? 1 : 0;
        }
        if (!strcmp(argv[1], "--version")) puts("codex-cli 0.0.0");
        else if (!strcmp(argv[1], "--help")) puts("Codex CLI\nUsage: codex [OPTIONS]\nlogin app-server");
        else if (argc == 3 && !strcmp(argv[1], "login") && !strcmp(argv[2], "status")) {
            fputs("Not logged in\n", stderr);
            return bad ? 0 : 1;
        } else return 93;
        return bad ? 1 : 0;
    }
    if (!isatty(0) || !isatty(1) || !isatty(2) || strcmp(getenv("TERM"), "xterm-256color")) return 94;
    char path[512];
    snprintf(path, sizeof(path), "%s/diagnostic-log", home);
    if (mkdir(path, 0700)) return 101;
    snprintf(path, sizeof(path), "%s/diagnostic-log/codex-tui.log", home);
    FILE *log = fopen(path, "w");
    if (!log) return 102;
    fputs("OLD-LOG-MUST-NOT-BE-RETAINED\n", log);
    for (int i = 0; i < 32768; ++i) fputc('x', log);
    fputs("\nPRIVATE-TUI-LOG-TAIL\n", log);
    if (fclose(log)) return 103;
    snprintf(path, sizeof(path), "%s/state_5.sqlite", home);
    log = fopen(path, "w");
    if (!log) return 104;
    fputs("fixture", log);
    if (fclose(log)) return 105;
    struct termios attributes;
    if (tcgetattr(0, &attributes)) return 95;
    cfmakeraw(&attributes);
    if (tcsetattr(0, TCSANOW, &attributes)) return 96;
    fputs("\033[6n", stdout);
    fflush(stdout);
    char response[6];
    size_t count = 0;
    while (count < sizeof(response)) {
        ssize_t n = read(0, response + count, sizeof(response) - count);
        if (n <= 0) return 97;
        count += (size_t)n;
    }
    if (memcmp(response, "\033[1;1R", sizeof(response))) return 98;
    if (strstr(argv[0], "compact")) {
        fputs("Welcome\033[1Cto\033[1CCodex\033[2;1HSign\033[1Cin\033[1Cwith\033[1CChatGPT"
              "\033[3;1HProvide\033[1Cyour\033[1Cown\033[1CAPI\033[1Ckey", stdout);
    } else if (strstr(argv[0], "incomplete")) {
        fputs("Welcome to Codex\nSign in with ChatGPT\n", stdout);
    } else {
        fputs("\033]0;private title\007Welcome to \033[1mCodex\033[0m\nSign in with ChatGPT\nUse an OpenAI API key\n", stdout);
    }
    fflush(stdout);
    char key;
    while (read(0, &key, 1) == 1) {
        if (key == 3) {
            struct winsize size;
            if (ioctl(0, TIOCGWINSZ, &size) || size.ws_col != 100 || size.ws_row != 32) return 99;
            return bad ? 1 : 0;
        }
    }
    return 100;
}
'''


class CodexCliProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="codex-cli-probe-test-")
        cls.root = Path(cls.temporary.name)
        cls.probe, cls.fixture = cls.root / "probe", cls.root / "fixture"
        compiler = shlex.split(os.environ.get("CC", "cc"))
        source = cls.root / "fixture.c"
        source.write_text(FIXTURE)
        for source, output in [(PROBE, cls.probe), (source, cls.fixture)]:
            subprocess.run([*compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(source), "-o", str(output)], check=True, timeout=60)
        for suffix in ("bad", "wrong", "hang", "signal", "compact", "incomplete"):
            (cls.root / f"fixture-{suffix}").symlink_to(cls.fixture)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_probe(self, mode, suffix="", timeout=5000):
        env = dict(os.environ, CODEX_CLI_QUALIFY_TIMEOUT_MS=str(timeout),
                   CODEX_API_KEY="must-not-reach-child", OPENAI_API_KEY="must-not-reach-child")
        return subprocess.run([str(self.probe), mode, str(self.fixture) + suffix],
                              capture_output=True, text=True, env=env, timeout=10)

    def test_commands_require_output_and_exact_exit_status(self):
        for mode in ("version", "help", "login-status"):
            with self.subTest(mode=mode):
                good = self.run_probe(mode)
                self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
                self.assertIn(f"CODEX-CLI: PASS {mode}\n", good.stdout)
                bad = self.run_probe(mode, "-bad")
                self.assertNotEqual(bad.returncode, 0)
                self.assertNotIn(f"CODEX-CLI: PASS {mode}\n", bad.stdout)
                wrong = self.run_probe(mode, "-wrong")
                self.assertNotEqual(wrong.returncode, 0)
                self.assertNotIn(f"CODEX-CLI: PASS {mode}\n", wrong.stdout)

    def test_timeout_and_signal_cannot_pass(self):
        for suffix in ("-hang", "-signal"):
            with self.subTest(suffix=suffix):
                result = self.run_probe("version", suffix, timeout=200)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("CODEX-CLI: PASS", result.stdout)
                if suffix == "-hang":
                    self.assertIn(f"errno={errno.ETIMEDOUT}\n", result.stderr)

    def test_private_pty_query_resize_and_keyboard_exit(self):
        result = self.run_probe("pty-onboarding")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CODEX-CLI: PASS pty-onboarding\n", result.stdout)
        self.assertNotIn("private title", result.stdout)
        self.assertNotIn("\033", result.stdout)
        self.assertIn("PRIVATE-TUI-LOG-TAIL", result.stdout)
        self.assertNotIn("OLD-LOG-MUST-NOT-BE-RETAINED", result.stdout)
        self.assertIn("private database state_5.sqlite bytes=7", result.stdout)
        self.assertLess(len(result.stdout), 18000)
        result = self.run_probe("pty-onboarding", "-bad")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("CODEX-CLI: PASS pty-onboarding", result.stdout)

    def test_ratatui_cursor_spacing_and_default_api_label(self):
        result = self.run_probe("pty-onboarding", "-compact")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WelcometoCodexSigninwithChatGPTProvideyourownAPIkey", result.stdout)
        self.assertIn("CODEX-CLI: PASS pty-onboarding\n", result.stdout)
        result = self.run_probe("pty-onboarding", "-incomplete", timeout=2000)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("CODEX-CLI: PASS pty-onboarding", result.stdout)


if __name__ == "__main__":
    unittest.main()
