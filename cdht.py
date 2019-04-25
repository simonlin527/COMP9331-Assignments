import sys
import threading
import time
import socket
import datetime


class wait_for_input(threading.Thread):

    def __init__(self):
        super(wait_for_input, self).__init__()
        self._stop_event = threading.Event()
        self.setDaemon(False)

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        global peer_id, successor, sec_successor, predecessor, pre_pre
        while True:
            cmd = input().lower().strip()
            if cmd == 'quit':
                self.stop()
                quit()
            else:
                cmd = cmd.split(' ')
                #  shit ton of functions (actually there are only 3)
                if cmd[0] == 'request':
                    cycle = 0
                    found_flag = 0
                    if hash_name(cmd[1]) <= peer_id:
                        cycle = 1
                    if peer_id > successor and hash_name(cmd[1]) > peer_id:
                    	found_flag = 1
                    msg = f'REQUEST_FILE {cmd[1]} {peer_id} {found_flag} {cycle}'
                    send_TCP_message(int(successor)+50000, msg.encode())
                    print(f'File request message for {cmd[1]} has been sent to my successor.')
                elif cmd[0] == 'test':
                    print (f'id: {peer_id}, succ: {successor}, sec_succ: {sec_successor}, pre: {predecessor}, pre_pre: {pre_pre}')
                else:
                    print('Incorrect cmd you noob')
                    pass  # shit loads of functions


class ping_request(threading.Thread):
    def __init__(self):
        super(ping_request, self).__init__()
        self.setDaemon(True)

    def run(self):
        global peer_id, successor, sec_successor, predecessor, pre_pre, succ_seq, sec_succ_seq, succ_seq_t, sec_succ_seq_t
        p_succ, p_sec_succ =successor, sec_successor
        while True:
            # determine if successor has changed, meaning sequence resetes with 0
            if p_succ != successor:
                p_succ, succ_seq = successor, 0
            # detec packet loss
            if succ_seq_t[0]-succ_seq_t[1] >= 5:
                # reset sequence first, otherwise another packet loss even will be triggered
                succ_seq_t, sec_succ_seq_t = [0, 0], [0, 0]
                print(f'Peer {successor} is no longer alive')
                successor = sec_successor
                print(f'Peer {successor} is now my first successor')
                send_TCP_message(50000+successor, f'GET_SUCC {peer_id} SEC_SUCC'.encode())
            if sec_succ_seq_t[0]-sec_succ_seq_t[1] >= 7:
                # reset sequence first, otherwise another packet loss even will be triggered
                succ_seq_t = [0, 0]
                print(f'Peer {sec_successor} is no longer alive')
                send_TCP_message(50000+successor, f'GET_SUCC {peer_id} SEC_SUCC'.encode())
            # ping successor
            time.sleep(0.05)
            send_UDP_message(successor+50000, f'PING {peer_id} succ {succ_seq}')
            succ_seq_t[0] = succ_seq
            succ_seq += 1
            print(f'Ping request sent to {successor} at {str(datetime.datetime.now().time())}')
            time.sleep(10)
            # determine if sec_succ has changed, reset sequence if true
            if p_sec_succ != sec_successor:
                p_sec_succ, sec_succ_seq = sec_successor, 0
            # ping sec_successor after 10 secs to avoid traffic jam at port
            send_UDP_message(sec_successor+50000, f'PING {peer_id} sec_succ {sec_succ_seq}')
            sec_succ_seq_t[0] = sec_succ_seq
            sec_succ_seq += 1
            print(f'Ping request sent to {sec_successor} at {str(datetime.datetime.now().time())}')
            time.sleep(10)


class ping_response(threading.Thread):

    def __init__(self):
        super(ping_response, self).__init__()
        self.setDaemon(True)

    def run(self):
        global peer_id, successor, sec_successor, predecessor, pre_pre, succ_seq_t, sec_succ_seq_t
        flags = {}
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(180)
        sock.bind(('localhost', peer_id+50000))

        while True:
            # Listen for incoming messages on 50000+self.id socket for 60 seconds
            try:
                data, server = sock.recvfrom(2048)
                data_handler = threading.Thread(target=response_UDP, args=(data, flags, succ_seq_t, sec_succ_seq_t))
                data_handler.start()  
            except socket.timeout:
                print('Did not receive data for 180 secs')
                # This should only happen if both peers are killed at the same time
                # Will not be tested
            

