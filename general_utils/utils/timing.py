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
            import inspect

            start_time = time.time()
            result = f(*args, **kwargs)
            end_time = time.time()
            import inspect
            import os
            import sys

            # Find the first frame in user's project
            module_path = None
            lineno = -1
            frame = inspect.currentframe()
            outer_frames = inspect.getouterframes(frame)
            project_file_path = "unknown"
            for frameinfo in outer_frames:
                fname = frameinfo.filename
                if "/general_utils/" in fname:
                    # Try to get module path from filename
                    for mod in sys.modules.values():
                        if hasattr(mod, "__file__") and mod.__file__:
                            if not (
                                mod.__file__.startswith("<") or fname.startswith("<")
                            ):
                                try:
                                    if os.path.samefile(mod.__file__, fname):
                                        module_path = mod.__name__
                                        break
                                except FileNotFoundError:
                                    continue
                    if not module_path:
                        rel_path = os.path.relpath(fname, start=os.getcwd())
                        module_path = rel_path.replace(os.sep, ".").rsplit(".", 1)[0]
                    lineno = frameinfo.lineno
                    # Add project file path (relative to current working directory)
                    project_file_path = os.path.relpath(fname, start=os.getcwd())
                    break
            if not module_path:
                module_path = "unknown"
            qualname = f.__qualname__ if hasattr(f, "__qualname__") else f.__name__
            logger.info(
                f"Function {module_path}.{qualname} called at {project_file_path}:{lineno} took {end_time - start_time:.4f} seconds to execute"
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
            import inspect

            start_time = time.time()
            result = await f(*args, **kwargs)
            end_time = time.time()
            import inspect
            import os
            import sys

            module_path = None
            lineno = -1
            frame = inspect.currentframe()
            outer_frames = inspect.getouterframes(frame)
            project_file_path = "unknown"
            for frameinfo in outer_frames:
                fname = frameinfo.filename
                if "/general_utils/" in fname:
                    for mod in sys.modules.values():
                        if hasattr(mod, "__file__") and mod.__file__:
                            if not (
                                mod.__file__.startswith("<") or fname.startswith("<")
                            ):
                                try:
                                    if os.path.samefile(mod.__file__, fname):
                                        module_path = mod.__name__
                                        break
                                except FileNotFoundError:
                                    continue
                    if not module_path:
                        rel_path = os.path.relpath(fname, start=os.getcwd())
                        module_path = rel_path.replace(os.sep, ".").rsplit(".", 1)[0]
                    lineno = frameinfo.lineno
                    project_file_path = os.path.relpath(fname, start=os.getcwd())
                    break
            if not module_path:
                module_path = "unknown"
            qualname = f.__qualname__ if hasattr(f, "__qualname__") else f.__name__
            logger.info(
                f"Function {module_path}.{qualname} called at {project_file_path}:{lineno} took {end_time - start_time:.4f} seconds to execute"
            )
            return result

        return wrapper

    if func is None:
        # Called with arguments: @measure_execution_time_async(logger=...)
        return decorator
    else:
        # Called without arguments: @measure_execution_time_async
        return decorator(func)


if __name__ == "__main__":
    # Example usage
    @measure_execution_time
    def example_function():
        time.sleep(1)  # Simulate a delay

    example_function()

    @measure_execution_time_async
    async def example_async_function():
        await asyncio.sleep(1)  # Simulate a delay

    import asyncio

    asyncio.run(example_async_function())
