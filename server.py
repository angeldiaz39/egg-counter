import socket

def start_server():
	host=socket.gethostname()
	port=5000
	server = socket.socket()
	#server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
	server.bind((host,port))
	server.listen(5)
	
	server2 = socket.socket()
	server.bind((host,int(6000)))
	server2.listen(5)
	
	cliente, direccion = server.accept()
	cliente2, direccion2 = server2.accept()
	print(f"Conectado a {direccion}")

	while True:
		#data = cliente.recv(1024).decode()
		data = input('->')
		cliente.send(data.encode())

if __name__=="__main__":
	start_server()
