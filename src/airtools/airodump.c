typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern int sys_write(int fd, const void *buffer, unsigned int count);
extern int sys_ioctl(int fd, unsigned int request, void *argument);
extern int sys_socket(int domain, int type, int protocol);
extern int sys_bind(int fd, const void *address, unsigned int length);
extern int sys_recv(int fd, void *buffer, unsigned int length, unsigned int flags);
extern int sys_close(int fd);
extern int sys_open(const char *path, unsigned int flags, unsigned int mode);
extern int sys_read(int fd, void *buffer, unsigned int count);
extern int sys_mkdir(const char *path, unsigned int mode);
extern int sys_unlink(const char *path);
extern void sys_exit(int status);

#define AF_PACKET 17
#define SOCK_RAW 3
#define ETH_P_ALL_NETWORK_ORDER 0x0300
#define SIOCGIFINDEX 0x8933

#define O_WRONLY 0x0001
#define O_CREAT  0x0100
#define O_TRUNC  0x0200

#define MAX_APS 24
#define MAX_SSID 32
#define MAX_HANDSHAKES 16
#define HS_FRAMES 6
#define HS_CAPTURE_BYTES 768
#define HS_STORE_DIR "/tmp/airhs"
#define HS_INDEX_PATH "/tmp/airhs/index.txt"
#define NETWORK_INDEX_PATH "/tmp/airscan-networks.txt"

struct stored_frame {
    u16 length;
    u8 data[HS_CAPTURE_BYTES];
};

struct ap_info {
    u8 used;
    u8 bssid[6];
    u8 channel;
    u8 ssid_len;
    u8 has_signal;
    int signal_dbm;
    char ssid[MAX_SSID + 1];
    u32 beacons;
    u32 probes;
    u32 data;
    u8 has_eapol;
    u8 has_mic;
    u8 has_ack;
    u8 hs_saved;
    u8 hs_frame_count;
    u8 hs_file[32];
    u32 hs_tick;
    struct stored_frame hs_frames[HS_FRAMES];
};

static struct ap_info aps[MAX_APS];
static u32 total_frames;
static u32 mgmt_frames;
static u32 ctrl_frames;
static u32 data_frames;
static u32 short_frames;
static u32 handshake_count;
static u32 storage_tick;
static u8 filter_has_bssid;
static u8 filter_bssid[6];
static u8 filter_has_channel;
static u8 filter_channel;
static char cmdline_buffer[256];
static char *cmdline_argv[10];
static const u8 broadcast_mac[6] = { 0xff, 0xff, 0xff, 0xff, 0xff, 0xff };

static void write_text(const char *text)
{
    unsigned int length = 0;
    while (text[length] != 0)
        length++;
    sys_write(1, text, length);
}

static void write_dec(u32 value)
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

static void write_hex_byte(u8 value)
{
    static const char hex[] = "0123456789abcdef";
    char out[2];
    out[0] = hex[value >> 4];
    out[1] = hex[value & 0x0f];
    sys_write(1, out, 2);
}

static void write_mac(const u8 *mac)
{
    unsigned int index;
    for (index = 0; index < 6; index++) {
        if (index)
            write_text(":");
        write_hex_byte(mac[index]);
    }
}

static void zero_bytes(u8 *data, unsigned int length)
{
    unsigned int index;
    for (index = 0; index < length; index++)
        data[index] = 0;
}

static void copy_bytes(u8 *destination, const u8 *source, unsigned int length)
{
    unsigned int index;
    for (index = 0; index < length; index++)
        destination[index] = source[index];
}

static void copy_mac(u8 *destination, const u8 *source)
{
    copy_bytes(destination, source, 6);
}

