.PHONY: test test-coverage test-verbose install-test-deps clean lint

# Install test dependencies
install-test-deps:
	pip install -r test-requirements.txt

# Run basic tests
test:
	pytest

# Run tests with coverage
test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term

# Run tests with verbose output
test-verbose:
	pytest -v -s

# Run specific test file
test-file:
	pytest $(FILE) -v

# Run tests matching a pattern
test-pattern:
	pytest -k $(PATTERN) -v

# Clean test artifacts
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Lint the source code
lint:
	python -m py_compile src/*.py
	python -m py_compile tests/*.py

# Install all dependencies (main + test)
install-all:
	pip install -r src/requirements.txt
	pip install -r test-requirements.txt

# Run tests in development mode with auto-reload
test-watch:
	pytest --looponfail

# Generate test report
test-report:
	pytest --cov=src --cov-report=html --cov-report=xml --junit-xml=test-results.xml

help:
	@echo "Available targets:"
	@echo "  test              - Run basic tests"
	@echo "  test-coverage     - Run tests with coverage report"
	@echo "  test-verbose      - Run tests with verbose output"
	@echo "  test-file FILE=   - Run specific test file"
	@echo "  test-pattern PATTERN= - Run tests matching pattern"
	@echo "  install-test-deps - Install test dependencies"
	@echo "  install-all       - Install all dependencies"
	@echo "  clean             - Clean test artifacts"
	@echo "  lint              - Lint source code"
	@echo "  test-report       - Generate detailed test reports"