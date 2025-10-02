import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AppConfig:
    bigquery: Dict[str, Any]
    llm: Dict[str, Any]
    evaluation: Dict[str, Any]

def load_config() -> AppConfig:
    """Load application configuration from environment variables."""
    bigquery = {
        "project_id": os.getenv("GCP_PROJECT"),
        "dataset_id": "ds_iIVR_agent_export",
        "conversation_view": "conversation_extraction_view",
        "evaluation_table": "ct_interaction_eval"
    }
    
    llm = {
        "model_name": "gemini-2.5-flash",
        "project": os.getenv("GCP_PROJECT"),
        "gw_api_key": os.getenv("LLM_GW_API_KEY"),
        "cert_path": os.getenv("CERT_PATH", "/certificate/certificate.pem"),
        "location": "europe-west4"
    }
    
    evaluation = {
        "metrics_config_path": "config/metrics.json",
        "max_concurrent_evaluations": 50,
        "default_last_x_days": 7
    }
    
    return AppConfig(bigquery=bigquery, llm=llm, evaluation=evaluation)

config = load_config()

