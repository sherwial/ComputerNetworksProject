import Queue
import socket
import sys
import threading
from textwrap import wrap
import time


class DeviceMappingRelay:
    def __init__(self):
        self.connected_transmitters = {}
        self.connected_receivers = []

    def add_transmitter(self, host, port):
        if host in self.connected_transmitters.keys():
            if port in self.connected_transmitters[host].keys():
                pass
            else:
                self.connected_transmitters[host][port] = []
        else:
            self.connected_transmitters[host] = {}
            self.connected_transmitters[host][port] = {}

    def add_receiver(self, ip, port):
        ind = self.get_receiver_index(ip, port)
        if ind == -1:
            self.connected_receivers.append((ip, port))
            return True
        else:
            return False

    def remove_receiver(self, ip, port):
        ind = self.get_receiver_index(ip, port)
        if ind == -1:
            return False
        else:
            del self.connected_receivers[ind]
            return True

    def add_receiver_subscription(self, host, port):
        ind = self.get_receiver_index(host, port)
        if ind == -1:
            return False
        else:
            self.connected_transmitters[host][port].append(self.connected_receivers[ind])
            return True

    def remove_receiver_subscription(self, host, port, receiver_index):
        if self.connected_receivers[receiver_index] in self.connected_transmitters[host][port]:
            self.connected_receivers[host][port].remove(self.connected_receivers[receiver_index])

    def get_receiver_index(self, ip, port):
        if (ip, port) in self.connected_receivers:
            return self.connected_receivers.index((ip, port))
        else:
            return -1

    def __str__(self):
        if len(self.connected_receivers) == 0:
            return "Current receivers subscribed: None"
        else:
            string = "Current receivers subscribed...:"
            for i in range(0, len(self.connected_receivers)):
                string += str(i) + "\r\t" + \
                          self.connected_receivers[i][0] + \
                          "\r\t" + str(self.connected_receivers[i][1]) + \
                          ":"
            return string


class MessageSender(threading.Thread):
    def __init__(self, send_queue):
        threading.Thread.__init__(self)
        self.send_queue = send_queue
        self.continue_running = False

    def run(self):
        self.continue_running = True

        while self.continue_running:

            if self.send_queue.qsize() > 0:
                send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data = self.send_queue.get()
                addr = data[0]
                bytes = data[1]
                partitions = wrap(bytes, 1024)

                send_socket.connect(addr)
                for i in partitions[0:len(partitions)-1]:
                    self.send_socket.send("1" + i)
                send_socket.send("0"+partitions[len(partitions)-1])
                send_socket.recv(1)
                send_socket.close()
            else:
                threading._sleep(.1)

    def stop(self):
        self.continue_running = False


# Receives packets for the relay device and places in queue
class MessageReceiver(threading.Thread):
    def __init__(self, ip, port, receive_queue):
        threading.Thread.__init__(self)
        self.receive_queue = receive_queue
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receive_socket.bind((ip, port))
        #self.receive_socket.settimeout(.5)
        self.continue_running = False

    def run(self):
        self.continue_running = True

        self.receive_socket.listen(5)

        while self.continue_running:
            try:
                conn, addr = self.receive_socket.accept()
                still_sending = True

                data = ""
                while still_sending:
                    new_segment = conn.recv(1025)
                    data = data + new_segment[1:len(new_segment)]
                    if new_segment[0] == '0':
                        conn.send('1', 1)
                        conn.close()
                        self.receive_queue.put((addr, data))
                        still_sending = False
            except socket.timeout:
                pass

    def stop(self):
        self.continue_running = False


class Relay:
    def __init__(self, ip, port):
        self.mapping = DeviceMappingRelay()

        self.send_queue = Queue.Queue()
        self.sender = MessageSender(self.send_queue)
        self.receive_queue = Queue.Queue()
        self.receiver = MessageReceiver(ip, port, self.receive_queue)

        self.sender.start()
        self.receiver.start()

        self.continue_running = False

    def run(self):
        self.continue_running = True

        while self.continue_running:
            if self.receive_queue.qsize() > 0:
                packet = self.receive_queue.get()
                addr = packet[0]
                data = packet[1]

                char = data[0]

                if char == 'E':
                    self.mapping.add_receiver(addr[0], addr[1])

                if char == 'L':
                    self.mapping.remove_receiver(addr[0], addr[1])

                if char == 'v':
                    # Send the string of available hosts back to the transmitter
                    string = data[1:len(data)]
                    ip, port_string = string.split(":")
                    self.send_queue.put(((ip, int(port_string)), str(self.mapping)))

                if char == 'p':
                    pass

                if char == 'c':
                    pass



            else:
                threading._sleep(.2) # Sleep for .2 seconds if no activity


