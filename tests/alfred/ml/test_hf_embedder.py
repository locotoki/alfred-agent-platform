"""Tests for the HuggingFace transformer embedder."""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from alfred.ml.hf_embedder import HFEmbedder

class TestHFEmbedder:
    """Test HuggingFace transformer embedder functionality."""

    @pytest.fixture
    def embedder(self):
        """Create an embedder instance."""
        return HFEmbedder(device="cpu", batch_size=8)

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer class."""
        with patch("alfred.ml.hf_embedder.SentenceTransformer") as mock:
            mock_model = Mock()
            mock_model.encode.return_value = np.random.rand(5, 384)
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.max_seq_length = 512
            mock.return_value = mock_model
            yield mock

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_initialization(self, embedder):
        """Test embedder initialization."""
        assert embedder.model_name == "all-MiniLM-L6-v2"
        assert embedder.device == "cpu"
        assert embedder.batch_size == 8
        assert embedder._model is None  # Lazy loading

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_custom_model_initialization(self):
        """Test initialization with custom model."""
        embedder = HFEmbedder(model_name="bert-base-uncased", device="cuda", batch_size=16)
        assert embedder.model_name == "bert-base-uncased"
        assert embedder.device == "cuda"
        assert embedder.batch_size == 16

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_lazy_model_loading(self, embedder, mock_sentence_transformer):
        """Test that model is loaded lazily on first use."""
        # Model should not be loaded yet
        assert embedder._model is None

        # Access model property
        model = embedder.model

        # Model should now be loaded
        assert model is not None
        mock_sentence_transformer.assert_called_once_with(
            "all-MiniLM-L6-v2", device="cpu", cache_folder=HFEmbedder.CACHE_DIR
        )

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_embed_single_text(self, embedder, mock_sentence_transformer):
        """Test embedding a single text."""
        text = "This is a test alert message"
        mock_model = mock_sentence_transformer.return_value
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])

        embedding = embedder.embed(text)

        # Should return 1D array for single text
        assert embedding.shape == (3,)
        np.testing.assert_array_equal(embedding, [0.1, 0.2, 0.3])

        # Check encoding was called correctly
        mock_model.encode.assert_called_once_with(
            [text], batch_size=8, show_progress_bar=False, convert_to_numpy=True
        )

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_embed_multiple_texts(self, embedder, mock_sentence_transformer):
        """Test embedding multiple texts."""
        texts = ["First alert", "Second alert", "Third alert"]
        mock_model = mock_sentence_transformer.return_value
        expected_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])
        mock_model.encode.return_value = expected_embeddings

        embeddings = embedder.embed(texts)

        # Should return 2D array for multiple texts
        assert embeddings.shape == (3, 3)
        np.testing.assert_array_equal(embeddings, expected_embeddings)

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_text_cleaning(self, embedder):
        """Test text cleaning functionality."""
        # Test whitespace handling
        assert embedder._clean_text("  text  with  spaces  ") == "text with spaces"

        # Test newline and tab removal
        assert (
            embedder._clean_text("text\nwith\nnewlines\tand\ttabs") == "text with newlines and tabs"
        )

        # Test long text truncation
        long_text = "x" * 600
        cleaned = embedder._clean_text(long_text)
        assert len(cleaned) == 515  # 512 + "..."
        assert cleaned.endswith("...")

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_cosine_similarity(self, embedder):
        """Test cosine similarity calculation."""
        # Test identical vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        assert embedder.cosine_similarity(vec1, vec2) == 1.0

        # Test orthogonal vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        assert embedder.cosine_similarity(vec1, vec2) == 0.0

        # Test opposite vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])
        assert embedder.cosine_similarity(vec1, vec2) == 0.0  # Clipped to 0

        # Test with zero vector
        vec1 = np.array([0.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        assert embedder.cosine_similarity(vec1, vec2) == 0.0

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_batch_similarity(self, embedder):
        """Test batch similarity calculation."""
        query = np.array([1.0, 0.0, 0.0])
        candidates = np.array(
            [
                [1.0, 0.0, 0.0],  # Identical
                [0.0, 1.0, 0.0],  # Orthogonal
                [0.7071, 0.7071, 0.0],  # 45 degrees
                [-1.0, 0.0, 0.0],  # Opposite
            ]
        )

        similarities = embedder.batch_similarity(query, candidates)

        assert len(similarities) == 4
        assert similarities[0] == 1.0  # Identical
        assert similarities[1] == 0.0  # Orthogonal
        assert 0.7 < similarities[2] < 0.8  # 45 degrees
        assert similarities[3] == 0.0  # Opposite (clipped)

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_batch_similarity_edge_cases(self, embedder):
        """Test batch similarity with edge cases."""
        # Empty candidates
        query = np.array([1.0, 0.0, 0.0])
        candidates = np.array([]).reshape(0, 3)
        similarities = embedder.batch_similarity(query, candidates)
        assert len(similarities) == 0

        # Zero candidates
        candidates = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        similarities = embedder.batch_similarity(query, candidates)
        assert len(similarities) == 2
        assert all(s == 0.0 for s in similarities)

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_warmup(self, embedder, mock_sentence_transformer):
        """Test model warmup."""
        embedder.warmup()

        # Model should be loaded
        assert embedder._model is not None
        mock_sentence_transformer.assert_called_once()

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_get_model_info(self, embedder, mock_sentence_transformer):
        """Test getting model information."""
        mock_model = mock_sentence_transformer.return_value
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.max_seq_length = 512

        info = embedder.get_model_info()

        assert info["model_name"] == "all-MiniLM-L6-v2"
        assert info["device"] == "cpu"
        assert info["batch_size"] == 8
        assert info["embedding_dimension"] == 384
        assert info["max_seq_length"] == 512

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_embedding_consistency(self, embedder, mock_sentence_transformer):
        """Test that same text produces same embedding."""
        text = "Consistent test message"
        mock_model = mock_sentence_transformer.return_value
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])

        embedding1 = embedder.embed(text)
        embedding2 = embedder.embed(text)

        np.testing.assert_array_equal(embedding1, embedding2)

        # Model encode should be called twice
        assert mock_model.encode.call_count == 2

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_batch_processing(self, embedder, mock_sentence_transformer):
        """Test that batch processing works correctly."""
        texts = ["Alert " + str(i) for i in range(100)]
        mock_model = mock_sentence_transformer.return_value
        mock_model.encode.return_value = np.random.rand(100, 384)

        embeddings = embedder.embed(texts)

        assert embeddings.shape == (100, 384)

        # Check batch size was passed correctly
        mock_model.encode.assert_called_once_with(
            texts, batch_size=8, show_progress_bar=False, convert_to_numpy=True
        )

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_error_handling(self, embedder):
        """Test error handling in embedder."""
        # Test with None input
        with pytest.raises(AttributeError):
            embedder.embed(None)

        # Test with empty text
        embedding = embedder.embed("")
        assert isinstance(embedding, np.ndarray)

        # Test with empty list
        embeddings = embedder.embed([])
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape[0] == 0

    @pytest.mark.parametrize("device", ["cpu", "cuda"])
    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_device_handling(self, device, mock_sentence_transformer):
        """Test handling of different devices."""
        embedder = HFEmbedder(device=device)
        _ = embedder.model

        mock_sentence_transformer.assert_called_once_with(
            "all-MiniLM-L6-v2", device=device, cache_folder=HFEmbedder.CACHE_DIR
        )

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_cache_directory(self, embedder):
        """Test cache directory configuration."""
        expected_cache = "~/.cache/huggingface"
        assert embedder.CACHE_DIR == expected_cache

    @pytest.mark.xfail(
        reason="Missing sentence_transformers dependency, see issue #220", strict=False
    )
    def test_numerical_stability(self, embedder):
        """Test numerical stability of similarity calculations."""
        # Very small vectors
        vec1 = np.array([1e-8, 1e-8, 1e-8])
        vec2 = np.array([1e-8, 1e-8, 1e-8])
        similarity = embedder.cosine_similarity(vec1, vec2)
        assert 0.99 < similarity <= 1.0

        # Mixed scale vectors
        vec1 = np.array([1e8, 1e-8, 1.0])
        vec2 = np.array([1e8, 1e-8, 1.0])
        similarity = embedder.cosine_similarity(vec1, vec2)
        assert similarity > 0.99
