import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from job_store import job_store
from evaluation_runner import evaluation_runner
from config import config

logger = logging.getLogger(__name__)
router = APIRouter()

class EvaluationRequest(BaseModel):
    last_x_days: int = 7
    re_calculate: bool = False
    evaluation_run: bool = False

class EvaluationResponse(BaseModel):
    job_id: str
    start_time: str
    status: str
    progress: dict

class EvaluationListResponse(BaseModel):
    evaluations: List[EvaluationResponse]

class ProgressInfo(BaseModel):
    total: int
    completed: int
    failed: int

class EvaluationStatusResponse(BaseModel):
    job_id: str
    start_time: str
    status: str
    progress: ProgressInfo

@router.post("/evaluation", response_model=EvaluationResponse)
async def start_evaluation(request: EvaluationRequest):
    """Start a new evaluation job with specified parameters."""
    try:
        if request.last_x_days < -1:
            raise HTTPException(status_code=400, detail="last_x_days must be -1 (all) or >= 0")
        
        job_id = evaluation_runner.start_evaluation_job(
            last_x_days=request.last_x_days,
            re_calculate=request.re_calculate,
            evaluation_run=request.evaluation_run
        )
        
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=500, detail="Failed to create evaluation job")
        
        return EvaluationResponse(
            job_id=job["job_id"],
            start_time=job["start_time"],
            status=job["status"],
            progress=job["progress"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in start_evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting evaluation: {str(e)}")

@router.get("/evaluation/{job_id}", response_model=EvaluationStatusResponse)
async def get_evaluation_status(job_id: str):
    """Get evaluation job status and progress."""
    try:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return EvaluationStatusResponse(
            job_id=job["job_id"],
            start_time=job["start_time"],
            status=job["status"],
            progress=ProgressInfo(**job["progress"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_evaluation_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving job status: {str(e)}")

@router.get("/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(start: Optional[str] = None):
    """List all evaluation jobs, optionally filtered by start date."""
    try:
        jobs = job_store.get_all_jobs(start_date=start)
        evaluations = [
            EvaluationResponse(
                job_id=job["job_id"],
                start_time=job["start_time"],
                status=job["status"],
                progress=job["progress"]
            ) for job in jobs
        ]
        
        return EvaluationListResponse(evaluations=evaluations)
        
    except Exception as e:
        logger.error(f"Error in list_evaluations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing evaluations: {str(e)}")

@router.post("/evaluation/{job_id}/stop")
async def stop_evaluation(job_id: str):
    """Stop a running evaluation job."""
    try:
        success = job_store.stop_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or not running")
        
        return {"message": f"Job {job_id} stopped successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in stop_evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping job: {str(e)}")

@router.get("/metrics")
async def get_metrics():
    """Get available evaluation metrics."""
    try:
        metrics = evaluation_runner.metrics_config
        return {"metrics": metrics, "total_metrics": len(metrics)}
    except Exception as e:
        logger.error(f"Error in get_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")

