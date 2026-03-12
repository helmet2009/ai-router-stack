FROM python:3.11-slim

WORKDIR /app

# Build context is the repo root
COPY router/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy router source files
COPY router/*.py .

# Copy crew package (multi-agent logic)
COPY crew/ ./crew/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
