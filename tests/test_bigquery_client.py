"""
Unit tests for BigQuery client re_calculate behavior.

Tests the BigQuery client's handling of the re_calculate flag in get_conversations method.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bigquery_client import BigQueryClient


class TestBigQueryClientRecalculate:
    """Test BigQuery client re_calculate behavior"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.project_id = "test-project"
        self.dataset_id = "test-dataset"
        self.conversation_view = "test-view"
        self.evaluation_table = "test-table"
    
    @patch('bigquery_client.bigquery.Client')
    def test_get_conversations_recalculate_false_excludes_evaluated(self, mock_client_class):
        """Test that re_calculate=False excludes already evaluated conversations"""
        # Mock BigQuery client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock query execution - return empty results (no conversations to evaluate)
        mock_query_job = Mock()
        mock_client.query.return_value = mock_query_job
        mock_query_job.result.return_value = []
        
        # Mock table creation
        mock_client.get_table.side_effect = Exception("Table not found")
        mock_client.create_table.return_value = Mock()
        
        # Create BigQuery client
        client = BigQueryClient(
            project_id=self.project_id,
            dataset_id=self.dataset_id,
            conversation_view=self.conversation_view,
            evaluation_table=self.evaluation_table
        )
        
        # Call get_conversations with re_calculate=False
        conversations = client.get_conversations(
            last_x_days=7,
            re_calculate=False
        )
        
        # Verify query was executed
        mock_client.query.assert_called()
        
        # Get the executed query
        executed_query = mock_client.query.call_args[0][0]
        
        # Verify the query contains NOT IN clause to exclude already evaluated conversations
        assert "NOT IN" in executed_query
        assert f"{self.project_id}.{self.dataset_id}.{self.evaluation_table}" in executed_query
        assert "session_id NOT IN" in executed_query
        
        # Verify no conversations returned (all already evaluated)
        assert conversations == []
    
    @patch('bigquery_client.bigquery.Client')
    def test_get_conversations_recalculate_true_includes_evaluated(self, mock_client_class):
        """Test that re_calculate=True includes already evaluated conversations"""
        # Mock BigQuery client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock query execution - return some conversations
        mock_query_job = Mock()
        mock_client.query.return_value = mock_query_job
        
        # Mock row results
        from datetime import datetime
        mock_row1 = Mock()
        mock_row1.project_id = "test-project"
        mock_row1.agent_id = "agent-1"
        mock_row1.session_id = "session-1"
        mock_row1.conversation_turns = '{"turns": []}'
        mock_row1.extraction_timestamp = datetime(2024, 1, 1, 10, 0, 0)
        
        mock_query_job.result.return_value = [mock_row1]
        
        # Mock table creation
        mock_client.get_table.side_effect = Exception("Table not found")
        mock_client.create_table.return_value = Mock()
        
        # Create BigQuery client
        client = BigQueryClient(
            project_id=self.project_id,
            dataset_id=self.dataset_id,
            conversation_view=self.conversation_view,
            evaluation_table=self.evaluation_table
        )
        
        # Call get_conversations with re_calculate=True
        conversations = client.get_conversations(
            last_x_days=7,
            re_calculate=True
        )
        
        # Verify query was executed
        mock_client.query.assert_called()
        
        # Get the executed query
        executed_query = mock_client.query.call_args[0][0]
        
        # Verify the query does NOT contain NOT IN clause
        assert "NOT IN" not in executed_query
        
        # Verify conversations were returned (including already evaluated ones)
        assert len(conversations) == 1
        assert conversations[0]["session_id"] == "session-1"
    
    @patch('bigquery_client.bigquery.Client')
    def test_get_conversations_agent_filter(self, mock_client_class):
        """Test that agent filter works correctly with re_calculate flag"""
        # Mock BigQuery client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock query execution
        mock_query_job = Mock()
        mock_client.query.return_value = mock_query_job
        mock_query_job.result.return_value = []
        
        # Mock table creation
        mock_client.get_table.side_effect = Exception("Table not found")
        mock_client.create_table.return_value = Mock()
        
        # Create BigQuery client
        client = BigQueryClient(
            project_id=self.project_id,
            dataset_id=self.dataset_id,
            conversation_view=self.conversation_view,
            evaluation_table=self.evaluation_table
        )
        
        # Call get_conversations with specific agent
        conversations = client.get_conversations(
            last_x_days=7,
            agent_id="agent-1",
            re_calculate=False
        )
        
        # Get the executed query
        executed_query = mock_client.query.call_args[0][0]
        
        # Verify both agent filter and re_calculate filter are present
        assert "agent_id = 'agent-1'" in executed_query
        assert "NOT IN" in executed_query
    
    @patch('bigquery_client.bigquery.Client')
    def test_get_conversations_all_agents(self, mock_client_class):
        """Test that 'all' agent filter works correctly"""
        # Mock BigQuery client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock query execution
        mock_query_job = Mock()
        mock_client.query.return_value = mock_query_job
        mock_query_job.result.return_value = []
        
        # Mock table creation
        mock_client.get_table.side_effect = Exception("Table not found")
        mock_client.create_table.return_value = Mock()
        
        # Create BigQuery client
        client = BigQueryClient(
            project_id=self.project_id,
            dataset_id=self.dataset_id,
            conversation_view=self.conversation_view,
            evaluation_table=self.evaluation_table
        )
        
        # Call get_conversations with agent_id="all"
        conversations = client.get_conversations(
            last_x_days=7,
            agent_id="all",
            re_calculate=False
        )
        
        # Get the executed query
        executed_query = mock_client.query.call_args[0][0]
        
        # Verify no agent filter is applied for "all"
        assert "agent_id = 'all'" not in executed_query
        assert "NOT IN" in executed_query  # re_calculate filter should still be present
    
    @patch('bigquery_client.bigquery.Client')
    def test_query_structure_recalculate_false(self, mock_client_class):
        """Test the structure of the SQL query when re_calculate=False"""
        # Mock BigQuery client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock query execution
        mock_query_job = Mock()
        mock_client.query.return_value = mock_query_job
        mock_query_job.result.return_value = []
        
        # Mock table creation
        mock_client.get_table.side_effect = Exception("Table not found")
        mock_client.create_table.return_value = Mock()
        
        # Create BigQuery client
        client = BigQueryClient(
            project_id=self.project_id,
            dataset_id=self.dataset_id,
            conversation_view=self.conversation_view,
            evaluation_table=self.evaluation_table
        )
        
        # Call get_conversations with re_calculate=False
        client.get_conversations(last_x_days=7, re_calculate=False)
        
        # Get the executed query
        executed_query = mock_client.query.call_args[0][0]
        
        # Verify query structure
        assert "SELECT" in executed_query
        assert "FROM" in executed_query
        assert "WHERE 1=1" in executed_query
        assert "ORDER BY session_id" in executed_query
        
        # Verify re_calculate=False specific parts
        assert "NOT IN" in executed_query
        assert "SELECT DISTINCT session_id" in executed_query
        assert f"FROM `{self.project_id}.{self.dataset_id}.{self.evaluation_table}`" in executed_query
    
    @patch('bigquery_client.bigquery.Client')
    def test_query_structure_recalculate_true(self, mock_client_class):
        """Test the structure of the SQL query when re_calculate=True"""
        # Mock BigQuery client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock query execution
        mock_query_job = Mock()
        mock_client.query.return_value = mock_query_job
        mock_query_job.result.return_value = []
        
        # Mock table creation
        mock_client.get_table.side_effect = Exception("Table not found")
        mock_client.create_table.return_value = Mock()
        
        # Create BigQuery client
        client = BigQueryClient(
            project_id=self.project_id,
            dataset_id=self.dataset_id,
            conversation_view=self.conversation_view,
            evaluation_table=self.evaluation_table
        )
        
        # Call get_conversations with re_calculate=True
        client.get_conversations(last_x_days=7, re_calculate=True)
        
        # Get the executed query
        executed_query = mock_client.query.call_args[0][0]
        
        # Verify query structure
        assert "SELECT" in executed_query
        assert "FROM" in executed_query
        assert "WHERE 1=1" in executed_query
        assert "ORDER BY session_id" in executed_query
        
        # Verify re_calculate=True specific parts (no NOT IN clause)
        assert "NOT IN" not in executed_query
        assert "SELECT DISTINCT session_id" not in executed_query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
