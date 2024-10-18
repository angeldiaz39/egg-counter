import sys
import json
import socket 
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal

class SocketRecibe5000(QThread):
	data_received=pyqtSignal(dict)
	#reset_counts = pyqtSignal()
	def __init__(self):
		super().__init__()
		self.host=socket.gethostname()
		self.port=5000
		self.running=True
	def run(self):
		s = socket.socket()
		s.connect((self.host,self.port))
		
		while self.running:
			try:
				data=s.recv(1024).decode()
				if data:
					json_data =json.loads(data)
					self.data_received.emit(json_data)
			except Exception as e:
				print(f"Error recibiendo datos_ {e}")
				self.running=False
		s.close()
	
	def stop(self):
		self.running=False
		
class SocketEnvia6000(QThread):
	def __init__(self):
		super().__init__()
		self.host=socket.gethostname()
		self.port=6000
		self.socket=None
		self.run()
		
	def run(self):
		try:
			self.socket = socket.socket()
			self.socket.connect((self.host,self.port))
		except socket.error as e:
			logging.error("GUI:Error en Socket_Envia: {e}")
	def enviar_comando(self,comando):
		try:
			
			if self.socket:
				self.socket.send(comando.encode())
			else:
				logging.error("GUI:Socket_Envia no conectado")
				

		except socket.error as e:
			logging.error("GUI:Error en Socket_Envia al enviar el comando: {e}")	
			self.run()	
	
	def stop(self):
		if self.socket:
			try:
				self.socket.close()
			except socket.error as e:
				logging.error("GUI:Error en Socket_Envia al cerrar el socket: {e}")	

class MainWindow(QWidget):
	def __init__(self):
		super().__init__()
		self.layout=QVBoxLayout()
		self.labels = {}
		self.setLayout(self.layout)
		self.setWindowTitle("Contador de Huevos")
		
		self.socket_envia=SocketEnvia6000()
		
		self.reset_button = QPushButton("Resetar Contador")
		self.reset_button.clicked.connect(lambda: self.socket_envia.enviar_comando("RESET"))
		self.layout.addWidget(self.reset_button)
		
		self.off_button = QPushButton("Apagar Sistema")
		self.off_button.clicked.connect(lambda: self.socket_envia.enviar_comando("OFF"))
		self.layout.addWidget(self.off_button)
		
		self.show_button = QPushButton("Mostrar/Ocultar Video")
		self.show_button.clicked.connect(lambda: self.socket_envia.enviar_comando("SHOW_VID"))
		self.layout.addWidget(self.show_button)
		
		
		label_info=QLabel("Camara : Huevos contados")
		self.layout.addWidget(label_info)
		
		self.socket_recibe =SocketRecibe5000()
		self.socket_recibe.data_received.connect(self.update_labels)
		self.socket_recibe.start()
		
		
	def update_labels(self,data):
		for key,value in  data.items():
			label_text =f"Camara-{key} : {value}"
			if key not in self.labels:
				label =QLabel(label_text)
				self.labels[key]=label
				self.layout.addWidget(label)
			else:
				self.labels[key].setText(label_text)
				

		
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
		

