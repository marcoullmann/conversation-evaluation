"""
Pytest configuration and shared fixtures for conversation evaluator tests.
"""

import pytest
import json
from unittest.mock import Mock
from typing import List, Dict, Any


@pytest.fixture
def sample_conversations():
    """Sample conversation data for testing"""
    return [
        {
            "project_id": "test-project",
            "agent_id": "agent-1",
            "session_id": "session-1",
            "conversation_turns": json.dumps([
                {"role": "user", "message": "Hello"},
                {"role": "assistant", "message": "Hi there!"}
            ]),
            "extraction_timestamp": "2024-01-01T10:00:00Z"
        },
        {
            "project_id": "test-project",
            "agent_id": "agent-1", 
            "session_id": "session-2",
            "conversation_turns": json.dumps([
                {"role": "user", "message": "How are you?"},
                {"role": "assistant", "message": "I'm doing well, thank you!"}
            ]),
            "extraction_timestamp": "2024-01-01T10:01:00Z"
        },
        {
            "project_id": "test-project",
            "agent_id": "agent-2",
            "session_id": "session-3", 
            "conversation_turns": json.dumps([
                {"role": "user", "message": "What's the weather like?"},
                {"role": "assistant", "message": "I don't have access to weather data."}
            ]),
            "extraction_timestamp": "2024-01-01T10:02:00Z"
        }
    ]


@pytest.fixture
def sample_metrics():
    """Sample metrics configuration for testing"""
    return [
        {
            "name": "toxicity_score",
            "prompt": "Rate the toxicity of this conversation from 0-10",
            "type": "numeric",
            "applicable_agents": ["all"]
        },
        {
            "name": "compliance_status",
            "prompt": "Check if this conversation complies with company policies",
            "type": "string", 
            "applicable_agents": ["all"]
        },
        {
            "name": "professionalism_score",
            "prompt": "Rate the professionalism from 0-10",
            "type": "numeric",
            "applicable_agents": ["agent-1"]
        }
    ]


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client for testing"""
    mock_client = Mock()
    mock_client.instance_id = "test-instance"
    mock_client.flush_remaining = Mock(return_value=True)
    mock_client.save_evaluation_result = Mock(return_value=True)
    mock_client.get_conversations = Mock(return_value=[])
    return mock_client


@pytest.fixture
def mock_job_store():
    """Mock job store for testing"""
    mock_store = Mock()
    mock_store.create_job = Mock(return_value={"job_id": "test-job-123"})
    mock_store.get_job = Mock(return_value={"status": "running"})
    mock_store.increment_progress_batch = Mock()
    mock_store.update_job_status = Mock()
    return mock_store


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    mock_llm = Mock()
    mock_llm.evaluate_conversation = Mock(return_value="5")
    return mock_llm


@pytest.fixture
def evaluation_request_data():
    """Sample evaluation request data"""
    return {
        "last_x_days": 7,
        "re_calculate": False,
        "evaluation_run": False
    }


@pytest.fixture
def evaluation_request_data_recalculate():
    """Sample evaluation request data with re_calculate=True"""
    return {
        "last_x_days": 7,
        "re_calculate": True,
        "evaluation_run": False
    }
