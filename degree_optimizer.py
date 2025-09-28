#!/usr/bin/env python3
"""
Degree Path Optimizer for UMBC Degree Planner
Finds optimal graduation paths considering learning styles and course history
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import heapq

logger = logging.getLogger(__name__)

class DegreeOptimizer:
    def __init__(self, neo4j_client, gemini_client):
        self.neo4j = neo4j_client
        self.gemini = gemini_client
        
    def find_optimal_path(self, student_id: str) -> Dict:
        """
        Find the fastest path to graduation for a student
        considering their learning style, course history, and preferences
        """
        try:
            # Get comprehensive student context
            context = self.neo4j.get_student_context(student_id)
            if not context or not context.get('student'):
                raise ValueError(f"Student {student_id} not found")
            
            student = context['student']
            degree_progress = self.neo4j.get_degree_requirements_progress(student_id)
            
            # Calculate optimal course sequence
            optimal_sequence = self._calculate_optimal_sequence(context, degree_progress)
            
            # Generate term-by-term plan
            completed_history = {c['course_id'] for c in context['completed_courses']}
            term_plan = self._generate_term_plan(student, optimal_sequence, completed_history)
            
            # Get AI recommendations
            ai_insights = self._get_ai_recommendations(context, optimal_sequence)
            
            return {
                "student_info": student,
                "degree_progress": degree_progress,
                "optimal_sequence": optimal_sequence,
                "term_plan": term_plan,
                "ai_insights": ai_insights,
                "estimated_graduation": self._estimate_graduation_date(student, term_plan),
                "total_terms_remaining": len(term_plan),
                "risk_factors": self._identify_risk_factors(context, optimal_sequence)
            }
            
        except Exception as e:
            logger.error(f"Error optimizing path for {student_id}: {e}")
            raise

    def _calculate_optimal_sequence(self, context: Dict, degree_progress: Dict) -> List[Dict]:
        """Calculate optimal course sequence using graph algorithms and heuristics"""
        student = context['student']
        completed_courses = set(c['course_id'] for c in context['completed_courses'])
        enrolled_courses = set(c['course_id'] for c in context['enrolled_courses'])
        available_courses = context['available_courses']
        
        # Build prerequisite graph
        prereq_graph = defaultdict(set)
        reverse_prereq_graph = defaultdict(set)
        course_info = {}
        
        for course in available_courses:
            course_id = course['course_id']
            course_info[course_id] = course
            
            # Get prerequisites for this course
            prereqs = self.neo4j.get_course_prerequisites(course_id)
            for prereq in prereqs:
                prereq_id = prereq['course_id']
                prereq_graph[prereq_id].add(course_id)
                reverse_prereq_graph[course_id].add(prereq_id)
        
        # Calculate course priorities using multiple factors
        course_scores = {}
        for course in available_courses:
            course_id = course['course_id']
            score = self._calculate_course_score(course, context, prereq_graph)
            course_scores[course_id] = score
        
        # Sort courses by priority (higher score = higher priority)
        prioritized_courses = sorted(
            available_courses,
            key=lambda c: course_scores[c['course_id']],
            reverse=True
        )
        
        # Add additional metadata for each course
        for course in prioritized_courses:
            course_id = course['course_id']
            course['priority_score'] = course_scores[course_id]
            course['prerequisites'] = self.neo4j.get_course_prerequisites(course_id)
            course['unlocks'] = self.neo4j.get_courses_unlocked_by(course_id)
            course['learning_style_match'] = self._calculate_learning_style_match(course, student)
            course['difficulty_prediction'] = self._predict_difficulty(course, context)
            
        return prioritized_courses

    def _calculate_course_score(self, course: Dict, context: Dict, prereq_graph: Dict) -> float:
        """Calculate priority score for a course based on multiple factors"""
        student = context['student']
        course_id = course['course_id']
        
        score = 0.0
        
        # 1. Prerequisite impact (courses that unlock more courses get higher priority)
        unlocked_courses = len(prereq_graph.get(course_id, []))
        score += unlocked_courses * 10
        
        # 2. Learning style alignment
        learning_style_bonus = self._calculate_learning_style_match(course, student) * 15
        score += learning_style_bonus
        
        # 3. Course level (lower level = higher priority for foundational courses)
        level = course.get('level', 400)
        level_score = (500 - level) / 100 * 5
        score += level_score
        
        # 4. Success rate with similar students
        similar_students = context.get('similar_students', [])
        if similar_students:
            # This would require additional queries to get success rates
            # For now, use a basic heuristic based on average difficulty
            avg_difficulty = course.get('avg_difficulty', 3.0)
            difficulty_penalty = (avg_difficulty - 1) * -3
            score += difficulty_penalty
        
        # 5. Credits (more credits = higher priority for efficiency)
        credits = course.get('credits', 3)
        credit_bonus = credits * 2
        score += credit_bonus
        
        # 6. Instruction mode preference
        instruction_modes = course.get('instruction_modes', [])
        preferred_mode = student.get('preferred_instruction_mode', 'In-person')
        if preferred_mode in instruction_modes:
            score += 5
        
        return score

    def _calculate_learning_style_match(self, course: Dict, student: Dict) -> float:
        """Calculate how well a course matches student's learning style"""
        student_style = student.get('learning_style', '')
        course_tags = course.get('tags', [])
        
        # Learning style to course tag mapping
        style_mappings = {
            'Visual': ['visual', 'graphics', 'charts', 'diagrams', 'visualization'],
            'Auditory': ['discussion', 'lecture', 'presentation', 'verbal'],
            'Kinesthetic': ['hands-on', 'lab', 'practical', 'project', 'interactive'],
            'Reading-Writing': ['writing', 'reading', 'research', 'analysis', 'documentation']
        }
        
        preferred_tags = style_mappings.get(student_style, [])
        
        # Calculate match score
        if not course_tags or not preferred_tags:
            return 0.5  # neutral
        
        matches = sum(1 for tag in course_tags if any(pref in tag.lower() for pref in preferred_tags))
        return min(matches / len(course_tags), 1.0)

    def _predict_difficulty(self, course: Dict, context: Dict) -> float:
        """Predict difficulty of a course for this specific student"""
        base_difficulty = course.get('avg_difficulty', 3.0)
        student = context['student']
        similar_students = context.get('similar_students', [])
        
        # If we have data from similar students, use it
        # This would require additional queries to get specific course experiences
        # For now, adjust based on learning style match
        
        learning_style_match = self._calculate_learning_style_match(course, student)
        
        # Better match = lower perceived difficulty
        difficulty_adjustment = (0.5 - learning_style_match) * 2
        predicted_difficulty = base_difficulty + difficulty_adjustment
        
        return max(1.0, min(5.0, predicted_difficulty))

    def _generate_term_plan(self, student: Dict, optimal_sequence: List[Dict], completed_history: Optional[Set[str]] = None) -> List[Dict]:
        """Generate term-by-term course plan"""
        preferred_load = student.get('preferred_course_load', 4)
        preferred_pace = student.get('preferred_pace', 'Standard')
        work_hours = student.get('work_hours_per_week', 0)
        completed_history = set(completed_history or [])
        
        # Adjust course load based on preferences and constraints
        if preferred_pace == 'Part-time' or work_hours > 20:
            max_courses_per_term = max(2, preferred_load - 1)
        elif preferred_pace == 'Accelerated':
            max_courses_per_term = min(6, preferred_load + 1)
        else:
            max_courses_per_term = preferred_load
        
        # Group courses by term, respecting prerequisites and load limits
        terms = []
        remaining_courses = optimal_sequence.copy()
        completed_in_plan = set()
        
        term_counter = 1
        current_term_type = self._get_next_term_type()
        
        while remaining_courses:
            current_term = {
                "term_number": term_counter,
                "term_type": current_term_type,
                "courses": [],
                "total_credits": 0,
                "estimated_difficulty": 0.0,
                "risk_level": "Low"
            }
            
            # Find courses that can be taken this term
            available_this_term = []
            for course in remaining_courses:
                prereqs = course.get('prerequisites', [])
                prereqs_met = all(
                    prereq.get('course_id') in completed_in_plan or
                    prereq.get('course_id') in completed_history
                    for prereq in prereqs
                )
                if prereqs_met:
                    available_this_term.append(course)
            
            # Select courses for this term
            courses_added = 0
            total_credits = 0
            total_difficulty = 0
            
            for course in available_this_term:
                if courses_added >= max_courses_per_term:
                    break
                
                credits = course.get('credits', 3)
                difficulty = course.get('difficulty_prediction', 3.0)
                
                # Check if adding this course would be too much
                if total_credits + credits > max_courses_per_term * 4:  # Max ~4 credits per course slot
                    continue
                
                # Avoid too many high-difficulty courses in one term
                if courses_added > 0 and difficulty > 4.0 and total_difficulty / courses_added > 3.5:
                    continue
                
                current_term["courses"].append(course)
                current_term["total_credits"] += credits
                total_credits += credits
                total_difficulty += difficulty
                courses_added += 1
                
                completed_in_plan.add(course['course_id'])
                completed_history.add(course['course_id'])
                remaining_courses.remove(course)
            
            # Calculate term risk level
            if courses_added > 0:
                current_term["estimated_difficulty"] = total_difficulty / courses_added
                current_term["risk_level"] = self._calculate_term_risk(current_term)
                terms.append(current_term)
            
            term_counter += 1
            current_term_type = self._get_next_term_type(current_term_type)
            
            # Safety check to avoid infinite loop
            if term_counter > 20:
                logger.warning("Term planning exceeded 20 terms, breaking")
                break
        
        return terms

    def _get_next_term_type(self, current_term_type: str = None) -> str:
        """Get next term type in sequence"""
        if current_term_type is None:
            # Start with next upcoming term
            current_month = datetime.now().month
            if current_month <= 5:
                return "Fall"
            elif current_month <= 7:
                return "Spring" 
            else:
                return "Spring"
        
        # Cycle through terms (skipping summer for most students)
        if current_term_type == "Fall":
            return "Spring"
        elif current_term_type == "Spring":
            return "Fall"
        else:
            return "Fall"

    def _calculate_term_risk(self, term: Dict) -> str:
        """Calculate risk level for a term"""
        avg_difficulty = term.get('estimated_difficulty', 0)
        course_count = len(term.get('courses', []))
        total_credits = term.get('total_credits', 0)
        
        risk_score = 0
        
        # Difficulty risk
        if avg_difficulty > 4.0:
            risk_score += 3
        elif avg_difficulty > 3.5:
            risk_score += 2
        elif avg_difficulty > 3.0:
            risk_score += 1
        
        # Course load risk
        if course_count > 5:
            risk_score += 2
        elif course_count > 4:
            risk_score += 1
        
        # Credit risk
        if total_credits > 18:
            risk_score += 2
        elif total_credits > 15:
            risk_score += 1
        
        if risk_score >= 5:
            return "High"
        elif risk_score >= 3:
            return "Medium"
        else:
            return "Low"

    def _estimate_graduation_date(self, student: Dict, term_plan: List[Dict]) -> str:
        """Estimate graduation date based on term plan"""
        if not term_plan:
            return student.get('expected_graduation', 'Unknown')
        
        # Calculate based on number of terms
        terms_needed = len(term_plan)
        current_date = datetime.now()
        
        # Estimate 4 months per term (including breaks)
        estimated_date = current_date + timedelta(days=terms_needed * 120)
        
        return estimated_date.strftime('%Y-%m-%d')

    def _identify_risk_factors(self, context: Dict, optimal_sequence: List[Dict]) -> List[Dict]:
        """Identify potential risk factors in the graduation plan"""
        risks = []
        student = context['student']
        
        # Check for high-difficulty course clusters
        high_difficulty_courses = [
            c for c in optimal_sequence 
            if c.get('difficulty_prediction', 0) > 4.0
        ]
        if len(high_difficulty_courses) > 3:
            risks.append({
                "type": "High Difficulty Load",
                "severity": "Medium",
                "description": f"Plan includes {len(high_difficulty_courses)} high-difficulty courses",
                "recommendation": "Consider spreading difficult courses across more terms"
            })
        
        # Check work-study balance
        work_hours = student.get('work_hours_per_week', 0)
        if work_hours > 20:
            risks.append({
                "type": "Work-Study Balance",
                "severity": "High",
                "description": f"Working {work_hours} hours per week while studying",
                "recommendation": "Consider reducing course load or work hours during difficult terms"
            })
        
        # Check learning style mismatches
        mismatched_courses = [
            c for c in optimal_sequence[:6]  # Check first 6 courses
            if c.get('learning_style_match', 1.0) < 0.3
        ]
        if mismatched_courses:
            risks.append({
                "type": "Learning Style Mismatch",
                "severity": "Low",
                "description": f"{len(mismatched_courses)} courses may not align with your learning style",
                "recommendation": "Seek additional support or alternative sections for these courses"
            })
        
        # Check prerequisite chains
        complex_chains = self._find_complex_prerequisite_chains(optimal_sequence)
        if complex_chains:
            risks.append({
                "type": "Complex Prerequisites",
                "severity": "Medium", 
                "description": "Some courses have long prerequisite chains",
                "recommendation": "Plan carefully to avoid delays if any prerequisite course is failed"
            })
        
        return risks

    def _find_complex_prerequisite_chains(self, courses: List[Dict]) -> List[str]:
        """Find courses with complex prerequisite chains"""
        complex_chains = []
        for course in courses:
            prereqs = course.get('prerequisites', [])
            if len(prereqs) > 2:
                complex_chains.append(course['course_id'])
        return complex_chains

    def _get_ai_recommendations(self, context: Dict, optimal_sequence: List[Dict]) -> Dict:
        """Get AI-powered recommendations from Gemini"""
        try:
            if not self.gemini:
                return {"message": "AI recommendations unavailable"}
            
            # Prepare context for AI
            student_summary = self._prepare_student_summary_for_ai(context)
            course_summary = self._prepare_course_summary_for_ai(optimal_sequence[:10])  # First 10 courses
            
            prompt = f"""
            As an academic advisor AI, provide personalized recommendations for this student's degree plan:
            
            Student Profile:
            {student_summary}
            
            Proposed Course Sequence (First 10 courses):
            {course_summary}
            
            Please provide:
            1. Overall assessment of the plan
            2. Specific recommendations for course selection or timing
            3. Study strategies based on learning style
            4. Potential challenges and how to address them
            5. Resources or support services that might be helpful
            
            Keep recommendations practical and actionable.
            """
            
            response = self.gemini.get_academic_advice(prompt, context)
            return {"ai_recommendations": response}
            
        except Exception as e:
            logger.error(f"Error getting AI recommendations: {e}")
            return {"message": "AI recommendations temporarily unavailable"}

    def _prepare_student_summary_for_ai(self, context: Dict) -> str:
        """Prepare student context summary for AI"""
        student = context['student']
        completed = context['completed_courses']
        
        summary = f"""
        Name: {student.get('name', 'Unknown')}
        Learning Style: {student.get('learning_style', 'Unknown')}
        Degree: {student.get('degree_name', 'Unknown')}
        Preferred Course Load: {student.get('preferred_course_load', 'Unknown')} courses per term
        Preferred Pace: {student.get('preferred_pace', 'Unknown')}
        Work Hours: {student.get('work_hours_per_week', 0)} hours per week
        Completed Courses: {len(completed)} courses
        Average Grade: {self._calculate_average_grade(completed)}
        """
        return summary

    def _prepare_course_summary_for_ai(self, courses: List[Dict]) -> str:
        """Prepare course sequence summary for AI"""
        summary = ""
        for i, course in enumerate(courses, 1):
            summary += f"{i}. {course.get('course_name', 'Unknown')} ({course.get('course_id', '')}) - "
            summary += f"{course.get('credits', 0)} credits, "
            summary += f"Level {course.get('level', 0)}, "
            summary += f"Predicted Difficulty: {course.get('difficulty_prediction', 0):.1f}/5.0\n"
        return summary

    def _calculate_average_grade(self, completed_courses: List[Dict]) -> str:
        """Calculate GPA from completed courses"""
        if not completed_courses:
            return "No grades available"
        
        grade_points = {
            'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
        }
        
        total_points = 0
        total_credits = 0
        
        for course in completed_courses:
            grade = course.get('grade', 'F')
            credits = course.get('credits', 3)
            points = grade_points.get(grade, 0.0)
            total_points += points * credits
            total_credits += credits
        
        if total_credits == 0:
            return "No credits available"
        
        gpa = total_points / total_credits
        return f"{gpa:.2f}"

    def get_course_recommendations(self, student_id: str, limit: int = 5) -> List[Dict]:
        """Get AI-powered course recommendations for next term"""
        try:
            context = self.neo4j.get_student_context(student_id)
            if not context:
                return []
            
            available_courses = context['available_courses']
            student = context['student']
            
            # Score and rank available courses
            recommendations = []
            for course in available_courses[:limit * 2]:  # Get more to filter from
                score = self._calculate_course_score(course, context, {})
                
                # Add course with enriched data
                enriched_course = course.copy()
                enriched_course['recommendation_score'] = score
                enriched_course['learning_style_match'] = self._calculate_learning_style_match(course, student)
                enriched_course['difficulty_prediction'] = self._predict_difficulty(course, context)
                enriched_course['prerequisites'] = self.neo4j.get_course_prerequisites(course['course_id'])
                enriched_course['unlocks'] = self.neo4j.get_courses_unlocked_by(course['course_id'])
                
                recommendations.append(enriched_course)
            
            # Sort by recommendation score and return top results
            recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting course recommendations for {student_id}: {e}")
            return []
