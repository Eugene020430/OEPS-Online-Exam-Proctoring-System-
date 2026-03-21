// document.addEventListener('DOMContentLoaded', async function() {
//     await initializeFirebase();

//     await startCamera();
//     // DOM elements
//     const video = document.getElementById('videoElement');
//     const canvas = document.getElementById('canvas');
//     const captureBtn = document.getElementById('captureBtn');
//     const submitBtn = document.getElementById('submitBtn');
//     const retakeBtn = document.getElementById('retakeBtn');
//     const preview = document.getElementById('preview');
//     const successAlert = document.getElementById('successAlert');
//     const errorAlert = document.getElementById('errorAlert');
//     const errorMessage = document.getElementById('errorMessage');
//     const loadingMessage = document.getElementById('loadingMessage');
//     const cameraError = document.getElementById('cameraError');

//     // Hide alerts initially
//     successAlert.style.display = 'none';
//     errorAlert.style.display = 'none';

//     // Canvas context
//     const ctx = canvas.getContext('2d');
    
//     // Photo capture
//     let capturedImage = null;
    
//     // Access the camera
//     async function startCamera() {
//         try {
//             const stream = await navigator.mediaDevices.getUserMedia({ 
//                 video: { 
//                     width: { ideal: 640 },
//                     height: { ideal: 480 },
//                     facingMode: "user"
//                 } 
//             });
            
//             video.srcObject = stream;
//             loadingMessage.style.display = 'none';
            
//             // Set canvas dimensions to match video
//             video.onloadedmetadata = () => {
//                 canvas.width = video.videoWidth;
//                 canvas.height = video.videoHeight;
//             };
            
//         } catch (error) {
//             console.error("Error accessing camera:", error);
//             loadingMessage.style.display = 'none';
//             cameraError.style.display = 'block';
//             cameraError.textContent = `Camera access error: ${error.message}. Please ensure you've granted camera permissions.`;
//         }
//     }
    
//     // Start the camera when the page loads
//     startCamera();
    
//     // Capture photo
//     captureBtn.addEventListener('click', function() {
//         // Draw current video frame to canvas
//         ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
//         // Convert canvas to data URL (base64 encoded image)
//         capturedImage = canvas.toDataURL('image/jpeg');
        
//         // Display preview
//         preview.src = capturedImage;
        
//         // Enable submit button and show retake button
//         submitBtn.disabled = false;
//         retakeBtn.style.display = 'block';
//     });
    
//     // Retake photo
//     retakeBtn.addEventListener('click', function() {
//         // Clear preview and disable submit button
//         preview.src = '';
//         submitBtn.disabled = true;
//         retakeBtn.style.display = 'none';
//         capturedImage = null;
//     });
    
//     // Submit enrollment
//     submitBtn.addEventListener('click', async function() {
//         if (!capturedImage) {
//             showError("No image captured. Please take a photo first.");
//             return;
//         }
        
//         const studentId = document.getElementById('studentId').value;
//         const fullName = document.getElementById('fullName').value;
//         const email = document.getElementById('email').value;
//         const course = document.getElementById('course').value;
        
//         // Validate form data
//         if (!studentId || !fullName || !email || !course) {
//             showError("Please fill in all student information fields.");
//             return;
//         }
        
//         try {
//             // First, upload image to Firebase Storage
//             const storageRef = storage.ref();
//             const imageRef = storageRef.child(`student_faces/${studentId}_${Date.now()}.jpg`);
            
//             // Convert base64 image to blob
//             const response = await fetch(capturedImage);
//             const blob = await response.blob();
            
//             // Upload image
//             const uploadTask = await imageRef.put(blob);
//             const imageUrl = await imageRef.getDownloadURL();
            
//             // Save student data to Firestore
//             await db.collection("students").doc(studentId).set({
//                 studentId: studentId,
//                 fullName: fullName,
//                 email: email,
//                 course: course,
//                 faceImageUrl: imageUrl,
//                 enrollmentDate: firebase.firestore.FieldValue.serverTimestamp()
//             });
            
//             // Send to backend for face processing as well
//             await uploadReferenceImage(blob, studentId);
            
//             // Show success message
//             successAlert.style.display = 'block';
//             errorAlert.style.display = 'none';
            
//             // Clear form
//             document.getElementById('studentInfoForm').reset();
//             preview.src = '';
//             retakeBtn.style.display = 'none';
//             submitBtn.disabled = true;
            
//         } catch (error) {
//             console.error("Error during enrollment:", error);
//             showError(`Enrollment failed: ${error.message}`);
//         }
//     });
    
//     // Upload reference image to backend
//     async function uploadReferenceImage(blob, studentId) {
//         const formData = new FormData();
//         formData.append('photo', blob, `${studentId}.jpg`);
//         formData.append('studentId', studentId);
        
//         const response = await fetch('/upload_reference', {
//             method: 'POST',
//             body: formData
//         });
        
//         const result = await response.json();
        
//         if (!result.success) {
//             throw new Error(result.message);
//         }
        
//         return result;
//     }
    
