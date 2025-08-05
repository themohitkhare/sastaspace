# Backend Test Suite Documentation

## Overview

This document provides comprehensive documentation for the backend test suite of the SastaSpace application. The test suite is designed to ensure code quality, reliability, and maintainability across all backend components.

## Test Structure

### Test Categories

The test suite is organized into the following categories:

1. **Unit Tests** (`@pytest.mark.unit`)
   - Test individual components in isolation
   - Fast execution
   - No external dependencies

2. **Integration Tests** (`@pytest.mark.integration`)
   - Test component interactions
   - Database operations
   - API endpoints

3. **API Tests** (`@pytest.mark.api`)
   - Test REST API endpoints
   - Authentication and authorization
   - Request/response validation

4. **Model Tests** (`@pytest.mark.model`)
   - Test Django models
   - Database constraints
   - Model methods and properties

5. **View Tests** (`@pytest.mark.view`)
   - Test Django views
   - Business logic
   - Error handling

6. **AI Service Tests** (`@pytest.mark.ai`)
   - Test AI integration
   - Mock external services
   - Response validation

7. **Performance Tests** (`@pytest.mark.performance`)
   - Test performance characteristics
   - Load testing
   - Benchmarking

8. **Slow Tests** (`@pytest.mark.slow`)
   - Tests that take longer to execute
   - External service calls
   - Complex operations

## Apps and Test Coverage

### 1. Users App (`apps/users/`)

**Test Files:**
- `tests.py` - Main test suite
- `test_edge_cases.py` - Edge cases and error scenarios
- `factories.py` - Test data factories

**Coverage:**
- User model creation and validation
- User authentication and authorization
- User serialization
- API endpoints
- Edge cases (special characters, long inputs, etc.)
- Performance testing
- Error handling

**Key Test Classes:**
- `CustomUserModelTest` - Model functionality
- `CustomUserSerializerTest` - Serialization
- `CustomUserViewTest` - API endpoints
- `CustomUserIntegrationTest` - End-to-end workflows
- `UserEdgeCaseTest` - Edge cases
- `UserErrorHandlingTest` - Error scenarios
- `UserPerformanceTest` - Performance characteristics

### 2. Profiles App (`apps/profiles/`)

**Test Files:**
- `tests.py` - Main test suite
- `factories.py` - Test data factories

**Coverage:**
- Profile model creation and validation
- LinkedIn URL parsing
- Resume file handling
- AI analysis integration
- Onboarding workflow
- Data validation

**Key Test Classes:**
- `ProfileModelTest` - Model functionality
- `ProfileSerializerTest` - Serialization
- `AIServiceTest` - AI integration
- `ProfileViewTest` - API endpoints
- `ProfileIntegrationTest` - End-to-end workflows

### 3. Portfolio App (`apps/portfolio/`)

**Test Files:**
- `tests.py` - Main test suite
- `factories.py` - Test data factories

**Coverage:**
- Portfolio model creation and validation
- JSON field handling
- Slug uniqueness
- Template selection
- Public and private access
- Data updates

**Key Test Classes:**
- `PortfolioModelTest` - Model functionality
- `PortfolioSerializerTest` - Serialization
- `PortfolioViewTest` - API endpoints
- `PortfolioIntegrationTest` - End-to-end workflows

## Test Data Factories

### User Factories (`apps/users/factories.py`)

- `UserFactory` - Creates standard users
- `SuperUserFactory` - Creates admin users
- `InactiveUserFactory` - Creates inactive users

### Profile Factories (`apps/profiles/factories.py`)

- `ProfileFactory` - Creates standard profiles
- `ProfileWithResumeFactory` - Creates profiles with resume files
- `ProfileWithAIAnalysisFactory` - Creates profiles with AI analysis

### Portfolio Factories (`apps/portfolio/factories.py`)

- `PortfolioFactory` - Creates standard portfolios
- `PortfolioWithMinimalDataFactory` - Creates minimal portfolios
- `PortfolioWithExtensiveDataFactory` - Creates detailed portfolios
- `PortfolioWithCustomTemplateFactory` - Creates custom template portfolios

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Set up environment variables:
```bash
export DJANGO_SETTINGS_MODULE=sastaspace_project.settings
export GEMINI_API_KEY=your_test_api_key
```

### Test Runner Script

Use the comprehensive test runner script:

```bash
# Run all tests with coverage
python run_tests.py --type all

# Run specific test types
python run_tests.py --type unit
python run_tests.py --type integration
python run_tests.py --type api
python run_tests.py --type model
python run_tests.py --type view
python run_tests.py --type ai
python run_tests.py --type performance
python run_tests.py --type slow

# Run tests in parallel
python run_tests.py --type parallel

# Run code quality checks
python run_tests.py --type quality

# Run security checks
python run_tests.py --type security
```

### Direct Pytest Commands

