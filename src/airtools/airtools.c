typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern int sys_read(int fd, void *buffer, unsigned int count);
extern int sys_write(int fd, const void *buffer, unsigned int count);
extern int sys_open(const char *path, unsigned int flags, unsigned int mode);
extern int sys_close(int fd);
extern int sys_socket(int domain, int type, int protocol);
extern int sys_setsockopt(int fd, int level, int option, const void *value, unsigned int length);
extern int sys_bind(int fd, const void *address, unsigned int length);
extern int sys_listen(int fd, int backlog);
extern int sys_accept(int fd, void *address, unsigned int *address_length);
extern int sys_recv(int fd, void *buffer, unsigned int length, unsigned int flags);
extern int sys_send(int fd, const void *buffer, unsigned int length, unsigned int flags);
extern int sys_unlink(const char *path);
extern int sys_recvfrom(int fd, void *buffer, unsigned int length, unsigned int flags, void *address, unsigned int *address_length);
extern int sys_sendto(int fd, const void *buffer, unsigned int length, unsigned int flags, const void *address, unsigned int address_length);
extern int sys_fork(void);
extern int sys_execve(const char *path, char *const argv[], char *const envp[]);
extern int sys_waitpid(int pid, int *status, int options);
extern int sys_kill(int pid, int signal);
extern int sys_dup2(int oldfd, int newfd);
extern int sys_nanosleep(const void *request, void *remaining);
extern void sys_exit(int status);

#define AF_INET 2
#define SOCK_DGRAM 1
#define SOCK_STREAM 2
#define SOL_SOCKET 0xffff
#define SO_REUSEADDR 4
#define AIRTOOLS_PORT 8088
#define SIGTERM 15

#define O_RDONLY 0x0000
#define O_WRONLY 0x0001
#define O_CREAT  0x0100
#define O_TRUNC  0x0200

#define STATE_PATH "/tmp/airtools.state"
#define AIRHS_INDEX "/tmp/airhs/index.txt"
#define AIRSCAN_INDEX "/tmp/airscan-networks.txt"

struct mode_state {
    u8 mode;       /* 0=all, 1=bssid */
    u8 has_channel;
    u8 channel;
    u8 reserved;
    u8 bssid[6];
};

static struct mode_state current_state;
static int airodump_pid;
static int scan_hopper_pid;
static char request_buffer[512];
static char response_buffer[4096];
static unsigned int response_length;
static char channel_text[4];
static char count_text[10];
static char bssid_text[18];
static char station_text[18];
static char ssid_text[40];
static char wifi_ssid_text[33];
static char wifi_pass_text[64];
static char state_line[96];
static char *empty_envp[] = { 0 };

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

static void copy_string(char *destination, unsigned int destination_size, const char *source)
{
    unsigned int index = 0;
    if (destination_size == 0)
        return;
    while (source[index] != 0 && index + 1 < destination_size) {
        destination[index] = source[index];
        index++;
    }
    destination[index] = 0;
}

static void response_reset(void)
{
    response_length = 0;
}

static void response_append_char(char value)
{
    if (response_length + 1 < sizeof(response_buffer))
        response_buffer[response_length++] = value;
}

