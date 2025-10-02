import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional

class EvaluationJobStore:
    def __init__(self):
        """Initialize job store with thread-safe storage for evaluation jobs."""
        self._jobs = {}
        self._lock = threading.Lock()

    def create_job(self, last_x_days: int, re_calculate: bool, evaluation_run: bool, 
                   total_conversations: int, total_metrics: int) -> Dict:
        """Create a new evaluation job with progress tracking."""
        with self._lock:
            job_id = str(uuid.uuid4())
            total_evaluations = total_conversations * total_metrics
            
            job_data = {
                "job_id": job_id,
                "start_time": datetime.now().isoformat(),
                "status": "started",
                "progress": {"total": total_evaluations, "completed": 0, "failed": 0},
                "last_x_days": last_x_days,
                "re_calculate": re_calculate,
                "evaluation_run": evaluation_run,
                "total_conversations": total_conversations,
                "total_metrics": total_metrics,
                "total_evaluations": total_evaluations
            }
            
            self._jobs[job_id] = job_data
            return job_data

    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job details by job ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def update_job_status(self, job_id: str, status: str):
        """Update job status and set end time for completed jobs."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status
                if status in ["completed", "failed", "stopped"]:
                    self._jobs[job_id]["end_time"] = datetime.now().isoformat()

    def increment_progress_batch(self, job_id: str, success_count: int, failed_count: int):
        """Update job progress in batch and mark as completed when done."""
        with self._lock:
            if job_id in self._jobs:
                progress = self._jobs[job_id]["progress"]
                progress["completed"] += success_count
                progress["failed"] += failed_count
                
                if progress["completed"] + progress["failed"] >= progress["total"]:
                    self._jobs[job_id]["status"] = "completed" if progress["failed"] == 0 else "completed_with_errors"
                    self._jobs[job_id]["end_time"] = datetime.now().isoformat()

    def set_job_error(self, job_id: str, error_message: str):
        """Mark job as failed with error message and end time."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update({
                    "status": "failed",
                    "error": error_message,
                    "end_time": datetime.now().isoformat()
                })

    def get_all_jobs(self, start_date: Optional[str] = None) -> List[Dict]:
        """Get all jobs, optionally filtered by start date, sorted by newest first."""
        with self._lock:
            jobs = list(self._jobs.values())
            
            if start_date:
                try:
                    start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    jobs = [job for job in jobs 
                           if datetime.fromisoformat(job["start_time"].replace('Z', '+00:00')) >= start_datetime]
                except ValueError:
                    pass
            
            jobs.sort(key=lambda x: x["start_time"], reverse=True)
            return jobs

    def stop_job(self, job_id: str) -> bool:
        """Stop a running job and return success status."""
        with self._lock:
            if job_id in self._jobs and self._jobs[job_id]["status"] in ["started", "running"]:
                self._jobs[job_id].update({
                    "status": "stopped",
                    "end_time": datetime.now().isoformat()
                })
                return True
            return False

job_store = EvaluationJobStore()

