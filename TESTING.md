# Testing Guide for Audiobook Server API

## Overview

This document describes the testing strategy and how to run tests for the Audiobook Server API. The test suite covers unit tests, integration tests, and API validation.

## Test Structure

```
tests/
├── __init__.py              # Test package
├── test_api.py             # Comprehensive API tests
├── requirements.txt        # Test dependencies
└── run_tests.py           # Test runner script

test_api_quick.py          # Quick API validation script
```

## Test Categories

### 1. Unit Tests (`tests/test_api.py`)
- **Database operations**: CRUD operations, data validation
- **Data models**: Pydantic model validation, enum testing
- **Authentication**: API key validation, error responses
- **File handling**: Upload validation, format checking

### 2. Integration Tests (`tests/test_api.py::TestIntegration`)
- **Complete workflows**: End-to-end book processing
- **Service communication**: API-to-database interactions
- **Error propagation**: Error handling across services

### 3. API Documentation Tests
- **OpenAPI docs**: Swagger UI accessibility
- **Health checks**: Service status validation
- **Endpoint validation**: All endpoints respond correctly

### 4. Curl-based Tests
- **Real HTTP requests**: Actual API calls
- **Authentication flows**: Bearer token validation
- **File uploads**: Multipart form data handling

## Running Tests

### Prerequisites

1. **Install test dependencies**:
   ```bash
   pip install -r tests/requirements.txt
   ```

2. **Start the API service** (for integration tests):
   ```bash
   docker-compose up -d api
   ```

### Quick Test (Recommended for Development)

Run a quick validation of the API:

```bash
python test_api_quick.py
```

This script:
- Tests health endpoint
- Validates authentication
- Submits a test book
- Checks status and chunks endpoints
- Tests error handling

**Expected Output**:
```
🚀 Audiobook Server API Quick Test
========================================
🔍 Testing health endpoint...
✅ Health: healthy
   Redis: healthy
   Database: healthy

🔐 Testing authentication...
✅ Invalid auth correctly rejected
✅ Valid auth accepted

📚 Testing book submission...
✅ Book submitted: 550e8400-e29b-41d4-a716-446655440000

📊 Testing book status for 550e8400-e29b-41d4-a716-446655440000...
✅ Status: pending (0.0%)

🎵 Testing chunks listing for 550e8400-e29b-41d4-a716-446655440000...
✅ Chunks: 0 chunks, 0.0s total

⚠️  Testing error handling...
✅ 404 correctly returned for non-existent book
✅ 400 correctly returned for invalid format

========================================
📊 TEST SUMMARY
========================================
Health Check: ✅ PASS
Authentication: ✅ PASS
Error Handling: ✅ PASS
Book Submission: ✅ PASS
Book Status: ✅ PASS
Chunks Listing: ✅ PASS

Overall: 6/6 tests passed
🎉 All tests passed!
```

### Full Test Suite

Run the complete test suite:

```bash
python tests/run_tests.py
```

This includes:
- Unit tests
- API documentation tests
- Curl-based tests
- Integration tests

### Individual Test Categories

#### Unit Tests Only
```bash
pytest tests/test_api.py::TestAudiobookAPI -v
```

#### Database Tests Only
```bash
pytest tests/test_api.py::TestDatabaseManager -v
```

#### Data Model Tests Only
```bash
pytest tests/test_api.py::TestDataModels -v
```

#### Integration Tests Only
```bash
pytest tests/test_api.py::TestIntegration -v
```

## Test Coverage

### API Endpoints Tested

| Endpoint | Method | Test Coverage |
|----------|--------|---------------|
| `/health` | GET | ✅ Health status, dependencies |
| `/` | GET | ✅ API information |
| `/docs` | GET | ✅ OpenAPI documentation |
| `/api/v1/books` | GET | ✅ List books, auth validation |
| `/api/v1/books` | POST | ✅ Book submission, validation |
| `/api/v1/books/{id}/status` | GET | ✅ Status checking, progress |
| `/api/v1/books/{id}/chunks` | GET | ✅ Chunks listing |
| `/api/v1/books/{id}/chunks/{seq}` | GET | ✅ Audio streaming |
| `/api/v1/books/{id}` | DELETE | ✅ Book deletion |

### Authentication Tests

- ✅ Valid API key acceptance
- ✅ Invalid API key rejection
- ✅ Missing API key handling
- ✅ Bearer token format validation

### Validation Tests

