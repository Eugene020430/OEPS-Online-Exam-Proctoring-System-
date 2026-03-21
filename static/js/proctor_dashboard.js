// // Proctor Dashboard JavaScript

// // Global variable to store ID of question being edited
// let editingQuestionId = null;

// document.addEventListener('DOMContentLoaded', function() {
//     // Initialize nav menu functionality
//     initNavigation();
    
//     // Load initial data for the default active section (Dashboard)
//     loadDashboardData();
    
//     // Set up event listeners
//     document.getElementById('refreshDashboard').addEventListener('click', loadDashboardData);
//     document.getElementById('addQuestionBtn').addEventListener('click', () => showAddQuestionForm(null)); // null for new question
//     document.getElementById('cancelQuestionBtn').addEventListener('click', hideAddQuestionForm);
//     document.getElementById('questionForm').addEventListener('submit', saveQuestion);
//     document.getElementById('addOptionBtn').addEventListener('click', addQuestionOption);
    
//     // Student search functionality
//     const studentSearchInput = document.getElementById('studentSearch');
//     if (studentSearchInput) {
//         studentSearchInput.addEventListener('input', function() {
//             filterStudents(this.value);
//         });
//     }
// });

// // Navigation functions
// function initNavigation() {
//     const navLinks = document.querySelectorAll('.sidebar .nav-link'); // More specific selector
//     navLinks.forEach(link => {
//         link.addEventListener('click', function(e) {
//             e.preventDefault();
            
//             navLinks.forEach(l => l.classList.remove('active'));
//             this.classList.add('active');
            
//             const sectionId = this.getAttribute('data-section');
//             document.querySelectorAll('.content-section').forEach(section => {
//                 section.classList.remove('active');
//             });
//             const targetSection = document.getElementById(sectionId);
//             if (targetSection) {
//                 targetSection.classList.add('active');
//             }
            
//             if (sectionId === 'dashboard') {
//                 loadDashboardData();
//             } else if (sectionId === 'students') {
//                 loadStudentsList();
//             } else if (sectionId === 'exams') {
//                 loadExamQuestions();
//             }
//         });
//     });
//      // Activate the first nav link and its section by default if needed
//     if (navLinks.length > 0 && !document.querySelector('.sidebar .nav-link.active')) {
//         navLinks[0].click(); // Simulate a click on the first link
//     }
// }

// // Dashboard data loading
// async function loadDashboardData() {
//     try {
//         const response = await fetch('/api/dashboard_stats');
//         if (!response.ok) {
//             throw new Error(`HTTP error! status: ${response.status}`);
//         }
//         const data = await response.json();

//         if (data.success) {
//             document.getElementById('studentCount').textContent = data.studentCount || '0';
//             document.getElementById('questionCount').textContent = data.questionCount || '0';
            
//             const recentActivityBody = document.getElementById('recentActivity');
//             if (data.recentActivity && data.recentActivity.length > 0) {
//                 let activityHtml = '';
//                 data.recentActivity.forEach(activity => {
//                     const activityTime = activity.timestamp ? new Date(activity.timestamp).toLocaleTimeString() : 'N/A';
//                     activityHtml += `
//                         <tr>
//                             <td>${activityTime}</td>
//                             <td>${activity.student_id || 'N/A'}</td>
//                             <td>${activity.object || 'Unknown Activity'}</td>
//                             <td><span class="badge ${activity.object === 'identity_mismatch' || (activity.severity_score && activity.severity_score > 5) ? 'bg-danger' : 'bg-warning'}">${activity.object === 'identity_mismatch' ? 'ID Mismatch' : 'Alert'}</span></td>
//                         </tr>
//                     `;
//                 });
//                 recentActivityBody.innerHTML = activityHtml;
//             } else {
//                 recentActivityBody.innerHTML = '<tr><td colspan="4" class="text-center">No recent activity.</td></tr>';
//             }
//         } else {
//             console.error("Failed to load dashboard stats:", data.message);
//             document.getElementById('recentActivity').innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading activity.</td></tr>';
//         }
//     } catch (error) {
//         console.error("Error fetching dashboard data:", error);
//         document.getElementById('studentCount').textContent = 'Error';
//         document.getElementById('questionCount').textContent = 'Error';
//         if(document.getElementById('recentActivity')) {
//             document.getElementById('recentActivity').innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading activity.</td></tr>';
//         }
//     }
// }

// // Students list functionality
// async function loadStudentsList() {
//     const studentsListContainer = document.getElementById('studentsList');
//     studentsListContainer.innerHTML = '<div class="col-12 text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p>Loading student data...</p></div>';
    
//     try {
//         const response = await fetch('/api/students');
//         if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
//         const studentsData = await response.json();
//         renderStudentsList(studentsData);
//     } catch (error) {
//         console.error("Error fetching students list:", error);
//         studentsListContainer.innerHTML = '<div class="col-12 no-data-message"><h4 class="text-danger">Failed to load student data.</h4></div>';
//     }
// }

// function renderStudentsList(students) {
//     const studentsListContainer = document.getElementById('studentsList');
    
//     if (!students || students.length === 0) {
//         studentsListContainer.innerHTML = '<div class="col-12 no-data-message"><h4>No students found.</h4></div>';
//         return;
//     }
    
//     let html = '';
//     students.forEach(student => {
//         const studentName = `${student.firstName || ''} ${student.lastName || ''}`.trim() || 'N/A';
//         const enrollmentDate = student.enrollment_date ? new Date(student.enrollment_date).toLocaleDateString() : 'N/A';
//         const violationScore = student.violation_score !== undefined ? student.violation_score.toFixed(1) : 'N/A';
        
//         let status = 'active'; // Determine status based on score or other criteria
//         if (violationScore > 50) status = 'high_risk';
//         else if (violationScore > 20) status = 'medium_risk';

//         const statusClass = getStatusClass(status); // You'll need to define this or adjust
//         const statusText = status.replace('_', ' ').split(' ').map(capitalizeFirstLetter).join(' ');


//         html += `
//         <div class="col-md-6 col-lg-4 mb-4 student-item" data-student-name="${studentName.toLowerCase()}" data-student-id="${student._id.toLowerCase()}">
//             <div class="card student-card h-100">
//                 <div class="card-body d-flex flex-column">
//                     <div class="d-flex justify-content-between align-items-center mb-2">
//                         <h5 class="card-title mb-0">${studentName}</h5>
//                         <span class="badge ${statusClass}">${statusText}</span>
//                     </div>
//                     <p class="card-text small mb-1"><strong>ID:</strong> ${student._id}</p>
//                     <p class="card-text small mb-1"><strong>Email:</strong> ${student.email || 'N/A'}</p>
//                     <p class="card-text small mb-1"><strong>Enrolled:</strong> ${enrollmentDate}</p>
//                     <p class="card-text small mb-2"><strong>Violation Score:</strong> ${violationScore}</p>
//                     <div class="student-actions mt-auto">
//                         <button class="btn btn-sm btn-primary view-student" data-id="${student._id}">View Details</button>
//                         <button class="btn btn-sm btn-danger clear-violations-btn" data-id="${student._id}">Clear Violations</button>
//                     </div>
//                 </div>
//             </div>
//         </div>`;
//     });
    
