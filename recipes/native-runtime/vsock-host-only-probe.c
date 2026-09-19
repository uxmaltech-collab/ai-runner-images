/* Native negative probe for an owned, credential-free macOS rehearsal VM. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/vsock.h>
#include <unistd.h>

static int unknown(int fd, const char *phase) {
    int error = errno;
    if (fd >= 0) close(fd);
    printf("{\"status\":\"inconclusive\",\"phase\":\"%s\",\"errno\":%d}\n", phase, error);
    return 2;
}

int main(void) {
    if (geteuid() == 0) {
        puts("{\"status\":\"inconclusive\",\"phase\":\"nonadmin-user-required\"}");
        return 2;
    }
    int fd = socket(AF_VSOCK, SOCK_STREAM, 0);
    if (fd < 0) return unknown(fd, "socket");
    struct timeval timeout = {.tv_sec = 3, .tv_usec = 0};
    int no_sigpipe = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) ||
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) ||
        setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &no_sigpipe, sizeof(no_sigpipe)))
        return unknown(fd, "timeout");
    uint32_t cid;
    if (ioctl(fd, IOCTL_VM_SOCKETS_GET_LOCAL_CID, &cid)) return unknown(fd, "cid");
    if (cid == VMADDR_CID_HOST || cid == VMADDR_CID_HYPERVISOR || cid == VMADDR_CID_ANY) {
        errno = EINVAL;
        return unknown(fd, "unexpected-local-cid");
    }
    struct sockaddr_vm peer = {
        .svm_len = sizeof(peer), .svm_family = AF_VSOCK,
        .svm_reserved1 = 0, .svm_port = 8080, .svm_cid = cid
    };
    if (connect(fd, (struct sockaddr *)&peer, sizeof(peer))) return unknown(fd, "connect");
    static const unsigned char preface[] =
        "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
        "\x00\x00\x00\x04\x00\x00\x00\x00\x00";
    size_t sent = 0;
    while (sent < sizeof(preface) - 1) {
        ssize_t count = send(fd, preface + sent, sizeof(preface) - 1 - sent, 0);
        if (count < 0 && (errno == EPIPE || errno == ECONNRESET)) goto rejected;
        if (count <= 0) return unknown(fd, "send");
        sent += (size_t)count;
    }
    unsigned char response[9];
    ssize_t count = recv(fd, response, sizeof(response), 0);
    if (count == 0 || (count < 0 && errno == ECONNRESET)) goto rejected;
    if (count < 0) return unknown(fd, "receive");
    close(fd);
    printf("{\"status\":\"exposed\",\"uid\":%u,\"cid\":%u,\"response_bytes\":%zd}\n",
           (unsigned)geteuid(), cid, count);
    return 1;
rejected:
    close(fd);
    printf("{\"status\":\"rejected\",\"uid\":%u,\"cid\":%u}\n", (unsigned)geteuid(), cid);
    return 0;
}
