from __future__ import division
import os
import cv2
import dlib
from eye import Eye # Assuming eye.py contains the Eye class
from calibration import Calibration # Assuming calibration.py contains the Calibration class

class GazeTracking(object):
    """
    This class tracks the user's gaze.
    It provides useful information like the position of the eyes
    and pupils and allows to know if the eyes are open or closed.
    """

    def __init__(self):
        self.frame = None
        self.eye_left = None
        self.eye_right = None
        self.calibration = Calibration()

        # _face_detector is used to detect faces
        self._face_detector = dlib.get_frontal_face_detector()

        # _predictor is used to get facial landmarks of a given face
        # Ensure the path to shape_predictor_68_face_landmarks.dat is correct
        cwd = os.path.abspath(os.path.dirname(__file__))
        model_path = os.path.abspath(os.path.join(cwd, "shape_predictor_68_face_landmarks.dat"))
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Shape predictor model not found at {model_path}")
        self._predictor = dlib.shape_predictor(model_path)

    @property
    def pupils_located(self):
        """Check that pupils have been located in BOTH eyes and have valid coordinates."""
        try:
            # Check left eye
            if not (self.eye_left and 
                    self.eye_left.pupil and 
                    isinstance(self.eye_left.pupil.x, (int, float)) and 
                    isinstance(self.eye_left.pupil.y, (int, float))):
                return False
            # Check right eye
            if not (self.eye_right and
                    self.eye_right.pupil and
                    isinstance(self.eye_right.pupil.x, (int, float)) and
                    isinstance(self.eye_right.pupil.y, (int, float))):
                return False
            return True
        except Exception: # Catch any other unexpected issues
            return False

    def _analyze(self):
        """Detects the face and initialize Eye objects."""
        if self.frame is None:
            print("[GAZETRACKING _analyze] Error: Frame is None.")
            self.eye_left = None
            self.eye_right = None
            return

        gray_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_detector(gray_frame)

        if len(faces) > 0:
            try:
                landmarks = self._predictor(gray_frame, faces[0])
                self.eye_left = Eye(gray_frame, landmarks, 0, self.calibration)
                self.eye_right = Eye(gray_frame, landmarks, 1, self.calibration)
            except Exception as e: # Catch potential errors during Eye initialization or landmark prediction
                print(f"[GAZETRACKING _analyze] Error during landmark prediction or Eye init: {e}")
                self.eye_left = None
                self.eye_right = None
        else:
            # print("[GAZETRACKING _analyze] No faces detected.") # Can be noisy, enable if needed
            self.eye_left = None
            self.eye_right = None

    def refresh(self, frame):
        """Refreshes the frame and analyzes it."""
        self.frame = frame.copy() # Work on a copy to avoid modifying the original frame if passed by reference
        self._analyze()

    def pupil_left_coords(self):
        """Returns the coordinates of the left pupil relative to the original frame."""
        if self.eye_left and self.eye_left.pupil and \
           self.eye_left.origin is not None and \
           self.eye_left.pupil.x is not None and self.eye_left.pupil.y is not None:
            x = self.eye_left.origin[0] + self.eye_left.pupil.x
            y = self.eye_left.origin[1] + self.eye_left.pupil.y
            return (int(x), int(y))
        return None

    def pupil_right_coords(self):
        """Returns the coordinates of the right pupil relative to the original frame."""
        if self.eye_right and self.eye_right.pupil and \
           self.eye_right.origin is not None and \
           self.eye_right.pupil.x is not None and self.eye_right.pupil.y is not None:
            x = self.eye_right.origin[0] + self.eye_right.pupil.x
            y = self.eye_right.origin[1] + self.eye_right.pupil.y
            return (int(x), int(y))
        return None

    def _calculate_single_eye_ratio(self, eye_pupil_coord, eye_crop_center_coord, eye_side_str, axis_str):
        """Helper function to calculate and log ratio for a single eye."""
        if eye_pupil_coord is None or eye_crop_center_coord is None:
            print(f"[GAZETRACKING _calculate_single_eye_ratio] {eye_side_str} Eye {axis_str}: Pupil or Center is None.")
            return None

        # eye_crop_center_coord is half of the crop dimension (width or height)
        # So, full dimension is eye_crop_center_coord * 2
        eye_crop_dimension = eye_crop_center_coord * 2.0
        
        if eye_crop_dimension <= 1e-6: # Avoid division by zero or invalid crop
            print(f"[GAZETRACKING _calculate_single_eye_ratio] {eye_side_str} Eye {axis_str}: Invalid crop dimension ({eye_crop_dimension}).")
            return None # Cannot calculate ratio

        ratio_contrib = eye_pupil_coord / eye_crop_dimension
        
        # Log details for this eye
        coord_val = "X" if axis_str == "Horizontal" else "Y"
        dim_name = "Width" if axis_str == "Horizontal" else "Height"
        print(f"[RATIO_DEBUG] Side: {eye_side_str}, Axis: {axis_str}, PupilCoord: {eye_pupil_coord}, EyeCropDim: {eye_crop_dimension:.1f}, ResultingRatio: {ratio_contrib:.4f}")
        
        return ratio_contrib

    def horizontal_ratio(self):
        """
        Returns a number indicating the horizontal direction of the gaze.
        Ideally 0.0 (extreme right of active eye area) to 1.0 (extreme left of active eye area).
        Center is around 0.5.
        """
        if not self.pupils_located: # Checks if both pupils have valid x, y
            # print("[GAZETRACKING horizontal_ratio] Pupils not located (or attributes missing).")
            return None
        
        # Ensure eye objects and their necessary attributes are present
        if not (self.eye_left and self.eye_left.pupil and self.eye_left.center and \
                self.eye_right and self.eye_right.pupil and self.eye_right.center):
            print("[GAZETRACKING horizontal_ratio] One or both eye objects (or their pupil/center) are None.")
            return None

        pupil_left_contrib = self._calculate_single_eye_ratio(
            self.eye_left.pupil.x, self.eye_left.center[0], "Left", "Horizontal"
        )
        pupil_right_contrib = self._calculate_single_eye_ratio(
            self.eye_right.pupil.x, self.eye_right.center[0], "Right", "Horizontal"
        )

        if pupil_left_contrib is None or pupil_right_contrib is None:
            print("[GAZETRACKING horizontal_ratio] Contribution from one or both eyes is None.")
            return None 
            
        # Averaging the ratios from both eyes
        # Note: This simple averaging assumes symmetrical eye crops and behavior.
        # More advanced methods might weigh them or handle asymmetries.
        final_ratio = (pupil_left_contrib + pupil_right_contrib) / 2.0
        print(f"[GAZETRACKING horizontal_ratio] Calculated Final Horizontal Ratio: {final_ratio:.4f}")
        return final_ratio

    def vertical_ratio(self):
        """
        Returns a number indicating the vertical direction of the gaze.
        Ideally 0.0 (extreme top of active eye area) to 1.0 (extreme bottom of active eye area).
        Center is around 0.5.
        """
        if not self.pupils_located:
            # print("[GAZETRACKING vertical_ratio] Pupils not located (or attributes missing).")
            return None

        if not (self.eye_left and self.eye_left.pupil and self.eye_left.center and \
                self.eye_right and self.eye_right.pupil and self.eye_right.center):
            print("[GAZETRACKING vertical_ratio] One or both eye objects (or their pupil/center) are None.")
            return None

        pupil_left_v_contrib = self._calculate_single_eye_ratio(
            self.eye_left.pupil.y, self.eye_left.center[1], "Left", "Vertical"
        )
        pupil_right_v_contrib = self._calculate_single_eye_ratio(
            self.eye_right.pupil.y, self.eye_right.center[1], "Right", "Vertical"
        )

        if pupil_left_v_contrib is None or pupil_right_v_contrib is None:
            print("[GAZETRACKING vertical_ratio] Contribution from one or both eyes is None.")
            return None
            
        final_ratio = (pupil_left_v_contrib + pupil_right_v_contrib) / 2.0
        print(f"[GAZETRACKING vertical_ratio] Calculated Final Vertical Ratio: {final_ratio:.4f}")
        return final_ratio

    def is_right(self):
        """Returns true if the user is looking to the right."""
        hr = self.horizontal_ratio()
        if hr is not None:
            return hr <= 0.40 # Adjusted threshold (example, tune this)
        return False

    def is_left(self):
        """Returns true if the user is looking to the left."""
        hr = self.horizontal_ratio()
        if hr is not None:
            return hr >= 0.60 # Adjusted threshold (example, tune this)
        return False

    def is_center(self):
        """Returns true if the user is looking to the center."""
        # is_right() and is_left() will call horizontal_ratio() again.
        # For efficiency, you might call horizontal_ratio() once here if performance is critical.
        # However, for clarity, this is fine.
        return self.pupils_located and (not self.is_right()) and (not self.is_left())


    def is_blinking(self):
        """Returns true if the user closes his eyes."""
        if self.eye_left and self.eye_right and \
           self.eye_left.blinking is not None and self.eye_right.blinking is not None:
            # Ensure blinking ratios are valid numbers before averaging
            if isinstance(self.eye_left.blinking, (int, float)) and isinstance(self.eye_right.blinking, (int, float)):
                blinking_ratio = (self.eye_left.blinking + self.eye_right.blinking) / 2
                print(f"[GAZETRACKING is_blinking] L_blink: {self.eye_left.blinking:.2f}, R_blink: {self.eye_right.blinking:.2f}, Avg_blink_ratio: {blinking_ratio:.2f}")
                return blinking_ratio > 3.8 # This threshold might need tuning
            else:
                # print(f"[GAZETRACKING is_blinking] Invalid blinking ratio types: L={type(self.eye_left.blinking)}, R={type(self.eye_right.blinking)}")
                return False # Or treat as not blinking
        return False # Default to not blinking if eye data is incomplete


    def annotated_frame(self):
        """Returns the main frame with pupils highlighted"""
        frame = self.frame.copy()
        # No need to check self.pupils_located here again, as pupil_left_coords and pupil_right_coords do it.
        
        l_coords = self.pupil_left_coords()
        r_coords = self.pupil_right_coords()
        color = (0, 255, 0)

        if l_coords:
            cv2.line(frame, (l_coords[0] - 5, l_coords[1]), (l_coords[0] + 5, l_coords[1]), color)
            cv2.line(frame, (l_coords[0], l_coords[1] - 5), (l_coords[0], l_coords[1] + 5), color)
        if r_coords:
            cv2.line(frame, (r_coords[0] - 5, r_coords[1]), (r_coords[0] + 5, r_coords[1]), color)
            cv2.line(frame, (r_coords[0], r_coords[1] - 5), (r_coords[0], r_coords[1] + 5), color)

        return frame
    
    def load_student_calibration(self, calibration_data):
        """Load student-specific calibration data into the Calibration object."""
        self.calibration.load_student_calibration(calibration_data)
        print("[GAZETRACKING load_student_calibration] Calibration data loaded into GazeTracking's Calibration object.")
    
    def get_screen_position(self):
        """Get estimated screen position based on gaze and calibration."""
        # print(f"[GAZETRACKING get_screen_position] Called. Pupils located: {self.pupils_located}") # Already logged
        if not self.pupils_located:
            return None
        
        gaze_mapping = self.calibration.get_gaze_mapping() # This calls calibration.py
        # print(f"[GAZETRACKING get_screen_position] Gaze mapping from calibration: {gaze_mapping}") # Already logged
        if not gaze_mapping:
            return None
        
        h_ratio = self.horizontal_ratio()
        v_ratio = self.vertical_ratio()
        # print(f"[GAZETRACKING get_screen_position] h_ratio: {h_ratio}, v_ratio: {v_ratio}") # Ratios are logged internally now
        
        if h_ratio is None or v_ratio is None:
            return None
        
        try:
            # Ensure gaze_mapping has the 'horizontal' and 'vertical' keys
            horizontal_map_data = gaze_mapping.get('horizontal', [])
            vertical_map_data = gaze_mapping.get('vertical', [])

            if not horizontal_map_data or not isinstance(horizontal_map_data, list) or not all(isinstance(p, list) and len(p) == 2 for p in horizontal_map_data) :
                print(f"[GAZETRACKING get_screen_position] Invalid or empty horizontal mapping data: {horizontal_map_data}")
                return None
            if not vertical_map_data or not isinstance(vertical_map_data, list) or not all(isinstance(p, list) and len(p) == 2 for p in vertical_map_data):
                print(f"[GAZETRACKING get_screen_position] Invalid or empty vertical mapping data: {vertical_map_data}")
                return None

            screen_x = self._interpolate_position(h_ratio, horizontal_map_data)
            screen_y = self._interpolate_position(v_ratio, vertical_map_data)
            
            # print(f"[GAZETRACKING get_screen_position] Interpolated screen_x: {screen_x}, screen_y: {screen_y}") # Logged in _interpolate_position
            
            if screen_x is None or screen_y is None:
                 return None
            return (screen_x, screen_y)
        except KeyError as ke:
            print(f"[GAZETRACKING get_screen_position] KeyError during interpolation (likely 'horizontal' or 'vertical' missing in gaze_mapping): {ke}")
            return None
        except Exception as e:
            print(f"[GAZETRACKING get_screen_position] Error during interpolation: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _interpolate_position(self, current_eye_ratio, single_axis_mapping_data):
        """
        Interpolate screen position for a single axis.
        current_eye_ratio: The h_ratio or v_ratio.
        single_axis_mapping_data: List of [eye_ratio_at_calib_pt, screen_coord_at_calib_pt]
        """
        if not single_axis_mapping_data:
            print("[INTERPOLATE] Mapping data is empty.")
            return None

        # Sort points by eye_ratio (first element of sub-arrays)
        # This is crucial for finding bracketing points correctly.
        sorted_points = sorted(single_axis_mapping_data, key=lambda p: p[0])

        # Handle extrapolation: if current_eye_ratio is outside the calibrated range
        if current_eye_ratio <= sorted_points[0][0]:
            # print(f"[INTERPOLATE] Ratio {current_eye_ratio:.4f} <= min calibrated {sorted_points[0][0]:.4f}. Using screen coord {sorted_points[0][1]:.4f}")
            return max(0.0, min(1.0, sorted_points[0][1])) # Clamp to 0.0-1.0

        if current_eye_ratio >= sorted_points[-1][0]:
            # print(f"[INTERPOLATE] Ratio {current_eye_ratio:.4f} >= max calibrated {sorted_points[-1][0]:.4f}. Using screen coord {sorted_points[-1][1]:.4f}")
            return max(0.0, min(1.0, sorted_points[-1][1])) # Clamp to 0.0-1.0

        # Find the two points that bracket the current_eye_ratio for interpolation
        p1, p2 = None, None
        for i in range(len(sorted_points) - 1):
            if sorted_points[i][0] <= current_eye_ratio <= sorted_points[i+1][0]:
                p1 = sorted_points[i]
                p2 = sorted_points[i+1]
                break
        
        if p1 and p2:
            eye_ratio1, screen_coord1 = p1
            eye_ratio2, screen_coord2 = p2

            if abs(eye_ratio1 - eye_ratio2) < 1e-6: # Avoid division by zero if eye_ratios are identical
                # print(f"[INTERPOLATE] Bracketing eye ratios are identical ({eye_ratio1:.4f}). Returning screen_coord {screen_coord1:.4f}")
                return max(0.0, min(1.0, screen_coord1))

            # Linear interpolation: y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
            # Here, x is current_eye_ratio, y is the screen_coord we want.
            # (x1,y1) are (eye_ratio1, screen_coord1)
            # (x2,y2) are (eye_ratio2, screen_coord2)
            interpolated_screen_coord = screen_coord1 + \
                                     (current_eye_ratio - eye_ratio1) * \
                                     (screen_coord2 - screen_coord1) / \
                                     (eye_ratio2 - eye_ratio1)
            
            clamped_interpolated_screen_coord = max(0.0, min(1.0, interpolated_screen_coord))
            # print(f"[INTERPOLATE] Ratio: {current_eye_ratio:.4f} between ({eye_ratio1:.4f}, {screen_coord1:.4f}) and ({eye_ratio2:.4f}, {screen_coord2:.4f}) -> Screen: {interpolated_screen_coord:.4f} (Clamped: {clamped_interpolated_screen_coord:.4f})")
            return clamped_interpolated_screen_coord
        else:
            # This case should ideally be rare if the extrapolation checks above work,
            # or if the input ratios are always within the calibrated range.
            print(f"[INTERPOLATE] Could not find bracketing points for ratio {current_eye_ratio:.4f}. Using closest point from sorted list.")
            # Fallback: return coordinate of the numerically closest calibrated point's screen coordinate
            closest_point = min(sorted_points, key=lambda p_item: abs(p_item[0] - current_eye_ratio))
            return max(0.0, min(1.0, closest_point[1]))