import boto3
import json
import logging
from typing import List, Dict
import configs

class Reranker:
    """A robust client for Phase 4: High-precision re-ranking via SageMaker."""
    
    def __init__(self, region_name: str = "us-east-1"):
        # Initialize the SageMaker runtime client
        self.client = boto3.client("sagemaker-runtime", region_name=region_name)
        self.endpoint_name = configs.ENDPOINT_RERANKER
        self.logger = logging.getLogger(__name__)

    def sort(self, boolean_query: str, chunks: List[Dict], top_k: int = 3) -> List[Dict]:
        """Refines top chunks by calling the SageMaker reranker endpoint."""
        if not chunks:
            return []

        # Prepare payload as expected by your SageMaker container's app.py
        payload = {
            "query": boolean_query,
            "documents": chunks
        }
        
        try:
            # Call the SageMaker endpoint
            response = self.client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            
            # Parse the response (the container returns a sorted list of dicts)
            result = json.loads(response['Body'].read().decode('utf-8'))
            
            return result[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error invoking Reranker endpoint '{self.endpoint_name}': {e}")
            raise Exception(f"Reranker inference failed: {e}")
