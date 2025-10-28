from enum import Enum
from typing import Union


class LogLevel(Enum):
    """
    Enum for log levels to ensure type safety.

    Supports both integer values and string names for compatibility with
    environment variables and Pydantic settings.

    Examples:
        ```python
        # From integer
        level = LogLevel(20)  # INFO

        # From string name
        level = LogLevel.from_string("INFO")  # INFO
        level = LogLevel.from_string("info")  # INFO (case insensitive)

        # In Pydantic settings
        LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO)
        # Can be set via env var: LOG_LEVEL=DEBUG
        ```

    """

    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def from_string(cls, value: Union[str, int, "LogLevel"]) -> "LogLevel":
        """
        Create LogLevel from string, integer, or existing LogLevel.

        Args:
            value: String name (case insensitive), integer value, or LogLevel instance

        Returns:
            LogLevel: Corresponding log level

        Raises:
            ValueError: If the value is not a valid log level

        Examples:
            >>> LogLevel.from_string("DEBUG")
            <LogLevel.DEBUG: 10>
            >>> LogLevel.from_string("info")
            <LogLevel.INFO: 20>
            >>> LogLevel.from_string(20)
            <LogLevel.INFO: 20>

        """
        if isinstance(value, cls):
            return value

        if isinstance(value, int):
            try:
                return cls(value)
            except ValueError:
                valid_values = [level.value for level in cls]
                raise ValueError(
                    f"Invalid log level value: {value}. Valid values: {valid_values}"
                )

        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                valid_names = [level.name for level in cls]
                raise ValueError(
                    f"Invalid log level name: {value}. Valid names: {valid_names}"
                )

        raise ValueError(
            f"Invalid log level type: {type(value)}. Expected str, int, or LogLevel."
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """Customize Pydantic v2 JSON schema to accept string values."""
        json_schema = handler(core_schema)
        json_schema.update(
            type="string",
            enum=[level.name for level in cls],
            description="Log level - can be specified as string name (case insensitive) or integer value",
        )
        return json_schema

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """Pydantic v2 core schema."""
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(
            cls.validate, serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def validate(cls, value):
        """Pydantic validator that accepts strings, integers, or LogLevel instances."""
        return cls.from_string(value)

    def __str__(self) -> str:
        """Return the name of the log level."""
        return self.name

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"<LogLevel.{self.name}: {self.value}>"
