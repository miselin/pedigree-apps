#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include "json.h"

#define SESSION "pedigree-qualification"
#define CAPABILITY "session-cell-execution-resource-limits"
static const char *stage = "setup";
static long long deadline, progress_at;
static int input = -1, output = -1, request_id, cell_count, tool_calls;
static unsigned closed_cells;
static char cells[8][64];

static long long now_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static int ready(int fd, short events)
{
    for (;;) {
        long long now = now_ms();
        if (now < 0 || now >= deadline) { errno = ETIMEDOUT; return -1; }
        if (now >= progress_at) {
            printf("CODEX-CODE-MODE: waiting stage=%s\n", stage);
            progress_at = now + 30000;
        }
        struct pollfd p = {.fd = fd, .events = events};
        int n = poll(&p, 1, (int)(deadline - now < 1000 ? deadline - now : 1000));
        if (n > 0) return 0;
        if (n < 0 && errno != EINTR) return -1;
    }
}

static int transfer(int fd, void *buffer, size_t size, int sending)
{
    size_t done = 0;
    while (done < size) {
        if (ready(fd, sending ? POLLOUT : POLLIN)) return -1;
        ssize_t n = sending ? write(fd, (char *)buffer + done, size - done) :
                              read(fd, (char *)buffer + done, size - done);
        if (n > 0) done += (size_t)n;
        else if (!n) { errno = EPIPE; return -1; }
        else if (errno != EINTR && errno != EAGAIN) return -1;
    }
    return 0;
}

static int send_frame(const char *json)
{
    size_t n = strlen(json);
    unsigned char length[4] = {n & 255, (n >> 8) & 255, (n >> 16) & 255, (n >> 24) & 255};
    return transfer(input, length, 4, 1) || transfer(input, (void *)json, n, 1);
}

static int read_frame(void)
{
    unsigned char length[4];
    if (transfer(output, length, 4, 0)) return -1;
    uint32_t n = (uint32_t)length[0] | (uint32_t)length[1] << 8 |
                 (uint32_t)length[2] << 16 | (uint32_t)length[3] << 24;
    if (!n || n >= FRAME_SIZE) { errno = EMSGSIZE; return -1; }
    if (transfer(output, frame, n, 0) || parse_frame(n)) return -1;
    return 0;
}

static int is(int object, const char *key, const char *text)
{
    return equal(field(object, key), '"', text);
}

static int integer(int index, char *buffer, size_t capacity)
{
    if (index < 0 || tokens[index].kind != 'p') return -1;
    size_t n = (size_t)(tokens[index].end - tokens[index].start);
    if (!n || n >= capacity) return -1;
    memcpy(buffer, frame + tokens[index].start, n); buffer[n] = 0;
    char *end;
    errno = 0;
    strtoll(buffer, &end, 10);
    return errno || *end || strchr(buffer, '.') || strchr(buffer, 'e') || strchr(buffer, 'E') ? -1 : 0;
}

/* Only the fixed echo callback is serviced; unknown tools cannot execute anything. */
static int async_message(void)
{
    if (is(0, "type", "cell/closed")) {
        if (!is(0, "sessionId", SESSION)) return -1;
        for (int i = 0; i < cell_count; ++i) if (is(0, "cellId", cells[i])) {
            if (closed_cells & (1u << i)) return -1;
            closed_cells |= 1u << i;
            return 1;
        }
        return -1;
    }
    if (!is(0, "type", "delegate/request")) return 0;
    int request = field(0, "request"), call = field(request, "invocation");
    int name = field(call, "tool_name"), argument = field(call, "input");
    char id[32], reply[256];
    if (strcmp(stage, "promises-tool") || tool_calls || !is(0, "sessionId", SESSION) ||
        !is(request, "type", "tool/invoke") || !is(call, "cell_id", cells[cell_count - 1]) ||
        !is(call, "tool_kind", "function") || !is(name, "name", "echo") ||
        !equal(field(name, "namespace"), 'p', "null") ||
        !equal(field(argument, "value"), 'p', "42") || integer(field(0, "id"), id, sizeof(id))) return -1;
    snprintf(reply, sizeof(reply), "{\"type\":\"delegate/response\",\"id\":%s,\"result\":{\"status\":\"ok\","
             "\"value\":{\"type\":\"tool/result\",\"result\":{\"answer\":43}}}}", id);
    if (send_frame(reply)) return -1;
    ++tool_calls;
    return 1;
}

