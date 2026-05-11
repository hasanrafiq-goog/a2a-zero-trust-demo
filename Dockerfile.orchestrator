# Dockerfile for Orchestrator Agent
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=True
ENV PORT=8080
# Ensure /app is in the python path
ENV PYTHONPATH=/app

# Expose the port for the ADK UI
EXPOSE 8080

# Command to run the ADK Web Server
# Removing the explicit "orchestrator_agent" argument so it scans the current directory (/app) for all agents.
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8080"]
