# DBCSRC Enhanced Backend API

A production-ready, enterprise-grade FastAPI backend for the DBCSRC (Database Case Source) system, featuring advanced security, monitoring, performance optimization, and comprehensive AI-powered analysis capabilities.

## 🚀 Enhanced Features

### Core Functionality
- **Case Management**: Complete CRUD operations for legal cases with advanced validation
- **Document Processing**: Support for multiple file formats (PDF, DOCX, XLSX) with async processing
- **AI-Powered Analysis**: Text classification, entity extraction, and content analysis
- **Batch Processing**: Efficient handling of multiple documents and cases with background tasks
- **Data Export**: Flexible export options for processed data

### 🔒 Security Enhancements
- **Input Sanitization**: XSS protection and malicious input filtering
- **Rate Limiting**: Configurable request rate limiting per IP
- **Security Headers**: Comprehensive security headers implementation
- **Input Validation**: Advanced Pydantic validation with custom validators
- **Error Handling**: Secure error responses without information leakage

### 📊 Monitoring & Observability
- **Health Checks**: Basic and detailed health monitoring endpoints
- **Metrics Collection**: Request metrics, performance statistics, and system monitoring
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Performance Tracking**: Request timing and resource usage monitoring
- **Prometheus Integration**: Ready for Prometheus metrics scraping

### ⚡ Performance Optimizations
- **Async Operations**: Full async/await implementation
- **Connection Pooling**: Database connection pooling for better performance
- **Caching**: Redis-based caching for frequently accessed data
- **Background Tasks**: Celery integration for heavy processing
- **Resource Monitoring**: Real-time system resource tracking

### 🛠 DevOps & Deployment
- **Docker Support**: Multi-stage Docker builds for production
- **CI/CD Pipeline**: GitHub Actions workflow with comprehensive testing
- **Container Orchestration**: Docker Compose with monitoring stack
- **Load Testing**: Locust-based performance testing suite
- **Security Scanning**: Automated vulnerability scanning

## Quick Start

### Prerequisites
- Python 3.8+
- MongoDB (optional, for database features)
- OpenAI API key (for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dbcsrc/backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Setup

```bash
# Build the image
docker build -t dbcsrc-backend .

# Run the container
docker run -p 8000:8000 --env-file .env dbcsrc-backend
```

## API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

### API Response Format

All endpoints return a standardized response format:

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {},
  "count": 0,
  "error": null
}
```

### Core Endpoints

#### Case Management
- `GET /` - Health check and API information
- `GET /summary` - Get case summary statistics
- `POST /search` - Search cases with filters
- `POST /update` - Update cases for specific organization
- `POST /refresh-data` - Refresh case data from database

#### AI Analysis (Enhanced with Security)
- `POST /classify` - Classify single text with input sanitization
- `POST /batch-classify` - Batch classify multiple texts
- `POST /amount-analysis` - Extract penalty amounts
- `POST /location-analysis` - Analyze locations
- `POST /people-analysis` - Analyze people/entities

#### Document Processing
- `POST /convert-documents` - Convert documents to text
- `POST /analyze-attachments` - Analyze case attachments
- `POST /download-attachments` - Download case attachments

#### Monitoring & Health Checks
- `GET /health` - Basic health check with uptime
- `GET /health/detailed` - Comprehensive health status (database, external APIs, resources)
- `GET /metrics` - Application metrics and performance statistics

#### Security Features
- **Rate Limiting**: Automatic IP-based rate limiting (configurable)
- **Input Sanitization**: XSS protection and malicious content filtering
- **Security Headers**: CORS, CSP, and other security headers
- **Request Validation**: Enhanced Pydantic validation with custom sanitizers

## Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Application
APP_NAME=DBCSRC Enhanced Backend API
DEBUG=false
ENVIRONMENT=production

# Server
HOST=localhost
PORT=8000
FRONTEND_URL=http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
MONGODB_URL=mongodb://localhost:27017/dbcsrc
MONGODB_MAX_CONNECTIONS=100
MONGODB_MIN_CONNECTIONS=10

# Redis (for caching and rate limiting)
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=20

# OpenAI
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1000

# Security
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# Monitoring
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
PERFORMACE_MONITORING=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/app.log

# Background Tasks
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### Logging

The application uses structured logging with different levels:
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages with stack traces

Logs include:
- Request/response tracking
- Performance metrics
- Error details with context
- Database operations

## Development

### Code Quality

The project includes several code quality tools:

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

### Testing

```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Test specific endpoint
pytest tests/test_endpoints.py::test_summary_endpoint

# Run enhanced API tests
python test_enhanced_api.py
```

### Performance Testing

Use Locust for load testing:

```bash
# Install Locust
pip install locust

# Run performance tests
locust -f performance_tests.py --host=http://localhost:8000

# Run headless performance test
locust -f performance_tests.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 60s --headless
```

### Adding New Endpoints

1. **Define Pydantic models** for request/response validation
2. **Add endpoint function** with proper typing and documentation
3. **Use APIResponse model** for consistent responses
4. **Add logging** for operations and errors
5. **Include input validation** and error handling

Example:

```python
@app.post("/new-endpoint", response_model=APIResponse)
async def new_endpoint(request: NewRequest):
    """Description of the endpoint"""
    try:
        logger.info(f"Starting operation: {request.param}")
        
        # Your logic here
        result = process_data(request.data)
        
        logger.info("Operation completed successfully")
        return APIResponse(
            success=True,
            message="Operation completed",
            data={"result": result}
        )
        
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Operation failed",
            error=str(e)
        )
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use production values in `.env`
2. **Database**: Configure production MongoDB instance with connection pooling
3. **Redis**: Set up Redis for caching and rate limiting
4. **Logging**: Configure structured logging with appropriate levels
5. **Security**: Enable rate limiting, input sanitization, and security headers
6. **Monitoring**: Set up comprehensive monitoring and alerting
7. **Performance**: Configure async operations and background tasks