//     studentsListContainer.innerHTML = html;
    
//     document.querySelectorAll('.view-student').forEach(btn => {
//         btn.addEventListener('click', function() { viewStudentDetails(this.getAttribute('data-id')); });
//     });
    
//     document.querySelectorAll('.clear-violations-btn').forEach(btn => {
//         btn.addEventListener('click', function() { clearStudentViolations(this.getAttribute('data-id')); });
//     });
// }

// function filterStudents(searchTerm) {
//     const studentItems = document.querySelectorAll('#studentsList .student-item');
//     searchTerm = searchTerm.toLowerCase();
    
//     studentItems.forEach(item => {
//         const name = item.getAttribute('data-student-name') || '';
//         const id = item.getAttribute('data-student-id') || '';
//         if (name.includes(searchTerm) || id.includes(searchTerm)) {
//             item.style.display = '';
//         } else {
//             item.style.display = 'none';
//         }
//     });
// }

// async function viewStudentDetails(studentId) {
//     const modal = new bootstrap.Modal(document.getElementById('studentDetailsModal'));
//     const studentDetailsContent = document.getElementById('studentDetailsContent');
//     studentDetailsContent.innerHTML = `<div class="text-center"><div class="spinner-border text-primary"></div><p>Loading details for student ${studentId}...</p></div>`;
//     modal.show();

//     try {
//         // Fetch student basic info, violations, score, heatmap data
//         const [studentRes, violationsRes, scoreRes, heatmapRes] = await Promise.all([
//             fetch(`/api/students/${studentId}`).then(r => r.ok ? r.json() : Promise.reject(r)),
//             fetch(`/get_violations?studentId=${studentId}`).then(r => r.ok ? r.json() : Promise.reject(r)),
//             fetch(`/get_violation_score?studentId=${studentId}`).then(r => r.ok ? r.json() : Promise.reject(r)),
//             fetch(`/get_heatmap_data?studentId=${studentId}`).then(r => r.ok ? r.json() : Promise.reject(r))
//         ]);

//         const student = studentRes; // Already JSON from /api/students/:id
//         const violationsData = violationsRes;
//         const scoreData = scoreRes;
//         const heatmapData = heatmapRes;
        
//         const studentName = `${student.firstName || ''} ${student.lastName || ''}`.trim() || 'N/A';
//         const violationScore = scoreData.success ? (scoreData.violation_score !== undefined ? scoreData.violation_score.toFixed(1) : 'N/A') : 'Error';

//         let detailsHtml = `
//             <div class="row">
//                 <div class="col-md-4">
//                     <img src="https://via.placeholder.com/200x200.png?text=Student+Photo" class="student-image img-fluid rounded mb-3" alt="Student Photo">
//                     <h4 class="mb-1">${studentName}</h4>
//                     <p class="small text-muted mb-2">ID: ${student._id}</p>
//                     <div class="alert ${parseFloat(violationScore) > 50 ? 'alert-danger' : (parseFloat(violationScore) > 20 ? 'alert-warning' : 'alert-info')}">
//                         <strong>Violation Score: ${violationScore}</strong>
//                     </div>
//                     <button class="btn btn-sm btn-outline-secondary w-100" onclick="printStudentReport('${studentId}')">
//                         <i class="bx bxs-printer"></i> Print Report
//                     </button>
//                 </div>
//                 <div class="col-md-8">
//                     <nav>
//                         <div class="nav nav-tabs" id="student-tab" role="tablist">
//                             <button class="nav-link active" id="violations-tab" data-bs-toggle="tab" data-bs-target="#violations-content" type="button" role="tab">Violations</button>
//                             <button class="nav-link" id="heatmap-tab" data-bs-toggle="tab" data-bs-target="#heatmap-content" type="button" role="tab">Gaze Heatmap</button>
//                         </div>
//                     </nav>
//                     <div class="tab-content p-3 border border-top-0 rounded-bottom" id="student-tabContent">
//                         <div class="tab-pane fade show active" id="violations-content" role="tabpanel">
//                             <h5>Violation Log (${violationsData.success && violationsData.violations ? violationsData.violations.length : 0})</h5>`;
        
//         if (violationsData.success && violationsData.violations && violationsData.violations.length > 0) {
//             detailsHtml += '<div class="list-group" style="max-height: 300px; overflow-y: auto;">';
//             violationsData.violations.forEach(v => {
//                 const time = v.timestamp ? new Date(v.timestamp).toLocaleString() : 'N/A';
//                 detailsHtml += `
//                     <div class="list-group-item list-group-item-action flex-column align-items-start mb-2">
//                         <div class="d-flex w-100 justify-content-between">
//                             <h6 class="mb-1 text-danger">${v.object || 'Unknown'}</h6>
//                             <small class="text-muted">${time}</small>
//                         </div>
//                         <p class="mb-1 small">${v.details || `Confidence: ${v.confidence ? (v.confidence*100).toFixed(0)+'%' : 'N/A'}`}</p>
//                         ${v.severity_score ? `<small class="text-muted">Severity: ${v.severity_score.toFixed(1)}</small>` : ''}
//                     </div>`;
//             });
//             detailsHtml += '</div>';
//         } else {
//             detailsHtml += '<p>No violations recorded or error loading violations.</p>';
//         }
//         detailsHtml += `</div>
//                         <div class="tab-pane fade" id="heatmap-content" role="tabpanel">
//                             <h5>Gaze Tracking Statistics</h5>`;
//         if (heatmapData.success && heatmapData.stats && Object.keys(heatmapData.stats).length > 0) {
//             detailsHtml += '<ul class="list-unstyled">';
//             for (const [direction, percentage] of Object.entries(heatmapData.stats)) {
//                 detailsHtml += `<li>${capitalizeFirstLetter(direction.replace('_', ' '))}: ${percentage.toFixed(1)}%</li>`;
//             }
//             detailsHtml += '</ul>';
//             // Placeholder for actual heatmap image if you implement it
//             // detailsHtml += '<div class="text-center py-3"><img src="/api/student_heatmap_image/${studentId}" class="img-fluid border" alt="Heatmap"></div>';
//         } else {
//             detailsHtml += '<p>No heatmap data available or error loading data.</p>';
//         }
//         detailsHtml += `       </div>
//                     </div>
//                 </div>
//             </div>`;
//         studentDetailsContent.innerHTML = detailsHtml;

