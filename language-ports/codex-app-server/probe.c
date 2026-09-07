#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

enum { FRAME_SIZE = 65536, TOKEN_COUNT = 4096, TIMEOUT_MS = 240000 };
struct token { char kind; int start, end, next; };
static struct token tokens[TOKEN_COUNT];
static char frame[FRAME_SIZE], pending[FRAME_SIZE];
static size_t pending_size;
static int position, token_count;
static const char *stage = "setup";
static const char *progress_home;
static long long deadline, progress_at;

static long long now_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void space(void)
{
    while (frame[position] && strchr(" \r\n\t", frame[position])) ++position;
}

static int hex4(int *offset)
{
    int result = 0;
    for (int i = 0; i < 4; ++i) {
        unsigned char c = (unsigned char)frame[(*offset)++];
        if (!isxdigit(c)) return -1;
        result = result * 16 + (isdigit(c) ? c - '0' : tolower(c) - 'a' + 10);
    }
    return result;
}

/* Compare decoded names so escaped spellings cannot bypass duplicate detection. */
static int string_char(int *offset)
{
    unsigned char c = (unsigned char)frame[(*offset)++];
    if (c == '\\') {
        c = (unsigned char)frame[(*offset)++];
        if (c != 'u') {
            static const char escapes[] = "\"\\/bfnrt", decoded[] = "\"\\/\b\f\n\r\t";
            const char *escape = strchr(escapes, c);
            return c && escape ? decoded[escape - escapes] : -1;
        }
        int result = hex4(offset);
        if (result >= 0xd800 && result <= 0xdbff) {
            if (frame[(*offset)++] != '\\' || frame[(*offset)++] != 'u') return -1;
            int low = hex4(offset);
            return low >= 0xdc00 && low <= 0xdfff ?
                   0x10000 + (result - 0xd800) * 1024 + low - 0xdc00 : -1;
        }
        return result >= 0xdc00 && result <= 0xdfff ? -1 : result;
    }
    if (c < 0x80) return c;
    int extra = c >= 0xf0 && c <= 0xf4 ? 3 : c >= 0xe0 && c <= 0xef ? 2 :
                c >= 0xc2 && c <= 0xdf ? 1 : 0;
    if (!extra) return -1;
    int result = c & ((1 << (6 - extra)) - 1);
    for (int i = 0; i < extra; ++i) {
        c = (unsigned char)frame[(*offset)++];
        if ((c & 0xc0) != 0x80) return -1;
        result = result * 64 + (c & 0x3f);
    }
    int minimum = extra == 1 ? 0x80 : extra == 2 ? 0x800 : 0x10000;
    return result < minimum || result > 0x10ffff ||
           (result >= 0xd800 && result <= 0xdfff) ? -1 : result;
}

static int same_string(int left, int right)
{
    int a = tokens[left].start + 1, b = tokens[right].start + 1;
    while (a < tokens[left].end - 1 && b < tokens[right].end - 1)
        if (string_char(&a) != string_char(&b)) return 0;
    return a == tokens[left].end - 1 && b == tokens[right].end - 1;
}