static int receive(const char *type, int id)
{
    char expected[32];
    snprintf(expected, sizeof(expected), "%d", id);
    for (;;) {
        if (read_frame()) return -1;
        int handled = async_message();
        if (handled < 0) return -1;
        if (handled) continue;
        if (!is(0, "type", type) || (id && !equal(field(0, "id"), 'p', expected))) return -1;
        if (!id) return 0;
        int result = field(0, "result");
        if (!is(result, "status", "ok")) return -1;
        return field(result, "value");
    }
}

static int request(const char *body, const char *response_type)
{
    char message[4096];
    int id = ++request_id;
    int n = snprintf(message, sizeof(message), "{\"type\":\"operation/request\",\"id\":%d,\"request\":%s}", id, body);
    if (n < 0 || (size_t)n >= sizeof(message) || send_frame(message)) return -1;
    int response = receive("operation/response", id);
    return response >= 0 && is(response, "type", response_type) ? response : -1;
}

static int runtime(int object, const char *kind, const char *text, int error)
{
    int result = field(object, kind), content = field(result, "content_items");
    char duration[32];
    if (!is(result, "cell_id", cells[cell_count - 1]) || content < 0 || tokens[content].kind != '[' ||
        integer(field(result, "code_mode_host_duration_ns"), duration, sizeof(duration)) || duration[0] == '-') return -1;
    if (text) {
        int item = content + 1;
        if (item == tokens[content].next || !is(item, "type", "input_text") || !is(item, "text", text) ||
            tokens[item].next != tokens[content].next) return -1;
    } else if (content + 1 != tokens[content].next) return -1;
    if (!strcmp(kind, "Result")) {
        if (error) {
            char message[4096];
            if (copy_string(field(result, "error_text"), message, sizeof(message)) || !strstr(message, "qualify-error")) return -1;
        } else if (!equal(field(result, "error_text"), 'p', "null")) return -1;
    }
    return 0;
}

static int execute(const char *source, const char *text, int error, int pending)
{
    static const char tool[] = "[{\"name\":\"echo\",\"tool_name\":{\"name\":\"echo\",\"namespace\":null},"
        "\"description\":\"qualification callback\",\"kind\":\"function\",\"input_schema\":null,\"output_schema\":null}]";
    char body[3072];
    if (cell_count == 8) return -1;
    /* Fresh sessions use sequential cell IDs; all later messages must correlate. */
    snprintf(cells[cell_count], sizeof(cells[0]), "%d", cell_count + 1);
    ++cell_count;
    int n = snprintf(body, sizeof(body), "{\"method\":\"session/execute\",\"sessionId\":\"" SESSION "\",\"request\":{"
        "\"tool_call_id\":\"qualify-%d\",\"enabled_tools\":%s,\"source\":\"%s\",\"yield_time_ms\":%d,\"max_output_tokens\":1024}}",
        cell_count, !strcmp(stage, "promises-tool") ? tool : "[]", source, pending ? 1 : 1000);
    if (n < 0 || (size_t)n >= sizeof(body)) return -1;
    int result = request(body, "execution/started");
    int id = request_id;
    if (result < 0 || !is(result, "cellId", cells[cell_count - 1])) return -1;
    result = receive("execute/initialResponse", id);
    if (result < 0) return -1;
    if (pending) return runtime(result, "Yielded", NULL, 0);
    int seen_text = 0;
    /* A yield can carry output; count it once across the whole execution. */
    while (field(result, "Yielded") >= 0) {
        if (runtime(result, "Yielded", NULL, 0)) {
            if (!text || seen_text || runtime(result, "Yielded", text, 0)) return -1;
            seen_text = 1;
        }
        snprintf(body, sizeof(body), "{\"method\":\"session/wait\",\"sessionId\":\"" SESSION "\","
                 "\"request\":{\"cell_id\":\"%s\",\"yield_time_ms\":1000}}", cells[cell_count - 1]);
        result = request(body, "wait/completed");
        if (result < 0) return -1;
        int outcome = field(result, "outcome");
        result = field(outcome, "LiveCell");
        if (result < 0) result = field(outcome, "MissingCell");
    }
    if (runtime(result, "Result", NULL, error)) {
        if (!text || seen_text || runtime(result, "Result", text, error)) return -1;
        seen_text = 1;
    }
    return text && !seen_text ? -1 : 0;
}

