import cv2
import numpy as np
import base64
import os
import time
from datetime import datetime
import threading
# import pickle
import dlib
import face_recognition
import gaze_heatmap
from gaze_tracking import GazeTracking

class ObjectDetector:
    def __init__(self, students_collection, violations_collection, calibrations_collection, heatmaps_collection, weights_path="yolov3.weights", config_path="yolov3.cfg", classes_path="coco.names"):
        # Initialize paths
        self.weights_path = weights_path
        self.config_path = config_path
        self.classes_path = classes_path
        
        # Load the YOLO model
        self.net = None
        self.output_layers = None
        self.classes = None
        self._load_model()

        # Initialize collections of DB
        self.students_collection = students_collection
        self.violations_collection = violations_collection
        self.calibrations_collection = calibrations_collection
        self.heatmaps_collection = heatmaps_collection

        # Initilize GazeTracker
        self.gaze_tracker = GazeTracking()

        # For Gaze heatmap
        self.gaze_heatmap = gaze_heatmap.GazeHeatmap(db_collection=self.heatmaps_collection)

        # For gaze detection
        self.gaze_states = {}
        self.gaze_threshold  = 6.0 # threshold in seconds
        
        # Dictionary to store suspicious activities by student ID
        self.suspicious_activities = {}
        
        # List of objects considered suspicious during exams
        self.suspicious_objects = ["cell phone", "book", "laptop", "tv", "remote", "keyboard", "mouse", 
                                   "cell phone", "book", "laptop", "cell phone", "book", "laptop", "tvmonitor"]

        # Scoring Violations
        self.violation_scores = {
        # Object-based violations
        "cell phone": 8.0,
        "book": 5.0,
        "laptop": 7.0,
        "tv": 6.0,
        "remote": 3.0,
        "keyboard": 5.0,
        "mouse": 3.0,
        "tvmonitor": 6.0,
        "multiple_persons": 10.0,
        
        # Gaze-based violations
        "looking_left": 0.0,
        "looking_right": 0.0,
        "looking_far_left": 0.0,
        "looking_far_right": 0.0,
        "looking_blinking": 0.0,
        "prolonged_looking_left": 4.0,
        "prolonged_looking_right": 4.0,
        "prolonged_looking_far_left": 6.0,
        "prolonged_looking_far_right": 6.0,
        "tab_change_blur": 7.0,        # Example score
        "tab_change_focus": 0.5,       # Example score (maybe lower for returning)
        "tab_change_visibility": 7.0,
        
        # Default score for unspecified violations
        "default": 0.0
        }
        
        # Lock for thread-safe operations
        self.lock = threading.Lock()

    def _load_model(self):
        """Load the YOLO model and classes"""
        try:
            self.net = cv2.dnn.readNet(self.weights_path, self.config_path)
            layer_names = self.net.getLayerNames()
            self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
            
            # Load class names
            with open(self.classes_path, "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
                
            print("YOLO model loaded successfully")
            return True
        except Exception as e:
            print(f"Error loading YOLO model: {str(e)}")
            return False
    

    def _are_boxes_overlapping(self, boxes, overlap_threshold=0.7):
    # """Check if boxes have significant overlap (suggesting same object)"""
        if len(boxes) <= 1:
            return False
        
        for i in range(len(boxes)):
            for j in range(i+1, len(boxes)):
                # Calculate IoU (Intersection over Union)
                x1, y1, w1, h1 = boxes[i]
                x2, y2, w2, h2 = boxes[j]
            
                # Calculate intersection area
                x_overlap = max(0, min(x1+w1, x2+w2) - max(x1, x2))
                y_overlap = max(0, min(y1+h1, y2+h2) - max(y1, y2))
                intersection = x_overlap * y_overlap
            
                # Calculate union area
                union = w1*h1 + w2*h2 - intersection
            
                if intersection / union > overlap_threshold:
                    return True
        return False
    
    def detect_objects(self, frame, student_id=None):
        """Detect objects in a video frame"""
        height, width, _ = frame.shape
        
        # Prepare the frame for YOLO
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)
        
        # Process detections
        class_ids = []
        confidences = []
        boxes = []
        suspicious_objects = []
        person_count = 0
        
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > 0.65:  # Confidence threshold
                    # Object detected
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    # Rectangle coordinates
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
                    
                    object_name = self.classes[class_id]
                    
                    # Check for suspicious objects
                    suspicious = False
                    if object_name == "person":
                        person_count += 1

                        if confidence < 0.7:
                            person_count -= 1
                    elif object_name in self.suspicious_objects:
                        suspicious = True
                    
                    if suspicious:
                        suspicious_objects.append({
                            "object": object_name,
                            "confidence": float(confidence),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
        
        # Check if multiple people are detected
        # Check if multiple people are detected
        if person_count > 1:
        # Additional validation - check if bounding boxes are distinct enough
            person_boxes = [boxes[i] for i in range(len(boxes)) if class_ids[i] == self.classes.index("person")]
            if self._are_boxes_overlapping(person_boxes):
                person_count = 1  # Likely the same person detected multiple times
    
            if person_count > 1:  # Still multiple persons after validation
                suspicious_objects.append({
                    "object": "multiple_persons",
                    "confidence": 1.0,  # High confidence for multiple persons
                    "count": person_count,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # Apply non-max suppression to remove overlapping boxes
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.65, 0.3)  # Adjusted thresholds
        
        # Draw bounding boxes and labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
        
        detections = []
        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                label = str(self.classes[class_ids[i]])
                confidence = confidences[i]
                color = colors[class_ids[i]]
                
                # Use red color for suspicious objects
                if label in self.suspicious_objects or (label == "person" and person_count > 1):
                    color = (0, 0, 255)  # Red color for suspicious objects
                
                # Draw the detection on the frame
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, f"{label} {confidence:.2f}", (x, y - 10), font, 0.5, color, 2)
                
                detections.append({
                    "object": label,
                    "confidence": float(confidence),
                    "box": [x, y, w, h]
                })
        
        # If student_id is provided, store suspicious activities for this student
        if student_id and suspicious_objects:
            with self.lock:
                if student_id not in self.suspicious_activities:
                    self.suspicious_activities[student_id] = []
                self.suspicious_activities[student_id].extend(suspicious_objects)
        
        return frame, detections, suspicious_objects
    

    def load_student_calibration(self, student_id):
        """Load student-specific calibration data from MongoDB"""
        print(f"[OBJECT_DETECTOR load_student_calibration] Attempting to load calibration for student: {student_id}")
        
        calibration_doc = self.calibrations_collection.find_one({'_id': student_id})
        
        if calibration_doc and 'calibration' in calibration_doc:
            print(f"[OBJECT_DETECTOR load_student_calibration] Found calibration_doc: {calibration_doc}")
            if 'calibration' in calibration_doc:
                try:
                    calibration_data = calibration_doc['calibration']
                    print(f"[OBJECT_DETECTOR load_student_calibration] Extracted calibration_data: {calibration_data}")
                    
                    # Apply calibration to gaze tracker
                    self.gaze_tracker.load_student_calibration(calibration_data)
                    print(f"[OBJECT_DETECTOR load_student_calibration] Called gaze_tracker.load_student_calibration()")
                    
                    # Store calibration-specific thresholds
                    if 'thresholds' in calibration_data:
                        self.student_thresholds = calibration_data['thresholds']
                        print(f"[OBJECT_DETECTOR load_student_calibration] Loaded student_thresholds: {self.student_thresholds}")
                    print("RETURN TRUE")
                    return True
                    
                except Exception as e:
                    print(f"[OBJECT_DETECTOR load_student_calibration] ERROR applying calibration data: {str(e)}")
                    return False
        
            else:
                print(f"[OBJECT_DETECTOR load_student_calibration] 'calibration' key MISSING in calibration_doc for student {student_id}")
                return False
        else:
            print(f"[OBJECT_DETECTOR load_student_calibration] NO calibration_doc found for student {student_id}")
            return False
    
    def process_base64_image(self, base64_string, student_id=None, show_heatmap=False):
        print(f"[OBJECT_DETECTOR process_base64_image] START - Student: {student_id}, show_heatmap: {show_heatmap}")
        try:
            if student_id:
                if getattr(self, 'current_student_id', None) != student_id:
                    # ***** ENSURE CALIBRATION LOADING IS CALLED *BEFORE* gaze_tracker.refresh *****
                    self.load_student_calibration(student_id) 
                    self.current_student_id = student_id

            encoded_data = base64_string.split(',')[1] if ',' in base64_string else base64_string
            nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            self.gaze_tracker.refresh(frame) # Refresh GazeTracking with the current frame
            print(f"[OBJECT_DETECTOR process_base64_image] GazeTracker pupils located: {self.gaze_tracker.pupils_located}")

            processed_frame = self.gaze_tracker.annotated_frame() # Get frame with pupil crosses if any

            # --- REVISED GAZE DIRECTION LOGIC ---
            current_h_ratio = self.gaze_tracker.horizontal_ratio()
            current_v_ratio = self.gaze_tracker.vertical_ratio()
            is_currently_blinking = self.gaze_tracker.is_blinking()

            # This gaze_direction will be refined and used for heatmap and violations
            gaze_direction = "center" # Default final direction

            if is_currently_blinking:
                gaze_direction = "blinking"
            elif self.gaze_tracker.pupils_located: # Only proceed if pupils are found and not blinking
                screen_pos = self.gaze_tracker.get_screen_position()
                print(f"Reached use calibration data [OBJECT_DETECTOR process_base64_image] H_Ratio: {current_h_ratio}, V_Ratio: {current_v_ratio}, Screen Pos: {screen_pos}")

                if screen_pos:
                    x, y = screen_pos # x and y are normalized screen coordinates
                    # Refine gaze_direction based on screen_pos.x
                    # These thresholds (0.2, 0.4, 0.6, 0.8) WILL LIKELY NEED TUNING based on your observed screen_pos.x values
                    if x < 0.2: gaze_direction = "far_left"
                    elif x < 0.4: gaze_direction = "left"
                    elif x > 0.8: gaze_direction = "far_right"
                    elif x > 0.6: gaze_direction = "right"
                    else: gaze_direction = "center"
                    # Optionally, you could add logic for 'up'/'down' based on y here
                    # e.g., if y < 0.3 and gaze_direction == "center": gaze_direction = "up" (or "center_up")
                else:
                    # Fallback to basic ratio-based direction if screen_pos is None (e.g. bad calibration)
                    if self.gaze_tracker.is_right(): # Uses current_h_ratio
                        gaze_direction = "right"
                    elif self.gaze_tracker.is_left(): # Uses current_h_ratio
                        gaze_direction = "left"
                    else:
                        gaze_direction = "center" 
            else: # Pupils not located (and not blinking)
                gaze_direction = "undetermined" 
            # --- END OF REVISED GAZE DIRECTION LOGIC ---

            # Add eye tracking info to the frame (USING THE FINAL gaze_direction)
            cv2.putText(processed_frame, f"Gaze: {gaze_direction}", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            if current_h_ratio is not None and current_v_ratio is not None:
                cv2.putText(processed_frame, f"H: {current_h_ratio:.2f}, V: {current_v_ratio:.2f}", 
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            elif self.gaze_tracker.pupils_located:
                 cv2.putText(processed_frame, "Ratios N/A", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            # else: # No pupils, "Gaze: undetermined" or "Gaze: blinking" already covers it
                # cv2.putText(processed_frame, "No pupils detected", (10, 30), ...) is redundant if Gaze status is shown

            # Use calibration data for more accurate screen position mapping (DRAWING PART)
            # screen_pos was already fetched above if pupils were located and not blinking
            if self.gaze_tracker.pupils_located and not is_currently_blinking and 'screen_pos' in locals() and screen_pos :
                # Re-fetch only if necessary or use the one from above
                # screen_pos_for_drawing = self.gaze_tracker.get_screen_position() # Can use the screen_pos from above
                # if screen_pos_for_drawing:
                est_x, est_y = screen_pos # Use the already determined screen_pos
                frame_width_disp, frame_height_disp = processed_frame.shape[1], processed_frame.shape[0] # Use processed_frame dimensions
            
                # Clamp drawing coordinates to be within frame, and ensure they are int
                draw_x = int(max(0, min(est_x * frame_width_disp, frame_width_disp - 1)))
                draw_y = int(max(0, min(est_y * frame_height_disp, frame_height_disp - 1)))

                cv2.circle(processed_frame, (draw_x, draw_y), 
                            10, (0, 255, 255), -1) # Yellow dot for estimated gaze on screen

            # Track gaze direction and check for violations (USING THE FINAL gaze_direction)
            current_time = time.time()
            prolonged_gaze = None
            if student_id and self.gaze_tracker.pupils_located: # Only track if pupils are there
                prolonged_gaze = self.track_gaze_direction(student_id, gaze_direction, current_time)

                face_position_for_heatmap = None
                if self.gaze_tracker.pupils_located: # Redundant check, but safe
                    left_pupil = self.gaze_tracker.pupil_left_coords()
                    right_pupil = self.gaze_tracker.pupil_right_coords()
                    print(f"[OBJECT_DETECTOR] Left pupil coords: {left_pupil}, Right pupil coords: {right_pupil}")

                    if left_pupil and right_pupil:
                        x_fp = min(left_pupil[0], right_pupil[0]) - 50
                        y_fp = min(left_pupil[1], right_pupil[1]) - 50
                        w_fp = abs(right_pupil[0] - left_pupil[0]) + 100
                        h_fp = 100
                    
                        face_position_for_heatmap = (int(x_fp), int(y_fp), int(w_fp), int(h_fp))
                        print(f"[OBJECT_DETECTOR process_base64_image] GAZE_DIRECTION for heatmap: {gaze_direction}, FACE_POS_FOR_HEATMAP: {face_position_for_heatmap}")
                        self.gaze_heatmap.add_gaze_point(student_id, gaze_direction, face_position_for_heatmap, frame.shape[:2]) # Pass H,W
                    else:
                        print(f"[OBJECT_DETECTOR] Not adding gaze point to heatmap: pupil coords missing or invalid.")
                else:
                    print(f"[OBJECT_DETECTOR] Not adding gaze point to heatmap: pupils not located for heatmap point.") 
            
            # Check if gaze is not center and log as suspicious activity (USING THE FINAL gaze_direction)
            # Only log if not blinking and not undetermined
            if student_id and gaze_direction not in ["center", "blinking", "undetermined"]:
                suspicious_gaze_activity = {
                    "object": f"looking_{gaze_direction}",
                    "confidence": 0.9,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self.log_violation(student_id, suspicious_gaze_activity.copy()) # Log a copy
            
            # Perform object detection
            # Pass processed_frame because it might have pupil annotations already
            output_display_frame, detections, frame_suspicious_objects = self.detect_objects(processed_frame, student_id)

            # Generate heatmap overlay if requested
            if show_heatmap and student_id:
                output_display_frame = self.gaze_heatmap.generate_heatmap_overlay(student_id, output_display_frame)
                # ... (attention stats drawing on output_display_frame) ...

            # Convert the FINAL output_display_frame back to base64
            _, buffer = cv2.imencode('.jpg', output_display_frame)
            processed_image_b64 = base64.b64encode(buffer).decode('utf-8')

            # Build suspicious activities list for return
            all_current_suspicious_activities = [s.copy() for s in frame_suspicious_objects]
            if student_id and gaze_direction not in ["center", "blinking", "undetermined"]: # To match the earlier logging condition
                # This dict is for the *return payload*, not for re-logging
                gaze_activity_for_return = {
                    "object": f"looking_{gaze_direction}",
                    "confidence": 0.9,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") # New timestamp for this specific list item
                }
                all_current_suspicious_activities.append(gaze_activity_for_return)
            
            if prolonged_gaze: # prolonged_gaze is already a fresh dict from track_gaze_direction
                all_current_suspicious_activities.append(prolonged_gaze)
            
            final_attention_stats = self.gaze_heatmap.get_attention_statistics(student_id) if student_id else {}
            print(f"[OBJECT_DETECTOR process_base64_image] END - Returning attention_stats: {final_attention_stats}")

            return {
                "processed_image": f"data:image/jpeg;base64,{processed_image_b64}",
                "detections": detections,
                "suspicious_activities": all_current_suspicious_activities,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "attention_stats": final_attention_stats 
            }
        
        except Exception as e:
            print(f"[OBJECT_DETECTOR process_base64_image] ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    
    def track_gaze_direction(self, student_id, gaze_direction, current_time=None):
        # """Track gaze direction and log violations if gaze persists in a direction"""
        if current_time is None:
            current_time = time.time()
            
        # Initialize gaze state for student if not exists
        with self.lock:
            if student_id not in self.gaze_states:
                self.gaze_states[student_id] = {
                    "direction": "center",
                    "start_time": current_time,
                    "logged": False
                }
        
        # Get current state
        state = self.gaze_states[student_id]
        
        # If direction changed, reset timer
        if gaze_direction != state["direction"]:
            self.gaze_states[student_id] = {
                "direction": gaze_direction,
                "start_time": current_time,
                "logged": False
            }
            return None  # No violation to report
        
        # Calculate duration of current gaze direction
        duration = current_time - state["start_time"]
        
        # If looking in same non-center direction for more than threshold and not logged yet
        if (gaze_direction != "center" and 
            duration >= self.gaze_threshold and 
            not state["logged"]):
            
            # Mark as logged to prevent duplicate logs
            self.gaze_states[student_id]["logged"] = True
            
            # Create violation data
            violation = {
                "object": f"prolonged_looking_{gaze_direction}",
                "confidence": 0.95,
                "duration": round(duration, 2),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Log the violation
            self.log_violation(student_id, violation)
            
            return violation
        
        return None
    

    # route handlers for heatmap functions
    def get_heatmap(self, student_id):
        # get heatmap of specific student
        return self.gaze_heatmap.get_attention_statistics(student_id)
    
    def clear_heatmap(self, student_id):
        return self.gaze_heatmap.clear_heatmap(student_id)
    
    def get_student_violations(self, student_id):
        """Get all suspicious activities for a specific student from MongoDB"""

        
        # Get violations from MongoDB
        cursor = self.violations_collection.find({'student_id': student_id})
        violations_list = list(cursor)
        
        # Convert ObjectId to string for JSON serialization
        for violation in violations_list:
            if '_id' in violation:
                violation['_id'] = str(violation['_id'])
        
        return violations_list
    
    def get_student_violation_score(self, student_id):
        """Get the current total violation score for a student"""
        student = self.students_collection.find_one({'_id': student_id})
        if student and 'violation_score' in student:
            return student['violation_score']
        return 0

    def clear_student_violations(self, student_id):
        """Clear suspicious activities for a specific student from MongoDB"""
        
        # Clear in-memory cache
        with self.lock:
            if student_id in self.suspicious_activities:
                self.suspicious_activities[student_id] = []
        
        # Delete from MongoDB
        result = self.violations_collection.delete_many({'student_id': student_id})

        # Reset the student's violation score to 0
        self.students_collection.update_one(
            {'_id': student_id},
            {'$set': {'violation_score': 0}}
        )
        return result.deleted_count > 0
    
    def log_violation(self, student_id, violation_data):
        """Log a specific violation for a student to MongoDB"""
        
        with self.lock:
            # Keep in-memory record for immediate access
            if student_id not in self.suspicious_activities:
                self.suspicious_activities[student_id] = []

            # Add timestamp
            if "timestamp" not in violation_data:
                violation_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate severity score
            violation_type = violation_data.get("object", "default")
            score = self.violation_scores.get(violation_type, self.violation_scores["default"])


            # Adjust score based on confidence
            if "confidence" in violation_data:
                score *= violation_data["confidence"]
            
            # Add score to violation data
            violation_data["severity_score"] = round(score, 2)

            self.suspicious_activities[student_id].append(violation_data)
            
            # Add to MongoDB
            violation_data['student_id'] = student_id
            self.violations_collection.insert_one(violation_data)

            # Update the student's total violation score in the students collection
            self._update_student_violation_score(student_id, score)
            
            return True
        
    # Update student total violation score
    def _update_student_violation_score(self, student_id, additional_score):
        """Update the student's total violation score in the students collection"""
        try:
            # Use $inc to atomically increment the violation_score field
            result = self.students_collection.update_one(
                {'_id': student_id},
                {'$inc': {'violation_score': additional_score}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating student violation score: {e}")
            return False

# Function to initialize the detector with specific paths
def initialize_detector(students_collection, violations_collection, calibrations_collection, heatmaps_collection, weights_path="yolov3.weights", config_path="yolov3.cfg", classes_path="coco.names"):
    detector_instance = ObjectDetector(
    violations_collection=violations_collection,
    calibrations_collection=calibrations_collection,
    heatmaps_collection=heatmaps_collection, # Pass heatmaps collection
    students_collection=students_collection,
    weights_path=weights_path,
    config_path=config_path,
    classes_path=classes_path
)
    return detector_instance