static void response_append(const char *text)
{
    unsigned int index = 0;
    while (text[index] != 0 && response_length + 1 < sizeof(response_buffer))
        response_buffer[response_length++] = text[index++];
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

static void dec_to_text(char *output, unsigned int output_size, unsigned int value)
{
    char temp[10];
    unsigned int index = 0;
    unsigned int out = 0;
    if (output_size == 0)
        return;
    if (value == 0) {
        output[0] = '0';
        output[1] = 0;
        return;
    }
    while (value > 0 && index < sizeof(temp)) {
        temp[index++] = (char)('0' + (value % 10));
        value /= 10;
    }
    while (index > 0 && out + 1 < output_size) {
        index--;
        output[out++] = temp[index];
    }
    output[out] = 0;
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
        result = result * 10U + (unsigned int)(text[index] - '0');
        if (result > 100000U)
            return -1;
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
    return text[17] == 0 ? 0 : -1;
}

static void mac_to_text(char *output, const u8 mac[6])
{
    static const char hex[] = "0123456789abcdef";
    unsigned int index;
    unsigned int offset = 0;
    for (index = 0; index < 6; index++) {
        if (index)
            output[offset++] = ':';
        output[offset++] = hex[mac[index] >> 4];
        output[offset++] = hex[mac[index] & 0x0f];
    }
    output[offset] = 0;
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
        destination[output++] = source[input] == '+' ? ' ' : source[input];
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
        unsigned int k;
        int match = 1;

        while (path[index] != 0 && path[index] != '=' && path[index] != '&' && path[index] != ' ')
            index++;
        key_length = index - start;
        if (path[index] != '=') {
            while (path[index] != 0 && path[index] != '&' && path[index] != ' ')
                index++;
            if (path[index] == '&')
                index++;
            continue;
        }
        index++;
        value_start = index;
        while (path[index] != 0 && path[index] != '&' && path[index] != ' ')
            index++;
        value_length = index - value_start;
        if (key_length == name_length) {
            for (k = 0; k < name_length; k++) {
                if (path[start + k] != name[k])
                    match = 0;
            }
            if (match) {
                url_decode_copy(output, output_size, path + value_start, value_length);
                return 1;
            }
        }
        if (path[index] == '&')
            index++;
    }
    return 0;
}

static void default_state(void)
{
    zero_bytes((u8 *)&current_state, sizeof(current_state));
    current_state.mode = 0;
    current_state.has_channel = 1;
    current_state.channel = 11;
}

static void append_state_line(char *line, unsigned int *offset, const char *text)
{
    while (*text != 0 && *offset + 1 < sizeof(state_line))
        line[(*offset)++] = *text++;
}

static void build_state_line(void)
{
    unsigned int offset = 0;
    append_state_line(state_line, &offset, "?mode=");
    if (current_state.mode == 1) {
        append_state_line(state_line, &offset, "bssid&bssid=");
        mac_to_text(bssid_text, current_state.bssid);
        append_state_line(state_line, &offset, bssid_text);
    } else {
        append_state_line(state_line, &offset, "all");
    }
    if (current_state.has_channel) {
        append_state_line(state_line, &offset, "&channel=");
        dec_to_text(channel_text, sizeof(channel_text), current_state.channel);
        append_state_line(state_line, &offset, channel_text);
    }
    append_state_line(state_line, &offset, "\n");
    state_line[offset] = 0;
}

static void save_state(void)
{
    int fd;
    build_state_line();
    fd = sys_open(STATE_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd >= 0) {
        sys_write(fd, state_line, str_len(state_line));
        sys_close(fd);
    }
}

static void load_state(void)
{
    int fd;
    int length;
    char value[64];
    default_state();
    fd = sys_open(STATE_PATH, O_RDONLY, 0);
    if (fd < 0)
        return;
    length = sys_read(fd, state_line, sizeof(state_line) - 1);
    sys_close(fd);
    if (length <= 0)
        return;
    state_line[length] = 0;
    if (get_query_value(state_line, "mode", value, sizeof(value))) {
        if (str_equal(value, "bssid"))
            current_state.mode = 1;
        else
            current_state.mode = 0;
    }
    if (get_query_value(state_line, "bssid", value, sizeof(value)) && parse_mac(value, current_state.bssid) == 0)
        current_state.mode = 1;
    if (get_query_value(state_line, "channel", value, sizeof(value))) {
        unsigned int channel;
        if (parse_uint(value, &channel) == 0 && channel >= 1 && channel <= 14) {
            current_state.has_channel = 1;
            current_state.channel = (u8)channel;
        }
    }
}

static int child_redirect_devnull(void)
{
    int fd = sys_open("/dev/null", O_WRONLY, 0);
    if (fd >= 0) {
        sys_dup2(fd, 1);
        sys_dup2(fd, 2);
        if (fd > 2)
            sys_close(fd);
    }
    return 0;
}

