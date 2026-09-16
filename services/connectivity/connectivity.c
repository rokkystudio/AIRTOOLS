/*
 * ENDOSCOPE local connectivity-check responder.
 *
 * This program is intentionally freestanding: it uses Linux MIPS O32 syscalls
 * directly and does not depend on libc, libpthread, epoll, or the Go runtime.
 *
 * It serves:
 *   UDP/53  - DNS A responses for common OS connectivity-check hostnames.
 *   TCP/80  - HTTP responses expected by Android, Apple, and Windows probes.
 *
 * Usage:
 *   endoscope-connectivity-c <ap-ipv4>
 *
 * Example:
 *   endoscope-connectivity-c 192.168.10.123
 */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned int size_t;

#define AF_INET 2
#define SOCK_DGRAM 1
#define SOCK_STREAM 2
#define IPPROTO_IP 0
#define POLLIN 0x0001

#define NR_exit      4001
#define NR_read      4003
#define NR_write     4004
#define NR_close     4006
#define NR_accept    4168
#define NR_bind      4169
#define NR_listen    4174
#define NR_recvmsg   4177
#define NR_sendmsg   4179
#define NR_socket    4183
#define NR_poll      4188

struct sockaddr_in {
    u16 family;
    u16 port;
    u32 address;
    u8 zero[8];
};

struct iovec {
    void *base;
    u32 len;
};

struct msghdr {
    void *name;
    u32 namelen;
    struct iovec *iov;
    u32 iovlen;
    void *control;
    u32 controllen;
    u32 flags;
};

struct pollfd {
    s32 fd;
    short events;
    short revents;
};

/* sys_call1 invokes a one-argument Linux MIPS O32 syscall. */
static __attribute__((noinline)) long sys_call1(long number, long arg0)
{
    register long v0 __asm__("$2") = number;
    register long a0 __asm__("$4") = arg0;
    register long a3 __asm__("$7");

    __asm__ volatile(
        "syscall"
        : "+r"(v0), "=r"(a3)
        : "r"(a0)
        : "memory"
    );

    return a3 ? -v0 : v0;
}

/* sys_call2 invokes a two-argument Linux MIPS O32 syscall. */
static __attribute__((noinline)) long sys_call2(long number, long arg0, long arg1)
{
    register long v0 __asm__("$2") = number;
    register long a0 __asm__("$4") = arg0;
    register long a1 __asm__("$5") = arg1;
    register long a3 __asm__("$7");

    __asm__ volatile(
        "syscall"
        : "+r"(v0), "=r"(a3)
        : "r"(a0), "r"(a1)
        : "memory"
    );

    return a3 ? -v0 : v0;
}

/* sys_call3 invokes a three-argument Linux MIPS O32 syscall. */
static __attribute__((noinline)) long sys_call3(long number, long arg0, long arg1, long arg2)
{
    register long v0 __asm__("$2") = number;
    register long a0 __asm__("$4") = arg0;
    register long a1 __asm__("$5") = arg1;
    register long a2 __asm__("$6") = arg2;
    register long a3 __asm__("$7");

    __asm__ volatile(
        "syscall"
        : "+r"(v0), "=r"(a3)
        : "r"(a0), "r"(a1), "r"(a2)
        : "memory"
    );

    return a3 ? -v0 : v0;
}

/* mem_copy copies exactly count bytes and returns destination. */
static void *mem_copy(void *destination, const void *source, u32 count)
{
    u8 *dst = (u8 *)destination;
    const u8 *src = (const u8 *)source;
    u32 index;

    for (index = 0; index < count; index++) {
        dst[index] = src[index];
    }

    return destination;
}

/* str_length returns the number of bytes before the first NUL character. */
static u32 str_length(const char *text)
{
    u32 length = 0;

    while (text[length] != 0) {
        length++;
    }

    return length;
}

/* str_equal compares two NUL-terminated ASCII strings. */
static int str_equal(const char *left, const char *right)
{
    u32 index = 0;

    while (left[index] != 0 && right[index] != 0) {
        if (left[index] != right[index]) {
            return 0;
        }
        index++;
    }

    return left[index] == right[index];
}

