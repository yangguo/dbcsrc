# DBCSRC Project Overview

## Project Description
DBCSRC is a comprehensive document analysis and web crawling system designed for processing regulatory documents, extracting financial information, and performing entity analysis. The system combines web scraping capabilities with advanced document processing and machine learning-based analysis.

## Architecture
The project consists of three main components:
- **Backend**: FastAPI-based REST API with AI/ML capabilities
- **Frontend (Legacy)**: Streamlit web application 
- **Frontend (Modern)**: Next.js with TypeScript and Ant Design

## Key Technologies
- **Backend**: FastAPI, Python 3.8+, MongoDB, Redis, OpenAI API
- **Frontend**: Next.js 14, TypeScript, Ant Design, TailwindCSS
- **AI/ML**: Transformers, PyTorch, scikit-learn, OpenAI GPT models
- **Infrastructure**: Docker, Docker Compose, Prometheus monitoring

## Core Features
- Document processing (PDF, DOCX, XLSX)
- Web crawling and data collection
- Financial penalty extraction
- Entity recognition (people, organizations, locations)
- AI-powered document classification
- Case management and search
- Batch processing capabilities
- Real-time monitoring and health checks

## Development Workflow
1. Backend development in `backend/` directory
2. Frontend development in `nextjs-frontend/` directory
3. Legacy Streamlit app in `frontend/` directory
4. Docker deployment with monitoring stack
5. Comprehensive testing with pytest and performance testing