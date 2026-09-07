import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


PROBE = Path(__file__).resolve().parents[1] / "language-ports/codex-app-server/probe.c"
HARNESS = r'''
#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif
#include <sys/stat.h>
static int test_lstat(const char *path, struct stat *st);
#define lstat test_lstat
#define main qualifier_main
#include PROBE_SOURCE
#undef main
#undef lstat
#include <assert.h>

static const char *missing_child;
static int test_lstat(const char *path, struct stat *st)
{
    if (missing_child && !strcmp(path, missing_child)) {
        errno = ENOENT;
        return -1;
    }
    return fstatat(AT_FDCWD, path, st, AT_SYMLINK_NOFOLLOW);
}

static int check_response(const char *wire, size_t length)
{
    assert(length < sizeof(pending));
    memcpy(pending, wire, length);
    pending_size = length;
    deadline = now_ms() + 100;
    return response(-1, "1");
}
#define RESPONSE(s) check_response(s, sizeof(s) - 1)

int main(void)
{
    int result = RESPONSE("{\"id\":1,\"result\":{\"ok\":true,\"nested\":{\"ok\":false},"
                          "\"values\":[null,-1.2e+3,\"\\uD83D\\uDE80\"]}} \r\n");
    assert(result >= 0 && equal(field(result, "ok"), 'p', "true"));
    assert(RESPONSE("{\"id\":1,\"error\":null,\"error\":{},\"result\":{}}\n") < 0);
    assert(RESPONSE("{\"id\":1,\"error\":null,\"\\u0065rror\":{},\"result\":{}}\n") < 0);
    assert(RESPONSE("{\"id\":1,\"result\":{\"data\":[],\"data\":[]}}\n") < 0);
    assert(RESPONSE("{\"id\":1,\"result\":{\"\303\251\":1,\"\\u00e9\":2}}\n") < 0);
    assert(RESPONSE("{\"id\":1,\"result\":{\"\360\237\232\200\":1,\"\\uD83D\\uDE80\":2}}\n") < 0);
    assert(RESPONSE("{\"id\":1,\"result\":{}}\0trailing bytes\n") < 0);
    assert(RESPONSE("{\"id\":1,\"result\":{}} {}\n") < 0);
    assert(RESPONSE("{\"id\":1,\"result\":{\"bad\":\"\\ud800\"}}\n") < 0);
    assert(RESPONSE("{\"id\":1,\"result\":{\"bad\":\"\300\200\"}}\n") < 0);
    result = RESPONSE("{\"\\u0069d\":1,\"result\":{\"ok\":\"o\\u006b\"}}\n");
    assert(result >= 0 && equal(field(result, "ok"), '"', "ok"));

    char home[] = "/tmp/codex-probe-test-XXXXXX", child[256], outside[256], link[256];
    struct stat st;
    assert(mkdtemp(home));
    snprintf(child, sizeof(child), "%s/child", home);
    assert(!save_file(child, "fixture"));
    missing_child = child;
    assert(cleanup_home(home) == -1 && errno == ENOENT);
    assert(!lstat(home, &st) && S_ISDIR(st.st_mode));
    missing_child = NULL;
    snprintf(outside, sizeof(outside), "%s-outside", home);
    snprintf(link, sizeof(link), "%s/link", home);
    assert(!save_file(outside, "preserve"));
    assert(!symlink(outside, link));
    assert(!cleanup_home(home));
    assert(lstat(home, &st) == -1 && errno == ENOENT);
    assert(!lstat(outside, &st) && S_ISREG(st.st_mode));
    assert(!unlink(outside));
    assert(!cleanup_home(home));
    puts("CODEX-PROBE-TEST: PASS parser and cleanup");
    return 0;
}
'''


class CodexAppServerProbeTest(unittest.TestCase):
    def test_parser_and_cleanup(self):
        with tempfile.TemporaryDirectory(prefix="codex-probe-test-") as temporary:
            root = Path(temporary)
            source, executable = root / "test.c", root / "test"
            source.write_text(HARNESS.replace("PROBE_SOURCE", json.dumps(str(PROBE))))
            compiler = shlex.split(os.environ.get("CC", "cc"))
            subprocess.run(
                [*compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                 str(source), "-o", str(executable)], check=True, timeout=60,
            )
            result = subprocess.run([str(executable)], check=True, capture_output=True,
                                    text=True, timeout=10)
            self.assertEqual(result.stdout, "CODEX-PROBE-TEST: PASS parser and cleanup\n")


if __name__ == "__main__":
    unittest.main()