/* mem_contains returns true when needle occurs inside a bounded byte buffer. */
static int mem_contains(const u8 *buffer, u32 length, const char *needle)
{
    u32 needle_length = str_length(needle);
    u32 index;
    u32 match;

    if (needle_length == 0 || needle_length > length) {
        return 0;
    }

    for (index = 0; index + needle_length <= length; index++) {
        for (match = 0; match < needle_length; match++) {
            if (buffer[index + match] != (u8)needle[match]) {
                break;
            }
        }

        if (match == needle_length) {
            return 1;
        }
    }

    return 0;
}

/* parse_ipv4 converts dotted-decimal IPv4 into a network-order 32-bit value. */
static int parse_ipv4(const char *text, u32 *result)
{
    u32 parts[4];
    u32 part = 0;
    u32 value = 0;
    u32 index = 0;
    u32 digit;

    while (1) {
        char character = text[index++];

        if (character >= '0' && character <= '9') {
            digit = (u32)(character - '0');
            value = value * 10 + digit;
            if (value > 255) {
                return 0;
            }
            continue;
        }

        if (character == '.' || character == 0) {
            if (part >= 4) {
                return 0;
            }

            parts[part++] = value;
            value = 0;

            if (character == 0) {
                break;
            }

            continue;
        }

        return 0;
    }

    if (part != 4) {
        return 0;
    }

    *result =
        (parts[0] << 24) |
        (parts[1] << 16) |
        (parts[2] << 8) |
        parts[3];

    return 1;
}

/* swap16 converts a host-order 16-bit value to network byte order. */
static u16 swap16(u16 value)
{
    return (u16)((value << 8) | (value >> 8));
}

/* swap32 converts a host-order 32-bit value to network byte order. */
static u32 swap32(u32 value)
{
    return
        ((value & 0x000000FFU) << 24) |
        ((value & 0x0000FF00U) << 8) |
        ((value & 0x00FF0000U) >> 8) |
        ((value & 0xFF000000U) >> 24);
}

/* write_all writes the complete response unless the peer closes or an error occurs. */
static void write_all(int fd, const char *data, u32 length)
{
    u32 written = 0;

    while (written < length) {
        long result = sys_call3(NR_write, fd, (long)(data + written), length - written);
        if (result <= 0) {
            return;
        }
        written += (u32)result;
    }
}

/* open_bound_socket creates and binds an IPv4 TCP or UDP socket on all addresses. */
static int open_bound_socket(int type, u16 port)
{
    u8 address[16];
    long fd;
    u32 index;

    fd = sys_call3(NR_socket, AF_INET, type, IPPROTO_IP);
    if (fd < 0) {
        return -1;
    }

    for (index = 0; index < sizeof(address); index++) {
        address[index] = 0;
    }

    address[0] = AF_INET;
    address[1] = 0;
    address[2] = (u8)(port >> 8);
    address[3] = (u8)port;

    if (sys_call3(NR_bind, fd, (long)address, sizeof(address)) < 0) {
        sys_call1(NR_close, fd);
        return -1;
    }

    return (int)fd;
}

/* dns_name_match compares a dotted hostname with a DNS QNAME without compression. */
static int dns_name_match(const u8 *packet, u32 length, u32 offset, const char *hostname)
{
    u32 host_index = 0;

    while (offset < length) {
        u32 label_length = packet[offset++];
        u32 label_index;

        if (label_length == 0) {
            return hostname[host_index] == 0;
        }

        if (label_length > 63 || offset + label_length > length) {
            return 0;
        }

        for (label_index = 0; label_index < label_length; label_index++) {
            char left = (char)packet[offset + label_index];
            char right = hostname[host_index + label_index];

            if (left >= 'A' && left <= 'Z') {
                left = (char)(left - 'A' + 'a');
            }

            if (right >= 'A' && right <= 'Z') {
                right = (char)(right - 'A' + 'a');
            }

            if (left != right) {
                return 0;
            }
        }

        offset += label_length;
        host_index += label_length;

        if (packet[offset] != 0) {
            if (hostname[host_index] != '.') {
                return 0;
            }
            host_index++;
        }
    }

    return 0;
}

