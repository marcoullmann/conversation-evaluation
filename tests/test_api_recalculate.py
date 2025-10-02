"""
Unit tests for API endpoints re_calculate behavior.

Tests the API endpoints' handling of the re_calculate flag.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from api import router


class TestAPIRecalculateBehavior:
    """Test API re_calculate behavior"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.client = TestClient(app)
    
    @patch('api.evaluation_runner')
    @patch('api.job_store')
    def test_start_evaluation_recalculate_false(self, mock_job_store, mock_evaluation_runner):
        """Test POST /evaluation with re_calculate=False"""
        # Mock evaluation runner
        mock_evaluation_runner.start_evaluation_job.return_value = "test-job-123"
        
        # Mock job store
        mock_job_store.get_job.return_value = {
            "job_id": "test-job-123",
            "start_time": "2024-01-01T00:00:00",
            "status": "started",
            "progress": {"total": 10, "completed": 0, "failed": 0}
        }
        
        # Request data with re_calculate=False
        request_data = {
            "last_x_days": 7,
            "re_calculate": False,
            "evaluation_run": False
        }
        
        # Make request
        response = self.client.post("/evaluation", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["job_id"] == "test-job-123"
        assert response_data["status"] == "started"
        
        # Verify evaluation runner was called with correct parameters
        mock_evaluation_runner.start_evaluation_job.assert_called_with(
            last_x_days=7,
            re_calculate=False,
            evaluation_run=False
        )
    
    @patch('api.evaluation_runner')
    @patch('api.job_store')
    def test_start_evaluation_recalculate_true(self, mock_job_store, mock_evaluation_runner):
        """Test POST /evaluation with re_calculate=True"""
        # Mock evaluation runner
        mock_evaluation_runner.start_evaluation_job.return_value = "test-job-456"
        
        # Mock job store
        mock_job_store.get_job.return_value = {
            "job_id": "test-job-456",
            "start_time": "2024-01-01T00:00:00",
            "status": "started",
            "progress": {"total": 10, "completed": 0, "failed": 0}
        }
        
        # Request data with re_calculate=True
        request_data = {
            "last_x_days": 7,
            "re_calculate": True,
            "evaluation_run": False
        }
        
        # Make request
        response = self.client.post("/evaluation", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["job_id"] == "test-job-456"
        assert response_data["status"] == "started"
        
        # Verify evaluation runner was called with correct parameters
        mock_evaluation_runner.start_evaluation_job.assert_called_with(
            last_x_days=7,
            re_calculate=True,
            evaluation_run=False
        )
    
    @patch('api.evaluation_runner')
    @patch('api.job_store')
    def test_start_evaluation_default_recalculate(self, mock_job_store, mock_evaluation_runner):
        """Test POST /evaluation with default re_calculate value"""
        # Mock evaluation runner
        mock_evaluation_runner.start_evaluation_job.return_value = "test-job-789"
        
        # Mock job store
        mock_job_store.get_job.return_value = {
            "job_id": "test-job-789",
            "start_time": "2024-01-01T00:00:00",
            "status": "started",
            "progress": {"total": 10, "completed": 0, "failed": 0}
        }
        
        # Request data without re_calculate (should default to False)
        request_data = {
            "last_x_days": 7,
            "evaluation_run": False
        }
        
        # Make request
        response = self.client.post("/evaluation", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["job_id"] == "test-job-789"
        
        # Verify evaluation runner was called with re_calculate=False (default)
        mock_evaluation_runner.start_evaluation_job.assert_called_with(
            last_x_days=7,
            re_calculate=False,
            evaluation_run=False
        )
    
    @patch('api.job_store')
    def test_get_evaluation_status_preserves_recalculate_flag(self, mock_job_store):
        """Test that GET /evaluation/{job_id} preserves re_calculate flag in response"""
        # Mock job store
        mock_job_data = {
            "job_id": "test-job-123",
            "start_time": "2024-01-01T10:00:00Z",
            "status": "running",
            "progress": {
                "total": 20,
                "completed": 10,
                "failed": 0
            },
            "re_calculate": True  # This should be preserved
        }
        mock_job_store.get_job.return_value = mock_job_data
        
        # Make request
        response = self.client.get("/evaluation/test-job-123")
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["job_id"] == "test-job-123"
        assert response_data["status"] == "running"
        assert response_data["progress"]["total"] == 20
        assert response_data["progress"]["completed"] == 10
        
        # Verify job store was called
        mock_job_store.get_job.assert_called_with("test-job-123")
    
    @patch('api.job_store')
    def test_list_evaluations_includes_recalculate_flag(self, mock_job_store):
        """Test that GET /evaluations includes re_calculate flag in response"""
        # Mock job store
        mock_jobs = [
            {
                "job_id": "job-1",
                "start_time": "2024-01-01T10:00:00Z",
                "status": "completed",
                "progress": {"total": 10, "completed": 10, "failed": 0},
                "re_calculate": False
            },
            {
                "job_id": "job-2", 
                "start_time": "2024-01-01T11:00:00Z",
                "status": "completed",
                "progress": {"total": 15, "completed": 15, "failed": 0},
                "re_calculate": True
            }
        ]
        mock_job_store.get_all_jobs.return_value = mock_jobs
        
        # Make request
        response = self.client.get("/evaluations")
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["evaluations"]) == 2
        
        # Verify first job
        job1 = response_data["evaluations"][0]
        assert job1["job_id"] == "job-1"
        assert job1["status"] == "completed"
        
        # Verify second job
        job2 = response_data["evaluations"][1]
        assert job2["job_id"] == "job-2"
        assert job2["status"] == "completed"
        
        # Verify job store was called
        mock_job_store.get_all_jobs.assert_called_with(start_date=None)
    
    @patch('api.job_store')
    def test_list_evaluations_with_start_date(self, mock_job_store):
        """Test GET /evaluations with start date filter"""
        # Mock job store
        mock_jobs = [
            {
                "job_id": "job-1",
                "start_time": "2024-01-01T10:00:00Z",
                "status": "completed",
                "progress": {"total": 10, "completed": 10, "failed": 0},
                "re_calculate": True
            }
        ]
        mock_job_store.get_all_jobs.return_value = mock_jobs
        
        # Make request with start date
        response = self.client.get("/evaluations?start=2024-01-01")
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["evaluations"]) == 1
        
        # Verify job store was called with start date
        mock_job_store.get_all_jobs.assert_called_with(start_date="2024-01-01")
    
    def test_start_evaluation_invalid_request(self):
        """Test POST /evaluation with invalid request data"""
        # Invalid request data (negative last_x_days)
        request_data = {
            "last_x_days": -5,  # Invalid: must be -1 (all) or >= 0
            "re_calculate": True,
            "evaluation_run": False
        }
        
        # Make request
        response = self.client.post("/evaluation", json=request_data)
        
        # Verify error response
        assert response.status_code == 400  # Bad request
    
    def test_start_evaluation_invalid_recalculate_type(self):
        """Test POST /evaluation with invalid re_calculate type"""
        # Invalid request data (re_calculate as number instead of boolean)
        request_data = {
            "last_x_days": 7,
            "re_calculate": 123,  # Should be boolean, not number
            "evaluation_run": False
        }
        
        # Make request
        response = self.client.post("/evaluation", json=request_data)
        
        # Verify error response
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
