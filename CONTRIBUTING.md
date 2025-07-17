# Contributing to Upbit Trading Bot

Thank you for your interest in contributing to the Upbit Trading Bot! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

- Use the GitHub issue tracker
- Include a clear and descriptive title
- Provide detailed steps to reproduce the bug
- Include system information (OS, Python version, etc.)
- Include error messages and logs

### Suggesting Enhancements

- Use the GitHub issue tracker with the "enhancement label
- Describe the feature and why it would be useful
- Include mockups or examples if applicable

### Pull Requests

- Fork the repository
- Create a feature branch
- Make your changes
- Add tests for new functionality
- Update documentation
- Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/upbit-trading-bot.git
cd upbit-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # If available

# Set up pre-commit hooks
pre-commit install
```

### Environment Variables

Copy the example environment file and configure it:

```bash
cp env.example .env
# Edit .env with your configuration
```

## Pull Request Process

1. **Fork and Clone**: Fork the repository and clone your fork
2**Create Branch**: Create a feature branch from `main`3 **Make Changes**: Implement your changes
4. **Test**: Run tests and ensure they pass
5. **Document**: Update documentation if needed
6: Use conventional commit messages7 **Push**: Push to your fork8ubmit PR**: Create a pull request

### Commit Message Format

Use conventional commit messages:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- Bug fix
- ] New feature
- [ ] Breaking change
-cumentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
-  testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
-umentation updated
- [ ] No breaking changes (or documented)
```

## Coding Standards

### Python Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Keep functions small and focused
- Use descriptive variable names
- Add docstrings for public functions

### Code Quality

- Use a linter (flake8lint)
- Use a formatter (black, isort)
- Keep cyclomatic complexity low
- Write self-documenting code

### Example

```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def calculate_kimchi_premium(
    usdt_krw_price: float,
    usd_krw_rate: float
) -> float:
   
    Calculate the Kimchi Premium.
    
    Args:
        usdt_krw_price: USDT/KRW price from Upbit
        usd_krw_rate: USD/KRW exchange rate
        
    Returns:
        Kimchi premium percentage
       if usd_krw_rate <= 0:
        raise ValueError(USD/KRW rate must be positive")
    
    premium = ((usdt_krw_price - usd_krw_rate) / usd_krw_rate) * 100    logger.debug(fCalculated kimchi premium: {premium:.2f}%)    return premium
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=upbit_bot

# Run specific test file
pytest tests/test_trading_bot.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Write tests for new functionality
- Aim for high test coverage
- Use descriptive test names
- Mock external dependencies
- Test edge cases and error conditions

### Example Test

```python
import pytest
from upbit_bot.trading_bot import calculate_kimchi_premium


def test_calculate_kimchi_premium_positive():
est kimchi premium calculation with positive premium."""
    result = calculate_kimchi_premium(13501300
    assert result == pytest.approx(3.85l=0.01def test_calculate_kimchi_premium_negative():
est kimchi premium calculation with negative premium."""
    result = calculate_kimchi_premium(12501300
    assert result == pytest.approx(-3.85l=0.01def test_calculate_kimchi_premium_invalid_rate():
est kimchi premium calculation with invalid rate."    with pytest.raises(ValueError, match="must be positive"):
        calculate_kimchi_premium(130

## Documentation

### Code Documentation

- Add docstrings to all public functions
- Use Google or NumPy docstring format
- Include type hints
- Document exceptions and edge cases

### User Documentation

- Update README.md for user-facing changes
- Add examples and use cases
- Keep installation instructions current
- Document configuration options

### API Documentation

- Document all API endpoints
- Include request/response examples
- Document error codes and messages
- Keep OpenAPI/Swagger docs updated

## Getting Help

- Check existing issues and pull requests
- Join our community discussions
- Ask questions in GitHub Discussions
- Contact maintainers directly

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes
- Project documentation
- Community acknowledgments

Thank you for contributing to the Upbit Trading Bot! 