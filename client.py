import socket
import time
 
def start_client():
	host=socket.gethostname()
	port=5000
	client = socket.socket()
	client.connect((host,port))
	print(host + str(port))

	#msg=input("->")

	while True:
		#client.send(msg.encode())
		data=client.recv(1024).decode()
		
		print("recibido del servidor: "+data)
		time.sleep(3)
		#msg=input("->")
		
if __name__=="__main__":
	start_client()
