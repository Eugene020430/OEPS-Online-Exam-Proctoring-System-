document.addEventListener('DOMContentLoaded', async function() {
    // No need to initialize Firebase anymore
    console.log("Using local storage instead of Firebase");
    
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

    // Start the flow
    await startCamera();
    
    // Capture photo
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
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        if (!password) {
            showError("Please enter a password");
            return;
        }

        if (password !== confirmPassword) {
            showError("Passwords do not match");
            return;
        }
        
        // Validate form data
        if (!studentId || !fullName || !email || !course) {
            showError("Please fill in all student information fields.");
            return;
        }
        
        try {
            // Convert base64 image to blob
            const response = await fetch(capturedImage);
            const blob = await response.blob();
            
            // Save student data to local API
            const studentData = {
                studentId: studentId,
                fullName: fullName,
                email: email,
                course: course,
                enrollmentDate: new Date().toISOString(),
            };

            studentData.password = password;
            
            // Save student data locally via API
            await saveStudentDataLocally(studentData);
            
            // Upload reference image to backend for face processing
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
    
    // Save student data locally using our new API endpoint
    async function saveStudentDataLocally(studentData) {
        const response = await fetch('/save_student_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(studentData)
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message);
        }
        
        return result;
    }
    
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