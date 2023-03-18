# PlatoonNetworkClient.py
# Client interface connector program for the platoon network.
# Allows a client on the platoon network to communicate with other clients
#       through message broadcasting. 
# Author: Franz Alarcon

import socket
import threading

# PlatoonNetworkClient
# Client connector for platooning network
# Use to send and receive string messages between platoon clients
class PlatoonNetworkClient:
    _host = socket.gethostname()
    _port = 52384

    # Constructor
    def __init__(self):
        self.soc = None
        self.message_handler = None
        self.disconnect_handler = None

    # Connect to the platooning network server
    # Requires that message_handler be set before
    def connect(self):
        if self.message_handler == None:
            print('ERROR: PlatoonNetwork message handler not set.')
            return
        
        self.soc = socket.socket()
        self.soc.connect((self._host, self._port))
        threading.Thread(target=self._recv_handler).start()
    
    # Disconnect from the platooning network server
    # Does nothing if not already connected
    def disconnect(self):
        if self.soc == None:
            return
        
        self.soc.close()
        self.soc = None

    # Send a message to all clients on the platooning network server
    # Requires that a connection have been made with the server
    def send(self, message):
        if self.soc == None:
            print("ERROR: Trying to send message without connection.")
            return
        
        self.soc.send(message.encode('ascii'))

    # Set the message_handler
    # This handler is called whenever the connected client receives a message
    #   from the server
    # Handler function must accept a string parameter which contains the 
    #   content of the message
    def set_message_handler(self, handler):
        self.message_handler = handler

    # Set the disconnect_handler
    # This handler is called if the client disconnects from the server without
    #   explicitly calling disconnect()
    def set_disconnect_handler(self, handler):
        self.disconnect_handler = handler

    # Private receive socket message handler
    def _recv_handler(self):
        while True:
            try:
                msg = self.soc.recv(1024)
                if self.message_handler != None:
                    self.message_handler(msg.decode('ascii'))
            except Exception as e:

                if hasattr(e, 'message'):
                    print(e.message)
                else:
                    print(e)

                if self.soc != None:
                    print("ERROR: Connection lost to server.")
                    self.soc.close()
                    self.soc = None
                    if self.disconnect_handler != None:
                        print("Executing disconnect handler.")
                        self.disconnect_handler()
                break
