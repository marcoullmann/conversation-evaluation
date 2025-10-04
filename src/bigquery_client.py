import logging
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from google.cloud import bigquery

logger = logging.getLogger(__name__)

class BigQueryClient:
    def __init__(self, project_id: str, dataset_id: str, conversation_view: str, evaluation_table: str):
        """Initialize BigQuery client with buffered inserts and table creation."""
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.conversation_view = conversation_view
        self.evaluation_table = evaluation_table
        
        self.client = bigquery.Client(project=project_id, location="europe-west6")
        self._cached_table = None
        self._insert_buffer = []
        self._buffer_size = 50
        self._buffer_lock = threading.Lock()
        
        self.create_evaluation_table_if_not_exists()
        self.create_conversation_view_if_not_exists()
    
    def get_conversations(self, last_x_days: int = 7, agent_id: Optional[str] = None, re_calculate: bool = False) -> List[Dict[str, Any]]:
        """Get conversations from BigQuery with optional filtering and re_calculate logic."""
        try:
            agent_filter = f"AND agent_id = '{agent_id}'" if agent_id and agent_id != "all" else ""
            
            if not re_calculate:
                evaluation_subquery = f"SELECT DISTINCT session_id FROM `{self.project_id}.{self.dataset_id}.{self.evaluation_table}`"
                new_conversations_filter = f"AND session_id NOT IN ({evaluation_subquery})"
            else:
                new_conversations_filter = ""
            
            query = f"""
            SELECT project_id, agent_id, session_id, conversation_turns, CURRENT_TIMESTAMP() as extraction_timestamp
            FROM `{self.project_id}.{self.dataset_id}.{self.conversation_view}`
            WHERE 1=1 {agent_filter} {new_conversations_filter}
            ORDER BY session_id
            """
            
            results = self.client.query(query).result()
            conversations = [{
                "project_id": row.project_id,
                "agent_id": row.agent_id,
                "session_id": row.session_id,
                "conversation_turns": row.conversation_turns,
                "extraction_timestamp": row.extraction_timestamp.isoformat()
            } for row in results]
            
            logger.info(f"Retrieved {len(conversations)} conversations for evaluation")
            return conversations
            
        except Exception as e:
            logger.error(f"Error retrieving conversations from BigQuery: {str(e)}")
            raise
    
    def save_evaluation_result(self, agent_id: str, session_id: str, metric: str, 
                             metric_value_string: Optional[str] = None, 
                             metric_value_numeric: Optional[float] = None) -> bool:
        """Save evaluation result to BigQuery buffer with thread-safe batching."""
        try:
            row_data = {
                "agent_id": agent_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "metric": metric,
                "metric_value_string": metric_value_string,
                "metric_value_numeric": metric_value_numeric
            }
            
            with self._buffer_lock:
                self._insert_buffer.append(row_data)
                if len(self._insert_buffer) >= self._buffer_size:
                    return self._flush_buffer()
            return True
            
        except Exception as e:
            logger.error(f"Error adding evaluation result to buffer: {str(e)}")
            return False
    
    def _flush_buffer(self) -> bool:
        """Flush buffered evaluation results to BigQuery."""
        if not self._insert_buffer:
            return True
            
        try:
            if self._cached_table is None:
                table_id = f"{self.project_id}.{self.dataset_id}.{self.evaluation_table}"
                self._cached_table = self.client.get_table(table_id)
            
            errors = self.client.insert_rows_json(self._cached_table, self._insert_buffer)
            if errors:
                logger.error(f"Error inserting batch: {errors}")
                return False
            
            self._insert_buffer = []
            return True
            
        except Exception as e:
            logger.error(f"Error flushing buffer: {str(e)}")
            return False
    
    def flush_remaining(self) -> bool:
        """Flush any remaining buffered results to BigQuery."""
        with self._buffer_lock:
            return self._flush_buffer()

    def create_evaluation_table_if_not_exists(self) -> bool:
        """Create evaluation table if it doesn't exist with proper schema."""
        try:
            table_id = f"{self.project_id}.{self.dataset_id}.{self.evaluation_table}"
            
            try:
                self.client.get_table(table_id)
                return True
            except Exception:
                pass
            
            schema = [
                bigquery.SchemaField("agent_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("session_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("metric", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("metric_value_string", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("metric_value_numeric", "FLOAT64", mode="NULLABLE"),
            ]
            
            table = bigquery.Table(table_id, schema=schema)
            self.client.create_table(table)
            logger.info(f"Created evaluation table: {table_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating evaluation table: {str(e)}")
            return False

    def create_conversation_view_if_not_exists(self) -> bool:
        """Create conversation extraction view if it doesn't exist."""
        try:
            view_id = f"{self.project_id}.{self.dataset_id}.{self.conversation_view}"
            
            try:
                self.client.get_table(view_id)
                return True
            except Exception:
                pass
            
            view_sql = f"""
            CREATE OR REPLACE VIEW `{view_id}` AS
            WITH conversation_turns AS (
              SELECT 
                `conversation_name` as full_session_id,
                turn_position,
                1 as message_order,
                'User' as role,
                JSON_VALUE(request, '$.queryInput.text.text') as message,
                request_time
              FROM `{self.project_id}.{self.dataset_id}.ct_interaction_log`
              WHERE JSON_VALUE(request, '$.queryInput.text.text') IS NOT NULL
              
              UNION ALL
              
              SELECT 
                `conversation_name` as full_session_id,
                turn_position,
                2 as message_order,
                'Bot' as role,
                -- Handle initial greeting in responseMessages[1] and regular responses in [0]
                COALESCE(
                  JSON_VALUE(response, '$.queryResult.responseMessages[1].text.text[0]'),
                  JSON_VALUE(response, '$.queryResult.responseMessages[0].text.text[0]')
                ) as message,
                request_time
              FROM `{self.project_id}.{self.dataset_id}.ct_interaction_log`
              WHERE COALESCE(
                JSON_VALUE(response, '$.queryResult.responseMessages[1].text.text[0]'),
                JSON_VALUE(response, '$.queryResult.responseMessages[0].text.text[0]')
              ) IS NOT NULL
            )
            SELECT 
              -- Extract project ID
              REGEXP_EXTRACT(full_session_id, r'projects/([^/]+)') as project_id,
              -- Extract agent ID
              REGEXP_EXTRACT(full_session_id, r'/agents/([^/]+)') as agent_id,
              -- Extract session ID (handle both formats: /sessions/ and /environments/-/sessions/)
              CASE 
                WHEN REGEXP_CONTAINS(full_session_id, r'/environments/-/sessions/') THEN
                  REGEXP_EXTRACT(full_session_id, r'/environments/-/sessions/([^/]+)')
                ELSE
                  REGEXP_EXTRACT(full_session_id, r'/sessions/([^/]+)')
              END as session_id,
              -- Get the earliest request_time for the conversation
              MIN(request_time) as conversation_timestamp,
              TO_JSON_STRING(
                ARRAY_AGG(
                  STRUCT(role, message)
                  ORDER BY turn_position, message_order
                )
              ) as conversation_turns
            FROM conversation_turns
            GROUP BY project_id, agent_id, session_id
            ORDER BY project_id, agent_id, session_id
            """
            
            query_job = self.client.query(view_sql)
            query_job.result()
            logger.info(f"Created conversation view: {view_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating conversation view: {str(e)}")
            return False

