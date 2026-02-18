# Use the same base
FROM python:3.11-slim

WORKDIR /app

# Install dependencies (keep your existing apt-get and pip lines here)
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything
COPY . .

# Set PYTHONPATH so 'src' is recognizable as a module
ENV PYTHONPATH=/app

# Updated CMD to ensure it finds the files
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port 8501 --server.address 0.0.0.0"]