static void exec_path_pair(const char *first, const char *second, char *const argv[])
{
    sys_execve(first, argv, empty_envp);
    sys_execve(second, argv, empty_envp);
    sys_exit(127);
}

static int spawn_airodump(void)
{
    int pid;
    char *argv[8];
    unsigned int argc = 0;

    if (airodump_pid > 0) {
        sys_kill(airodump_pid, SIGTERM);
        sys_waitpid(airodump_pid, 0, 0);
        airodump_pid = 0;
    }

    if (current_state.has_channel) {
        int mpid;
        dec_to_text(channel_text, sizeof(channel_text), current_state.channel);
        mpid = sys_fork();
        if (mpid == 0) {
            char *margv[4];
            child_redirect_devnull();
            margv[0] = (char *)"wn723n-monitor";
            margv[1] = (char *)"monitor";
            margv[2] = channel_text;
            margv[3] = 0;
            exec_path_pair("/bin/wn723n-monitor", "/bin/wn723n-monitor", margv);
        } else if (mpid > 0) {
            sys_waitpid(mpid, 0, 0);
        }
    }

    pid = sys_fork();
    if (pid < 0)
        return -1;
    if (pid == 0) {
        child_redirect_devnull();
        argv[argc++] = (char *)"airodump";
        argv[argc++] = (char *)"0";
        if (current_state.mode == 1) {
            argv[argc++] = (char *)"bssid";
            mac_to_text(bssid_text, current_state.bssid);
            argv[argc++] = bssid_text;
        } else {
            argv[argc++] = (char *)"all";
        }
        if (current_state.has_channel) {
            argv[argc++] = (char *)"channel";
            dec_to_text(channel_text, sizeof(channel_text), current_state.channel);
            argv[argc++] = channel_text;
        }
        argv[argc] = 0;
        exec_path_pair("/bin/airodump", "/tmp/airodump", argv);
    }
    airodump_pid = pid;
    return 0;
}

static int stop_airodump(void)
{
    if (airodump_pid <= 0)
        return 0;
    sys_kill(airodump_pid, SIGTERM);
    sys_waitpid(airodump_pid, 0, 0);
    airodump_pid = 0;
    return 0;
}

static void stop_scan_hopper(void)
{
    if (scan_hopper_pid <= 0)
        return;
    sys_kill(scan_hopper_pid, SIGTERM);
    sys_waitpid(scan_hopper_pid, 0, 0);
    scan_hopper_pid = 0;
}

static int set_monitor_channel(unsigned int channel, int ensure_monitor)
{
    int pid;
    int wait_status = 0;
    dec_to_text(channel_text, sizeof(channel_text), channel);
    pid = sys_fork();
    if (pid < 0)
        return -1;
    if (pid == 0) {
        child_redirect_devnull();
        if (ensure_monitor) {
            char *argv[4];
            argv[0] = (char *)"wn723n-monitor";
            argv[1] = (char *)"monitor";
            argv[2] = channel_text;
            argv[3] = 0;
            exec_path_pair("/bin/wn723n-monitor", "/bin/wn723n-monitor", argv);
        } else {
            char *argv[5];
            argv[0] = (char *)"iwconfig";
            argv[1] = (char *)"wlan0";
            argv[2] = (char *)"channel";
            argv[3] = channel_text;
            argv[4] = 0;
            exec_path_pair("/bin/iwconfig", "/bin/iwconfig", argv);
        }
    }
    if (sys_waitpid(pid, &wait_status, 0) < 0)
        return -1;
    return wait_status == 0 ? 0 : -1;
}

static void channel_hopper_loop(void)
{
    unsigned int channel = 1;
    for (;;) {
        set_monitor_channel(channel, 0);
        {
            u32 request[2];
            request[0] = 0;
            request[1] = 350000000U;
            sys_nanosleep(request, 0);
        }
        channel++;
        if (channel > 13)
            channel = 1;
    }
}