//     // Show error message
//     function showError(message) {
//         errorMessage.textContent = message;
//         errorAlert.style.display = 'block';
//         successAlert.style.display = 'none';
//     }
// });

// async function initializeFirebase() {
//     try {
//         await Promise.all([
//             firebase.auth(),
//             firebase.firestore(),
//             firebase.storage()
//         ]);
//         console.log("Firebase initialized");
//     } catch (error) {
//         console.error("Firebase initialization error:", error);
//     }
// }


document.addEventListener('DOMContentLoaded', async function() {
    // Initialize Firebase first
    await initializeFirebase();
    
    // DOM elements
    const video = document.getElementById('videoElement');
    const captureBtn = document.getElementById('captureBtn');
    const canvas = document.getElementById('canvas');
    const submitBtn = document.getElementById('submitBtn');
    const retakeBtn = document.getElementById('retakeBtn');
    const preview = document.getElementById('preview');
    const successAlert = document.getElementById('successAlert');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const loadingMessage = document.getElementById('loadingMessage');
    const cameraError = document.getElementById('cameraError');

    successAlert.style.display = 'none';
    errorAlert.style.display = 'none';

    // Canvas context
    const ctx = canvas.getContext('2d');
    
    // Photo capture
    let capturedImage = null;

    // ... (rest of your elements)

    // Start camera
    async function startCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: "user"
                } 
            });
            
            video.srcObject = stream;
            loadingMessage.style.display = 'none';
            
            // Set canvas dimensions after video loads
            video.onloadedmetadata = () => {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                console.log("Video dimensions set:", canvas.width, canvas.height);
            };
            
        } catch (error) {
            console.error("Error accessing camera:", error);
            loadingMessage.style.display = 'none';
            cameraError.style.display = 'block';
            cameraError.textContent = `Camera access error: ${error.message}. Please ensure you've granted camera permissions and are using HTTPS.`;
        }
    }

    // Initialize Firebase
    async function initializeFirebase() {
        try {
            // Use the config from firebase_config.js
            // No need to reinitialize since your firebase_config.js does this already
            console.log("Firebase ready");
            return {
                db: firebase.firestore(),
                storage: firebase.storage(),
                auth: firebase.auth()
            };
        } catch (error) {
            console.error("Firebase init error:", error);
            throw error;
        }
    }

    // Start the flow
    await startCamera();
    
    // Rest of your event listeners...
    captureBtn.addEventListener('click', function() {
        // Draw current video frame to canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert canvas to data URL (base64 encoded image)
        capturedImage = canvas.toDataURL('image/jpeg');
        
        // Display preview
        preview.src = capturedImage;
        
        // Enable submit button and show retake button
        submitBtn.disabled = false;
        retakeBtn.style.display = 'block';
    });
    
    // Retake photo
    retakeBtn.addEventListener('click', function() {
        // Clear preview and disable submit button
        preview.src = '';
        submitBtn.disabled = true;
        retakeBtn.style.display = 'none';
        capturedImage = null;
    });
    
    // Submit enrollment
    submitBtn.addEventListener('click', async function() {
        if (!capturedImage) {
            showError("No image captured. Please take a photo first.");
            return;
        }
        
        const studentId = document.getElementById('studentId').value;
        const fullName = document.getElementById('fullName').value;
        const email = document.getElementById('email').value;
        const course = document.getElementById('course').value;
        
        // Validate form data
        if (!studentId || !fullName || !email || !course) {
            showError("Please fill in all student information fields.");
            return;
        }
        
        try {
            // First, upload image to Firebase Storage
            const storageRef = storage.ref();
            const imageRef = storageRef.child(`student_faces/${studentId}_${Date.now()}.jpg`);
            
            // Convert base64 image to blob
            const response = await fetch(capturedImage);
            const blob = await response.blob();
            
            // Upload image
            const uploadTask = await imageRef.put(blob);
            const imageUrl = await imageRef.getDownloadURL();
            
            // Save student data to Firestore
            await db.collection("students").doc(studentId).set({
                studentId: studentId,
                fullName: fullName,
                email: email,
                course: course,
                faceImageUrl: imageUrl,
                enrollmentDate: firebase.firestore.FieldValue.serverTimestamp()
            });
            
            // Send to backend for face processing as well
            await uploadReferenceImage(blob, studentId);
            
            // Show success message
            successAlert.style.display = 'block';
            errorAlert.style.display = 'none';
            
            // Clear form
            document.getElementById('studentInfoForm').reset();
            preview.src = '';
            retakeBtn.style.display = 'none';
            submitBtn.disabled = true;
            
        } catch (error) {
            console.error("Error during enrollment:", error);
            showError(`Enrollment failed: ${error.message}`);
        }
    });
    
    // Upload reference image to backend
    async function uploadReferenceImage(blob, studentId) {
        const formData = new FormData();
        formData.append('photo', blob, `${studentId}.jpg`);
        formData.append('studentId', studentId);
        
        const response = await fetch('/upload_reference', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message);
        }
        
        return result;
    }
    
    // Show error message
    function showError(message) {
        errorMessage.textContent = message;
        errorAlert.style.display = 'block';
        successAlert.style.display = 'none';
    }
});