from __future__ import division
import cv2
from pupil import Pupil


class Calibration(object):
    """
    This class calibrates the pupil detection algorithm by finding the
    best binarization threshold value for the person and the webcam.
    """

    def __init__(self):
        self.nb_frames = 20
        self.thresholds_left = []
        self.thresholds_right = []

    def is_complete(self):
        """Returns true if the calibration is completed"""
        return len(self.thresholds_left) >= self.nb_frames and len(self.thresholds_right) >= self.nb_frames

    def threshold(self, side):
        """Returns the threshold value for the given eye.

        Argument:
            side: Indicates whether it's the left eye (0) or the right eye (1)
        """
        if side == 0:
            return int(sum(self.thresholds_left) / len(self.thresholds_left))
        elif side == 1:
            return int(sum(self.thresholds_right) / len(self.thresholds_right))

    @staticmethod
    def iris_size(frame):
        """Returns the percentage of space that the iris takes up on
        the surface of the eye.

        Argument:
            frame (numpy.ndarray): Binarized iris frame
        """
        frame = frame[5:-5, 5:-5]
        height, width = frame.shape[:2]
        nb_pixels = height * width
        nb_blacks = nb_pixels - cv2.countNonZero(frame)
        return nb_blacks / nb_pixels

    @staticmethod
    def find_best_threshold(eye_frame):
        """Calculates the optimal threshold to binarize the
        frame for the given eye.

        Argument:
            eye_frame (numpy.ndarray): Frame of the eye to be analyzed
        """
        average_iris_size = 0.40 # earlier 0.48 -> 0.40 -> 0.35 -> 0.55
        trials = {}

        for threshold in range(5, 100, 5):
            iris_frame = Pupil.image_processing(eye_frame, threshold)
            trials[threshold] = Calibration.iris_size(iris_frame)

        best_threshold, iris_size = min(trials.items(), key=(lambda p: abs(p[1] - average_iris_size)))
        print(f"[CALIB find_best_threshold] BestT: {best_threshold}, IrisSize: {iris_size:.3f}")
        return best_threshold

    def evaluate(self, eye_frame, side):
        """Improves calibration by taking into consideration the
        given image.

        Arguments:
            eye_frame (numpy.ndarray): Frame of the eye
            side: Indicates whether it's the left eye (0) or the right eye (1)
        """
        threshold = self.find_best_threshold(eye_frame)

        if side == 0:
            self.thresholds_left.append(threshold)
        elif side == 1:
            self.thresholds_right.append(threshold)

    def load_student_calibration(self, calibration_data):
        """Load student-specific calibration data"""
        print(f"[CALIBRATION load_student_calibration] Received calibration_data: {calibration_data}")
        self.student_calibration = calibration_data
        self.has_student_calibration = True
        print(f"[CALIBRATION load_student_calibration] student_calibration set. Has student calibration: {self.has_student_calibration}")
    
    def get_eye_corner_positions(self):
        """Return eye corner positions if calibration exists"""
        if hasattr(self, 'student_calibration') and self.has_student_calibration:
            # Extract eye corner positions from calibration data
            return self.student_calibration.get('eye_corners', None)
        return None
    
    def get_pupil_size_range(self):
        """Get the student's pupil size range from calibration"""
        if hasattr(self, 'student_calibration') and self.has_student_calibration:
            return self.student_calibration.get('pupil_size_range', None)
        return None
    
    def get_gaze_mapping(self):
        """Get screen position to gaze mapping data"""
        print(f"[CALIBRATION get_gaze_mapping] Called. Has student calibration: {hasattr(self, 'has_student_calibration') and self.has_student_calibration}")
        if hasattr(self, 'student_calibration') and self.has_student_calibration:
            mapping = self.student_calibration.get('gaze_mapping', None)
            print(f"[CALIBRATION get_gaze_mapping] Found mapping: {mapping}")
            return mapping
        return None
