import ultralytics
from ultralytics import YOLO
import cv2
import time
import numpy as np


# Load the model.
model = YOLO("./S_500ep_v8.pt")
'''
#Para convertir a TensorRT
model_pytorch = YOLO("S_500ep_v8.pt")
model_pytorch.export(format="engine")
model=YOLO("S_500ep_v8.engine")
'''

video_path = "recortado.mp4"
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,int(640))
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,int(480))


# Create a dictionary to keep track of objects that have crossed the line
total=0
crossed_objects = {}
# Store the track history

# Variables for FPS calculation
prev_frame_time=0
new_frame_time=0

results=model.track(int(0), stream=True, show=True)
#for r in results:
	#num_objects=len(r.boxes.data)
	#total+=num_objects
	#print(total)




# Release the video capture object and close the display window
cap.release()
#sink.release()
cv2.destroyAllWindows()
