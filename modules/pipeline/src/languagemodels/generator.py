import json
import boto3
import logging
from typing import Optional
import configs  # Importing the central config module

class LanguageModelClient:
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client('sagemaker-runtime', region_name=region_name)
        self.logger = logging.getLogger(__name__)
        
        # Access endpoint names directly from config.py
        self.ENDPOINT_FACT_EXTRACTOR = configs.ENDPOINT_FACT_EXTRACTOR
        self.ENDPOINT_QUERY_GENERATOR = configs.ENDPOINT_QUERY_GENERATOR
        self.ENDPOINT_FACT_JUDGE = configs.ENDPOINT_FACT_JUDGE

    def _invoke(self, endpoint_name: str, prompt: str) -> Optional[str]:
        payload = {"prompt": prompt}
        try:
            response = self.client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            response_body = json.loads(response['Body'].read().decode('utf-8'))
            return response_body.get("content", "").strip()
            
        except Exception as e:
            self.logger.error(f"Error invoking SageMaker endpoint '{endpoint_name}': {e}")
            return None

    def fact_extractor(self, text: str) -> Optional[str]:
        return self._invoke(self.ENDPOINT_FACT_EXTRACTOR, text)

    def query_generator(self, text: str) -> Optional[str]:
        return self._invoke(self.ENDPOINT_QUERY_GENERATOR, text)

    def fact_judge(self, text: str) -> Optional[str]:
        return self._invoke(self.ENDPOINT_FACT_JUDGE, text)

# Global instance for use in pipeline.py
reranker = Reranker()
