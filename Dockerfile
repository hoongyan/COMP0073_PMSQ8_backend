
FROM python:3.12-slim

# Set working dir
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run app 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]