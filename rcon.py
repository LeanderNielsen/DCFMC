import socket
import struct

class RCON:
    def __init__(self, host, password, port=25575):
        self.host = host
        self.password = password
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        # Opret TCP forbindelse og autentificer med password
        self.socket.connect((self.host, self.port))
        self._send(3, self.password)  # Type 3 = login pakke

    def command(self, cmd):
        # Send en kommando til Minecraft serveren
        return self._send(2, cmd)  # Type 2 = kommando pakke

    def _send(self, type, message):
        # Byg RCON pakke efter Source RCON protokollen
        message = message.encode('utf-8')
        packet = struct.pack('<iii', len(message) + 10, 1, type) + message + b'\x00\x00'
        self.socket.send(packet)
        response = self.socket.recv(4096)
        return response[12:-2].decode('utf-8')

    def disconnect(self):
        # Luk TCP forbindelsen pænt
        self.socket.close()
