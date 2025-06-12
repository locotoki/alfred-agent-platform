"""Tests for FAISS vector index."""

import os
import tempfile
from unittest.mock import Mock

import numpy as np
import pytest

from backend.alfred.ml.faiss_index import AlertSearchEngine, FAISSIndex, SearchResult

class TestFAISSIndex:
    """Test FAISS index functionality."""

    @pytest.fixture
    def index(self):
        """Create test index."""
        return FAISSIndex(dimension=10, index_type="Flat")

    @pytest.fixture
    def sample_embeddings(self):
        """Create sample embeddings."""
        np.random.seed(42)
        return np.random.randn(5, 10).astype(np.float32)

    @pytest.fixture
    def sample_ids(self):
        """Create sample IDs."""
        return ["alert1", "alert2", "alert3", "alert4", "alert5"]

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_initialization(self):
        """Test index initialization."""
        index = FAISSIndex(dimension=384, index_type="IVF", nlist=50)

        assert index.dimension == 384
        assert index.index_type == "IVF"
        assert index.nlist == 50
        assert index.nprobe == 10
        assert index.device == "cpu"
        assert index.current_id == 0

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_flat_index_creation(self):
        """Test Flat index creation."""
        index = FAISSIndex(dimension=128, index_type="Flat")
        assert index.index is not None
        assert index.index.d == 128

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_ivf_index_creation(self):
        """Test IVF index creation."""
        index = FAISSIndex(dimension=64, index_type="IVF", nlist=10)
        assert index.index is not None
        assert index.index.d == 64
        assert index.index.nlist == 10

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_lsh_index_creation(self):
        """Test LSH index creation."""
        index = FAISSIndex(dimension=32, index_type="LSH")
        assert index.index is not None
        assert index.index.d == 32

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_hnsw_index_creation(self):
        """Test HNSW index creation."""
        index = FAISSIndex(dimension=16, index_type="HNSW")
        assert index.index is not None
        assert index.index.d == 16

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_add_embeddings(self, index, sample_embeddings, sample_ids):
        """Test adding embeddings."""
        index.add_embeddings(sample_embeddings, sample_ids)

        assert index.index.ntotal == 5
        assert index.current_id == 5
        assert len(index.id_map) == 5

        # Check ID mapping
        for i, alert_id in enumerate(sample_ids):
            assert index.id_map[i] == alert_id

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_add_embeddings_with_metadata(self, index, sample_embeddings, sample_ids):
        """Test adding embeddings with metadata."""
        metadata = [
            {"severity": "high"},
            {"severity": "low"},
            {"severity": "medium"},
            {"severity": "high"},
            {"severity": "low"},
        ]

        index.add_embeddings(sample_embeddings, sample_ids, metadata)

        # Check metadata storage
        for alert_id, meta in zip(sample_ids, metadata):
            assert index.metadata[alert_id] == meta

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_add_embeddings_dimension_mismatch(self, index):
        """Test dimension mismatch error."""
        wrong_embeddings = np.random.randn(3, 20)  # Wrong dimension

        with pytest.raises(ValueError, match="Expected dimension"):
            index.add_embeddings(wrong_embeddings, ["id1", "id2", "id3"])

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_add_embeddings_length_mismatch(self, index, sample_embeddings):
        """Test length mismatch error."""
        wrong_ids = ["id1", "id2"]  # Too few IDs

        with pytest.raises(ValueError, match="same length"):
            index.add_embeddings(sample_embeddings, wrong_ids)

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_search(self, index, sample_embeddings, sample_ids):
        """Test similarity search."""
        index.add_embeddings(sample_embeddings, sample_ids)

        # Search with first embedding
        query = sample_embeddings[0]
        results = index.search(query, k=3)

        assert len(results) <= 3
        assert results[0].alert_id == "alert1"  # Should find itself
        assert results[0].score > 0.9  # High similarity

        # Check all results have required fields
        for result in results:
            assert hasattr(result, "alert_id")
            assert hasattr(result, "score")
            assert hasattr(result, "metadata")

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_search_with_threshold(self, index, sample_embeddings, sample_ids):
        """Test search with similarity threshold."""
        index.add_embeddings(sample_embeddings, sample_ids)

        query = sample_embeddings[0] + np.random.randn(10) * 0.1  # Slightly modified
        results = index.search(query, k=5, threshold=0.8)

        # All results should meet threshold
        for result in results:
            assert result.score >= 0.8

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_batch_search(self, index, sample_embeddings, sample_ids):
        """Test batch search."""
        index.add_embeddings(sample_embeddings, sample_ids)

        # Search with first two embeddings
        queries = sample_embeddings[:2]
        all_results = index.batch_search(queries, k=3)

        assert len(all_results) == 2

        # Check first query results
        assert all_results[0][0].alert_id == "alert1"
        assert all_results[1][0].alert_id == "alert2"

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_save_load_index(self, index, sample_embeddings, sample_ids):
        """Test saving and loading index."""
        metadata = [
            {"severity": "high"},
            {"severity": "low"},
            {"severity": "medium"},
            {"severity": "high"},
            {"severity": "low"},
        ]

        index.add_embeddings(sample_embeddings, sample_ids, metadata)

        # Save index
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "test_index")
            index.save_index(save_path)

            # Create new index and load
            new_index = FAISSIndex(dimension=10)
            new_index.load_index(save_path)

            # Verify loaded data
            assert new_index.index.ntotal == 5
            assert new_index.current_id == 5
            assert new_index.id_map == index.id_map
            assert new_index.metadata == index.metadata

            # Test search on loaded index
            results = new_index.search(sample_embeddings[0], k=3)
            assert results[0].alert_id == "alert1"

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_get_stats(self, index, sample_embeddings, sample_ids):
        """Test statistics collection."""
        index.add_embeddings(sample_embeddings, sample_ids)

        # Perform some searches
        for _ in range(10):
            index.search(sample_embeddings[0], k=5)

        stats = index.get_stats()

        assert stats["total_vectors"] == 5
        assert stats["dimension"] == 10
        assert stats["index_type"] == "Flat"
        assert "avg_query_time_ms" in stats
        assert "p99_query_time_ms" in stats
        assert stats["total_queries"] == 10

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_ivf_training(self):
        """Test IVF index training."""
        index = FAISSIndex(dimension=10, index_type="IVF", nlist=2)

        # Need to train IVF index
        embeddings = np.random.randn(20, 10).astype(np.float32)
        ids = [f"id{i}" for i in range(20)]

        index.add_embeddings(embeddings, ids)

        assert index.index.is_trained
        assert index.index.ntotal == 20

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_performance_benchmark(self, index):
        """Test query performance meets target."""
        # Add many vectors
        n_vectors = 10000
        embeddings = np.random.randn(n_vectors, 10).astype(np.float32)
        ids = [f"id{i}" for i in range(n_vectors)]

        index.add_embeddings(embeddings, ids)

        # Run multiple queries
        query = np.random.randn(10).astype(np.float32)
        query_times = []

        for _ in range(100):
            import time
            start = time.time()
            index.search(query, k=10)
            query_time = (time.time() - start) * 1000  # ms
            query_times.append(query_time)

        # Check P99 latency
        p99_latency = np.percentile(query_times, 99)
        assert p99_latency < 15  # Must be under 15ms

