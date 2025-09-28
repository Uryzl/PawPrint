#!/usr/bin/env python3
"""
Neo4j Client for UMBC Degree Planner
Handles all database connections and queries
"""

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import AuthError, ServiceUnavailable
except ImportError:  # pragma: no cover
    GraphDatabase = None  # type: ignore
    class AuthError(Exception):
        pass
    class ServiceUnavailable(Exception):
        pass
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        self.driver = None
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        if GraphDatabase is None:
            raise ImportError("The 'neo4j' Python driver is not installed. Install it with 'pip install neo4j'.")

        if not all([uri, user, password]):
            raise ValueError("Neo4j credentials are missing. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD.")

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j")
        except AuthError as exc:
            logger.error(f"Neo4j auth failed: {exc}")
            raise
        except ServiceUnavailable as exc:
            logger.error(f"Neo4j unavailable: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Neo4j init error: {exc}")
            raise

    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()

    def test_connection(self) -> bool:
        """Test if Neo4j connection is working"""
        if not self.driver:
            return False
            
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                return bool(result.single())
        except Exception as e:
            logger.error(f"Neo4j connection test failed: {e}")
            return False

    def _check_connection(self):
        """Check if driver is available, raise exception if not"""
        if not self.driver:
            raise Exception("Neo4j connection not available. Check your credentials and ensure Neo4j is running.")

    def _convert_neo4j_types(self, data):
        """Convert Neo4j types to JSON-serializable types"""
        if isinstance(data, dict):
            return {key: self._convert_neo4j_types(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_neo4j_types(item) for item in data]
        elif hasattr(data, 'year') and hasattr(data, 'month') and hasattr(data, 'day'):
            # Neo4j Date object
            return f"{data.year}-{data.month:02d}-{data.day:02d}"
        elif hasattr(data, 'isoformat'):
            # Python datetime/date objects
            return data.isoformat()
        else:
            return data

    def get_all_students(self, limit: int = 100) -> List[Dict]:
        """Get list of all students for selection"""
        self._check_connection()
        
        query = """
        MATCH (s:Student)
        OPTIONAL MATCH (s)-[:PURSUING]->(d:Degree)
        RETURN s.id as id, s.name as name, s.learningStyle as learning_style,
               d.name as degree_name, s.expectedGraduation as expected_graduation
        ORDER BY s.name
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, limit=limit)
                students = [dict(record) for record in result]
                return [self._convert_neo4j_types(student) for student in students]
        except Exception as e:
            logger.error(f"Error fetching students: {e}")
            raise

    def search_students(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search students by name or ID"""
        self._check_connection()

        query = """
        MATCH (s:Student)
        OPTIONAL MATCH (s)-[:PURSUING]->(d:Degree)
        WHERE toLower(s.name) CONTAINS toLower($search_term) 
           OR toLower(s.id) CONTAINS toLower($search_term)
        RETURN s.id as id, s.name as name, s.learningStyle as learning_style,
               d.name as degree_name, s.expectedGraduation as expected_graduation
        ORDER BY s.name
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, search_term=search_term, limit=limit)
                students = [dict(record) for record in result]
                return [self._convert_neo4j_types(student) for student in students]
        except Exception as e:
            logger.error(f"Error searching students: {e}")
            raise


    def get_student_details(self, student_id: str) -> Optional[Dict]:
        """Get detailed information about a specific student"""
        self._check_connection()
            
        query = """
        MATCH (s:Student {id: $student_id})
        OPTIONAL MATCH (s)-[:PURSUING]->(d:Degree)
        RETURN s.id as id, s.name as name, s.learningStyle as learning_style,
               s.preferredCourseLoad as preferred_course_load,
               s.preferredPace as preferred_pace,
               s.workHoursPerWeek as work_hours_per_week,
               s.financialAidStatus as financial_aid_status,
               s.preferredInstructionMode as preferred_instruction_mode,
               s.enrollmentDate as enrollment_date,
               s.expectedGraduation as expected_graduation,
               d.id as degree_id, d.name as degree_name,
               d.totalCredits as total_credits
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, student_id=student_id)
                record = result.single()
                if record:
                    return self._convert_neo4j_types(dict(record))
                return None
        except Exception as e:
            logger.error(f"Error fetching student details: {e}")
            raise

    def get_student_completed_courses(self, student_id: str) -> List[Dict]:
        """Get courses completed by a student"""
        self._check_connection()
            
        query = """
        MATCH (s:Student {id: $student_id})-[comp:COMPLETED]->(c:Course)
        RETURN c.id as course_id, c.name as course_name, c.credits as credits,
               c.department as department, c.level as level,
               comp.grade as grade, comp.term as term,
               comp.studyHours as study_hours, comp.difficulty as difficulty
        ORDER BY comp.term, c.level, c.name
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, student_id=student_id)
                courses = [dict(record) for record in result]
                return [self._convert_neo4j_types(course) for course in courses]
        except Exception as e:
            logger.error(f"Error fetching completed courses: {e}")
            raise

    def get_student_enrolled_courses(self, student_id: str) -> List[Dict]:
        """Get courses currently enrolled by a student"""
        self._check_connection()
            
        query = """
        MATCH (s:Student {id: $student_id})-[enr:ENROLLED_IN]->(c:Course)
        RETURN c.id as course_id, c.name as course_name, c.credits as credits,
               c.department as department, c.level as level,
               enr.term as term, enr.expectedGrade as expected_grade
        ORDER BY enr.term, c.level, c.name
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, student_id=student_id)
                courses = [dict(record) for record in result]
                return [self._convert_neo4j_types(course) for course in courses]
        except Exception as e:
            logger.error(f"Error fetching enrolled courses: {e}")
            raise

    def get_student_degree(self, student_id: str) -> Optional[Dict]:
        """Get degree program information for a student"""
        self._check_connection()
            
        query = """
        MATCH (s:Student {id: $student_id})-[:PURSUING]->(d:Degree)
        MATCH (rg:RequirementGroup)-[:PART_OF]->(d)
        OPTIONAL MATCH (c:Course)-[:FULFILLS]->(rg)
        WITH d, rg, COUNT(c) as courses_in_group
        RETURN d.id as degree_id, d.name as degree_name, d.department as department,
               d.type as degree_type, d.totalCredits as total_credits,
               COLLECT({
                   id: rg.id,
                   name: rg.name,
                   required_courses: rg.requiredCourses,
                   credits_required: rg.creditsRequired,
                   course_count: courses_in_group
               }) as requirement_groups
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, student_id=student_id)
                record = result.single()
                if record:
                    return self._convert_neo4j_types(dict(record))
                return None
        except Exception as e:
            logger.error(f"Error fetching degree info: {e}")
            raise

    def get_available_courses(self, student_id: str, term: str = None) -> List[Dict]:
        """Get courses available to a student (prerequisites met, not already taken)"""
        self._check_connection()

        query = """
        MATCH (s:Student {id: $student_id})-[:PURSUING]->(d:Degree)
        MATCH (c:Course)-[:FULFILLS]->(:RequirementGroup)-[:PART_OF]->(d)
        
        // Ensure prerequisites are met
        WHERE NOT EXISTS {
            MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
            WHERE NOT (s)-[:COMPLETED]->(prereq)
        }
        
        // Student hasn't already completed the course
        AND NOT (s)-[:COMPLETED]->(c)
        AND NOT (s)-[:ENROLLED_IN]->(c)
        
        // If term is specified, check if course is offered
        """ + ("""
        AND EXISTS((c)-[:OFFERED_IN]->(:Term {id: $term}))
        """ if term else "") + """
        
        RETURN c.id as course_id, c.name as course_name, c.credits as credits,
               c.department as department, c.level as level,
               c.avgDifficulty as avg_difficulty, c.instructionModes as instruction_modes,
               c.tags as tags
        ORDER BY c.level, c.name
        """
        
        with self.driver.session() as session:
            params = {"student_id": student_id}
            if term:
                params["term"] = term
            result = session.run(query, **params)
            courses = [dict(record) for record in result]
            return [self._convert_neo4j_types(course) for course in courses]

    def get_course_prerequisites(self, course_id: str) -> List[Dict]:
        """Get prerequisites for a specific course"""
        self._check_connection()

        query = """
        MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c:Course {id: $course_id})
        RETURN prereq.id as course_id, prereq.name as course_name,
               prereq.credits as credits, prereq.level as level
        ORDER BY prereq.level, prereq.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, course_id=course_id)
            return [dict(record) for record in result]

    def get_courses_unlocked_by(self, course_id: str) -> List[Dict]:
        """Get courses that would be unlocked by taking a specific course"""
        self._check_connection()

        query = """
        MATCH (c:Course {id: $course_id})-[:PREREQUISITE_FOR]->(unlocked:Course)
        RETURN unlocked.id as course_id, unlocked.name as course_name,
               unlocked.credits as credits, unlocked.level as level
        ORDER BY unlocked.level, unlocked.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, course_id=course_id)
            return [dict(record) for record in result]

    def get_similar_students(self, student_id: str, min_similarity: float = 0.7) -> List[Dict]:
        """Find students similar to the given student"""
        self._check_connection()

        query = """
        MATCH (s:Student {id: $student_id})
        MATCH (s)-[sim:SIMILAR_LEARNING_STYLE|SIMILAR_PERFORMANCE]->(similar:Student)
        WHERE sim.similarity >= $min_similarity
        
        // Get their performance info
        OPTIONAL MATCH (similar)-[comp:COMPLETED]->(c:Course)
        WITH s, similar, sim, 
             AVG(CASE comp.grade
                 WHEN 'A' THEN 4.0 WHEN 'A-' THEN 3.7 WHEN 'B+' THEN 3.3
                 WHEN 'B' THEN 3.0 WHEN 'B-' THEN 2.7 WHEN 'C+' THEN 2.3
                 WHEN 'C' THEN 2.0 WHEN 'C-' THEN 1.7 WHEN 'D+' THEN 1.3
                 WHEN 'D' THEN 1.0 ELSE 0.0 
             END) AS avg_gpa,
             COUNT(comp) as courses_completed
             
        RETURN similar.id as id, similar.name as name, similar.learningStyle as learning_style,
               sim.similarity as similarity, type(sim) as similarity_type,
               avg_gpa, courses_completed
        ORDER BY sim.similarity DESC
        LIMIT 10
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id, min_similarity=min_similarity)
            return [dict(record) for record in result]

    def get_student_context(self, student_id: str) -> Dict:
        """Get comprehensive context about a student for AI recommendations"""
        student = self.get_student_details(student_id)
        if not student:
            return {}
            
        completed = self.get_student_completed_courses(student_id)
        enrolled = self.get_student_enrolled_courses(student_id)
        degree = self.get_student_degree(student_id)
        available = self.get_available_courses(student_id)
        similar = self.get_similar_students(student_id)
        
        return {
            "student": student,
            "completed_courses": completed,
            "enrolled_courses": enrolled,
            "degree_info": degree,
            "available_courses": available,
            "similar_students": similar
        }

    def get_optimal_course_sequence(self, student_id: str) -> List[Dict]:
        """Find optimal course sequence considering prerequisites and learning style"""
        self._check_connection()

        query = """
        // Get student's degree and available courses
        MATCH (s:Student {id: $student_id})-[:PURSUING]->(d:Degree)
        MATCH (c:Course)-[:FULFILLS]->(:RequirementGroup)-[:PART_OF]->(d)
        
        // Ensure prerequisites are met or can be met
        WHERE NOT EXISTS {
            MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
            WHERE NOT (s)-[:COMPLETED]->(prereq)
        }
        AND NOT (s)-[:COMPLETED]->(c)
        AND NOT (s)-[:ENROLLED_IN]->(c)
        
        // Get similar students' experiences with these courses
        OPTIONAL MATCH (s)-[sim:SIMILAR_LEARNING_STYLE]->(similar:Student)-[comp:COMPLETED]->(c)
        WHERE sim.similarity > 0.7
        
        // Calculate predicted difficulty and success rate
        WITH c, s, 
             CASE WHEN COUNT(comp) > 0 
                  THEN AVG(comp.difficulty) 
                  ELSE c.avgDifficulty 
             END as predicted_difficulty,
             CASE WHEN COUNT(comp) > 0
                  THEN AVG(CASE WHEN comp.grade IN ['A', 'A-', 'B+'] THEN 1.0 ELSE 0.0 END)
                  ELSE 0.7
             END as success_rate,
             COUNT(comp) as similar_student_data
        
        // Count courses this would unlock
        OPTIONAL MATCH (c)-[:PREREQUISITE_FOR]->(unlocked:Course)-[:FULFILLS]->(:RequirementGroup)-[:PART_OF]->(d:Degree)
        WHERE NOT (s)-[:COMPLETED]->(unlocked)
        
        RETURN c.id as course_id, c.name as course_name, c.credits as credits,
               c.level as level, c.department as department,
               predicted_difficulty, success_rate, similar_student_data,
               COUNT(unlocked) as courses_unlocked,
               c.instructionModes as instruction_modes
        ORDER BY c.level ASC, predicted_difficulty ASC, courses_unlocked DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            return [dict(record) for record in result]

    def get_degree_requirements_progress(self, student_id: str) -> Dict:
        """Get detailed progress on degree requirements"""
        self._check_connection()

        query = """
        MATCH (s:Student {id: $student_id})-[:PURSUING]->(d:Degree)
        MATCH (rg:RequirementGroup)-[:PART_OF]->(d)
        
        // Get courses that fulfill this requirement group
        OPTIONAL MATCH (course:Course)-[:FULFILLS]->(rg)
        
        // Get completed courses in this requirement group
        OPTIONAL MATCH (s)-[:COMPLETED]->(completed_course:Course)-[:FULFILLS]->(rg)
        
        // Get enrolled courses in this requirement group  
        OPTIONAL MATCH (s)-[:ENROLLED_IN]->(enrolled_course:Course)-[:FULFILLS]->(rg)
        
        WITH rg, 
             COLLECT(DISTINCT {
                 id: course.id, 
                 name: course.name, 
                 credits: course.credits,
                 level: course.level
             }) as all_courses,
             COLLECT(DISTINCT {
                 id: completed_course.id,
                 name: completed_course.name,
                 credits: completed_course.credits
             }) as completed_courses,
             COLLECT(DISTINCT {
                 id: enrolled_course.id,
                 name: enrolled_course.name, 
                 credits: enrolled_course.credits
             }) as enrolled_courses,
             SUM(completed_course.credits) as completed_credits,
             SUM(enrolled_course.credits) as enrolled_credits
             
        RETURN rg.id as requirement_id, rg.name as requirement_name,
               rg.creditsRequired as credits_required,
               rg.requiredCourses as courses_required,
               COALESCE(completed_credits, 0) as completed_credits,
               COALESCE(enrolled_credits, 0) as enrolled_credits,
               all_courses, completed_courses, enrolled_courses
        ORDER BY rg.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            requirements = [dict(record) for record in result]
            
            # Calculate overall progress
            def _numeric(value, default=0):
                if isinstance(value, (int, float)):
                    return value
                if value in (None, ""):
                    return default
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return default

            total_required = sum(_numeric(req.get('credits_required')) for req in requirements)
            total_completed = sum(_numeric(req.get('completed_credits')) for req in requirements)
            total_enrolled = sum(_numeric(req.get('enrolled_credits')) for req in requirements)
            
            return {
                "requirements": requirements,
                "total_credits_required": total_required,
                "total_credits_completed": total_completed,
                "total_credits_enrolled": total_enrolled,
                "total_credits_remaining": total_required - total_completed - total_enrolled,
                "completion_percentage": (total_completed / total_required * 100) if total_required > 0 else 0
            }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
