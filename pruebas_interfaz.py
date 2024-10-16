import sys
import time
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal
import ultralytics
from ultralytics import YOLO
import cv2
from collections import defaultdict
import supervision as sv
import numpy as np
import logging
import threading
from datetime import datetime

SOURCES = [int(0),int(2)] 
MODELS=['N_500ep_v8.pt','N_500ep_v8.pt']
SHOW_VID=[False,True]
EXPORTED_MODELS=[] 
trt_on=False
logging.basicConfig(level=logging.INFO)

SCHEDULE = {
    0: ('08:00', '18:00'),   # Worker 0 trabaja entre las 8:00 y 21:00
    1: ('12:00', '21:00'),   # Worker 1 trabaja entre las 14:00 y 18:00
}

class Worker(QThread):
    update_signal = pyqtSignal(int, int) # Señal para enviar la actualización a la UI, incluyendo número de hilo y valor actualizado

    def __init__(self, thread_num, source, model, show, parent=None):
        super().__init__(parent)
        self.thread_num = thread_num
        self.source = source
        self.model = model
        self.show = show
        self.count = 0
        self.running = True
        self.track_history = defaultdict(list)

    def run(self):
        cap = self.initialize_capture()
        START = sv.Point(10, 300)
        END = sv.Point(1500, 300)

        #while self.running and cap.isOpened():
        while cap.isOpened():
            #cap=self.initialize_capture()
            logging.info("running")
			now = datetime.now().strftime('%H:%M')
			start_time, end_time = SCHEDULE.get(self.thread_num, (None, None))

			if start_time and end_time and start_time <= now <= end_time:
                success, frame = cap.read()
                if success:
                    logging.info(now)
                    logging.info(f"Sucess Cam-{self.thread_num}")
                    cv2.imshow(f"hola-{self.thread_num}",frame)
                    cv2.waitKey(1)
                    #self.process_frame(frame, START, END)
                else:
                    break
                # time.sleep(1)  # Tiempo de espera simulado para el procesamiento
                # self.count = random.randint(1, 6)
                # self.update_signal.emit(self.thread_num, self.count)
            else:
                time.sleep(5)
        cap.release()
    
    def initialize_capture(self):
        cap = cv2.VideoCapture(self.source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return cap

    def process_frame(self,frame, start, end):
        results = self.model.track(frame, persist=True,conf=0.3, iou=0.5, verbose=False, save=False, tracker="bytetrack.yaml", imgsz=640)
        
        if results[0].boxes.id is None:
            return
        
        boxes = results[0].boxes.xywh.cpu()
        track_ids = results[0].boxes.id.int().cpu().tolist()	

        # Visualizar los resultados en el frame
        annotated_frame = results[0].plot()
        self.update_detection(boxes, track_ids, annotated_frame, start, end)

        cv2.imshow(f"Contador-{self.thread_num}", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self.running = False 

    def update_detection(self, boxes, track_ids, annotated_frame, start, end):
        crossed_objects = {}
        for box, track_id in zip(boxes, track_ids):
            x, y, w, h = box
            # Guardar la trayectoria del objeto
            self.track_history[track_id].append((float(x), float(y)))  # x, y como punto center
            
            # Limitar la altura de seguimiento
            if len(self.track_history[track_id]) > 30:  # Retener 30 seguimientos para 30 fotogramas
                self.track_history[track_id].pop(0)
            # Verificar si el objeto cruza la línea
            if start.x < x < end.x and abs(y - start.y) < 5:  # Supone que los objetos cruzan horizontalmente
                if track_id not in crossed_objects:
                    crossed_objects[track_id] = True  # Marcar el objeto como cruzado
        # Contar el número de objetos cruzados
        if len(crossed_objects) != self.count:
            self.count = len(crossed_objects)  # Actualizar conteo de cruzados
            self.update_signal.emit(self.thread_num, self.count)  # Emitir actualización
            logging.info(f"Cam-{self.thread_num}: Crossed Objects: {self.crossed}")
            
        cv2.line(annotated_frame, (start.x, start.y), (end.x, end.y), (0, 255, 0), 2)
        # Mostrar la cuenta de objetos en cada fotograma
        count_text = f"Objects crossed: {self.count}"
        cv2.putText(annotated_frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)   



    def reset_count(self):
        self.count = 0
        self.update_signal.emit(self.thread_num, self.count)  # Asegúrate de que la UI se actualiza

    def stop(self):
        self.running = False  # Para detener el hilo de forma segura

    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.labels = {}
        layout = QVBoxLayout()

        #Exportacion de modelo a tensorRT
        if trt_on:
            for model in MODELS:
                exported_model = YOLO(model)
                exported_model.export(format="engine")
                engine_filename = f"{model}.engine"
                loaded_model =YOLO(engine_filename)
                EXPORTED_MODELS.append(loaded_model)
        else:
            EXPORTED_MODELS = [YOLO(model) for model in MODELS]
        
        # Creación de hilos y etiquetas para cada hilo
        self.workers = []
        for video_file, model_name, show in zip(SOURCES, EXPORTED_MODELS, SHOW_VID):
            i=int(len(self.workers))
            label = QLabel(f"Cam-{i}: 0", self)
            layout.addWidget(label)
            self.labels[i] = label

            worker = Worker(i,video_file, model_name, show)
            worker.update_signal.connect(self.update_label)
            self.workers.append(worker)
            worker.start()

        # Crear un botón para restablecer el conteo
            reset_button = QPushButton(f"Reset Cam-{i}", self)
            reset_button.clicked.connect(worker.reset_count)  # Conectar al método de reset
            layout.addWidget(reset_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)


    def update_label(self, thread_num, value):
        self.labels[thread_num].setText(f"Cam-{thread_num}: {value}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
