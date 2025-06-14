FROM python:3.12-slim
WORKDIR /app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src .
CMD ["python", "-m", "hubspot_mock"]

# Security: Run as non-root user
USER 1001
