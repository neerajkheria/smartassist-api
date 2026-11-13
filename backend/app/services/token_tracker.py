import tiktoken
import logging
from typing import List, Dict

logger = logging.getLogger("smartassist.tokens")

class TokenTracker:
    def __init__(self, model_encoding: str = "o200k_base"):
        try:
            self.encoder = tiktoken.get_encoding(model_encoding)
        except Exception:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        self.history: List[Dict] = []
        self.MAX_INPUT_TOKENS_PER_REQUEST = 800

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def validate_request_size(self, text: str) -> bool:
        return self.count_tokens(text) <= self.MAX_INPUT_TOKENS_PER_REQUEST

    def record_usage(self, customer_id: str, prompt_tokens: int, completion_tokens: int):
        self.history.append({
            "customer_id": customer_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        })

    def generate_report(self) -> dict:
        total_requests = len(self.history)
        total_prompt = sum(item["prompt_tokens"] for item in self.history)
        total_completion = sum(item["completion_tokens"] for item in self.history)
        grand_total = total_prompt + total_completion

        return {
            "total_requests": total_requests,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "grand_total_tokens": grand_total,
            "average_tokens_per_request": round(grand_total / total_requests, 2) if total_requests > 0 else 0
        }

token_tracker = TokenTracker()