class Receiver:
    def __init__(self, ip, port):
        self.receive_queue = Queue.Queue()
        self.receiver = MessageReceiver(ip, port, self.receive_queue)

        self.continue_listening = False

        self.receiver.start()

    def run(self):
        self.continue_listening = True
        input = raw_input("[ip,port] of relay: ")
        ip, port_string = input.split(":")
        self.connect(ip, int(port_string))

        while self.continue_listening:

            if self.receive_queue.qsize() != 0:
                packet = self.receive_queue.get()
                addr = packet[0]
                data = packet[1]

                if data[0] == 'f':
                    title_length = int(data[1:3])
                    with open(data[3:title_length+3]) as f:
                        f.write(data[title_length+3:len(data)])

                if packet[0] == 'm':
                    print "From: " + str(addr)
                    print "\t" + str(data[1:len(data)])

    def connect(self, ip, port):
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.connect((ip, port))
        connection_socket.send("0E")
        connection_socket.recv(1)
        connection_socket.close()


class Transmitter:
    def __init__(self, ip, port):
        self.send_queue = Queue.Queue()
        self.receiver_queue = Queue.Queue()

        self.sender = MessageSender(self.send_queue)

        self.receive_ip = ip
        self.receive_port = port

        self.receiver = MessageReceiver(ip, port, self.receiver_queue)
        self.receiver.start()
        self.sender.start()
        self.continue_running = False

        self.send_ip = None
        self.send_port = None

    def run(self):
        self.continue_running = True

        while self.continue_running:
            self.print_menu()
            user_input = raw_input("Command: ")

            if user_input[0] == "c":
                string = user_input[2:len(user_input)]
                ip, port_string = string.split(':')
                self.send_ip = ip
                self.send_port = int(port_string)
                self.send_queue.put(((self.send_ip, self.send_port), 'c'))

            if user_input == "v":
                self.send_queue.put(((self.send_ip, self.send_port), "v" + self.receive_ip + ":" + str(self.receive_port)))

                while self.receiver_queue.qsize() == 0:
                    pass
                print "\n"
                message = str(self.receiver_queue.get()[1])  # Print the data obtained from receiver
                splitstr = message.split(":")
                for i in splitstr:
                    print i

            if user_input == "f":
                filename = raw_input("Enter filename: ")
                self.send_file(filename)

            if user_input == 'm':
                string = raw_input("Enter message: ")
                self.send_message(string)

            if user_input == 'p':
                number = raw_input("Enter connection number to push")
                self.send_queue.put(((self.send_ip, self.send_port), int(number)))


    def send_file(self, filename):
        with open(filename, 'rb') as f:
            string = f.read()
            if len(str(len(filename))) != 2:
                self.send_queue.put('f0' + str(len(filename)) + filename + string)
            else:
                self.send_queue.put('f' + str(len(filename)) + filename + string)

    def send_message(self, message):
        self.send_queue.put('m' + message)

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
    min_arg_length = 2

    if sys.argv[1] == "--receive":
        if len(sys.argv) < 4:
            print_help_menu()
        else:
            receive = Receiver(sys.argv[2], int(sys.argv[3]))
            receive.run()

    elif sys.argv[1] == "--transmit":
        if len(sys.argv) < 4:
            print_help_menu()
        else:
            transmit = Transmitter(sys.argv[2], int(sys.argv[3]))
            transmit.run()

    elif sys.argv[1] == "--relay":
        if len(sys.argv) < 4:
            print_help_menu()
        else:
            relay = Relay(sys.argv[2], int(sys.argv[3]))
            relay.run()

    else:
        print_help_menu()
    # sq = Queue.Queue(0)
    # rq = Queue.Queue(0)
    # ms = MessageSender(sq)
    # mr = MessageReceiver("127.0.0.1", 19001, rq)
    #
    # ms.start()
    # mr.start()
    #
    # sq.put((("127.0.0.1", 19001),"asdasdasdasdas"))
    # sq.put((("127.0.0.1", 19001),"dfsdifunhsdkfjhgsd"))
    # sq.put((("127.0.0.1", 19001),"dsfsdfsdfsdfsdfs"))
