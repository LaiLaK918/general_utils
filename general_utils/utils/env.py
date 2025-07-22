import os


def get_env(name: str):
    """
    Get the value of an environment variable.

    If the variable is not set, raise an exception.
    :param name: The name of the environment variable.
    :return: The value of the environment variable, or None if it is not set.
    :raises KeyError: If the environment variable is not set.
    :raises ValueError: If the environment variable is set to an empty string.
    :raises TypeError: If the name is not a string.
    """
    if not isinstance(name, str):
        raise TypeError(f"Expected a string for name, got {type(name).__name__}")

    value = os.environ.get(name)
    if value is None:
        raise KeyError(f"Environment variable '{name}' is not set.")
    if value == "":
        raise ValueError(f"Environment variable '{name}' is set to an empty string.")

    return value
