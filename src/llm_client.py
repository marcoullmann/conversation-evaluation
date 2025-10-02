import os
import random
import logging
from typing import List, Dict
from config import config

logger = logging.getLogger(__name__)

class MockLLMClient:
    def __init__(self):
        """Initialize mock LLM client with predefined responses for testing."""
        self.responses = {
            "toxicity_score": lambda: str(random.randint(0, 3)),
            "compliance_status": lambda: random.choice(["COMPLIANT", "COMPLIANT", "COMPLIANT", "NEEDS_REVIEW"]),
            "professionalism_score": lambda: str(random.randint(7, 10)),
            "data_privacy_check": lambda: random.choice(["SAFE", "SAFE", "SAFE", "POTENTIAL_RISK"]),
            "hallucination_detection": lambda: random.choice(["ACCURATE", "ACCURATE", "ACCURATE", "POTENTIAL_HALLUCINATION"]),
            "customer_satisfaction_prediction": lambda: str(random.randint(6, 9)),
            "escalation_necessity": lambda: random.choice(["APPROPRIATE_ESCALATION", "UNNECESSARY_ESCALATION", "SHOULD_HAVE_ESCALATED"]),
            "conversation_flow_quality": lambda: str(random.randint(6, 9))
        }
    
    def evaluate_conversation(self, conversation_turns: List[Dict[str, str]], metric_name: str, prompt: str) -> str:
        """Return mock evaluation result based on metric name."""
        return self.responses.get(metric_name, lambda: "MOCK_RESPONSE")()

class LLMClient:
    def __init__(self):
        """Initialize LLM client with GenAI Core or mock implementation."""
        self.client = None
        self.model_name = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize GenAI Core client from environment variables."""
        try:
            from genai_core_langchain_addons import GenAICoreChatVertexAI
            
            self.model_name = config.llm["model_name"]
            project = config.llm["project"]
            api_key = config.llm["gw_api_key"]
            cert_path = config.llm["cert_path"]
            location = config.llm["location"]

            if all([project, api_key]):
                self.client = GenAICoreChatVertexAI(
                    project=project,
                    llm_gw_api_key=api_key,
                    esg_consumer_cert_path=cert_path,
                    model=self.model_name,
                    location=location,
                )
                logger.info("GenAI Core client initialized successfully")
            else:
                logger.warning("GenAI Core client not configured - missing required environment variables")
                
        except ImportError:
            logger.warning("genai-core-langchain-addons not available - using mock client")
        except Exception as e:
            logger.error(f"Error initializing GenAI Core client: {str(e)}")

    def is_configured(self) -> bool:
        """Check if the LLM client is properly configured."""
        return self.client is not None

    def evaluate_conversation(self, conversation_turns: List[Dict[str, str]], metric_name: str, prompt: str) -> str:
        """Evaluate conversation using GenAI Core LLM or mock."""
        use_mock = os.getenv("USE_LLM_MOCK", "true").lower() == "true"
        
        if use_mock or not self.is_configured():
            # Use mock client
            mock_client = MockLLMClient()
            return mock_client.evaluate_conversation(conversation_turns, metric_name, prompt)
        
        # Convert conversation turns to the format expected by GenAI Core
        conversation_history = []
        for turn in conversation_turns:
            role = "human" if turn.get('role', '').lower() in ['user', 'human'] else "ai"
            conversation_history.append({"role": role, "content": turn.get('message', '')})
        
        # Add the evaluation prompt as a human message
        conversation_text = "\n".join(f"{turn.get('role', 'Unknown')}: {turn.get('message', '')}" for turn in conversation_turns)
        conversation_history.append({
            "role": "human", 
            "content": f"{prompt}\n\nKonversation:\n{conversation_text}"
        })
        
        response = self.client.invoke(conversation_history)
        return response.content.strip()

llm_client = LLMClient()

