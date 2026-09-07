#define _GNU_SOURCE
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

enum { OUTPUT_LIMIT = 262144 };
struct terminal_output {
    char text[OUTPUT_LIMIT], sequence[128];
    size_t used, sequence_used;
    int escape;
};

static long long now_ms(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) return -1;
    return (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

/* Terminal queries must be answered without injecting ordinary input. */
static int collect(struct terminal_output *out, const char *data, size_t size, int master)
{
    for (size_t i = 0; i < size; ++i) {
        unsigned char c = (unsigned char)data[i];
        if (out->escape == 1) {
            out->escape = c == '[' ? 2 : c == ']' ? 3 : 0;
            out->sequence_used = 0;
        } else if (out->escape == 2) {
            if (out->sequence_used + 1 >= sizeof(out->sequence)) return -1;
            out->sequence[out->sequence_used++] = (char)c;
            out->sequence[out->sequence_used] = 0;
            if (c >= 0x40 && c <= 0x7e) {
                const char *reply = NULL;
                if (!strcmp(out->sequence, "6n")) reply = "\033[1;1R";
                else if (!strcmp(out->sequence, "c") || !strcmp(out->sequence, "0c"))
                    reply = "\033[?1;2c";
                if (master >= 0 && reply && write(master, reply, strlen(reply)) != (ssize_t)strlen(reply))
                    return -1;
                out->escape = 0;
            }
        } else if (out->escape == 3) {
            if (c == 7) out->escape = 0;
            else if (c == 27) out->escape = 4;
        } else if (out->escape == 4) {
            out->escape = c == '\\' ? 0 : 3;
        } else if (c == 27) out->escape = 1;
        else if (c >= 32 || c == '\n' || c == '\t') {
            if (out->used + 1 >= sizeof(out->text)) return -1;
            out->text[out->used++] = (char)c;
            out->text[out->used] = 0;
        }
    }
    return 0;
}

static int onboarding_visible(const char *text)
{
    /* Ratatui cursor motions can replace printed spaces between words. */
    static char compact[OUTPUT_LIMIT];
    size_t length = 0;
    for (const unsigned char *p = (const unsigned char *)text; *p; ++p)
        if (!isspace(*p)) compact[length++] = (char)*p;
    compact[length] = 0;
    return strstr(compact, "WelcometoCodex") && strstr(compact, "SigninwithChatGPT") &&
           (strstr(compact, "UseanOpenAIAPIkey") || strstr(compact, "ProvideyourownAPIkey"));
}

static int output_matches(const char *mode, const char *text, int status, int interacted)
{
    if (!WIFEXITED(status)) return 0;
    if (!strcmp(mode, "version"))
        return WEXITSTATUS(status) == 0 && strstr(text, "codex-cli 0.0.0\n");
    if (!strcmp(mode, "help"))
        return WEXITSTATUS(status) == 0 && strstr(text, "Codex CLI\n") &&
               strstr(text, "Usage: codex") && strstr(text, "login") && strstr(text, "app-server");
    if (!strcmp(mode, "login-status"))
        return WEXITSTATUS(status) == 1 && strstr(text, "Not logged in\n") &&
               !strstr(text, "Error checking login status:") && !strstr(text, "Logged in using");
    return WEXITSTATUS(status) == 0 && interacted && onboarding_visible(text);
}

static int cleanup_home(const char *path)
{
    struct stat st;
    if (lstat(path, &st)) return -1;
    if (!S_ISDIR(st.st_mode)) return unlink(path);
    DIR *directory = opendir(path);
    if (!directory) return -1;
    int result = 0;
    struct dirent *entry;
    errno = 0;
    while ((entry = readdir(directory))) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        char child[4096];
        int length = snprintf(child, sizeof(child), "%s/%s", path, entry->d_name);
        if (length < 0 || (size_t)length >= sizeof(child) || cleanup_home(child)) {
            result = -1;
            break;
        }
        errno = 0;
    }
    if (errno) result = -1;
    if (closedir(directory)) result = -1;
    return result ? -1 : rmdir(path);
}