/* Subtree boundaries keep field lookup local to the requested object. */
static int value(int depth)
{
    int index, child;
    char c;
    if (depth > 32 || token_count == TOKEN_COUNT) return -1;
    space();
    index = token_count++;
    tokens[index].start = position;
    c = tokens[index].kind = frame[position++];
    if (c == '{' || c == '[') {
        char end = c == '{' ? '}' : ']';
        space();
        if (frame[position] != end) for (;;) {
            child = value(depth + 1);
            if (child < 0) return -1;
            if (c == '{') {
                if (tokens[child].kind != '"') return -1;
                for (int previous = index + 1; previous < child;
                     previous = tokens[previous + 1].next)
                    if (same_string(previous, child)) return -1;
                space();
                if (frame[position++] != ':' || value(depth + 1) < 0) return -1;
            }
            space();
            if (frame[position] == end) break;
            if (frame[position++] != ',') return -1;
        }
        ++position;
    } else if (c == '"') {
        while ((c = frame[position++]) != '"') {
            if ((unsigned char)c < 32) return -1;
            if (c == '\\') {
                c = frame[position++];
                if (c == 'u') {
                    for (int i = 0; i < 4; ++i)
                        if (!isxdigit((unsigned char)frame[position++])) return -1;
                } else if (!c || !strchr("\"\\/bfnrt", c)) return -1;
            }
        }
    } else {
        --position;
        tokens[index].kind = 'p';
        if (!strncmp(frame + position, "null", 4) ||
            !strncmp(frame + position, "true", 4)) position += 4;
        else if (!strncmp(frame + position, "false", 5)) position += 5;
        else {
            if (frame[position] == '-') ++position;
            if (frame[position] == '0') ++position;
            else {
                if (frame[position] < '1' || frame[position] > '9') return -1;
                while (isdigit((unsigned char)frame[position])) ++position;
            }
            if (frame[position] == '.') {
                ++position;
                if (!isdigit((unsigned char)frame[position])) return -1;
                while (isdigit((unsigned char)frame[position])) ++position;
            }
            if (frame[position] == 'e' || frame[position] == 'E') {
                ++position;
                if (frame[position] == '+' || frame[position] == '-') ++position;
                if (!isdigit((unsigned char)frame[position])) return -1;
                while (isdigit((unsigned char)frame[position])) ++position;
            }
        }
    }
    tokens[index].end = position;
    tokens[index].next = token_count;
    if (tokens[index].kind == '"') {
        int offset = tokens[index].start + 1;
        while (offset < position - 1) if (string_char(&offset) < 0) return -1;
        if (offset != position - 1) return -1;
    }
    return index;
}

static int equal(int index, char kind, const char *expected)
{
    int begin, end;
    if (index < 0 || tokens[index].kind != kind) return 0;
    begin = tokens[index].start + (kind == '"');
    end = tokens[index].end - (kind == '"');
    if (kind == '"') {
        size_t offset = 0, length = strlen(expected);
        while (begin < end)
            if (offset == length || string_char(&begin) != (unsigned char)expected[offset++])
                return 0;
        return offset == length;
    }
    return end - begin == (int)strlen(expected) &&
           !memcmp(frame + begin, expected, (size_t)(end - begin));
}

static int field(int object, const char *name)
{
    int found = -1;
    if (object < 0 || tokens[object].kind != '{') return -1;
    for (int i = object + 1; i < tokens[object].next;) {
        int v = i + 1;
        if (equal(i, '"', name)) {
            if (found != -1) return -1;
            found = v;
        }
        i = tokens[v].next;
    }
    return found;
}

static void report_progress(void)
{
    static const char *names[] = {"state_5.sqlite", "logs_2.sqlite", "goals_1.sqlite",
                                  "memories_1.sqlite", "queue_1.sqlite"};
    static const char *suffixes[] = {"", "-wal", "-shm"};
    int saved_errno = errno, found = 0;
    /* Fixed names bound the inspection and avoid reading database contents. */
    for (size_t i = 0; i < sizeof(names) / sizeof(names[0]); ++i)
        for (size_t j = 0; j < sizeof(suffixes) / sizeof(suffixes[0]); ++j) {
            char path[256];
            struct stat st;
            int n = snprintf(path, sizeof(path), "%s/%s%s", progress_home, names[i], suffixes[j]);
            if (n < 0 || (size_t)n >= sizeof(path) || lstat(path, &st) || !S_ISREG(st.st_mode))
                continue;
            fprintf(stderr, "CODEX-APP-SERVER: waiting stage=%s file=%s size=%lld\n",
                    stage, path, (long long)st.st_size);
            ++found;
        }
    if (!found) fprintf(stderr, "CODEX-APP-SERVER: waiting stage=%s sqlite-files=0\n", stage);
    errno = saved_errno;
}

