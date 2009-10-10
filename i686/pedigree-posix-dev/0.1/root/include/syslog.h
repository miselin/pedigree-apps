#ifndef _SYSLOG_H
#define _SYSLOG_H

#define LOG_PID     1

// Not relevant on Pedigree until the log is an actual file
#define LOG_CONS    2
#define LOG_NDELAY  4
#define LOG_ODELAY  8
#define LOG_NOWAIT  16

// Log facilities (not relevant on Pedigree yet)
#define LOG_KERN    0
#define LOG_USER    1
#define LOG_MAIL    2
#define LOG_NEWS    3
#define LOG_UUCP    4
#define LOG_DAEMON  5
#define LOG_AUTH    6
#define LOG_LPR     7
#define LOG_LOCAL0  8
#define LOG_LOCAL1  9
#define LOG_LOCAL2  10
#define LOG_LOCAL3  11
#define LOG_LOCAL4  12
#define LOG_LOCAL5  13
#define LOG_LOCAL6  14
#define LOG_LOCAL7  15

// Log masks
#define LOG_MASK(pri) (1<<pri)

// Log priority (highest level is ERROR, userspace applications cannot halt the
// system).
#define LOG_EMERG   0
#define LOG_ALERT   1
#define LOG_CRIT    2
#define LOG_ERR     3
#define LOG_WARNING 4
#define LOG_NOTICE  5
#define LOG_INFO    6
#define LOG_DEBUG   7

#include <unistd.h>

_BEGIN_STD_C

void _EXFUN(closelog, (void));
void _EXFUN(openlog, (const char*, int, int));
int  _EXFUN(setlogmask, (int));
void _EXFUN(syslog, (int, const char*, ...));

_END_STD_C

#endif
