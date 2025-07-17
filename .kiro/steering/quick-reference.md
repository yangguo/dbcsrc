# DBCSRC Quick Reference Guide

## Project Structure
```
dbcsrc/
├── backend/              # FastAPI backend (Python 3.8+)
├── nextjs-frontend/      # Modern Next.js frontend (TypeScript)
├── frontend/             # Legacy Streamlit frontend
├── data/                 # Data storage and processing
├── monitoring/           # Monitoring configurations
└── .kiro/steering/       # Development guidelines
```

## Quick Start Commands
```bash
# Start backend
cd backend && python main.py

# Start Next.js frontend
cd nextjs-frontend && npm run dev

# Start with Docker
docker-compose up -d
```

## Key Endpoints
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **Health Check**: http://localhost:8000/health

## Core Features
1. **Document Processing**: PDF, DOCX, XLSX support with AI analysis
2. **Web Crawling**: Automated data collection from regulatory sites
3. **Entity Extraction**: People, organizations, locations, financial amounts
4. **Case Management**: Search, update, classify, and export cases
5. **AI Classification**: OpenAI-powered document categorization
6. **Monitoring**: Health checks, metrics, and performance tracking

## Environment Variables (Backend)
```env
OPENAI_API_KEY=your_api_key_here
MONGODB_URL=mongodb://localhost:27017/dbcsrc
FRONTEND_URL=http://localhost:3000
DEBUG=false
```

## Common Issues & Solutions
1. **Network Error**: Ensure backend is running on port 8000
2. **CORS Issues**: Check FRONTEND_URL in backend .env
3. **Import Errors**: Install requirements.txt dependencies
4. **Docker Issues**: Check docker-compose.yml configuration

## Development Workflow
1. Create feature branch from main
2. Develop in appropriate directory (backend/ or nextjs-frontend/)
3. Follow code quality standards (Black, ESLint, TypeScript)
4. Write tests for new functionality
5. Update documentation as needed
6. Submit pull request with proper description

## Testing Strategy
- **Backend**: pytest with async support, 80%+ coverage
- **Frontend**: Component testing with mock data
- **Integration**: API endpoint testing with httpx
- **Performance**: Locust load testing
- **Security**: bandit and safety scanning

## Deployment Options
- **Development**: Local with hot reload
- **Docker**: docker-compose for full stack
- **Production**: Enhanced Docker with monitoring stack
- **CI/CD**: GitHub Actions with automated testing