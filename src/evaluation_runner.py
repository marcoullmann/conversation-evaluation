import json
import logging
import threading
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import config
from bigquery_client import BigQueryClient
from llm_client import llm_client
from job_store import job_store

logger = logging.getLogger(__name__)

class EvaluationRunner:
    def __init__(self):
        """Initialize evaluation runner with BigQuery client and metrics configuration."""
        self.bigquery_client = BigQueryClient(
            project_id=config.bigquery["project_id"],
            dataset_id=config.bigquery["dataset_id"],
            conversation_view=config.bigquery["conversation_view"],
            evaluation_table=config.bigquery["evaluation_table"]
        )
        self.metrics_config = self._load_metrics_config()
        self.max_concurrent_evaluations = int(config.evaluation.get("max_concurrent_evaluations", 50))

    def _load_metrics_config(self) -> List[Dict[str, Any]]:
        """Load metrics configuration from JSON file."""
        try:
            with open(config.evaluation["metrics_config_path"], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metrics config: {str(e)}")
            return []
    
    def run_evaluation_job(self, job_id: str, last_x_days: int, re_calculate: bool, evaluation_run: bool):
        """Run evaluation job with parallel processing and progress tracking."""
        try:
            logger.info(f"Starting evaluation job {job_id}")
            job_store.update_job_status(job_id, "running")
            
            conversations = self.bigquery_client.get_conversations(last_x_days=last_x_days, agent_id=None, re_calculate=re_calculate)
            if not conversations:
                job_store.update_job_status(job_id, "completed")
                return
            
            applicable_metrics = self._get_applicable_metrics(conversations)
            all_evaluations = [
                {'conversation': conv, 'metric': metric}
                for conv in conversations for metric in applicable_metrics
            ]
            
            logger.info(f"Job {job_id}: Processing {len(all_evaluations)} evaluations with {self.max_concurrent_evaluations} concurrent LLM calls")
            
            with ThreadPoolExecutor(max_workers=self.max_concurrent_evaluations) as executor:
                future_to_evaluation = {
                    executor.submit(
                        self._evaluate_single_metric,
                        job_id, 
                        eval['conversation']['agent_id'],
                        eval['conversation']['session_id'],
                        json.loads(eval['conversation']['conversation_turns']),
                        eval['metric']
                    ): eval for eval in all_evaluations
                }
                
                completed_count = success_count = failed_count = 0
                
                for future in as_completed(future_to_evaluation):
                    evaluation = future_to_evaluation[future]
                    try:
                        success = future.result()
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1
                        
                        completed_count += 1
                        
                        if completed_count % 100 == 0:
                            job_store.increment_progress_batch(job_id, success_count, failed_count)
                            logger.info(f"Job {job_id}: Completed {completed_count}/{len(all_evaluations)} evaluations")
                            success_count = failed_count = 0
                        
                    except Exception as e:
                        logger.error(f"Error processing evaluation {evaluation['conversation'].get('session_id', 'unknown')} - {evaluation['metric']['name']}: {str(e)}")
                        failed_count += 1
                
                if success_count > 0 or failed_count > 0:
                    job_store.increment_progress_batch(job_id, success_count, failed_count)
            
            self.bigquery_client.flush_remaining()
            
            final_job = job_store.get_job(job_id)
            if final_job["status"] == "running":
                job_store.update_job_status(job_id, "completed")
            
            logger.info(f"Evaluation job {job_id} completed")
            
        except Exception as e:
            logger.error(f"Error in evaluation job {job_id}: {str(e)}")
            job_store.set_job_error(job_id, str(e))
    
    def _get_applicable_metrics(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get metrics applicable to the conversations based on agent IDs."""
        agent_ids = set(conv.get("agent_id") for conv in conversations)
        applicable_metrics = []
        
        for metric in self.metrics_config:
            applicable_agents = metric.get("applicable_agents", [])
            if "all" in applicable_agents or any(agent_id in applicable_agents for agent_id in agent_ids):
                applicable_metrics.append(metric)
        
        return applicable_metrics
    
    def _evaluate_single_metric(self, job_id: str, agent_id: str, session_id: str, 
                               conversation_turns: List[Dict], metric: Dict[str, Any]) -> bool:
        """Evaluate a single metric for a conversation and save result to BigQuery."""
        try:
            metric_name = metric["name"]
            prompt = metric["prompt"]
            metric_type = metric["type"]
            
            evaluation_result = llm_client.evaluate_conversation(
                conversation_turns=conversation_turns,
                metric_name=metric_name,
                prompt=prompt
            )
            
            if metric_type == "numeric":
                try:
                    numeric_value = float(evaluation_result)
                    self.bigquery_client.save_evaluation_result(
                        agent_id=agent_id, session_id=session_id, metric=metric_name,
                        metric_value_numeric=numeric_value
                    )
                except ValueError:
                    self.bigquery_client.save_evaluation_result(
                        agent_id=agent_id, session_id=session_id, metric=metric_name,
                        metric_value_string=evaluation_result
                    )
            else:
                self.bigquery_client.save_evaluation_result(
                    agent_id=agent_id, session_id=session_id, metric=metric_name,
                    metric_value_string=evaluation_result
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error evaluating {session_id} for metric {metric['name']}: {str(e)}")
            return False
    
    def start_evaluation_job(self, last_x_days: int, re_calculate: bool, evaluation_run: bool) -> str:
        """Start evaluation job and return job ID for tracking."""
        try:
            conversations = self.bigquery_client.get_conversations(last_x_days=last_x_days, agent_id=None, re_calculate=re_calculate)
            if not conversations:
                # Create a completed job with 0 evaluations
                job_data = job_store.create_job(
                    last_x_days=last_x_days, re_calculate=re_calculate, evaluation_run=evaluation_run,
                    total_conversations=0, total_metrics=0
                )
                job_store.update_job_status(job_data["job_id"], "completed")
                return job_data["job_id"]
            
            applicable_metrics = self._get_applicable_metrics(conversations)
            job_data = job_store.create_job(
                last_x_days=last_x_days, re_calculate=re_calculate, evaluation_run=evaluation_run,
                total_conversations=len(conversations), total_metrics=len(applicable_metrics)
            )
            
            thread = threading.Thread(
                target=self.run_evaluation_job,
                args=(job_data["job_id"], last_x_days, re_calculate, evaluation_run),
                daemon=True
            )
            thread.start()
            
            return job_data["job_id"]
            
        except Exception as e:
            logger.error(f"Error starting evaluation job: {str(e)}")
            raise

evaluation_runner = EvaluationRunner()