//     } catch (error) {
//         console.error("Error fetching student details:", error);
//         let errorMessage = "Failed to load student details.";
//         if (error.status === 404) errorMessage = "Student not found.";
//         else if (error.message) errorMessage = error.message;
//         studentDetailsContent.innerHTML = `<div class="alert alert-danger">${errorMessage}</div>`;
//     }
// }


// function clearStudentViolations(studentId) {
//     const deleteModalEl = document.getElementById('deleteConfirmationModal');
//     const deleteModal = bootstrap.Modal.getInstance(deleteModalEl) || new bootstrap.Modal(deleteModalEl);
//     const confirmBtn = document.getElementById('confirmDeleteBtn');
    
//     // Clone and replace the button to remove old event listeners
//     const newConfirmBtn = confirmBtn.cloneNode(true);
//     confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

//     newConfirmBtn.addEventListener('click', async function handleConfirm() {
//         newConfirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
//         newConfirmBtn.disabled = true;
        
//         try {
//             const response = await fetch('/clear_violations', {
//                 method: 'POST', 
//                 headers: {'Content-Type': 'application/json'},
//                 body: JSON.stringify({studentId: studentId})
//             });
//             const data = await response.json();
//             if (!response.ok || !data.success) {
//                 throw new Error(data.message || "Failed to clear violations");
//             }
//             alert('Violations cleared for student ' + studentId);
//             loadStudentsList(); // Refresh student list to show updated scores
//             if (document.getElementById('studentDetailsModal').classList.contains('show')) {
//                  viewStudentDetails(studentId); // Refresh details if modal is open
//             }
//         } catch (error) {
//             alert('Error clearing violations: ' + error.message);
//         } finally {
//             deleteModal.hide();
//             newConfirmBtn.innerHTML = 'Delete';
//             newConfirmBtn.disabled = false;
//         }
//     });
    
//     deleteModal.show();
// }

// // Exam questions functionality
// async function loadExamQuestions() {
//     const questionsListContainer = document.getElementById('questionsList');
//     questionsListContainer.innerHTML = '<div class="text-center p-4"><div class="spinner-border text-primary"></div><p class="mt-2">Loading exam questions...</p></div>';
    
//     try {
//         const response = await fetch('/api/questions');
//         if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
//         const questionsData = await response.json();
//         renderQuestionsList(questionsData);
//     } catch (error) {
//         console.error("Error fetching exam questions:", error);
//         questionsListContainer.innerHTML = '<div class="no-data-message text-danger">Failed to load exam questions.</div>';
//     }
// }

// function renderQuestionsList(questions) {
//     const questionsListContainer = document.getElementById('questionsList');
    
//     if (!questions || questions.length === 0) {
//         questionsListContainer.innerHTML = '<div class="no-data-message">No questions found. Add your first question!</div>';
//         return;
//     }
    
//     let html = '';
//     questions.sort((a, b) => (a.question_number || 0) - (b.question_number || 0)).forEach(question => {
//         html += `
//         <div class="question-card" data-id="${question._id}">
//             <div class="question-controls">
//                 <button class="btn btn-sm btn-outline-primary edit-question-btn" data-id="${question._id}">
//                     <i class="bx bx-edit"></i>
//                 </button>
//                 <button class="btn btn-sm btn-outline-danger delete-question-btn" data-id="${question._id}">
//                     <i class="bx bx-trash"></i>
//                 </button>
//             </div>
//             <h4>Question ${question.question_number}</h4>
//             <p>${question.text}</p>
//             <div class="options-list">
//                 <ol type="A" class="list-unstyled">
//                     ${question.options.map((option, index) => 
//                         `<li class="${index === question.correct_option_index ? 'text-success fw-bold' : ''}">
//                             ${String.fromCharCode(65 + index)}. ${option}
//                             ${index === question.correct_option_index ? ' <i class="bx bx-check-circle"></i>' : ''}
//                         </li>`
//                     ).join('')}
//                 </ol>
//             </div>
//         </div>`;
//     });
    
//     questionsListContainer.innerHTML = html;
    
//     document.querySelectorAll('.edit-question-btn').forEach(btn => {
//         btn.addEventListener('click', function() { editQuestion(this.getAttribute('data-id')); });
//     });
    
//     document.querySelectorAll('.delete-question-btn').forEach(btn => {
//         btn.addEventListener('click', function() { deleteQuestionPrompt(this.getAttribute('data-id')); });
//     });
// }

// function showAddQuestionForm(questionToEdit = null) {
//     editingQuestionId = questionToEdit ? questionToEdit._id : null;
//     document.getElementById('addQuestionForm').classList.remove('hidden');
//     document.getElementById('questionForm').reset(); // Clear form
    
//     const optionsContainer = document.getElementById('optionsContainer');
//     optionsContainer.innerHTML = ''; // Clear existing options

//     if (questionToEdit) {
//         document.getElementById('questionNumber').value = questionToEdit.question_number;
//         document.getElementById('questionText').value = questionToEdit.text;
//         questionToEdit.options.forEach((optText, index) => {
//             addQuestionOption(optText, index === questionToEdit.correct_option_index);
//         });
//     } else {
//         // Add 3 default empty options for new question
//         addQuestionOption('', true); // First option correct by default
//         addQuestionOption('');
//         addQuestionOption('');
//     }
//     updateOptionValues(); // Ensure radio values are correct
// }

// function hideAddQuestionForm() {
//     document.getElementById('addQuestionForm').classList.add('hidden');
//     editingQuestionId = null; // Reset editing state
//     document.getElementById('questionForm').reset();
// }

// async function saveQuestion(event) {
//     event.preventDefault();
    
//     const questionNumber = document.getElementById('questionNumber').value;
//     const questionText = document.getElementById('questionText').value;
    
//     const optionInputs = document.querySelectorAll('#optionsContainer input[type="text"]');
//     const options = Array.from(optionInputs).map(input => input.value.trim()).filter(opt => opt); // Filter out empty options
    
//     const correctOptionRadio = document.querySelector('#optionsContainer input[name="correctOption"]:checked');
//     const correctOptionIndex = correctOptionRadio ? parseInt(correctOptionRadio.value) : -1;
    
//     if (!questionNumber || !questionText || options.length < 2 || correctOptionIndex < 0 || correctOptionIndex >= options.length) {
//         alert('Please fill in question number, text, at least two non-empty options, and select a correct answer.');
//         return;
//     }
    