static int start_discovery_scan(void)
{
    int pid;
    char *argv[4];
    stop_scan_hopper();
    stop_airodump();
    sys_unlink(AIRSCAN_INDEX);

    if (set_monitor_channel(1, 1) != 0)
        return 52;

    pid = sys_fork();
    if (pid < 0)
        return 50;
    if (pid == 0) {
        child_redirect_devnull();
        argv[0] = (char *)"airodump";
        argv[1] = (char *)"0";
        argv[2] = (char *)"all";
        argv[3] = 0;
        exec_path_pair("/bin/airodump", "/tmp/airodump", argv);
    }
    airodump_pid = pid;

    pid = sys_fork();
    if (pid < 0) {
        stop_airodump();
        return 51;
    }
    if (pid == 0) {
        channel_hopper_loop();
        sys_exit(0);
    }
    scan_hopper_pid = pid;
    return 0;
}

static int spawn_aireplay_from_path(const char *path)
{
    char mode[16];
    char value[64];
    char *argv[8];
    unsigned int argc = 0;
    int pid;

    if (!get_query_value(path, "mode", mode, sizeof(mode)))
        copy_string(mode, sizeof(mode), "test");
    if (!get_query_value(path, "count", count_text, sizeof(count_text)))
        copy_string(count_text, sizeof(count_text), "1");

    argv[argc++] = (char *)"aireplay";
    if (str_equal(mode, "deauth") || str_equal(mode, "-0")) {
        argv[argc++] = (char *)"-0";
        argv[argc++] = count_text;
        if (!get_query_value(path, "bssid", bssid_text, sizeof(bssid_text)))
            return 31;
        argv[argc++] = bssid_text;
        if (get_query_value(path, "station", station_text, sizeof(station_text)))
            argv[argc++] = station_text;
    } else if (str_equal(mode, "probe")) {
        argv[argc++] = (char *)"probe";
        argv[argc++] = count_text;
        if (get_query_value(path, "ssid", ssid_text, sizeof(ssid_text)))
            argv[argc++] = ssid_text;
    } else {
        argv[argc++] = (char *)"test";
        argv[argc++] = count_text;
    }
    argv[argc] = 0;

    pid = sys_fork();
    if (pid < 0)
        return 32;
    if (pid == 0) {
        child_redirect_devnull();
        exec_path_pair("/bin/aireplay", "/tmp/aireplay", argv);
    }
    sys_waitpid(pid, 0, 0);
    response_append("OK aireplay mode=");
    response_append(mode);
    response_append("\n");
    return 0;
}

