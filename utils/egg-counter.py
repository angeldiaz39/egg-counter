import ultralytics
from ultralytics import YOLO
import cv2
from collections import defaultdict
import supervision as sv
import time
import numpy as np
import torch
import logging
import threading
import socket
import json
from datetime import datetime
import subprocess

SOURCES = [0,2]
SHOW_VID=True
model_name="./N_500ep_v8.pt"

torch.cuda.set_device(0)
trt_on=True #Use TensorRT Engine
logging.basicConfig(level=logging.INFO)
#MODEL_NAMES= ["./N_500ep_v8.pt","./N_500ep_v8.pt"]
EXPORTED_MODELS=[]
#SHOW_VID = [False,True,True]
prev_frame_time=0

COUNTS={}
SCHEDULE = {
    0: ('08:00', '23:58'), 
    1: ('15:58', '23:00'), 
    2: ('08:00', '23:39'), 
    3: ('08:00', '23:00'), 
    4: ('08:00', '18:00'),    
}
RSTs=[False,False,False,False, False, False]
APAGAR=False

def run_counter_in_thread(model, source, trt, num):
	cap=initializeCapture(source)
	START = sv.Point(1, 500)
	END = sv.Point(1500, 500)

	crossed_objects = {}
	crossed=0
	track_history = defaultdict(lambda: [])

	# Variables for FPS calculation
	#prev_frame_time=0
	new_frame_time=0

	while cap.isOpened():
		if RSTs[num]:
			crossed_objects={}
			crossed = 0
			COUNTS[num] = 0
			RSTs[num]=False
		if APAGAR:
			logging.info(f"Cam-{num}-Apagar=True")
			break
				
		now = datetime.now().strftime('%H:%M')
		start_time, end_time = SCHEDULE.get(num, (None, None))
		if start_time <= now <= end_time:
			success, frame = cap.read()
			if success:
				process_frame(frame, START, END,crossed_objects,crossed,track_history,num)
				if cv2.waitKey(1) & 0xFF == ord("q"):
					break			
			else:		
				break# Break the loop if the end of the video is reached
		else:
			logging.info(f"Camara-{num} fuera de su horario de funcionamiento")
			time.sleep(10)

	cap.release()
	
def process_frame(frame, start,end,crossed_objects,crossed,track_history,num):
	results = model.track(frame, persist=True,conf=0.3, iou=0.5, verbose=False, save=False, tracker="bytetrack.yaml", imgsz=640)
	if results[0].boxes.id is None:
		return
	boxes = results[0].boxes.xywh.cpu()
	track_ids = results[0].boxes.id.int().cpu().tolist()
	# SH Visualize the results on the frame
	if SHOW_VID:
		annotated_frame = results[0].plot()
		update_detection(boxes, track_ids, annotated_frame, start, end,crossed_objects,crossed,track_history,num)
	else:
		update_detection(boxes, track_ids, None , start, end,crossed_objects,crossed,track_history,num)

	if SHOW_VID:
		cv2.imshow(f"Contador-{num}", annotated_frame)
	


