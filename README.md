# 🎓 Online Exam Proctoring System

An AI-powered online exam proctoring system that uses computer vision to detect suspicious behavior during online exams.

---

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Downloading Required Model Files](#downloading-required-model-files)
- [Usage](#usage)
- [Project Structure](#project-structure)

---

## Features

- Real-time face detection and tracking
- Eye gaze estimation
- Multiple face detection
- Head pose estimation
- Suspicious activity alerts

---

## Installation
```bash
git clone https://github.com/Eugene020430/ONLINE-EXAM-PROCTORING-SYSTEM.git
cd ONLINE-EXAM-PROCTORING-SYSTEM
pip install -r requirements.txt
```

---

## Downloading Required Model Files

>These files are too large to be included in the repository. Download them manually and place them in the project root directory.

1. `yolov3.weights`  (236 MB) [Download from official YOLO site](https://pjreddie.com/media/files/yolov3.weights) 
2. `shape_predictor_68_face_landmarks.dat` (95 MB) [Download from dlib](http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2) |

After downloading, place both files in the **project root folder**:
```
ONLINE-EXAM-PROCTORING-SYSTEM/
├── yolov3.weights                        ← place here
├── shape_predictor_68_face_landmarks.dat ← place here
├── app3.py
└── ...
```

For `shape_predictor_68_face_landmarks.dat`, you need to extract it first:
```bash
bzip2 -d shape_predictor_68_face_landmarks.dat.bz2
```

---

## Usage
```bash
python app3.py
```

---

## Project Structure
```
ONLINE-EXAM-PROCTORING-SYSTEM/
├── app3.py
├── requirements.txt
├── README.md
└── ...
```