import socket
import sys


class Receiver():
    def __init__(self):
        pass

    def listen_and_return(self):
        pass

    def run(self):
        receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class Transmitter():
    def __init__(self):
        pass

    def run(self):
        pass


class Relay():
    def __init__(self):
        pass

    def run(self):
        pass


def print_help_menu():
    pass


if __name__ == '__main__':
    min_arg_length = 2
    print len(sys.argv)

    if sys.argv[1] == "--receive":
        receive = Receiver()
        receive.run()

    elif sys.argv[2] == "--transmit":
        transmit = Transmitter()
        transmit.run()

    elif sys.argv[3] == "--relay":
        relay = Relay()
        relay.run()

    else:
        print_help_menu()
