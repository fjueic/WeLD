#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        return 1;
    }

    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock == -1) {
        return 1;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, "/tmp/weld.sock", sizeof(addr.sun_path) - 1);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        close(sock);
        return 1;
    }

    char msg[256];
    snprintf(
        msg, sizeof(msg),
        "{\"action\": \"send\", \"widget\": \"%s\", \"bind_event\": \"%s\"}",
        argv[1], argv[2]);

    send(sock, msg, strlen(msg), 0);
    close(sock);

    return 0;
}
