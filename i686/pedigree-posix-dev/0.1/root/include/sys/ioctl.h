#ifndef _SYS_IOCTL_H
#define _SYS_IOCTL_H

#include <sys/termios.h>

_BEGIN_STD_C

/* If you change this, please change file-syscalls.cc. */

#define __IOCTL_FIRST 0x1000

#define TIOCGWINSZ  0x1000  /* Get console window size. */
#define TIOCSWINSZ  0x1001  /* Set console window size. */
#define TIOCPKT     0x1002

#define FIONREAD    0x2000  /* Number of bytes available to read */
#define FIONBIO     0x2001  /* Non-blocking? */

#define SIOCATMARK  0x3000  /* Socket at the OOB mark? */

/* http://www.opengroup.org/onlinepubs/009695399/functions/ioctl.html */
#define I_PUSH      0x4000
#define I_POP       0x4001
#define I_LOOK      0x4002
#define I_FLUSH     0x4003
#define I_FLUSHBAND 0x4004
#define I_SETSIG    0x4005
#define I_GETSIG    0x4006
#define I_FIND      0x4007
#define I_PEEK      0x4008
#define I_SRDOPT    0x4009
#define I_GRDOPT    0x400A
#define I_NREAD     0x400B
#define I_FDINSERT  0x400C
#define I_STR       0x400D
#define I_SWROPT    0x400E
#define I_GWROPT    0x400F
#define I_SENDFD    0x4010
#define I_RECVFD    0x4011
#define I_LIST      0x4012
#define I_ATMARK    0x4013
#define I_CKBAND    0x4014
#define I_GETBAND   0x4015
#define I_CANPUT    0x4016
#define I_SETCLTIME 0x4017
#define I_GETCLTIME 0x4018

#define I_LINK      0x4019
#define I_UNLINK    0x401A
#define I_PLINK     0x401B
#define I_PUNLINK   0x401C

#define __IOCTL_LAST  0x401C

int _EXFUN(ioctl, (int fildes, int request, void *buff));

_END_STD_C

#endif
