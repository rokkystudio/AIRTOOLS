typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern int sys_write(int fd, const void *buffer, unsigned int count);
extern int sys_close(int fd);
extern int sys_gettimeofday(void *timeval, void *timezone);
extern int sys_ioctl(int fd, unsigned int request, void *argument);
extern int sys_bind(int fd, const void *address, unsigned int length);
extern int sys_recv(int fd, void *buffer, unsigned int length, unsigned int flags);
extern int sys_socket(int domain, int type, int protocol);
extern void sys_exit(int status);

#define AF_PACKET 17
#define SOCK_RAW 3
#define ETH_P_ALL_NETWORK_ORDER 0x0300
#define SIOCGIFINDEX 0x8933
#define CAPTURE_FRAME_COUNT 64
#define CAPTURE_BUFFER_SIZE 4096
#define PCAP_LINKTYPE_IEEE802_11_RADIOTAP 127

struct timeval32
{
    u32 seconds;
    u32 microseconds;
};

struct pcap_global_header
{
    u32 magic;
    u16 version_major;
    u16 version_minor;
    u32 thiszone;
    u32 sigfigs;
    u32 snaplen;
    u32 network;
};

struct pcap_packet_header
{
    u32 timestamp_seconds;
    u32 timestamp_microseconds;
    u32 captured_length;
    u32 original_length;
};

static u8 frame[CAPTURE_BUFFER_SIZE];

static void zero_bytes(u8 *data, unsigned int length)
{
    unsigned int index;

    for (index = 0; index < length; index++)
        data[index] = 0;
}

static int write_all(int fd, const void *buffer, unsigned int length)
{
    const u8 *cursor = (const u8 *)buffer;
    unsigned int remaining = length;

    while (remaining != 0) {
        int written = sys_write(fd, cursor, remaining);

        if (written <= 0)
            return -1;

        cursor += written;
        remaining -= (unsigned int)written;
    }

    return 0;
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

static void read_timestamp(struct pcap_packet_header *packet_header)
{
    struct timeval32 timeval;

    timeval.seconds = 0;
    timeval.microseconds = 0;

    if (sys_gettimeofday(&timeval, 0) == 0) {
        packet_header->timestamp_seconds = timeval.seconds;
        packet_header->timestamp_microseconds = timeval.microseconds;
    } else {
        packet_header->timestamp_seconds = 0;
        packet_header->timestamp_microseconds = 0;
    }
}

static int capture_pcap(void)
{
    struct pcap_global_header global_header;
    int fd;
    int interface_index;
    unsigned int frame_index;

    fd = sys_socket(AF_PACKET, SOCK_RAW, ETH_P_ALL_NETWORK_ORDER);
    if (fd < 0)
        return 10;

    interface_index = get_interface_index(fd);
    if (interface_index < 0) {
        sys_close(fd);
        return 11;
    }

    if (bind_interface(fd, interface_index) < 0) {
        sys_close(fd);
        return 12;
    }

    global_header.magic = 0xa1b2c3d4;
    global_header.version_major = 2;
    global_header.version_minor = 4;
    global_header.thiszone = 0;
    global_header.sigfigs = 0;
    global_header.snaplen = CAPTURE_BUFFER_SIZE;
    global_header.network = PCAP_LINKTYPE_IEEE802_11_RADIOTAP;

    if (write_all(1, &global_header, sizeof(global_header)) < 0) {
        sys_close(fd);
        return 13;
    }

    for (frame_index = 0; frame_index < CAPTURE_FRAME_COUNT; frame_index++) {
        struct pcap_packet_header packet_header;
        int length = sys_recv(fd, frame, sizeof(frame), 0);

        if (length <= 0) {
            sys_close(fd);
            return 14;
        }

        read_timestamp(&packet_header);
        packet_header.captured_length = (u32)length;
        packet_header.original_length = (u32)length;

        if (write_all(1, &packet_header, sizeof(packet_header)) < 0) {
            sys_close(fd);
            return 15;
        }

        if (write_all(1, frame, (unsigned int)length) < 0) {
            sys_close(fd);
            return 16;
        }
    }

    sys_close(fd);
    return 0;
}

void _start(void)
{
    int status = capture_pcap();

    sys_exit(status);

    for (;;)
        ;
}
