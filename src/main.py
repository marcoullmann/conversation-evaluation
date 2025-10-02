import logging
from fastapi import FastAPI
from api import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Conversation Evaluator API", 
    version="0.1.0",
    description="Automated evaluation system for conversational agents"
)

app.include_router(router)

logger.info("Conversation Evaluator API started")

@app.get("/")
async def root():
    """Get API information and version."""
    return {
        "message": "Conversation Evaluator API",
        "version": "0.1.0",
        "description": "Automated evaluation system for conversational agents"
    }

