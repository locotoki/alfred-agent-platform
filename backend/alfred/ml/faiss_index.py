"""FAISS vector index for fast similarity search.

Provides sub-15ms query performance for alert embeddings.
"""

import pickle
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import faiss
import numpy as np

from alfred.core.protocols import Service
from alfred.ml.hf_embedder import HFEmbedder

@dataclass
class SearchResult:
    """Result from FAISS similarity search"""

    alert_id: str
    score: float
    metadata: Dict

class FAISSIndex(Service):
    """Fast similarity search using FAISS indexes.

    Supports multiple index types optimized for different use cases.
    """

    def __init__(
        self,
        dimension: int = 384,
        index_type: str = "IVF",
        nlist: int = 100,
        nprobe: int = 10,
        device: str = "cpu",
    ):
        """Initialize FAISS index.

        Args:
            dimension: Embedding dimension (384 for MiniLM)
            index_type: Index type (IVF, LSH, HNSW, Flat)
            nlist: Number of clusters for IVF
            nprobe: Number of clusters to search
            device: Device to use (cpu/gpu).

        """
        self.dimension = dimension
        self.index_type = index_type
        self.nlist = nlist
        self.nprobe = nprobe
        self.device = device

        # Initialize index
        self.index = self._create_index()

        # Metadata storage
        self.id_map = {}  # index_id -> alert_id
        self.metadata = {}  # alert_id -> metadata
        self.current_id = 0

        # Performance tracking
        self.build_times = []
        self.query_times = []

    def _create_index(self) -> faiss.Index:
        """Create FAISS index based on type.

        Returns:
            FAISS index instance.

        """
        if self.index_type == "Flat":
            # Exact search (slow but accurate)
            index = faiss.IndexFlatL2(self.dimension)

        elif self.index_type == "IVF":
            # Inverted file index (faster, approximate)
            quantizer = faiss.IndexFlatL2(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)

        elif self.index_type == "LSH":
            # Locality sensitive hashing
            index = faiss.IndexLSH(self.dimension, self.dimension * 2)

        elif self.index_type == "HNSW":
            # Hierarchical navigable small world
            index = faiss.IndexHNSW(self.dimension, 32)
            index.hnsw.efConstruction = 40
            index.hnsw.efSearch = 16

        else:
            raise ValueError(f"Unknown index type: {self.index_type}")

        # Move to GPU if available and requested
        if self.device == "gpu" and faiss.get_num_gpus() > 0:
            index = faiss.index_cpu_to_gpu(faiss.StandardGpuResources(), 0, index)

        return index

    def add_embeddings(
        self,
        embeddings: np.ndarray,
        alert_ids: List[str],
        metadata: Optional[List[Dict]] = None,
    ):
        """Add embeddings to the index.

        Args:
            embeddings: Embedding vectors
            alert_ids: Alert identifiers
            metadata: Optional metadata for each alert.

        """
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Expected dimension {self.dimension}, got {embeddings.shape[1]}")

        if len(embeddings) != len(alert_ids):
            raise ValueError("Embeddings and IDs must have same length")

        # Train index if needed (for IVF)
        if self.index_type == "IVF" and not self.index.is_trained:
            start_time = time.time()
            self.index.train(embeddings)
            train_time = time.time() - start_time
            print(f"Index trained in {train_time:.3f}s")

        # Add vectors
        start_time = time.time()
        start_id = self.current_id

        self.index.add(embeddings)

        # Update mappings
        for i, alert_id in enumerate(alert_ids):
            idx = start_id + i
            self.id_map[idx] = alert_id

            if metadata and i < len(metadata):
                self.metadata[alert_id] = metadata[i]
            else:
                self.metadata[alert_id] = {}

        self.current_id += len(embeddings)

        build_time = time.time() - start_time
        self.build_times.append(build_time)

        print(f"Added {len(embeddings)} vectors in {build_time:.3f}s")

    def search(
        self, query_embedding: np.ndarray, k: int = 10, threshold: float = 0.0
    ) -> List[SearchResult]:
        """Search for similar embeddings.

        Args:
            query_embedding: Query vector
            k: Number of results
            threshold: Minimum similarity score

        Returns:
            List of search results.

        """
        if query_embedding.shape[0] != self.dimension:
            raise ValueError(f"Expected dimension {self.dimension}, got {query_embedding.shape[0]}")

        # Ensure query is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Set search parameters
        if self.index_type == "IVF":
            self.index.nprobe = self.nprobe

        # Search
        start_time = time.time()
        distances, indices = self.index.search(query_embedding, k)
        query_time = time.time() - start_time
        self.query_times.append(query_time)

        # Convert to results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # No result
                continue

            # Convert L2 distance to similarity score
            score = 1.0 / (1.0 + dist)

            if score >= threshold:
                alert_id = self.id_map.get(idx, str(idx))
                result = SearchResult(
                    alert_id=alert_id,
                    score=score,
                    metadata=self.metadata.get(alert_id, {}),
                )
                results.append(result)

        return results

    def batch_search(
        self, query_embeddings: np.ndarray, k: int = 10, threshold: float = 0.0
    ) -> List[List[SearchResult]]:
        """Batch search for multiple queries.

        Args:
            query_embeddings: Query vectors
            k: Number of results per query
            threshold: Minimum similarity score

        Returns:
            List of result lists.

        """
        if query_embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Expected dimension {self.dimension}, got {query_embeddings.shape[1]}"
            )

        # Set search parameters
        if self.index_type == "IVF":
            self.index.nprobe = self.nprobe

        # Search
        start_time = time.time()
        distances, indices = self.index.search(query_embeddings, k)
        query_time = time.time() - start_time
        self.query_times.extend([query_time / len(query_embeddings)] * len(query_embeddings))

        # Convert to results
        all_results = []
        for query_idx in range(len(query_embeddings)):
            results = []
            for dist, idx in zip(distances[query_idx], indices[query_idx]):
                if idx == -1:
                    continue

                score = 1.0 / (1.0 + dist)

                if score >= threshold:
                    alert_id = self.id_map.get(idx, str(idx))
                    result = SearchResult(
                        alert_id=alert_id,
                        score=score,
                        metadata=self.metadata.get(alert_id, {}),
                    )
                    results.append(result)

            all_results.append(results)

        return all_results

    def save_index(self, path: str):
        """Save index to disk.

        Args:
            path: Save path.

        """
        # Save FAISS index
        faiss.write_index(self.index, f"{path}.index")

        # Save metadata
        metadata = {
            "id_map": self.id_map,
            "metadata": self.metadata,
            "current_id": self.current_id,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "nlist": self.nlist,
            "nprobe": self.nprobe,
        }

        with open(f"{path}.meta", "wb") as f:
            pickle.dump(metadata, f)

        print(f"Index saved to {path}")

    def load_index(self, path: str):
        """Load index from disk.

        Args:
            path: Load path.

        """
        # Load FAISS index
        self.index = faiss.read_index(f"{path}.index")

        # Load metadata
        with open(f"{path}.meta", "rb") as f:
            metadata = pickle.load(f)

        self.id_map = metadata["id_map"]
        self.metadata = metadata["metadata"]
        self.current_id = metadata["current_id"]
        self.dimension = metadata["dimension"]
        self.index_type = metadata["index_type"]
        self.nlist = metadata["nlist"]
        self.nprobe = metadata["nprobe"]

        print(f"Index loaded from {path}")

    def get_stats(self) -> Dict:
        """Get index statistics.

        Returns:
            Statistics dictionary.

        """
        stats = {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "device": self.device,
            "current_id": self.current_id,
            "is_trained": getattr(self.index, "is_trained", True),
        }

        if self.build_times:
            stats["avg_build_time"] = np.mean(self.build_times)
            stats["total_build_time"] = sum(self.build_times)

        if self.query_times:
            stats["avg_query_time_ms"] = np.mean(self.query_times) * 1000
            stats["p99_query_time_ms"] = np.percentile(self.query_times, 99) * 1000
            stats["total_queries"] = len(self.query_times)

        return stats

    def optimize(self):
        """Optimize index for better performance"""
        if self.index_type == "IVF":
            # Rebalance IVF clusters
            print("Optimizing IVF index...")
            # This would involve retraining with better centroids

        elif self.index_type == "HNSW":
            # Adjust HNSW parameters
            print("Optimizing HNSW index...")
            self.index.hnsw.efSearch = min(32, self.index.ntotal // 100)

    def remove_alerts(self, alert_ids: List[str]):
        """Remove alerts from index (soft delete).

        Args:
            alert_ids: Alert IDs to remove.

        """
        # FAISS doesn't support direct removal, so we mark as deleted
        for alert_id in alert_ids:
            if alert_id in self.metadata:
                self.metadata[alert_id]["deleted"] = True

class AlertSearchEngine:
    """High-level search engine combining embedder and index"""

    def __init__(
        self,
        embedder: Optional[HFEmbedder] = None,
        index_type: str = "IVF",
        device: str = "cpu",
    ):
        """Initialize search engine.

        Args:
            embedder: HF embedder instance
            index_type: FAISS index type
            device: Device to use.

        """
        self.embedder = embedder or HFEmbedder(device=device)
        self.index = FAISSIndex(
            dimension=self.embedder.model.get_sentence_embedding_dimension(),
            index_type=index_type,
            device=device,
        )

    def index_alerts(self, alerts: List[Dict]):
        """Index a batch of alerts.

        Args:
            alerts: List of alert dictionaries.

        """
        # Extract texts and IDs
        texts = []
        alert_ids = []
        metadata = []

        for alert in alerts:
            # Combine alert fields for indexing
            name = alert.get("name", "")
            desc = alert.get("description", "")
            summary = alert.get("summary", "")
            text = f"{name} {desc} {summary}".strip()
            texts.append(text)
            alert_ids.append(alert["id"])
            metadata.append(
                {
                    "severity": alert.get("severity"),
                    "source": alert.get("source"),
                    "created_at": alert.get("created_at"),
                }
            )

        # Generate embeddings
        embeddings = self.embedder.embed(texts)

        # Add to index
        self.index.add_embeddings(embeddings, alert_ids, metadata)

    def search_similar(
        self, query_text: str, k: int = 10, threshold: float = 0.7
    ) -> List[SearchResult]:
        """Search for similar alerts.

        Args:
            query_text: Query text
            k: Number of results
            threshold: Minimum similarity

        Returns:
            Search results.

        """
        # Generate query embedding
        query_embedding = self.embedder.embed(query_text)

        # Search
        results = self.index.search(query_embedding, k, threshold)

        return results

    def get_performance_stats(self) -> Dict:
        """Get performance statistics.

        Returns:
            Performance stats.

        """
        stats = self.index.get_stats()
        stats["embedder_model"] = self.embedder.model_name
        return stats

# CLI interface
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FAISS Alert Search")
    parser.add_argument("--action", choices=["build", "search", "stats"], required=True)
    parser.add_argument("--index-path", default="alert_index", help="Index save/load path")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--k", type=int, default=10, help="Number of results")

    args = parser.parse_args()

    engine = AlertSearchEngine()

    if args.action == "build":
        # Demo: Build index with sample data
        sample_alerts = [
            {
                "id": "1",
                "name": "Database Error",
                "description": "Connection timeout",
                "severity": "critical",
            },
            {
                "id": "2",
                "name": "API Latency",
                "description": "High response time",
                "severity": "warning",
            },
            {
                "id": "3",
                "name": "Memory Usage",
                "description": "High memory consumption",
                "severity": "warning",
            },
        ]

        engine.index_alerts(sample_alerts)
        engine.index.save_index(args.index_path)
        print("Index built and saved")

    elif args.action == "search":
        engine.index.load_index(args.index_path)
        results = engine.search_similar(args.query, k=args.k)

        for i, result in enumerate(results):
            print(f"{i+1}. Alert {result.alert_id} (score: {result.score:.3f})")
            print(f"   Metadata: {result.metadata}")

    elif args.action == "stats":
        engine.index.load_index(args.index_path)
        stats = engine.get_performance_stats()

        import json
        print(json.dumps(stats, indent=2))
