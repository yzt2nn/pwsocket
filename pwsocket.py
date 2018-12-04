#####################
# PWSocket
# Author: yzt
# License: MIT
#####################

import socket, hashlib, base64, struct


class WebSocket():
    class Error(Exception):
        def __str__(self):
            return '[Error]' + self.message

    class ConnectionFailureError(Error):
        def __init__(self):
            self.message = 'Websocket connection Failure happened.'

    class ConnectionClosedError(Error):
        def __init__(self):
            self.message = 'Websocket Connection was closed.'

    class ReceiveOutOfRangeError(Error):
        def __init__(self):
            self.message = 'Received a message out of range.'

    class ClientMessageWithoutMaskError(Error):
        def __init__(self):
            self.message = 'Client message without mask.'

    class RequestIsNotForWebsocketError(Error):
        def __init__(self):
            self.message = 'Request is not for websocket.'

    def __init__(self, host, port=80, bufsize=4096, timeout=0, conn_timeout=0):
        self.host = host
        self.port = port
        self.bufsize = bufsize
        self.client = None
        self.client_addr = None
        self.timeout = timeout
        self.conn_timeout = conn_timeout
        self.onreceive = None
        self.headers = None

    def is_closed(self):
        closed = getattr(self.client, '_closed', False)
        return closed

    def get_server_key(self, client_key):
        magic_string = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        server_key =  base64.b64encode(hashlib.sha1((client_key + magic_string).encode('utf-8')).digest()).decode('utf-8')
        return server_key

    def parse_header(self, b_rev):
        headers = {}
        r_str = b_rev.decode('utf-8')
        s0 = r_str.split('\r\n')
        s1 = s0[0].split(' ')
        headers['Method'] = s1[0]
        headers['Url'] = s1[1]
        headers['Protocol'] = s1[2]
        for kv in s0[1:]:
            if kv:
                s2 = kv.split(': ')
                headers[s2[0]] = s2[1]
        self.headers = headers
        return self.headers

    def is_websocket(self):
        if 'Upgrade' in self.headers['Connection'] and self.headers['Upgrade'] == 'websocket':
            return True
        return False

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
        total = len(revmsg)
        fin = revmsg[0] >> 7
        opcode = revmsg[0] & 0xF

        if opcode == 0x08:
            self.close()
            return
        has_mask = revmsg[1] >> 7
        if not has_mask:
            self.client.close()
            raise WebSocket.ClientMessageWithoutMaskError()
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
        remain = total - mask_end
        if data_length > remain:
            raise WebSocket.ReceiveOutOfRangeError()
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
        while True:
            try:
                self.client, self.client_addr = s.accept()
            except socket.timeout:
                s.close()
                raise WebSocket.ConnectionFailureError()
            if self.timeout > 0:
                self.client.settimeout(self.timeout)
            r = self.client.recv(1024)
            if not r:
                self.client.close()
                continue
            else:
                try:
                    self.parse_header(r)
                except:
                    continue
                if self.is_websocket():
                    client_key = self.headers.get('Sec-WebSocket-Key', None)
                    if client_key:
                        server_key = self.get_server_key(client_key)
                        msg = self.build_websocket_header_resp(server_key)
                        self.client.sendall(msg)
                        s.close()
                        break
                self.client.close()

    def receive(self):
        if self.is_closed():
            raise WebSocket.ConnectionClosedError()
        b_msg = self.client.recv(self.bufsize)
        try:
            msg = self.parse_client_msg(b_msg)
        except WebSocket.ClientMessageWithoutMaskError as e:
            self.close()
            raise e
        else:
            if self.onreceive and not self.is_closed():
                self.onreceive(self, msg)
            return msg

    def send(self, msg):
        if self.is_closed():
            raise WebSocket.ConnectionClosedError()
        b_msg = self.build_server_to_client_msg(msg)
        self.client.sendall(b_msg)

    def close(self):
        if self.client and not self.is_closed():
            try:
                self.client.send(self.build_server_to_client_msg('', opcode=8))
            except:
                pass
            finally:
                self.client.close()