static int wait_ready(int fd, short events)
{
    for (;;) {
        long long now = now_ms();
        if (progress_home && now >= progress_at) {
            report_progress();
            progress_at = now_ms() + 30000;
        }
        now = now_ms();
        long long remaining = deadline - now;
        struct pollfd p = {fd, events, 0};
        int result;
        if (remaining <= 0) { errno = ETIMEDOUT; return -1; }
        if (progress_home && progress_at - now < remaining)
            remaining = progress_at - now;
        if (remaining <= 0) continue;
        result = poll(&p, 1, (int)remaining);
        if (result < 0 && errno == EINTR) continue;
        if (!result) continue;
        return result > 0 ? 0 : -1;
    }
}

static int send_text(int fd, const char *text)
{
    size_t left = strlen(text);
    while (left) {
        ssize_t n;
        if (wait_ready(fd, POLLOUT)) return -1;
        n = write(fd, text, left);
        if (n < 0 && (errno == EINTR || errno == EAGAIN)) continue;
        if (n <= 0) return -1;
        text += n;
        left -= (size_t)n;
    }
    return 0;
}

static int response(int fd, const char *id)
{
    for (;;) {
        char *newline = memchr(pending, '\n', pending_size);
        if (newline) {
            size_t length = (size_t)(newline - pending);
            int received_id, result;
            memcpy(frame, pending, length);
            frame[length] = 0;
            pending_size -= length + 1;
            memmove(pending, newline + 1, pending_size);
            position = token_count = 0;
            if (value(0) != 0) return -1;
            space();
            if ((size_t)position != length || tokens[0].kind != '{') return -1;
            received_id = field(0, "id");
            if (received_id < 0 && field(0, "method") >= 0) continue;
            if (!equal(received_id, 'p', id) || field(0, "error") >= 0) {
                fprintf(stderr, "CODEX-APP-SERVER: unexpected response %.1024s\n", frame);
                return -1;
            }
            result = field(0, "result");
            return result >= 0 && tokens[result].kind == '{' ? result : -1;
        }
        if (pending_size == sizeof(pending) - 1 || wait_ready(fd, POLLIN)) return -1;
        ssize_t n = read(fd, pending + pending_size, sizeof(pending) - 1 - pending_size);
        if (n < 0 && (errno == EINTR || errno == EAGAIN)) continue;
        if (n <= 0) return -1;
        pending_size += (size_t)n;
    }
}

static int request(int out, int in, const char *id, const char *name, const char *params)
{
    char message[1024];
    stage = name;
    printf("CODEX-APP-SERVER: RUN %s\n", stage);
    int n = snprintf(message, sizeof(message),
                     "{\"id\":%s,\"method\":\"%s\",\"params\":%s}\n", id, name, params);
    if (n < 0 || (size_t)n >= sizeof(message) || send_text(out, message)) return -1;
    return response(in, id);
}

static int save_file(const char *path, const char *contents)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    size_t length = strlen(contents);
    if (fd < 0) return -1;
    ssize_t n = write(fd, contents, length);
    int error = close(fd);
    return n == (ssize_t)length && !error ? 0 : -1;
}

static int remove_tree(const char *path, int depth)
{
    struct stat st;
    if (depth > 16 || lstat(path, &st)) return -1;
    if (!S_ISDIR(st.st_mode)) return unlink(path);
    DIR *dir = opendir(path);
    struct dirent *entry;
    int result = 0, count = 0;
    if (!dir) return -1;
    while ((entry = readdir(dir))) {
        char child[1024];
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        int n = snprintf(child, sizeof(child), "%s/%s", path, entry->d_name);
        if (++count > 10000 || n < 0 || (size_t)n >= sizeof(child) ||
            remove_tree(child, depth + 1)) { result = -1; break; }
    }
    if (closedir(dir)) result = -1;
    return result ? result : rmdir(path);
}

