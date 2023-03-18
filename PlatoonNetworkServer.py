# PlatoonNetworkServer.py
# Server program for the platoon network.
# Maintains client connections and broadcasts all recieved client messages to
#   other clients. 
# Author: Franz Alarcon

import socket
import threading

host = socket.gethostname()
port =  52384

# Create server socket and bind
soc = socket.socket()
soc.bind((host, port))
soc.listen()

# Client list
# Stores the corresponding socket and port number for client i
client_soc_list = []
client_port_list = []

# Broadcast a recieved message to other clients (excludes calling client)
def broadcast_others(msg, sender_port):
    for i in range(len(client_soc_list)):
        if sender_port != client_port_list[i]:
                print('Sending message to {}'.format(client_port_list[i]))
                client_soc_list[i].send(msg)

# Thread client for recieving messages
def client_thread(client_conn, address):
    addr_host, addr_port = address
    client_soc_list.append(client_conn)
    client_port_list.append(addr_port)

    print('Added client of port {}'.format(addr_port))
    
    while True:
        try:
            msg = client_conn.recv(1024)
            print('Got message from client of port {}'.format(addr_port))
            broadcast_others(msg, addr_port)
        except:
            # Known issue: If a client disconnects, the server will attempt to
            #   remove the client from its list. However, this causes an error
            #   saying that the client socket and port could not be found in the
            #   list. Idk what the solution is I'm prioritizing other issues rn
            #   since this only occurs when a client disconnects.
            print("Error! Removing client of port {}".format(addr_port))
            client_soc_list.remove(client_conn)
            client_port_list.remove(addr_port)
            
print('PlatoonNetworkServer started.')

# Client connection accept loop
while True:
    client_conn, addr = soc.accept()
    threading.Thread(target=client_thread, args=(client_conn, addr)).start()
