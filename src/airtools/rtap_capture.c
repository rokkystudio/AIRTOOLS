typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern int sys_write(int fd, const void *buffer, unsigned int count);
extern int sys_ioctl(int fd, unsigned int request, void *argument);
extern int sys_socket(int domain, int type, int protocol);
extern int sys_bind(int fd, const void *address, unsigned int length);
extern int sys_recv(int fd, void *buffer, unsigned int length, unsigned int flags);
extern int sys_close(int fd);
extern void sys_exit(int status);

#define AF_PACKET 17
#define SOCK_RAW 3
#define ETH_P_ALL_NETWORK_ORDER 0x0300
#define SIOCGIFINDEX 0x8933

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

static void write_hex_bytes(const u8 *data, unsigned int length)
{
    static const char hex[] = "0123456789abcdef";
    char line[16 * 3 + 1];
    unsigned int offset = 0;

    while (offset < length) {
        unsigned int count = length - offset;
        unsigned int index;
        unsigned int output = 0;

        if (count > 16)
            count = 16;

        for (index = 0; index < count; index++) {
            u8 value = data[offset + index];

            line[output++] = hex[value >> 4];
            line[output++] = hex[value & 0x0f];
            line[output++] = ' ';
        }

        line[output++] = '\n';
        sys_write(1, line, output);
        offset += count;
    }
}

static void zero_bytes(u8 *data, unsigned int length)
{
    unsigned int index;

    for (index = 0; index < length; index++)
        data[index] = 0;
}

static int get_interface_index(int fd)
{
    u8 request[40];
    int index;

    zero_bytes(request, sizeof(request));
    request[0] = 'w';
    request[1] = 'l';
    request[2] = 'a';
    request[3] = 'n';
    request[4] = '0';

    if (sys_ioctl(fd, SIOCGIFINDEX, request) < 0)
        return -1;

    index = *(int *)(request + 16);
    return index;
}

static int bind_interface(int fd, int interface_index)
{
    u8 address[20];

    zero_bytes(address, sizeof(address));

    address[0] = AF_PACKET;
    address[1] = 0;
    address[2] = 0;
    address[3] = 3;
    *(int *)(address + 4) = interface_index;

    return sys_bind(fd, address, sizeof(address));
}

static int capture_frame(void)
{
    static u8 frame[4096];
    int fd;
    int interface_index;
    int length;
    unsigned int dump_length;

    fd = sys_socket(AF_PACKET, SOCK_RAW, ETH_P_ALL_NETWORK_ORDER);
    if (fd < 0) {
        write_text("SOCKET_ERROR=0x");
        write_hex32((u32)(-fd));
        write_text("\n");
        return 10;
    }

    interface_index = get_interface_index(fd);
    if (interface_index < 0) {
        write_text("IFINDEX_ERROR\n");
        sys_close(fd);
        return 11;
    }

    write_text("IFINDEX=0x");
    write_hex32((u32)interface_index);
    write_text("\n");

    if (bind_interface(fd, interface_index) < 0) {
        write_text("BIND_ERROR\n");
        sys_close(fd);
        return 12;
    }

    write_text("WAITING_FOR_FRAME\n");
    length = sys_recv(fd, frame, sizeof(frame), 0);
    if (length < 0) {
        write_text("RECV_ERROR=0x");
        write_hex32((u32)(-length));
        write_text("\n");
        sys_close(fd);
        return 13;
    }

    write_text("FRAME_LEN=0x");
    write_hex32((u32)length);
    write_text("\n");

    if (length >= 4) {
        u16 radiotap_length = (u16)frame[2] | ((u16)frame[3] << 8);

        write_text("RADIOTAP_VERSION=0x");
        write_hex32((u32)frame[0]);
        write_text("\nRADIOTAP_LEN=0x");
        write_hex32((u32)radiotap_length);
        write_text("\n");
    }

    dump_length = (unsigned int)length;
    if (dump_length > 128)
        dump_length = 128;

    write_text("FRAME_HEAD_HEX:\n");
    write_hex_bytes(frame, dump_length);
    write_text("CAPTURE_OK\n");

    sys_close(fd);
    return 0;
}

void _start(void)
{
    int status = capture_frame();

    sys_exit(status);

    for (;;)
        ;
}
