# Contributing to px-kitchen-blender

Thank you for your interest in contributing to px-kitchen-blender! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.10 or higher
- Blender 3.0 or higher
- Blender-MCP addon installed

### Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/px-kitchen-blender.git
   cd px-kitchen-blender
   ```

3. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Making Changes

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose

### Testing

Before submitting a PR, ensure all tests pass:

```bash
# Run mock tests
python3 test_mock.py

# Validate Python syntax
python3 -m py_compile kitchen_renderer.py
python3 -m py_compile examples.py
```

### Documentation

- Update README.md if adding new features
- Update QUICKSTART.md if changing installation/usage
- Update VIEWER_MANIFEST.md if changing manifest format
- Add examples to examples.py for new functionality

## Types of Contributions

### Bug Fixes

1. Create an issue describing the bug
2. Reference the issue in your PR
3. Include steps to reproduce
4. Add tests if applicable

### New Features

1. Open an issue to discuss the feature first
2. Get feedback before implementing
3. Update documentation
4. Add examples and tests

### Documentation

- Fix typos
- Improve clarity
- Add examples
- Update outdated information

## Adding New Kitchen Styles

To add new door or countertop styles:

1. Edit `config.json`:
   ```json
   {
     "door_styles": [
       {
         "id": "new_style",
         "name": "New Style Name",
         "color": [R, G, B, 1.0],
         "roughness": 0.3
       }
     ]
   }
   ```

2. Update `kitchen_renderer.py` DOOR_STYLES or COUNTERTOP_STYLES

3. Update documentation with the new style

4. Test with Blender-MCP

## Adding New Camera Views

To add new camera angles:

1. Edit `config.json`:
   ```json
   {
     "camera_views": {
       "KITCHEN_CUSTOM": {
         "location": [x, y, z],
         "rotation": [rx, ry, rz],
         "description": "Custom view description"
       }
     }
   }
   ```

2. Update `kitchen_renderer.py` CAMERA_VIEWS

3. Update documentation

4. Test rendering

## Submission Guidelines

### Pull Request Process

1. **Update Tests**: Add/update tests for your changes
2. **Update Docs**: Update relevant documentation
3. **Test Thoroughly**: Run all tests and manual testing
4. **Clear Commits**: Use descriptive commit messages
5. **One Feature Per PR**: Keep PRs focused

### Commit Messages

Follow this format:
```
<type>: <short summary>

<detailed description if needed>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test updates
- `refactor`: Code refactoring
- `style`: Code style changes
- `chore`: Build/config changes

Examples:
```
feat: Add wood grain texture support for cabinets
fix: Correct camera rotation for KITCHEN_AERIAL view
docs: Update QUICKSTART with GPU rendering instructions
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Mock tests pass
- [ ] Syntax validation passes
- [ ] Tested with live Blender-MCP
- [ ] Documentation updated

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No security issues introduced
```

## Code Review Process

1. Maintainers will review your PR
2. Address any feedback
3. Once approved, PR will be merged
4. Your contribution will be credited

## Reporting Issues

### Bug Reports

Include:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python version, Blender version)
- Error messages/logs
- Screenshots if applicable

### Feature Requests

Include:
- Clear description of the feature
- Use case and benefits
- Possible implementation approach
- Examples if applicable

## Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others when possible
- Follow the code of conduct

## Questions?

- Open an issue for general questions
- Tag issues with `question` label
- Check existing issues first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Git commit history

Thank you for contributing to px-kitchen-blender! 🎉
