# Base image: Python 3.12 (matches your code's needs)
FROM python:3.12-slim

# # Install libpq-dev for psycopg to work (Postgres client library)
# RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Set working dir
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run app (matches your main.py)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]