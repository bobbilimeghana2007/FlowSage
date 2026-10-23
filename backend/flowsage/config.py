"""Configuration from environment variables only. No secrets in code."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str = "flowsage.db"
    secret_key: str = ""
    decider_mode: str = "simulated"      # "live" | "simulated"
    decider_url: str = "http://127.0.0.1:8099"
    decider_timeout_s: float = 10.0
    bedrock_mode: str = "off"            # "live" | "off"
    bedrock_model_id: str = ""
    aws_region: str = "us-east-1"
    bedrock_timeout_s: float = 20.0
    max_agent_steps: int = 3
    token_ttl_s: int = 8 * 3600

    @staticmethod
    def from_env() -> "Settings":
        e = os.environ.get
        return Settings(
            db_path=e("FLOWSAGE_DB", "flowsage.db"),
            secret_key=e("FLOWSAGE_SECRET_KEY", ""),
            decider_mode=e("FLOWSAGE_DECIDER_MODE", "simulated"),
            decider_url=e("STRANDS_DECIDER_URL", "http://127.0.0.1:8099"),
            bedrock_mode=e("FLOWSAGE_BEDROCK_MODE", "off"),
            bedrock_model_id=e("BEDROCK_MODEL_ID", ""),
            aws_region=e("AWS_REGION", "us-east-1"),
        )
