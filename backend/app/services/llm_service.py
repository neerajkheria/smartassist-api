import time
from openai import AzureOpenAI, APIError, RateLimitError, APITimeoutError
from app.core.config import settings
from app.core.telemetry import telemetry_logger

class CircuitBreaker:
    """Prevents cascading failures when Azure OpenAI experiences sustained errors."""
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED (healthy), OPEN (tripped), HALF-OPEN (testing)

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF-OPEN"
                telemetry_logger.warning("Circuit breaker entering HALF-OPEN recovery state.")
                return True
            return False
        return True

    def record_success(self):
        if self.state != "CLOSED":
            telemetry_logger.info("Circuit breaker recovered -> CLOSED.")
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            telemetry_logger.error(
                f"Circuit breaker TRIPPED -> OPEN after {self.failure_count} consecutive failures."
            )

class LLMService:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            timeout=20.0
        )
        self.deployment = "gpt-5.1"
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

    def _fallback_response(self, prompt: str, reason: str) -> dict:
        """Graceful degradation response when upstream model is unavailable."""
        return {
            "success": True,
            "degraded_mode": True,
            "response": (
                "[Automated Fallback - AI Service Temporarily Degraded]\n"
                "Your incident has been logged and queued for L2 Engineer review. "
                "Immediate checklist: 1) Verify Azure Service Health status, "
                "2) Check NSG/Firewall rules, 3) Attach diagnostic logs to your ticket."
            ),
            "fallback_reason": reason,
            "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }

    def generate_chat_response(
        self, 
        prompt: str, 
        system_instruction: str = "You are an enterprise IT support engineer for GlobalTech Solutions.",
        max_tokens: int = None
    ) -> dict:
        if not self.circuit_breaker.allow_request():
            telemetry_logger.warning("Request short-circuited by OPEN circuit breaker.")
            return self._fallback_response(prompt, reason="CircuitBreakerOpen")

        max_completion = int(max_tokens) if max_tokens else getattr(settings, "DEFAULT_MAX_COMPLETION_TOKENS", 500)
        max_retries = 3
        backoff = 2

        for attempt in range(max_retries):
            start_ts = time.perf_counter()
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=max_completion
                )

                llm_latency_ms = round((time.perf_counter() - start_ts) * 1000, 2)
                self.circuit_breaker.record_success()

                choice = response.choices[0]
                usage = response.usage

                telemetry_logger.info(
                    "Azure OpenAI inference succeeded",
                    extra={
                        "custom_dimensions": {
                            "model": self.deployment,
                            "llm_latency_ms": llm_latency_ms,
                            "prompt_tokens": usage.prompt_tokens,
                            "completion_tokens": usage.completion_tokens,
                            "total_tokens": usage.total_tokens
                        }
                    }
                )

                return {
                    "success": True,
                    "degraded_mode": False,
                    "response": choice.message.content,
                    "finish_reason": choice.finish_reason,
                    "tokens": {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens
                    },
                    "parameters": {
                        "model": self.deployment,
                        "max_completion_tokens": max_completion,
                        "llm_latency_ms": llm_latency_ms
                    }
                }

            except RateLimitError as e:
                telemetry_logger.warning(f"HTTP 429 RateLimit on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    self.circuit_breaker.record_failure()
                    return self._fallback_response(prompt, reason="RateLimitExhausted")
                time.sleep(backoff)
                backoff *= 2

            except (APITimeoutError, APIError) as e:
                telemetry_logger.error(f"Azure OpenAI API failure: {str(e)}")
                self.circuit_breaker.record_failure()
                return self._fallback_response(prompt, reason=type(e).__name__)

    def stream_chat_response(
        self,
        prompt: str,
        system_instruction: str = "You are an enterprise IT support engineer for GlobalTech Solutions.",
        max_tokens: int = None
    ):
        if not self.circuit_breaker.allow_request():
            yield "[Automated Fallback] AI service circuit breaker is currently open. Please retry in 30 seconds."
            return

        max_completion = int(max_tokens) if max_tokens else getattr(settings, "DEFAULT_MAX_COMPLETION_TOKENS", 500)
        try:
            response_stream = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=max_completion,
                stream=True
            )
            for chunk in response_stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
            self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            telemetry_logger.error(f"Streaming error: {str(e)}")
            yield f"\n[Stream Interrupted - Fallback Activated]: {str(e)}"

llm_service = LLMService()