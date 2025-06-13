"""Performance test harness for RAG API endpoint."""

from locust import HttpUser, between, task

class RAGUser(HttpUser):  # type: ignore
    """User class for RAG API performance testing."""

    wait_time = between(0.1, 0.1)
    host = "http://localhost:8000"

    @task
    def query_rag(self):
        """Test RAG query endpoint with sample query."""
        self.client.post("/rag/query", json={"query": "What is the platform architecture?"})
