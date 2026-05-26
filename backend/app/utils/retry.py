import logging

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def ai_retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda state: logger.warning("AI retry attempt %s", state.attempt_number),
    )