/* dns_question_end returns the byte after QTYPE/QCLASS for a one-question request. */
static u32 dns_question_end(const u8 *packet, u32 length)
{
    u32 offset = 12;

    while (offset < length) {
        u32 label_length = packet[offset++];

        if (label_length == 0) {
            if (offset + 4 <= length) {
                return offset + 4;
            }
            return 0;
        }

        if (label_length > 63 || offset + label_length > length) {
            return 0;
        }

        offset += label_length;
    }

    return 0;
}

/* is_connectivity_host recognizes hostnames used by common OS network probes. */
static int is_connectivity_host(const u8 *packet, u32 length)
{
    static const char *hosts[] = {
        "connectivitycheck.gstatic.com",
        "www.google.com",
        "play.googleapis.com",
        "captive.apple.com",
        "www.apple.com",
        "www.msftconnecttest.com",
        "dns.msftncsi.com"
    };
    u32 index;

    for (index = 0; index < sizeof(hosts) / sizeof(hosts[0]); index++) {
        if (dns_name_match(packet, length, 12, hosts[index])) {
            return 1;
        }
    }

    return 0;
}

/* handle_dns processes one UDP DNS request and replies to its source address. */
static void handle_dns(int fd, u32 service_ip)
{
    u8 request[512];
    u8 response[544];
    struct sockaddr_in remote;
    struct iovec recv_iov;
    struct iovec send_iov;
    struct msghdr recv_message;
    struct msghdr send_message;
    long received;
    u32 question_end;
    u16 qtype;
    u16 qclass;
    int answer;
    u32 index;

    recv_iov.base = request;
    recv_iov.len = sizeof(request);

    recv_message.name = &remote;
    recv_message.namelen = sizeof(remote);
    recv_message.iov = &recv_iov;
    recv_message.iovlen = 1;
    recv_message.control = 0;
    recv_message.controllen = 0;
    recv_message.flags = 0;

    received = sys_call3(NR_recvmsg, fd, (long)&recv_message, 0);
    if (received < 16) {
        return;
    }

    if (request[4] != 0 || request[5] != 1) {
        return;
    }

    question_end = dns_question_end(request, (u32)received);
    if (question_end == 0) {
        return;
    }

    qtype = (u16)(((u16)request[question_end - 4] << 8) | request[question_end - 3]);
    qclass = (u16)(((u16)request[question_end - 2] << 8) | request[question_end - 1]);
    answer = qtype == 1 && qclass == 1 && is_connectivity_host(request, (u32)received);

    mem_copy(response, request, question_end);

    response[2] = 0x81;
    response[3] = answer ? 0x80 : 0x83;
    response[6] = 0;
    response[7] = answer ? 1 : 0;
    response[8] = 0;
    response[9] = 0;
    response[10] = 0;
    response[11] = 0;

    if (answer) {
        index = question_end;
        response[index++] = 0xC0;
        response[index++] = 0x0C;
        response[index++] = 0x00;
        response[index++] = 0x01;
        response[index++] = 0x00;
        response[index++] = 0x01;
        response[index++] = 0x00;
        response[index++] = 0x00;
        response[index++] = 0x00;
        response[index++] = 30;
        response[index++] = 0x00;
        response[index++] = 0x04;
        response[index++] = (u8)(service_ip >> 24);
        response[index++] = (u8)(service_ip >> 16);
        response[index++] = (u8)(service_ip >> 8);
        response[index++] = (u8)service_ip;
    } else {
        index = question_end;
    }

    send_iov.base = response;
    send_iov.len = index;

    send_message.name = &remote;
    send_message.namelen = recv_message.namelen;
    send_message.iov = &send_iov;
    send_message.iovlen = 1;
    send_message.control = 0;
    send_message.controllen = 0;
    send_message.flags = 0;

    sys_call3(NR_sendmsg, fd, (long)&send_message, 0);
}

