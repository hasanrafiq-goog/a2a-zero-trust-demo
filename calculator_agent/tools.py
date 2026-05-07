"""Calculator Agent Tools."""

from google.adk.tools import ToolContext


def calculate(tool_context: ToolContext, expression: str) -> str:
    """
    Perform basic calculations.

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2", "10 * 5")

    Returns:
        Result of the calculation
    """
    try:
        # Using eval for simplicity - in production, use a proper parser
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"


def convert_units(tool_context: ToolContext, value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert between units.

    Args:
        value: Numeric value to convert
        from_unit: Source unit (celsius, fahrenheit, km, miles)
        to_unit: Target unit

    Returns:
        Converted value
    """
    conversions = {
        ('celsius', 'fahrenheit'): lambda x: (x * 9/5) + 32,
        ('fahrenheit', 'celsius'): lambda x: (x - 32) * 5/9,
        ('km', 'miles'): lambda x: x * 0.621371,
        ('miles', 'km'): lambda x: x * 1.60934,
    }

    key = (from_unit.lower(), to_unit.lower())
    if key in conversions:
        result = conversions[key](value)
        return f"{value} {from_unit} = {result:.2f} {to_unit}"
    else:
        return f"Conversion from {from_unit} to {to_unit} not supported"
