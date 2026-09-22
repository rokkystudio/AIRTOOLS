#include "LzmaDec.h"

typedef unsigned char u8;
typedef unsigned int u32;

#ifndef PAYLOAD_OFFSET
#define PAYLOAD_OFFSET 0x00340000
#endif

#ifndef PAYLOAD_SIZE
#define PAYLOAD_SIZE 441060
#endif

#ifndef UNPACKED_SIZE
#define UNPACKED_SIZE 2146132
#endif

extern int sys_open(const char *path, int flags, int mode);
extern int sys_read(int fd, void *buffer, unsigned int count);
extern int sys_write(int fd, const void *buffer, unsigned int count);
extern int sys_lseek(int fd, int offset, int whence);
extern int sys_close(int fd);
extern void sys_exit(int status);

#define O_RDONLY 0
#define O_WRONLY 1
#define O_CREAT 0x0100
#define O_TRUNC 0x0200
#define SEEK_SET 0

static u8 input_data[PAYLOAD_SIZE];
static u8 output_data[UNPACKED_SIZE];
static u8 alloc_pool[2 * 1024 * 1024];
static unsigned int alloc_offset;

void *memcpy(void *dest, const void *src, size_t n)
{
    u8 *d = (u8 *)dest;
    const u8 *s = (const u8 *)src;
    while (n--)
        *d++ = *s++;
    return dest;
}

void *memset(void *dest, int value, size_t n)
{
    u8 *d = (u8 *)dest;
    while (n--)
        *d++ = (u8)value;
    return dest;
}

static void write_text(const char *text)
{
    unsigned int length = 0;
    while (text[length] != 0)
        length++;
    sys_write(1, text, length);
}

static void write_hex32(u32 value)
{
    static const char hex[] = "0123456789abcdef";
    char output[8];
    int index;
    for (index = 7; index >= 0; index--) {
        output[index] = hex[value & 0x0f];
        value >>= 4;
    }
    sys_write(1, output, sizeof(output));
}

static int read_exact(int fd, u8 *buffer, unsigned int length)
{
    unsigned int done = 0;
    while (done < length) {
        int ret = sys_read(fd, buffer + done, length - done);
        if (ret <= 0)
            return -1;
        done += (unsigned int)ret;
    }
    return 0;
}

static int write_all(int fd, const u8 *buffer, unsigned int length)
{
    unsigned int done = 0;
    while (done < length) {
        int ret = sys_write(fd, buffer + done, length - done);
        if (ret <= 0)
            return -1;
        done += (unsigned int)ret;
    }
    return 0;
}

static void *lzma_alloc(void *p, size_t size)
{
    unsigned int aligned;
    (void)p;
    aligned = (alloc_offset + 15U) & ~15U;
    if (aligned + (unsigned int)size > sizeof(alloc_pool))
        return 0;
    alloc_offset = aligned + (unsigned int)size;
    return alloc_pool + aligned;
}

static void lzma_free(void *p, void *address)
{
    (void)p;
    (void)address;
}

static unsigned int le32(const u8 *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8) | ((unsigned int)p[2] << 16) | ((unsigned int)p[3] << 24);
}

static unsigned int le64_low(const u8 *p)
{
    return le32(p);
}

static int extract_driver(void)
{
    static ISzAlloc allocator = { lzma_alloc, lzma_free };
    SizeT src_len;
    SizeT dst_len;
    ELzmaStatus status;
    int in_fd;
    int out_fd;
    int ret;

    write_text("PAYLOAD_OFFSET=0x");
    write_hex32(PAYLOAD_OFFSET);
    write_text("\nPAYLOAD_SIZE=0x");
    write_hex32(PAYLOAD_SIZE);
    write_text("\nUNPACKED_SIZE=0x");
    write_hex32(UNPACKED_SIZE);
    write_text("\n");

    in_fd = sys_open("/dev/mtd4ro", O_RDONLY, 0);
    if (in_fd < 0) {
        write_text("OPEN_MTD4RO_ERROR=0x");
        write_hex32((u32)(-in_fd));
        write_text("\n");
        return 10;
    }

    if (sys_lseek(in_fd, PAYLOAD_OFFSET, SEEK_SET) < 0) {
        write_text("LSEEK_ERROR\n");
        sys_close(in_fd);
        return 11;
    }

    if (read_exact(in_fd, input_data, PAYLOAD_SIZE) != 0) {
        write_text("READ_PAYLOAD_ERROR\n");
        sys_close(in_fd);
        return 12;
    }
    sys_close(in_fd);

    if (input_data[0] == 0xff && input_data[1] == 0xff) {
        write_text("PAYLOAD_EMPTY\n");
        return 13;
    }

    if (le64_low(input_data + 5) != UNPACKED_SIZE) {
        write_text("UNPACKED_SIZE_FIELD_MISMATCH=0x");
        write_hex32(le64_low(input_data + 5));
        write_text("\n");
        return 14;
    }

    alloc_offset = 0;
    src_len = PAYLOAD_SIZE - 13;
    dst_len = UNPACKED_SIZE;
    ret = LzmaDecode(output_data, &dst_len, input_data + 13, &src_len, input_data, 5, LZMA_FINISH_END, &status, &allocator);
    if (ret != SZ_OK || dst_len != UNPACKED_SIZE) {
        write_text("LZMA_DECODE_ERROR=0x");
        write_hex32((u32)ret);
        write_text(" DST=0x");
        write_hex32((u32)dst_len);
        write_text(" SRC=0x");
        write_hex32((u32)src_len);
        write_text(" STATUS=0x");
        write_hex32((u32)status);
        write_text("\n");
        return 15;
    }

    out_fd = sys_open("/tmp/8188eu.ko", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (out_fd < 0) {
        write_text("OPEN_OUTPUT_ERROR=0x");
        write_hex32((u32)(-out_fd));
        write_text("\n");
        return 16;
    }

    if (write_all(out_fd, output_data, UNPACKED_SIZE) != 0) {
        write_text("WRITE_OUTPUT_ERROR\n");
        sys_close(out_fd);
        return 17;
    }
    sys_close(out_fd);

    write_text("EXTRACT_OK\n");
    return 0;
}

void _start(void)
{
    int status = extract_driver();
    sys_exit(status);
    for (;;)
        ;
}
