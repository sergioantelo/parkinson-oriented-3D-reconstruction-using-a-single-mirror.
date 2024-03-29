from __future__ import print_function
from mpl_toolkits.mplot3d import Axes3D
import sys
import cv2
import numpy as np
import pickle
import config
import matplotlib.pyplot as plt
import time
import csv

(major_ver, minor_ver, subminor_ver) = cv2.__version__.split(".")
trackerTypes = ['BOOSTING', 'MIL', 'KCF','TLD', 'MEDIANFLOW', 'GOTURN', 'MOSSE', 'CSRT']
colors = [(128,128,0),(255,255,0),(255,0,0),(0,0,255),(0,255,0),(255,204,255)]
centers_ellipse = []
box_coords = []
bboxes = []
areas = []
fingerprints = []

# Create a tracker based on tracker name
def createTrackerByName(trackerType):
  if trackerType == trackerTypes[0]:
    tracker = cv2.TrackerBoosting_create()
  elif trackerType == trackerTypes[1]: 
    tracker = cv2.TrackerMIL_create()
  elif trackerType == trackerTypes[2]:
    tracker = cv2.TrackerKCF_create()
  elif trackerType == trackerTypes[3]:
    tracker = cv2.TrackerTLD_create()
  elif trackerType == trackerTypes[4]:
    tracker = cv2.TrackerMedianFlow_create()
  elif trackerType == trackerTypes[5]:
    tracker = cv2.TrackerGOTURN_create()
  elif trackerType == trackerTypes[6]:
    tracker = cv2.TrackerMOSSE_create()
  elif trackerType == trackerTypes[7]:
    tracker = cv2.TrackerCSRT_create()
  else:
    tracker = None
    print('Incorrect tracker name')
    print('Available trackers are:')
    for t in trackerTypes:
      print(t)
     
  return tracker

# Setting the video to load
videoPath = "vid/X_Lab_Reconst/horizontal.mp4" #input() to insert by terminal
 
# Reading video
video = cv2.VideoCapture(videoPath)
 
# Reading first frame
success, frame = video.read()
frameS = cv2.resize(frame, (1000,700))

# Quit if unable to read the video file
if not success:
  print('Failed to read video')
  sys.exit(1)

#Obtain the bboxes from ellipse through masking
hsv = cv2.cvtColor(frameS, cv2.COLOR_BGR2HSV)

azul_bajos = np.array([80,30,30], dtype=np.uint8)
azul_altos = np.array([130, 255, 255], dtype=np.uint8)

mask = cv2.inRange(hsv, azul_bajos, azul_altos)

plt.imshow(mask)

if major_ver == '3':
    _, cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
else:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Taking the two biggest contour areas
for i in range(len(cnts)):
    fitted_area = cv2.contourArea(cnts[i])
    print(i, fitted_area)   
    areas.append((fitted_area,cnts[i]))

sorted_areas = sorted(areas, reverse=True, key = lambda x: x[0])

c = cv2.cvtColor(mask,cv2.COLOR_GRAY2BGR)

for i in [0,1]:
    box = cv2.boundingRect(sorted_areas[i][1])
    box = list(box)
    box[2] = int(box[2] * 1.2)
    box[3] = int(box[3] * 1.2)
    box_coords.append(tuple(box))
        
    c = cv2.rectangle(c, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]),
                      (0,255,0), 3)
plt.imshow(c)
plt.show()

print('Selected bounding boxes {}'.format(len(bboxes)))

trackerType = "CSRT"   
 
# Creating a MultiTracker object
multiTracker = cv2.MultiTracker_create()
 
for bbox in box_coords:
  multiTracker.add(createTrackerByName(trackerType), mask, tuple(bbox))

# Triangulation parameters
[stereocalib_retval, M1, d1, M2, d2, R, T, E, F, valid_images, img_left_points, img_right_points] = (
    pickle.load(open(config.PKL_FILE, "rb"))
)

# Projection matrices for triangulation
(rectification_l, rectification_r, projection_l, projection_r, disparityToDepthMap, ROI_l, ROI_r) = (
    cv2.stereoRectify(M1, d1, M2, d2, config.IMG_SHAPE[:2], R, T, None, None, None, None, None, 0,
                      alpha=config.ALPHA)
)
    
elev = -105
azim = -110

# Tracking bboxes and plotting the 3D reconstruction
Xs = []
Ys = []
Zs = []
while video.isOpened():
    success, frame = video.read()
  
    if not success:
        break
    
    frameS = cv2.resize(frame, (1000,700))
    
    hsv = cv2.cvtColor(frameS, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, azul_bajos, azul_altos)
    
    success, boxes = multiTracker.update(mask)
    print(len(boxes))
 
    # Drawing tracked objects
    points = []
    for i, newbox in enumerate(boxes):
        p1 = (int(newbox[0]), int(newbox[1]))
        p2 = (int(newbox[0] + newbox[2]), int(newbox[1] + newbox[3]))
        cv2.rectangle(mask, p1, p2, colors[i], 2, 1)
        points.append(p1)
    
    # Finding 4D points from boxes
    pts4D = cv2.triangulatePoints(projection_l, projection_r, points[0], points[1]).T
    # Converting from homogeneous coordinates to 3D
    pts3D = pts4D[:, :3]/np.repeat(pts4D[:, 3], 3).reshape(-1, 3)
    
    Xs.append(pts3D[:, 0])
    Ys.append(pts3D[:, 1])
    Zs.append(pts3D[:, 2])
    
    cv2.imshow('MultiTracker', mask)  
 
    # Exit on esc key
    if cv2.waitKey(1) & 0xFF == 27:
        break


fig = plt.figure()
ax = fig.gca(projection='3d')
Xs = np.array(Xs).flatten()
Ys = np.array(Ys).flatten()
Zs = np.array(Zs).flatten()
pickle.dump([Xs,Ys,Zs], open("static","wb"))
ax.plot(Xs, Ys, Zs)

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.view_init(elev=20, azim=-80)
plt.show()


