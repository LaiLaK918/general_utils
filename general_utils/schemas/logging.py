from enum import Enum


class LogLevel(Enum):
    """Enum for log levels to ensure type safety."""

    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
