# Conversation Evaluator Tests

This directory contains unit tests for the conversation evaluator, specifically focusing on the `re_calculate` behavior.

## Test Structure

### Test Files

- **`test_recalculate_behavior.py`** - Main tests for re_calculate functionality
- **`test_bigquery_client.py`** - Tests for BigQuery client re_calculate behavior
- **`test_api_recalculate.py`** - Tests for API endpoints re_calculate behavior
- **`conftest.py`** - Shared pytest fixtures
- **`run_tests.py`** - Test runner script

### Test Coverage

The tests cover the following scenarios:

#### re_calculate=False (Default)
- ✅ Skips already evaluated conversations
- ✅ Only processes new conversations
- ✅ Generates SQL query with `NOT IN` clause
- ✅ API endpoint passes `re_calculate=False` to evaluation runner

#### re_calculate=True
- ✅ Includes already evaluated conversations
- ✅ Recalculates existing metrics with new timestamps
- ✅ Generates SQL query without `NOT IN` clause
- ✅ API endpoint passes `re_calculate=True` to evaluation runner

#### BigQuery Client Tests
- ✅ Query structure validation
- ✅ Agent filtering with re_calculate
- ✅ Proper SQL generation for both scenarios

#### API Tests
- ✅ Request validation
- ✅ Parameter passing
- ✅ Response structure
- ✅ Error handling

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-mock
```

### Run All Tests

```bash
# From the conversation_evaluator directory
python tests/run_tests.py

# Or using pytest directly
pytest tests/ -v
```

### Run Specific Test Files

```bash
# Test re_calculate behavior
pytest tests/test_recalculate_behavior.py -v

# Test BigQuery client
pytest tests/test_bigquery_client.py -v

# Test API endpoints
pytest tests/test_api_recalculate.py -v
```

### Run Specific Test Classes

```bash
# Test BigQuery client re_calculate behavior
pytest tests/test_bigquery_client.py::TestBigQueryClientRecalculate -v

# Test API re_calculate behavior
pytest tests/test_api_recalculate.py::TestAPIRecalculateBehavior -v
```

## Test Scenarios

### 1. re_calculate=False Behavior

**Expected Behavior:**
- BigQuery query includes `NOT IN` clause to exclude already evaluated sessions
- Only new conversations are processed
- Existing evaluations are not recalculated

**Test Cases:**
- `test_recalculate_false_skips_existing_evaluations()`
- `test_get_conversations_recalculate_false_excludes_evaluated()`
- `test_start_evaluation_recalculate_false()`

### 2. re_calculate=True Behavior

**Expected Behavior:**
- BigQuery query does NOT include `NOT IN` clause
- All conversations are processed, including already evaluated ones
- Existing evaluations are recalculated with new timestamps

**Test Cases:**
- `test_recalculate_true_includes_existing_evaluations()`
- `test_get_conversations_recalculate_true_includes_evaluated()`
- `test_start_evaluation_recalculate_true()`

### 3. SQL Query Validation

**Expected SQL for re_calculate=False:**
```sql
SELECT project_id, agent_id, session_id, conversation_turns, CURRENT_TIMESTAMP() as extraction_timestamp
FROM `project.dataset.conversation_view`
WHERE 1=1
AND session_id NOT IN (
    SELECT DISTINCT session_id 
    FROM `project.dataset.evaluation_table`
)
ORDER BY session_id
```

**Expected SQL for re_calculate=True:**
```sql
SELECT project_id, agent_id, session_id, conversation_turns, CURRENT_TIMESTAMP() as extraction_timestamp
FROM `project.dataset.conversation_view`
WHERE 1=1
ORDER BY session_id
```

## Mocking Strategy

The tests use comprehensive mocking to isolate units under test:

- **BigQuery Client**: Mocked to avoid actual BigQuery calls
- **Job Store**: Mocked to avoid state persistence
- **LLM Client**: Mocked to avoid actual LLM API calls
- **Evaluation Runner**: Mocked for API tests

## Fixtures

Shared fixtures in `conftest.py`:
- `sample_conversations` - Test conversation data
- `sample_metrics` - Test metrics configuration
- `mock_bigquery_client` - Mocked BigQuery client
- `mock_job_store` - Mocked job store
- `mock_llm_client` - Mocked LLM client

## Assertions

Tests verify:
- ✅ Correct method calls with expected parameters
- ✅ Proper SQL query generation
- ✅ API request/response handling
- ✅ Error conditions
- ✅ Data flow through the system

## Continuous Integration

These tests should be run in CI/CD pipelines to ensure:
- re_calculate behavior works correctly
- No regressions in existing functionality
- API contracts are maintained
- BigQuery queries are properly generated
