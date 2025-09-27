#!/usr/bin/env python3
"""
Gemini AI Client for UMBC Degree Planner
Integrates Google Gemini for personalized academic advice and recommendations
"""

import os
import logging
from typing import Dict, Optional, List
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        """Initialize Gemini AI client"""
        self.api_key = os.getenv('GOOGLE_API_KEY')
        
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found - Gemini features will be disabled")
            self.model = None
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini AI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {e}")
            self.model = None

    def test_connection(self) -> bool:
        """Test if Gemini AI is working"""
        if not self.model:
            return False
        
        try:
            response = self.model.generate_content("Test connection. Respond with 'OK'.")
            return "OK" in response.text
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False

    def get_academic_advice(self, message: str, student_context: Optional[Dict] = None, 
                          additional_context: Optional[Dict] = None) -> str:
        """
        Get personalized academic advice from Gemini AI
        
        Args:
            message: User's question or request
            student_context: Student's academic data and history
            additional_context: Additional context like course data, similar students, etc.
        """
        if not self.model:
            return "AI assistant is currently unavailable. Please check your API configuration."
        
        try:
            # Construct comprehensive prompt
            prompt = self._build_advisor_prompt(message, student_context, additional_context)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            if not response.text:
                return "I'm sorry, I couldn't generate a response. Please try rephrasing your question."
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error getting Gemini response: {e}")
            return f"I encountered an error while processing your request: {str(e)}"

    def _build_advisor_prompt(self, message: str, student_context: Optional[Dict], 
                            additional_context: Optional[Dict]) -> str:
        """Build comprehensive prompt for academic advising"""
        
        # Base system prompt
        system_prompt = """You are an expert academic advisor at UMBC (University of Maryland, Baltimore County). 
        You specialize in helping students optimize their degree paths, improve academic performance, and make informed decisions about their education.

        Your responses should be:
        - Personalized and specific to the student's situation
        - Practical and actionable
        - Encouraging but realistic
        - Based on data when available
        - Focused on academic success and well-being

        When discussing courses:
        - Consider prerequisites and scheduling
        - Account for course difficulty and student workload
        - Suggest study strategies based on learning styles
        - Recommend resources and support services

        Always maintain a supportive, professional tone while being direct about challenges and opportunities.
        """

        # Add student context if available
        context_section = ""
        if student_context and student_context.get('student'):
            context_section += self._format_student_context(student_context)
        
        if additional_context:
            context_section += self._format_additional_context(additional_context)

        # Combine all parts
        full_prompt = f"{system_prompt}\n\n{context_section}\n\nStudent Question: {message}\n\nResponse:"
        
        return full_prompt

    def _format_student_context(self, context: Dict) -> str:
        """Format student context for the AI prompt"""
        student = context.get('student', {})
        completed_courses = context.get('completed_courses', [])
        degree_info = context.get('degree_info', {})
        available_courses = context.get('available_courses', [])
        similar_students = context.get('similar_students', [])
        
        context_text = "=== STUDENT PROFILE ===\n"
        context_text += f"Name: {student.get('name', 'Student')}\n"
        context_text += f"Learning Style: {student.get('learning_style', 'Unknown')}\n"
        context_text += f"Degree Program: {degree_info.get('degree_name', 'Unknown')}\n"
        context_text += f"Expected Graduation: {student.get('expected_graduation', 'Unknown')}\n"
        context_text += f"Preferred Course Load: {student.get('preferred_course_load', 'Unknown')} courses per term\n"
        context_text += f"Preferred Pace: {student.get('preferred_pace', 'Unknown')}\n"
        context_text += f"Work Hours/Week: {student.get('work_hours_per_week', 0)}\n"
        context_text += f"Preferred Instruction: {student.get('preferred_instruction_mode', 'Unknown')}\n"
        
        # Academic progress
        if completed_courses:
            context_text += f"\n=== ACADEMIC PROGRESS ===\n"
            context_text += f"Completed Courses: {len(completed_courses)}\n"
            
            # Calculate GPA
            gpa = self._calculate_gpa(completed_courses)
            context_text += f"Current GPA: {gpa}\n"
            
            # Recent courses (last 3)
            recent_courses = sorted(completed_courses, 
                                  key=lambda x: x.get('term', ''), reverse=True)[:3]
            context_text += "Recent Courses:\n"
            for course in recent_courses:
                context_text += f"  - {course.get('course_name', 'Unknown')} ({course.get('grade', 'N/A')})\n"
        
        # Degree progress
        if degree_info and degree_info.get('requirements'):
            context_text += f"\n=== DEGREE PROGRESS ===\n"
            total_required = degree_info.get('total_credits_required', 0)
            total_completed = degree_info.get('total_credits_completed', 0)
            completion_pct = degree_info.get('completion_percentage', 0)
            context_text += f"Credits: {total_completed}/{total_required} ({completion_pct:.1f}% complete)\n"
        
        # Available courses (sample)
        if available_courses:
            context_text += f"\n=== AVAILABLE COURSES (Sample) ===\n"
            for course in available_courses[:5]:  # Show first 5
                context_text += f"  - {course.get('course_name', 'Unknown')} "
                context_text += f"({course.get('level', 'N/A')}, {course.get('credits', 3)} credits)\n"
        
        # Similar students insights
        if similar_students:
            context_text += f"\n=== PEER INSIGHTS ===\n"
            high_performers = [s for s in similar_students if s.get('avg_gpa', 0) > 3.5]
            if high_performers:
                context_text += f"Found {len(high_performers)} high-performing similar students for comparison\n"
        
        return context_text

    def _format_additional_context(self, context: Dict) -> str:
        """Format additional context (course recommendations, path analysis, etc.)"""
        context_text = ""
        
        if context.get('optimal_sequence'):
            context_text += "\n=== RECOMMENDED COURSE SEQUENCE ===\n"
            courses = context['optimal_sequence'][:8]  # First 8 courses
            for i, course in enumerate(courses, 1):
                context_text += f"{i}. {course.get('course_name', 'Unknown')} "
                context_text += f"(Difficulty: {course.get('difficulty_prediction', 0):.1f}/5.0)\n"
        
        if context.get('term_plan'):
            context_text += f"\n=== GRADUATION TIMELINE ===\n"
            context_text += f"Estimated terms to graduation: {len(context['term_plan'])}\n"
            
            # Show next 2 terms
            for term in context['term_plan'][:2]:
                context_text += f"Term {term.get('term_number', 0)} ({term.get('term_type', 'Unknown')}):\n"
                for course in term.get('courses', []):
                    context_text += f"  - {course.get('course_name', 'Unknown')}\n"
        
        if context.get('risk_factors'):
            context_text += f"\n=== IDENTIFIED RISKS ===\n"
            for risk in context['risk_factors']:
                context_text += f"- {risk.get('type', 'Unknown')}: {risk.get('description', '')}\n"
        
        return context_text

    def _calculate_gpa(self, completed_courses: List[Dict]) -> str:
        """Calculate GPA from completed courses"""
        grade_points = {
            'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0, 'W': 0.0
        }
        
        if not completed_courses:
            return "No GPA data"
        
        total_points = 0
        total_credits = 0
        
        for course in completed_courses:
            grade = course.get('grade', 'F')
            credits = course.get('credits', 3)
            
            if grade in grade_points:
                total_points += grade_points[grade] * credits
                total_credits += credits
        
        if total_credits == 0:
            return "No GPA data"
        
        return f"{total_points / total_credits:.2f}"

    def get_study_recommendations(self, student_context: Dict, course_list: List[Dict]) -> str:
        """Get study strategy recommendations for specific courses"""
        if not self.model:
            return "Study recommendations are currently unavailable."
        
        try:
            student = student_context.get('student', {})
            learning_style = student.get('learning_style', 'Unknown')
            
            prompt = f"""
            As an academic advisor, provide specific study strategies for a {learning_style} learner
            taking these courses:
            
            Student Profile:
            - Learning Style: {learning_style}
            - Work Hours: {student.get('work_hours_per_week', 0)} per week
            - Preferred Pace: {student.get('preferred_pace', 'Standard')}
            
            Upcoming Courses:
            """
            
            for course in course_list[:5]:  # Limit to 5 courses
                prompt += f"- {course.get('course_name', 'Unknown')} "
                prompt += f"(Level {course.get('level', 0)}, "
                prompt += f"Difficulty: {course.get('difficulty_prediction', 3.0):.1f}/5.0)\n"
            
            prompt += """
            Provide:
            1. Learning style-specific study strategies
            2. Time management recommendations
            3. Course-specific tips based on difficulty
            4. Resources and tools that would help
            5. Warning signs to watch for
            
            Keep recommendations practical and actionable.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else "Unable to generate study recommendations."
            
        except Exception as e:
            logger.error(f"Error getting study recommendations: {e}")
            return f"Error generating study recommendations: {str(e)}"

    def analyze_course_fit(self, student_context: Dict, course: Dict) -> str:
        """Analyze how well a specific course fits a student"""
        if not self.model:
            return "Course analysis is currently unavailable."
        
        try:
            student = student_context.get('student', {})
            
            prompt = f"""
            Analyze how well this course fits this student's profile:
            
            Student Profile:
            - Learning Style: {student.get('learning_style', 'Unknown')}
            - Current GPA: {self._calculate_gpa(student_context.get('completed_courses', []))}
            - Work Load: {student.get('work_hours_per_week', 0)} hours/week
            - Preferred Instruction: {student.get('preferred_instruction_mode', 'Unknown')}
            
            Course Details:
            - Name: {course.get('course_name', 'Unknown')}
            - Level: {course.get('level', 0)}
            - Credits: {course.get('credits', 3)}
            - Average Difficulty: {course.get('avg_difficulty', 3.0)}/5.0
            - Instruction Modes: {course.get('instruction_modes', [])}
            - Tags: {course.get('tags', [])}
            
            Prerequisites Required: {len(course.get('prerequisites', []))}
            Courses This Unlocks: {len(course.get('unlocks', []))}
            
            Provide:
            1. Overall fit assessment (Excellent/Good/Fair/Poor)
            2. Specific reasons for the assessment
            3. Potential challenges and how to address them
            4. Success strategies for this student
            5. Whether to take it now or wait
            
            Be specific and actionable in your recommendations.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else "Unable to analyze course fit."
            
        except Exception as e:
            logger.error(f"Error analyzing course fit: {e}")
            return f"Error analyzing course fit: {str(e)}"

    def get_graduation_timeline_advice(self, path_data: Dict) -> str:
        """Get advice on graduation timeline and potential optimizations"""
        if not self.model:
            return "Timeline advice is currently unavailable."
        
        try:
            student = path_data.get('student_info', {})
            term_plan = path_data.get('term_plan', [])
            risks = path_data.get('risk_factors', [])
            
            prompt = f"""
            Review this student's graduation plan and provide optimization advice:
            
            Student: {student.get('name', 'Student')}
            Current Timeline: {len(term_plan)} terms to graduation
            Expected Graduation: {path_data.get('estimated_graduation', 'Unknown')}
            
            Risk Factors:
            """
            
            for risk in risks:
                prompt += f"- {risk.get('type', 'Unknown')}: {risk.get('description', '')}\n"
            
            prompt += f"""
            
            Term Plan Overview:
            """
            
            for i, term in enumerate(term_plan[:4], 1):  # First 4 terms
                prompt += f"Term {i} ({term.get('term_type', 'Unknown')}): "
                prompt += f"{len(term.get('courses', []))} courses, "
                prompt += f"{term.get('total_credits', 0)} credits, "
                prompt += f"Risk: {term.get('risk_level', 'Unknown')}\n"
            
            prompt += """
            
            Provide:
            1. Assessment of the current timeline (realistic/optimistic/conservative)
            2. Opportunities to graduate earlier
            3. Recommendations to reduce identified risks
            4. Alternative pacing strategies
            5. Key milestones to track progress
            
            Focus on practical, actionable advice that considers the student's constraints.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else "Unable to generate timeline advice."
            
        except Exception as e:
            logger.error(f"Error getting timeline advice: {e}")
            return f"Error generating timeline advice: {str(e)}"

    def get_similar_student_insights(self, student_context: Dict, similar_students: List[Dict]) -> str:
        """Generate insights based on similar students' experiences"""
        if not self.model or not similar_students:
            return "Similar student insights are currently unavailable."
        
        try:
            student = student_context.get('student', {})
            current_gpa = self._calculate_gpa(student_context.get('completed_courses', []))
            
            prompt = f"""
            Analyze successful similar students to provide insights for improvement:
            
            Target Student:
            - Learning Style: {student.get('learning_style', 'Unknown')}
            - Current GPA: {current_gpa}
            - Completed Courses: {len(student_context.get('completed_courses', []))}
            
            Similar High-Performing Students:
            """
            
            for similar in similar_students[:5]:  # Top 5 similar students
                prompt += f"- {similar.get('name', 'Student')} (GPA: {similar.get('avg_gpa', 0):.2f}, "
                prompt += f"Similarity: {similar.get('similarity', 0):.2f}, "
                prompt += f"Courses: {similar.get('courses_completed', 0)})\n"
            
            prompt += """
            
            Based on these similar successful students, provide:
            1. Key behavioral patterns that lead to success
            2. Study habits and strategies they likely used
            3. Course selection patterns to emulate
            4. Specific actionable changes the target student can make
            5. Warning signs to avoid based on what didn't work for others
            
            Focus on evidence-based recommendations that the student can implement immediately.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else "Unable to generate similar student insights."
            
        except Exception as e:
            logger.error(f"Error getting similar student insights: {e}")
            return f"Error generating insights: {str(e)}"
