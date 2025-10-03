# Testing Guide

This document provides comprehensive guidance for testing the Bank Customer Churn Prediction Pipeline.

## Test Structure

```
tests/
├── conftest.py                      # Shared test fixtures
├── api/                            # API unit tests
│   ├── test_inference.py
│   ├── test_loader.py
│   └── test_main.py
├── bank_customer_churn_prediction_pipeline/  # Core pipeline unit tests
│   ├── test_data_io.py
│   ├── test_flow_tasks.py
│   ├── test_monitoring.py
│   ├── test_preprocessing.py
│   └── test_training.py
└── integration/                    # Integration tests
    ├── conftest.py                 # Integration test fixtures
    ├── api/
    │   └── test_fastapi_integration.py
    ├── pipeline/
    │   └── test_ml_pipeline_integration.py
    ├── monitoring/
    │   └── test_monitoring_integration.py
    └── test_integration_simple.py
```

## Running Tests

### Unit Tests

```bash
# Run all unit tests
pixi run pytest tests/ --ignore=tests/integration/

# Run specific unit test modules
pixi run pytest tests/api/ -v
pixi run pytest tests/bank_customer_churn_prediction_pipeline/ -v

# Run with coverage
pixi run pytest tests/ --ignore=tests/integration/ --cov=src --cov-report=html
```

### Integration Tests

```bash
# Run all integration tests
pixi run pytest tests/integration/ -m integration

# Run specific integration test categories
pixi run pytest tests/integration/api/ -v
pixi run pytest tests/integration/pipeline/ -v
pixi run pytest tests/integration/monitoring/ -v

# Run fast integration tests only
pixi run pytest tests/integration/ -m "integration and not slow"
```

### CI Command (matches GitHub Actions)

```bash
# Same command as used in CI
pixi run pytest --ignore=tests/api/test_main.py --ignore=tests/bank_customer_churn_prediction_pipeline/test_flow_tasks.py
```

## Test Categories

### Unit Tests

Test individual components in isolation with mocked dependencies:

**API Tests (`tests/api/`):**
- `test_inference.py` - Data validation, prediction logic
- `test_loader.py` - MLflow model loading utilities
- `test_main.py` - FastAPI endpoints (skipped in CI)

**Core Pipeline Tests (`tests/bank_customer_churn_prediction_pipeline/`):**
- `test_data_io.py` - Data reading and splitting
- `test_preprocessing.py` - Feature engineering
- `test_training.py` - Model training and optimization
- `test_monitoring.py` - Data drift monitoring
- `test_flow_tasks.py` - Prefect workflow tasks (skipped in CI)

### Integration Tests

Test end-to-end functionality and real component interactions:

**FastAPI Integration (`tests/integration/api/`):**
- Application startup and lifecycle
- Real request/response cycles
- Model loading and prediction workflows
- Error handling and service failures

**ML Pipeline Integration (`tests/integration/pipeline/`):**
- End-to-end data processing
- Real file I/O operations
- Actual model training workflows
- Pipeline error handling

**Monitoring Integration (`tests/integration/monitoring/`):**
- Evidently report generation
- Database operations (when available)
- Service integration and fallbacks

## Test Markers

```bash
# Available pytest markers
@pytest.mark.integration  # Integration tests
@pytest.mark.slow         # Long-running tests
@pytest.mark.unit         # Unit tests
@pytest.mark.skip         # Skip tests requiring external services
```

## Test Data and Fixtures

### Unit Test Fixtures (`tests/conftest.py`)

- `sample_data` - 100 rows of synthetic customer data
- `sample_features` - Feature data without target
- `sample_targets` - Target labels
- `temp_csv_file` - Temporary CSV for file I/O tests
- `mock_preprocessor` - Mocked sklearn preprocessor
- `mock_xgb_model` - Mocked XGBoost model
- `sample_prediction_request` - API request payload

### Integration Test Fixtures (`tests/integration/conftest.py`)

- `integration_test_data` - 1000 rows of realistic test data
- `integration_csv_file` - Temporary CSV with integration data
- `real_preprocessor` - Actual sklearn ColumnTransformer
- `trained_xgb_model` - Real trained XGBoost model
- `mlflow_test_setup` - Temporary MLflow tracking
- `registered_test_models` - Models in test MLflow registry

## External Dependencies

### Required for All Tests
- Python 3.11+
- All dependencies from `pyproject.toml`

### Optional for Integration Tests
- **MLflow Tracking Server** (`localhost:5000`)
- **Evidently Service** (`localhost:8000`)
- **PostgreSQL Database** (`localhost:5432`)

### Running with Docker Services

