# UMBC Degree Planner - AI-Powered Academic Advisor

An interactive web application that helps students find the fastest path to graduation by leveraging the UMBC Neo4j academic dataset and Google Gemini AI for personalized recommendations.

## 🌟 Features

- **Student Search & Selection**: Browse and select from UMBC student database
- **Optimal Path Planning**: AI-powered algorithm to find fastest graduation route
- **Learning Style Optimization**: Course recommendations based on individual learning styles  
- **Prerequisites Management**: Automatic prerequisite checking and sequencing
- **Risk Analysis**: Identifies potential challenges and bottlenecks
- **Peer Insights**: Learn from similar successful students
- **AI Chat Assistant**: Get personalized academic advice using Gemini AI
- **Interactive Timeline**: Visual course planning with term-by-term breakdown

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Neo4j Database** with UMBC dataset loaded
3. **Google API Key** for Gemini AI (optional but recommended)

### 1. Set Up Neo4j Database

Follow the instructions in the main README to set up Neo4j with the UMBC academic dataset.

Ensure your Neo4j instance is running at `bolt://localhost:7687` with default credentials, or set environment variables:
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"
```

### 2. Get Google API Key (Recommended)

1. Go to [Google AI Studio](https://makersuite.google.com/)
2. Create an API key for Gemini
3. Set the environment variable:
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

### 3. Install Dependencies

```bash
# Navigate to degree_planner directory
cd degree_planner

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 🏗️ Architecture

```
degree_planner/
├── app.py              # Main Flask application
├── neo4j_client.py     # Neo4j database interface
├── gemini_client.py    # Google Gemini AI integration
├── degree_optimizer.py # Path optimization algorithms
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Main HTML template
└── static/
    ├── css/
    │   └── styles.css  # Custom styling
    └── js/
        └── app.js      # Frontend JavaScript
```

## 📊 Core Algorithms

### Degree Path Optimization

The system uses a multi-factor scoring algorithm to find optimal course sequences:

1. **Prerequisite Impact**: Courses that unlock more future courses get higher priority
2. **Learning Style Alignment**: Matches courses to student's learning preferences
3. **Difficulty Prediction**: Based on similar students' experiences
4. **Credit Efficiency**: Optimizes for faster degree completion
5. **Success Rate**: Considers historical performance data

### Risk Analysis

Identifies potential challenges:
- High difficulty course clusters
- Work-study balance issues
- Learning style mismatches
- Complex prerequisite chains

## 🤖 AI Integration

### Gemini AI Features

The application integrates Google Gemini for:
- **Personalized Course Recommendations**
- **Study Strategy Advice** based on learning styles
- **Academic Timeline Optimization**
- **Risk Mitigation Strategies**
- **Peer Comparison Insights**

### Chat Interface

Students can ask questions like:
- "What courses should I take next semester?"
- "How can I improve my study habits for difficult courses?"
- "Am I on track to graduate on time?"
- "What do successful students with my learning style do differently?"

## 🎯 Usage Guide

### 1. Select a Student
- Use the search box to find students by name or ID
- Click on a student to load their academic profile

### 2. View Overview
- See degree progress, completion percentage
- Review academic timeline
- Check identified risk factors

### 3. Generate Optimal Path
- Click "Optimize Path" to run the algorithm
- Review term-by-term course recommendations
- See difficulty predictions and risk assessments

### 4. Get Recommendations
- View next-term course suggestions
- Compare with similar successful students
- Access personalized insights

### 5. Chat with AI
- Ask specific questions about academic planning
- Get study strategies based on your learning style
- Receive timeline optimization advice

## 🔧 Configuration

### Environment Variables

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Gemini AI Configuration (optional)
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-1.5-flash-001  # optional override

# Flask Configuration
FLASK_ENV=development  # or production
FLASK_DEBUG=true       # for development
```

### Database Requirements

The application expects the UMBC Neo4j dataset with these node types:
- `Student`: Student profiles with learning styles
- `Course`: Course information with difficulty ratings
- `Degree`: Degree program requirements
- `RequirementGroup`: Degree requirement categories
- `Term`: Academic terms and scheduling
- `Faculty`: Instructor information

## 🚨 Troubleshooting

### Common Issues

1. **Neo4j Connection Failed**
   - Verify Neo4j is running
   - Check connection credentials
   - Ensure UMBC dataset is loaded

2. **AI Features Not Working**
   - Verify GOOGLE_API_KEY is set
   - Confirm the Gemini model name matches an available model (default: `models/gemini-2.5-flash`)
   - Check API quota and billing
   - Application will run without AI (limited features)

3. **Slow Path Optimization**
   - Large datasets may take time to process
   - Consider reducing dataset size for testing
   - Check Neo4j indexes are created

4. **Empty Student List**
   - Verify UMBC dataset is properly imported
   - Check Neo4j query permissions
   - Review application logs for errors

### Health Check

Visit `http://localhost:5000/health` to check:
- Neo4j connection status
- Gemini AI availability
- System health overview

## 🎓 Educational Value

This application demonstrates:
- **Graph Database Queries**: Complex Cypher queries for academic relationships
- **AI Integration**: Practical use of Large Language Models for education
- **Optimization Algorithms**: Multi-factor course sequencing
- **Web Development**: Full-stack application with modern UI
- **Data Visualization**: Interactive charts and timelines

## 🛠️ Development

### Adding New Features

1. **New API Endpoints**: Add routes in `app.py`
2. **Database Queries**: Extend `neo4j_client.py`
3. **AI Functionality**: Enhance `gemini_client.py`
4. **Frontend Features**: Update `static/js/app.js`

### Testing

```bash
# Test Neo4j connection
python -c "from neo4j_client import Neo4jClient; print(Neo4jClient().test_connection())"

# Test Gemini API
python -c "from gemini_client import GeminiClient; print(GeminiClient().test_connection())"
```

## 📄 License

This project is part of the HackUMBC 2025 dataset and is intended for educational and hackathon purposes.

## 🤝 Contributing

This is a hackathon project, but feel free to:
1. Fork the repository
2. Add new features or improvements
3. Submit pull requests
4. Report issues

## 📞 Support

For questions about the UMBC dataset or this application:
- **Email**: Jason Paluck - paluck@umbc.edu  
- **Phone**: 914-420-8505

---

Built with ❤️ for HackUMBC 2025
