/**
 * UMBC Degree Planner - Main Application JavaScript
 * Handles student selection, path optimization, and AI chat functionality
 */

class DegreePlanner {
    constructor() {
        this.selectedStudent = null;
        this.optimizedPath = null;
        this.charts = {};
        
        this.initializeEventListeners();
        this.loadStudents();
    }

    initializeEventListeners() {
        // Student search functionality
        document.getElementById('studentSearch').addEventListener('input', (e) => {
            this.filterStudents(e.target.value);
        });

        // Optimize path button
        document.getElementById('optimizeBtn').addEventListener('click', () => {
            if (this.selectedStudent) {
                this.optimizePath(this.selectedStudent.id);
            }
        });

        // Chat functionality
        document.getElementById('sendChatBtn').addEventListener('click', () => {
            this.sendChatMessage();
        });

        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendChatMessage();
            }
        });

        // Tab switching
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.handleTabSwitch(e.target.getAttribute('data-bs-target'));
            });
        });
    }

    async loadStudents() {
        try {
            const response = await fetch('/api/students');
            const data = await response.json();
            
            if (data.success) {
                this.renderStudentList(data.students);
            } else {
                this.showError('Failed to load students: ' + data.error);
            }
        } catch (error) {
            console.error('Error loading students:', error);
            this.showError('Failed to load students');
        }
    }

    renderStudentList(students) {
        const studentList = document.getElementById('studentList');
        
        if (!students || students.length === 0) {
            studentList.innerHTML = '<div class="text-center text-muted">No students found</div>';
            return;
        }

        studentList.innerHTML = students.map(student => `
            <div class="student-item" data-student-id="${student.id}" onclick="app.selectStudent('${student.id}')">
                <h6>${student.name || 'Unknown'}</h6>
                <small>
                    <div><i class="fas fa-graduation-cap me-1"></i>${student.degree_name || 'No degree'}</div>
                    <div><i class="fas fa-brain me-1"></i>${student.learning_style || 'Unknown'}</div>
                </small>
            </div>
        `).join('');
    }

    filterStudents(searchTerm) {
        const studentItems = document.querySelectorAll('.student-item');
        const term = searchTerm.toLowerCase();

        studentItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(term)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }

    async selectStudent(studentId) {
        try {
            // Update UI to show selected student
            document.querySelectorAll('.student-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelector(`[data-student-id="${studentId}"]`).classList.add('active');

            // Load student details
            const response = await fetch(`/api/student/${studentId}`);
            const data = await response.json();

            if (data.success) {
                this.selectedStudent = data.student;
                this.renderStudentInfo(data);
                this.showPlanningInterface();
                this.loadOverviewData(data);
            } else {
                this.showError('Failed to load student details: ' + data.error);
            }
        } catch (error) {
            console.error('Error selecting student:', error);
            this.showError('Failed to load student details');
        }
    }

    renderStudentInfo(data) {
        const student = data.student;
        const studentInfoPanel = document.getElementById('studentInfoPanel');
        const studentInfo = document.getElementById('studentInfo');

        studentInfo.innerHTML = `
            <div class="student-info-item">
                <span class="student-info-label">Name</span>
                <span class="student-info-value">${student.name}</span>
            </div>
            <div class="student-info-item">
                <span class="student-info-label">Learning Style</span>
                <span class="student-info-value">
                    <i class="fas fa-brain me-1"></i>${student.learning_style}
                </span>
            </div>
            <div class="student-info-item">
                <span class="student-info-label">Degree</span>
                <span class="student-info-value">${student.degree_name}</span>
            </div>
            <div class="student-info-item">
                <span class="student-info-label">Expected Graduation</span>
                <span class="student-info-value">${student.expected_graduation}</span>
            </div>
            <div class="student-info-item">
                <span class="student-info-label">Preferred Load</span>
                <span class="student-info-value">${student.preferred_course_load} courses</span>
            </div>
            <div class="student-info-item">
                <span class="student-info-label">Work Hours</span>
                <span class="student-info-value">${student.work_hours_per_week}h/week</span>
            </div>
            <div class="student-info-item">
                <span class="student-info-label">Completed Courses</span>
                <span class="student-info-value">${data.completed_courses.length}</span>
            </div>
        `;

        studentInfoPanel.style.display = 'block';
    }

    showPlanningInterface() {
        document.getElementById('welcomeMessage').style.display = 'none';
        document.getElementById('planningInterface').style.display = 'block';
    }

    loadOverviewData(studentData) {
        this.renderDegreeProgress(studentData);
        this.renderTimelineOverview();
        this.renderRiskFactors([]);
    }

    renderDegreeProgress(studentData) {
        const degreeProgress = document.getElementById('degreeProgress');
        const completed = studentData.completed_courses.length;
        const enrolled = studentData.enrolled_courses.length;
        const totalCreditsCompleted = studentData.completed_courses.reduce((sum, course) => sum + (course.credits || 3), 0);
        const totalCreditsRequired = studentData.degree_info?.total_credits || 120;
        const progressPercentage = (totalCreditsCompleted / totalCreditsRequired * 100).toFixed(1);

        degreeProgress.innerHTML = `
            <div class="text-center mb-4">
                <div class="progress-circle">
                    <canvas id="progressChart" width="200" height="200"></canvas>
                </div>
            </div>
            <div class="row text-center">
                <div class="col-4">
                    <div class="stat-item">
                        <h4 class="text-success">${completed}</h4>
                        <small>Completed</small>
                    </div>
                </div>
                <div class="col-4">
                    <div class="stat-item">
                        <h4 class="text-info">${enrolled}</h4>
                        <small>Enrolled</small>
                    </div>
                </div>
                <div class="col-4">
                    <div class="stat-item">
                        <h4 class="text-primary">${totalCreditsCompleted}</h4>
                        <small>Credits</small>
                    </div>
                </div>
            </div>
            <div class="mt-3">
                <div class="d-flex justify-content-between mb-2">
                    <span>Progress to Graduation</span>
                    <span>${progressPercentage}%</span>
                </div>
                <div class="progress">
                    <div class="progress-bar bg-success" style="width: ${progressPercentage}%"></div>
                </div>
            </div>
        `;

        // Create progress chart
        this.createProgressChart(progressPercentage);
    }

    createProgressChart(percentage) {
        const ctx = document.getElementById('progressChart');
        if (!ctx) return;

        // Clear existing chart
        if (this.charts.progress) {
            this.charts.progress.destroy();
        }

        this.charts.progress = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [percentage, 100 - percentage],
                    backgroundColor: ['#28a745', '#e9ecef'],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: '70%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                responsive: false
            },
            plugins: [{
                beforeDraw: (chart) => {
                    const ctx = chart.ctx;
                    ctx.save();
                    const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
                    const centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = 'bold 24px Arial';
                    ctx.fillStyle = '#28a745';
                    ctx.fillText(`${percentage.toFixed(0)}%`, centerX, centerY);
                    ctx.restore();
                }
            }]
        });
    }

    renderTimelineOverview() {
        const timelineOverview = document.getElementById('timelineOverview');
        timelineOverview.innerHTML = `
            <div class="text-center">
                <p class="text-muted">Click "Optimize Path" to generate a detailed timeline</p>
                <button class="btn btn-outline-primary btn-sm" onclick="document.getElementById('pathway-tab').click()">
                    <i class="fas fa-route me-1"></i>Generate Timeline
                </button>
            </div>
        `;
    }

    renderRiskFactors(risks) {
        const riskFactors = document.getElementById('riskFactors');
        
        if (!risks || risks.length === 0) {
            riskFactors.innerHTML = `
                <div class="text-center text-success">
                    <i class="fas fa-check-circle fa-2x mb-2"></i>
                    <p>No significant risk factors identified</p>
                    <small class="text-muted">Generate optimal path for detailed risk analysis</small>
                </div>
            `;
            return;
        }

        riskFactors.innerHTML = risks.map(risk => `
            <div class="alert alert-${this.getRiskSeverityClass(risk.severity)} mb-2">
                <h6><i class="fas fa-exclamation-triangle me-2"></i>${risk.type}</h6>
                <p class="mb-1">${risk.description}</p>
                <small><strong>Recommendation:</strong> ${risk.recommendation}</small>
            </div>
        `).join('');
    }

    getRiskSeverityClass(severity) {
        switch (severity?.toLowerCase()) {
            case 'high': return 'danger';
            case 'medium': return 'warning';
            case 'low': return 'info';
            default: return 'secondary';
        }
    }

    async optimizePath(studentId) {
        try {
            this.showLoadingModal('Optimizing graduation path...');

            const response = await fetch(`/api/optimize-path/${studentId}`);
            const data = await response.json();

            if (data.success) {
                this.optimizedPath = data.path;
                this.renderOptimalPath(data.path);
                this.renderRiskFactors(data.path.risk_factors);
                this.loadRecommendations(studentId);
                
                // Switch to pathway tab
                document.getElementById('pathway-tab').click();
            } else {
                this.showError('Failed to optimize path: ' + data.error);
            }
        } catch (error) {
            console.error('Error optimizing path:', error);
            this.showError('Failed to optimize graduation path');
        } finally {
            this.hideLoadingModal();
        }
    }

    renderOptimalPath(pathData) {
        const pathwayContent = document.getElementById('pathwayContent');
        
        if (!pathData.term_plan || pathData.term_plan.length === 0) {
            pathwayContent.innerHTML = '<div class="text-center">No course plan generated</div>';
            return;
        }

        const timelineHtml = pathData.term_plan.map((term, index) => `
            <div class="term-card card">
                <div class="term-header">
                    <div>
                        <h5 class="mb-1">Term ${term.term_number} - ${term.term_type}</h5>
                        <span class="risk-badge risk-${term.risk_level.toLowerCase()}">${term.risk_level} Risk</span>
                    </div>
                    <div class="term-info">
                        <div class="term-stat">
                            <div class="term-stat-value">${term.courses.length}</div>
                            <div class="term-stat-label">Courses</div>
                        </div>
                        <div class="term-stat">
                            <div class="term-stat-value">${term.total_credits}</div>
                            <div class="term-stat-label">Credits</div>
                        </div>
                        <div class="term-stat">
                            <div class="term-stat-value">${term.estimated_difficulty.toFixed(1)}</div>
                            <div class="term-stat-label">Difficulty</div>
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    ${term.courses.map(course => `
                        <div class="course-item">
                            <div class="course-title">${course.course_name}</div>
                            <div class="course-meta">
                                <span><i class="fas fa-hashtag me-1"></i>${course.course_id}</span>
                                <span><i class="fas fa-credit-card me-1"></i>${course.credits} credits</span>
                                <span><i class="fas fa-signal me-1"></i>Level ${course.level}</span>
                                <span class="difficulty-indicator">
                                    ${this.renderDifficultyStars(course.difficulty_prediction)}
                                </span>
                            </div>
                            ${course.prerequisites && course.prerequisites.length > 0 ? `
                                <div class="mt-2">
                                    <small><strong>Prerequisites:</strong> ${course.prerequisites.map(p => p.course_name).join(', ')}</small>
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

        pathwayContent.innerHTML = `
            <div class="mb-4">
                <div class="row text-center">
                    <div class="col-md-3">
                        <h4 class="text-primary">${pathData.total_terms_remaining}</h4>
                        <small>Terms Remaining</small>
                    </div>
                    <div class="col-md-3">
                        <h4 class="text-success">${pathData.estimated_graduation}</h4>
                        <small>Est. Graduation</small>
                    </div>
                    <div class="col-md-3">
                        <h4 class="text-info">${pathData.optimal_sequence.length}</h4>
                        <small>Courses Planned</small>
                    </div>
                    <div class="col-md-3">
                        <h4 class="text-warning">${pathData.risk_factors.length}</h4>
                        <small>Risk Factors</small>
                    </div>
                </div>
            </div>
            
            <div class="timeline">
                ${timelineHtml}
            </div>
        `;
    }

    renderDifficultyStars(difficulty) {
        const stars = [];
        const roundedDifficulty = Math.round(difficulty);
        
        for (let i = 1; i <= 5; i++) {
            if (i <= roundedDifficulty) {
                stars.push('<i class="fas fa-star difficulty-star"></i>');
            } else {
                stars.push('<i class="fas fa-star difficulty-star empty"></i>');
            }
        }
        
        return stars.join('');
    }

    async loadRecommendations(studentId) {
        try {
            // Load course recommendations
            const response = await fetch(`/api/course-recommendations/${studentId}`);
            const data = await response.json();

            if (data.success) {
                this.renderCourseRecommendations(data.recommendations);
            }

            // Load similar students
            const similarResponse = await fetch(`/api/similar-students/${studentId}`);
            const similarData = await similarResponse.json();

            if (similarData.success) {
                this.renderPeerInsights(similarData.similar_students);
            }
        } catch (error) {
            console.error('Error loading recommendations:', error);
        }
    }

    renderCourseRecommendations(recommendations) {
        const nextTermRecommendations = document.getElementById('nextTermRecommendations');
        
        if (!recommendations || recommendations.length === 0) {
            nextTermRecommendations.innerHTML = '<div class="text-center text-muted">No recommendations available</div>';
            return;
        }

        nextTermRecommendations.innerHTML = recommendations.map(course => `
            <div class="recommendation-item">
                <div class="recommendation-score">${(course.recommendation_score || 0).toFixed(0)}</div>
                <h6>${course.course_name}</h6>
                <div class="course-meta">
                    <span><i class="fas fa-hashtag me-1"></i>${course.course_id}</span>
                    <span><i class="fas fa-credit-card me-1"></i>${course.credits} credits</span>
                    <span><i class="fas fa-signal me-1"></i>Level ${course.level}</span>
                </div>
                <div class="mt-2">
                    <span class="difficulty-indicator">
                        Difficulty: ${this.renderDifficultyStars(course.difficulty_prediction)}
                    </span>
                    <span class="ms-3">Learning Style Match: ${(course.learning_style_match * 100).toFixed(0)}%</span>
                </div>
                ${course.prerequisites && course.prerequisites.length > 0 ? `
                    <div class="mt-2">
                        <small><strong>Prerequisites:</strong></small>
                        ${course.prerequisites.map(p => `
                            <div class="prerequisite-item">${p.course_name}</div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    renderPeerInsights(similarStudents) {
        const peerInsights = document.getElementById('peerInsights');
        
        if (!similarStudents || similarStudents.length === 0) {
            peerInsights.innerHTML = '<div class="text-center text-muted">No similar students found</div>';
            return;
        }

        peerInsights.innerHTML = `
            <div class="mb-3">
                <p>Found ${similarStudents.length} students with similar profiles:</p>
            </div>
            ${similarStudents.map(student => `
                <div class="card mb-2">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1">${student.name}</h6>
                                <small class="text-muted">
                                    ${student.learning_style} • GPA: ${(student.avg_gpa || 0).toFixed(2)} • 
                                    ${student.courses_completed} courses
                                </small>
                            </div>
                            <div class="text-end">
                                <div class="text-primary font-weight-bold">
                                    ${(student.similarity * 100).toFixed(0)}%
                                </div>
                                <small class="text-muted">Match</small>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('')}
        `;
    }

    async sendChatMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();
        
        if (!message) return;

        // Add user message to chat
        this.addChatMessage(message, 'user');
        chatInput.value = '';

        try {
            // Show typing indicator
            this.addChatMessage('AI is thinking...', 'bot', 'typing');

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    student_id: this.selectedStudent?.id,
                    context: {
                        optimal_sequence: this.optimizedPath?.optimal_sequence,
                        term_plan: this.optimizedPath?.term_plan,
                        risk_factors: this.optimizedPath?.risk_factors
                    }
                })
            });

            const data = await response.json();

            // Remove typing indicator
            this.removeChatMessage('typing');

            if (data.success) {
                this.addChatMessage(data.response, 'bot');
            } else {
                this.addChatMessage('Sorry, I encountered an error: ' + data.error, 'bot');
            }
        } catch (error) {
            this.removeChatMessage('typing');
            this.addChatMessage('Sorry, I encountered a technical error. Please try again.', 'bot');
            console.error('Chat error:', error);
        }
    }

    addChatMessage(message, sender, id = null) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}-message`;
        if (id) messageDiv.id = id;
        
        messageDiv.innerHTML = `
            <i class="fas fa-${sender === 'user' ? 'user' : 'robot'} me-2"></i>
            <div class="message-content">
                <strong>${sender === 'user' ? 'You' : 'AI Advisor'}:</strong>
                ${message.replace(/\n/g, '<br>')}
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    removeChatMessage(id) {
        const message = document.getElementById(id);
        if (message) {
            message.remove();
        }
    }

    handleTabSwitch(tabId) {
        // Handle any specific logic when tabs are switched
        switch (tabId) {
            case '#recommendations':
                if (this.selectedStudent && !this.optimizedPath) {
                    this.loadRecommendations(this.selectedStudent.id);
                }
                break;
        }
    }

    showLoadingModal(text) {
        document.getElementById('loadingText').textContent = text;
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        modal.show();
    }

    hideLoadingModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (modal) modal.hide();
    }

    showError(message) {
        // Simple error display - could be enhanced with toast notifications
        alert('Error: ' + message);
    }
}

// Initialize the application when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new DegreePlanner();
});
