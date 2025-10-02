# Conversation Evaluator

Automated evaluation system for conversational agents that analyzes agent conversations for quality assessment and GenAI compliance monitoring.

## Features

- **Automated Evaluation**: LLM-based evaluation of conversations using configurable metrics
- **GenAI Risk Monitoring**: Detection of toxicity, compliance issues, hallucinations, and data privacy risks
- **Scalable Architecture**: Cloud Run service with BigQuery integration
- **Real-time Progress Tracking**: Job-based evaluation with progress monitoring
- **Flexible Metrics**: JSON-configured evaluation metrics for easy maintenance
- **GenAI Core Integration**: Uses genai-core-langchain-addons for AXA internal LLM access

## Architecture

The system consists of:

- **Conversation Evaluator (ConvEval)**: Cloud Run service for evaluation
- **BigQuery Integration**: Storage of conversation logs and evaluation results
- **GenAI Core LLM**: Text analysis using genai-core-langchain-addons (Gemini 2.5 Flash)
- **REST API**: Management of evaluation jobs and results

## Quick Start

### Local Development

1. **Install dependencies**:
```bash
pip install -r requirements.txt
# or using uv
uv pip install -r requirements.txt
```

2. **Run the application**:
```bash
# Windows - using batch file
.\run_server.bat

# Or manually
set PYTHONPATH=src
set GCP_PROJECT=adnovum-gm-cai
python -m uvicorn src.main:app --host 127.0.0.1 --port 8080 --reload
```

### Docker

```bash
docker build -t conversation-evaluator .
docker run -p 8080:8080 conversation-evaluator
```

## API Endpoints

### Start Evaluation
```bash
POST /evaluation
{
  "last_x_days": 7,
  "re_calculate": false,
  "evaluation_run": false
}
```

### Get Job Status
```bash
GET /evaluation/{job_id}
```

### List Evaluations
```bash
GET /evaluations?start=2024-01-01
```

### Stop Evaluation
```bash
POST /evaluation/{job_id}/stop
```

## Configuration

### Metrics Configuration

Evaluation metrics are defined in `config/metrics.json`:

```json
[
  {
    "name": "toxicity_score",
    "prompt": "Bewerte die Toxizität dieser Konversation...",
    "type": "numeric",
    "applicable_agents": ["all"]
  }
]
```

### Environment Variables

- `USE_LLM_MOCK`: Use mock LLM for local testing (default: true)
- `GCP_PROJECT`: Google Cloud project ID
- `LLM_GW_API_KEY`: GenAI Gateway API key (for real LLM)
- `CERT_PATH`: Certificate path for GenAI Core (optional, default: /certificate/certificate.pem)

## Evaluation Metrics

The system includes pre-configured metrics for GenAI risk monitoring:

1. **Toxicity Score**: Detects harmful or inappropriate language
2. **Compliance Status**: Checks adherence to AXA policies
3. **Professionalism Score**: Evaluates agent professionalism
4. **Data Privacy Check**: Identifies sensitive data exposure
5. **Hallucination Detection**: Finds false or invented information
6. **Customer Satisfaction Prediction**: Predicts customer satisfaction
7. **Escalation Necessity**: Evaluates escalation appropriateness
8. **Conversation Flow Quality**: Assesses conversation structure

## Data Model

### Evaluation Results Table

```sql
CREATE TABLE ct_interaction_eval (
  agent_id STRING NOT NULL,
  session_id STRING NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  metric STRING NOT NULL,
  metric_value_string STRING,
  metric_value_numeric FLOAT64
);
```

## Development

### Project Structure

```
conversation_monitoring/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── api.py               # REST API endpoints
│   ├── config.py            # Configuration management
│   ├── llm_client.py        # GenAI Core LLM integration
│   ├── bigquery_client.py   # BigQuery integration
│   ├── job_store.py         # Job tracking
│   └── evaluation_runner.py # Evaluation execution
├── config/
│   └── metrics.json         # Evaluation metrics
├── tests/                   # Unit tests
├── requirements.txt
├── pyproject.toml
├── run_server.bat          # Windows startup script
└── Dockerfile
```

### Testing

```bash
# Run all tests
set PYTHONPATH=src
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_bigquery_client.py -v

# Test API endpoints (with server running)
curl http://localhost:8080/
curl http://localhost:8080/metrics
curl http://localhost:8080/config
```

## Deployment

### Cloud Run

1. Build and push Docker image
2. Deploy to Cloud Run with appropriate environment variables
3. Configure BigQuery permissions
4. Set up monitoring and alerting

### Environment Variables for Production

```bash
USE_LLM_MOCK=false
GCP_PROJECT=your-project
LLM_GW_API_KEY=your-genai-gateway-api-key
CERT_PATH=/certificate/certificate.pem
```

## Monitoring

- Job progress tracking via API endpoints
- BigQuery integration for result storage
- Configurable evaluation metrics
- Error handling and logging
- Automatic conversation view creation

## BigQuery Integration

The system automatically creates the required BigQuery resources:

- **Conversation View**: `conversation_extraction_view` - Extracts conversations from `ct_interaction_log`
- **Evaluation Table**: `ct_interaction_eval` - Stores evaluation results

The conversation view processes interaction logs and formats them for evaluation, handling both user and bot messages with proper ordering.

## Contributing

1. Follow the existing code structure
2. Add new metrics to `config/metrics.json`
3. Update tests for new functionality
4. Document API changes
5. Ensure GenAI Core compatibility

