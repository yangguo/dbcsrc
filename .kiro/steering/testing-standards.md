# Testing Standards

## Backend Testing
- Use pytest for all Python testing
- Implement async test support with pytest-asyncio
- Write unit tests for all business logic functions
- Create integration tests for API endpoints
- Use httpx.AsyncClient for testing FastAPI endpoints
- Mock external dependencies (OpenAI API, MongoDB, Redis)

## Test Structure
- Organize tests in parallel structure to source code
- Use descriptive test names that explain the scenario
- Follow AAA pattern (Arrange, Act, Assert)
- Use fixtures for common test setup
- Include both positive and negative test cases

## Coverage Requirements
- Maintain minimum 80% test coverage
- Use pytest-cov for coverage reporting
- Generate HTML coverage reports for review
- Focus on critical business logic coverage
- Test error handling and edge cases

## Performance Testing
- Use Locust for load testing API endpoints
- Test with realistic data volumes
- Monitor response times and resource usage
- Test concurrent user scenarios
- Include stress testing for critical endpoints

## Frontend Testing
- Test React components with proper mock data
- Verify API integration with mock responses
- Test user interactions and form submissions
- Include accessibility testing
- Test responsive design across devices

## Test Data Management
- Use factories or fixtures for test data
- Avoid hardcoded test data in tests
- Clean up test data after each test
- Use separate test database/environment
- Include realistic data scenarios

## Continuous Integration
- Run all tests on every pull request
- Include linting and code quality checks
- Run security scans (bandit, safety)
- Generate and publish test reports
- Fail builds on test failures or coverage drops

## Test Documentation
- Document test scenarios and expected outcomes
- Include setup instructions for test environment
- Document known test limitations
- Provide troubleshooting guide for test failures