class TCP_listen(threading.Thread):
    def __init__(self):
        super(TCP_listen, self).__init__()
        self.setDaemon(True)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', peer_id+50000))
        sock.listen(5)

        # Listen to TCP messages
        while True:
            client_sock, address = sock.accept()
            # Open a new thread for receiving messages, hopefully it does not explode
            client_handler = threading.Thread(target=response_TCP, args=(client_sock,))
            client_handler.start()


def response_UDP(data, flags, succ_seq_t, sec_succ_seq_t):
    global predecessor, pre_pre, successor, sec_successor
    # open thread for each message
    # Q: How to keep track of timeout time/predecessor? Probably globals or pass dict/list by reference
    # Decide what to do according to accumulated messages
    data = data.decode()
    data = data.split(' ')
    # if message is a ping request from a predecessor
    if data[0] == 'PING':
        # [0] = PING, [1] = peer_id, [2] = succ or sec_succ, [3] = seq_num
        print(f'Received PING request from: {data[1]} at {str(datetime.datetime.now().time())}')
        # Store predecessors
        if data[2] == 'succ':
            predecessor = int(data[1])
        elif data[2] == 'sec_succ':
            pre_pre = int(data[1])
        # send PING_ACK for every ping received cos sometimes it gets lost in time and space
        send_UDP_message(int(data[1]) + 50000, f'PING_ACK {peer_id} {data[1]} {data[2]} {data[3]}')
    # elif data received is a ping_ack from one of the successors
    elif data[0] == 'PING_ACK':
        # [0] = PING, [1] = peer_id, [2] = pre, [3] = succ or sec_succ, [4] = seq_num
        flags[data[1]] = datetime.datetime.now()
        if data[3] == 'succ':
            succ_seq_t[1] = int(data[4])
        elif data[3] == 'sec_succ':
            sec_succ_seq_t[1] = int(data[4])
        print(f'Received PING_ACK from: {data[1]} at {str(datetime.datetime.now().time())}')
    # see if predecessors have changed
    if len(flags) > 2:
        flags.clear()
        succ_seq_t, sec_succ_seq_t = [0, 0], [0, 0]
    # detect time out
    for key, values in flags.items():
        if (datetime.datetime.now() - values).total_seconds() > 180:
            print(f'Have not received a PING_ACK from {key} in over 180 seconds')
    # need to find new successor


def send_UDP_message(port, msg):  # Takes a pot number, and a string
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', port)
    sock.sendto(msg.encode(), server_address)


def hash_name(name):  # Takes a string, returns an int
    return int(name) % 256


def send_TCP_message(port, encoded_msg):  # Takes a port number and an enconded
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', port))
    sock.send(encoded_msg)
    # response = sock.recv(4096)
    sock.close()
    # print(response)


