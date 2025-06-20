# Contributing to Audiobook Server

Thank you for your interest in contributing to the Audiobook Server project! This document provides guidelines and setup instructions for developers.

## 🛠️ Development Setup

### Prerequisites

- **Docker & Docker Compose**: Latest stable versions
- **NVIDIA GPU**: RTX 3090 or equivalent with CUDA support
- **NVIDIA Container Toolkit**: For GPU acceleration
- **Git**: Latest version
- **Python 3.10+**: For local development
- **Node.js 18+**: For PWA client development

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd audiobook-server
   ```

2. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your development settings
   ```

3. **Install pre-commit hooks**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **Start development environment**:
   ```bash
   docker compose up -d
   ```

### Service Development

Each service can be developed independently:

#### Python Services (API, Storage, Ingest, Segmenter, TTS Worker, Transcoder)

1. **Navigate to service directory**:
   ```bash
   cd services/api  # or other service
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # if available
   ```

4. **Run tests**:
   ```bash
   pytest
   pytest --cov=. --cov-report=html  # with coverage
   ```

5. **Run service locally**:
   ```bash
   python main.py  # or appropriate entry point
   ```

#### PWA Client

1. **Navigate to client directory**:
   ```bash
   cd pwa-client
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Run tests**:
   ```bash
   npm test
   npm run build  # test build process
   ```

## 📝 Coding Standards

### Python

- **Style**: Follow [PEP 8](https://pep8.org/) with Black formatting
- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Use Google-style docstrings for all public functions
- **Imports**: Organize imports with isort
- **Testing**: Use pytest with comprehensive test coverage

#### Example Python Code

```python
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


def process_text_chunk(text: str, chunk_size: int = 800) -> List[str]:
    """Split text into chunks of specified size.
    
    Args:
        text: Input text to be chunked
        chunk_size: Maximum size of each chunk in characters
        
    Returns:
        List of text chunks
        
    Raises:
        ValueError: If chunk_size is less than 1
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    
    logger.info(f"Split text into {len(chunks)} chunks")
    return chunks
```

### JavaScript/TypeScript

- **Style**: Use Prettier for formatting
- **Linting**: ESLint with TypeScript rules
- **Type Safety**: Use TypeScript for all new code
- **Testing**: Jest with React Testing Library

#### Example TypeScript Code

```typescript
interface BookUploadResponse {
  bookId: string;
  status: 'processing' | 'completed' | 'failed';
  message?: string;
}

export const uploadBook = async (
  file: File,
  title: string
): Promise<BookUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);

  const response = await fetch('/api/v1/books', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.REACT_APP_API_KEY}`,
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  return response.json();
};
```

## 🧪 Testing Guidelines

### Python Testing

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test service interactions
- **Fixtures**: Use pytest fixtures for test data
- **Mocking**: Mock external dependencies (Redis, file system)

#### Example Test

```python
import pytest
from unittest.mock import Mock, patch
from services.api.models import Book


@pytest.fixture
def sample_book():
    return Book(
        id="test-123",
        title="Test Book",
        format="pdf",
        status="processing"
    )


def test_book_creation(sample_book):
    assert sample_book.id == "test-123"
    assert sample_book.title == "Test Book"
    assert sample_book.status == "processing"


@patch('services.api.storage.redis_client')
def test_book_status_update(mock_redis, sample_book):
    mock_redis.set.return_value = True
    
    sample_book.update_status("completed")
    
    assert sample_book.status == "completed"
    mock_redis.set.assert_called_once()
```

### Frontend Testing

- **Component Tests**: Test React components in isolation
- **Integration Tests**: Test user workflows
- **API Mocking**: Mock API calls in tests

#### Example Test

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { uploadBook } from '../api';

jest.mock('../api');

describe('BookUpload', () => {
  it('should upload file and show progress', async () => {
    const mockUpload = uploadBook as jest.MockedFunction<typeof uploadBook>;
    mockUpload.mockResolvedValue({
      bookId: 'test-123',
      status: 'processing',
    });

    render(<BookUpload />);
    
    const fileInput = screen.getByLabelText(/choose file/i);
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    expect(await screen.findByText(/uploading/i)).toBeInTheDocument();
  });
});
```

## 🔄 Git Workflow

### Branch Naming

- `feature/description`: New features
- `fix/description`: Bug fixes
- `refactor/description`: Code refactoring
- `docs/description`: Documentation updates

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
- `feat(api): add book upload endpoint`
- `fix(storage): resolve SQLite connection leak`
- `docs(readme): update installation instructions`

### Pull Request Process

1. **Create feature branch** from `main`
2. **Make changes** with tests
3. **Run full test suite**:
   ```bash
   docker compose exec api pytest
   docker compose exec storage pytest
   cd pwa-client && npm test
   ```
4. **Update documentation** if needed
5. **Create pull request** with clear description
6. **Request review** from maintainers

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment**: OS, Docker version, GPU model
- **Steps to reproduce**: Clear, numbered steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Logs**: Relevant error messages and stack traces
- **Screenshots**: If applicable

## 💡 Feature Requests

When requesting features:

- **Describe the problem** you're trying to solve
- **Propose a solution** with implementation details
- **Consider alternatives** and trade-offs
- **Provide examples** of similar features in other projects

## 📊 Performance Considerations

### Backend

- **Database queries**: Use indexes and optimize queries
- **Memory usage**: Monitor memory consumption in long-running services
- **GPU utilization**: Profile TTS worker performance
- **File I/O**: Use async operations where possible

### Frontend

- **Bundle size**: Keep dependencies minimal
- **Caching**: Implement proper caching strategies
- **Lazy loading**: Load components and routes on demand
- **Audio streaming**: Optimize for low-latency playback

## 🔒 Security Guidelines

- **Input validation**: Validate all user inputs
- **Authentication**: Use secure API key management
- **File uploads**: Validate file types and sizes
- **Dependencies**: Keep dependencies updated
- **Secrets**: Never commit secrets to version control

## 📚 Documentation

- **Code comments**: Explain complex logic
- **API documentation**: Keep OpenAPI specs updated
- **README updates**: Update when adding new features
- **Architecture docs**: Document design decisions

## 🎯 Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions
- **Code review**: Request reviews for complex changes
- **Pair programming**: Reach out for collaboration

Thank you for contributing to Audiobook Server! 🎉 