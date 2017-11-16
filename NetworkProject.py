import socket
import sys


class DeviceMappingRelay:
    def __init__(self):
        self.connected_transmitters = {}
        self.connected_receivers = []
        self.host_to_receiver_index = 2

    def add_transmitter(self, host, port):
        if host in self.connected_transmitters.keys():
            if port in self.connected_transmitters[host].keys():
                pass
            else:
                self.connected_transmitters[host][port] = []
        else:
            self.connected_transmitters[host] = {}
            self.connected_transmitters[host][port] = {}

    def add_receiver_subscription(self, host, port, receiver_index):
        self.connected_transmitters[host][port].append(self.connected_receivers[receiver_index])

    def remove_receiver_subscription(self, host, port, receiver_index):
        if self.connected_receivers[receiver_index] in self.connected_transmitters[host][port]:
            self.connected_receivers[host][port].remove(self.connected_receivers[receiver_index])


class Receiver:
    def __init__(self, ip, port):
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.continue_listening = False
        self.mapping = [] # Holds the current list of connected devices

        self.ip = ip
        self.port = port

    def listen_and_return(self):
        pass

    def run(self):
        self.continue_listening = True
        self.receive_socket.bind((self.ip, self.port))
        self.receive_socket.listen(5)
        print "Socket listening"
        while self.continue_listening:
            c, addr = self.receive_socket.accept()
            print "Got a connection from " + addr
            print self.receive_socket.recv(2048)


class Transmitter:
    def __init__(self):
        self.transmit_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.continue_running = False

    def run(self):
        self.continue_running = True

        while self.continue_running:
            self.print_menu()
            user_input = raw_input("Command: ")

    def print_menu(self):
        print "Enter: "
        print "\tConnect: c [IP:port]"
        print "\tPush Connection: p"
        print "\tTransmit Message: [message]"
        print "\tTransmit File: [filename]"


class Relay():
    def __init__(self):
        pass

    def run(self):
        pass


def print_help_menu():
    print "Help Menu"
    print "\t--receive [host] [port]"
    print "\t--relay [host] [port]"


if __name__ == '__main__':
    min_arg_length = 2

    if sys.argv[1] == "--receive":
        if len(sys.argv) < 4:
            print_help_menu()
        else:
            receive = Receiver(sys.argv[2], int(sys.argv[3]))
            receive.run()

    elif sys.argv[1] == "--transmit":
        transmit = Transmitter()
        transmit.run()

    elif sys.argv[1] == "--relay":
        relay = Relay()
        relay.run()

    else:
        print_help_menu()