class TestAlertSearchEngine:
    """Test high-level search engine."""

    @pytest.fixture
    def mock_embedder(self):
        """Mock HF embedder."""
        embedder = Mock()
        embedder.model_name = "test-model"
        embedder.embed.return_value = np.random.randn(3, 384).astype(np.float32)

        # Mock model dimension
        model = Mock()
        model.get_sentence_embedding_dimension.return_value = 384
        embedder.model = model

        return embedder

    @pytest.fixture
    def engine(self, mock_embedder):
        """Create search engine."""
        return AlertSearchEngine(embedder=mock_embedder, index_type="Flat")

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine.embedder is not None
        assert engine.index is not None
        assert engine.index.dimension == 384

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_index_alerts(self, engine, mock_embedder):
        """Test indexing alerts."""
        alerts = [
            {
                "id": "1",
                "name": "DB Error",
                "description": "Connection lost",
                "severity": "high",
            },
            {
                "id": "2",
                "name": "API Slow",
                "description": "High latency",
                "severity": "medium",
            },
            {
                "id": "3",
                "name": "Disk Full",
                "description": "No space left",
                "severity": "critical",
            },
        ]

        engine.index_alerts(alerts)

        # Check embedder was called with correct texts
        mock_embedder.embed.assert_called_once()
        texts = mock_embedder.embed.call_args[0][0]
        assert len(texts) == 3
        assert "DB Error" in texts[0]
        assert "Connection lost" in texts[0]

        # Check index has vectors
        assert engine.index.index.ntotal == 3

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_search_similar(self, engine, mock_embedder):
        """Test similarity search."""
        # First index some alerts
        alerts = [
            {
                "id": "1",
                "name": "DB Error",
                "description": "Connection lost",
                "severity": "high",
            },
            {
                "id": "2",
                "name": "API Slow",
                "description": "High latency",
                "severity": "medium",
            },
        ]

        # Mock embeddings for indexing
        mock_embedder.embed.return_value = np.array(
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]  # First alert  # Second alert
        ).astype(np.float32)

        engine.index_alerts(alerts)

        # Mock query embedding - similar to first alert
        mock_embedder.embed.return_value = np.array([0.9, 0.1, 0.0]).astype(np.float32)

        results = engine.search_similar("database connection error", k=2)

        assert len(results) > 0
        # Results should be SearchResult objects
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.xfail(reason="Missing faiss dependency, see issue #220", strict=False)
    def test_get_performance_stats(self, engine):
        """Test performance statistics."""
        stats = engine.get_performance_stats()

        assert "total_vectors" in stats
        assert "dimension" in stats
        assert "embedder_model" in stats
        assert stats["embedder_model"] == "test-model"
