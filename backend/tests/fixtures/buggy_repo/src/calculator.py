"""
Calculator Service with deliberate division by zero bug.
"""

def divide(a: float, b: float) -> float:
    # BUG: No check for b == 0, causes unhandled ZeroDivisionError
    return a / b


def calculate_average(items: list[float]) -> float:
    # BUG: If items is empty, len(items) is 0 leading to division by zero
    total = sum(items)
    return divide(total, len(items))
