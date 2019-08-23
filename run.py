#! /usr/bin/python3

import sys
import signal

import server


def signal_handler(_, __):
    print("Shutting down")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: {cmd} filename".format(cmd=sys.argv[0]))
        sys.exit()

    port = 10322
    host = '127.0.0.1'
    file = sys.argv[1]

    server.Server(host, port, file).listen()