/* handle_http accepts one request and returns the matching connectivity response. */
static void handle_http(int listen_fd)
{
    static const char response_204[] =
        "HTTP/1.1 204 No Content\r\n"
        "Connection: close\r\n"
        "Content-Length: 0\r\n"
        "\r\n";

    static const char apple_body[] =
        "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>";

    static const char apple_header[] =
        "HTTP/1.1 200 OK\r\n"
        "Connection: close\r\n"
        "Content-Type: text/html\r\n"
        "Content-Length: 68\r\n"
        "\r\n";

    static const char microsoft_body[] = "Microsoft Connect Test";
    static const char microsoft_header[] =
        "HTTP/1.1 200 OK\r\n"
        "Connection: close\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: 22\r\n"
        "\r\n";

    static const char ncsi_body[] = "Microsoft NCSI";
    static const char ncsi_header[] =
        "HTTP/1.1 200 OK\r\n"
        "Connection: close\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: 14\r\n"
        "\r\n";

    static const char default_body[] = "ENDOSCOPE local network\n";
    static const char default_header[] =
        "HTTP/1.1 200 OK\r\n"
        "Connection: close\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: 24\r\n"
        "\r\n";

    u8 request[1024];
    long client;
    long received;

    client = sys_call3(NR_accept, listen_fd, 0, 0);
    if (client < 0) {
        return;
    }

    received = sys_call3(NR_read, client, (long)request, sizeof(request));

    if (received > 0) {
        if (mem_contains(request, (u32)received, "/generate_204") ||
            mem_contains(request, (u32)received, "/gen_204")) {
            write_all((int)client, response_204, sizeof(response_204) - 1);
        } else if (mem_contains(request, (u32)received, "/hotspot-detect.html")) {
            write_all((int)client, apple_header, sizeof(apple_header) - 1);
            write_all((int)client, apple_body, sizeof(apple_body) - 1);
        } else if (mem_contains(request, (u32)received, "/connecttest.txt")) {
            write_all((int)client, microsoft_header, sizeof(microsoft_header) - 1);
            write_all((int)client, microsoft_body, sizeof(microsoft_body) - 1);
        } else if (mem_contains(request, (u32)received, "/ncsi.txt")) {
            write_all((int)client, ncsi_header, sizeof(ncsi_header) - 1);
            write_all((int)client, ncsi_body, sizeof(ncsi_body) - 1);
        } else {
            write_all((int)client, default_header, sizeof(default_header) - 1);
            write_all((int)client, default_body, sizeof(default_body) - 1);
        }
    }

    sys_call1(NR_close, client);
}

/* main starts DNS/HTTP listeners and services both sockets using poll(). */
int main(int argc, char **argv)
{
    struct pollfd descriptors[2];
    u32 service_ip;
    int dns_fd;
    int http_fd;

    if (argc != 2 || !parse_ipv4(argv[1], &service_ip)) {
        return 2;
    }

    dns_fd = open_bound_socket(SOCK_DGRAM, 53);
    if (dns_fd < 0) {
        return 3;
    }

    http_fd = open_bound_socket(SOCK_STREAM, 80);
    if (http_fd < 0) {
        sys_call1(NR_close, dns_fd);
        return 4;
    }

    {
        long listen_result = sys_call2(NR_listen, http_fd, 8);
        if (listen_result < 0) {
            sys_call1(NR_close, http_fd);
            sys_call1(NR_close, dns_fd);
            return 100 + (int)(-listen_result);
        }
    }

    descriptors[0].fd = dns_fd;
    descriptors[0].events = POLLIN;
    descriptors[0].revents = 0;
    descriptors[1].fd = http_fd;
    descriptors[1].events = POLLIN;
    descriptors[1].revents = 0;

    while (1) {
        long ready = sys_call3(NR_poll, (long)descriptors, 2, -1);

        if (ready <= 0) {
            continue;
        }

        if (descriptors[0].revents & POLLIN) {
            handle_dns(dns_fd, service_ip);
        }

        if (descriptors[1].revents & POLLIN) {
            handle_http(http_fd);
        }

        descriptors[0].revents = 0;
        descriptors[1].revents = 0;
    }

    return 0;
}
