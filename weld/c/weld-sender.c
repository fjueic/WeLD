#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <widget_name> <event_name>\n", argv[0]);
        return 1;
    }

    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock == -1) {
        perror("socket");
        return 1;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, "/tmp/weld.sock", sizeof(addr.sun_path) - 1);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("connect");
        close(sock);
        return 1;
    }

    char msg[256];
    snprintf(
        msg, sizeof(msg),
        "{\"action\": \"send\", \"widget\": \"%s\", \"bind_event\": \"%s\"}",
        argv[1], argv[2]);

    if (send(sock, msg, strlen(msg), 0) == -1) {
        perror("send");
        close(sock);
        return 1;
    }

    char buffer[1024];
    if (recv(sock, buffer, sizeof(buffer) - 1, 0) == -1) {
        perror("recv");
    }
    close(sock);
    return 0;
}
