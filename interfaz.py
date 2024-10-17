import sys
import json
import socket 
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal

class SocketThread(QThread):
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

class MainWindow(QWidget):
	def __init__(self):
		super().__init__()
		self.layout=QVBoxLayout()
		self.labels = {}
		self.setLayout(self.layout)
		self.setWindowTitle("Interfaz para conteo de huevos")
		
		self.reset_button = QPushButton("Resetar Contador")
		self.reset_button.clicked.connect(self.reset_counts)
		self.layout.addWidget(self.reset_button)
		
		self.off_button = QPushButton("Apagar Sistema")
		self.off_button.clicked.connect(self.apagar_sistema)
		self.layout.addWidget(self.off_button)
		
		self.socket_thread =SocketThread()
		self.socket_thread.data_received.connect(self.update_labels)
		self.socket_thread.start()
		
		self.reset_socket = socket.socket()
		self.reset_socket.connect((socket.gethostname(),6000))
		
	def reset_counts(self):
		self.reset_socket.send("RESET".encode())
	def apagar_sistema(self):
		self.reset_socket.send("OFF".encode())
		
	def update_labels(self,data):
		for key,value in  data.items():
			if key not in self.labels:
				label =QLabel(f"{key}: {value}")
				self.labels[key]=label
				self.layout.addWidget(label)
			else:
				self.labels[key].setText(f"{key}: {value}")
				
	def closeEvent(self,event):
		self.socket_thread.stop()
		self.socket_thread.wait()
		event.accept()
		
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
		