//     const questionData = {
//         question_number: parseInt(questionNumber),
//         text: questionText,
//         options: options,
//         correct_option_index: correctOptionIndex
//     };

//     const url = editingQuestionId ? `/api/questions/${editingQuestionId}` : '/api/questions';
//     const method = editingQuestionId ? 'PUT' : 'POST';

//     try {
//         const response = await fetch(url, {
//             method: method,
//             headers: {'Content-Type': 'application/json'},
//             body: JSON.stringify(questionData)
//         });
//         const result = await response.json();
//         if (!response.ok || !result.success) {
//             throw new Error(result.message || `Failed to ${editingQuestionId ? 'update' : 'save'} question`);
//         }
//         alert(`Question ${editingQuestionId ? 'updated' : 'saved'} successfully!`);
//         hideAddQuestionForm();
//         loadExamQuestions();
//     } catch (error) {
//         alert('Error: ' + error.message);
//     }
// }

// function addQuestionOption(text = '', isChecked = false) {
//     const optionsContainer = document.getElementById('optionsContainer');
//     const optionCount = optionsContainer.children.length;
    
//     const newOptionDiv = document.createElement('div');
//     newOptionDiv.className = 'input-group mb-2';
    
//     const inputGroupText = document.createElement('div');
//     inputGroupText.className = 'input-group-text';
//     const radioInput = document.createElement('input');
//     radioInput.type = 'radio';
//     radioInput.name = 'correctOption';
//     radioInput.value = optionCount; // This will be updated by updateOptionValues
//     radioInput.required = true;
//     if (isChecked) radioInput.checked = true;
//     inputGroupText.appendChild(radioInput);
    
//     const textInput = document.createElement('input');
//     textInput.type = 'text';
//     textInput.className = 'form-control';
//     textInput.placeholder = `Option ${optionCount + 1}`;
//     textInput.value = text;
//     textInput.required = true;
    
//     const removeBtn = document.createElement('button');
//     removeBtn.type = 'button';
//     removeBtn.className = 'btn btn-outline-danger remove-option';
//     removeBtn.innerHTML = '<i class="bx bx-x"></i>';
//     removeBtn.addEventListener('click', function() {
//         newOptionDiv.remove();
//         updateOptionValues();
//     });
    
//     newOptionDiv.appendChild(inputGroupText);
//     newOptionDiv.appendChild(textInput);
//     newOptionDiv.appendChild(removeBtn);
//     optionsContainer.appendChild(newOptionDiv);
//     updateOptionValues(); // ensure numbering is correct
// }

// function updateOptionValues() {
//     const radioInputs = document.querySelectorAll('#optionsContainer input[type="radio"]');
//     const textInputs = document.querySelectorAll('#optionsContainer input[type="text"]');
//     radioInputs.forEach((radio, index) => {
//         radio.value = index;
//         if (textInputs[index]) {
//             textInputs[index].placeholder = `Option ${index + 1}`;
//         }
//     });
// }

// async function editQuestion(questionId) {
//     try {
//         const response = await fetch(`/api/questions/${questionId}`);
//         if (!response.ok) throw new Error('Failed to fetch question details.');
//         const questionData = await response.json();
//         if (questionData) { // Assuming API returns the question object directly or under a key
//             showAddQuestionForm(questionData);
//         } else {
//             alert('Question not found or error fetching data.');
//         }
//     } catch (error) {
//         alert('Error: ' + error.message);
//     }
// }

// function deleteQuestionPrompt(questionId) {
//     const deleteModalEl = document.getElementById('deleteConfirmationModal');
//     const deleteModal = bootstrap.Modal.getInstance(deleteModalEl) || new bootstrap.Modal(deleteModalEl);
//     const confirmBtn = document.getElementById('confirmDeleteBtn');

//     // Clone and replace to remove old listeners
//     const newConfirmBtn = confirmBtn.cloneNode(true);
//     confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

//     newConfirmBtn.addEventListener('click', async function handleDeleteConfirm() {
//         newConfirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';
//         newConfirmBtn.disabled = true;
        
//         try {
//             const response = await fetch(`/api/questions/${questionId}`, { method: 'DELETE' });
//             const result = await response.json();
//             if (!response.ok || !result.success) {
//                 throw new Error(result.message || 'Failed to delete question.');
//             }
//             alert(`Question ${questionId} deleted successfully!`);
//             loadExamQuestions();
//         } catch (error) {
//             alert('Error: ' + error.message);
//         } finally {
//             deleteModal.hide();
//             newConfirmBtn.innerHTML = 'Delete';
//             newConfirmBtn.disabled = false;
//         }
//     });
//     deleteModal.show();
// }

// // Utility functions
// function getStatusClass(status) {
//     switch(status) {
//         case 'active': return 'bg-success';
//         case 'medium_risk': return 'bg-warning text-dark'; // Ensure text is readable on yellow
//         case 'high_risk': return 'bg-danger';
//         case 'completed': return 'bg-info text-dark'; // Ensure text is readable on light blue
//         default: return 'bg-secondary';
//     }
// }

// function capitalizeFirstLetter(string) {
//     if (!string) return '';
//     return string.charAt(0).toUpperCase() + string.slice(1);
// }

// function printStudentReport(studentId) {
//     // This is a simple browser print. For a more formatted report, you'd generate HTML content.
//     const studentDetailsContent = document.getElementById('studentDetailsContent').innerHTML;
//     const printWindow = window.open('', '_blank');
//     printWindow.document.write('<html><head><title>Student Report</title>');
//     // You might want to link Bootstrap CSS or a custom print CSS for better formatting
//     printWindow.document.write('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css">');
//     printWindow.document.write('<style>body{padding:20px;}.student-image{max-width:150px;}</style>');
//     printWindow.document.write('</head><body>');
//     printWindow.document.write(studentDetailsContent);
//     printWindow.document.write('</body></html>');
//     printWindow.document.close();
//     printWindow.onload = function() { // Wait for content to load
//         printWindow.print();
//         // printWindow.close(); // Optionally close after printing
//     };
// }

let editingQuestionId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize nav menu functionality
    initNavigation();
    
    // Load initial data for the default active section (Dashboard)
    loadDashboardData(); // This should be fine if initNavigation doesn't call it
    
    // Set up event listeners
    const refreshDashboardBtn = document.getElementById('refreshDashboard');
    if (refreshDashboardBtn) {
        refreshDashboardBtn.addEventListener('click', loadDashboardData);
    }
    
    const addQuestionBtn = document.getElementById('addQuestionBtn');
    if (addQuestionBtn) {
        addQuestionBtn.addEventListener('click', () => showAddQuestionForm(null));
    }

    const cancelQuestionBtn = document.getElementById('cancelQuestionBtn');
    if (cancelQuestionBtn) {
        cancelQuestionBtn.addEventListener('click', hideAddQuestionForm);
    }

    const questionForm = document.getElementById('questionForm');
    if (questionForm) {
        questionForm.addEventListener('submit', saveQuestion);
    }

    const addOptionBtn = document.getElementById('addOptionBtn');
    if (addOptionBtn) {
        addOptionBtn.addEventListener('click', addQuestionOption);
    }
    
    // Student search functionality
    const studentSearchInput = document.getElementById('studentSearch');
    if (studentSearchInput) {
        studentSearchInput.addEventListener('input', function() {
            filterStudents(this.value);
        });
    }
});

