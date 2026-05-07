# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project code
COPY . .

# Set environment variables for Cloud Run
ENV PYTHONUNBUFFERED=True
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Run the calculator agent server
CMD ["python", "-m", "calculator_agent.server"]
