"""
Unit tests for re_calculate behavior in conversation evaluation.

Tests the behavior when re_calculate flag is set to true vs false:
- re_calculate=True: Should recalculate already calculated metrics (with new timestamp)
- re_calculate=False: Should skip already calculated metrics
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bigquery_client import BigQueryClient
from evaluation_runner import EvaluationRunner
from job_store import EvaluationJobStore


class TestRecalculateBehavior:
    """Test class for re_calculate behavior"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        # Mock BigQuery client
        self.mock_bigquery_client = Mock(spec=BigQueryClient)
        self.mock_bigquery_client.instance_id = "test-instance"
        self.mock_bigquery_client.flush_remaining = Mock(return_value=True)
        self.mock_bigquery_client.save_evaluation_result = Mock(return_value=True)
        
        # Mock job store
        self.mock_job_store = Mock(spec=EvaluationJobStore)
        self.mock_job_store.create_job = Mock(return_value={"job_id": "test-job-123"})
        self.mock_job_store.get_job = Mock(return_value={"status": "running"})
        self.mock_job_store.increment_progress_batch = Mock()
        self.mock_job_store.update_job_status = Mock()
        
        # Sample conversation data
        self.sample_conversations = [
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
            }
        ]
        
        # Sample metrics
        self.sample_metrics = [
            {
                "name": "toxicity_score",
                "prompt": "Rate toxicity from 0-10",
                "type": "numeric",
                "applicable_agents": ["all"]
            },
            {
                "name": "compliance_status", 
                "prompt": "Check compliance",
                "type": "string",
                "applicable_agents": ["all"]
            }
        ]

    @patch('evaluation_runner.llm_client')
    def test_recalculate_false_skips_existing_evaluations(self, mock_llm_client):
        """Test that re_calculate=False skips already evaluated conversations"""
        # Mock LLM client
        mock_llm_client.evaluate_conversation = Mock(return_value="5")

        # Mock BigQuery client to return conversations that have already been evaluated
        # When re_calculate=False, get_conversations should exclude already evaluated sessions
        self.mock_bigquery_client.get_conversations = Mock(return_value=[])
        
        # Create evaluation runner with mocked dependencies
        with patch('evaluation_runner.BigQueryClient', return_value=self.mock_bigquery_client), \
             patch('evaluation_runner.job_store', self.mock_job_store):
            
            runner = EvaluationRunner()
            
            # Start evaluation with re_calculate=False should return job_id when no conversations found
            job_id = runner.start_evaluation_job(
                last_x_days=7,
                re_calculate=False,
                evaluation_run=False
            )
            
            # Should return a valid job_id
            assert job_id is not None
            assert isinstance(job_id, str)
            
            # Verify that get_conversations was called with re_calculate=False  
            self.mock_bigquery_client.get_conversations.assert_called_with(
                last_x_days=7,
                agent_id=None,
                re_calculate=False
            )

    @patch('evaluation_runner.llm_client')
    def test_recalculate_true_includes_existing_evaluations(self, mock_llm_client):
        """Test that re_calculate=True includes already evaluated conversations"""
        # Mock LLM client
        mock_llm_client.evaluate_conversation = Mock(return_value="5")
        
        # Mock BigQuery client to return conversations (including already evaluated ones)
        self.mock_bigquery_client.get_conversations = Mock(return_value=self.sample_conversations)
        
        # Create evaluation runner with mocked dependencies
        with patch('evaluation_runner.BigQueryClient', return_value=self.mock_bigquery_client), \
             patch('evaluation_runner.job_store', self.mock_job_store):
            
            runner = EvaluationRunner()
            
            # Start evaluation with re_calculate=True
            job_id = runner.start_evaluation_job(
                last_x_days=7,
                re_calculate=True,
                evaluation_run=False
            )
            
            # Verify that get_conversations was called with re_calculate=True   
            self.mock_bigquery_client.get_conversations.assert_called_with(
                last_x_days=7,
                agent_id=None,
                re_calculate=True
            )
            
            # Verify that conversations were returned (including already evaluated ones)
            assert job_id == "test-job-123"

    def test_bigquery_client_recalculate_false_query(self):
        """Test that BigQuery client generates correct query when re_calculate=False"""
        # Create a real BigQueryClient instance for testing query generation
        with patch('bigquery_client.bigquery.Client') as mock_client:
            # Mock the BigQuery client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            
            # Mock query execution
            mock_query_job = Mock()
            mock_client_instance.query.return_value = mock_query_job
            mock_query_job.result.return_value = []
            
            # Mock table creation
            mock_client_instance.get_table.side_effect = Exception("Table not found")
            mock_client_instance.create_table.return_value = Mock()
            
            client = BigQueryClient(
                project_id="test-project",
                dataset_id="test-dataset", 
                conversation_view="test-view",
                evaluation_table="test-table"
            )
            
            # Call get_conversations with re_calculate=False
            conversations = client.get_conversations(
                last_x_days=7,
                agent_id=None,
                re_calculate=False
            )
            
            # Verify that query was executed (called twice: once for view creation, once for data retrieval)
            assert mock_client_instance.query.call_count == 2
            
            # Get the query that was executed
            executed_query = mock_client_instance.query.call_args[0][0]
            
            # Verify that the query contains the NOT IN subquery for re_calculate=False
            assert "NOT IN" in executed_query
            assert "test-project.test-dataset.test-table" in executed_query

    def test_bigquery_client_recalculate_true_query(self):
        """Test that BigQuery client generates correct query when re_calculate=True"""
        # Create a real BigQueryClient instance for testing query generation
        with patch('bigquery_client.bigquery.Client') as mock_client:
            # Mock the BigQuery client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            
            # Mock query execution
            mock_query_job = Mock()
            mock_client_instance.query.return_value = mock_query_job
            mock_query_job.result.return_value = []
            
            # Mock table creation
            mock_client_instance.get_table.side_effect = Exception("Table not found")
            mock_client_instance.create_table.return_value = Mock()
            
            client = BigQueryClient(
                project_id="test-project",
                dataset_id="test-dataset",
                conversation_view="test-view", 
                evaluation_table="test-table"
            )
            
            # Call get_conversations with re_calculate=True
            conversations = client.get_conversations(
                last_x_days=7,
                agent_id=None,
                re_calculate=True
            )
            
            # Verify that query was executed (called twice: once for view creation, once for data retrieval)
            assert mock_client_instance.query.call_count == 2
            
            # Get the query that was executed
            executed_query = mock_client_instance.query.call_args[0][0]
            
            # Verify that the query does NOT contain the NOT IN subquery for re_calculate=True
            assert "NOT IN" not in executed_query


    def test_job_store_handles_recalculate_flag(self):
        """Test that job store properly handles the re_calculate flag"""
        job_store = EvaluationJobStore()
        
        # Create job with re_calculate=True
        job_data_true = job_store.create_job(
            last_x_days=7,
            re_calculate=True,
            evaluation_run=False,
            total_conversations=10,
            total_metrics=2
        )
        
        # Create job with re_calculate=False
        job_data_false = job_store.create_job(
            last_x_days=7,
            re_calculate=False,
            evaluation_run=False,
            total_conversations=5,
            total_metrics=2
        )
        
        # Verify both jobs were created successfully
        assert job_data_true["job_id"] is not None
        assert job_data_false["job_id"] is not None
        assert job_data_true["job_id"] != job_data_false["job_id"]
        
        # Verify job data
        job_true = job_store.get_job(job_data_true["job_id"])
        job_false = job_store.get_job(job_data_false["job_id"])
        
        assert job_true["re_calculate"] is True
        assert job_false["re_calculate"] is False
        assert job_true["total_conversations"] == 10
        assert job_false["total_conversations"] == 5