// Navigation functions
function initNavigation() {
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            const sectionId = this.getAttribute('data-section');
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });
            const targetSection = document.getElementById(sectionId);
            if (targetSection) {
                targetSection.classList.add('active');
            }
            
            if (sectionId === 'dashboard') {
                loadDashboardData();
            } else if (sectionId === 'students') {
                loadStudentsList();
            } else if (sectionId === 'exams') {
                loadExamQuestions();
            }
        });
    });
    if (navLinks.length > 0 && !document.querySelector('.sidebar .nav-link.active')) {
        navLinks[0].click();
    }
}

// Dashboard data loading
async function loadDashboardData() {
    // ... (your existing loadDashboardData function - seems okay)
    try {
        const response = await fetch('/api/dashboard_stats');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.success) {
            document.getElementById('studentCount').textContent = data.studentCount || '0';
            document.getElementById('questionCount').textContent = data.questionCount || '0';
            
            const recentActivityBody = document.getElementById('recentActivity');
            if (data.recentActivity && data.recentActivity.length > 0) {
                let activityHtml = '';
                data.recentActivity.forEach(activity => {
                    let activityTime = 'N/A';
                     if (activity.timestamp) {
                         try {
                             activityTime = new Date(activity.timestamp).toLocaleString();
                         } catch (e) { activityTime = activity.timestamp; }
                    }
                    activityHtml += `
                        <tr>
                            <td>${activityTime}</td>
                            <td>${activity.student_id || 'N/A'}</td>
                            <td>${activity.object || 'Unknown Activity'}</td>
                            <td><span class="badge ${activity.object === 'identity_mismatch' || (activity.severity_score && activity.severity_score > 5) ? 'bg-danger' : 'bg-warning'}">${activity.object === 'identity_mismatch' ? 'ID Mismatch' : 'Alert'}</span></td>
                        </tr>
                    `;
                });
                recentActivityBody.innerHTML = activityHtml;
            } else {
                recentActivityBody.innerHTML = '<tr><td colspan="4" class="text-center">No recent activity.</td></tr>';
            }
        } else {
            console.error("Failed to load dashboard stats:", data.message);
            if(document.getElementById('recentActivity')) {
                document.getElementById('recentActivity').innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading activity.</td></tr>';
            }
        }
    } catch (error) {
        console.error("Error fetching dashboard data:", error);
        if(document.getElementById('studentCount')) document.getElementById('studentCount').textContent = 'Error';
        if(document.getElementById('questionCount')) document.getElementById('questionCount').textContent = 'Error';
        if(document.getElementById('recentActivity')) {
            document.getElementById('recentActivity').innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading activity.</td></tr>';
        }
    }
}

// Students list functionality
async function loadStudentsList() {
    // ... (your existing loadStudentsList function - seems okay for fetching)
    const studentsListContainer = document.getElementById('studentsList');
    if (!studentsListContainer) return;
    studentsListContainer.innerHTML = '<div class="col-12 text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p>Loading student data...</p></div>';
    
    try {
        const response = await fetch('/api/students');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const studentsData = await response.json();
        renderStudentsList(studentsData); // Call renderStudentsList here
    } catch (error) {
        console.error("Error fetching students list:", error);
        studentsListContainer.innerHTML = '<div class="col-12 no-data-message"><h4 class="text-danger">Failed to load student data.</h4></div>';
    }
}

function renderStudentsList(students) {
    // ... (your existing renderStudentsList function - make sure data-id is student._id)
    const studentsListContainer = document.getElementById('studentsList');
    if (!studentsListContainer) return;
    
    if (!Array.isArray(students) && students.success === false) {
        studentsListContainer.innerHTML = `<div class="col-12 no-data-message"><h4>Error: ${students.message || "Could not load students."}</h4></div>`;
        return;
    }
    if (!students || students.length === 0) {
        studentsListContainer.innerHTML = '<div class="col-12 no-data-message"><h4>No students found.</h4></div>';
        return;
    }
    
    let html = '';
    students.forEach(student => {
        // Use student.fullName if available from your /api/students endpoint
        // Otherwise, construct from firstName and lastName if those are the fields
        const studentName = student.fullName || `${student.firstName || ''} ${student.lastName || ''}`.trim() || 'N/A';
        const enrollmentDate = student.enrollment_date ? new Date(student.enrollment_date).toLocaleDateString() : 'N/A';
        // Violation score will be fetched in viewStudentDetails for accuracy

        html += `
        <div class="col-md-6 col-lg-4 mb-4 student-item" data-student-name="${studentName.toLowerCase()}" data-student-id="${student._id ? student._id.toLowerCase() : ''}">
            <div class="card student-card h-100">
                <div class="card-body d-flex flex-column">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h5 class="card-title mb-0">${studentName}</h5>
                        <!-- Status badge might be added here later if needed -->
                    </div>
                    <p class="card-text small mb-1"><strong>ID:</strong> ${student._id || 'N/A'}</p>
                    <p class="card-text small mb-1"><strong>Email:</strong> ${student.email || 'N/A'}</p>
                    <p class="card-text small mb-1"><strong>Course:</strong> ${student.course || 'N/A'}</p>
                    <p class="card-text small mb-1"><strong>Enrolled:</strong> ${enrollmentDate}</p>
                    <div class="student-actions mt-auto">
                        <button class="btn btn-sm btn-primary view-student" data-id="${student._id}">View Details</button>
                        <button class="btn btn-sm btn-danger clear-violations-btn" data-id="${student._id}">Clear Violations</button>
                    </div>
                </div>
            </div>
        </div>`;
    });
    
    studentsListContainer.innerHTML = html;
    
    // Re-attach event listeners for dynamically created buttons
    document.querySelectorAll('.view-student').forEach(btn => {
        btn.addEventListener('click', function() { 
            // Ensure Bootstrap modal is correctly triggered if not using its event system
            const studentId = this.getAttribute('data-id');
            if (studentId) {
                viewStudentDetails(studentId); 
                // Manually show modal if not using data-bs-toggle/target
                var studentModal = new bootstrap.Modal(document.getElementById('studentDetailsModal'));
                studentModal.show();
            }
        });
    });
    
    document.querySelectorAll('.clear-violations-btn').forEach(btn => {
        btn.addEventListener('click', function() { clearStudentViolations(this.getAttribute('data-id')); });
    });
}


