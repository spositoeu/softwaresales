import logging
import json
import traceback
from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs JSON structured logs for production
    and human-readable logs for development.
    """

    def __init__(self, json_output: bool = False):
        super().__init__()
        self.json_output = json_output

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach extra context fields if provided
        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context

        # Attach request_id if present
        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = record.request_id

        # Attach user_id if present
        if hasattr(record, "user_id") and record.user_id:
            log_data["user_id"] = record.user_id

        # Attach exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        if self.json_output:
            return json.dumps(log_data, ensure_ascii=False, default=str)

        # Human-readable format for development
        parts = [
            f"[{log_data['timestamp']}]",
            f"[{log_data['level']}]",
            f"[{log_data['logger']}]",
            log_data["message"],
        ]

        if log_data.get("context"):
            parts.append(f"| context={json.dumps(log_data['context'], default=str)}")

        if log_data.get("request_id"):
            parts.append(f"| request_id={log_data['request_id']}")

        if log_data.get("exception"):
            exc = log_data["exception"]
            parts.append(f"\nEXCEPTION [{exc['type']}]: {exc['message']}")
            if exc.get("traceback"):
                parts.append("".join(exc["traceback"]))

        return " ".join(parts)


class AppLogger:
    """
    Application logger with contextual metadata support.
    Wraps Python's standard logging with structured output.
    """

    _instances: dict[str, "AppLogger"] = {}

    def __init__(
        self,
        name: str,
        level: str = "INFO",
        json_output: bool = False,
    ):
        self.name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter(json_output=json_output))
            self._logger.addHandler(handler)

        self._default_context: dict[str, Any] = {}

    @classmethod
    def get(
        cls,
        name: str,
        level: str = "INFO",
        json_output: bool = False,
    ) -> "AppLogger":
        """
        Get or create a named logger instance (singleton per name).
        """
        if name not in cls._instances:
            cls._instances[name] = cls(name, level=level, json_output=json_output)
        return cls._instances[name]

    def with_context(self, **kwargs: Any) -> "AppLogger":
        """
        Return a child logger that carries additional default context.
        """
        child = AppLogger(
            name=f"{self.name}.ctx",
            level=logging.getLevelName(self._logger.level),
        )
        child._logger = self._logger
        child._default_context = {**self._default_context, **kwargs}
        return child

    def _build_extra(
        self,
        context: Optional[dict[str, Any]],
        request_id: Optional[str],
        user_id: Optional[str],
    ) -> dict[str, Any]:
        merged_context = {**self._default_context}
        if context:
            merged_context.update(context)

        return {
            "context": merged_context if merged_context else None,
            "request_id": request_id,
            "user_id": user_id,
        }

    def debug(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        self._logger.debug(
            message,
            extra=self._build_extra(context, request_id, user_id),
        )

    def info(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        self._logger.info(
            message,
            extra=self._build_extra(context, request_id, user_id),
        )

    def warning(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        self._logger.warning(
            message,
            extra=self._build_extra(context, request_id, user_id),
        )

    def error(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        exc_info: bool = False,
    ) -> None:
        self._logger.error(
            message,
            exc_info=exc_info,
            extra=self._build_extra(context, request_id, user_id),
        )

    def critical(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        exc_info: bool = True,
    ) -> None:
        self._logger.critical(
            message,
            exc_info=exc_info,
            extra=self._build_extra(context, request_id, user_id),
        )

    def exception(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Log an error with automatic exception traceback capture.
        Should be called inside an except block.
        """
        self._logger.exception(
            message,
            extra=self._build_extra(context, request_id, user_id),
        )


def configure_root_logger(
    level: str = "INFO",
    json_output: bool = False,
) -> None:
    """
    Configure the root logger for the application.
    Call once at application startup.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter(json_output=json_output))
        root.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("stripe").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Module-level default logger for quick imports
# ---------------------------------------------------------------------------

logger = AppLogger.get("softwaresales")