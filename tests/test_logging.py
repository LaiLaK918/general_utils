#!/usr/bin/env python3
"""
Test script for the enhanced logging functionality.
"""

import time

from general_utils.utils.log_common import LogLevel, LogRotationConfig, build_logger


def test_basic_logging():
    """Test basic logging functionality."""
    print("Testing basic logging...")

    logger = build_logger("test_basic", log_path="./logs")

    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.success("This is a success message")

    print("✓ Basic logging test completed")


def test_enhanced_logging():
    """Test enhanced logging with custom configuration."""
    print("Testing enhanced logging...")

    # Create rotation config
    rotation_config = LogRotationConfig(
        max_file_size="1 KB",  # Small size for testing
        backup_count=3,
        compression="gz",
    )

    logger = build_logger(
        "test_enhanced", rotation_config=rotation_config, log_path="./logs"
    )

    # Generate enough logs to trigger rotation
    for i in range(100):
        logger.info(f"Test message {i} - " + "x" * 10)
        if i % 20 == 0:
            time.sleep(0.1)  # Small delay

    print("✓ Enhanced logging test completed")


def test_log_levels():
    """Test different log levels."""
    print("Testing log levels...")

    logger = build_logger(
        "test_levels", level=LogLevel.INFO, log_path="./logs", log_verbose=True
    )

    logger.trace("This is a trace message")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    print("✓ Log levels test completed")


if __name__ == "__main__":
    print("Starting logging tests...")

    test_basic_logging()
    test_enhanced_logging()
    test_log_levels()

    print("\n✓ All tests completed successfully!")
    print("\nCheck the 'logs' directory for generated log files.")
