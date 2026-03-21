import numpy as np
import cv2
from datetime import datetime
import time
import pandas as pd # Keep for stats calculation


class GazeHeatmap:
    # Modify __init__ to accept db_collection
    def __init__(self, db_collection, resolution=(640, 480), decay_time=30):
        """
        Initialize the gaze heatmap tracker
        Args:
            db_collection: The MongoDB collection object for heatmaps.
            resolution: Tuple (width, height) of the frame resolution (for potential overlay generation).
            decay_time: Time in seconds (relevant if doing in-memory processing, less relevant if only DB).
        """
        self.heatmaps_collection = db_collection # Store the collection object
        self.width, self.height = resolution

    def add_gaze_point(self, student_id, gaze_direction, face_position, frame_shape):
        """Add a gaze point directly to the MongoDB heatmap collection"""

        print(f"[GAZE_HEATMAP add_gaze_point] Student: {student_id}, Direction: {gaze_direction}, FacePos: {face_position}")
        try:
            # Prepare the document to insert
            heatmap_point = {
                'student_id': student_id,
                'gaze_direction': gaze_direction,
                'face_position': list(face_position) if isinstance(face_position, tuple) else face_position, # Ensure serializable
                'frame_shape': list(frame_shape) if isinstance(frame_shape, tuple) else frame_shape, # Ensure serializable
                'timestamp': datetime.now() # Use datetime object
            }
            # Use the passed-in collection object
            self.heatmaps_collection.insert_one(heatmap_point)
            print(f"[GAZE_HEATMAP add_gaze_point] Inserted for {student_id}, direction {gaze_direction}")
            return True
        except Exception as e:
            print(f"[GAZE_HEATMAP add_gaze_point] DB Insert ERROR for {student_id}: {e}")
            print(f"Error adding heatmap point for {student_id} to DB: {e}")
            return False

    def generate_heatmap_overlay(self, student_id, frame):
        """
        Generate a heatmap overlay for the given frame (Reads from DB - potentially slow)

        NOTE: This implementation now queries the DB every time. For performance,
              consider caching recent points or generating the overlay less frequently.
              For simplicity, we'll query here.
        """
        try:
            frame_h, frame_w = frame.shape[:2]
            # Query recent heatmap points (e.g., last 5 minutes)
            cutoff_time = datetime.now() - pd.Timedelta(minutes=5)
            cursor = self.heatmaps_collection.find({
                'student_id': student_id,
                'timestamp': {'$gte': cutoff_time}
            })
            points = list(cursor)

            if not points:
                return frame # Return original frame if no recent points

            # Create an empty heatmap array
            heatmap = np.zeros((frame_h, frame_w), dtype=np.float32)

            # Add points to the heatmap (simplified - just incrementing pixels)
            # For Gaussian effect, query would be much slower.
            for point in points:
                 # Estimate gaze point from face center and direction (reuse logic if needed)
                 # Simplified: Using face center for this example
                 if 'face_position' in point and point['face_position']:
                     fx, fy, fw, fh = point['face_position']
                     center_x = int(fx + fw / 2)
                     center_y = int(fy + fh / 2)
                     # Clamp coordinates
                     px = min(max(center_x, 0), frame_w - 1)
                     py = min(max(center_y, 0), frame_h - 1)
                     heatmap[py, px] += 0.1 # Increment intensity

            # Normalize and apply colormap (keep this part)
            if np.max(heatmap) > 0:
                heatmap = np.clip(heatmap / np.max(heatmap), 0, 1) # Clip before scaling
            else:
                return frame # No heat

            heatmap_colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)

            # Blending (keep this part)
            alpha = 0.4 # Blend factor
            overlay = cv2.addWeighted(frame.astype(np.float32), 1 - alpha, heatmap_colored.astype(np.float32), alpha, 0)

            # Add legend (keep this part)
            self._add_heatmap_legend(overlay)

            return overlay.astype(np.uint8)

        except Exception as e:
            print(f"Error generating heatmap overlay for {student_id}: {e}")
            return frame # Return original frame on error

    def _add_heatmap_legend(self, frame):
        # ... (keep this method as is) ...
        h, w = frame.shape[:2]
        legend_height, legend_width = 20, 150
        x_offset, y_offset = w - legend_width - 10, 10
        gradient = np.linspace(0, 1, legend_width)
        gradient = np.tile(gradient, (legend_height, 1))
        gradient_colored = cv2.applyColorMap((gradient * 255).astype(np.uint8), cv2.COLORMAP_JET)
        if y_offset + legend_height <= h and x_offset + legend_width <= w: # Bounds check
            frame[y_offset:y_offset+legend_height, x_offset:x_offset+legend_width] = gradient_colored
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(frame, "Low", (x_offset, y_offset + legend_height + 15), font, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, "High", (x_offset + legend_width - 30, y_offset + legend_height + 15), font, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, "Gaze Intensity", (x_offset + 10, y_offset - 5), font, 0.4, (255, 255, 255), 1)


    def get_attention_statistics(self, student_id):
        """Get attention statistics using the passed collection"""

        print(f"[GAZE_HEATMAP get_attention_statistics] Called for student: {student_id}")
        default_stats = {"center": 0, "left": 0, "right": 0, "blinking": 0, "far_left": 0, "far_right": 0, "up":0, "down":0, "other": 0}
        try:
            # Use the passed-in collection object
            cursor = self.heatmaps_collection.find({'student_id': student_id}, {'gaze_direction': 1, '_id': 0})
            heatmap_data = list(cursor)

            print(f"[GAZE_HEATMAP get_attention_statistics] Found {len(heatmap_data)} records for student {student_id}. Sample (up to 5): {heatmap_data[:5] if heatmap_data else 'None'}")

            if not heatmap_data:
                # Return default if no data, maybe 100% center? Or all 0s.
                 # Let's return all 0s if empty
                 return default_stats


            df = pd.DataFrame(heatmap_data)
            if 'gaze_direction' not in df.columns or df.empty:
                 return default_stats

            direction_counts = df['gaze_direction'].value_counts()
            total = len(df)

            if total == 0: return default_stats

            # Calculate percentages
            stats = {}
            known_directions = ['center', 'left', 'right', 'blinking', 'far_left', 'far_right', 'up', 'down'] # Add up/down if used
            current_sum_percentage = 0
            for direction in known_directions:
                percentage = round((direction_counts.get(direction, 0) / total) * 100, 1)
                stats[direction] = percentage
                current_sum_percentage += percentage

            # Calculate 'other' category
            # Ensure 'other' doesn't make sum > 100 due to rounding, or become negative
            stats['other'] = round(max(0, 100 - current_sum_percentage), 1)
            if stats['other'] < 0: stats['other'] = 0 # Avoid potential floating point issues

            # Ensure all keys from default_stats are in the final stats
            for key in default_stats:
                if key not in stats:
                    stats[key] = 0.0

            print(f"[GAZE_HEATMAP get_attention_statistics] Calculated stats for {student_id}: {stats}")

            return stats

        except Exception as e:
            print(f"[GAZE_HEATMAP get_attention_statistics] ERROR for {student_id}: {e}")
            print(f"Error getting attention stats for {student_id}: {e}")
            return default_stats # Return default on error

    def clear_heatmap(self, student_id):
        """Clear heatmap data for a student using the passed collection"""

        try:
             # Use the passed-in collection object
            result = self.heatmaps_collection.delete_many({'student_id': student_id})
            print(f"Cleared {result.deleted_count} heatmap points from DB for {student_id}")
            return result.deleted_count >= 0 # Return True if successful
        except Exception as e:
            print(f"Error clearing heatmap data for {student_id}: {e}")
            return False
