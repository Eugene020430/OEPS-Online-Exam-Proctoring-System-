# eye.py

import math
import numpy as np
import cv2
from pupil import Pupil


class Eye(object):
    """
    This class creates a new frame to isolate the eye and
    initiates the pupil detection.
    """

    LEFT_EYE_POINTS = [36, 37, 38, 39, 40, 41]
    RIGHT_EYE_POINTS = [42, 43, 44, 45, 46, 47]

    def __init__(self, original_frame, landmarks, side, calibration):
        self.frame = None # Initialized to None
        self.origin = None
        self.center = None
        self.pupil = None
        self.landmark_points = None
        self.side = side # Store side for logging

        self._analyze(original_frame, landmarks, side, calibration)

    @staticmethod
    def _middle_point(p1, p2):
        # ... (no change)
        x = int((p1.x + p2.x) / 2)
        y = int((p1.y + p2.y) / 2)
        return (x, y)

    def _isolate(self, frame, landmarks, points):
        # ... (region calculation, mask, eye bitwise_not - no change here) ...
        region = np.array([(landmarks.part(point).x, landmarks.part(point).y) for point in points])
        region = region.astype(np.int32)
        self.landmark_points = region

        # Applying a mask to get only the eye
        height, width = frame.shape[:2] # Original frame dimensions
        black_frame = np.zeros((height, width), np.uint8)
        mask = np.full((height, width), 255, np.uint8)
        cv2.fillPoly(mask, [region], (0, 0, 0))
        eye_masked_full = cv2.bitwise_not(black_frame, frame.copy(), mask=mask) # Renamed to avoid confusion

        # Cropping on the eye
        margin = 25
        min_x = np.min(region[:, 0]) - margin
        max_x = np.max(region[:, 0]) + margin
        min_y = np.min(region[:, 1]) - margin
        max_y = np.max(region[:, 1]) + margin

        # Ensure coordinates are within the frame bounds
        min_x = max(0, min_x)
        min_y = max(0, min_y)
        max_x = min(width, max_x)   # Use original frame width
        max_y = min(height, max_y)  # Use original frame height

        # Check for invalid crop dimensions BEFORE slicing
        if min_x >= max_x or min_y >= max_y:
            eye_side_str = "Left" if self.side == 0 else "Right"
            print(f"[EYE _isolate] {eye_side_str} Eye: Invalid crop dimensions. min_x={min_x}, max_x={max_x}, min_y={min_y}, max_y={max_y}. Setting self.frame to None.")
            self.frame = None # Explicitly set to None
            self.center = None
            self.origin = None
            return

        # ******** FIX IS HERE ********
        # Assign the cropped eye to self.frame FIRST
        self.frame = eye_masked_full[min_y:max_y, min_x:max_x]
        self.origin = (min_x, min_y) # Set origin based on the crop

        # NOW check if self.frame is empty or valid
        if self.frame is None or self.frame.size == 0: # Check if slicing resulted in an empty frame
            eye_side_str = "Left" if self.side == 0 else "Right"
            print(f"[EYE _isolate] {eye_side_str} Eye: Resulting eye frame is EMPTY after slicing. Setting center to None.")
            self.center = None # Or handle appropriately
            # self.frame will remain None or empty from the assignment if it failed
            return

        crop_height, crop_width = self.frame.shape[:2]
        self.center = (crop_width / 2, crop_height / 2)

        eye_side_str = "Left" if self.side == 0 else "Right"
        print(f"[EYE _isolate] {eye_side_str} Eye Crop - Dimensions (H, W): ({crop_height}, {crop_width}), Center: {self.center}")
        # ******** END OF FIX AREA ********

    def _blinking_ratio(self, landmarks, points):
        # ... (no change)
        left = (landmarks.part(points[0]).x, landmarks.part(points[0]).y)
        right = (landmarks.part(points[3]).x, landmarks.part(points[3]).y)
        top = self._middle_point(landmarks.part(points[1]), landmarks.part(points[2]))
        bottom = self._middle_point(landmarks.part(points[5]), landmarks.part(points[4]))

        eye_width = math.hypot((left[0] - right[0]), (left[1] - right[1]))
        eye_height = math.hypot((top[0] - bottom[0]), (top[1] - bottom[1]))

        try:
            ratio = eye_width / eye_height
        except ZeroDivisionError:
            ratio = None
        return ratio


    def _analyze(self, original_frame, landmarks, side, calibration):
        # ... (ensure self.side is set if not already in __init__)
        # self.side = side # It's already set in __init__ in your provided code, which is good.

        if side == 0:
            points = self.LEFT_EYE_POINTS
        elif side == 1:
            points = self.RIGHT_EYE_POINTS
        else:
            self.pupil = None
            return

        self.blinking = self._blinking_ratio(landmarks, points)
        self._isolate(original_frame, landmarks, points)

        if self.frame is None or self.frame.size == 0 or self.center is None:
            eye_side_str = "Left" if self.side == 0 else "Right"
            print(f"[EYE _analyze] {eye_side_str} Eye: Frame or center is invalid after _isolate. Skipping pupil detection.")
            self.pupil = None
            return

        if not calibration.is_complete():
            calibration.evaluate(self.frame, side)

        # Robust threshold fetching
        threshold_val = None
        if side == 0:
            if calibration.thresholds_left:
                threshold_val = int(sum(calibration.thresholds_left) / len(calibration.thresholds_left))
        elif side == 1:
            if calibration.thresholds_right:
                threshold_val = int(sum(calibration.thresholds_right) / len(calibration.thresholds_right))

        if threshold_val is None:
            eye_side_str = "Left" if self.side == 0 else "Right"
            print(f"[EYE _analyze] {eye_side_str} Eye: Not enough data in calibration thresholds yet or side invalid. Using default threshold 50.")
            threshold_val = 50 
        
        self.pupil = Pupil(self.frame, threshold_val)