```bash
# Run all tests
pytest apps/

# Run specific app tests
pytest apps/users/
pytest apps/profiles/
pytest apps/portfolio/

# Run specific test categories
pytest -m unit apps/
pytest -m integration apps/
pytest -m api apps/
pytest -m model apps/
pytest -m view apps/
pytest -m ai apps/
pytest -m performance apps/
pytest -m slow apps/

# Run with coverage
pytest --cov=apps --cov-report=html apps/

# Run in parallel
pytest -n auto apps/

# Run specific test file
pytest apps/users/tests.py
pytest apps/users/test_edge_cases.py
```

## Test Configuration

### pytest.ini

The test configuration includes:
- Django settings module
- Test discovery patterns
- Coverage reporting
- Markers for test categorization
- Performance settings

### Coverage Configuration

Coverage reports are generated in multiple formats:
- Terminal output with missing lines
- HTML report in `htmlcov/` directory
- XML report for CI/CD integration

## Test Patterns and Best Practices

### 1. Test Organization

- **Arrange**: Set up test data and conditions
- **Act**: Execute the code being tested
- **Assert**: Verify the expected outcomes

### 2. Test Naming

- Use descriptive test method names
- Follow the pattern: `test_[what]_[condition]_[expected_result]`
- Include docstrings explaining test purpose

### 3. Test Data Management

- Use factories for consistent test data
- Clean up test data in `tearDown` methods
- Use unique identifiers to avoid conflicts

### 4. Mocking and Stubbing

- Mock external services (AI APIs, file storage)
- Use `unittest.mock` for complex interactions
- Stub database operations when appropriate

### 5. Error Testing

- Test both success and failure scenarios
- Verify error messages and status codes
- Test edge cases and boundary conditions

## Performance Testing

### Benchmarks

Performance tests measure:
- Database query performance
- API response times
- Memory usage
- CPU utilization

### Load Testing

Load tests verify:
- Concurrent request handling
- Database connection pooling
- Memory leaks
- Response time degradation

## Security Testing

### Code Analysis

Security tests include:
- Static code analysis with bandit
- Dependency vulnerability scanning
- Input validation testing
- Authentication bypass attempts

## Continuous Integration

### GitHub Actions

The test suite is integrated with CI/CD:
- Runs on every pull request
- Generates coverage reports
- Fails builds on test failures
- Provides detailed test results

### Pre-commit Hooks

Pre-commit hooks ensure:
- Code formatting (black)
- Import sorting (isort)
- Linting (flake8)
- Security checks (bandit)

## Test Maintenance

### Adding New Tests

1. Create test file in appropriate app directory
2. Use appropriate markers for categorization
3. Follow naming conventions
4. Include comprehensive docstrings
5. Add to test runner if needed

### Updating Tests

1. Update tests when functionality changes
2. Maintain backward compatibility
3. Update factories for new fields
4. Regenerate test data as needed

### Test Data Management

1. Use factories for consistent data
2. Clean up test data properly
3. Use unique identifiers
4. Avoid hardcoded values

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check MongoDB connection settings
   - Verify test database configuration
   - Ensure proper cleanup

2. **Import Errors**
   - Check Python path
   - Verify app configuration
   - Update import statements

3. **Test Failures**
   - Check test data setup
   - Verify mock configurations
   - Review error messages

4. **Performance Issues**
   - Optimize database queries
   - Use appropriate test markers
   - Consider parallel execution

### Debugging Tests

1. Use `pytest -s` for verbose output
2. Add `print()` statements for debugging
3. Use `pytest --pdb` for interactive debugging
4. Check coverage reports for untested code

## Metrics and Reporting

### Coverage Metrics

- Line coverage percentage
- Branch coverage analysis
- Missing line identification
- Coverage trends over time

### Performance Metrics

- Test execution time
- Memory usage patterns
- Database query counts
- API response times

### Quality Metrics

- Test pass/fail rates
- Code complexity scores
- Security vulnerability counts
- Technical debt indicators

## Future Enhancements

### Planned Improvements

1. **Property-based Testing**
   - Use Hypothesis for property-based tests
   - Generate test cases automatically
   - Improve edge case coverage

2. **Contract Testing**
   - Test API contracts
   - Verify data schemas
   - Ensure backward compatibility

3. **Visual Regression Testing**
   - Test UI components
   - Screenshot comparison
   - Layout verification

4. **Chaos Engineering**
   - Test system resilience
   - Failure injection
   - Recovery verification

### Monitoring and Alerting

1. **Test Metrics Dashboard**
   - Real-time test results
   - Performance trends
   - Coverage reports

2. **Automated Alerts**
   - Test failure notifications
   - Performance degradation alerts
   - Security vulnerability alerts

## Conclusion

This comprehensive test suite ensures the reliability, performance, and security of the SastaSpace backend. Regular test execution and maintenance are essential for maintaining code quality and preventing regressions.

For questions or contributions to the test suite, please refer to the project documentation or contact the development team. 