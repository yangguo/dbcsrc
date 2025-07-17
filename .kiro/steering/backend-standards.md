# Backend Development Standards

## Code Structure and Organization
- Follow FastAPI best practices with proper dependency injection
- Use Pydantic models for request/response validation
- Implement async/await patterns for all I/O operations
- Organize code into logical modules (main.py, utils.py, data_service.py, etc.)

## API Design Standards
- Use standardized APIResponse model for all endpoints
- Include proper HTTP status codes and error handling
- Implement comprehensive input validation and sanitization
- Add detailed docstrings and OpenAPI documentation
- Follow RESTful conventions for endpoint naming

## Security Requirements
- Implement rate limiting using slowapi
- Sanitize all user inputs with bleach
- Use proper CORS configuration
- Include security headers in responses
- Validate file uploads with size and type restrictions
- Never expose sensitive information in error messages

## Database and Caching
- Use Motor for async MongoDB operations
- Implement connection pooling for better performance
- Use Redis for caching frequently accessed data
- Include proper error handling for database operations
- Use indexes for query optimization

## AI/ML Integration
- Use OpenAI API with proper error handling and retries
- Implement batch processing for multiple documents
- Include input validation for AI model requests
- Handle API rate limits and quota management
- Support both OpenAI and OpenAI-compatible APIs

## Monitoring and Logging
- Use structured logging with correlation IDs
- Implement health check endpoints (/health, /health/detailed)
- Include Prometheus metrics collection
- Monitor system resources (CPU, memory, disk)
- Log all API requests and responses for debugging

## Testing Standards
- Write unit tests for all business logic
- Include integration tests for API endpoints
- Use pytest with async support
- Implement performance testing with Locust
- Maintain test coverage above 80%

## Environment Configuration
- Use .env files for configuration management
- Include .env.example with all required variables
- Support multiple environments (dev, staging, production)
- Validate required environment variables on startup