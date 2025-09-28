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
            logger.warning("Neo4j driver not installed; running in demo mode")
            return

        if not all([uri, user, password]):
            logger.warning("Neo4j credentials missing; running in demo mode")
            return

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j")
        except AuthError as exc:
            logger.error(f"Neo4j auth failed: {exc}; falling back to demo data")
            self.driver = None
        except ServiceUnavailable as exc:
            logger.error(f"Neo4j unavailable: {exc}; falling back to demo data")
            self.driver = None
        except Exception as exc:
            logger.error(f"Neo4j init error: {exc}; falling back to demo data")
            self.driver = None

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
        if not self.driver:
            logger.warning("Neo4j not connected, returning demo data")
            return self._get_demo_students()
            
        query = """
        MATCH (s:Student)
        RETURN s.id as id, 
               s.name as name, 
               s.learningStyle as learning_style,
               s.enrollmentDate as enrollment_date,
               s.expectedGraduation as expected_graduation,
               s.preferredCourseLoad as preferred_course_load,
               s.preferredPace as preferred_pace,
               s.workHoursPerWeek as work_hours_per_week,
               s.financialAidStatus as financial_aid_status,
               s.preferredInstructionMode as preferred_instruction_mode
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
            return self._get_demo_students()

    def _get_demo_students(self) -> List[Dict]:
        """Return demo student data when Neo4j is not available"""
        return [
            {
                "id": "RE14884",
                "name": "Nicholas Berry",
                "learning_style": "Auditory",
                "enrollment_date": "2024-03-27",
                "expected_graduation": "2027-07-19",
                "preferred_course_load": 5,
                "preferred_pace": "Standard",
                "work_hours_per_week": 10,
                "financial_aid_status": "Self-Pay",
                "preferred_instruction_mode": "In-person"
            },
            {
                "id": "ST23456",
                "name": "Bob Smith",
                "learning_style": "Kinesthetic",
                "enrollment_date": "2023-08-20",
                "expected_graduation": "2025-12-15",
                "preferred_course_load": 4,
                "preferred_pace": "Accelerated",
                "work_hours_per_week": 15,
                "financial_aid_status": "Financial Aid",
                "preferred_instruction_mode": "Hybrid"
            },
            {
                "id": "ST34567",
                "name": "Carol Davis",
                "learning_style": "Visual",
                "enrollment_date": "2022-08-25",
                "expected_graduation": "2026-05-15",
                "preferred_course_load": 5,
                "preferred_pace": "Standard",
                "work_hours_per_week": 8,
                "financial_aid_status": "Scholarship",
                "preferred_instruction_mode": "Online"
            },
            {
                "id": "ST45678",
                "name": "David Wilson",
                "learning_style": "Reading-Writing",
                "enrollment_date": "2021-08-30",
                "expected_graduation": "2025-08-15",
                "preferred_course_load": 6,
                "preferred_pace": "Standard",
                "work_hours_per_week": 12,
                "financial_aid_status": "Self-Pay",
                "preferred_instruction_mode": "In-person"
            }
        ]

    def search_students(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search students by name or ID"""
        if not self.driver:
            logger.warning("Neo4j not connected, returning filtered demo data")
            demo_students = self._get_demo_students()
            search_lower = search_term.lower()
            return [s for s in demo_students 
                   if search_lower in s['name'].lower() or search_lower in s['id'].lower()]
            
        query = """
        MATCH (s:Student)
        WHERE toLower(s.name) CONTAINS toLower($search_term) 
           OR toLower(s.id) CONTAINS toLower($search_term)
        RETURN s.id as id, 
               s.name as name, 
               s.learningStyle as learning_style,
               s.enrollmentDate as enrollment_date,
               s.expectedGraduation as expected_graduation,
               s.preferredCourseLoad as preferred_course_load,
               s.preferredPace as preferred_pace,
               s.workHoursPerWeek as work_hours_per_week,
               s.financialAidStatus as financial_aid_status,
               s.preferredInstructionMode as preferred_instruction_mode
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
            # Fallback to demo data search
            demo_students = self._get_demo_students()
            search_lower = search_term.lower()
            return [s for s in demo_students 
                   if search_lower in s['name'].lower() or search_lower in s['id'].lower()]

    def _get_demo_student_details(self, student_id: str) -> Optional[Dict]:
        """Return detailed demo student information."""
        demo_details = {
            "ST12345": {
                "id": "ST12345",
                "name": "Alice Johnson",
                "learning_style": "Visual",
                "preferred_course_load": 4,
                "preferred_pace": "Accelerated",
                "work_hours_per_week": 10,
                "financial_aid_status": "Scholarship",
                "preferred_instruction_mode": "Hybrid",
                "enrollment_date": "2021-08-15",
                "expected_graduation": "2025-05-15",
                "degree_id": "BS-CS",
                "degree_name": "Bachelor of Science in Computer Science",
                "total_credits": 120
            },
            "ST23456": {
                "id": "ST23456",
                "name": "Bob Smith",
                "learning_style": "Kinesthetic",
                "preferred_course_load": 3,
                "preferred_pace": "Balanced",
                "work_hours_per_week": 20,
                "financial_aid_status": "None",
                "preferred_instruction_mode": "In-Person",
                "enrollment_date": "2020-08-15",
                "expected_graduation": "2025-12-15",
                "degree_id": "BA-CS",
                "degree_name": "Bachelor of Arts in Computer Science",
                "total_credits": 120
            },
            "ST34567": {
                "id": "ST34567",
                "name": "Carol Davis",
                "learning_style": "Auditory",
                "preferred_course_load": 2,
                "preferred_pace": "Steady",
                "work_hours_per_week": 30,
                "financial_aid_status": "Grants",
                "preferred_instruction_mode": "Online",
                "enrollment_date": "2022-01-15",
                "expected_graduation": "2026-05-15",
                "degree_id": "BS-BIO",
                "degree_name": "Bachelor of Science in Biology",
                "total_credits": 120
            },
            "ST45678": {
                "id": "ST45678",
                "name": "David Wilson",
                "learning_style": "Reading-Writing",
                "preferred_course_load": 4,
                "preferred_pace": "Balanced",
                "work_hours_per_week": 15,
                "financial_aid_status": "Loans",
                "preferred_instruction_mode": "In-Person",
                "enrollment_date": "2021-01-10",
                "expected_graduation": "2025-08-15",
                "degree_id": "BA-BIO",
                "degree_name": "Bachelor of Arts in Biology",
                "total_credits": 120
            }
        }

        if student_id not in demo_details:
            logger.warning(f"Demo student details requested for unknown ID {student_id}")
            return next(iter(demo_details.values()), None)
        return demo_details[student_id]

    def _get_demo_completed_courses(self, student_id: str) -> List[Dict]:
        """Return demo completed courses for a student."""
        demo_completed = {
            "RE14884": [
                {
                    "id": "CSUU 300",
                    "name": "Game Development Applications",
                    "department": "Computer Science",
                    "credits": 3,
                    "level": 300,
                    "avgDifficulty": 2,
                    "avgTimeCommitment": 7,
                    "termAvailability": ["Fall", "Spring"],
                    "instructionModes": ["In-person", "Online", "Hybrid"],
                    "tags": ["Computer Science", "Level-3", "Applications", "Game"],
                    "visualLearnerSuccess": 0.75,
                    "auditoryLearnerSuccess": 0.81,
                    "kinestheticLearnerSuccess": 0.84,
                    "readingLearnerSuccess": 0.87,
                    # Completion details from COMPLETED relationship
                    "completion_term": "Summer2024",
                    "grade": "A",
                    "difficulty_experienced": 4,
                    "time_spent_hours": 7,
                    "instruction_mode": "In-person",
                    "enjoyment": True
                },
                {
                    "id": "CSSS 200",
                    "name": "Data Structures",
                    "department": "Computer Science",
                    "credits": 4,
                    "level": 200,
                    "avgDifficulty": 3,
                    "avgTimeCommitment": 9,
                    "termAvailability": ["Fall", "Spring"],
                    "instructionModes": ["In-person", "Online"],
                    "tags": ["Computer Science", "Level-2", "Fundamentals"],
                    "visualLearnerSuccess": 0.70,
                    "auditoryLearnerSuccess": 0.85,
                    "kinestheticLearnerSuccess": 0.78,
                    "readingLearnerSuccess": 0.82,
                    # Completion details from COMPLETED relationship
                    "completion_term": "Spring2024",
                    "grade": "A-",
                    "difficulty_experienced": 3,
                    "time_spent_hours": 9,
                    "instruction_mode": "Online",
                    "enjoyment": True
                },
                {
                    "id": "CSTT 101",
                    "name": "Introduction to Programming",
                    "department": "Computer Science",
                    "credits": 4,
                    "level": 101,
                    "completion_term": "Fall2023",
                    "grade": "A+",
                    "difficulty_experienced": 2,
                    "time_spent_hours": 6,
                    "instruction_mode": "In-person",
                    "enjoyment": True
                },
                {
                    "id": "MATH 150",
                    "name": "Calculus I",
                    "department": "Mathematics",
                    "credits": 4,
                    "level": 150,
                    "completion_term": "Fall2023",
                    "grade": "B+",
                    "difficulty_experienced": 4,
                    "time_spent_hours": 12,
                    "instruction_mode": "In-person",
                    "enjoyment": False
                },
                {
                    "id": "ENGL 100",
                    "name": "Writing and Research",
                    "department": "English",
                    "credits": 3,
                    "level": 100,
                    "completion_term": "Spring2024",
                    "grade": "A",
                    "difficulty_experienced": 2,
                    "time_spent_hours": 5,
                    "instruction_mode": "Online",
                    "enjoyment": True
                },
                {
                    "id": "PHYS 121",
                    "name": "Physics I",
                    "department": "Physics",
                    "credits": 4,
                    "level": 121,
                    "completion_term": "Spring2024",
                    "grade": "B",
                    "difficulty_experienced": 5,
                    "time_spent_hours": 14,
                    "instruction_mode": "In-person",
                    "enjoyment": False
                },
                {
                    "id": "CMSC 201",
                    "name": "Computer Science I",
                    "department": "Computer Science",
                    "credits": 4,
                    "level": 201,
                    "completion_term": "Fall2023",
                    "grade": "A",
                    "difficulty_experienced": 3,
                    "time_spent_hours": 8,
                    "instruction_mode": "In-person",
                    "enjoyment": True
                },
                {
                    "id": "CMSC 202",
                    "name": "Computer Science II",
                    "department": "Computer Science",
                    "credits": 4,
                    "level": 202,
                    "completion_term": "Spring2024",
                    "grade": "A-",
                    "difficulty_experienced": 4,
                    "time_spent_hours": 10,
                    "instruction_mode": "In-person",
                    "enjoyment": True
                }
            ],
            "ST23456": [
                {
                    "course_id": "CMSC201",
                    "course_name": "Computer Science I",
                    "credits": 4,
                    "department": "CMSC",
                    "level": 200,
                    "grade": "B",
                    "term": "2020FA",
                    "study_hours": 9,
                    "difficulty": 0.5
                },
                {
                    "course_id": "ENGL100",
                    "course_name": "Composition",
                    "credits": 3,
                    "department": "ENGL",
                    "level": 100,
                    "grade": "A",
                    "term": "2020FA",
                    "study_hours": 5,
                    "difficulty": 0.3
                }
            ],
            "ST34567": [
                {
                    "course_id": "BIOL141",
                    "course_name": "Foundations of Biology",
                    "credits": 4,
                    "department": "BIOL",
                    "level": 100,
                    "grade": "A",
                    "term": "2022SP",
                    "study_hours": 11,
                    "difficulty": 0.4
                }
            ],
            "ST45678": [
                {
                    "course_id": "BIOL141",
                    "course_name": "Foundations of Biology",
                    "credits": 4,
                    "department": "BIOL",
                    "level": 100,
                    "grade": "B+",
                    "term": "2021SP",
                    "study_hours": 9,
                    "difficulty": 0.5
                },
                {
                    "course_id": "CHEM101",
                    "course_name": "Principles of Chemistry I",
                    "credits": 4,
                    "department": "CHEM",
                    "level": 100,
                    "grade": "B",
                    "term": "2021FA",
                    "study_hours": 10,
                    "difficulty": 0.6
                }
            ]
        }

        return demo_completed.get(student_id, [])

    def _get_demo_enrolled_courses(self, student_id: str) -> List[Dict]:
        """Return demo currently enrolled courses for a student."""
        demo_enrolled = {
            "RE14884": [
                {
                    "id": "BRRR 100",
                    "name": "Current Enrolled Course",
                    "credits": 3,
                    "department": "Computer Science",
                    "level": 100,
                    "avgDifficulty": 2,
                    "avgTimeCommitment": 6,
                    "termAvailability": ["Fall", "Spring", "Summer"],
                    "instructionModes": ["In-person", "Online"],
                    "tags": ["Computer Science", "Level-1", "Foundations"]
                },
                {
                    "id": "CSXX 400",
                    "name": "Advanced Topics in CS",
                    "credits": 4,
                    "department": "Computer Science", 
                    "level": 400,
                    "avgDifficulty": 4,
                    "avgTimeCommitment": 12,
                    "termAvailability": ["Fall", "Spring"],
                    "instructionModes": ["In-person"],
                    "tags": ["Computer Science", "Level-4", "Advanced"]
                },
                {
                    "id": "CSYY 350",
                    "name": "Software Engineering Methods",
                    "credits": 3,
                    "department": "Computer Science",
                    "level": 350,
                    "avgDifficulty": 3,
                    "avgTimeCommitment": 9,
                    "termAvailability": ["Fall", "Spring"],
                    "instructionModes": ["In-person", "Hybrid"],
                    "tags": ["Computer Science", "Level-3", "Software"]
                },
                {
                    "id": "CSZZ 300",
                    "name": "Database Systems",
                    "credits": 4,
                    "department": "Computer Science",
                    "level": 300,
                    "avgDifficulty": 3,
                    "avgTimeCommitment": 10,
                    "termAvailability": ["Fall", "Spring"],
                    "instructionModes": ["In-person", "Online"],
                    "tags": ["Computer Science", "Level-3", "Database"]
                },
                {
                    "id": "CSAA 250",
                    "name": "Data Structures Advanced",
                    "credits": 3,
                    "department": "Computer Science",
                    "level": 250,
                    "avgDifficulty": 3,
                    "avgTimeCommitment": 8,
                    "termAvailability": ["Fall", "Spring"],
                    "instructionModes": ["In-person", "Online"],
                    "tags": ["Computer Science", "Level-2", "Data Structures"]
                },
                {
                    "id": "CSBB 380",
                    "name": "Computer Networks",
                    "credits": 4,
                    "department": "Computer Science",
                    "level": 380,
                    "avgDifficulty": 4,
                    "avgTimeCommitment": 11,
                    "termAvailability": ["Fall", "Spring"],
                    "instructionModes": ["In-person"],
                    "tags": ["Computer Science", "Level-3", "Networks"]
                },
                {
                    "id": "CSCC 320",
                    "name": "Machine Learning Basics",
                    "credits": 3,
                    "department": "Computer Science",
                    "level": 320,
                    "avgDifficulty": 4,
                    "avgTimeCommitment": 10,
                    "termAvailability": ["Fall", "Spring"],
                    "instructionModes": ["In-person", "Online"],
                    "tags": ["Computer Science", "Level-3", "AI", "ML"]
                }
            ],
            "ST23456": [
                {
                    "course_id": "CMSC313",
                    "course_name": "Computer Organization",
                    "credits": 3,
                    "department": "CMSC",
                    "level": 300,
                    "term": "2024SP",
                    "expected_grade": "B"
                }
            ],
            "ST34567": [
                {
                    "course_id": "BIOL303",
                    "course_name": "Molecular and General Genetics",
                    "credits": 4,
                    "department": "BIOL",
                    "level": 300,
                    "term": "2024SP",
                    "expected_grade": "A-"
                }
            ],
            "ST45678": [
                {
                    "course_id": "BIOL251",
                    "course_name": "Human Anatomy and Physiology I",
                    "credits": 4,
                    "department": "BIOL",
                    "level": 200,
                    "term": "2024SP",
                    "expected_grade": "B+"
                }
            ]
        }

        return demo_enrolled.get(student_id, [])

    def _get_demo_degree_info(self, student_id: str) -> Optional[Dict]:
        """Return demo degree information for a student."""
        student_degree_map = {
            "ST12345": "BS-CS",
            "ST23456": "BA-CS",
            "ST34567": "BS-BIO",
            "ST45678": "BA-BIO"
        }

        degree_id = student_degree_map.get(student_id)
        if not degree_id:
            logger.warning(f"Demo degree info requested for unknown ID {student_id}")
            return None

        demo_degrees = {
            "BS-CS": {
                "degree_id": "BS-CS",
                "degree_name": "Bachelor of Science in Computer Science",
                "department": "Computer Science and Electrical Engineering",
                "degree_type": "B.S.",
                "total_credits": 120,
                "requirement_groups": [
                    {
                        "id": "BSCS-CORE",
                        "name": "Core Computer Science",
                        "required_courses": 8,
                        "credits_required": 32,
                        "course_count": 10
                    },
                    {
                        "id": "BSCS-MATH",
                        "name": "Mathematics",
                        "required_courses": 4,
                        "credits_required": 16,
                        "course_count": 6
                    }
                ]
            },
            "BA-CS": {
                "degree_id": "BA-CS",
                "degree_name": "Bachelor of Arts in Computer Science",
                "department": "Computer Science and Electrical Engineering",
                "degree_type": "B.A.",
                "total_credits": 120,
                "requirement_groups": [
                    {
                        "id": "BACS-CORE",
                        "name": "Core Computer Science",
                        "required_courses": 6,
                        "credits_required": 24,
                        "course_count": 8
                    },
                    {
                        "id": "BACS-CORE-DISC",
                        "name": "Disciplinary Electives",
                        "required_courses": 4,
                        "credits_required": 12,
                        "course_count": 6
                    }
                ]
            },
            "BS-BIO": {
                "degree_id": "BS-BIO",
                "degree_name": "Bachelor of Science in Biology",
                "department": "Biological Sciences",
                "degree_type": "B.S.",
                "total_credits": 120,
                "requirement_groups": [
                    {
                        "id": "BSBIO-CORE",
                        "name": "Core Biology",
                        "required_courses": 7,
                        "credits_required": 28,
                        "course_count": 9
                    },
                    {
                        "id": "BSBIO-LAB",
                        "name": "Laboratory Requirements",
                        "required_courses": 3,
                        "credits_required": 9,
                        "course_count": 4
                    }
                ]
            },
            "BA-BIO": {
                "degree_id": "BA-BIO",
                "degree_name": "Bachelor of Arts in Biology",
                "department": "Biological Sciences",
                "degree_type": "B.A.",
                "total_credits": 120,
                "requirement_groups": [
                    {
                        "id": "BABIO-CORE",
                        "name": "Core Biology",
                        "required_courses": 6,
                        "credits_required": 24,
                        "course_count": 8
                    },
                    {
                        "id": "BABIO-ELECT",
                        "name": "Biology Electives",
                        "required_courses": 4,
                        "credits_required": 12,
                        "course_count": 6
                    }
                ]
            }
        }

        return demo_degrees.get(degree_id)

    def _get_demo_course_catalog(self) -> Dict[str, Dict]:
        """Central catalog for demo course metadata and relationships."""
        if not hasattr(self, "_demo_course_catalog"):
            self._demo_course_catalog = {
                "CMSC201": {
                    "course_id": "CMSC201",
                    "course_name": "Computer Science I",
                    "credits": 4,
                    "department": "CMSC",
                    "level": 200,
                    "avg_difficulty": 2.5,
                    "instruction_modes": ["In-Person", "Hybrid"],
                    "tags": ["hands-on", "visual"],
                    "prerequisites": [],
                    "unlocks": ["CMSC202"],
                    "terms_offered": ["2024SP", "2024FA"],
                    "requirement_groups": ["BSCS-CORE", "BACS-CORE"]
                },
                "CMSC202": {
                    "course_id": "CMSC202",
                    "course_name": "Computer Science II",
                    "credits": 4,
                    "department": "CMSC",
                    "level": 200,
                    "avg_difficulty": 3.0,
                    "instruction_modes": ["In-Person", "Online"],
                    "tags": ["project", "hands-on"],
                    "prerequisites": ["CMSC201"],
                    "unlocks": ["CMSC313", "CMSC331"],
                    "terms_offered": ["2024SP", "2024FA"],
                    "requirement_groups": ["BSCS-CORE", "BACS-CORE"]
                },
                "CMSC313": {
                    "course_id": "CMSC313",
                    "course_name": "Computer Organization",
                    "credits": 3,
                    "department": "CMSC",
                    "level": 300,
                    "avg_difficulty": 3.4,
                    "instruction_modes": ["In-Person"],
                    "tags": ["hands-on", "lab"],
                    "prerequisites": ["CMSC202"],
                    "unlocks": ["CMSC411"],
                    "terms_offered": ["2024SP"],
                    "requirement_groups": ["BSCS-CORE", "BACS-CORE"]
                },
                "CMSC331": {
                    "course_id": "CMSC331",
                    "course_name": "Principles of Programming Languages",
                    "credits": 3,
                    "department": "CMSC",
                    "level": 300,
                    "avg_difficulty": 3.2,
                    "instruction_modes": ["In-Person", "Hybrid"],
                    "tags": ["writing", "analysis"],
                    "prerequisites": ["CMSC202"],
                    "unlocks": ["CMSC431"],
                    "terms_offered": ["2024SP", "2024FA"],
                    "requirement_groups": ["BSCS-CORE", "BACS-CORE"]
                },
                "CMSC341": {
                    "course_id": "CMSC341",
                    "course_name": "Data Structures",
                    "credits": 3,
                    "department": "CMSC",
                    "level": 300,
                    "avg_difficulty": 3.3,
                    "instruction_modes": ["In-Person", "Hybrid"],
                    "tags": ["visual", "project"],
                    "prerequisites": ["CMSC202"],
                    "unlocks": ["CMSC441"],
                    "terms_offered": ["2024SP", "2024FA"],
                    "requirement_groups": ["BSCS-CORE"]
                },
                "STAT355": {
                    "course_id": "STAT355",
                    "course_name": "Probability and Statistics",
                    "credits": 4,
                    "department": "STAT",
                    "level": 300,
                    "avg_difficulty": 2.8,
                    "instruction_modes": ["In-Person", "Online"],
                    "tags": ["visual", "analysis"],
                    "prerequisites": ["MATH152"],
                    "unlocks": [],
                    "terms_offered": ["2024SP"],
                    "requirement_groups": ["BSCS-MATH"]
                },
                "ENGL100": {
                    "course_id": "ENGL100",
                    "course_name": "Composition",
                    "credits": 3,
                    "department": "ENGL",
                    "level": 100,
                    "avg_difficulty": 2.0,
                    "instruction_modes": ["In-Person", "Online"],
                    "tags": ["writing"],
                    "prerequisites": [],
                    "unlocks": [],
                    "terms_offered": ["2024SP", "2024FA"],
                    "requirement_groups": ["BACS-CORE-DISC", "BABIO-ELECT"]
                },
                "MATH151": {
                    "course_id": "MATH151",
                    "course_name": "Calculus I",
                    "credits": 4,
                    "department": "MATH",
                    "level": 100,
                    "avg_difficulty": 3.0,
                    "instruction_modes": ["In-Person"],
                    "tags": ["visual", "analysis"],
                    "prerequisites": [],
                    "unlocks": ["MATH152"],
                    "terms_offered": ["2024SP", "2024FA"],
                    "requirement_groups": ["BSCS-MATH"]
                },
                "MATH152": {
                    "course_id": "MATH152",
                    "course_name": "Calculus II",
                    "credits": 4,
                    "department": "MATH",
                    "level": 100,
                    "avg_difficulty": 3.1,
                    "instruction_modes": ["In-Person"],
                    "tags": ["visual", "analysis"],
                    "prerequisites": ["MATH151"],
                    "unlocks": ["STAT355"],
                    "terms_offered": ["2024FA"],
                    "requirement_groups": ["BSCS-MATH"]
                },
                "BIOL141": {
                    "course_id": "BIOL141",
                    "course_name": "Foundations of Biology",
                    "credits": 4,
                    "department": "BIOL",
                    "level": 100,
                    "avg_difficulty": 2.7,
                    "instruction_modes": ["In-Person", "Lab"],
                    "tags": ["hands-on", "lab"],
                    "prerequisites": [],
                    "unlocks": ["BIOL303", "BIOL251"],
                    "terms_offered": ["2024SP", "2024FA"],
                    "requirement_groups": ["BSBIO-CORE", "BABIO-CORE"]
                },
                "BIOL251": {
                    "course_id": "BIOL251",
                    "course_name": "Human Anatomy and Physiology I",
                    "credits": 4,
                    "department": "BIOL",
                    "level": 200,
                    "avg_difficulty": 3.1,
                    "instruction_modes": ["In-Person", "Lab"],
                    "tags": ["lab", "hands-on"],
                    "prerequisites": ["BIOL141"],
                    "unlocks": [],
                    "terms_offered": ["2024SP"],
                    "requirement_groups": ["BSBIO-CORE", "BABIO-CORE"]
                },
                "BIOL303": {
                    "course_id": "BIOL303",
                    "course_name": "Molecular and General Genetics",
                    "credits": 4,
                    "department": "BIOL",
                    "level": 300,
                    "avg_difficulty": 3.6,
                    "instruction_modes": ["In-Person", "Lab"],
                    "tags": ["lab", "research"],
                    "prerequisites": ["BIOL141"],
                    "unlocks": ["BIOL424"],
                    "terms_offered": ["2024SP", "2024FA"],
                    "requirement_groups": ["BSBIO-CORE", "BABIO-ELECT", "BSBIO-LAB"]
                },
                "CHEM101": {
                    "course_id": "CHEM101",
                    "course_name": "Principles of Chemistry I",
                    "credits": 4,
                    "department": "CHEM",
                    "level": 100,
                    "avg_difficulty": 3.0,
                    "instruction_modes": ["In-Person", "Lab"],
                    "tags": ["lab", "analysis"],
                    "prerequisites": [],
                    "unlocks": ["CHEM102"],
                    "terms_offered": ["2024FA"],
                    "requirement_groups": ["BSBIO-CORE", "BABIO-CORE"]
                }
            }
        return self._demo_course_catalog

    def _clone_demo_course(self, course: Dict) -> Dict:
        """Return a shallow copy of a course dict with standardized keys."""
        return {
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "credits": course["credits"],
            "department": course["department"],
            "level": course["level"],
            "avg_difficulty": course.get("avg_difficulty", 0.6),
            "instruction_modes": course.get("instruction_modes", []),
            "tags": course.get("tags", [])
        }

    def _get_demo_available_courses(self, student_id: str, term: str = None) -> List[Dict]:
        catalog = self._get_demo_course_catalog()
        completed = {c["course_id"] for c in self._get_demo_completed_courses(student_id)}
        enrolled = {c["course_id"] for c in self._get_demo_enrolled_courses(student_id)}

        available = []
        for course_id, data in catalog.items():
            if course_id in completed or course_id in enrolled:
                continue

            prereqs = set(data.get("prerequisites", []))
            if not prereqs.issubset(completed):
                continue

            if term and term not in data.get("terms_offered", []):
                continue

            course_entry = self._clone_demo_course(data)
            course_entry["avg_difficulty"] = data.get("avg_difficulty", 0.6)
            available.append(course_entry)

        available.sort(key=lambda c: (c.get("level", 400), c.get("course_name", "")))
        return available

    def _get_demo_course_prerequisites(self, course_id: str) -> List[Dict]:
        catalog = self._get_demo_course_catalog()
        course = catalog.get(course_id)
        if not course:
            return []

        prereq_ids = course.get("prerequisites", [])
        results = []
        for pid in prereq_ids:
            prereq = catalog.get(pid)
            if prereq:
                prereq_entry = self._clone_demo_course(prereq)
                results.append(prereq_entry)
        results.sort(key=lambda c: (c.get("level", 400), c.get("course_name", "")))
        return results

    def _get_demo_courses_unlocked_by(self, course_id: str) -> List[Dict]:
        catalog = self._get_demo_course_catalog()
        unlocked_courses = []
        for course in catalog.values():
            if course_id in course.get("prerequisites", []):
                unlocked_courses.append(self._clone_demo_course(course))

        unlocked_courses.sort(key=lambda c: (c.get("level", 400), c.get("course_name", "")))
        return unlocked_courses

    def _get_demo_similar_students(self, student_id: str, min_similarity: float) -> List[Dict]:
        demo_students = {
            "ST12345": [
                {"id": "ST23456", "name": "Bob Smith", "learning_style": "Kinesthetic", "similarity": 0.78, "similarity_type": "SIMILAR_PERFORMANCE", "avg_gpa": 3.3, "courses_completed": 24},
                {"id": "ST34567", "name": "Carol Davis", "learning_style": "Auditory", "similarity": 0.72, "similarity_type": "SIMILAR_LEARNING_STYLE", "avg_gpa": 3.6, "courses_completed": 18}
            ],
            "ST23456": [
                {"id": "ST12345", "name": "Alice Johnson", "learning_style": "Visual", "similarity": 0.74, "similarity_type": "SIMILAR_PERFORMANCE", "avg_gpa": 3.5, "courses_completed": 28}
            ],
            "ST34567": [
                {"id": "ST45678", "name": "David Wilson", "learning_style": "Reading-Writing", "similarity": 0.76, "similarity_type": "SIMILAR_LEARNING_STYLE", "avg_gpa": 3.2, "courses_completed": 20}
            ],
            "ST45678": [
                {"id": "ST34567", "name": "Carol Davis", "learning_style": "Auditory", "similarity": 0.81, "similarity_type": "SIMILAR_PERFORMANCE", "avg_gpa": 3.4, "courses_completed": 22}
            ]
        }

        candidates = demo_students.get(student_id, [])
        return [student for student in candidates if student.get("similarity", 0) >= min_similarity]

    def _get_demo_optimal_course_sequence(self, student_id: str) -> List[Dict]:
        catalog = self._get_demo_course_catalog()
        available = self._get_demo_available_courses(student_id)
        student = self._get_demo_student_details(student_id) or {}
        learning_style = student.get("learning_style", "")
        completed_ids = {c["course_id"] for c in self._get_demo_completed_courses(student_id)}

        demo_sequences = {
            "ST12345": ["MATH152", "STAT355", "CMSC331", "CMSC341", "CMSC313"],
            "ST23456": ["CMSC331", "CMSC313", "ENGL100", "MATH152"],
            "ST34567": ["BIOL251", "BIOL303", "CHEM101", "ENGL100"],
            "ST45678": ["BIOL303", "BIOL251", "CHEM101", "ENGL100"]
        }
        course_order = demo_sequences.get(student_id)
        if course_order:
            ordered_courses = [course for cid in course_order for course in available if course["course_id"] == cid]
            remaining = [course for course in available if course["course_id"] not in course_order]
            ordered_courses.extend(remaining)
        else:
            ordered_courses = available

        style_mappings = {
            'Visual': ['visual', 'graphics', 'charts', 'diagrams', 'visualization'],
            'Auditory': ['discussion', 'lecture', 'presentation', 'verbal'],
            'Kinesthetic': ['hands-on', 'lab', 'practical', 'project', 'interactive'],
            'Reading-Writing': ['writing', 'reading', 'research', 'analysis', 'documentation']
        }
        preferred_tags = [tag.lower() for tag in style_mappings.get(learning_style, [])]

        sequence = []
        for course in ordered_courses:
            catalog_entry = catalog.get(course["course_id"], {})
            tags = [tag.lower() for tag in catalog_entry.get("tags", [])]
            if tags and preferred_tags:
                matches = sum(1 for tag in tags if any(pref in tag for pref in preferred_tags))
                learning_match = min(matches / len(tags), 1.0)
            else:
                learning_match = 0.5

            avg_difficulty = catalog_entry.get("avg_difficulty", 3.0)
            unlocks = catalog_entry.get("unlocks", [])
            similar_students = self._get_demo_similar_students(student_id, 0.0)
            prereq_entries = [p for p in self._get_demo_course_prerequisites(course["course_id"]) if p["course_id"] not in completed_ids]

            sequence.append({
                **course,
                "priority_score": len(unlocks) * 10 + course.get("credits", 3) * 2,
                "prerequisites": prereq_entries,
                "unlocks": self._get_demo_courses_unlocked_by(course["course_id"]),
                "learning_style_match": learning_match,
                "difficulty_prediction": avg_difficulty,
                "predicted_difficulty": avg_difficulty,
                "success_rate": 0.8,
                "similar_student_data": len(similar_students),
                "courses_unlocked": len(unlocks),
                "instruction_modes": catalog_entry.get("instruction_modes", [])
            })

        sequence.sort(key=lambda c: (c.get("level", 400), c.get("predicted_difficulty", 1.0), -c.get("courses_unlocked", 0)))
        return sequence

    def _get_demo_degree_requirements_progress(self, student_id: str) -> Dict:
        degree = self._get_demo_degree_info(student_id)
        if not degree:
            return {
                "requirements": [],
                "total_credits_required": 0,
                "total_credits_completed": 0,
                "total_credits_enrolled": 0,
                "total_credits_remaining": 0,
                "completion_percentage": 0
            }

        catalog = self._get_demo_course_catalog()
        completed = self._get_demo_completed_courses(student_id)
        enrolled = self._get_demo_enrolled_courses(student_id)
        completed_ids = {c["course_id"] for c in completed}
        enrolled_ids = {c["course_id"] for c in enrolled}

        requirements = []
        total_required = 0
        total_completed = 0
        total_enrolled = 0

        for group in degree.get("requirement_groups", []):
            group_id = group.get("id")
            all_courses = [self._clone_demo_course(course) for course in catalog.values() if group_id in course.get("requirement_groups", [])]
            completed_courses = [self._clone_demo_course(catalog[cid]) for cid in completed_ids if cid in catalog and group_id in catalog[cid].get("requirement_groups", [])]
            enrolled_courses = [self._clone_demo_course(catalog[cid]) for cid in enrolled_ids if cid in catalog and group_id in catalog[cid].get("requirement_groups", [])]

            completed_credits = sum(course["credits"] for course in completed_courses)
            enrolled_credits = sum(course["credits"] for course in enrolled_courses)

            total_required += group.get("credits_required", 0)
            total_completed += completed_credits
            total_enrolled += enrolled_credits

            requirements.append({
                "requirement_id": group_id,
                "requirement_name": group.get("name"),
                "credits_required": group.get("credits_required", 0),
                "courses_required": group.get("required_courses", 0),
                "completed_credits": completed_credits,
                "enrolled_credits": enrolled_credits,
                "all_courses": all_courses,
                "completed_courses": completed_courses,
                "enrolled_courses": enrolled_courses
            })

        total_remaining = max(total_required - total_completed - total_enrolled, 0)
        completion_percentage = (total_completed / total_required * 100) if total_required else 0

        return {
            "requirements": requirements,
            "total_credits_required": total_required,
            "total_credits_completed": total_completed,
            "total_credits_enrolled": total_enrolled,
            "total_credits_remaining": total_remaining,
            "completion_percentage": completion_percentage
        }

    def get_student_details(self, student_id: str) -> Optional[Dict]:
        """Get detailed information about a specific student"""
        if not self.driver:
            return self._get_demo_student_details(student_id)
            
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
                else:
                    return self._get_demo_student_details(student_id)
        except Exception as e:
            logger.error(f"Error fetching student details: {e}")
            return self._get_demo_student_details(student_id)

    def get_student_completed_courses(self, student_id: str) -> List[Dict]:
        """Get courses completed by a student"""
        if not self.driver:
            return self._get_demo_completed_courses(student_id)
            
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
            return self._get_demo_completed_courses(student_id)

    def get_student_enrolled_courses(self, student_id: str) -> List[Dict]:
        """Get courses currently enrolled by a student"""
        if not self.driver:
            return self._get_demo_enrolled_courses(student_id)
            
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
            return self._get_demo_enrolled_courses(student_id)

    def get_student_degree(self, student_id: str) -> Optional[Dict]:
        """Get degree program information for a student"""
        if not self.driver:
            return self._get_demo_degree_info(student_id)
            
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
                else:
                    return self._get_demo_degree_info(student_id)
        except Exception as e:
            logger.error(f"Error fetching degree info: {e}")
            return self._get_demo_degree_info(student_id)

    def get_available_courses(self, student_id: str, term: str = None) -> List[Dict]:
        """Get courses available to a student (prerequisites met, not already taken)"""
        if not self.driver:
            return self._get_demo_available_courses(student_id, term)

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
        if not self.driver:
            return self._get_demo_course_prerequisites(course_id)

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
        if not self.driver:
            return self._get_demo_courses_unlocked_by(course_id)

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
        if not self.driver:
            return self._get_demo_similar_students(student_id, min_similarity)

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
        if not self.driver:
            return self._get_demo_optimal_course_sequence(student_id)

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
        if not self.driver:
            return self._get_demo_degree_requirements_progress(student_id)

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
            total_required = sum(req['credits_required'] for req in requirements)
            total_completed = sum(req['completed_credits'] for req in requirements)
            total_enrolled = sum(req['enrolled_credits'] for req in requirements)
            
            return {
                "requirements": requirements,
                "total_credits_required": total_required,
                "total_credits_completed": total_completed,
                "total_credits_enrolled": total_enrolled,
                "total_credits_remaining": total_required - total_completed - total_enrolled,
                "completion_percentage": (total_completed / total_required * 100) if total_required > 0 else 0
            }

    def get_student_complete_data(self, student_id: str) -> Optional[Dict]:
        """Get ALL student data in a single optimized query"""
        if not self.driver:
            logger.warning("Neo4j not connected, returning demo data")
            return self._get_demo_complete_data(student_id)
            
        query = """
        MATCH (s:Student {id: $student_id})
        OPTIONAL MATCH (s)-[comp:COMPLETED]->(cc:Course)
        OPTIONAL MATCH (s)-[:ENROLLED_IN]->(ec:Course)
        
        RETURN s,
               collect(DISTINCT {
                   course: cc,
                   relationship: comp,
                   type: 'completed'
               }) as completed_courses,
               collect(DISTINCT {
                   course: ec,
                   type: 'enrolled'
               }) as enrolled_courses
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, student_id=student_id)
                record = result.single()
                
                if not record:
                    return None
                
                # Process the comprehensive result
                student_data = self._convert_neo4j_types(dict(record['s']))
                
                # Process completed courses with relationship data
                completed = []
                for item in record['completed_courses']:
                    if item['course']:
                        course_data = self._convert_neo4j_types(dict(item['course']))
                        
                        # Add completion details from the relationship
                        if item['relationship']:
                            rel_data = self._convert_neo4j_types(dict(item['relationship']))
                            course_data.update({
                                'completion_term': rel_data.get('term'),
                                'grade': rel_data.get('grade'),
                                'difficulty_experienced': rel_data.get('difficulty'),
                                'time_spent_hours': rel_data.get('timeSpent'),
                                'instruction_mode': rel_data.get('instructionMode'),
                                'enjoyment': rel_data.get('enjoyment')
                            })
                        
                        completed.append(course_data)
                
                # Process enrolled courses
                enrolled = []
                for item in record['enrolled_courses']:
                    if item['course']:
                        enrolled.append(self._convert_neo4j_types(dict(item['course'])))
                
                # Calculate degree progress based on completed courses
                total_credits_completed = sum(course.get('credits', 0) for course in completed)
                
                return {
                    'student': student_data,
                    'degree_info': {
                        'total_credits_completed': total_credits_completed,
                        'estimated_total_credits': 120  # Default, can be updated later
                    },
                    'completed_courses': completed,
                    'enrolled_courses': enrolled
                }
                
        except Exception as e:
            logger.error(f"Error fetching complete student data: {e}")
            return self._get_demo_complete_data(student_id)
    
    def get_course_details(self, course_id: str) -> Optional[Dict]:
        """Get detailed course information with relationships"""
        if not self.driver:
            logger.warning("Neo4j not connected, returning demo data")
            return self._get_demo_course_details(course_id)
            
        query = """
        MATCH (c:Course {id: $course_id})
        OPTIONAL MATCH (c)-[prereq:PREREQUISITE_FOR]->(target:Course)
        OPTIONAL MATCH (source:Course)-[leads:LEADS_TO]->(c)
        OPTIONAL MATCH (c)-[similar:SIMILAR_CONTENT]->(related:Course)
        
        RETURN c,
               collect(DISTINCT {
                   course: target,
                   relationship: prereq,
                   type: 'prerequisite_for'
               }) as prerequisites_for,
               collect(DISTINCT {
                   course: source,
                   relationship: leads,
                   type: 'leads_from'
               }) as leads_from,
               collect(DISTINCT {
                   course: related,
                   relationship: similar,
                   type: 'similar_content'
               }) as similar_courses
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, course_id=course_id)
                record = result.single()
                
                if not record:
                    return None
                
                course_data = self._convert_neo4j_types(dict(record['c']))
                
                # Process relationships
                course_data['prerequisites_for'] = []
                course_data['leads_from'] = []
                course_data['similar_courses'] = []
                
                for item in record['prerequisites_for']:
                    if item['course'] and item['relationship']:
                        rel_data = self._convert_neo4j_types(dict(item['relationship']))
                        target_course = self._convert_neo4j_types(dict(item['course']))
                        course_data['prerequisites_for'].append({
                            'course': target_course,
                            'strength': rel_data.get('strength'),
                            'min_grade': rel_data.get('minGrade')
                        })
                
                for item in record['leads_from']:
                    if item['course'] and item['relationship']:
                        rel_data = self._convert_neo4j_types(dict(item['relationship']))
                        source_course = self._convert_neo4j_types(dict(item['course']))
                        course_data['leads_from'].append({
                            'course': source_course,
                            'commonality': rel_data.get('commonality'),
                            'success_correlation': rel_data.get('successCorrelation')
                        })
                
                for item in record['similar_courses']:
                    if item['course'] and item['relationship']:
                        rel_data = self._convert_neo4j_types(dict(item['relationship']))
                        related_course = self._convert_neo4j_types(dict(item['course']))
                        course_data['similar_courses'].append({
                            'course': related_course,
                            'similarity': rel_data.get('similarity')
                        })
                
                return course_data
                
        except Exception as e:
            logger.error(f"Error fetching course details: {e}")
            return self._get_demo_course_details(course_id)

    def get_learning_style_course_success(self, course_id: str, learning_style: str) -> float:
        """Get success rate for a specific learning style in a course"""
        if not self.driver:
            return 0.75  # Default success rate
            
        query = """
        MATCH (c:Course {id: $course_id})
        RETURN c.visualLearnerSuccess as visual,
               c.auditoryLearnerSuccess as auditory,
               c.kinestheticLearnerSuccess as kinesthetic,
               c.readingLearnerSuccess as reading
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, course_id=course_id)
                record = result.single()
                
                if not record:
                    return 0.75
                
                style_map = {
                    'Visual': record.get('visual', 0.75),
                    'Auditory': record.get('auditory', 0.75),
                    'Kinesthetic': record.get('kinesthetic', 0.75),
                    'Reading-Writing': record.get('reading', 0.75)
                }
                
                return style_map.get(learning_style, 0.75)
                
        except Exception as e:
            logger.error(f"Error fetching learning style success rate: {e}")
            return 0.75

    def _get_demo_course_details(self, course_id: str) -> Optional[Dict]:
        """Return demo course details"""
        demo_courses = {
            "CSUU 300": {
                "id": "CSUU 300",
                "name": "Game Development Applications",
                "department": "Computer Science",
                "credits": 3,
                "level": 300,
                "avgDifficulty": 2,
                "avgTimeCommitment": 7,
                "termAvailability": ["Fall", "Spring"],
                "instructionModes": ["In-person", "Online", "Hybrid"],
                "tags": ["Computer Science", "Level-3", "Applications", "Game"],
                "visualLearnerSuccess": 0.75,
                "auditoryLearnerSuccess": 0.81,
                "kinestheticLearnerSuccess": 0.84,
                "readingLearnerSuccess": 0.87,
                "prerequisites_for": [],
                "leads_from": [],
                "similar_courses": []
            }
        }
        return demo_courses.get(course_id)

    def _get_demo_complete_data(self, student_id: str) -> Dict:
        """Return all demo data for a student in one structure"""
        student = self._get_demo_student_details(student_id)
        if not student:
            return None
            
        return {
            'student': student,
            'degree_info': {
                'total_credits_completed': 60,
                'estimated_total_credits': 120
            },
            'completed_courses': self._get_demo_completed_courses(student_id),
            'enrolled_courses': self._get_demo_enrolled_courses(student_id)
        }

    def create_sample_data(self):
        """Create sample data matching the new schema format"""
        if not self.driver:
            logger.warning("Neo4j not connected, cannot create sample data")
            return False
            
        try:
            with self.driver.session() as session:
                # Create sample student
                student_query = """
                CREATE (s:Student {
                    id: "RE14884",
                    name: "Nicholas Berry",
                    enrollmentDate: date("2024-03-27"),
                    expectedGraduation: date("2027-07-19"),
                    learningStyle: "Auditory",
                    preferredCourseLoad: 5,
                    preferredPace: "Standard",
                    workHoursPerWeek: 10,
                    financialAidStatus: "Self-Pay",
                    preferredInstructionMode: "In-person"
                })
                """
                session.run(student_query)
                
                # Create sample courses
                course_queries = [
                    """
                    CREATE (c:Course {
                        id: "CSUU 300",
                        name: "Game Development Applications",
                        department: "Computer Science",
                        credits: 3,
                        level: 300,
                        avgDifficulty: 2,
                        avgTimeCommitment: 7,
                        termAvailability: ["Fall", "Spring"],
                        instructionModes: ["In-person", "Online", "Hybrid"],
                        tags: ["Computer Science", "Level-3", "Applications", "Game"],
                        visualLearnerSuccess: 0.75,
                        auditoryLearnerSuccess: 0.81,
                        kinestheticLearnerSuccess: 0.84,
                        readingLearnerSuccess: 0.87
                    })
                    """,
                    """
                    CREATE (c:Course {
                        id: "CSSS 400",
                        name: "Advanced Software Engineering",
                        department: "Computer Science",
                        credits: 4,
                        level: 400,
                        avgDifficulty: 4,
                        avgTimeCommitment: 10,
                        termAvailability: ["Fall", "Spring"],
                        instructionModes: ["In-person", "Hybrid"],
                        tags: ["Computer Science", "Level-4", "Software", "Engineering"],
                        visualLearnerSuccess: 0.70,
                        auditoryLearnerSuccess: 0.75,
                        kinestheticLearnerSuccess: 0.80,
                        readingLearnerSuccess: 0.85
                    })
                    """
                ]
                
                for query in course_queries:
                    session.run(query)
                
                # Create relationships
                relationship_queries = [
                    """
                    MATCH (source:Course {id: "CSUU 300"}), (target:Course {id: "CSSS 400"})
                    CREATE (source)-[:LEADS_TO {commonality: 0.77, successCorrelation: 0.61}]->(target)
                    """,
                    """
                    MATCH (s:Student {id: "RE14884"}), (c:Course {id: "CSUU 300"})
                    CREATE (s)-[:COMPLETED {
                        term: "Summer2024",
                        grade: "A",
                        difficulty: 4,
                        timeSpent: 7,
                        instructionMode: "In-person",
                        enjoyment: true
                    }]->(c)
                    """
                ]
                
                for query in relationship_queries:
                    session.run(query)
                
                logger.info("Sample data created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error creating sample data: {e}")
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
