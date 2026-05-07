"""Calculator Agent for ADK web UI."""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import FunctionTool
from .tools import calculate, convert_units


# Create Calculator Agent
calculator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="calculator_agent",
    description="Calculator agent for math operations and unit conversions",
    instruction="""
You are a helpful calculator agent. You can:
1. Perform mathematical calculations using the 'calculate' tool
2. Convert between units using the 'convert_units' tool

When a user asks for a calculation, use the calculate tool with the expression.
When a user asks for unit conversion, use the convert_units tool with the value, from_unit, and to_unit.

Always provide clear and accurate results.
    """,
    tools=[
        FunctionTool(calculate),
        FunctionTool(convert_units),
    ]
)

# ADK expects a 'root_agent' variable
root_agent = calculator_agent
