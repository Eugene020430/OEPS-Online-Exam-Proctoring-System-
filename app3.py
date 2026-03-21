from flask import Flask, render_template, request, jsonify, redirect, session
import os
import base64
from datetime import datetime
from werkzeug.utils import secure_filename
import face_recognition
from object_detection import initialize_detector # Import the initializer
import cv2
import hashlib
import json
from pymongo import MongoClient
from pymongo.errors import PyMongoError # Import specific errors
import numpy as np
from bson.binary import Binary
from bson.objectid import ObjectId
from bson.errors import InvalidId
import sys # For potential exit on DB failure
from gaze_tracking import GazeTracking

app = Flask(__name__)
# Use environment variable or a strong default
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_replace_me')

# --- MongoDB Setup ---
try:
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    DB_NAME = 'OEPS_app' # Use your specific DB name
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # Add timeout
    # Test connection early
    client.admin.command('ping')
    db = client[DB_NAME]
    print("MongoDB connection successful.")

    # Get collection handles (these are now the single source)
    students_collection = db['students']
    face_encodings_collection = db['face_encodings']
    violations_collection = db['violations']
    heatmaps_collection = db['heatmaps']
    calibrations_collection = db['calibrations']
    questions_collection = db['exam_questions']


    # Initialize Indexes (call the function)
    def initialize_db_indexes():
        """Ensure necessary indexes exist"""
        try:
            # Note: _id index is automatic and unique.
            # students_collection.create_index('_id', unique=True) # INVALID
            # face_encodings_collection.create_index('_id', unique=True) # INVALID
            # calibrations_collection.create_index('_id', unique=True) # INVALID

            # Create indexes on fields used for querying/uniqueness
            violations_collection.create_index([('student_id', 1), ('timestamp', -1)])
            heatmaps_collection.create_index([('student_id', 1), ('timestamp', -1)]) # Index timestamp too?
            # Optionally index fields in students collection if queried often, e.g., email
            # students_collection.create_index('email', unique=True, sparse=True) # Example

            print("MongoDB indexes ensured.")
        except PyMongoError as index_e:
            print(f"Warning: Could not ensure indexes. Error: {index_e}")
        except Exception as e:
            print(f"Error ensuring indexes: {e}")

    initialize_db_indexes() # Call index creation at startup

except PyMongoError as conn_e:
    print(f"FATAL: Could not connect to MongoDB at {MONGO_URI}. Check connection string/server status.")
    print(f"Error: {conn_e}")
    # Decide action: Exit? Or let Flask run but DB operations will fail?
    # For production, exiting might be safer if DB is critical.
    sys.exit("Database connection failed.") # Exit if connection fails

# --- Flask App Setup ---
UPLOAD_FOLDER = 'uploads' # Keep for temp reference image storage
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Initialize Object Detector ---
# Pass the necessary collection objects from app3.py
detector = initialize_detector(
    violations_collection=violations_collection,
    calibrations_collection=calibrations_collection,
    heatmaps_collection=heatmaps_collection, # Pass heatmaps collection here
    students_collection=students_collection
)

def serialize_mongo_doc(doc):
    if doc is None:
        return None
    serialized = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            serialized[key] = str(value)
        elif isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized

def serialize_mongo_docs(docs):
    return [serialize_mongo_doc(doc) for doc in docs]

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# ... (keep other simple routes like /enroll, /signin, /proctor_signin) ...
@app.route('/enroll')
def enroll():
    return render_template('enroll.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/proctor_signin')
def proctor_signin():
    return render_template('proctor_signin.html')

@app.route('/authenticate_proctor', methods=['POST'])
def authenticate_proctor():
    # Use environment variables for credentials
    PROCTOR_USER = os.environ.get("PROCTOR_USER", "username")
    PROCTOR_PASS = os.environ.get("PROCTOR_PASS", "password")
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"success": False, "message": "Missing username or password"}), 400

    if data['username'] == PROCTOR_USER and data['password'] == PROCTOR_PASS:
        session['is_proctor'] = True
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/proctor_dashboard')
def proctor_dashboard():
    if not session.get('is_proctor'):
        return redirect('/proctor_signin')
    return render_template('proctor_dashboard.html')