### Enhanced Docker Deployment

#### Single Container
```bash
# Build enhanced image
docker build -f Dockerfile.enhanced -t dbcsrc-backend-enhanced .

# Run with environment file
docker run -d -p 8000:8000 --env-file .env --name dbcsrc-api dbcsrc-backend-enhanced
```

#### Full Stack with Monitoring
```bash
# Deploy complete stack with monitoring
docker-compose -f docker-compose.enhanced.yml up -d

# View logs
docker-compose -f docker-compose.enhanced.yml logs -f dbcsrc-api

# Scale the API
docker-compose -f docker-compose.enhanced.yml up -d --scale dbcsrc-api=3
```

### Monitoring Stack

The enhanced deployment includes:

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Redis**: Caching and session storage
- **Nginx**: Load balancing and reverse proxy
- **ELK Stack**: Centralized logging (optional)

#### Access Monitoring Services
- **API**: http://localhost:8000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **Redis Commander**: http://localhost:8081

### CI/CD Pipeline

The project includes a comprehensive GitHub Actions workflow:

```yaml
# Triggers on:
- Push to main/develop branches
- Pull requests
- Release tags

# Pipeline stages:
1. Code Quality & Security
2. Backend Testing
3. Frontend Testing (if applicable)
4. Docker Build & Security Scan
5. Performance Testing
6. Deployment (staging/production)
```

### Health Checks

Comprehensive health monitoring:
- `GET /health` - Basic health check with uptime
- `GET /health/detailed` - Database, external APIs, and system resources
- `GET /metrics` - Prometheus-compatible metrics

#### Health Check Response
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime": 3600,
  "version": "1.0.0",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "external_apis": "healthy",
    "disk_space": "healthy",
    "memory_usage": "healthy"
  }
}
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed from `requirements.txt`
2. **Database Connection**: Check MongoDB URL and connectivity
3. **Redis Connection**: Verify Redis is running and accessible
4. **API Key Issues**: Verify OpenAI API key configuration
5. **CORS Errors**: Check FRONTEND_URL and ALLOWED_ORIGINS configuration
6. **Rate Limiting**: Check if requests are being rate limited
7. **File Upload Issues**: Verify file size limits and permissions
8. **Memory Issues**: Monitor system resources via `/health/detailed`
9. **Performance Issues**: Check metrics at `/metrics` endpoint

### Debug Mode

Enable debug mode for detailed error information:

```env
DEBUG=true
LOG_LEVEL=DEBUG
PERFORMANCE_MONITORING=true
METRICS_ENABLED=true
```

### Monitoring and Diagnostics

#### Check Application Health
```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health status
curl http://localhost:8000/health/detailed

# Application metrics
curl http://localhost:8000/metrics
```

#### View Logs
```bash
# Docker logs
docker logs dbcsrc-api

# Docker Compose logs
docker-compose -f docker-compose.enhanced.yml logs -f

# Application logs (if file logging enabled)
tail -f logs/app.log
```

#### Performance Analysis
```bash
# Run performance tests
locust -f performance_tests.py --host=http://localhost:8000 --headless --users 10 --spawn-rate 2 --run-time 30s

# Monitor system resources
htop
# or
docker stats
```

## Enhanced Files and Tools

The enhanced version includes several new files and tools:

### New Configuration Files
- `Dockerfile.enhanced` - Multi-stage Docker build for production
- `docker-compose.enhanced.yml` - Complete stack with monitoring
- `.github/workflows/ci-cd.yml` - Comprehensive CI/CD pipeline
- `monitoring/prometheus.yml` - Prometheus configuration
- `monitoring/alert_rules.yml` - Alerting rules for monitoring

### Testing and Performance
- `test_enhanced_api.py` - Comprehensive API test suite
- `performance_tests.py` - Locust-based load testing

### Enhanced Dependencies
The `requirements.txt` now includes:
- **Security**: `bleach`, `bandit`, `safety`
- **Monitoring**: `prometheus-client`, `psutil`
- **Performance**: `motor`, `aioredis`, `celery`
- **Testing**: `locust`, `pytest-cov`, `mypy`
- **Documentation**: `mkdocs`

## Contributing

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Set up development environment**
   ```bash
   pip install -r requirements.txt
   pre-commit install  # If using pre-commit hooks
   ```
4. **Make your changes**
5. **Run quality checks**
   ```bash
   black .
   isort .
   flake8 .
   mypy .
   bandit -r .
   ```
6. **Add tests for new functionality**
   ```bash
   pytest --cov=. --cov-report=html
   ```
7. **Test performance impact**
   ```bash
   locust -f performance_tests.py --host=http://localhost:8000 --headless --users 10 --spawn-rate 2 --run-time 30s
   ```
8. **Ensure all checks pass**
9. **Submit a pull request**

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Add docstrings for public methods
- Include error handling and logging
- Write comprehensive tests
- Update documentation for new features

## License

[Add your license information here]

## Support

For issues and questions:
- **API Documentation**: http://localhost:8000/docs
- **Health Status**: http://localhost:8000/health/detailed
- **Metrics**: http://localhost:8000/metrics
- **Logs**: Check application logs for error details
- **Issues**: Create an issue in the repository
- **Performance**: Use the performance testing suite
- **Monitoring**: Check Prometheus/Grafana dashboards