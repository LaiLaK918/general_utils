import gzip
import logging  # noqa: TID251
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Union

import loguru
import loguru._logger
from memoization import CachingAlgorithmFlag, cached

from ..schemas.logging import LogLevel


class LogRotationConfig:
    """Configuration class for log rotation settings."""

    def __init__(
        self,
        max_file_size: str = "10 MB",
        backup_count: int = 5,
        compression: str = "gz",
        rotation_time: Optional[str] = None,
    ):
        """
        Initialize log rotation configuration.

        Args:
            max_file_size: Maximum size before rotation (e.g., "10 MB", "50 KB")
            backup_count: Number of backup files to keep
            compression: Compression format for old logs ("gz", "zip", or None)
            rotation_time: Time-based rotation (e.g., "daily", "weekly", "1 hour")

        """
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.compression = compression
        self.rotation_time = rotation_time


class LogManager:
    """
    Thread-safe singleton log manager for centralized logging configuration.

    This class provides a centralized way to manage loggers across the application
    with consistent configuration, rotation, and filtering.
    """

    _instance = None
    _lock = threading.Lock()
    _loggers: Dict[str, loguru._logger.Logger] = {}

    def __new__(cls):
        """Ensure singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the log manager if not already initialized."""
        if not hasattr(self, "_initialized"):
            self._initialized = True

    def _setup_log_directory(self, log_path: Path) -> Path:
        """
        Ensure log directory exists and is writable.

        Args:
            log_path: Desired log directory path

        Returns:
            Path: Validated log directory path (or fallback)

        """
        try:
            log_path.mkdir(parents=True, exist_ok=True)

            # Test write permission
            test_file = log_path / ".write_test"
            test_file.touch()
            test_file.unlink()

            return log_path

        except (OSError, PermissionError):
            # Fallback to temporary directory
            import tempfile

            fallback_path = Path(tempfile.gettempdir()) / "general_utils_logs"
            fallback_path.mkdir(parents=True, exist_ok=True)
            print(
                f"Warning: Cannot write to {log_path}, using fallback: {fallback_path}"
            )
            return fallback_path

    def _compress_log_file(self, file_path: Path, compression: str = "gz") -> None:
        """
        Compress log file to save space.

        Args:
            file_path: Path to the file to compress
            compression: Compression format ("gz" or "zip")

        """
        try:
            if compression == "gz":
                with open(file_path, "rb") as f_in:
                    with gzip.open(f"{file_path}.gz", "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                file_path.unlink()
            elif compression == "zip":
                import zipfile

                with zipfile.ZipFile(
                    f"{file_path}.zip", "w", zipfile.ZIP_DEFLATED
                ) as zipf:
                    zipf.write(file_path, file_path.name)
                file_path.unlink()
        except Exception as e:
            print(f"Warning: Failed to compress {file_path}: {e}")

    def _log_filter(
        self,
        record: dict,
        log_verbose: bool = True,
        min_level: Union[LogLevel, str] = LogLevel.INFO,
    ) -> bool:
        """
        Enhanced log filtering with better error handling.

        Args:
            record: Log record dictionary
            log_verbose: Whether to show debug logs and full error traces
            min_level: Minimum log level to show

        Returns:
            bool: True if the record should be logged, False otherwise

        """
        try:
            # Convert min_level to LogLevel enum if it's a string
            if isinstance(min_level, str):
                min_level = LogLevel[min_level.upper()]

            # Filter by minimum log level
            if record["level"].no < min_level.value:
                return False

            # Hide debug and trace logs if verbose mode is disabled (additional filter)
            if record["level"].no <= LogLevel.DEBUG.value and not log_verbose:
                return False

            # Handle exception display based on verbose mode
            if record["level"].no == LogLevel.ERROR.value and not log_verbose:
                record["exception"] = None

            return True
        except (KeyError, AttributeError) as e:
            # If record is malformed, log it anyway to avoid losing information
            print(f"Warning: Malformed log record: {e}")
            return True


# Global variables for filter state
_log_verbose_global = True
_log_level_global = LogLevel.INFO
_log_manager_instance = None


def _get_effective_log_level(
    level: Union[str, LogLevel], is_default: bool = False
) -> Union[str, LogLevel]:
    """
    Determine the effective log level based on parameter and environment variable.

    Priority order:
    1. If level parameter is provided explicitly (not default), use it as highest priority
    2. If GNU_LOG_LEVEL environment variable is set, use it
    3. Use default LogLevel.INFO

    Args:
        level: The log level parameter passed to build_logger
        is_default: Whether the level parameter is the default value

    Returns:
        Union[str, LogLevel]: The effective log level to use

    """
    # If parameter is explicitly provided (not default), use it with highest priority
    if not is_default:
        return level

    # Check if GNU_LOG_LEVEL environment variable is set
    env_log_level = os.getenv("GNU_LOG_LEVEL")

    if env_log_level:
        try:
            # Try to convert environment variable to LogLevel enum
            if isinstance(env_log_level, str):
                return LogLevel[env_log_level.upper()]
            return env_log_level
        except (KeyError, ValueError):
            # If invalid level in environment variable, fall back to parameter
            print(
                f"Warning: Invalid log level '{env_log_level}' in GNU_LOG_LEVEL environment variable, using parameter value"
            )

    # Return the provided level (default value)
    return level


def _filter_logs(record: dict) -> bool:
    """
    Legacy filter function for backward compatibility.

    Args:
        record: Log record dictionary

    Returns:
        bool: True if the record should be logged, False otherwise

    """
    global _log_manager_instance, _log_verbose_global, _log_level_global
    if _log_manager_instance is None:
        _log_manager_instance = LogManager()
    return _log_manager_instance._log_filter(
        record, _log_verbose_global, _log_level_global
    )


@cached(max_size=100, algorithm=CachingAlgorithmFlag.LRU)
def build_logger(
    log_file: str = "App-Logger",
    rotation_config: Optional[LogRotationConfig] = None,
    format_string: Optional[str] = None,
    level: Union[str, LogLevel] = LogLevel.INFO,
    log_path: Optional[Union[str, Path]] = None,
    log_verbose: bool = True,
) -> loguru._logger.Logger:
    """
    Build a logger with enhanced features including rotation and compression.

    This function creates a logger with both console and file output, featuring:
    - Automatic log rotation based on size or time
    - Compression of old log files
    - Configurable formatting
    - Thread-safe operation
    - Enhanced error handling
    - Environment variable-based log level configuration

    Log Level Priority:
    1. If level parameter is explicitly provided (not default), it takes highest priority
    2. If GNU_LOG_LEVEL environment variable is set, use it (only when level is default)
    3. Default is LogLevel.INFO if neither is specified

    Args:
        log_file: Name of the log file (without extension) or full path
        rotation_config: Configuration for log rotation and compression
        format_string: Custom format string for log messages
        level: Minimum log level to capture (takes priority over GNU_LOG_LEVEL env var if explicitly set)
        log_path: Base directory for log files (defaults to ./logs)
        log_verbose: Whether to show debug logs and full error traces

    Returns:
        loguru.Logger: Configured logger instance

    Raises:
        ValueError: If log_file parameter is invalid
        OSError: If log directory cannot be created or accessed

    Example:
        ```python
        from general_utils.utils.log_common import build_logger, LogRotationConfig
        import os

        # Basic usage - will use GNU_LOG_LEVEL env var if set, otherwise INFO
        logger = build_logger("api")
        logger.info("Application started")

        # Parameter takes priority over environment variable
        os.environ['GNU_LOG_LEVEL'] = 'DEBUG'
        logger = build_logger("api", level="WARNING")  # Will use WARNING (parameter priority)

        # Environment variable used when parameter is default
        logger = build_logger("api")  # Will use DEBUG from env var

        # With custom rotation and path
        rotation_config = LogRotationConfig(
            max_file_size="10 MB",
            backup_count=5,
            compression="gz"
        )
        logger = build_logger(
            "detailed_api",
            rotation_config=rotation_config,
            log_path="/var/log/myapp",
            log_verbose=False
        )
        logger.info("<green>Enhanced logging enabled</green>")
        ```

    """
    if not log_file or not isinstance(log_file, str):
        raise ValueError("log_file must be a non-empty string")

    # Check if level is the default value
    is_default_level = level == LogLevel.INFO

    # Determine effective log level based on parameter priority and environment variable
    effective_level = _get_effective_log_level(level, is_default_level)

    # Set default log path if not provided
    if log_path is None:
        log_path = Path.cwd() / "logs"
    elif isinstance(log_path, str):
        log_path = Path(log_path)

    # Update global verbose setting and log level for filter
    global _log_verbose_global, _log_level_global
    _log_verbose_global = log_verbose
    _log_level_global = (
        effective_level
        if isinstance(effective_level, LogLevel)
        else LogLevel[effective_level.upper()]
    )

    # Set up rotation configuration
    if rotation_config is None:
        rotation_config = LogRotationConfig()

    # Set up format string
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Convert effective_level to string if it's an enum
    if isinstance(effective_level, LogLevel):
        effective_level = effective_level.name

    # Ensure log manager is initialized and setup log directory
    log_manager = LogManager()
    validated_log_path = log_manager._setup_log_directory(log_path)

    logger = loguru.logger

    # Remove default handler and add console handler with proper filter and level
    logger.remove()
    logger.add(
        sys.stderr,
        format=format_string,
        level=effective_level,
        filter=_filter_logs,
        colorize=True,
    )

    # Add backward compatibility aliases
    if not hasattr(logger, "warn"):
        logger.warn = logger.warning

    # Set up file logging if requested
    if log_file:
        log_file_path = _prepare_log_file_path(log_file, validated_log_path)

        # Set up rotation parameters
        rotation = rotation_config.max_file_size
        if rotation_config.rotation_time:
            rotation = rotation_config.rotation_time

        # Add file handler with rotation and compression
        logger.add(
            log_file_path,
            format=format_string,
            level=effective_level,
            rotation=rotation,
            retention=rotation_config.backup_count,
            compression=_get_compression_function(rotation_config.compression),
            colorize=False,
            filter=_filter_logs,
            backtrace=True,
            diagnose=True,
            enqueue=True,  # Thread-safe logging
        )

    return logger


def _prepare_log_file_path(log_file: str, base_log_path: Path) -> Path:
    """
    Prepare and validate log file path.

    Args:
        log_file: Log file name or path
        base_log_path: Base directory for log files

    Returns:
        Path: Resolved log file path

    Raises:
        OSError: If path cannot be created or accessed

    """
    if not log_file.endswith(".log"):
        log_file = f"{log_file}.log"

    if not os.path.isabs(log_file):
        log_path = base_log_path / log_file
    else:
        log_path = Path(log_file)

    # Ensure parent directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    return log_path


def _get_compression_function(compression: Optional[str]):
    """
    Get appropriate compression function based on format.

    Args:
        compression: Compression format ("gz", "zip", or None)

    Returns:
        Compression function or format string

    """
    if compression == "gz":
        return "gz"
    elif compression == "zip":
        return "zip"
    else:
        return None


# Legacy functions for backward compatibility


class LoggerNameFilter(logging.Filter):
    """Legacy filter class for backward compatibility with standard logging."""

    def filter(self, record):
        """
        Filter log records (legacy compatibility).

        Args:
            record: Log record to filter

        Returns:
            bool: Always True for backward compatibility

        """
        return True


def get_timestamp_ms():
    """
    Get current timestamp in milliseconds.

    Returns:
        int: Current timestamp in milliseconds

    """
    t = time.time()
    return int(round(t * 1000))


def get_log_file(log_path: str, sub_dir: str):
    """
    Create log file path with subdirectory (legacy function).

    Args:
        log_path: Base log directory path
        sub_dir: Subdirectory name (should contain timestamp)

    Returns:
        str: Full path to log file

    Raises:
        OSError: If directory cannot be created

    Note:
        This function is deprecated. Use LogManager and build_logger instead.

    """
    log_dir = os.path.join(log_path, sub_dir)
    # Here should be creating a new directory each time, so `exist_ok=False`
    os.makedirs(log_dir, exist_ok=False)
    return os.path.join(log_dir, f"{sub_dir}.log")


def get_config_dict(
    log_level: str, log_file_path: str, log_backup_count: int, log_max_bytes: int
) -> dict:
    """
    Generate logging configuration dictionary for standard Python logging.

    This function creates a configuration dictionary compatible with Python's
    standard logging.config.dictConfig() for applications that need to use
    the standard logging framework instead of loguru.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file_path: Path to the log file
        log_backup_count: Number of backup files to keep during rotation
        log_max_bytes: Maximum file size in bytes before rotation

    Returns:
        dict: Configuration dictionary for logging.config.dictConfig()

    Note:
        This function is provided for backward compatibility. For new projects,
        consider using build_logger() with LogRotationConfig instead.

    Example:
        ```python
        import logging.config
        from general_utils.utils.log_common import get_config_dict

        config = get_config_dict(
            log_level="INFO",
            log_file_path="/var/log/app.log",
            log_backup_count=5,
            log_max_bytes=10*1024*1024  # 10MB
        )
        logging.config.dictConfig(config)
        logger = logging.getLogger("chatchat_core")
        ```

    """
    # for windows, the path should be a raw string.
    log_file_path = (
        log_file_path.encode("unicode-escape").decode()
        if os.name == "nt"
        else log_file_path
    )
    log_level = log_level.upper()
    config_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "formatter": {
                "format": (
                    "%(asctime)s %(name)-12s %(process)d %(levelname)-8s %(message)s"
                )
            },
        },
        "filters": {
            "logger_name_filter": {
                "()": __name__ + ".LoggerNameFilter",
            },
        },
        "handlers": {
            "stream_handler": {
                "class": "logging.StreamHandler",
                "formatter": "formatter",
                "level": log_level,
            },
            "file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "formatter",
                "level": log_level,
                "filename": log_file_path,
                "mode": "a",
                "maxBytes": log_max_bytes,
                "backupCount": log_backup_count,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "chatchat_core": {
                "handlers": ["stream_handler", "file_handler"],
                "level": log_level,
                "propagate": False,
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["stream_handler", "file_handler"],
        },
    }
    return config_dict