```bash
# Start services
cd infra && docker-compose up -d

# Run full integration tests
pixi run pytest tests/integration/ -v

# Stop services
cd infra && docker-compose down
```

## Service Detection and Mocking

Integration tests automatically detect service availability:

```python
@pytest.fixture
def skip_integration_if_no_docker():
    """Skip if Docker services not available"""

@pytest.fixture
def mock_external_services():
    """Mock external services when not available"""
```

When services aren't available, tests use realistic mocks to ensure functionality.

## Test Performance

### Execution Times
- **Unit Tests**: ~3-5 seconds total
- **Fast Integration Tests**: ~5-10 seconds
- **Slow Integration Tests**: ~30-60 seconds (marked with `@pytest.mark.slow`)

### Optimization Strategies
- Minimal data sizes for speed while maintaining realism
- Mocked external services by default
- Parallel test execution support
- Selective test execution with markers

## Debugging Tests

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure dependencies installed
   pixi install
   ```

2. **Test Timeouts**
   ```bash
   # Run without integration tests
   pixi run pytest tests/ --ignore=tests/integration/
   ```

3. **Service Connection Failures**
   ```bash
   # Run with mocked services
   pixi run pytest tests/integration/ -k "not service"
   ```

### Debugging Commands

```bash
# Verbose output with traceback
pixi run pytest tests/ -vvv --tb=long

# Run single test with debugging
pixi run pytest tests/api/test_inference.py::TestValidateAndFrame::test_validate_and_frame_valid_data -vvv

# Drop into debugger on failure
pixi run pytest tests/ --pdb

# Run with coverage
pixi run pytest tests/ --cov=src --cov-report=term-missing
```

## Continuous Integration

### GitHub Actions Configuration

Tests run automatically on push with:
- Python 3.12 on Ubuntu
- Pixi package manager
- Specific test exclusions: `test_main.py` and `test_flow_tasks.py`

### Local CI Simulation

```bash
# Run same tests as CI
pixi add python=3.12
pixi run pytest --ignore=tests/api/test_main.py --ignore=tests/bank_customer_churn_prediction_pipeline/test_flow_tasks.py
```

## Test Coverage

### Current Coverage

- **Unit Tests**: ~90% of core functionality
- **Integration Tests**: Key end-to-end workflows
- **API Tests**: All endpoints and error conditions
- **Pipeline Tests**: Complete ML workflow coverage

### Coverage Reports

```bash
# Generate HTML coverage report
pixi run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Terminal coverage report
pixi run pytest tests/ --cov=src --cov-report=term-missing
```

## Adding New Tests

### Unit Tests

1. Create test file: `test_<module_name>.py`
2. Import module under test
3. Use fixtures from `conftest.py`
4. Mock external dependencies
5. Test both success and failure cases

```python
def test_function_name(self, fixture_name):
    """Test description"""
    with patch('module.dependency') as mock_dep:
        result = function_under_test(input_data)
        assert result == expected_output
```

### Integration Tests

1. Create test in `tests/integration/`
2. Add `@pytest.mark.integration` marker
3. Use integration fixtures
4. Test real component interactions
5. Mock only unavailable external services

```python
@pytest.mark.integration
def test_integration_scenario(self, integration_test_data):
    """Test real end-to-end functionality"""
    result = real_function(integration_test_data)
    assert isinstance(result, expected_type)
```

## Best Practices

### General Testing

- **Test Behavior, Not Implementation**: Focus on inputs/outputs
- **Independent Tests**: Each test should run in isolation
- **Descriptive Names**: Test names should explain what they verify
- **Arrange, Act, Assert**: Clear test structure

### Unit Testing

- **Mock External Dependencies**: Database, API calls, file systems
- **Test Edge Cases**: Empty data, invalid inputs, boundary conditions
- **Fast Execution**: Unit tests should complete in milliseconds

### Integration Testing

- **Use Real Components**: Test actual sklearn, XGBoost, pandas operations
- **Realistic Data**: Representative data sizes and distributions
- **Service Fallbacks**: Handle unavailable external services gracefully
- **Performance Aware**: Mark slow tests appropriately

## Test Maintenance

### Regular Tasks

1. **Update Test Data**: Ensure test data reflects current schema
2. **Review Mocks**: Verify mocks match real service behavior
3. **Performance Monitoring**: Check for test execution time increases
4. **Coverage Analysis**: Identify untested code paths

### Dependency Updates

When updating dependencies:
1. Run full test suite: `pixi run pytest tests/`
2. Update fixtures if APIs change
3. Review integration tests for compatibility
4. Update mocks to match new behavior

This testing framework ensures reliable, maintainable code while supporting both rapid development and production deployment confidence.
