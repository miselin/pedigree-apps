#ifndef _SYS_UIO_H
#define _SYS_UIO_H

#include <sys/types.h>

struct iovec
{
  void* iov_base;
  size_t iov_len;
};

#ifdef __cplusplus
extern "C" {
#endif

ssize_t readv(int fildes, const struct iovec *iov, int iovcnt);
ssize_t writev(int fildes, const struct iovec *iov, int iovcnt);

#ifdef __cplusplus
}
#endif

#endif
