"""
Test file to validate GitHub workflows and pre-commit hooks.

This file will be used to test:
- Pre-commit hooks (formatting, linting, type checking)
- CI workflows (test-and-coverage.yml)
- GitHub integration
"""


def hello_world(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


def add_numbers(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b


# Intentionally poor formatting to test pre-commit hooks
def poorly_formatted_function(x: int, y: int) -> int:
    return x * y


class TestClass:
    """A simple test class."""

    def __init__(self, value: int):
        self.value = value

    def get_value(self) -> int:
        """Get the stored value."""
        return self.value


if __name__ == "__main__":
    print(hello_world("World"))
    print(f"2 + 3 = {add_numbers(2, 3)}")
    test_obj = TestClass(42)
    print(f"Test value: {test_obj.get_value()}")