@app.route('/api/dashboard_stats', methods=['GET'])
def dashboard_stats():
    if not session.get('is_proctor'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        student_count = students_collection.count_documents({})
        question_count = questions_collection.count_documents({})
        
        # Fetch recent violations (e.g., last 5)
        recent_activity_cursor = violations_collection.find().sort('timestamp', -1).limit(5)
        recent_activity = []
        for activity in recent_activity_cursor:
            activity['_id'] = str(activity['_id']) # Convert ObjectId
            # Ensure timestamp is a string if it's not already (it should be from log_violation)
            if 'timestamp' in activity and not isinstance(activity['timestamp'], str):
                activity['timestamp'] = str(activity['timestamp'])
            recent_activity.append(activity)

        return jsonify({
            "success": True,
            "studentCount": student_count,
            "questionCount": question_count,
            "recentActivity": recent_activity 
        })
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        return jsonify({"success": False, "message": "Error fetching dashboard stats"}), 500

@app.route('/api/students', methods=['GET'])
def get_students():
    if not session.get('is_proctor'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        # Exclude password_hash and potentially large encoding data for the list view
        student_list = list(students_collection.find({}, {"password_hash": 0, "encoding": 0}))
        return jsonify(serialize_mongo_docs(student_list))
    except Exception as e:
        print(f"Error fetching students: {e}")
        return jsonify({"success": False, "message": "Error fetching students"}), 500

@app.route('/api/students/<student_id_str>', methods=['GET'])
def get_student_details(student_id_str):
    if not session.get('is_proctor'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        student = students_collection.find_one({'_id': student_id_str}, {"password_hash": 0})
        
        if student:
            # The rest of your serialization logic remains the same
            return jsonify(serialize_mongo_doc(student))
        else:
            return jsonify({"success": False, "message": "Student not found"}), 404
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid student ID format"}), 400
    except Exception as e:
        print(f"Error fetching student details for {student_id_str}: {e}")
        return jsonify({"success": False, "message": "Error fetching student details"}), 500

@app.route('/api/questions', methods=['GET'])
def get_questions():
    # This endpoint can be accessed by students (for exam) and proctors
    try:
        # Sort by question_number if it exists, otherwise by _id or another field
        questions_list = list(questions_collection.find().sort([("question_number", 1), ("_id", 1)]))
        return jsonify(serialize_mongo_docs(questions_list))
    except Exception as e:
        print(f"Error fetching questions: {e}")
        return jsonify({"success": False, "message": "Error fetching questions"}), 500

@app.route('/api/questions', methods=['POST'])
def add_question():
    if not session.get('is_proctor'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        data = request.json
        # Basic validation
        if not all(k in data for k in ['question_number', 'text', 'options', 'correct_option_index']):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        if not isinstance(data['options'], list) or not data['options']:
            return jsonify({"success": False, "message": "Options must be a non-empty list"}), 400
        if not (0 <= data['correct_option_index'] < len(data['options'])):
            return jsonify({"success": False, "message": "Invalid correct_option_index"}), 400

        data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        
        # Ensure question_number is int
        try:
            data['question_number'] = int(data['question_number'])
        except ValueError:
            return jsonify({"success": False, "message": "Question number must be an integer"}), 400

        result = questions_collection.insert_one(data)
        new_question = questions_collection.find_one({'_id': result.inserted_id})
        return jsonify({"success": True, "question": serialize_mongo_doc(new_question)}), 201
    except Exception as e:
        print(f"Error adding question: {e}")
        return jsonify({"success": False, "message": "Error adding question"}), 500

@app.route('/api/questions/<question_id_str>', methods=['GET'])
def get_question(question_id_str):
    if not session.get('is_proctor'): # Or allow students if needed for some reason
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        question_obj_id = ObjectId(question_id_str)
        question = questions_collection.find_one({'_id': question_obj_id})
        if question:
            return jsonify(serialize_mongo_doc(question))
        else:
            return jsonify({"success": False, "message": "Question not found"}), 404
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid question ID format"}), 400
    except Exception as e:
        print(f"Error fetching question {question_id_str}: {e}")
        return jsonify({"success": False, "message": "Error fetching question"}), 500

@app.route('/api/questions/<question_id_str>', methods=['PUT'])
def update_question(question_id_str):
    if not session.get('is_proctor'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        question_obj_id = ObjectId(question_id_str)
        data = request.json
        # Basic validation (similar to POST)
        if not all(k in data for k in ['question_number', 'text', 'options', 'correct_option_index']):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        try:
            data['question_number'] = int(data['question_number'])
        except ValueError:
            return jsonify({"success": False, "message": "Question number must be an integer"}), 400

        data['updated_at'] = datetime.now()
        
        result = questions_collection.update_one({'_id': question_obj_id}, {'$set': data})
        if result.matched_count:
            updated_question = questions_collection.find_one({'_id': question_obj_id})
            return jsonify({"success": True, "question": serialize_mongo_doc(updated_question)})
        else:
            return jsonify({"success": False, "message": "Question not found"}), 404
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid question ID format"}), 400
    except Exception as e:
        print(f"Error updating question {question_id_str}: {e}")
        return jsonify({"success": False, "message": "Error updating question"}), 500

@app.route('/api/questions/<question_id_str>', methods=['DELETE'])
def delete_question_db(question_id_str): # Renamed to avoid conflict with JS function
    if not session.get('is_proctor'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        question_obj_id = ObjectId(question_id_str)
        result = questions_collection.delete_one({'_id': question_obj_id})
        if result.deleted_count:
            return jsonify({"success": True, "message": "Question deleted"})
        else:
            return jsonify({"success": False, "message": "Question not found"}), 404
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid question ID format"}), 400
    except Exception as e:
        print(f"Error deleting question {question_id_str}: {e}")
        return jsonify({"success": False, "message": "Error deleting question"}), 500
    
@app.route('/record_violation', methods=['POST']) # NEW ENDPOINT
def record_violation_route():
    # Prioritize studentId from payload for client-side events like tab changes
    student_id = request.json.get('studentId')

    if not student_id:
        # Fallback to session if not in payload (though less ideal for this specific event)
        student_id_session = session.get('student_id')
        if student_id_session:
            student_id = student_id_session
        else:
            return jsonify({"success": False, "message": "Student ID missing from payload or session."}), 400

    if not request.json or 'violation' not in request.json:
        return jsonify({"success": False, "message": "No violation data provided"}), 400

    violation_data_from_client = request.json['violation']

    # Basic validation of the received violation data
    if not violation_data_from_client.get('object'): # 'details' might be optional for some
        return jsonify({"success": False, "message": "Violation data is incomplete (missing object type)"}), 400

    try:
        # Ensure timestamp from client is used, or add one if missing
        if 'timestamp' not in violation_data_from_client or not violation_data_from_client['timestamp']:
            violation_data_from_client['timestamp'] = datetime.now().isoformat()
        
        # The detector.log_violation method should handle severity score calculation
        # based on the 'object' type (e.g., "tab_change_blur").
        # Make sure these new 'tab_change_...' types are in your detector.violation_scores.
        
        print(f"[APP3 /record_violation] Logging for student {student_id}: {violation_data_from_client}")
        detector.log_violation(student_id, violation_data_from_client)
        
        # Return the logged violation for confirmation (optional)
        return jsonify({"success": True, "message": "Violation logged successfully", "violation": violation_data_from_client})

    except Exception as e:
        print(f"Error logging custom violation for student {student_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Server error logging violation: {str(e)}"}), 500



@app.route('/exam')
def exam():
    if not session.get('verified', False) or not session.get('student_id'):
        print("User not verified or no student ID in session. Redirecting to signin.")
        return redirect('/signin')
    # Pass student_id to template if needed there
    return render_template('exam.html', student_id=session.get('student_id'))

@app.route('/upload_reference', methods=['POST'])
def upload_reference():
    if 'photo' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400

    file = request.files['photo']
    student_id = request.form.get('studentId')

    if not student_id:
         return jsonify({"success": False, "message": "Student ID is required"}), 400
    if not file or file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400

    try:
        image_data = file.read() # Read binary data

        # Convert binary data to numpy array for face_recognition
        nparr = np.frombuffer(image_data, np.uint8)
        # Use cv2.imdecode which is generally robust
        reference_image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if reference_image_bgr is None:
            return jsonify({"success": False, "message": "Could not decode image file."}), 400

        # face_recognition needs RGB
        reference_image_rgb = cv2.cvtColor(reference_image_bgr, cv2.COLOR_BGR2RGB)

        # Use HOG model for faster processing unless CNN is explicitly needed and GPU available
        model = "cnn" if cv2.cuda.getCudaEnabledDeviceCount() > 0 else "hog"
        print(f"[INFO] Using '{model}' model for face detection.")
        face_locations = face_recognition.face_locations(reference_image_rgb, model=model)

        if not face_locations:
            return jsonify({"success": False, "message": "No face detected in reference image."}), 400
        
        if len(face_locations) > 1:
            return jsonify({"success": False, "message": "Multiple faces detected. Please upload an image with only your face."}), 400
        
        # CHECK IMAGE QUALITY
        face_quality = assess_face_quality(reference_image_rgb, face_locations[0])
        if face_quality['status'] == 'failed':
            return jsonify({
                "success": False,
                "message": f"Image quality check failed: {face_quality['reason']}. Please upload a clearer image."
            }), 400

        face_encodings_list = face_recognition.face_encodings(reference_image_rgb,
                                                              face_locations,
                                                              num_jitters=5,
                                                              model="large")

        if not face_encodings_list:
             return jsonify({"success": False, "message": "Could not generate face encoding."}), 400

        # Prepare data for MongoDB
        reference_data = {
            # Storing the raw image binary is optional and takes space. Only store if needed.
            'image': Binary(image_data),
            'encoding': face_encodings_list[0].tolist(), # Store encoding as list
            'face_location': face_locations[0],
            'quality_score': face_quality['score'],
            # 'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'image_width': reference_image_rgb.shape[1],
            'image_height': reference_image_rgb.shape[0],
            'encoding_model': "large",
            'is_primary': True
        }

        # Update or insert face encoding in MongoDB
        # Use the collection handle defined globally
        face_encodings_collection.update_one(
            {'_id': student_id},
            {'$set': reference_data,
             '$setOnInsert': {'_id': student_id, 'created_at': datetime.now()}}, # Ensure _id on insert
            upsert=True
        )

        session['student_id'] = student_id # Set session only on success

        return jsonify({"success": True,
                        "message": "Reference face set successfully",
                        "quality_score": face_quality['score']
                        })

    except PyMongoError as db_e:
         print(f"Database error during reference upload for {student_id}: {db_e}")
         return jsonify({"success": False, "message": "Database error processing reference."}), 500
    except Exception as e:
         # Log the full traceback for debugging
         import traceback
         print(f"Error processing reference image for {student_id}: {e}")
         print(traceback.format_exc())
         return jsonify({"success": False, "message": f"Error processing image: {str(e)}"}), 500

# ASSESS QUALITY OF IMAGE
def assess_face_quality(image_rgb, face_location):
    """
    Assesses the quality of a face image for reliable recognition.
    
    Args:
        image_rgb: RGB image containing the face
        face_location: Tuple of (top, right, bottom, left) coordinates
        
    Returns:
        dict: Quality assessment results
    """
    try:
        top, right, bottom, left = face_location
        face_image = image_rgb[top:bottom, left:right]
        
        # 1. Check face size (small faces are unreliable)
        face_width = right - left
        face_height = bottom - top
        
        if face_width < 100 or face_height < 100:
            return {
                'status': 'failed',
                'reason': 'Face too small',
                'score': 0.0
            }
            
        # 2. Check if face is too large (too close to camera)
        if face_width > image_rgb.shape[1] * 0.9 or face_height > image_rgb.shape[0] * 0.9:
            return {
                'status': 'failed',
                'reason': 'Face too close to camera',
                'score': 0.0
            }
        
        # 3. Check image sharpness
        gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if laplacian_var < 100:  # Arbitrary threshold, adjust based on testing
            return {
                'status': 'failed',
                'reason': 'Image too blurry',
                'score': laplacian_var / 500  # Normalized score
            }
            
        # 4. Check lighting (brightness and contrast)
        mean_brightness = np.mean(gray)
        if mean_brightness < 40:
            return {
                'status': 'failed', 
                'reason': 'Image too dark',
                'score': mean_brightness / 100
            }
        if mean_brightness > 220:
            return {
                'status': 'failed',
                'reason': 'Image too bright',
                'score': (255 - mean_brightness) / 50
            }
            
        # 5. Calculate contrast
        std_dev = np.std(gray)
        if std_dev < 20:
            return {
                'status': 'failed',
                'reason': 'Image has low contrast',
                'score': std_dev / 40
            }
            
        # Calculate overall quality score (0-1)
        # Weight factors based on importance
        size_score = min(face_width, face_height) / 200  # Normalized for typical good size
        sharpness_score = min(1.0, laplacian_var / 500)
        brightness_score = 1.0 - abs(mean_brightness - 150) / 150  # Closer to middle is better
        contrast_score = min(1.0, std_dev / 80)
        
        # Weighted average
        overall_score = (size_score * 0.3 + 
                         sharpness_score * 0.3 + 
                         brightness_score * 0.2 + 
                         contrast_score * 0.2)
        
        # Pass if score is reasonable
        if overall_score > 0.5:
            return {
                'status': 'passed',
                'score': overall_score,
                'metrics': {
                    'size': (face_width, face_height),
                    'sharpness': laplacian_var,
                    'brightness': mean_brightness,
                    'contrast': std_dev
                }
            }
        else:
            return {
                'status': 'failed',
                'reason': 'Overall quality too low',
                'score': overall_score
            }
            
    except Exception as e:
        print(f"Error in face quality assessment: {e}")
        return {
            'status': 'failed',
            'reason': f'Error during quality assessment: {str(e)}',
            'score': 0.0
        }

@app.route('/verify_password', methods=['POST'])
def verify_password():
    data = request.json
    if not data or 'studentId' not in data or 'password' not in data:
        return jsonify({"success": False, "message": "Missing student ID or password"}), 400

    student_id = data['studentId']
    password = data['password']

    try:
        # Use the global collection handle
        student = students_collection.find_one({'_id': student_id})
        if not student:
            return jsonify({"success": False, "message": "Student not found"}), 404 # Not Found

        stored_password_hash = student.get('password_hash')
        if not stored_password_hash:
            return jsonify({"success": False, "message": "Password not set for this student"}), 400 # Bad Request

        # Verify password (using SHA256 as per current code)
        # !! Consider upgrading to bcrypt !!
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        if hashed_password == stored_password_hash:
            # Set session variables on successful verification
            session['student_id'] = student_id
            session['verified'] = True
            print(f"Password verified for {student_id}. Session set.")
            return jsonify({"success": True, "message": "Password verified"})
        else:
            print(f"Invalid password attempt for {student_id}")
            return jsonify({"success": False, "message": "Invalid password"}), 401 # Unauthorized

    except PyMongoError as db_e:
        print(f"Database error verifying password for {student_id}: {db_e}")
        return jsonify({"success": False, "message": "Database error"}), 500
    except Exception as e:
        print(f"Error verifying password for {student_id}: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route('/set_verified_session', methods=['POST'])
def set_verified_session():
    # This route might be redundant if /verify_password sets the session
    data = request.json
    if not data or 'studentId' not in data or 'verified' not in data:
        return jsonify({"success": False, "message": "Missing required data"}), 400

    student_id = data['studentId']
    verified = data['verified']

    if verified and student_id:
        session['student_id'] = student_id
        session['verified'] = True
    else:
        session.pop('student_id', None)
        session.pop('verified', None)

    return jsonify({"success": True})

@app.route('/save_student_data', methods=['POST'])
def save_student_data():
    data = request.json
    if not data or 'studentId' not in data or not data['studentId']:
        return jsonify({"success": False, "message": "Valid student ID is required"}), 400

    student_id = data['studentId']

    try:
        # Prepare student info document
        info_data = {k: v for k, v in data.items() if k not in ['password', 'confirmPassword', 'studentId']}
        info_data['updated_at'] = datetime.now()

        update_doc = {'$set': info_data, '$setOnInsert': {'_id': student_id, 'enrollment_date': datetime.now()}}

        # Handle password
        if 'password' in data and data['password']:
             # !! SECURITY: Use bcrypt instead of SHA256 !!
            hashed_password = hashlib.sha256(data['password'].encode()).hexdigest()
            update_doc['$set']['password_hash'] = hashed_password

        # Use the global collection handle
        result = students_collection.update_one(
            {'_id': student_id},
            update_doc,
            upsert=True
        )

        message = "Student data saved."
        if result.upserted_id: message = "Student enrolled successfully."
        elif result.modified_count > 0: message = "Student data updated."

        return jsonify({"success": True, "message": message})

    except PyMongoError as db_e:
         print(f"Database error saving student data for {student_id}: {db_e}")
         # Check for duplicate key error specifically if needed
         # from pymongo.errors import DuplicateKeyError
         # if isinstance(db_e, DuplicateKeyError): ...
         return jsonify({"success": False, "message": "Database error saving student data."}), 500
    except Exception as e:
        print(f"Unexpected error saving student data for {student_id}: {e}")
        return jsonify({"success": False, "message": "Server error saving student data."}), 500

@app.route('/calibration')
def calibration_page_serve(): # Renamed to avoid conflict if you had `calibration` object
    student_id = request.args.get('studentId')
    if not student_id:
        # Handle case where student_id is missing, maybe redirect or show error
        return "Error: Student ID is required for calibration.", 400
    print(f"[APP3.PY /calibration] Serving calibration page for student: {student_id}")
    return render_template('calibration.html', student_id_for_template=student_id)

@app.route('/save_calibration', methods=['POST'])
def save_calibration():
    data = request.json
    if not data or 'calibration' not in data:
        return jsonify({"success": False, "message": "No calibration data provided"}), 400

    student_id = session.get('student_id')

    if not student_id:
        student_id = data.get('studentId')
    if not student_id:
        return jsonify({"success": False, "message": "User session not found or invalid."}), 401

    try:
        calibration_payload = data['calibration']
        # Add any necessary validation for calibration_payload here

        calibration_data = {
            'calibration': calibration_payload,
            'updated_at': datetime.now()
        }
        # Use the global collection handle
        calibrations_collection.update_one(
            {'_id': student_id},
            {'$set': calibration_data, '$setOnInsert': {'_id': student_id, 'created_at': datetime.now()}},
            upsert=True
        )
        return jsonify({"success": True, "message": "Calibration data saved successfully"})

    except PyMongoError as db_e:
         print(f"Database error saving calibration for {student_id}: {db_e}")
         return jsonify({"success": False, "message": "Database error saving calibration."}), 500
    except Exception as e:
        print(f"Error saving calibration for {student_id}: {e}")
        return jsonify({"success": False, "message": "Server error saving calibration."}), 500

@app.route('/check_calibration', methods=['GET'])
def check_calibration():
    student_id = request.args.get('studentId', session.get('student_id'))
    if not student_id:
        return jsonify({"calibrated": False, "message": "No student ID identified"}), 400

    try:
        # Use the global collection handle
        calibration_exists = calibrations_collection.count_documents({'_id': student_id}) > 0
        return jsonify({"calibrated": calibration_exists})
    except PyMongoError as db_e:
         print(f"Database error checking calibration for {student_id}: {db_e}")
         return jsonify({"calibrated": False, "message": "Database error"}), 500

@app.route('/api/get_ratios_for_calibration_point', methods=['POST'])
def get_ratios_for_calibration_point():
    if 'image' not in request.json:
        return jsonify({"success": False, "message": "No image data provided"}), 400
    
    base64_string = request.json['image']
    student_id_from_request = request.json.get('studentId') # Optional: if you want to log or use it

    print(f"[APP3 /get_ratios_for_calibration_point] Received image for student: {student_id_from_request if student_id_from_request else 'Unknown'}")

    try:
        encoded_data = base64_string.split(',')[1] if ',' in base64_string else base64_string
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            print("[APP3 /get_ratios_for_calibration_point] Failed to decode image")
            return jsonify({"success": False, "message": "Could not decode image"}), 400

        # Create a GazeTracking instance FOR THIS REQUEST
        # This instance will perform its own internal binarization calibration
        # if its .calibration.is_complete() is false.
        # For gaze_mapping, we primarily need the ratios.
        gaze_tracker_calib = GazeTracking() 
        gaze_tracker_calib.refresh(frame)

        if gaze_tracker_calib.pupils_located:
            h_ratio = gaze_tracker_calib.horizontal_ratio()
            v_ratio = gaze_tracker_calib.vertical_ratio()

            if h_ratio is not None and v_ratio is not None:
                # Clamp ratios to a 0.0-1.0 range (or adjust as needed)
                h_ratio_clamped = max(0.0, min(1.0, h_ratio))
                v_ratio_clamped = max(0.0, min(1.0, v_ratio))
                print(f"[APP3 /get_ratios_for_calibration_point] Original Ratios - H: {h_ratio}, V: {v_ratio}")
                print(f"[APP3 /get_ratios_for_calibration_point] Clamped Ratios - H: {h_ratio_clamped}, V: {v_ratio_clamped}")
                return jsonify({
                    "success": True, 
                    "h_ratio": h_ratio_clamped, 
                    "v_ratio": v_ratio_clamped
                })
            else:
                print("[APP3 /get_ratios_for_calibration_point] Pupils located, but ratios are None.")
                return jsonify({"success": False, "message": "Pupils located, but could not calculate ratios."}), 200 # 200 with success:false
        else:
            print("[APP3 /get_ratios_for_calibration_point] Pupils not located in the provided image.")
            return jsonify({"success": False, "message": "Pupils not located in image."}), 200 # 200 with success:false

    except Exception as e:
        import traceback
        print(f"Error in /api/get_ratios_for_calibration_point: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": "Server error processing calibration image."}), 500


@app.route('/detect_objects', methods=['POST'])
def detect_objects():
    # Ensure user is verified via session
    student_id = session.get('student_id')
    if not student_id or not session.get('verified'):
         return jsonify({"success": False, "message": "User not verified or session invalid."}), 401

    if 'image' not in request.json:
        return jsonify({"success": False, "message": "No image data provided"}), 400

    image_data = request.json['image']
    show_heatmap = request.json.get('showHeatmap', False) # Get heatmap flag

    try:
        # Call the detector instance's method
        # The detector instance now uses the correct DB collections internally
        result = detector.process_base64_image(
            image_data,
            student_id=student_id,
            show_heatmap=show_heatmap
        )
        print(f"[APP3.PY /detect_objects] Student: {student_id}, Result from detector (attention_stats part): {result.get('attention_stats')}")

        if "error" in result:
            # Use a different status code for internal errors vs client errors
            return jsonify({"success": False, "message": result["error"]}), 500
        else:
            return jsonify({"success": True, **result}) # Unpack the result dict

    except Exception as e:
        # Catch unexpected errors during processing
        import traceback
        print(f"Critical error in /detect_objects for student {student_id}: {e}")
        print(traceback.format_exc())
        # Log a violation maybe?
        try:
            detector.log_violation(student_id, {"object": "detection_endpoint_error", "details": str(e)})
        except: pass # Avoid error loops
        return jsonify({"success": False, "message": "Internal server error during detection."}), 500

@app.route('/verify_identity', methods=['POST'])

def verify_identity():
    # Ensure user is verified (password step) via session before face verification
    student_id = session.get('student_id')
    if not student_id or not session.get('verified'): # 'verified' here refers to password verification
        print(f"[PY SERVER /verify_identity] PRE-CHECK FAILED: User not password-verified or no student_id in session. Session: {session}")
        return jsonify({"success": False, "verified": False, "message": "User session invalid or not password-verified."}), 401

    if 'image' not in request.json:
        print(f"[PY SERVER /verify_identity] BAD REQUEST: No image data provided.")
        return jsonify({"success": False, "verified": False, "message": "No image data provided"}), 400

    print(f"[PY SERVER /verify_identity] --- STARTING IDENTITY VERIFICATION FOR STUDENT: {student_id} ---")

    try:
        # 1. Fetch Reference Encoding
        print(f"[PY SERVER /verify_identity] Fetching reference encoding for student: {student_id}")
        encoding_doc = face_encodings_collection.find_one({'_id': student_id})
        if not encoding_doc or 'encoding' not in encoding_doc:
            print(f"[PY SERVER /verify_identity] ERROR: Reference face encoding not found for student: {student_id}")
            return jsonify({"success": False, "verified": False, "message": "Reference face encoding not found."}), 404 # Using 404 for resource not found

        known_face_encoding = np.array(encoding_doc['encoding'])
        ref_model_used = encoding_doc.get('encoding_model', 'N/A')
        print(f"[PY SERVER /verify_identity] Reference encoding loaded. Model used for reference: {ref_model_used}")

        # 2. Decode Webcam Image
        image_data = request.json['image']
        encoded_data = image_data.split(',')[1] if ',' in image_data else image_data
        try:
            img_bytes = base64.b64decode(encoded_data)
            img_np = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img_np is None:
                raise ValueError("cv2.imdecode returned None, image might be corrupted or invalid format")
            webcam_image_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
            print(f"[PY SERVER /verify_identity] Webcam image decoded successfully.")
        except Exception as decode_error:
            print(f"[PY SERVER /verify_identity] ERROR: Could not decode webcam image for student {student_id}. Error: {decode_error}")
            return jsonify({"success": False, "verified": False, "message": f"Could not decode webcam image: {str(decode_error)}"}), 400

        # 3. Face Detection on Webcam Image
        # Consistent model usage (hog for speed unless GPU, large for encodings)
        detection_model = "cnn" if cv2.cuda.getCudaEnabledDeviceCount() > 0 else "hog"
        print(f"[PY SERVER /verify_identity] Using '{detection_model}' model for FACE DETECTION on webcam image.")
        face_locations = face_recognition.face_locations(webcam_image_rgb, model=detection_model)

        if not face_locations:
            print(f"[PY SERVER /verify_identity] RESULT: No face detected in webcam image.")
            return jsonify({
                "success": True, # API call succeeded
                "verified": False, # Verification failed
                "message": "No face detected in webcam image",
                "debug_is_match_server": False,
                "debug_multiple_faces_server": False,
                "debug_liveness_passed_server": False # N/A if no face
            })

        print(f"[PY SERVER /verify_identity] {len(face_locations)} face(s) detected in webcam image.")
        multiple_faces = len(face_locations) > 1

        # 4. Webcam Face Encoding (using "large" model consistently)
        print(f"[PY SERVER /verify_identity] Using 'large' model for FACE ENCODING on webcam face(s).")
        webcam_face_encodings = face_recognition.face_encodings(webcam_image_rgb,
                                                                face_locations, # Process all detected faces initially
                                                                model="large") # Crucial: consistent model
        if not webcam_face_encodings:
            print(f"[PY SERVER /verify_identity] ERROR: Could not generate encoding(s) from webcam face(s).")
            return jsonify({
                "success": True,
                "verified": False,
                "message": "Could not generate encoding from webcam face",
                "debug_is_match_server": False,
                "debug_multiple_faces_server": multiple_faces,
                "debug_liveness_passed_server": False # N/A if no encoding
            })
        
        # We'll focus on the first detected face for primary verification
        primary_webcam_encoding = webcam_face_encodings[0]
        primary_face_location = face_locations[0]

        # 5. Liveness Detection (on the primary detected face)
        print(f"[PY SERVER /verify_identity] Performing liveness detection.")
        is_live_face = detect_liveness(webcam_image_rgb, primary_face_location)
        if not is_live_face:
            print(f"[PY SERVER /verify_identity] RESULT: Liveness check FAILED.")
            detector.log_violation(student_id, {
                "object": "liveness_detection_failed",
                "details": "Possible presentation attack detected"
            })
            return jsonify({
                "success": True,
                "verified": False,
                "message": "Liveness check failed. Please ensure you're using a real face.",
                "debug_is_match_server": False, # Not applicable or False
                "debug_multiple_faces_server": multiple_faces,
                "debug_liveness_passed_server": False
            })
        print(f"[PY SERVER /verify_identity] Liveness check PASSED.")

        # 6. Face Comparison (primary webcam face vs reference)
        STRICT_TOLERANCE = 0.5 # Your defined strict tolerance
        print(f"[PY SERVER /verify_identity] Comparing faces with tolerance: {STRICT_TOLERANCE}")
        matches = face_recognition.compare_faces([known_face_encoding], primary_webcam_encoding, tolerance=STRICT_TOLERANCE)
        face_distances = face_recognition.face_distance([known_face_encoding], primary_webcam_encoding)
        
        is_match = matches[0]
        actual_face_distance = face_distances[0]
        calculated_confidence = max(0.0, 1.0 - actual_face_distance)

        print(f"[PY SERVER /verify_identity] --- RAW DATA FOR DECISION ---")
        print(f"[PY SERVER /verify_identity] Face Distance: {actual_face_distance}")
        print(f"[PY SERVER /verify_identity] is_match (tolerance {STRICT_TOLERANCE}): {is_match}")
        print(f"[PY SERVER /verify_identity] Calculated Confidence: {calculated_confidence}")
        print(f"[PY SERVER /verify_identity] Multiple Faces Detected Flag: {multiple_faces}")
        # Liveness already checked and passed if we reach here

        # 7. Final Decision Logic
        response_verified_final = False
        response_message_final = "Identity verification failed (default)"

        if multiple_faces:
            print(f"[PY SERVER /verify_identity] --- FINAL DECISION: MULTIPLE FACES DETECTED --- Verification FAILED.")
            detector.log_violation(student_id, {
                "object": "multiple_faces_detected_final_check",
                "face_count": len(face_locations),
                "primary_match_status_if_checked": is_match # For info
            })
            response_message_final = "Multiple faces detected. Please ensure only your face is visible."
            response_verified_final = False
        elif is_match: # Single face (or primary face checked), and it matches
            print(f"[PY SERVER /verify_identity] --- FINAL DECISION: MATCH (is_match: True) --- Verification SUCCEEDED.")
            response_message_final = "Identity verified"
            response_verified_final = True
        else: # Single face (or primary face checked), but it does NOT match
            print(f"[PY SERVER /verify_identity] --- FINAL DECISION: NO MATCH (is_match: False) --- Verification FAILED.")
            detector.log_violation(student_id, {
                "object": "identity_mismatch_final_check",
                "face_distance": float(actual_face_distance),
                "confidence_score": float(calculated_confidence)
            })
            response_message_final = f"Identity verification failed (No match, Distance: {actual_face_distance:.4f})"
            response_verified_final = False
        
        # Construct the final JSON response
        response_payload = {
            "success": True, # API call itself was successful in processing
            "verified": response_verified_final,
            "message": response_message_final,
            "confidence": float(calculated_confidence),
            "face_distance": float(actual_face_distance),
            "debug_is_match_server": bool(is_match),
            "debug_multiple_faces_server": bool(multiple_faces), # The flag based on len(face_locations)
            "debug_liveness_passed_server": bool(is_live_face)
        }

        print(f"[PY SERVER /verify_identity] --- SENDING RESPONSE TO CLIENT ---: {response_payload}")
        return jsonify(response_payload)

    except PyMongoError as db_e:
        print(f"[PY SERVER /verify_identity] DATABASE ERROR for student {student_id}: {db_e}")
        return jsonify({"success": False, "verified": False, "message": "Database error during verification."}), 500
    except Exception as e:
        import traceback
        print(f"[PY SERVER /verify_identity] UNEXPECTED ERROR for student {student_id}: {e}")
        print(traceback.format_exc())
        try:
            detector.log_violation(student_id, {"object": "verification_endpoint_error", "details": str(e)})
        except Exception as log_err:
            print(f"[PY SERVER /verify_identity] Failed to log verification_endpoint_error: {log_err}")
        return jsonify({"success": False, "verified": False, "message": f"Server error during identity verification: {str(e)}"}), 500
    
# HELPER FUNCTION FOR LIVENESS DETECTION
def detect_liveness(image_rgb, face_location):
    """
    Basic liveness detection to prevent presentation attacks.
    This is a simplified implementation - consider using more sophisticated methods.
    
    Args:
        image_rgb: RGB image from webcam
        face_location: Location of the face in the image
    
    Returns:
        bool: True if the face appears to be a live face, False otherwise
    """
    try:
        top, right, bottom, left = face_location
        face_image = image_rgb[top:bottom, left:right]
        
        # 1. Check image quality (blurry images might indicate printed photos)
        gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 50:  # Low variance indicates blurry image
            return False
            
        # 2. Check for unnatural color distribution (printed photos often have different color stats)
        hsv = cv2.cvtColor(face_image, cv2.COLOR_RGB2HSV)
        saturation = hsv[:, :, 1]
        mean_saturation = np.mean(saturation)
        if mean_saturation < 20 or mean_saturation > 230:  # Unusual saturation
            return False
            
        # 3. Extract eye regions for blink detection (simplified)
        height, width = face_image.shape[:2]
        eye_region_width = width // 3
        eye_region_height = height // 5
        eye_region_top = height // 4
        
        # Left eye region
        left_eye_region = gray[eye_region_top:eye_region_top+eye_region_height, 
                              width//5:width//5+eye_region_width]
        
        # Calculate eye region variance (closed eyes have less variance)
        eye_variance = np.var(left_eye_region)
        if eye_variance < 100:  # Very uniform eye region suggests closed eyes or flat image
            return False
        
        # Additional checks could be implemented here:
        # - Texture analysis
        # - Depth estimation
        # - Reflection analysis
        # - Motion detection between frames (would require modifications to capture multiple frames)
        
        return True
        
    except Exception as e:
        print(f"Error in liveness detection: {e}")
        # Default to True in case of errors to prevent blocking legitimate users
        # In production, this could be a configuration option
        return True


@app.route('/check_enrollment', methods=['GET'])
def check_enrollment():
    student_id = request.args.get('studentId')
    if not student_id:
        return jsonify({"enrolled": False, "message": "No student ID provided"}), 400

    try:
        # Use global collection handles
        student_exists = students_collection.count_documents({'_id': student_id}) > 0
        face_data_exists = face_encodings_collection.count_documents({'_id': student_id}) > 0
        is_enrolled = student_exists and face_data_exists

        if is_enrolled:
            return jsonify({"enrolled": True})
        elif student_exists:
            return jsonify({"enrolled": False, "message": "Student enrolled but reference face missing."})
        else:
            return jsonify({"enrolled": False, "message": "Student not found."})

    except PyMongoError as db_e:
        print(f"Database error checking enrollment for {student_id}: {db_e}")
        return jsonify({"enrolled": False, "message": "Database error"}), 500


@app.route('/check_verification', methods=['GET'])
def check_verification():
    # Checks session status, not DB
    student_id = session.get('student_id')
    verified = session.get('verified', False)
    is_session_valid = bool(student_id and verified)
    return jsonify({
        "verified": is_session_valid,
        "studentId": student_id if is_session_valid else None
    })

# --- HEAT-MAP & VIOLATION Routes ---
# These routes now primarily call methods on the 'detector' instance,
# which in turn calls methods on its 'gaze_heatmap' instance.
# The DB interactions happen within those instances using the passed collections.

@app.route('/get_heatmap_data', methods=['GET'])
def get_heatmap_data():
    # Prefer studentId from query param for proctor view? Fallback to session.
    student_id = request.args.get('studentId', session.get('student_id'))
    if not student_id:
        return jsonify({"success": False, "message": "No student ID identified"}), 400
    try:
        stats = detector.get_heatmap(student_id) # Delegate to detector instance
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        print(f"Error in get_heatmap_data for {student_id}: {e}")
        return jsonify({"success": False, "message": "Error retrieving heatmap data"}), 500

@app.route('/clear_heatmap', methods=['POST'])
def clear_heatmap():
    # Get student ID from JSON body, fallback to session
    student_id = request.json.get('studentId', session.get('student_id'))
    if not student_id:
        return jsonify({"success": False, "message": "No student ID identified"}), 400
    try:
        success = detector.clear_heatmap(student_id) # Delegate to detector instance
        return jsonify({"success": success})
    except Exception as e:
        print(f"Error in clear_heatmap for {student_id}: {e}")
        return jsonify({"success": False, "message": "Error clearing heatmap data"}), 500

@app.route('/get_violations', methods=['GET'])
def get_violations():
    student_id = request.args.get('studentId', session.get('student_id'))
    if not student_id:
        return jsonify({"success": False, "message": "No student ID identified"}), 400
    try:
        violations_list = detector.get_student_violations(student_id) # Delegate
        return jsonify({"success": True, "violations": violations_list})
    except Exception as e:
        print(f"Error in get_violations for {student_id}: {e}")
        return jsonify({"success": False, "message": "Error retrieving violations"}), 500
    
@app.route('/get_violation_score', methods=['GET'])
def get_violation_score():
    student_id = request.args.get('studentId', session.get('student_id'))
    if not student_id:
        return jsonify({"success": False, "message": "No student ID identified"}), 400
    
    try:
        score = detector.get_student_violation_score(student_id)
        total_score = detector.get_student_violation_score(student_id)
        return jsonify({"success": True,
                        "violation_score": score,
                        "total_score": total_score
            })
    except Exception as e:
        print(f"Error in get_violation_score for {student_id}: {e}")
        return jsonify({"success": False, "message": "Error retrieving violation score"}), 500

@app.route('/clear_violations', methods=['POST'])
def clear_violations():
    student_id = request.json.get('studentId', session.get('student_id'))
    if not student_id:
        return jsonify({"success": False, "message": "No student ID identified"}), 400
    try:
        success = detector.clear_student_violations(student_id) # Delegate
        return jsonify({"success": success})
    except Exception as e:
        print(f"Error in clear_violations for {student_id}: {e}")
        return jsonify({"success": False, "message": "Error clearing violations"}), 500


# --- Main Execution ---
if __name__ == "__main__":
    # Environment variables for configuration
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't', 'yes']

    print(f"Starting Flask app on {host}:{port} (Debug: {debug_mode})")
    # Use a production WSGI server (like Gunicorn or Waitress) instead of app.run in production
    app.run(host=host, port=port, debug=debug_mode)