static int is_alnum_text(const char *text)
{
    unsigned int index = 0;
    while (text[index] != 0) {
        char c = text[index];
        if (!((c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')))
            return 0;
        index++;
    }
    return 1;
}

static int validate_wifi_ssid(const char *text)
{
    unsigned int length = str_len(text);
    return length >= 1 && length <= 32 && is_alnum_text(text);
}

static int validate_wifi_pass(const char *text)
{
    unsigned int length = str_len(text);
    return length >= 8 && length <= 63 && is_alnum_text(text);
}

static int spawn_airwifi_apply(const char *ssid, const char *pass)
{
    int pid = sys_fork();
    if (pid < 0)
        return 40;
    if (pid == 0) {
        char *argv[5];
        child_redirect_devnull();
        argv[0] = (char *)"airwifi";
        argv[1] = (char *)"apply-delayed";
        argv[2] = (char *)ssid;
        argv[3] = (char *)pass;
        argv[4] = 0;
        exec_path_pair("/bin/airwifi", "/tmp/airwifi", argv);
    }
    return 0;
}

static int handle_wifi_request(const char *path)
{
    char ssid[33];
    char pass[64];
    int has_ssid;
    int has_pass;

    if (starts_with(path, "/wifi/status")) {
        response_append("OK wifi ssid=");
        response_append(wifi_ssid_text[0] ? wifi_ssid_text : "AT");
        response_append(" pass_len=8 auth=WPA2PSK charset=alnum ssid_len=1..32 pass_len=8..63\n");
        return 0;
    }

    if (!starts_with(path, "/wifi/set")) {
        response_append("ERR wifi unknown\n");
        return 41;
    }

    has_ssid = get_query_value(path, "ssid", ssid, sizeof(ssid));
    has_pass = get_query_value(path, "pass", pass, sizeof(pass));
    if (!has_ssid || !has_pass) {
        response_append("ERR wifi missing ssid/pass\n");
        return 42;
    }
    if (!validate_wifi_ssid(ssid)) {
        response_append("ERR wifi ssid must be 1..32 chars A-Z a-z 0-9 only\n");
        return 43;
    }
    if (!validate_wifi_pass(pass)) {
        response_append("ERR wifi pass must be 8..63 chars A-Z a-z 0-9 only\n");
        return 44;
    }

    copy_string(wifi_ssid_text, sizeof(wifi_ssid_text), ssid);
    copy_string(wifi_pass_text, sizeof(wifi_pass_text), pass);
    if (spawn_airwifi_apply(wifi_ssid_text, wifi_pass_text) != 0) {
        response_append("ERR wifi apply spawn\n");
        return 45;
    }
    response_append("OK wifi scheduled ssid=");
    response_append(wifi_ssid_text);
    response_append(" pass_len=");
    response_append_dec(str_len(wifi_pass_text));
    response_append("\n");
    return 0;
}

static int apply_set_request(const char *path)
{
    char value[64];
    struct mode_state next = current_state;

    if (get_query_value(path, "mode", value, sizeof(value))) {
        if (str_equal(value, "bssid"))
            next.mode = 1;
        else if (str_equal(value, "all"))
            next.mode = 0;
        else
            return 20;
    }
    if (next.mode == 1 || get_query_value(path, "bssid", value, sizeof(value))) {
        if (!get_query_value(path, "bssid", value, sizeof(value)) || parse_mac(value, next.bssid) != 0)
            return 21;
        next.mode = 1;
    }
    if (get_query_value(path, "channel", value, sizeof(value))) {
        unsigned int channel;
        if (parse_uint(value, &channel) != 0 || channel < 1 || channel > 14)
            return 22;
        next.has_channel = 1;
        next.channel = (u8)channel;
    } else if (get_query_value(path, "nochannel", value, sizeof(value))) {
        next.has_channel = 0;
    }

    current_state = next;
    save_state();
    response_append("OK set ");
    build_state_line();
    response_append(state_line);
    return 0;
}

static void refresh_children(void)
{
    if (airodump_pid > 0 && sys_waitpid(airodump_pid, 0, 1) == airodump_pid) {
        airodump_pid = 0;
        stop_scan_hopper();
    }
    if (scan_hopper_pid > 0 && sys_waitpid(scan_hopper_pid, 0, 1) == scan_hopper_pid)
        scan_hopper_pid = 0;
}

static void append_status(void)
{
    refresh_children();
    response_append("OK airtools=1 pid=");
    response_append_dec((airodump_pid > 0 && scan_hopper_pid <= 0) ? (unsigned int)airodump_pid : 0);
    response_append(" scan=");
    response_append_dec(scan_hopper_pid > 0 ? 1 : 0);
    response_append(" ");
    build_state_line();
    response_append(state_line);
    response_append("state_path=");
    response_append(STATE_PATH);
    response_append("\n");
}

static void append_file(const char *path)
{
    int fd;
    int length;
    char buffer[512];
    fd = sys_open(path, O_RDONLY, 0);
    if (fd < 0) {
        response_append("ERR open\n");
        return;
    }
    for (;;) {
        length = sys_read(fd, buffer, sizeof(buffer));
        if (length <= 0)
            break;
        if (response_length + (unsigned int)length >= sizeof(response_buffer))
            length = sizeof(response_buffer) - response_length - 1;
        copy_bytes((u8 *)response_buffer + response_length, (u8 *)buffer, (unsigned int)length);
        response_length += (unsigned int)length;
        if (response_length + 1 >= sizeof(response_buffer))
            break;
    }
    sys_close(fd);
}

static int handle_request(const char *path)
{
    int status = 0;
    response_reset();

    if (starts_with(path, "/wifi"))
        return handle_wifi_request(path);

    if (starts_with(path, "/status")) {
        append_status();
        return 0;
    }
    if (starts_with(path, "/set"))
        return apply_set_request(path);
    if (starts_with(path, "/scan/start")) {
        status = start_discovery_scan();
        response_append(status == 0 ? "OK scan start\n" : "ERR scan start\n");
        return status;
    }
    if (starts_with(path, "/scan/stop")) {
        stop_scan_hopper();
        stop_airodump();
        response_append("OK scan stop\n");
        return 0;
    }
    if (starts_with(path, "/networks")) {
        response_append("OK networks\n");
        append_file(AIRSCAN_INDEX);
        return 0;
    }
    if (starts_with(path, "/start")) {
        stop_scan_hopper();
        stop_airodump();
        load_state();
        status = spawn_airodump();
        response_append(status == 0 ? "OK start\n" : "ERR start\n");
        return status;
    }
    if (starts_with(path, "/stop")) {
        stop_scan_hopper();
        stop_airodump();
        response_append("OK stop\n");
        return 0;
    }
    if (starts_with(path, "/handshakes")) {
        response_append("OK handshakes\n");
        append_file(AIRHS_INDEX);
        return 0;
    }
    if (starts_with(path, "/aireplay"))
        return spawn_aireplay_from_path(path);

    response_append("ERR unknown\n");
    return 1;
}

static int write_all(int fd, const char *buffer, unsigned int length)
{
    unsigned int offset = 0;
    while (offset < length) {
        int written = sys_send(fd, buffer + offset, length - offset, 0);
        if (written <= 0)
            return -1;
        offset += (unsigned int)written;
    }
    return 0;
}

static void send_response(int client_fd, int status)
{
    if (status != 0) {
        response_append("ERR status=");
        response_append_dec((unsigned int)status);
        response_append("\n");
    }
    write_all(client_fd, response_buffer, response_length);
}

static void handle_client(int client_fd)
{
    unsigned int total = 0;
    int status;

    while (total + 1 < sizeof(request_buffer)) {
        int length = sys_recv(client_fd, request_buffer + total,
                              sizeof(request_buffer) - total - 1, 0);
        unsigned int index;
        if (length <= 0)
            break;
        total += (unsigned int)length;
        for (index = 0; index < total; index++) {
            if (request_buffer[index] == '\n') {
                total = index;
                goto request_complete;
            }
        }
    }

request_complete:
    while (total > 0 && (request_buffer[total - 1] == '\n' || request_buffer[total - 1] == '\r'))
        total--;
    request_buffer[total] = 0;
    if (total == 0)
        return;
    status = handle_request(request_buffer);
    send_response(client_fd, status);
}

static int run_server(void)
{
    int server_fd;
    u8 address[16];

    server_fd = sys_socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd >= 0) {
        int reuse = 1;
        sys_setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    }
    if (server_fd < 0)
        return 10;

    zero_bytes(address, sizeof(address));
    address[0] = AF_INET;
    address[1] = 0;
    address[2] = (u8)(AIRTOOLS_PORT >> 8);
    address[3] = (u8)(AIRTOOLS_PORT & 0xff);
    if (sys_bind(server_fd, address, sizeof(address)) < 0)
        return 11;
    if (sys_listen(server_fd, 4) < 0)
        return 12;

    sys_write(1, "AIRTOOLS_TCP_LISTEN port=8088\n", 30);
    load_state();

    for (;;) {
        u8 client[16];
        unsigned int client_length = sizeof(client);
        int client_fd;
        zero_bytes(client, sizeof(client));
        client_fd = sys_accept(server_fd, client, &client_length);
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
