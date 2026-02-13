# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some compiled python packages)
RUN apt-get update && apt-get install -y gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port for FastAPI (Ingestion Engine)
EXPOSE 8000

# Define environment variable for unbuffered logs
ENV PYTHONUNBUFFERED=1

# Command to run the application
# We run the ingestion engine by default, or main.py for the agent.
# Let's use a startup script or default to ingestion engine as the long-running service,
# while the agent (main.py) might be a job or a separate interaction endpoint.
# Given main.py uses stdio for interaction in the demo, we'll keep it as the entrypoint for "Agent Mode"
# but typically a production app would run the API.
# Let's run the Ingestion API as the primary service.
CMD ["uvicorn", "src.ingestion_engine:app", "--host", "0.0.0.0", "--port", "8000"]
