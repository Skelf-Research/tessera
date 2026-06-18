# Contributing to Tessera

Thank you for your interest in contributing to Tessera! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Security](#security)

## Code of Conduct

This project follows a standard code of conduct. Be respectful, professional, and constructive in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a feature branch for your changes

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Poetry for dependency management
- Git

### Setup Commands

```bash
# Clone your fork
git clone https://github.com/yourusername/tessera.git
cd tessera

# Run the setup script
./scripts/setup_dev.sh

# Or manually:
poetry install
poetry run pytest tests/
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-encryption`
- `fix/key-rotation-bug`
- `docs/update-api-reference`

### Code Style

- Follow PEP 8 for Python code style
- Use type hints where appropriate
- Write clear, self-documenting code
- Add docstrings for all public functions and classes

### Commit Messages

Write clear commit messages:
```
feat: add AES-GCM encryption support

- Replace XOR encryption with proper AEAD
- Add comprehensive input validation
- Update tests for new encryption method
```

Use conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `test:` for test changes
- `refactor:` for code refactoring

## Testing

### Running Tests

```bash
# Run all tests
./scripts/run_tests.sh

# Run specific test file
poetry run pytest tests/test_crypto.py -v

# Run with coverage
poetry run pytest tests/ --cov=tessera
```

### Writing Tests

- Write tests for all new functionality
- Ensure edge cases are covered
- Use descriptive test names
- Maintain >90% test coverage

### Test Categories

- Unit tests for individual components
- Integration tests for component interactions
- Security tests for cryptographic functions
- Performance tests for critical paths

## Submitting Changes

### Pull Request Process

1. Ensure all tests pass locally
2. Update documentation as needed
3. Add entries to CHANGELOG.md
4. Create a pull request with:
   - Clear title and description
   - Reference to related issues
   - List of changes made
   - Testing performed

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Security

### Security Issues

**DO NOT** open public issues for security vulnerabilities. Instead:

1. Email security issues to: security@dipankar.name
2. Include "Tessera Security" in the subject line
3. Provide detailed information about the vulnerability
4. Allow reasonable time for response before disclosure

### Security Guidelines

- Never commit secrets, keys, or passwords
- Use secure coding practices
- Validate all inputs
- Follow cryptographic best practices
- Review code for timing attacks

## Development Guidelines

### Architecture

- Follow the existing module structure
- Keep components loosely coupled
- Use dependency injection where appropriate
- Document architectural decisions

### Performance

- Profile critical paths
- Optimize for common use cases
- Maintain sub-millisecond proof operations
- Consider memory usage in long-running services

### Documentation

- Update API documentation for changes
- Include examples for new features
- Write clear error messages
- Document security considerations

## Getting Help

- Check existing issues and documentation
- Join discussions in GitHub Discussions
- Ask questions in pull request comments
- Contact maintainers for guidance

## Recognition

Contributors will be acknowledged in:
- CHANGELOG.md for their contributions
- Release notes
- Project documentation

Thank you for contributing to Tessera!