static int cleanup(const char *path)
{
    struct stat st;
    if (lstat(path, &st)) return -1;
    if (!S_ISDIR(st.st_mode)) return unlink(path);
    DIR *dir = opendir(path);
    if (!dir) return -1;
    struct dirent *entry;
    int result = 0;
    errno = 0;
    while ((entry = readdir(dir))) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        char child[4096];
        int n = snprintf(child, sizeof(child), "%s/%s", path, entry->d_name);
        if (n < 0 || (size_t)n >= sizeof(child) || cleanup(child)) { result = -1; break; }
        errno = 0;
    }
    if (errno) result = -1;
    if (closedir(dir)) result = -1;
    return result ? -1 : rmdir(path);
}

static void phase(const char *name)
{
    stage = name;
    printf("CODEX-CODE-MODE: RUN %s\n", stage);
}

static void pass(void) { printf("CODEX-CODE-MODE: PASS %s\n", stage); }

int main(int argc, char **argv)
{
    const char *program = argc == 2 ? argv[1] : "/usr/libexec/codex-code-mode-host";
    char home[] = "/tmp/codex-code-mode-qualify-XXXXXX", home_env[160], codex_env[160], tmp_env[160];
    int pipes_in[2] = {-1, -1}, pipes_out[2] = {-1, -1}, status = -1, reaped = 0, failed = 1, made_home = 0;
    pid_t child = -1;
    setvbuf(stdout, NULL, _IONBF, 0);
    signal(SIGPIPE, SIG_IGN);
    long timeout = 600000;
    const char *setting = getenv("CODEX_CODE_MODE_QUALIFY_TIMEOUT_MS");
    if (setting) {
        char *end; errno = 0; timeout = strtol(setting, &end, 10);
        if (errno || *end || timeout < 100 || timeout > 2400000) return 2;
    }
    deadline = now_ms() + timeout; progress_at = now_ms() + 30000;
    if (argc > 2 || program[0] != '/' || !mkdtemp(home)) goto done;
    made_home = 1;
    if (pipe(pipes_in) || pipe(pipes_out)) goto done;
    child = fork();
    if (child < 0) goto done;
    if (!child) {
        if (setpgid(0, 0) || chdir(home) || dup2(pipes_in[0], 0) < 0 || dup2(pipes_out[1], 1) < 0) _exit(126);
        close(pipes_in[0]); close(pipes_in[1]); close(pipes_out[0]); close(pipes_out[1]);
        snprintf(home_env, sizeof(home_env), "HOME=%s", home);
        snprintf(codex_env, sizeof(codex_env), "CODEX_HOME=%s", home);
        snprintf(tmp_env, sizeof(tmp_env), "TMPDIR=%s", home);
        char *env[] = {home_env, codex_env, tmp_env, "PATH=/usr/bin:/bin", "LANG=C", "RUST_LOG=warn", NULL};
        char *args[] = {(char *)program, "--listen", "stdio", NULL};
        execve(program, args, env);
        _exit(127);
    }
    setpgid(child, child);
    close(pipes_in[0]); pipes_in[0] = -1; close(pipes_out[1]); pipes_out[1] = -1;
    input = pipes_in[1]; output = pipes_out[0];
    if (fcntl(input, F_SETFL, O_NONBLOCK) || fcntl(output, F_SETFL, O_NONBLOCK)) goto done;
    phase("handshake");
    if (send_frame("{\"type\":\"connection/hello\",\"supportedVersions\":[1],\"requiredCapabilities\":[\"" CAPABILITY
                   "\"],\"optionalCapabilities\":[]}") || receive("connection/ready", 0)) goto done;
    int caps = field(0, "capabilities");
    if (!equal(field(0, "selectedVersion"), 'p', "1") || caps < 0 || tokens[caps].kind != '[' ||
        caps + 1 == tokens[caps].next || !equal(caps + 1, '"', CAPABILITY) ||
        tokens[caps + 1].next != tokens[caps].next) goto done;
    pass();
    phase("session-open");
    int result = request("{\"method\":\"session/open\",\"sessionId\":\"" SESSION "\","
        "\"cellExecutionLimits\":{\"maxHeapSizeBytes\":67108864,\"maxYieldTimeMs\":1000}}", "session/ready");
    if (result < 0 || !is(result, "sessionId", SESSION)) goto done;
    pass();
    phase("arithmetic");
    if (execute("store('answer', 6 * 7); text(load('answer'));", "42", 0, 0)) goto done;
    pass();
    phase("promises-tool");
    if (execute("const r = await tools.echo({value: await Promise.resolve(load('answer'))}); text(r.answer);", "43", 0, 0) || tool_calls != 1) goto done;
    pass();
    phase("exception");
    if (execute("throw new Error('qualify-error');", NULL, 1, 0)) goto done;
    pass();
    phase("recovery");
    if (execute("text(load('answer') + 1);", "43", 0, 0)) goto done;
    pass();
    phase("yield-terminate");
    if (execute("await new Promise(() => {});", NULL, 0, 1)) goto done;
    char body[256];
    snprintf(body, sizeof(body), "{\"method\":\"session/wait\",\"sessionId\":\"" SESSION "\","
             "\"request\":{\"cell_id\":\"%s\",\"yield_time_ms\":1}}", cells[cell_count - 1]);
    result = request(body, "wait/completed");
    if (result < 0 || runtime(field(field(result, "outcome"), "LiveCell"), "Yielded", NULL, 0)) goto done;
    snprintf(body, sizeof(body), "{\"method\":\"session/terminate\",\"sessionId\":\"" SESSION "\",\"cellId\":\"%s\"}", cells[cell_count - 1]);
    result = request(body, "wait/completed");
    if (result < 0 || runtime(field(field(result, "outcome"), "LiveCell"), "Terminated", NULL, 0)) goto done;
    pass();
    phase("termination-recovery");
    if (execute("text(load('answer') * 2);", "84", 0, 0)) goto done;
    pass();
    phase("shutdown");
    result = request("{\"method\":\"session/shutdown\",\"sessionId\":\"" SESSION "\"}", "session/closed");
    if (result < 0 || !is(result, "sessionId", SESSION) || closed_cells != (1u << cell_count) - 1) goto done;
    close(input); input = pipes_in[1] = -1;
    int eof = 0;
    while (now_ms() < deadline && (!reaped || !eof)) {
        if (!reaped) {
            pid_t ended = waitpid(child, &status, WNOHANG);
            if (ended == child) reaped = 1;
            else if (ended < 0 && errno != EINTR) goto done;
        }
        if (!eof) {
            if (ready(output, POLLIN)) goto done;
            char extra;
            ssize_t n = read(output, &extra, 1);
            if (n > 0 || (n < 0 && errno != EAGAIN && errno != EINTR)) goto done;
            if (!n) eof = 1;
        }
        poll(NULL, 0, 10);
    }
    if (!eof || !reaped || !WIFEXITED(status) || WEXITSTATUS(status)) goto done;
    pass(); failed = 0;
done:
    {
        int saved = errno;
        if (failed && frame[0]) fprintf(stderr, "CODEX-CODE-MODE: last frame %.2048s\n", frame);
        if (child > 0 && !reaped) {
            kill(-child, SIGKILL); kill(child, SIGKILL);
            long long until = now_ms() + 2000;
            while (now_ms() < until) {
                if (waitpid(child, &status, WNOHANG) == child) { reaped = 1; break; }
                poll(NULL, 0, 10);
            }
        }
        if (child > 0) kill(-child, SIGKILL);
        for (int i = 0; i < 2; ++i) {
            if (pipes_in[i] >= 0) close(pipes_in[i]);
            if (pipes_out[i] >= 0) close(pipes_out[i]);
        }
        if (made_home && cleanup(home)) { failed = 1; saved = errno; }
        printf("CODEX-CODE-MODE: %s stage=%s status=%d reaped=%d errno=%d\n", failed ? "FAIL" : "complete", stage, status, reaped, saved);
        if (!failed) puts("CODEX-CODE-MODE: PASS all (9 checks)");
    }
    return failed;
}
