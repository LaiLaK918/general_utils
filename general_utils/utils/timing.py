import time
from functools import wraps


def measure_execution_time(func):
    """
    Decorator to measure the execution time of a function.

    Prints the time taken to execute the function.

    Args:
        func (callable): The function to be decorated.

    Returns:
        callable: The wrapped function that measures execution time.

    Example:
        ```python
        @measure_execution_time
        def my_function():
            # Function logic here
            pass
        ```

    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(
            f"Function {func.__name__} took {end_time - start_time:.4f} seconds to execute"
        )
        return result

    return wrapper
