import time
from functools import wraps

from .log_common import build_logger


def measure_execution_time(func=None, *, logger=None):
    """
    Decorator to measure the execution time of a function.

    Logs the time taken to execute the function using the provided logger
    or a default logger if none is provided.

    Args:
        func (callable, optional): The function to be decorated.
        logger (optional): Logger instance to use for logging. If None,
                          a default logger will be created.

    Returns:
        callable: The wrapped function that measures execution time.

    Example:
        ```python
        # Using default logger
        @measure_execution_time
        def my_function():
            # Function logic here
            pass

        # Using custom logger
        from general_utils.utils.log_common import build_logger
        custom_logger = build_logger("timing")

        @measure_execution_time(logger=custom_logger)
        def my_function():
            # Function logic here
            pass
        ```

    """

    def decorator(f):
        nonlocal logger
        if logger is None:
            logger = build_logger("timing")

        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = f(*args, **kwargs)
            end_time = time.time()
            logger.info(
                f"Function {f.__name__} took {end_time - start_time:.4f} seconds to execute"
            )
            return result

        return wrapper

    if func is None:
        # Called with arguments: @measure_execution_time(logger=...)
        return decorator
    else:
        # Called without arguments: @measure_execution_time
        return decorator(func)


def measure_execution_time_async(func=None, *, logger=None):
    """
    Decorator to measure the execution time of an asynchronous function.

    Logs the time taken to execute the function using the provided logger
    or a default logger if none is provided.

    Args:
        func (callable, optional): The asynchronous function to be decorated.
        logger (optional): Logger instance to use for logging. If None,
                          a default logger will be created.

    Returns:
        callable: The wrapped asynchronous function that measures execution time.

    Example:
        ```python
        # Using default logger
        @measure_execution_time_async
        async def my_async_function():
            # Asynchronous function logic here
            pass

        # Using custom logger
        from general_utils.utils.log_common import build_logger
        custom_logger = build_logger("timing")

        @measure_execution_time_async(logger=custom_logger)
        async def my_async_function():
            # Asynchronous function logic here
            pass
        ```

    """

    def decorator(f):
        nonlocal logger
        if logger is None:
            logger = build_logger("timing")

        @wraps(f)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await f(*args, **kwargs)
            end_time = time.time()
            logger.info(
                f"Function {f.__name__} took {end_time - start_time:.4f} seconds to execute"
            )
            return result

        return wrapper

    if func is None:
        # Called with arguments: @measure_execution_time_async(logger=...)
        return decorator
    else:
        # Called without arguments: @measure_execution_time_async
        return decorator(func)