static int cleanup_home(const char *path)
{
    struct stat st;
    if (!remove_tree(path, 0)) return 0;
    int error = errno;
    if (error == ENOENT && lstat(path, &st) < 0 && errno == ENOENT) return 0;
    errno = error;
    return -1;
}

static int wait_child(pid_t child, int output, int *status, int milliseconds)
{
    long long end = now_ms() + milliseconds;
    do {
        char discard[4096];
        for (int i = 0; output >= 0 && i < 16; ++i)
            if (read(output, discard, sizeof(discard)) <= 0) break;
        pid_t result = waitpid(child, status, WNOHANG);
        if (result == child) return 0;
        if (result < 0 && errno != EINTR) return -1;
        poll(NULL, 0, 20);
    } while (now_ms() < end);
    return -1;
}

int main(int argc, char **argv)
{
    char home[] = "/tmp/codex-app-server-qualify-XXXXXX";
    char config[256], fixture[256], params[512];
    char home_env[256], codex_env[256], temp_env[256];
    int to_child[2] = {-1, -1}, from_child[2] = {-1, -1};
    int result, item, exit_code = 1, status = 0, home_created = 0;
    pid_t child = -1;
    char *server = argc == 2 ? argv[1] : "/usr/bin/codex-app-server";
    const char *timeout_env = getenv("CODEX_APP_SERVER_QUALIFY_TIMEOUT_MS");
    long timeout_ms = TIMEOUT_MS;
    if (argc > 2 || server[0] != '/') {
        fprintf(stderr, "usage: %s [/absolute/path/to/codex-app-server]\n", argv[0]);
        return 2;
    }
    if (timeout_env) {
        char *end;
        errno = 0;
        timeout_ms = strtol(timeout_env, &end, 10);
        if (errno || !isdigit((unsigned char)timeout_env[0]) || *end ||
            timeout_ms < 1 || timeout_ms > 1800000) {
            fputs("CODEX-APP-SERVER: timeout must be an integer from 1 to 1800000 ms\n", stderr);
            return 2;
        }
    }
    setvbuf(stdout, NULL, _IONBF, 0);
    signal(SIGPIPE, SIG_IGN);
    deadline = now_ms() + timeout_ms;
    if (!mkdtemp(home)) goto done;
    home_created = 1;
    progress_home = home;
    progress_at = now_ms() + 30000;
    snprintf(config, sizeof(config), "%s/config.toml", home);
    snprintf(fixture, sizeof(fixture), "%s/fixture.txt", home);
    if (save_file(config, "model_provider = \"openai\"\ncheck_for_update_on_startup = false\n"
                          "[analytics]\nenabled = false\n") ||
        save_file(fixture, "pedigree app-server\n") || pipe(to_child) || pipe(from_child)) goto done;
    snprintf(home_env, sizeof(home_env), "HOME=%s", home);
    snprintf(codex_env, sizeof(codex_env), "CODEX_HOME=%s", home);
    snprintf(temp_env, sizeof(temp_env), "TMPDIR=%s", home);
    child = fork();
    if (child < 0) goto done;
    if (!child) {
        char *args[] = {server, "--listen", "stdio://", NULL};
        /* An explicit environment prevents an installed account from entering this test. */
        char *environment[] = {home_env, codex_env, temp_env, "PATH=/usr/bin:/bin",
                               "RUST_LOG=warn,codex_app_server::message_processor=trace,os_info=trace",
                               "LANG=C", "OTEL_SDK_DISABLED=true", NULL};
        if (setpgid(0, 0) || chdir(home) || dup2(to_child[0], STDIN_FILENO) < 0 ||
            dup2(from_child[1], STDOUT_FILENO) < 0) _exit(125);
        for (int i = 0; i < 2; ++i) { close(to_child[i]); close(from_child[i]); }
        execve(args[0], args, environment);
        perror("CODEX-APP-SERVER: execve");
        _exit(126);
    }
    close(to_child[0]); to_child[0] = -1;
    close(from_child[1]); from_child[1] = -1;
    if (fcntl(to_child[1], F_SETFL, O_NONBLOCK) ||
        fcntl(from_child[0], F_SETFL, O_NONBLOCK)) {
        close(from_child[0]); from_child[0] = -1;
        goto done;
    }
    result = request(to_child[1], from_child[0], "1", "initialize",
                     "{\"clientInfo\":{\"name\":\"pedigree-qualify\",\"title\":\"Pedigree qualification\",\"version\":\"1\"}}");
    item = field(result, "userAgent");
    if (item < 0 || tokens[item].kind != '"' || tokens[item].end - tokens[item].start <= 2 ||
        !equal(field(result, "codexHome"), '"', home) ||
        !equal(field(result, "platformFamily"), '"', "unix") ||
        !equal(field(result, "platformOs"), '"', "linux") ||
        send_text(to_child[1], "{\"method\":\"initialized\"}\n")) goto done;
    puts("CODEX-APP-SERVER: PASS initialize");
    result = request(to_child[1], from_child[0], "2", "account/read", "{\"refreshToken\":false}");
    if (!equal(field(result, "account"), 'p', "null") ||
        !equal(field(result, "requiresOpenaiAuth"), 'p', "true")) goto done;
    puts("CODEX-APP-SERVER: PASS account-read");
    result = request(to_child[1], from_child[0], "3", "config/read", "{\"includeLayers\":false}");
    item = field(result, "config");
    if (!equal(field(item, "model_provider"), '"', "openai") ||
        !equal(field(field(item, "analytics"), "enabled"), 'p', "false")) goto done;
    puts("CODEX-APP-SERVER: PASS config-read");
    result = request(to_child[1], from_child[0], "4", "thread/list", "{\"limit\":1}");
    item = field(result, "data");
    if (item < 0 || tokens[item].kind != '[' || tokens[item].next != item + 1 ||
        !equal(field(result, "nextCursor"), 'p', "null")) goto done;
    puts("CODEX-APP-SERVER: PASS thread-list");
    snprintf(params, sizeof(params), "{\"path\":\"%s\"}", fixture);
    result = request(to_child[1], from_child[0], "5", "fs/readFile", params);
    if (!equal(field(result, "dataBase64"), '"', "cGVkaWdyZWUgYXBwLXNlcnZlcgo=")) goto done;
    puts("CODEX-APP-SERVER: PASS fs-read-file");
    exit_code = 0;
done:
    if (exit_code) fprintf(stderr, "CODEX-APP-SERVER: FAIL stage=%s errno=%d\n", stage, errno);
    for (int i = 0; i < 2; ++i) {
        if (to_child[i] >= 0) close(to_child[i]);
    }
    if (child > 0) {
        /* Guest teardown can drain SQLite and background tasks well after EOF. */
        if (wait_child(child, from_child[0], &status, 60000)) {
            kill(-child, SIGTERM);
            kill(child, SIGTERM);
            if (wait_child(child, from_child[0], &status, 2000)) {
                kill(-child, SIGKILL);
                kill(child, SIGKILL);
                if (wait_child(child, from_child[0], &status, 2000)) status = -1;
            }
            fprintf(stderr, "CODEX-APP-SERVER: FAIL shutdown required termination\n");
            exit_code = 1;
        }
        if (status == -1 || !WIFEXITED(status) || WEXITSTATUS(status)) {
            fprintf(stderr, "CODEX-APP-SERVER: FAIL child status=%d\n", status);
            exit_code = 1;
        }
        kill(-child, SIGKILL);
    }
    for (int i = 0; i < 2; ++i) if (from_child[i] >= 0) close(from_child[i]);
    if (home_created && cleanup_home(home)) {
        fprintf(stderr, "CODEX-APP-SERVER: FAIL cleanup errno=%d\n", errno);
        exit_code = 1;
    }
    if (!exit_code) puts("CODEX-APP-SERVER: PASS all (5 checks)");
    return exit_code;
}