static void report_private_logs(const char *home)
{
    char path[512], buffer[4096];
    struct stat st;
    DIR *directory = opendir(home);
    if (directory) {
        struct dirent *entry;
        unsigned count = 0;
        while (count < 32 && (entry = readdir(directory))) {
            const char *extension = strstr(entry->d_name, ".sqlite");
            if (!extension || (strcmp(extension, ".sqlite") &&
                strcmp(extension, ".sqlite-wal") && strcmp(extension, ".sqlite-shm"))) continue;
            int length = snprintf(path, sizeof(path), "%s/%s", home, entry->d_name);
            if (length < 0 || (size_t)length >= sizeof(path) || lstat(path, &st) || !S_ISREG(st.st_mode)) continue;
            printf("CODEX-CLI: private database %s bytes=%lld\n", entry->d_name, (long long)st.st_size);
            ++count;
        }
        closedir(directory);
    }
    snprintf(path, sizeof(path), "%s/diagnostic-log/codex-tui.log", home);
    int log = open(path, O_RDONLY | O_NONBLOCK | O_NOFOLLOW);
    if (log < 0) {
        printf("CODEX-CLI: private TUI log unavailable errno=%d\n", errno);
        return;
    }
    size_t remaining = 16384;
    if (!fstat(log, &st) && S_ISREG(st.st_mode) &&
        lseek(log, st.st_size > (off_t)remaining ? st.st_size - (off_t)remaining : 0, SEEK_SET) >= 0) {
        puts("CODEX-CLI: private TUI log tail (at most 16384 bytes)");
        while (remaining) {
            ssize_t size = read(log, buffer, remaining < sizeof(buffer) ? remaining : sizeof(buffer));
            if (size < 0 && errno == EINTR) continue;
            if (size <= 0) break;
            fwrite(buffer, 1, (size_t)size, stdout);
            remaining -= (size_t)size;
        }
        puts("\nCODEX-CLI: end private TUI log tail");
    }
    close(log);
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "", *binary = argc > 2 ? argv[2] : "/usr/bin/codex";
    int tty = !strcmp(mode, "pty-onboarding");
    if (argc > 3 || (!tty && strcmp(mode, "version") && strcmp(mode, "help") && strcmp(mode, "login-status"))) {
        fprintf(stderr, "usage: %s version|help|login-status|pty-onboarding [codex]\n", argv[0]);
        return 2;
    }
    long timeout_ms = 600000;
    const char *timeout = getenv("CODEX_CLI_QUALIFY_TIMEOUT_MS");
    if (timeout) {
        char *end;
        timeout_ms = strtol(timeout, &end, 10);
        if (!*timeout || *end || timeout_ms < 100 || timeout_ms > 1800000) return 2;
    }
    char home[] = "/tmp/codex-cli-qualify-XXXXXX", home_env[256], codex_env[256], temp_env[256];
    char config[256], slave_path[128];
    int home_created = 0, input = -1, output = -1, child_output = -1, master = -1;
    int failed = 1, failure_errno = 0, reaped = 0, eof = 0, status = -1, resized = 0, interrupted = 0;
    pid_t child = -1;
    static struct terminal_output captured;
    long long deadline = now_ms() + timeout_ms, interrupt_at = 0, progress_at = now_ms() + 30000;
    setvbuf(stdout, NULL, _IONBF, 0);
    signal(SIGPIPE, SIG_IGN);
    printf("CODEX-CLI: RUN %s\n", mode);
    if (!mkdtemp(home)) goto done;
    home_created = 1;
    snprintf(config, sizeof(config), "%s/config.toml", home);
    FILE *file = fopen(config, "w");
    if (!file) goto done;
    int written = fprintf(file, "model_provider = \"openai\"\ncheck_for_update_on_startup = false\n"
                          "log_dir = \"%s/diagnostic-log\"\n"
                          "[analytics]\nenabled = false\n[tui]\nanimations = false\n", home);
    if (fclose(file) || written < 0) goto done;
    if (tty) {
#ifdef __pedigree__
        /* Pedigree allocates an unlocked slave and exposes its number directly. */
        master = open("/dev/ptmx", O_RDWR | O_NOCTTY);
        output = master;
        unsigned int number;
        if (master < 0 || ioctl(master, TIOCGPTN, &number)) goto done;
        snprintf(slave_path, sizeof(slave_path), "/dev/pts/%u", number);
#else
        master = posix_openpt(O_RDWR | O_NOCTTY);
        output = master;
        if (master < 0 || grantpt(master) || unlockpt(master)) goto done;
        char *name = ptsname(master);
        if (!name || strlen(name) >= sizeof(slave_path)) goto done;
        strcpy(slave_path, name);
#endif
    } else {
        int descriptors[2];
        if (pipe(descriptors)) goto done;
        output = descriptors[0]; child_output = descriptors[1];
        input = open("/dev/null", O_RDONLY);
        if (input < 0) goto done;
    }
    snprintf(home_env, sizeof(home_env), "HOME=%s", home);
    snprintf(codex_env, sizeof(codex_env), "CODEX_HOME=%s", home);
    snprintf(temp_env, sizeof(temp_env), "TMPDIR=%s", home);
    child = fork();
    if (child < 0) goto done;
    if (!child) {
        char *args[] = {(char *)binary, NULL, NULL, NULL};
        if (!strcmp(mode, "version")) args[1] = "--version";
        else if (!strcmp(mode, "help")) args[1] = "--help";
        else if (!strcmp(mode, "login-status")) { args[1] = "login"; args[2] = "status"; }
        char *environment[] = {home_env, codex_env, temp_env, "PATH=/usr/bin:/bin",
                               "TERM=xterm-256color", "LANG=C.UTF-8",
                               "RUST_LOG=warn,codex_tui=debug,codex_app_server::app_server_tracing=info,"
                               "codex_app_server::message_processor=trace,codex_app_server::outgoing_message=trace,"
                               "codex_app_server::in_process=debug",
                               "OTEL_SDK_DISABLED=true", NULL};
        if (tty) {
            if (setsid() < 0) _exit(125);
            input = open(slave_path, O_RDWR);
            struct winsize size = {.ws_row = 40, .ws_col = 120};
            if (input < 0 || ioctl(input, TIOCSCTTY, 0) || ioctl(input, TIOCSWINSZ, &size)) _exit(125);
            child_output = input;
        } else if (setpgid(0, 0)) _exit(125);
        if (chdir(home) || dup2(input, 0) < 0 || dup2(child_output, 1) < 0 || dup2(child_output, 2) < 0) _exit(125);
        close(output);
        if (input > 2) close(input);
        if (child_output > 2 && child_output != input) close(child_output);
        execve(binary, args, environment);
        perror("CODEX-CLI: execve");
        _exit(126);
    }
    if (input >= 0) { close(input); input = -1; }
    if (child_output >= 0) { close(child_output); child_output = -1; }
    if (fcntl(output, F_SETFL, O_NONBLOCK)) goto done;
    while (!reaped || !eof) {
        if (now_ms() >= deadline) { errno = ETIMEDOUT; goto done; }
        if (!reaped) {
            pid_t waited = waitpid(child, &status, WNOHANG);
            if (waited == child) reaped = 1;
            else if (waited < 0 && errno != EINTR) goto done;
        }
        struct pollfd descriptor = {.fd = output, .events = POLLIN};
        int ready = poll(&descriptor, 1, 100);
        if (ready < 0 && errno != EINTR) goto done;
        if (ready > 0) {
            char buffer[4096];
            ssize_t size = read(output, buffer, sizeof(buffer));
            if (size > 0) {
                if (collect(&captured, buffer, (size_t)size, master)) goto done;
            } else if (!size || (tty && errno == EIO)) eof = 1;
            else if (errno != EINTR && errno != EAGAIN) goto done;
        }
        if (tty && !resized && onboarding_visible(captured.text)) {
            struct winsize size = {.ws_row = 32, .ws_col = 100};
            if (ioctl(master, TIOCSWINSZ, &size)) goto done;
            resized = 1;
            interrupt_at = now_ms() + 1000;
            puts("CODEX-CLI: observed private PTY onboarding; resized 120x40 to 100x32");
        }
        if (resized && !interrupted && now_ms() >= interrupt_at) {
            if (write(master, "\003", 1) != 1) goto done;
            interrupted = 1;
        }
        if (now_ms() >= progress_at) {
            printf("CODEX-CLI: waiting mode=%s bytes=%zu\n", mode, captured.used);
            progress_at = now_ms() + 30000;
        }
    }
    failed = !output_matches(mode, captured.text, status, interrupted);
done:
    failure_errno = errno;
    if (captured.used) printf("CODEX-CLI: captured %s output\n%s\n", mode, captured.text);
    if (child > 0 && !reaped) {
        kill(-child, SIGKILL); kill(child, SIGKILL);
        long long until = now_ms() + 2000;
        while (now_ms() < until) {
            if (waitpid(child, &status, WNOHANG) == child) { reaped = 1; break; }
            poll(NULL, 0, 10);
        }
    }
    if (child > 0) kill(-child, SIGKILL);
    if (output >= 0) close(output);
    if (input >= 0) close(input);
    if (child_output >= 0) close(child_output);
    if (tty && home_created) report_private_logs(home);
    if (home_created && cleanup_home(home)) {
        if (!failed) failure_errno = errno;
        failed = 1;
    }
    if (!reaped) failed = 1;
    if (failed) fprintf(stderr, "CODEX-CLI: FAIL %s status=%d errno=%d\n", mode, status, failure_errno);
    else printf("CODEX-CLI: PASS %s\n", mode);
    return failed;
}