def update_detection(boxes, track_ids, annotated_frame, start, end,crossed_objects,crossed,track_history,num):
	global prev_frame_time
	for box, track_id in zip(boxes, track_ids):
		x, y, w, h = box
		track = track_history[track_id]
		track.append((float(x), float(y)))  # x, y center point
		if len(track) > 30:  # retain 30 tracks for 30 frames
			track.pop(0)

		# Check if the object crosses the line
		if start.x < x < end.x and abs(y - start.y) < 5:  # Assuming objects cross horizontally
			if track_id not in crossed_objects:
				crossed_objects[track_id] = True
			# Annotate the object as it crosses the line
			#cv2.rectangle(annotated_frame, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)), (0, 255, 0), 2)
	if crossed != len(crossed_objects):
		crossed=len(crossed_objects)
		COUNTS[num]=crossed
		logging.info(f"Cam-{num}: Crossed Eggs: {crossed}")
	
	# SH Draw the line on the frame
	cv2.line(annotated_frame, (start.x, start.y), (end.x, end.y), (0, 255, 0), 2)

	# SH Write the count of objects on each frame
	count_text = f"Objects crossed: {str(len(crossed_objects))}"
	cv2.putText(annotated_frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

	 # SH Calculate FPS every second
	new_frame_time=time.time()
	fps=1/(new_frame_time - prev_frame_time)
	prev_frame_time = new_frame_time
	
	 # SH Display FPS
	cv2.putText(annotated_frame, str(int(fps)), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)


def initializeCapture(source):
	cap = cv2.VideoCapture(source)
	cap.set(cv2.CAP_PROP_FRAME_WIDTH,int(640))
	cap.set(cv2.CAP_PROP_FRAME_HEIGHT,int(480))
	return cap
def send_counts():
	host=socket.gethostname()
	port=5000
	server = socket.socket()
	server.bind((host,port))
	server.listen(5)
	cliente, direccion = server.accept()
	logging.info(f"Conectado a {direccion}")
	while True:
		msg=json.dumps(COUNTS)
		cliente.send(msg.encode())
		#logging.info("ENVIADO")
		time.sleep(1)
		if APAGAR:
			break
def reset_counts():
	global COUNTS
	COUNTS = {key: 0 for key in COUNTS.keys()}
	logging.info("Contadores reiniciados a cero")
	
def listen_for_resets():
	global APAGAR, SHOW_VID
	host=socket.gethostname()
	port=6000
	server=socket.socket()
	server.bind((host,port))
	server.listen(5)
	
	client,addr = server.accept()
	logging.info(f"Conectado a {addr}")
	while True:
		try:
			data=client.recv(1024).decode()
			if data == "RESET":
				#reset_counts()
				for i in range(len(RSTs)):
					RSTs[i]=True
			if data == "OFF":
				logging.info("Recibida señal de APAGAR")
				APAGAR=True
				time.sleep(2)
				break
			if data == "SHOW_VID":
				logging.info("Recibida señal de SHOW_VID")
				if SHOW_VID:
					SHOW_VID=False
					cv2.destroyAllWindows()
				else:
					SHOW_VID=True
						
		except Exception as e:
			logging.info(f"Error recibiendo orden de reset: {e}")
		
		
	

tracker_threads=[]

def create_model(model_name):
	#global EXPORTED_MODELS
	#model=YOLO(model_name)
	#Para un solo modelo
	if trt_on:
		#model.export(format="engine")
		model_name_sin_ext= model_name.split('.')[1].split('/')[1]
		engine_filename = f"{model_name_sin_ext}.engine"
		model =YOLO(engine_filename)
	'''#Para modelos distintos
	if trt_on:
		for model in MODEL_NAMES:
			exported_model = YOLO(model)
			exported_model.export(format="engine")
			engine_filename = f"{model}.engine"
			loaded_model =YOLO(engine_filename)
			EXPORTED_MODELS.append(loaded_model)
	else:
		EXPORTED_MODELS = [YOLO(model) for model in MODEL_NAMES]
	'''
	return model
	


model=create_model(model_name)    
for video_file in SOURCES:
	thread = threading.Thread(target=run_counter_in_thread, args=(model, video_file, trt_on, int(len(tracker_threads))))
	COUNTS[int(len(tracker_threads))]=0
	tracker_threads.append(thread)
	thread.start()

#Hilo para ir mostrando el conteo	
t_show=threading.Thread(target=send_counts)
t_show.start()
t_reset=threading.Thread(target=listen_for_resets)
t_reset.start()

#Ejecutar la interfaz
time.sleep(8)
logging.info("Abriendo interfaz...")
subprocess.run(['python','./interfaz.py'])


for thread in tracker_threads:
	thread.join()
#t_show.join()
#t_reset.join()
cv2.destroyAllWindows()

'''	
tracker_threads=[]
for video_file, model_name, show in zip(SOURCES, MODEL_NAMES, SHOW_VID):
	thread = threading.Thread(target=run_counter_in_thread, args=(model_name, video_file, trt_on, show, int(len(tracker_threads))))
	COUNTS[int(len(tracker_threads))]=0
	tracker_threads.append(thread)
	thread.start()

#Hilo para ir mostrando el conteo	
t_show=threading.Thread(target=show_counts)
t_show.start()

for thread in tracker_threads:
	thread.join()

cv2.destroyAllWindows()
'''
