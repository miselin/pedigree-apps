#ifndef _SYS_MMAN_H
#define _SYS_MMAN_H

_BEGIN_STD_C

#define PROT_READ 0
#define PROT_WRITE 1
#define PROT_EXEC 2
#define PROT_NONE 4

#define MAP_SHARED 1
#define MAP_PRIVATE 2
#define MAP_FIXED 4
#define MAP_ANON 8

#define MS_ASYNC 1
#define MS_SYNC  2
#define MS_INVALIDATE 4

#define MAP_FAILED ((void*) 0)

#include <sys/types.h>

void  *mmap(void *, size_t, int, int, int, off_t);
int    msync(void *addr, size_t len, int flags);
int    munmap(void *, size_t);

_END_STD_C

#endif
