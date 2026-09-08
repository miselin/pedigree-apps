/* Bounded JSON token parser shared in shape with the App Server qualifier. */
#ifndef CODE_MODE_QUALIFY_JSON_H
#define CODE_MODE_QUALIFY_JSON_H
#include <ctype.h>
#include <string.h>
enum { FRAME_SIZE = 65536, TOKEN_COUNT = 4096 };
struct token { char kind; int start, end, next; };
static struct token tokens[TOKEN_COUNT];
/* Padding makes truncated escapes safe to inspect before rejecting them. */
static char frame[FRAME_SIZE + 32];
static int position, token_count;

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

static int parse_frame(size_t length)
{
    position = token_count = 0;
    memset(frame + length, 0, 32);
    if (memchr(frame, 0, length) || value(0) != 0) return -1;
    space();
    return position == (int)length && tokens[0].kind == '{' ? 0 : -1;
}

static int copy_string(int index, char *output, size_t capacity)
{
    if (index < 0 || tokens[index].kind != '"' || !capacity) return -1;
    int offset = tokens[index].start + 1;
    size_t used = 0;
    while (offset < tokens[index].end - 1) {
        int c = string_char(&offset);
        if (c <= 0 || c > 127 || used + 1 == capacity) return -1;
        output[used++] = (char)c;
    }
    output[used] = 0;
    return 0;
}
#endif
