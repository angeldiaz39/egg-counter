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
import keyboard 

torch.cuda.set_device(0)
trt_on=False #Use TensorRT Engine
#video_path = int(3)		#Para la camara sj en usb up-left, el 0
				#Para la camara sports en usb up-right, el 3
logging.basicConfig(level=logging.INFO)
SOURCES = [int(0), int(4)]
MODEL_NAMES= ["./N_500ep_v8.pt","./N_500ep_v8.pt"]
SHOW_VID = [False, True]
#show_vid=True

COUNTS={}

def run_counter_in_thread(model, source, trt, show, num):
	# Load the model.
	model = YOLO(model)
	#Para convertir a TensorRT
	if trt:
		model.export(format="engine")
		model=YOLO("N_500ep_v8.engine")

	logging.info(f"Modelo Cam-{num} Correctamente cargado")
	cap = cv2.VideoCapture(source)
	cap.set(cv2.CAP_PROP_FRAME_WIDTH,int(640))
	cap.set(cv2.CAP_PROP_FRAME_HEIGHT,int(480))
	logging.info(f"Stream-{num} Correctamente cargado")

	START = sv.Point(10, 300)
	END = sv.Point(1500, 300)

	# Create a dictionary to keep track of objects that have crossed the line
	crossed_objects = {}
	crossed=0
	# Store the track history
	track_history = defaultdict(lambda: [])

	# Variables for FPS calculation
	prev_frame_time=0
	new_frame_time=0

	while cap.isOpened():
		success, frame = cap.read()

		if success:
			#log.info('ret=1')
			# Run YOLOv8 tracking on the frame, persisting tracks between frames
			results = model.track(frame, persist=True,conf=0.3, iou=0.5, verbose=False, save=False, tracker="bytetrack.yaml", imgsz=640)
			if results[0].boxes.id is None:
				pass

			else:
				# Get the boxes and track IDs
				boxes = results[0].boxes.xywh.cpu()
				track_ids = results[0].boxes.id.int().cpu().tolist()

				# Visualize the results on the frame
				annotated_frame = results[0].plot()
				detections = sv.Detections.from_yolov8(results[0])

				 # Plot the tracks and count objects crossing the line
				for box, track_id in zip(boxes, track_ids):
					x, y, w, h = box
					track = track_history[track_id]
					track.append((float(x), float(y)))  # x, y center point
					if len(track) > 30:  # retain 30 tracks for 30 frames
						track.pop(0)

					# Check if the object crosses the line
					if START.x < x < END.x and abs(y - START.y) < 5:  # Assuming objects cross horizontally
						if track_id not in crossed_objects:
							crossed_objects[track_id] = True
						# Annotate the object as it crosses the line
						#cv2.rectangle(annotated_frame, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)), (0, 255, 0), 2)

				 # Draw the line on the frame
				cv2.line(annotated_frame, (START.x, START.y), (END.x, END.y), (0, 255, 0), 2)

				# Write the count of objects on each frame
				count_text = f"Objects crossed: {str(len(crossed_objects))}"
				cv2.putText(annotated_frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

				 # Calculate FPS every second
				new_frame_time=time.time()
				fps=1/(new_frame_time - prev_frame_time)
				prev_frame_time = new_frame_time
				
				 # Display FPS
				cv2.putText(annotated_frame, str(int(fps)), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

				if crossed != len(crossed_objects):
					crossed=len(crossed_objects)
					COUNTS[num]=crossed
					logging.info(f"Cam-{num}: Crossed Eggs: {crossed}")
					#print('Cam- '+str(num)+': Crossed Eggs: '+str(len(crossed_objects)))
				#print('FPS Rate: ',str(int(fps)))

				cv2.imshow(f"Contador-{num}", annotated_frame)
			#else:
				#pass

			if cv2.waitKey(1) & 0xFF == ord("q"):
				break
		else:		
			break# Break the loop if the end of the video is reached

	cap.release()
	
def show_counts():
	while True:
		print(COUNTS)
		time.sleep(3)
		
		if keyboard.is_pressed('q'):
			break

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