class TestRecalculateIntegration:
    """Integration tests for re_calculate behavior"""
    
    def test_full_evaluation_workflow_recalculate_false(self):
        """Test complete evaluation workflow with re_calculate=False"""
        # This would be an integration test that tests the full workflow
        # For now, we'll test the key components
        
        # Mock the entire evaluation process
        with patch('evaluation_runner.BigQueryClient') as mock_bq_class, \
             patch('evaluation_runner.job_store') as mock_job_store, \
             patch('evaluation_runner.llm_client') as mock_llm:
            
            # Setup mocks
            mock_bq_instance = Mock()
            mock_bq_class.return_value = mock_bq_instance
            mock_bq_instance.get_conversations.return_value = []  # No conversations (all already evaluated)
            mock_bq_instance.flush_remaining.return_value = True
            
            mock_job_store.create_job.return_value = {"job_id": "test-job"}
            mock_job_store.get_job.return_value = {"status": "running"}
            mock_job_store.increment_progress_batch = Mock()
            mock_job_store.update_job_status = Mock()
            
            mock_llm.evaluate_conversation.return_value = "5"
            
            # Create runner and start evaluation
            runner = EvaluationRunner()
            
            # Start evaluation with re_calculate=False should return job_id when no conversations found
            job_id = runner.start_evaluation_job(
                last_x_days=7,
                re_calculate=False,
                evaluation_run=False
            )
            
            # Should return a valid job_id
            assert job_id is not None
            assert isinstance(job_id, str)
            
            # Verify that get_conversations was called with re_calculate=False  
            mock_bq_instance.get_conversations.assert_called_with(
                last_x_days=7,
                agent_id=None,
                re_calculate=False
            )

    def test_full_evaluation_workflow_recalculate_true(self):
        """Test complete evaluation workflow with re_calculate=True"""
        # Mock the entire evaluation process
        with patch('evaluation_runner.BigQueryClient') as mock_bq_class, \
             patch('evaluation_runner.job_store') as mock_job_store, \
             patch('evaluation_runner.llm_client') as mock_llm:
            
            # Setup mocks
            mock_bq_instance = Mock()
            mock_bq_class.return_value = mock_bq_instance
            
            # Return some conversations (including already evaluated ones)
            sample_conversations = [
                {
                    "project_id": "test-project",
                    "agent_id": "agent-1", 
                    "session_id": "session-1",
                    "conversation_turns": json.dumps([{"role": "user", "message": "Hello"}]),
                    "extraction_timestamp": "2024-01-01T10:00:00Z"
                }
            ]
            mock_bq_instance.get_conversations.return_value = sample_conversations
            mock_bq_instance.flush_remaining.return_value = True
            mock_bq_instance.save_evaluation_result.return_value = True
            
            mock_job_store.create_job.return_value = {"job_id": "test-job"}
            mock_job_store.get_job.return_value = {"status": "running"}
            mock_job_store.increment_progress_batch = Mock()
            mock_job_store.update_job_status = Mock()
            
            mock_llm.evaluate_conversation.return_value = "5"
            
            # Create runner and start evaluation
            runner = EvaluationRunner()
            job_id = runner.start_evaluation_job(
                last_x_days=7,
                re_calculate=True,
                evaluation_run=False
            )
            
            # Verify that get_conversations was called with re_calculate=True   
            mock_bq_instance.get_conversations.assert_called_with(
                last_x_days=7,
                agent_id=None,
                re_calculate=True
            )
            
            # Verify job was created
            assert job_id == "test-job"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
