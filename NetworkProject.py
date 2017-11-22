import Queue
import socket
import sys
import threading
from math import ceil
from textwrap import wrap


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


class RelaySender(threading.Thread):
    def __init__(self, sending_queue):
        threading.Thread.__init__(self)
        self.sending_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sending_queue = sending_queue
        self.continue_running = False

    def run(self):
        self.continue_running = True
        while self.continue_running:
            if self.sending_queue.qsize() > 0:
                item = self.sending_queue.get()
                self.sending_socket.connect(item[0])
                self.sending_socket.send(item[1])
                self.sending_socket.close()

class MessageSender(threading.Thread):
    def __init__(self, send_queue):
        threading.Thread.__init__(self)
        self.send_queue = send_queue
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.continue_running = False

    def run(self):
        self.continue_running = True

        while self.continue_running:
            if self.send_queue.qsize() > 0:
                data = self.send_queue.get()
                addr = data[0]
                bytes = data[1]
                partitions = wrap(bytes, 1024)

                self.send_socket.connect(addr)
                for i in partitions[0:len(partitions)-1]:
                    self.send_socket.send("1" + i)
                self.send_socket.send("0"+partitions[len(partitions)-1])
                self.send_socket.recv(1)
                self.send_socket.close()


# Receives packets for the relay device and places in queue
class MessageReceiver(threading.Thread):
    def __init__(self, ip, port, receive_queue):
        threading.Thread.__init__(self)
        self.receive_queue = receive_queue
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receive_socket.bind((ip, port))
        self.continue_running = False

    def run(self):
        self.continue_running = True

        self.receive_socket.listen(5)

        while self.continue_running:
            print "Receiving connection..."
            conn, addr = self.receive_socket.accept()
            print "Received connection"

            still_sending = True

            data = ""
            while still_sending:
                new_segment = conn.recv(1025)
                print "Received " + new_segment + " in total"
                data = data + new_segment[1:len(new_segment)]
                print new_segment[0]
                if new_segment[0] == '0':
                    conn.send('1', 1)
                    print "Sent ending response"
                    conn.close()
                    q.put(data)
                    still_sending = False


class Relay:
    def __init__(self, ip, port):
        self.mapping = DeviceMappingRelay()
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.send_queue = Queue.Queue()
        self.sender = RelaySender(self.send_queue)
        self.receive_queue = Queue.Queue()
        self.receiver = MessageReceiver(ip, port, self.receive_queue)

        self.sender.run()
        self.receiver.run()

        self.continue_running = False

    def run(self):
        self.continue_running = True

        while self.continue_running:
            if self.receive_queue.qsize() > 0:
                # Interpret the message sent
                pass
            else:
                threading._sleep(.2) # Sleep for .2 seconds if no activity

            pass


class Receiver:
    def __init__(self, ip, port):
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.continue_listening = False

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


def print_help_menu():
    print "Help Menu"
    print "\t--receive [host] [port]"
    print "\t--relay [host] [port]"


if __name__ == '__main__':
    # min_arg_length = 2
    #
    # if sys.argv[1] == "--receive":
    #     if len(sys.argv) < 4:
    #         print_help_menu()
    #     else:
    #         receive = Receiver(sys.argv[2], int(sys.argv[3]))
    #         receive.run()
    #
    # elif sys.argv[1] == "--transmit":
    #     if len(sys.argv) < 4:
    #         print_help_menu()
    #     else:
    #         transmit = Transmitter()
    #         transmit.run()
    #
    # elif sys.argv[1] == "--relay":
    #     if len(sys.argv) < 4:
    #         print_help_menu()
    #     else:
    #         relay = Relay(sys.argv[2], int(sys.argv[3]))
    #         relay.run()
    #
    # else:
    #     print_help_menu()
    q = Queue.Queue()
    r = MessageReceiver('127.0.0.1', 12002, q)

    r.start()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.connect(('127.0.0.1', 12002))

    print s.recv(1)
    s.close()
    print "Done"
    print q.qsize()
    f = q.get()
    print f.size()



