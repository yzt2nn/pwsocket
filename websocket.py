import socket, re, hashlib, base64, struct


class Error(Exception):
    def __str__(self):
        return '[Error]' + self.message

class ConnectionFailureError(Error):
    def __init__(self):
        self.message = 'Websocket connection Failure happened.'

class ConnectionClosedError(Error):
    def __init__(self):
        self.message = 'Websocket Connection was closed.'

class ReceiveMessageError(Error):
    def __init__(self):
        self.message = 'Received a wrong message.'

class ClientMessageWithoutMaskError(Error):
    def __init__(self):
        self.message = 'Client message without mask.'

class WebSocket():
    def __init__(self, host, port=80, bufsize=4096, timeout=0, conn_timeout=0):
        self.host = host
        self.port = port
        self.bufsize = bufsize
        self.client = None
        self.client_addr = None
        self.timeout = timeout
        self.conn_timeout = conn_timeout

    def is_closed(self):
        closed = getattr(self.client, '_closed', False)
        return closed

    def get_server_key(self, rev):
        magic_string = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        r_str = rev.decode('utf-8')
        client_key = re.search(r'(?<=Sec-WebSocket-Key: ).*(?=\r\n)', r_str).group()
        server_key =  base64.b64encode(hashlib.sha1((client_key + magic_string).encode('utf-8')).digest()).decode('utf-8')
        return server_key

    def build_websocket_header_resp(self, key):
        msg = "HTTP/1.1 101 Switching Protocols\r\n" \
        "Upgrade: websocket\r\n" \
        "Connection: Upgrade\r\n" \
        "Sec-WebSocket-Accept: " + key + "\r\n\r\n"
        return msg.encode('utf-8')

    def build_server_to_client_msg(self, msg, opcode=1):
        predata = bytes([0x80 + opcode]) #Fin=1 opcode=1
        b_msg = msg.encode('utf-8')
        length = len(b_msg)
        if length < 126:
            predata += struct.pack('B', length)
        elif length <= 0xFFFF:
            predata += struct.pack('!BH', 126, length)
        else:
            predata += struct.pack('!BQ', 127, length)
        b_resp = predata + b_msg
        return b_resp

    def parse_client_msg(self, revmsg):
        global cl
        fin = revmsg[0] >> 7
        opcode = revmsg[0] & 0xF

        if opcode == 0x08:
            self.client.close()
            return
        has_mask = revmsg[1] >> 7
        if not has_mask:
            raise ClientMessageWithoutMaskError()
        payloadlen = revmsg[1] & 0x7F
        start = 2
        if payloadlen < 126:
            data_length = payloadlen
        elif payloadlen == 126:
            start = 4
            data_length = struct.unpack('!H', revmsg[2:4])[0]
        else:
            start = 10
            data_length = struct.unpack('!Q', revmsg[2:10])[0]
        mask_end = start + 4
        mask = revmsg[start:mask_end]
        raw_msg = revmsg[mask_end:mask_end + data_length]
        real_msg = bytes([(b ^ mask[i%4]) for i, b in enumerate(raw_msg)])

        return real_msg.decode('utf-8')

    def accept(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(1)
        if self.conn_timeout > 0:
            s.settimeout(self.conn_timeout)
        try:
            self.client, self.client_addr = s.accept()
        except socket.timeout:
            raise ConnectionFailureError()
        finally:
            s.close()
        if self.timeout > 0:
            self.client.settimeout(self.timeout)
        r = self.client.recv(1024)
        if not r:
            raise ConnectionFailureError()
        else:
            server_key = self.get_server_key(r)
            msg = self.build_websocket_header_resp(server_key)
            self.client.sendall(msg)
            while True:
                print(self.is_closed())
                if self.is_closed():
                    break
                print(self.receive())
                import time
                time.sleep(1)
                self.send('ok!!')

    def receive(self):
        if self.is_closed():
            raise ConnectionClosedError()
        b_msg = self.client.recv(self.bufsize)
        try:
            msg = self.parse_client_msg(b_msg)
        except ClientMessageWithoutMaskError as e:
            self.close()
            raise e
        else:
            return msg

    def send(self, msg):
        if self.is_closed():
            raise ConnectionClosedError()
        b_msg = self.build_server_to_client_msg(msg)
        self.client.sendall(b_msg)

    def close(self):
        if self.client:
            self.client.send(self.build_server_to_client_msg('', opcode=8))
            self.client.close()


ws = WebSocket('127.0.0.1', timeout=10)
ws.accept()
#print(ClientMessageWithoutMaskError())
# print(parse_msg(b'\x81\x83KK\x92\x8fzy\xa1'))
# print(parse_msg(b'\x81\x90\xb7mp\xa7\xd1\t\x1a\xcc\x86^BB\x12\xd0\x9567_C\x94'))