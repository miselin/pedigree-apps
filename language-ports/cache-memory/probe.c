#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/sysinfo.h>
#include <unistd.h>

static int free_memory(uint64_t *result)
{
    struct sysinfo info;
    memset(&info, 0, sizeof(info));
    if (syscall(SYS_sysinfo, &info) != 0) {
        printf("CACHE-SPIKE: FAIL sysinfo errno=%d\n", errno);
        return -1;
    }
    *result = (uint64_t) info.freeram * info.mem_unit;
    return 0;
}

static int read_one(const char *directory, unsigned index)
{
    char path[512];
    int length = snprintf(path, sizeof(path), "%s/%04u.dat", directory, index);
    if (length < 0 || (size_t) length >= sizeof(path)) {
        printf("CACHE-SPIKE: FAIL path too long\n");
        return -1;
    }
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        printf("CACHE-SPIKE: FAIL open index=%u errno=%d\n", index, errno);
        return -1;
    }
    unsigned char byte = 0;
    ssize_t count;
    do {
        count = read(fd, &byte, 1);
    } while (count < 0 && errno == EINTR);
    int read_error = errno;
    int closed = close(fd);
    if (count != 1 || byte != index % 255 + 1 || closed != 0) {
        printf("CACHE-SPIKE: FAIL read index=%u count=%ld byte=%u errno=%d close=%d\n",
               index, (long) count, byte, read_error, closed);
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *directory = argc > 1 ? argv[1] : "/usr/share/memory-spike/inputs";
    unsigned files = argc > 2 ? (unsigned) strtoul(argv[2], NULL, 10) : 256;
    unsigned max_loss_mib = argc > 3 ? (unsigned) strtoul(argv[3], NULL, 10) : 64;
    if (!files || files > 256 || !max_loss_mib || max_loss_mib > 4096) {
        fprintf(stderr, "usage: cache-spike [input-directory [1..256-files [max-loss-MiB]]]\n");
        return 2;
    }
    setvbuf(stdout, NULL, _IONBF, 0);
    uint64_t before, after_first = 0, after_repeat = 0;
    if (free_memory(&before))
        return 1;
    printf("CACHE-SPIKE: BEGIN files=%u file_bytes=4096 read_bytes=1 free_kib=%" PRIu64 "\n",
           files, before / 1024);
    for (unsigned pass = 0; pass < 2; ++pass) {
        for (unsigned i = 0; i < files; ++i) {
            if (read_one(directory, i))
                return 1;
            if ((i + 1) % 16 == 0 || i + 1 == files) {
                uint64_t current;
                if (free_memory(&current))
                    return 1;
                printf("CACHE-SPIKE: pass=%u files=%u free_kib=%" PRIu64
                       " loss_kib=%" PRId64 "\n", pass + 1, i + 1, current / 1024,
                       ((int64_t) before - (int64_t) current) / 1024);
            }
        }
        if (free_memory(pass == 0 ? &after_first : &after_repeat))
            return 1;
    }
    int64_t first_loss = (int64_t) before - (int64_t) after_first;
    int64_t repeat_loss = (int64_t) after_first - (int64_t) after_repeat;
    int64_t total_loss = (int64_t) before - (int64_t) after_repeat;
    printf("CACHE-SPIKE: delta first_kib=%" PRId64 " repeat_kib=%" PRId64
           " total_kib=%" PRId64 "\n", first_loss / 1024, repeat_loss / 1024,
           total_loss / 1024);
    if (total_loss > (int64_t) max_loss_mib * 1024 * 1024) {
        printf("CACHE-SPIKE: FAIL memory budget=%uMiB\n", max_loss_mib);
        return 1;
    }
    printf("CACHE-SPIKE: PASS files=%u passes=2 budget_mib=%u\n", files, max_loss_mib);
    return 0;
}
