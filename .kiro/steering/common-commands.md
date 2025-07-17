# Common Development Commands

## Backend Development Commands

### Environment Setup
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
copy .env.example .env

# Start development server
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Commands
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest test_web_crawler.py

# Run performance tests
python performance_tests.py

# Run consolidated test suite
python consolidated_test_suite.py
```

### Code Quality Commands
```bash
# Format code
black .
isort .

# Lint code
flake8 .

# Type checking
mypy .

# Security scanning
bandit -r .
safety check
```

## Frontend Development Commands

### Next.js Frontend Setup
```bash
# Navigate to frontend directory
cd nextjs-frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Legacy Streamlit Frontend
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pip install -r requirements.txt

# Start Streamlit app
streamlit run app.py
```

## Docker Commands

### Development with Docker
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild specific service
docker-compose build backend
docker-compose up -d backend
```

### Enhanced Docker Stack
```bash
# Start enhanced stack with monitoring
docker-compose -f docker-compose.enhanced.yml up -d

# Scale API service
docker-compose -f docker-compose.enhanced.yml up -d --scale dbcsrc-api=3

# View service status
docker-compose -f docker-compose.enhanced.yml ps
```

## Database and Monitoring

### Health Checks
```bash
# Check API health
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# View metrics
curl http://localhost:8000/metrics
```

### MongoDB Operations
```bash
# Connect to MongoDB (if running locally)
mongo mongodb://localhost:27017/dbcsrc

# View collections
show collections

# Query cases
db.cases.find().limit(5)
```

## Troubleshooting Commands

### Check Service Status
```bash
# Check if backend is running
curl http://localhost:8000/

# Check if frontend is accessible
curl http://localhost:3000/

# View Docker container status
docker ps

# Check container logs
docker logs [container_name]
```

### Performance Monitoring
```bash
# Monitor system resources
htop

# Check disk usage
df -h

# Monitor network connections
netstat -tulpn | grep :8000
```