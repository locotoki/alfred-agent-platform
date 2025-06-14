FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
COPY security/jwks.json /app/security/jwks.json
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
# Security: Run as non-root user
USER 1001