- ✅ File format validation (PDF, EPUB, TXT)
- ✅ File extension matching
- ✅ File size limits (50MB max)
- ✅ Title length validation (1-255 chars)
- ✅ Required field validation

### Error Handling Tests

- ✅ 400 Bad Request for invalid input
- ✅ 401 Unauthorized for invalid auth
- ✅ 404 Not Found for missing resources
- ✅ 413 Request Entity Too Large for big files
- ✅ 500 Internal Server Error handling

### Database Tests

- ✅ Book creation and retrieval
- ✅ Status updates and progress tracking
- ✅ Chunk metadata management
- ✅ Book deletion with cascading
- ✅ Data integrity and constraints

## Test Data

### Sample Files Generated

**TXT Files**:
```python
"This is a test audiobook content for API testing.\n" * 10
```

**PDF Files**:
- Minimal PDF structure for testing
- Valid PDF format with test content

### Test Database

- **Location**: `/tmp/test_audiobooks.db` (temporary)
- **Cleanup**: Automatic cleanup after tests
- **Isolation**: Separate from production database

## Continuous Integration

### GitHub Actions (Recommended)

Create `.github/workflows/test.yml`:

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r tests/requirements.txt
    
    - name: Start API service
      run: |
        docker-compose up -d api
        sleep 10  # Wait for service to start
    
    - name: Run tests
      run: |
        python test_api_quick.py
        python tests/run_tests.py
```

### Local Development Workflow

1. **Make changes** to API code
2. **Run quick test**: `python test_api_quick.py`
3. **If quick test passes**, run full suite: `python tests/run_tests.py`
4. **Fix any failures** and repeat
5. **Commit changes** when all tests pass

## Troubleshooting

### Common Issues

#### API Not Running
```
❌ Cannot connect to API: Connection refused
```
**Solution**: Start the API service
```bash
docker-compose up -d api
```

#### Redis Connection Failed
```
❌ Health: unhealthy
   Redis: unhealthy: Connection refused
```
**Solution**: Start Redis service
```bash
docker-compose up -d redis
```

#### Database Permission Issues
```
❌ Database: unhealthy: Permission denied
```
**Solution**: Check Docker volume permissions
```bash
sudo chown -R $USER:$USER ./data/
```

#### Test Dependencies Missing
```
ModuleNotFoundError: No module named 'pytest'
```
**Solution**: Install test dependencies
```bash
pip install -r tests/requirements.txt
```

### Debug Mode

Enable debug output:

```bash
# Set debug environment variable
export DEBUG=true

# Run tests with verbose output
pytest tests/test_api.py -v -s
```

### Test Logs

View test execution logs:

```bash
# Run tests with logging
pytest tests/test_api.py --log-cli-level=DEBUG

# View API service logs during tests
docker-compose logs -f api
```

## Performance Testing

### Load Testing (Optional)

For performance validation, create `tests/load_test.py`:

```python
import asyncio
import aiohttp
import time

async def load_test():
    """Simple load test for the API."""
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # Make 100 concurrent requests
        tasks = []
        for i in range(100):
            task = session.get("http://localhost:8000/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        successful = sum(1 for r in responses if r.status == 200)
        print(f"Load test: {successful}/100 successful in {duration:.2f}s")
```

Run with:
```bash
python tests/load_test.py
```

## Best Practices

### Writing Tests

1. **Test one thing at a time**: Each test should validate a single behavior
2. **Use descriptive names**: Test names should explain what they validate
3. **Clean up after tests**: Remove temporary files and database entries
4. **Mock external dependencies**: Use mocks for Redis, file system, etc.
5. **Test both success and failure cases**: Validate error handling

### Test Organization

1. **Group related tests**: Use test classes for related functionality
2. **Use fixtures**: Share setup code between tests
3. **Keep tests independent**: Tests should not depend on each other
4. **Use appropriate assertions**: Choose the right assertion for the test

### Continuous Testing

1. **Run tests frequently**: Test after each significant change
2. **Automate testing**: Use CI/CD pipelines
3. **Monitor test results**: Track test success rates over time
4. **Update tests with code**: Keep tests in sync with API changes

## Contributing

When adding new features:

1. **Write tests first**: Follow TDD principles
2. **Update test documentation**: Document new test cases
3. **Ensure backward compatibility**: Don't break existing tests
4. **Add integration tests**: Test the complete workflow
5. **Update this guide**: Keep testing documentation current 