#ifndef SYS_TERMIOS_H
#define SYS_TERMIOS_H

#ifdef __cplusplus
extern "C"
{
#endif

typedef unsigned int cc_t;
typedef unsigned int speed_t;
typedef unsigned int tcflag_t;


#define NCCS 13 // The number of control characters.
#define VEOF   4       /* also VMIN -- thanks, AT&T */
#define VEOL   5       /* also VTIME -- thanks again */
#define VERASE 2
#define VINTR  0
#define VKILL  3
#define VMIN   4       /* also VEOF */
#define VQUIT  1
#define VSUSP  10
#define VTIME  5       /* also VEOL */
#define VSTART 11
#define VSTOP  12

# define TCSAFLUSH	0
# define TCSANOW	1
# define TCSADRAIN	2
# define TCSADFLUSH	3

# define IGNBRK	000001
# define BRKINT	000002
# define IGNPAR	000004
# define INPCK	000020
# define ISTRIP	000040
# define INLCR	000100
# define IGNCR	000200
# define ICRNL	000400
# define IXON	002000
# define IXANY  004000
# define IXOFF	010000
# define PARMRK 020000

# define OPOST	000001
# define OCRNL	000004
# define ONLCR	000010
# define ONOCR	000020
# define ONLRET 000040
# define TAB3	014000

# define CLOCAL	004000
# define CREAD	000200
# define CSIZE	000060
# define CS5	0
# define CS6	020
# define CS7	040
# define CS8	060
# define CSTOPB	000100
# define HUPCL	002000
# define PARENB	000400
# define PAODD	001000
# define PARODD 001000

// Defines for the c_lflag attribute of termios.
#define ECHO   0000010
#define ECHOE  0000020
#define ECHOK  0000040
#define ECHONL 0000100
#define ICANON 0000002
#define IEXTEN 0000400 /* anybody know *what* this does?! */
#define ISIG   0000001
#define NOFLSH 0000200
#define TOSTOP 0001000

/* tcflow() and TCXONC use these */
#define TCOOFF    0
#define TCOON   1
#define TCIOFF    2
#define TCION   3

/* tcflush() and TCFLSH use these */
#define TCIFLUSH  0
#define TCOFLUSH  1
#define TCIOFLUSH 2

#define  B0	0000000		/* hang up */
#define  B50	0000001
#define  B75	0000002
#define  B110	0000003
#define  B134	0000004
#define  B150	0000005
#define  B200	0000006
#define  B300	0000007
#define  B600	0000010
#define  B1200	0000011
#define  B1800	0000012
#define  B2400	0000013
#define  B4800	0000014
#define  B9600	0000015
#define  B19200	0000016
#define  B38400	0000017

typedef struct termios
{
  tcflag_t c_iflag;		///< Has useless properties - ignored.
  tcflag_t c_oflag;		///< Has useless properties - ignored.
  tcflag_t c_cflag;		///< Has useless properties - ignored.
  tcflag_t c_lflag;		///< ECHO,ECHOE,ECHONL recognised.
  cc_t     c_cc[NCCS];
} termios_t;

typedef struct winsize
{
  unsigned short ws_row;
  unsigned short ws_col;
} winsize_t;

int tcgetattr(int, struct termios *);
int tcsetattr(int, int, struct termios *);
int tcflow(int fd, int action);
int tcflush(int fd, int queue_selector);
int tcdrain(int fd);

#ifdef __cplusplus
}
#endif

#endif // SYS_TERMIOS_H