def response_TCP(client_socket):
    global peer_id, successor, sec_successor, predecessor, pre_pre
    request = client_socket.recv(1024).decode()
    message = request.split(' ')
    if message[0] == 'ACK':
        pass  # No need to do anything on ACK
    elif message[0] == 'REQUEST_FILE':  # see if file is here 
        # message[0] = type, [1] = file_name, [2] = request source, [3] = found_flag, [4] = send_to_cycle
        # found_flag is to determine if file is found after passing through cycle
        # sent_to_cycle is used to determine if request needs to be send around the whole cycle
        name, source, found_flag, cycle = int(message[1]), int(message[2]), int(message[3]), int(message[4])
        if cycle == 1:  # need to send to end
            if successor > peer_id:  # send to next peer
                print(f'File {name} is not stored here')
                send_TCP_message(50000+successor, request.encode())
                print(f'File request message has been forwarded to my successor {successor}')
            else: # Last link of cycle, send and continue as normal
                print(f'File {name} is not stored here')
                message[4] = '0'
                send_TCP_message(50000+successor, ' '.join(message).encode())
                print(f'File request message has been forwarded to my successor {successor}')
        else: # not a cycle, proceed as normal
            if found_flag != 1:
                if peer_id < successor:  # Not a cycle
                    if hash_name(name) > peer_id:  # send to next succ peer
                        print(f'File {name} is not stored here')
                        send_TCP_message(50000+successor, request.encode())
                        print(f'File request message has been forwarded to my successor {successor}')
                    elif hash_name(name) <= peer_id and hash_name(name) < successor:
                        # send TCP back to where the file came from
                        print(f'FOUND {name} BOYS')
                        print(f'A response message, destined for peer {source}, has been sent')
                        send_TCP_message(50000+source, f'RESPONSE {peer_id} {name}'.encode())
                else:  # End of cycle, peer 15 to peer 1 
                    if hash_name(name) <= peer_id:  # It's a cycle but the file is here
                        print(f'FOUND FILE {name} BOYS')
                        print(f'A response message, destined for peer {source}, has been sent')
                        send_TCP_message(50000+source, f'RESPONSE {peer_id} {name}'.encode())
                    else:  
                        print(f'File {name} is not stored here')
                        message[3] = 1
                        request = ' '.join(str(m) for m in message)
                        send_TCP_message(50000+successor, request.encode())
                        print(f'File request message has been forwarded to my successor {successor}')
            else: # found_flag is 1
                # send TCP back to where the file came from
                print(f'FOUND {name} BOYS')
                print(f'A response message, destined for peer {source}, has been sent')
                send_TCP_message(50000+source, f'RESPONSE {peer_id} {name}'.encode())
    elif message[0] == 'RESPONSE':  # response message of file request
        print(f'Received a response message from peer {message[1]}, which has the file {message[2]}')
    elif message[0] == 'QUIT':  # peer is departing and informs peer of new successors
        # [1] = PRE or PRE_PRE, [2] = peer_id, [3] = successor, [4] = sec_successor
        print(f'Peer {message[2]} will depart from the network')
        if message[1] == 'PRE':
            successor = int(message[3])
            sec_successor = int(message[4])
        elif message[1] == 'PRE_PRE':
            sec_successor = int(message[3])
        print(f'My first successor is now {successor}')
        print(f'My second successor is now {sec_successor}')
    elif message[0] == 'GET_SUCC':
        send_TCP_message(50000+int(message[1]), f'NEW_SUCC {successor} {message[2]}'.encode())
    elif message[0] == 'GET_SEC_SUCC':
        send_TCP_message(50000+int(message[1]), f'NEW_SEC_SUCC {sec_successor} {message[2]}'.encode())
    elif message[0] == 'NEW_SUCC':
        if message[2] == 'SEC_SUCC':
            sec_successor = int(message[1])
            print(f'My second successor is now {sec_successor}')

    client_socket.close()


if __name__ == '__main__':
    peer_id = int(sys.argv[1])
    successor = int(sys.argv[2])
    sec_successor = int(sys.argv[3])
    predecessor = -1
    pre_pre = -1
    succ_seq, sec_succ_seq = 0, 0
    succ_seq_t, sec_succ_seq_t = [0, 0], [0, 0]
    print(f'peer: {peer_id}, succ:{successor}, sec_succ:{sec_successor}')
    # Thread initialisations
    # ping threads
    input_thread = wait_for_input()
    ping_thread = ping_request()
    response_thread = ping_response()
    # TCP threads
    tcp_listen_thread = TCP_listen()
    # Starting all threads
    input_thread.start()
    ping_thread.start()
    response_thread.start()
    tcp_listen_thread.start()
    # Waiting for input thread to end on 'quit' command
    input_thread.join()
    # send message to predecessor
    send_TCP_message(50000+predecessor, f'QUIT PRE {peer_id} {successor} {sec_successor}'.encode())
    send_TCP_message(50000+pre_pre, f'QUIT PRE_PRE {peer_id} {successor} {sec_successor}'.encode())
    exit()