static void copy_stored_frame(struct stored_frame *destination, const struct stored_frame *source)
{
    destination->length = source->length;
    copy_bytes(destination->data, source->data, source->length);
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

static int is_broadcast(const u8 *mac)
{
    return mac_equal(mac, broadcast_mac);
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
        if (text[index] < '0' || text[index] > '9')
            return -1;
        if (result > 1000000U)
            return -1;
        result = result * 10U + (unsigned int)(text[index] - '0');
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

static int parse_mac_text(const char *text, u8 mac[6])
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

static int filter_accept_bssid(const u8 *bssid)
{
    if (filter_has_bssid && !mac_equal(bssid, filter_bssid))
        return 0;
    return 1;
}

static int filter_accept_ap(const struct ap_info *ap)
{
    if (filter_has_bssid && !mac_equal(ap->bssid, filter_bssid))
        return 0;
    if (filter_has_channel && ap->channel != 0 && ap->channel != filter_channel)
        return 0;
    return 1;
}

static int load_cmdline_args(char ***argv_out)
{
    int fd;
    int length;
    int argc = 0;
    int index;

    fd = sys_open("/proc/self/cmdline", 0, 0);
    if (fd < 0) {
        *argv_out = cmdline_argv;
        cmdline_argv[0] = (char *)"airodump";
        return 1;
    }
    length = sys_read(fd, cmdline_buffer, sizeof(cmdline_buffer) - 1);
    sys_close(fd);
    if (length <= 0) {
        *argv_out = cmdline_argv;
        cmdline_argv[0] = (char *)"airodump";
        return 1;
    }
    cmdline_buffer[length] = 0;
    if (cmdline_buffer[length - 1] != 0 && length + 1 < (int)sizeof(cmdline_buffer))
        cmdline_buffer[length++] = 0;
    cmdline_argv[argc++] = cmdline_buffer;
    for (index = 0; index < length - 1 && argc < 10; index++) {
        if (cmdline_buffer[index] == 0 && cmdline_buffer[index + 1] != 0)
            cmdline_argv[argc++] = cmdline_buffer + index + 1;
    }
    *argv_out = cmdline_argv;
    return argc;
}

static void append_char(char *buffer, unsigned int *offset, unsigned int max, char value)
{
    if (*offset + 1 < max)
        buffer[(*offset)++] = value;
}

static void append_text(char *buffer, unsigned int *offset, unsigned int max, const char *text)
{
    unsigned int index = 0;
    while (text[index] != 0)
        append_char(buffer, offset, max, text[index++]);
}

static void append_dec(char *buffer, unsigned int *offset, unsigned int max, u32 value)
{
    char output[10];
    unsigned int index = 0;
    if (value == 0) {
        append_char(buffer, offset, max, '0');
        return;
    }
    while (value > 0 && index < sizeof(output)) {
        output[index++] = (char)('0' + (value % 10));
        value /= 10;
    }
    while (index > 0) {
        index--;
        append_char(buffer, offset, max, output[index]);
    }
}

static void append_signed_dec(char *buffer, unsigned int *offset, unsigned int max, int value)
{
    if (value < 0) {
        append_char(buffer, offset, max, '-');
        append_dec(buffer, offset, max, (u32)(-value));
    } else {
        append_dec(buffer, offset, max, (u32)value);
    }
}

static void append_mac_plain(char *buffer, unsigned int *offset, unsigned int max, const u8 *mac)
{
    static const char hex[] = "0123456789abcdef";
    unsigned int index;
    for (index = 0; index < 6; index++) {
        append_char(buffer, offset, max, hex[mac[index] >> 4]);
        append_char(buffer, offset, max, hex[mac[index] & 0x0f]);
    }
}

static void append_mac_colon(char *buffer, unsigned int *offset, unsigned int max, const u8 *mac)
{
    static const char hex[] = "0123456789abcdef";
    unsigned int index;
    for (index = 0; index < 6; index++) {
        if (index)
            append_char(buffer, offset, max, ':');
        append_char(buffer, offset, max, hex[mac[index] >> 4]);
        append_char(buffer, offset, max, hex[mac[index] & 0x0f]);
    }
}

static void build_hs_file_path(struct ap_info *ap, char *path, unsigned int max)
{
    unsigned int offset = 0;
    append_text(path, &offset, max, HS_STORE_DIR "/");
    append_mac_plain(path, &offset, max, ap->bssid);
    append_text(path, &offset, max, ".pcap");
    path[offset] = 0;
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

static struct ap_info *find_ap(const u8 *bssid)
{
    unsigned int index;
    struct ap_info *free_slot = 0;
    for (index = 0; index < MAX_APS; index++) {
        if (aps[index].used) {
            if (mac_equal(aps[index].bssid, bssid))
                return &aps[index];
        } else if (!free_slot) {
            free_slot = &aps[index];
        }
    }
    if (!free_slot)
        return 0;
    zero_bytes((u8 *)free_slot, sizeof(*free_slot));
    free_slot->used = 1;
    copy_mac(free_slot->bssid, bssid);
    return free_slot;
}

static void set_ssid(struct ap_info *ap, const u8 *ssid, unsigned int length)
{
    unsigned int index;
    if (!ap || length == 0)
        return;
    if (length > MAX_SSID)
        length = MAX_SSID;
    ap->ssid_len = (u8)length;
    for (index = 0; index < length; index++) {
        u8 c = ssid[index];
        if (c < 32 || c > 126)
            c = '.';
        ap->ssid[index] = (char)c;
    }
    ap->ssid[length] = 0;
}

static void parse_tags(struct ap_info *ap, const u8 *tags, unsigned int length)
{
    unsigned int offset = 0;
    while (offset + 2 <= length) {
        u8 id = tags[offset];
        u8 tag_length = tags[offset + 1];
        const u8 *value = tags + offset + 2;
        offset += 2;
        if (offset + tag_length > length)
            return;
        if (id == 0)
            set_ssid(ap, value, tag_length);
        else if (id == 3 && tag_length >= 1 && ap)
            ap->channel = value[0];
        offset += tag_length;
    }
}

static void evict_oldest_if_needed(struct ap_info *current)
{
    struct ap_info *oldest = 0;
    unsigned int index;
    char path[64];

    if (current->hs_saved || handshake_count < MAX_HANDSHAKES)
        return;

    for (index = 0; index < MAX_APS; index++) {
        struct ap_info *ap = &aps[index];
        if (!ap->used || !ap->hs_saved || ap == current)
            continue;
        if (!oldest || ap->hs_tick < oldest->hs_tick)
            oldest = ap;
    }

    if (!oldest)
        return;

    build_hs_file_path(oldest, path, sizeof(path));
    sys_unlink(path);
    oldest->hs_saved = 0;
    if (handshake_count)
        handshake_count--;
}

static void write_u16_le(int fd, u16 value)
{
    u8 data[2];
    data[0] = (u8)(value & 0xff);
    data[1] = (u8)(value >> 8);
    sys_write(fd, data, 2);
}

static void write_u32_le(int fd, u32 value)
{
    u8 data[4];
    data[0] = (u8)(value & 0xff);
    data[1] = (u8)((value >> 8) & 0xff);
    data[2] = (u8)((value >> 16) & 0xff);
    data[3] = (u8)((value >> 24) & 0xff);
    sys_write(fd, data, 4);
}

static void rewrite_index(void)
{
    char line[160];
    unsigned int index;
    int fd;

    fd = sys_open(HS_INDEX_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0)
        return;

    {
        const char *header = "# bssid,stored_tick,frames,file,essid\n";
        sys_write(fd, header, str_len(header));
    }
    for (index = 0; index < MAX_APS; index++) {
        struct ap_info *ap = &aps[index];
        unsigned int offset = 0;
        if (!ap->used || !ap->hs_saved)
            continue;
        append_mac_colon(line, &offset, sizeof(line), ap->bssid);
        append_char(line, &offset, sizeof(line), ',');
        append_dec(line, &offset, sizeof(line), ap->hs_tick);
        append_char(line, &offset, sizeof(line), ',');
        append_dec(line, &offset, sizeof(line), ap->hs_frame_count);
        append_char(line, &offset, sizeof(line), ',');
        append_text(line, &offset, sizeof(line), (const char *)ap->hs_file);
        append_char(line, &offset, sizeof(line), ',');
        if (ap->ssid_len)
            append_text(line, &offset, sizeof(line), ap->ssid);
        else
            append_text(line, &offset, sizeof(line), "<hidden/unknown>");
        append_char(line, &offset, sizeof(line), '\n');
        sys_write(fd, line, offset);
    }
    sys_close(fd);
}

static void rewrite_network_index(void)
{
    char line[160];
    unsigned int index;
    int fd = sys_open(NETWORK_INDEX_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0)
        return;
    {
        const char *header = "# bssid,channel,signal_dbm,beacons,probes,data,essid\n";
        sys_write(fd, header, str_len(header));
    }
    for (index = 0; index < MAX_APS; index++) {
        struct ap_info *ap = &aps[index];
        unsigned int offset = 0;
        if (!ap->used || !ap->channel)
            continue;
        append_mac_colon(line, &offset, sizeof(line), ap->bssid);
        append_char(line, &offset, sizeof(line), ',');
        append_dec(line, &offset, sizeof(line), ap->channel);
        append_char(line, &offset, sizeof(line), ',');
        if (ap->has_signal)
            append_signed_dec(line, &offset, sizeof(line), ap->signal_dbm);
        else
            append_text(line, &offset, sizeof(line), "0");
        append_char(line, &offset, sizeof(line), ',');
        append_dec(line, &offset, sizeof(line), ap->beacons);
        append_char(line, &offset, sizeof(line), ',');
        append_dec(line, &offset, sizeof(line), ap->probes);
        append_char(line, &offset, sizeof(line), ',');
        append_dec(line, &offset, sizeof(line), ap->data);
        append_char(line, &offset, sizeof(line), ',');
        if (ap->ssid_len)
            append_text(line, &offset, sizeof(line), ap->ssid);
        else
            append_text(line, &offset, sizeof(line), "<hidden/unknown>");
        append_char(line, &offset, sizeof(line), '\n');
        sys_write(fd, line, offset);
    }
    sys_close(fd);
}
static void save_handshake(struct ap_info *ap)
{
    char path[64];
    int fd;
    unsigned int index;

    if (!ap || ap->hs_frame_count < 2)
        return;

    sys_mkdir(HS_STORE_DIR, 0755);
    evict_oldest_if_needed(ap);
    build_hs_file_path(ap, path, sizeof(path));

    fd = sys_open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        write_text("HANDSHAKE_SAVE_ERROR bssid=");
        write_mac(ap->bssid);
        write_text("\n");
        return;
    }

    write_u32_le(fd, 0xa1b2c3d4U);
    write_u16_le(fd, 2);
    write_u16_le(fd, 4);
    write_u32_le(fd, 0);
    write_u32_le(fd, 0);
    write_u32_le(fd, 65535U);
    write_u32_le(fd, 127U);

    for (index = 0; index < ap->hs_frame_count; index++) {
        struct stored_frame *stored = &ap->hs_frames[index];
        write_u32_le(fd, storage_tick + index);
        write_u32_le(fd, 0);
        write_u32_le(fd, stored->length);
        write_u32_le(fd, stored->length);
        sys_write(fd, stored->data, stored->length);
    }
    sys_close(fd);

    if (!ap->hs_saved)
        handshake_count++;
    ap->hs_saved = 1;
    ap->hs_tick = ++storage_tick;
    build_hs_file_path(ap, (char *)ap->hs_file, sizeof(ap->hs_file));
    rewrite_index();

    write_text("HANDSHAKE_SAVED bssid=");
    write_mac(ap->bssid);
    write_text(" file=");
    write_text((const char *)ap->hs_file);
    write_text(" frames=");
    write_dec(ap->hs_frame_count);
    write_text(" stored=");
    write_dec(handshake_count);
    write_text("\n");
}

static void record_eapol(struct ap_info *ap, const u8 *frame, unsigned int frame_length, const u8 *eapol, unsigned int eapol_length)
{
    u16 key_info = 0;
    unsigned int slot;
    unsigned int capture_length = frame_length;

    if (!ap || eapol_length < 8)
        return;
    if (eapol[1] != 3)
        return;

    key_info = ((u16)eapol[5] << 8) | eapol[6];
    ap->has_eapol = 1;
    if (key_info & 0x0100)
        ap->has_mic = 1;
    if (key_info & 0x0080)
        ap->has_ack = 1;

    if (capture_length > HS_CAPTURE_BYTES)
        capture_length = HS_CAPTURE_BYTES;

    if (ap->hs_frame_count < HS_FRAMES) {
        slot = ap->hs_frame_count++;
    } else {
        for (slot = 1; slot < HS_FRAMES; slot++)
            copy_stored_frame(&ap->hs_frames[slot - 1], &ap->hs_frames[slot]);
        slot = HS_FRAMES - 1;
    }

    ap->hs_frames[slot].length = (u16)capture_length;
    copy_bytes(ap->hs_frames[slot].data, frame, capture_length);

    if (ap->hs_frame_count >= 2 && ap->has_mic && ap->has_ack)
        save_handshake(ap);
}

static void handle_mgmt(const u8 *body, unsigned int length, u8 subtype, int has_signal, int signal_dbm)
{
    struct ap_info *ap;
    const u8 *bssid;
    if (length < 24) {
        short_frames++;
        return;
    }
    bssid = body + 16;
    if (is_broadcast(bssid) || !filter_accept_bssid(bssid))
        return;
    ap = find_ap(bssid);
    if (!ap)
        return;
    if (has_signal) {
        ap->has_signal = 1;
        ap->signal_dbm = signal_dbm;
    }
    if (subtype == 8 || subtype == 5) {
        if (subtype == 8)
            ap->beacons++;
        else
            ap->probes++;
        if (length > 36)
            parse_tags(ap, body + 36, length - 36);
    }
}

static unsigned int get_data_header_length(const u8 *body, unsigned int length)
{
    u8 to_ds;
    u8 from_ds;
    u8 subtype;
    unsigned int header_length = 24;
    if (length < 24)
        return 0;
    to_ds = body[1] & 0x01;
    from_ds = body[1] & 0x02;
    subtype = (body[0] >> 4) & 0x0f;
    if (to_ds && from_ds)
        header_length += 6;
    if (subtype & 0x08)
        header_length += 2;
    if (header_length > length)
        return 0;
    return header_length;
}

static const u8 *get_bssid_from_data(const u8 *body)
{
    u8 to_ds = body[1] & 0x01;
    u8 from_ds = body[1] & 0x02;
    if (to_ds && !from_ds)
        return body + 4;
    if (!to_ds && from_ds)
        return body + 10;
    return body + 16;
}

static void handle_data(const u8 *frame, unsigned int frame_length, const u8 *body, unsigned int length, int has_signal, int signal_dbm)
{
    const u8 *bssid;
    struct ap_info *ap;
    unsigned int header_length;
    const u8 *payload;
    unsigned int payload_length;

    if (length < 24) {
        short_frames++;
        return;
    }
    bssid = get_bssid_from_data(body);
    if (is_broadcast(bssid) || !filter_accept_bssid(bssid))
        return;
    ap = find_ap(bssid);
    if (ap) {
        ap->data++;
        if (has_signal) {
            ap->has_signal = 1;
            ap->signal_dbm = signal_dbm;
        }
    }

    header_length = get_data_header_length(body, length);
    if (!header_length || length < header_length + 8)
        return;

    payload = body + header_length;
    payload_length = length - header_length;
    if (payload[0] == 0xaa && payload[1] == 0xaa && payload[2] == 0x03 && payload[3] == 0x00 &&
        payload[4] == 0x00 && payload[5] == 0x00 && payload[6] == 0x88 && payload[7] == 0x8e) {
        record_eapol(ap, frame, frame_length, payload + 8, payload_length - 8);
    }
}

static unsigned int align_offset(unsigned int offset, unsigned int alignment)
{
    return (offset + alignment - 1U) & ~(alignment - 1U);
}

static int radiotap_signal_dbm(const u8 *frame, unsigned int length, int *signal_dbm)
{
    u32 present;
    unsigned int fields = 8;
    unsigned int offset;
    if (length < 8)
        return 0;
    present = (u32)frame[4] | ((u32)frame[5] << 8) | ((u32)frame[6] << 16) | ((u32)frame[7] << 24);
    while (present & 0x80000000U) {
        if (fields + 4 > length)
            return 0;
        present = (u32)frame[fields] | ((u32)frame[fields + 1] << 8) |
                  ((u32)frame[fields + 2] << 16) | ((u32)frame[fields + 3] << 24);
        fields += 4;
    }
    present = (u32)frame[4] | ((u32)frame[5] << 8) | ((u32)frame[6] << 16) | ((u32)frame[7] << 24);
    if (!(present & (1U << 5)))
        return 0;
    offset = fields;
    if (present & (1U << 0)) { offset = align_offset(offset, 8); offset += 8; }
    if (present & (1U << 1)) offset += 1;
    if (present & (1U << 2)) offset += 1;
    if (present & (1U << 3)) { offset = align_offset(offset, 2); offset += 4; }
    if (present & (1U << 4)) { offset = align_offset(offset, 2); offset += 2; }
    if (offset >= length || offset >= ((u16)frame[2] | ((u16)frame[3] << 8)))
        return 0;
    *signal_dbm = frame[offset] >= 128 ? (int)frame[offset] - 256 : (int)frame[offset];
    return 1;
}

static void handle_frame(const u8 *frame, unsigned int length)
{
    u16 radiotap_length;
    const u8 *body;
    unsigned int body_length;
    u8 frame_control;
    u8 type;
    u8 subtype;
    int signal_dbm = 0;
    int has_signal;

    total_frames++;
    if (length < 12) {
        short_frames++;
        return;
    }
    radiotap_length = (u16)frame[2] | ((u16)frame[3] << 8);
    has_signal = radiotap_signal_dbm(frame, length, &signal_dbm);
    if (radiotap_length >= length || radiotap_length < 8) {
        short_frames++;
        return;
    }
    body = frame + radiotap_length;
    body_length = length - radiotap_length;
    if (body_length < 2) {
        short_frames++;
        return;
    }
    frame_control = body[0];
    type = (frame_control >> 2) & 0x03;
    subtype = (frame_control >> 4) & 0x0f;
    if (type == 0) {
        mgmt_frames++;
        handle_mgmt(body, body_length, subtype, has_signal, signal_dbm);
    } else if (type == 1) {
        ctrl_frames++;
    } else if (type == 2) {
        data_frames++;
        handle_data(frame, length, body, body_length, has_signal, signal_dbm);
    }
}

static void print_table(void)
{
    unsigned int index;
    rewrite_network_index();
    write_text("\nBSSID              CH  BEACON PROBE DATA HS  ESSID\n");
    for (index = 0; index < MAX_APS; index++) {
        struct ap_info *ap = &aps[index];
        if (!ap->used || !filter_accept_ap(ap))
            continue;
        write_mac(ap->bssid);
        write_text("  ");
        if (ap->channel)
            write_dec(ap->channel);
        else
            write_text("?");
        write_text("   ");
        write_dec(ap->beacons);
        write_text("      ");
        write_dec(ap->probes);
        write_text("     ");
        write_dec(ap->data);
        write_text("    ");
        if (ap->hs_saved)
            write_text("yes ");
        else if (ap->hs_frame_count)
            write_text("eap ");
        else
            write_text("no  ");
        if (ap->ssid_len)
            write_text(ap->ssid);
        else
            write_text("<hidden/unknown>");
        write_text("\n");
    }
    write_text("\nFRAMES total=");
    write_dec(total_frames);
    write_text(" mgmt=");
    write_dec(mgmt_frames);
    write_text(" ctrl=");
    write_dec(ctrl_frames);
    write_text(" data=");
    write_dec(data_frames);
    write_text(" short=");
    write_dec(short_frames);
    write_text(" handshakes=");
    write_dec(handshake_count);
    write_text("\n");
}

static int run_dump(unsigned int target_frames)
{
    static u8 frame[4096];
    int fd;
    int interface_index;
    unsigned int received = 0;
    unsigned int next_print = 256;

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

    sys_mkdir(HS_STORE_DIR, 0755);
    rewrite_index();
    rewrite_network_index();

    write_text("AIRODUMP_START interface=wlan0 frames=");
    write_dec(target_frames);
    if (target_frames == 0)
        write_text(" forever");
    write_text(" store=/tmp/airhs max_handshakes=");
    write_dec(MAX_HANDSHAKES);
    write_text(" mode=");
    if (filter_has_bssid) {
        write_text("bssid:");
        write_mac(filter_bssid);
    } else {
        write_text("all");
    }
    if (filter_has_channel) {
        write_text(" channel=");
        write_dec(filter_channel);
    }
    write_text("\n");

    for (;;) {
        int length = sys_recv(fd, frame, sizeof(frame), 0);
        if (length < 0) {
            write_text("RECV_ERROR\n");
            sys_close(fd);
            return 13;
        }
        handle_frame(frame, (unsigned int)length);
        received++;
        if (target_frames && received >= target_frames)
            break;
        if (received >= next_print) {
            print_table();
            next_print += 256;
        }
    }
    sys_close(fd);
    print_table();
    write_text("AIRODUMP_OK\n");
    return 0;
}

static void usage(void)
{
    write_text("Usage: airodump [frames] [all|bssid <mac>] [channel <n>]\n");
    write_text("frames=0 runs forever. Interface is fixed to wlan0 monitor/radiotap.\n");
    write_text("Handshake store: /tmp/airhs, one latest PCAP per BSSID, oldest evicted after max.\n");
}

static int main_program(int argc, char **argv)
{
    unsigned int frames = 256;
    unsigned int index = 2;

    filter_has_bssid = 0;
    filter_has_channel = 0;

    if (argc >= 2) {
        if (str_equal(argv[1], "help") || str_equal(argv[1], "--help") || str_equal(argv[1], "-h")) {
            usage();
            return 0;
        }
        if (parse_uint(argv[1], &frames) != 0) {
            usage();
            return 1;
        }
    }

    while (index < (unsigned int)argc) {
        if (str_equal(argv[index], "all")) {
            filter_has_bssid = 0;
            index++;
        } else if (str_equal(argv[index], "bssid")) {
            if (index + 1 >= (unsigned int)argc || parse_mac_text(argv[index + 1], filter_bssid) != 0) {
                usage();
                return 1;
            }
            filter_has_bssid = 1;
            index += 2;
        } else if (str_equal(argv[index], "channel")) {
            unsigned int channel;
            if (index + 1 >= (unsigned int)argc || parse_uint(argv[index + 1], &channel) != 0 || channel == 0 || channel > 14) {
                usage();
                return 1;
            }
            filter_has_channel = 1;
            filter_channel = (u8)channel;
            index += 2;
        } else {
            usage();
            return 1;
        }
    }

    if (frames > 65535U)
        frames = 65535U;
    return run_dump(frames);
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