function filterStudents(searchTerm) {
    // ... (your existing filterStudents function - seems okay)
    const studentItems = document.querySelectorAll('#studentsList .student-item');
    searchTerm = searchTerm.toLowerCase();
    
    studentItems.forEach(item => {
        const name = item.getAttribute('data-student-name') || '';
        const id = item.getAttribute('data-student-id') || '';
        if (name.includes(searchTerm) || id.includes(searchTerm)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

async function viewStudentDetails(studentId) {
    // const modal = new bootstrap.Modal(document.getElementById('studentDetailsModal')); // Modal is shown by button now
    const studentDetailsContent = document.getElementById('studentDetailsContent');
    if (!studentDetailsContent) return;

    studentDetailsContent.innerHTML = `<div class="text-center"><div class="spinner-border text-primary"></div><p>Loading details for student ${studentId}...</p></div>`;
    // modal.show(); // Modal is shown by the button click that calls this function

    try {
        // Fetch student basic info (should include violation_score)
        // Fetch violations
        // Fetch heatmap (optional for this view, but your original code had it)
        const [studentRes, violationsRes, heatmapRes] = await Promise.all([
            fetch(`/api/students/${studentId}`).then(r => {
                if (!r.ok) return r.json().then(err => Promise.reject(err)); // Propagate error message
                return r.json();
            }),
            fetch(`/get_violations?studentId=${studentId}`).then(r => {
                 if (!r.ok) return r.json().then(err => Promise.reject(err));
                 return r.json();
            }),
            fetch(`/get_heatmap_data?studentId=${studentId}`).then(r => {
                 if (!r.ok) return r.json().then(err => Promise.reject(err));
                 return r.json();
            })
        ]);

        const student = studentRes; // This is the already parsed JSON
        const violationsData = violationsRes;
        const heatmapData = heatmapRes;
        
        // Check if student data itself is an error object (e.g., from a 404 or 400 in the studentRes fetch)
        if (student.success === false) { // Assuming your API returns {success: false, message: "..."} on error
            throw new Error(student.message || "Student data not found or invalid.");
        }
        
        // Use student.fullName (assuming it's returned by /api/students/:id)
        const studentName = student.fullName || `${student.firstName || ''} ${student.lastName || ''}`.trim() || 'N/A';
        const violationScoreValue = student.violation_score !== undefined ? parseFloat(student.violation_score).toFixed(2) : '0.00';

        let detailsHtml = `
            <div class="row">
                <div class="col-md-4">
                    <img src="https://via.placeholder.com/200x200.png?text=Student+Photo" class="student-image img-fluid rounded mb-3" alt="Student Photo">
                    <h4 class="mb-1">${studentName}</h4>
                    <p class="small text-muted mb-1">ID: ${student._id || 'N/A'}</p>
                    <div class="alert ${parseFloat(violationScoreValue) > 10 ? 'alert-danger' : (parseFloat(violationScoreValue) > 5 ? 'alert-warning' : 'alert-success')}">
                        <strong>Violation Score: ${violationScoreValue}</strong>
                    </div>
                    <p class="small text-muted mb-1">Email: ${student.email || 'N/A'}</p>
                    <p class="small text-muted mb-1">Course: ${student.course || 'N/A'}</p>
                    <p class="small text-muted mb-2">Enrolled: ${student.enrollment_date ? new Date(student.enrollment_date).toLocaleDateString() : 'N/A'}</p>
                    <button class="btn btn-sm btn-outline-secondary w-100" onclick="printStudentReport('${studentId}')">
                        <i class="bx bxs-printer"></i> Print Report
                    </button>
                </div>
                <div class="col-md-8">
                    <nav>
                        <div class="nav nav-tabs" id="student-details-tab-nav" role="tablist">
                            <button class="nav-link active" id="violations-pane-tab" data-bs-toggle="tab" data-bs-target="#violations-pane-content" type="button" role="tab">Violations</button>
                            <button class="nav-link" id="heatmap-pane-tab" data-bs-toggle="tab" data-bs-target="#heatmap-pane-content" type="button" role="tab">Gaze Stats</button>
                        </div>
                    </nav>
                    <div class="tab-content p-3 border border-top-0 rounded-bottom" id="student-details-tab-content">
                        <div class="tab-pane fade show active" id="violations-pane-content" role="tabpanel">
                            <h5>Violation Log (${violationsData.success && violationsData.violations ? violationsData.violations.length : 0})</h5>`;
        
        if (violationsData.success && violationsData.violations && violationsData.violations.length > 0) {
            detailsHtml += '<div class="list-group overflow-auto" style="max-height: 300px;">';
            // Sort by timestamp, most recent first
            violationsData.violations.sort((a,b) => {
                const dateA = a.timestamp ? new Date(a.timestamp) : 0;
                const dateB = b.timestamp ? new Date(b.timestamp) : 0;
                return dateB - dateA;
            }).forEach(v => {
                let time = 'N/A';
                if(v.timestamp) { try { time = new Date(v.timestamp).toLocaleString(); } catch(e){ time = v.timestamp; } }
                
                let detailText = '';
                if (v.details) { detailText = typeof v.details === 'object' ? JSON.stringify(v.details) : v.details; }
                else if (v.object === "multiple_persons" && v.count) { detailText = `Count: ${v.count}`; }
                else if (v.object && v.object.startsWith("prolonged_looking_") && v.duration) { detailText = `Duration: ${v.duration}s`; }
                else if (v.object === "identity_mismatch_final_check" && v.face_distance !== undefined) { detailText = `Face Dist: ${parseFloat(v.face_distance).toFixed(3)}`; }
                else if (v.confidence !== undefined) { detailText = `Confidence: ${(v.confidence*100).toFixed(0)}%`; }


                detailsHtml += `
                    <div class="list-group-item list-group-item-action flex-column align-items-start mb-2 p-2">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1 text-danger small">${v.object || 'Unknown'}</h6>
                            <small class="text-muted">${time}</small>
                        </div>
                        <p class="mb-1 small">${detailText}</p>
                        ${v.severity_score ? `<small class="text-muted fw-bold">Score: ${v.severity_score.toFixed(2)}</small>` : ''}
                    </div>`;
            });
            detailsHtml += '</div>';
        } else {
            detailsHtml += `<p class="text-muted">${violationsData.message || 'No violations recorded.'}</p>`;
        }
        detailsHtml += `</div>
                        <div class="tab-pane fade" id="heatmap-pane-content" role="tabpanel">
                            <h5>Gaze Tracking Statistics</h5>`;
        if (heatmapData.success && heatmapData.stats && Object.keys(heatmapData.stats).length > 0) {
            detailsHtml += '<ul class="list-unstyled">';
            for (const [direction, percentage] of Object.entries(heatmapData.stats)) {
                detailsHtml += `<li>${capitalizeFirstLetter(direction.replace(/_/g, ' '))}: ${percentage.toFixed(1)}%</li>`;
            }
            detailsHtml += '</ul>';
        } else {
            detailsHtml += `<p class="text-muted">${heatmapData.message || 'No heatmap data available.'}</p>`;
        }
        detailsHtml += `       </div>
                    </div>
                </div>
            </div>`;
        studentDetailsContent.innerHTML = detailsHtml;

    } catch (error) {
        console.error("Error fetching student details in viewStudentDetails:", error);
        let errorMessageText = "Failed to load student details.";
        if (error && error.message) { // If error is an object with a message (like from Promise.reject(err))
            errorMessageText = error.message;
        } else if (error && typeof error.json === 'function') { // If error is a Response object
             try {
                const errorJson = await error.json();
                errorMessageText = errorJson.message || `HTTP Error: ${error.status}`;
            } catch (parseError) {
                errorMessageText = `HTTP Error: ${error.status || 'Unknown'}`;
            }
        } else if (typeof error === 'string') {
            errorMessageText = error;
        }
        studentDetailsContent.innerHTML = `<div class="alert alert-danger">${errorMessageText}</div>`;
    }
}

// ... (Rest of your functions: clearStudentViolations, loadExamQuestions, renderQuestionsList, showAddQuestionForm, etc. should be largely okay but review for consistency if issues arise)
// Make sure clearStudentViolations also re-fetches details if modal is open
function clearStudentViolations(studentId) {
    const deleteModalEl = document.getElementById('deleteConfirmationModal');
    if (!deleteModalEl) return;
    const deleteModal = bootstrap.Modal.getInstance(deleteModalEl) || new bootstrap.Modal(deleteModalEl);
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (!confirmBtn) return;
    
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    newConfirmBtn.addEventListener('click', async function handleConfirm() {
        newConfirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
        newConfirmBtn.disabled = true;
        
        try {
            const response = await fetch('/clear_violations', {
                method: 'POST', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({studentId: studentId})
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.message || "Failed to clear violations");
            }
            alert('Violations cleared for student ' + studentId);
            loadStudentsList(); // Refresh student list to show updated scores (if violation score was on card)
            
            // Refresh modal if it's open for THIS student
            const studentDetailsModalEl = document.getElementById('studentDetailsModal');
            const studentDetailsContentEl = document.getElementById('studentDetailsContent');
            if (studentDetailsModalEl && studentDetailsModalEl.classList.contains('show') && 
                studentDetailsContentEl && studentDetailsContentEl.innerHTML.includes(studentId)) {
                 viewStudentDetails(studentId);
            }
        } catch (error) {
            alert('Error clearing violations: ' + error.message);
        } finally {
            deleteModal.hide();
            newConfirmBtn.innerHTML = 'Delete';
            newConfirmBtn.disabled = false;
        }
    });
    deleteModal.show();
}

// Exam questions functionality
async function loadExamQuestions() {
    const questionsListContainer = document.getElementById('questionsList');
    if (!questionsListContainer) return;
    questionsListContainer.innerHTML = '<div class="text-center p-4"><div class="spinner-border text-primary"></div><p class="mt-2">Loading exam questions...</p></div>';
    
    try {
        const response = await fetch('/api/questions');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const questionsData = await response.json();
        renderQuestionsList(questionsData);
    } catch (error) {
        console.error("Error fetching exam questions:", error);
        questionsListContainer.innerHTML = '<div class="no-data-message text-danger">Failed to load exam questions.</div>';
    }
}

function renderQuestionsList(questions) {
    const questionsListContainer = document.getElementById('questionsList');
    if (!questionsListContainer) return;
    
    if (!Array.isArray(questions) && questions.success === false) {
        questionsListContainer.innerHTML = `<div class="no-data-message text-danger">${questions.message || "Error loading questions."}</div>`;
        return;
    }
    if (!questions || questions.length === 0) {
        questionsListContainer.innerHTML = '<div class="no-data-message">No questions found. Add your first question!</div>';
        return;
    }
    
    let html = '';
    questions.sort((a, b) => (a.question_number || 0) - (b.question_number || 0)).forEach(question => {
        html += `
        <div class="question-card" data-id="${question._id}">
            <div class="question-controls">
                <button class="btn btn-sm btn-outline-primary edit-question-btn" data-id="${question._id}">
                    <i class="bx bx-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger delete-question-btn" data-id="${question._id}">
                    <i class="bx bx-trash"></i>
                </button>
            </div>
            <h4>Question ${question.question_number || ''}</h4>
            <p>${question.text || 'N/A'}</p>
            <div class="options-list">
                <ol type="A" class="list-unstyled">
                    ${(question.options || []).map((option, index) => 
                        `<li class="${index === question.correct_option_index ? 'text-success fw-bold' : ''}">
                            ${String.fromCharCode(65 + index)}. ${option}
                            ${index === question.correct_option_index ? ' <i class="bx bx-check-circle"></i>' : ''}
                        </li>`
                    ).join('')}
                </ol>
            </div>
        </div>`;
    });
    
    questionsListContainer.innerHTML = html;
    
    document.querySelectorAll('.edit-question-btn').forEach(btn => {
        btn.addEventListener('click', function() { editQuestion(this.getAttribute('data-id')); });
    });
    
    document.querySelectorAll('.delete-question-btn').forEach(btn => {
        btn.addEventListener('click', function() { deleteQuestionPrompt(this.getAttribute('data-id')); });
    });
}

function showAddQuestionForm(questionToEdit = null) {
    const addQuestionFormDiv = document.getElementById('addQuestionForm');
    const questionFormEl = document.getElementById('questionForm');
    const optionsContainer = document.getElementById('optionsContainer');

    if (!addQuestionFormDiv || !questionFormEl || !optionsContainer) return;

    editingQuestionId = questionToEdit ? questionToEdit._id : null;
    addQuestionFormDiv.classList.remove('hidden');
    questionFormEl.reset();
    
    document.querySelector('#addQuestionForm h4').textContent = questionToEdit ? 'Edit Question' : 'Add New Question';
    optionsContainer.innerHTML = ''; 

    if (questionToEdit) {
        document.getElementById('questionNumber').value = questionToEdit.question_number || '';
        document.getElementById('questionText').value = questionToEdit.text || '';
        (questionToEdit.options || []).forEach((optText, index) => {
            addQuestionOption(optText, index === questionToEdit.correct_option_index);
        });
    } else {
        addQuestionOption('', true);
        addQuestionOption('');
        addQuestionOption('');
    }
    updateOptionValues();
    addQuestionFormDiv.scrollIntoView({ behavior: 'smooth' });
}

function hideAddQuestionForm() {
    const addQuestionFormDiv = document.getElementById('addQuestionForm');
    const questionFormEl = document.getElementById('questionForm');
    if (!addQuestionFormDiv || !questionFormEl) return;

    addQuestionFormDiv.classList.add('hidden');
    editingQuestionId = null;
    questionFormEl.reset();
}

async function saveQuestion(event) {
    event.preventDefault();
    
    const questionNumber = document.getElementById('questionNumber').value;
    const questionText = document.getElementById('questionText').value;
    
    const optionInputs = document.querySelectorAll('#optionsContainer input[type="text"]');
    const options = Array.from(optionInputs).map(input => input.value.trim()).filter(opt => opt);
    
    const correctOptionRadio = document.querySelector('#optionsContainer input[name="correctOption"]:checked');
    const correctOptionIndex = correctOptionRadio ? parseInt(correctOptionRadio.value) : -1;
    
    if (!questionNumber || !questionText || options.length < 2 || correctOptionIndex < 0 || correctOptionIndex >= options.length) {
        alert('Please fill in question number, text, at least two non-empty options, and select a correct answer.');
        return;
    }
    
    const questionData = {
        question_number: parseInt(questionNumber),
        text: questionText,
        options: options,
        correct_option_index: correctOptionIndex
    };

    const url = editingQuestionId ? `/api/questions/${editingQuestionId}` : '/api/questions';
    const method = editingQuestionId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(questionData)
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.message || `Failed to ${editingQuestionId ? 'update' : 'save'} question`);
        }
        alert(`Question ${editingQuestionId ? 'updated' : 'saved'} successfully!`);
        hideAddQuestionForm();
        loadExamQuestions();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function addQuestionOption(text = '', isChecked = false) {
    const optionsContainer = document.getElementById('optionsContainer');
    if (!optionsContainer) return;
    const optionCount = optionsContainer.children.length;
    
    const newOptionDiv = document.createElement('div');
    newOptionDiv.className = 'input-group mb-2';
    
    const inputGroupText = document.createElement('div');
    inputGroupText.className = 'input-group-text';
    const radioInput = document.createElement('input');
    radioInput.type = 'radio';
    radioInput.name = 'correctOption';
    radioInput.value = optionCount;
    radioInput.required = true;
    if (isChecked) radioInput.checked = true;
    inputGroupText.appendChild(radioInput);
    
    const textInput = document.createElement('input');
    textInput.type = 'text';
    textInput.className = 'form-control';
    textInput.placeholder = `Option ${optionCount + 1}`;
    textInput.value = text;
    textInput.required = true;
    
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-outline-danger remove-option';
    removeBtn.innerHTML = '<i class="bx bx-x"></i>';
    removeBtn.addEventListener('click', function() {
        newOptionDiv.remove();
        updateOptionValues();
    });
    
    newOptionDiv.appendChild(inputGroupText);
    newOptionDiv.appendChild(textInput);
    newOptionDiv.appendChild(removeBtn);
    optionsContainer.appendChild(newOptionDiv);
    updateOptionValues();
}

function updateOptionValues() {
    const radioInputs = document.querySelectorAll('#optionsContainer input[type="radio"]');
    const textInputs = document.querySelectorAll('#optionsContainer input[type="text"]');
    radioInputs.forEach((radio, index) => {
        radio.value = index;
        if (textInputs[index]) {
            textInputs[index].placeholder = `Option ${index + 1}`;
        }
    });
    if (radioInputs.length > 0 && !document.querySelector('#optionsContainer input[name="correctOption"]:checked')) {
        radioInputs[0].checked = true;
    }
}

async function editQuestion(questionId) {
    try {
        const response = await fetch(`/api/questions/${questionId}`);
        if (!response.ok) throw new Error('Failed to fetch question details.');
        const questionData = await response.json();
        if (questionData && questionData._id) {
            showAddQuestionForm(questionData);
        } else {
            alert(questionData.message || 'Question not found or error fetching data.');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function deleteQuestionPrompt(questionId) {
    const deleteModalEl = document.getElementById('deleteConfirmationModal');
    if(!deleteModalEl) return;
    const deleteModal = bootstrap.Modal.getInstance(deleteModalEl) || new bootstrap.Modal(deleteModalEl);
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if(!confirmBtn) return;

    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    newConfirmBtn.addEventListener('click', async function handleDeleteConfirm() {
        newConfirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';
        newConfirmBtn.disabled = true;
        
        try {
            const response = await fetch(`/api/questions/${questionId}`, { method: 'DELETE' });
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.message || 'Failed to delete question.');
            }
            alert(`Question ${questionId} deleted successfully!`);
            loadExamQuestions();
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            deleteModal.hide();
            newConfirmBtn.innerHTML = 'Delete';
            newConfirmBtn.disabled = false;
        }
    });
    deleteModal.show();
}

// Utility functions
function getStatusClass(status) {
    switch(status) {
        case 'active': return 'bg-success';
        case 'medium_risk': return 'bg-warning text-dark';
        case 'high_risk': return 'bg-danger';
        case 'completed': return 'bg-info text-dark';
        default: return 'bg-secondary';
    }
}

function capitalizeFirstLetter(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function printStudentReport(studentId) {
    const studentDetailsContentEl = document.getElementById('studentDetailsContent');
    if(!studentDetailsContentEl) {
        alert("Cannot print report: Details content not found.");
        return;
    }
    const studentDetailsContent = studentDetailsContentEl.innerHTML;
    const printWindow = window.open('', '_blank');
    if(!printWindow) {
        alert("Cannot open print window. Please check your browser's pop-up blocker settings.");
        return;
    }
    printWindow.document.write('<html><head><title>Student Report - ID: ' + studentId + '</title>');
    printWindow.document.write('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css">');
    printWindow.document.write('<style>body{padding:20px;}.student-image{max-width:150px;} #student-details-tab-nav, .btn-outline-secondary { display: none !important; } .tab-content > .tab-pane { display: block !important; opacity: 1 !important; }</style>');
    printWindow.document.write('</head><body>');
    printWindow.document.write(`<h3>Student Report - ID: ${studentId}</h3><hr>`);
    printWindow.document.write(studentDetailsContent);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.onload = function() { 
        printWindow.print();
    };
}