#!/usr/bin/env python3
"""
Gemini AI Client for UMBC Degree Planner
Integrates Google Gemini for personalized academic advice and recommendations
"""

import os
import logging
from typing import Dict, Optional, List
import google.generativeai as genai
from google.api_core.exceptions import NotFound, GoogleAPIError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DEFAULT_MODEL = "models/gemini-2.5-flash"

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        """Initialize Gemini AI client"""
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.model_name = os.getenv('GEMINI_MODEL', DEFAULT_MODEL)
        
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found - Gemini features will be disabled")
            self.model = None
            return

        try:
            genai.configure(api_key=self.api_key)
            self.model = self._load_model(self.model_name)
            if self.model:
                logger.info("Gemini AI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {e}")
            self.model = None

    def _load_model(self, model_name: str):
        """Load a Gemini model, falling back to default when necessary."""
        try:
            model = genai.GenerativeModel(model_name)
            self.model_name = model_name
            return model
        except NotFound as exc:
            logger.error(f"Gemini model '{model_name}' not found: {exc}")
            if model_name != DEFAULT_MODEL:
                logger.info(f"Falling back to default Gemini model '{DEFAULT_MODEL}'")
                return self._load_model(DEFAULT_MODEL)
            return None
        except GoogleAPIError as exc:
            logger.error(f"Gemini API error while loading model '{model_name}': {exc}")
            return None
        except Exception as exc:
            logger.error(f"Unexpected error loading Gemini model '{model_name}': {exc}")
            return None

    def _ensure_model(self) -> bool:
        """Ensure a usable model is available, attempting fallback if needed."""
        if self.model:
            return True
        if not self.api_key:
            return False
        self.model = self._load_model(DEFAULT_MODEL)
        return self.model is not None

    def _generate_with_retry(self, prompt: str):
        """Generate content with automatic fallback to the default model."""
        last_error = None

        for attempt in range(2):
            if not self._ensure_model():
                break

            try:
                return self.model.generate_content(prompt)
            except NotFound as exc:
                last_error = exc
                logger.error(f"Gemini model '{self.model_name}' not found during generation: {exc}")
                if self.model_name == DEFAULT_MODEL:
                    break
                # Reset model so ensure_model reloads default on next iteration
                self.model = None
                self.model_name = DEFAULT_MODEL
                continue
            except GoogleAPIError as exc:
                last_error = exc
                logger.error(f"Gemini API error during generation: {exc}")
                raise
            except Exception as exc:
                last_error = exc
                logger.error(f"Unexpected error during Gemini generation: {exc}")
                raise

        if last_error:
            raise last_error

        raise RuntimeError("Gemini model unavailable")

    def test_connection(self) -> bool:
        """Test if Gemini AI is working"""
        if not self._ensure_model():
            return False
        
        try:
            response = self._generate_with_retry("Test connection. Respond with 'OK'.")
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
        if not self._ensure_model():
            return "AI assistant is currently unavailable. Please check your API configuration."
        
        try:
            # Construct comprehensive prompt
            prompt = self._build_advisor_prompt(message, student_context, additional_context)
            
            # Generate response
            response = self._generate_with_retry(prompt)
            
            if not response.text:
                return "I'm sorry, I couldn't generate a response. Please try rephrasing your question."
            
            # Clean up any markdown formatting that might slip through
            cleaned_response = self._clean_markdown_formatting(response.text.strip())
            return cleaned_response
            
        except NotFound as e:
            logger.error(f"Gemini model not found after retry: {e}")
            return "The configured Gemini model isn't available. Please verify your GEMINI_MODEL setting."
        except GoogleAPIError as e:
            logger.error(f"Gemini API error while generating advice: {e}")
            return "The AI service is temporarily unavailable due to an API error. Please try again later."
        except Exception as e:
            logger.error(f"Error getting Gemini response: {e}")
            return f"I encountered an error while processing your request: {str(e)}"

    def _build_advisor_prompt(self, message: str, student_context: Optional[Dict], 
                            additional_context: Optional[Dict]) -> str:
        """Build comprehensive prompt for academic advising"""
        
        # Base system prompt
        system_prompt = """You are an expert academic advisor at UMBC. Provide helpful, well-structured answers that are thorough but not overwhelming.

        RESPONSE GUIDELINES:
        - Keep responses focused and practical (4-8 sentences)
        - Use bullet points for multiple recommendations (use • not *)
        - Include brief explanations for your advice
        - No markdown formatting - plain text only
        - Be encouraging but realistic about challenges

        STRUCTURE YOUR RESPONSES:
        1. Brief assessment of the situation
        2. 2-4 specific, actionable recommendations with bullet points
        3. Short explanation of why these steps will help

        EXAMPLE FORMAT:
        Based on your [situation], here's what I recommend:

        • [Key recommendation with brief reason]
        • [Second important action]
        • [Third suggestion if relevant]

        [1-2 sentences explaining the benefit or next steps]

        Provide enough detail to be genuinely helpful while staying focused and actionable.
        """

        # Add student context if available
        context_section = ""
        if student_context and student_context.get('student'):
            context_section += self._format_student_context(student_context)
        
        if additional_context:
            context_section += self._format_additional_context(additional_context)

        # Combine all parts with balanced length guidance
        full_prompt = f"{system_prompt}\n\n{context_section}\n\nStudent Question: {message}\n\nProvide a helpful response (aim for 400-600 characters). Be thorough but focused:\n\nResponse:"
        
        return full_prompt

    def _clean_markdown_formatting(self, text: str) -> str:
        """Remove markdown formatting and ensure clean, formatted output"""
        import re
        
        # Remove markdown headers (# ## ###)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Remove bold/italic formatting but keep the emphasis visible
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # Remove backticks for code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        
        # Remove markdown links [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Standardize bullet points (- * + to •)
        text = re.sub(r'^[\-\*\+]\s+', '• ', text, flags=re.MULTILINE)
        
        # Add proper spacing around bullet points for readability
        text = re.sub(r'\n•', '\n\n•', text)
        
        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    def _format_student_context(self, context: Dict) -> str:
        """Format student context for the AI prompt - BALANCED VERSION"""
        student = context.get('student', {})
        completed_courses = context.get('completed_courses', [])
        enrolled_courses = context.get('enrolled_courses', [])
        degree_info = context.get('degree_info', {})
        
        context_text = "STUDENT PROFILE:\n"
        context_text += f"• {student.get('learning_style', 'Unknown')} learner\n"
        context_text += f"• {degree_info.get('degree_name', 'Unknown')} major\n"
        
        # Add current enrolled courses - this is key for current course questions!
        if enrolled_courses:
            context_text += f"• Currently enrolled in {len(enrolled_courses)} courses:\n"
            for course in enrolled_courses[:4]:  # Show up to 4 current courses
                course_name = course.get('course_name', course.get('name', 'Unknown'))
                course_id = course.get('course_id', course.get('id', 'Unknown'))
                context_text += f"  - {course_id}: {course_name}\n"
        
        if completed_courses:
            gpa = self._calculate_gpa(completed_courses)
            context_text += f"• {len(completed_courses)} courses completed, GPA: {gpa}\n"
            
            # Add recent performance context
            recent_courses = sorted(completed_courses, 
                                  key=lambda x: x.get('completion_term', x.get('term', '')), reverse=True)[:2]
            if recent_courses:
                context_text += f"• Recent courses: "
                recent_info = []
                for course in recent_courses:
                    course_name = course.get('course_name', course.get('name', 'Unknown'))[:15]  # Truncate long names
                    grade = course.get('grade', 'N/A')
                    recent_info.append(f"{course_name} ({grade})")
                context_text += ", ".join(recent_info)
        else:
            context_text += "• New student, no completed courses yet"
        
        # Add course load preference if available
        if student.get('preferred_course_load'):
            context_text += f"\n• Prefers {student.get('preferred_course_load')} courses per term"
        
        return context_text

    def _format_additional_context(self, context: Dict) -> str:
        """Format additional context - BALANCED VERSION"""
        context_text = ""
        
        if context.get('optimal_sequence'):
            courses = context['optimal_sequence'][:4]  # Show 4 recommended courses
            context_text += "\nRECOMMENDED COURSES:\n"
            for i, course in enumerate(courses, 1):
                course_name = course.get('course_name', 'Unknown')
                difficulty = course.get('difficulty_prediction', 0)
                context_text += f"• {course_name} (Difficulty: {difficulty:.1f}/5)\n"
        
        if context.get('risk_factors'):
            context_text += "\nPOTENTIAL CHALLENGES:\n"
            for risk in context['risk_factors'][:2]:  # Show top 2 risks
                context_text += f"• {risk.get('description', 'Unknown risk')}\n"
        
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
        if not self._ensure_model():
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
            
            IMPORTANT: Respond in plain text format only. Do not use markdown, asterisks, hashtags, or any special formatting characters.
            """
            
            response = self._generate_with_retry(prompt)
            cleaned_response = self._clean_markdown_formatting(response.text.strip()) if response.text else "Unable to generate study recommendations."
            return cleaned_response
            
        except NotFound as e:
            logger.error(f"Gemini model not found while generating study recommendations: {e}")
            return "The configured Gemini model isn't available. Please verify your GEMINI_MODEL setting."
        except GoogleAPIError as e:
            logger.error(f"Gemini API error while generating study recommendations: {e}")
            return "Study recommendations are temporarily unavailable due to an AI service error."
        except Exception as e:
            logger.error(f"Error getting study recommendations: {e}")
            return f"Error generating study recommendations: {str(e)}"

    def analyze_course_fit(self, student_context: Dict, course: Dict) -> str:
        """Analyze how well a specific course fits a student"""
        if not self._ensure_model():
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
            
            IMPORTANT: Respond in plain text format only. Do not use markdown, asterisks, hashtags, or any special formatting characters.
            """
            
            response = self._generate_with_retry(prompt)
            cleaned_response = self._clean_markdown_formatting(response.text.strip()) if response.text else "Unable to analyze course fit."
            return cleaned_response
            
        except NotFound as e:
            logger.error(f"Gemini model not found while analyzing course fit: {e}")
            return "The configured Gemini model isn't available. Please verify your GEMINI_MODEL setting."
        except GoogleAPIError as e:
            logger.error(f"Gemini API error while analyzing course fit: {e}")
            return "Course analysis is temporarily unavailable due to an AI service error."
        except Exception as e:
            logger.error(f"Error analyzing course fit: {e}")
            return f"Error analyzing course fit: {str(e)}"

    def get_graduation_timeline_advice(self, path_data: Dict) -> str:
        """Get advice on graduation timeline and potential optimizations"""
        if not self._ensure_model():
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
            
            IMPORTANT: Respond in plain text format only. Do not use markdown, asterisks, hashtags, or any special formatting characters.
            """
            
            response = self._generate_with_retry(prompt)
            cleaned_response = self._clean_markdown_formatting(response.text.strip()) if response.text else "Unable to generate timeline advice."
            return cleaned_response
            
        except NotFound as e:
            logger.error(f"Gemini model not found while generating timeline advice: {e}")
            return "The configured Gemini model isn't available. Please verify your GEMINI_MODEL setting."
        except GoogleAPIError as e:
            logger.error(f"Gemini API error while generating timeline advice: {e}")
            return "Timeline advice is temporarily unavailable due to an AI service error."
        except Exception as e:
            logger.error(f"Error getting timeline advice: {e}")
            return f"Error generating timeline advice: {str(e)}"

    def get_similar_student_insights(self, student_context: Dict, similar_students: List[Dict]) -> str:
        """Generate insights based on similar students' experiences"""
        if not similar_students:
            return "Similar student insights are currently unavailable."
        if not self._ensure_model():
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
            
            IMPORTANT: Respond in plain text format only. Do not use markdown, asterisks, hashtags, or any special formatting characters.
            """
            
            response = self._generate_with_retry(prompt)
            cleaned_response = self._clean_markdown_formatting(response.text.strip()) if response.text else "Unable to generate similar student insights."
            return cleaned_response
        except NotFound as e:
            logger.error(f"Gemini model not found while generating similar student insights: {e}")
            return "The configured Gemini model isn't available. Please verify your GEMINI_MODEL setting."
        except GoogleAPIError as e:
            logger.error(f"Gemini API error while generating similar student insights: {e}")
            return "Similar student insights are temporarily unavailable due to an AI service error."
        except Exception as e:
            logger.error(f"Error generating similar student insights: {e}")
            return f"Error generating similar student insights: {str(e)}"

    def get_course_recommendations(self, student_context: Dict, available_courses: List[Dict], 
                                 similar_students: List[Dict], degree_progress: Dict = None) -> List[Dict]:
        """
        Get AI-powered course recommendations with detailed analysis
        
        Args:
            student_context: Complete student context from Neo4j
            available_courses: List of courses the student can take
            similar_students: List of similar students with their performance data
            degree_progress: Optional degree progress information
            
        Returns:
            List of recommended courses with AI analysis and reasoning
        """
        if not self._ensure_model():
            return []
        
        try:
            student = student_context.get('student', {})
            completed_courses = student_context.get('completed_courses', [])
            enrolled_courses = student_context.get('enrolled_courses', [])
            degree_info = student_context.get('degree_info', {})
            
            # Build comprehensive prompt for course recommendations
            prompt = f"""
            You are an expert academic advisor at UMBC. Analyze this student's profile and recommend 4-5 courses from the available options.

            STUDENT PROFILE:
            • Name: {student.get('name', 'Student')}
            • Learning Style: {student.get('learning_style', 'Unknown')}
            • Major: {degree_info.get('degree_name', 'Unknown')}
            • Preferred Course Load: {student.get('preferred_course_load', 'Unknown')} courses/term
            • Work Hours/Week: {student.get('work_hours_per_week', 'Unknown')}
            • GPA: {self._calculate_gpa(completed_courses)}
            
            ACADEMIC HISTORY:
            • Completed: {len(completed_courses)} courses
            • Currently Enrolled: {len(enrolled_courses)} courses
            
            Recent Performance:
            """
            
            # Add recent course performance
            recent_courses = sorted(completed_courses, 
                                  key=lambda x: x.get('completion_term', x.get('term', '')), reverse=True)[:3]
            for course in recent_courses:
                prompt += f"• {course.get('course_name', 'Unknown')} ({course.get('grade', 'N/A')})\n"
            
            # Add current enrollment
            if enrolled_courses:
                prompt += f"\nCurrently Taking:\n"
                for course in enrolled_courses[:3]:
                    prompt += f"• {course.get('course_name', course.get('name', 'Unknown'))}\n"
            
            # Add similar student insights
            if similar_students:
                prompt += f"\nSIMILAR SUCCESSFUL STUDENTS:\n"
                for similar in similar_students[:3]:
                    prompt += f"• {similar.get('name', 'Student')} (GPA: {similar.get('avg_gpa', 0):.2f}, "
                    prompt += f"Learning: {similar.get('learning_style', 'Unknown')})\n"
            
            # Add available courses
            prompt += f"\nAVAILABLE COURSES ({len(available_courses)} total):\n"
            for i, course in enumerate(available_courses[:10], 1):  # Show up to 10 courses
                course_name = course.get('course_name', course.get('name', 'Unknown'))
                course_id = course.get('course_id', course.get('id', 'Unknown'))
                level = course.get('level', 'Unknown')
                credits = course.get('credits', 'Unknown')
                difficulty = course.get('avg_difficulty', course.get('avgDifficulty', 'Unknown'))
                
                prompt += f"{i}. {course_id}: {course_name}\n"
                prompt += f"   Level: {level}, Credits: {credits}, Avg Difficulty: {difficulty}\n"
                
                # Add prerequisites and unlocks if available
                prereqs = course.get('prerequisites', [])
                if prereqs:
                    prereq_names = [p.get('course_id', p.get('id', 'Unknown')) for p in prereqs[:2]]
                    prompt += f"   Prerequisites: {', '.join(prereq_names)}\n"
                
                unlocks = course.get('unlocks', [])
                if unlocks:
                    unlock_names = [u.get('course_id', u.get('id', 'Unknown')) for u in unlocks[:2]]
                    prompt += f"   Unlocks: {', '.join(unlock_names)}\n"
                
                prompt += "\n"
            
            prompt += f"""
            TASK: Recommend exactly 4-5 courses from the available list above. For each recommendation:

            Format each recommendation as:
            COURSE: [Course ID] - [Course Name]
            PRIORITY: [High/Medium/Low]
            REASON: [2-3 sentence explanation of why this course is recommended]
            DIFFICULTY: [Predicted difficulty 1-5 for this specific student]
            LEARNING_MATCH: [How well it matches their learning style 1-10]
            STRATEGIC_VALUE: [How this course fits their degree progression]

            Consider:
            • Student's learning style and preferences
            • Logical course sequence and prerequisites
            • Similar students' successful paths
            • Workload balance with current enrollment
            • Degree requirements and strategic progression
            • Student's demonstrated strengths and challenges

            Provide exactly 4-5 recommendations in the format above.
            """
            
            response = self._generate_with_retry(prompt)
            
            if not response.text:
                return []
            
            # Parse the AI response to extract structured recommendations
            recommendations = self._parse_course_recommendations(response.text, available_courses)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating AI course recommendations: {e}")
            return []
    
    def _parse_course_recommendations(self, ai_response: str, available_courses: List[Dict]) -> List[Dict]:
        """Parse AI recommendation text into structured course data"""
        recommendations = []
        lines = ai_response.split('\n')
        current_rec = {}
        
        # Create lookup for available courses
        course_lookup = {}
        for course in available_courses:
            course_id = course.get('course_id', course.get('id', ''))
            if course_id:
                course_lookup[course_id.upper()] = course
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('COURSE:'):
                # Save previous recommendation if complete
                if current_rec and current_rec.get('course_id'):
                    recommendations.append(current_rec)
                
                # Start new recommendation
                current_rec = {}
                course_part = line.replace('COURSE:', '').strip()
                
                # Extract course ID (first part before dash or colon)
                if ' - ' in course_part:
                    course_id = course_part.split(' - ')[0].strip()
                elif ':' in course_part:
                    course_id = course_part.split(':')[0].strip()
                else:
                    course_id = course_part.split()[0] if course_part.split() else ''
                
                # Find matching course data
                matching_course = course_lookup.get(course_id.upper())
                if matching_course:
                    current_rec.update(matching_course)
                    current_rec['course_id'] = course_id.upper()
                    current_rec['ai_recommended'] = True
                else:
                    # Fallback if course not found
                    current_rec['course_id'] = course_id
                    current_rec['course_name'] = course_part
                    current_rec['ai_recommended'] = True
                    
            elif line.startswith('PRIORITY:') and current_rec:
                priority_text = line.replace('PRIORITY:', '').strip().lower()
                if 'high' in priority_text:
                    current_rec['recommendation_score'] = 9.0
                    current_rec['priority'] = 'High'
                elif 'medium' in priority_text:
                    current_rec['recommendation_score'] = 7.0
                    current_rec['priority'] = 'Medium'
                else:
                    current_rec['recommendation_score'] = 5.0
                    current_rec['priority'] = 'Low'
                    
            elif line.startswith('REASON:') and current_rec:
                current_rec['ai_reasoning'] = line.replace('REASON:', '').strip()
                
            elif line.startswith('DIFFICULTY:') and current_rec:
                try:
                    difficulty_text = line.replace('DIFFICULTY:', '').strip()
                    difficulty_num = float(''.join(filter(str.isdigit, difficulty_text.split()[0])))
                    current_rec['difficulty_prediction'] = min(max(difficulty_num, 1.0), 5.0)
                except (ValueError, IndexError):
                    current_rec['difficulty_prediction'] = 3.0
                    
            elif line.startswith('LEARNING_MATCH:') and current_rec:
                try:
                    match_text = line.replace('LEARNING_MATCH:', '').strip()
                    match_num = float(''.join(filter(str.isdigit, match_text.split()[0])))
                    current_rec['learning_style_match'] = min(max(match_num / 10.0, 0.0), 1.0)
                except (ValueError, IndexError):
                    current_rec['learning_style_match'] = 0.7
                    
            elif line.startswith('STRATEGIC_VALUE:') and current_rec:
                current_rec['strategic_reasoning'] = line.replace('STRATEGIC_VALUE:', '').strip()
        
        # Add the last recommendation
        if current_rec and current_rec.get('course_id'):
            recommendations.append(current_rec)
        
        # Ensure we have all required fields and sort by priority
        for rec in recommendations:
            rec.setdefault('credits', 3)
            rec.setdefault('level', 300)
            rec.setdefault('department', 'Unknown')
            rec.setdefault('recommendation_score', 7.0)
            rec.setdefault('difficulty_prediction', 3.0)
            rec.setdefault('learning_style_match', 0.7)
            rec.setdefault('ai_reasoning', 'AI recommended based on your profile')
            rec.setdefault('priority', 'Medium')
        
        # Sort by recommendation score (descending)
        recommendations.sort(key=lambda x: x.get('recommendation_score', 0), reverse=True)
        
        return recommendations[:5]  # Return top 5
