import Queue
import socket
import sys
import threading
from textwrap import wrap
import time
import uuid


class DeviceMappingRelay:
    def __init__(self):
        self.connected_transmitters = {}
        self.connected_receivers = {}

    def add_transmitter(self, id):
        if id in self.connected_transmitters.keys():
            pass
        else:
            self.connected_transmitters[id] = []

    def add_receiver(self, id, host, port):
        if id in self.connected_receivers.keys():
            return False
        else:
            self.connected_receivers[id] = (host, port)
            return True

    def remove_receiver(self, id):
        if id in self.connected_receivers.keys():
            return False
        else:
            self.connected_receivers.pop(id)
            return True

    def remove_transmitter(self, id):
        if id in self.connected_transmitters.keys():
            self.connected_transmitters.pop(id, 0)
            return True
        else:
            return False

    def add_receiver_subscription(self, transmitter_id, receiver_id):
        if receiver_id in self.connected_receivers.keys():
            self.connected_transmitters[transmitter_id].append(receiver_id)
            return True
        else:
            return False

    def get_receiver_addrs_transmitter(self, transmitter_id):
        if transmitter_id in self.connected_transmitters.keys():
            return [self.connected_receivers[i] for i in self.connected_transmitters[transmitter_id]]
        else:
            return []

    def remove_receiver_subscription(self, transmitter_id, receiver_id):
        if receiver_id in self.connected_transmitters[transmitter_id]:
            self.connected_transmitters[transmitter_id].remove(receiver_id)

    def get_id_by_index(self, index):
        ids = self.connected_receivers.keys()
        return ids[index]

    def __str__(self):
        if len(self.connected_receivers.keys()) == 0:
            return "Current receivers subscribed: None"
        else:
            string = "Current receivers subscribed...:"
            for i in enumerate(self.connected_receivers.keys()):
                string += str(i[0]) + \
                        "\t" + str(i[1]) + \
                        "\t" + str(self.connected_receivers[i[1]]) + \
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

        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receive_socket.bind((ip, port))

        self.sender.start()

        self.continue_running = False

    def run(self):
        self.continue_running = True
        self.receive_socket.listen(5)
        while self.continue_running:
            conn, addr = self.receive_socket.accept()
            print "Accepted from " + str(addr)
            t = threading.Thread(target=self.handle_connection, args=(conn,addr))
            t.start()

    def handle_connection(self, conn, addr):
        still_sending = True

        data = ""
        while still_sending:
            new_segment = conn.recv(1025)
            data = data + new_segment[1:len(new_segment)]
            if new_segment[0] == '0':
                still_sending = False

        char = data[32]

        print data
        if char == 'E':
            addr_string = data[33:len(data)]
            ip, port_string = addr_string.split(":")
            self.mapping.add_receiver(data[0:32], ip, int(port_string))
            conn.send('E')

        if char == 'L':
            self.mapping.remove_receiver(data[0:32])

        if char == 'v':
            conn.send(str(self.mapping))

        if char == 'p':
            id = data[0:32]
            index = int(data[33:len(data)])
            self.mapping.add_receiver_subscription(id, self.mapping.get_id_by_index(index))

        if char == 'c':
            id = data[0:32]
            self.mapping.add_transmitter(id)
            conn.send('c')
            conn.close()

        if char == 'm':
            id = data[0:32]
            to_send = data[32:len(data)]
            for i in self.mapping.get_receiver_addrs_transmitter(id):
                self.send_queue.put((i, id + to_send))

        if char == 'f':
            id = data[0:32]
            to_send = data
            for i in self.mapping.get_receiver_addrs_transmitter(id):
                self.send_queue.put((i, to_send))

        if char == 'r':
            id = data[0:32]
            index = int(data[33:len(data)])
            self.mapping.remove_receiver_subscription(id, self.mapping.get_id_by_index(index))


class Receiver:
    def __init__(self, ip, port):
        self.receive_queue = Queue.Queue()
        self.receiver = MessageReceiver(ip, port, self.receive_queue)

        self.ip = ip
        self.port = port

        self.continue_listening = False

        self.receiver.start()
        self.id = uuid.uuid1()

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

                print data

                if data[32] == 'f':
                    print "Received f"
                    title_length = int(data[33:35])
                    print title_length
                    with open(data[35:35+title_length], 'wb') as f:
                        f.write(data[35+title_length:len(data)])

                if data[32] == 'm':
                    id = data[0:32]
                    print "From: " + id
                    print "\t" + str(data[33:len(data)])

    def connect(self, ip, port):
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.connect((ip, port))
        connection_socket.send("0" + str(self.id.get_hex()) + 'E' + self.ip + ":" + str(self.port))
        connection_socket.recv(1)
        connection_socket.close()
        print "Connected"


class Transmitter:
    def __init__(self, ip, port):
        self.continue_running = False

        self.send_ip = None
        self.send_port = None
        self.id = uuid.uuid1()

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
                data = str(self.id.get_hex()) + 'c'

            if user_input == "v":
                data = str(self.id.get_hex()) + 'v'

            if user_input[0] == "f":
                data = str(self.id.get_hex()) + self.get_file_string(user_input[2:len(user_input)])

            if user_input[0] == 'm':
                data = str(self.id.get_hex()) + 'm' + user_input[2:len(user_input)]

            if user_input[0] == 'p':
                data = str(self.id.get_hex()) + 'p' + user_input[2:len(user_input)]

            if user_input[0] == 'r':
                data = str(self.id.get_hex()) + 'r' + user_input[2:len(user_input)]


            # Send the message
            send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            partitions = wrap(data, 1024)
            send_socket.connect((self.send_ip, self.send_port))
            for i in partitions[0:len(partitions) - 1]:
                send_socket.send("1" + i)
            send_socket.send("0" + partitions[len(partitions) - 1])

            if user_input == 'v':
                message = send_socket.recv(2048)
                send_socket.close()
                splitstr = message.split(":")
                for i in splitstr:
                    print i

            if user_input[0] == "c":
                send_socket.recv(1)
                send_socket.close()

    def get_file_string(self, filename):
        with open(filename, 'rb') as f:
            string = f.read()
            if len(str(len(filename))) != 2:
                file_string = 'f0' + str(len(filename)) + filename + string
            else:
                file_string = 'f' + str(len(filename)) + filename + string
        return file_string

    def print_menu(self):
        print "Enter: "
        print "\tConnect:\t\tc [IP:port]"
        print "\tPush Connection:\tp [connection number]"
        print "\tRemove Connection:\tr [connection number]"
        print "\tTransmit Message:\tm [message]"
        print "\tTransmit File:\t\tf [filename]"
        print "\tQuit:\t\t\tq"


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

    for i in enumerate(d):
        print i