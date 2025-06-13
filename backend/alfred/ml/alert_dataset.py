"""Alert dataset loader with PII stripping.

Loads alert data from database and prepares for ML training.
"""

import hashlib
import re
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from alfred.core.protocols import Service

class AlertDataset(Service):
    """Loads and preprocesses alert data for ML training"""

    PII_PATTERNS = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),  # SSN
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "CREDIT_CARD"),  # Credit card
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL"),  # Email
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "PHONE"),  # Phone
        (
            r"\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
            "IP_ADDRESS",
        ),  # IP
    ]

    def __init__(self, source: str):
        """Initialize dataset loader.

        Args:
            source: Database URI or file path.

        """
        self.source = source
        self.is_database = source.startswith(("postgresql://", "mysql://", "sqlite://"))
        self.data = None
        self.features = None
        self.labels = None

    def load(self) -> pd.DataFrame:
        """Load data from source.

        Returns:
            DataFrame with alert data.

        """
        if self.is_database:
            engine = create_engine(self.source)
            query = text(
                """
                SELECT
                    id,
                    message,
                    source,
                    severity,
                    created_at,
                    metadata,
                    resolved,
                    false_positive
                FROM alerts
                WHERE created_at > NOW() - INTERVAL '30 days'
                LIMIT 100000
            """
            )
            df = pd.read_sql(query, engine)
        else:
            # Load from CSV
            df = pd.read_csv(self.source)

        # Strip PII
        df["message"] = df["message"].apply(self._strip_pii)

        self.data = df
        return df

    def _strip_pii(self, text: str) -> str:
        """Remove PII from text.

        Args:
            text: Input text

        Returns:
            Text with PII removed.

        """
        for pattern, pii_type in self.PII_PATTERNS:
            text = re.sub(pattern, f"[{pii_type}]", text)
        return text

    def extract_features(self) -> np.ndarray:
        """Extract feature vectors from alerts.

        Returns:
            Feature matrix.

        """
        if self.data is None:
            self.load()

        features = []

        for _, row in self.data.iterrows():
            # Message features
            msg_len = len(row["message"])
            msg_words = len(row["message"].split())
            has_error = 1 if "error" in row["message"].lower() else 0
            has_critical = 1 if "critical" in row["message"].lower() else 0

            # Severity features
            severity_map = {"critical": 4, "warning": 3, "info": 2, "debug": 1}
            severity_score = severity_map.get(row["severity"].lower(), 2)

            # Time features
            hour = row["created_at"].hour if hasattr(row["created_at"], "hour") else 12
            weekday = row["created_at"].weekday() if hasattr(row["created_at"], "weekday") else 3
            is_weekend = 1 if weekday >= 5 else 0
            is_business_hours = 1 if 9 <= hour <= 17 and weekday < 5 else 0

            # Source features
            source_hash = int(hashlib.md5(row["source"].encode()).hexdigest()[:8], 16) % 100

            feature_vec = [
                msg_len,
                msg_words,
                has_error,
                has_critical,
                severity_score,
                hour,
                weekday,
                is_weekend,
                is_business_hours,
                source_hash,
            ]

            features.append(feature_vec)

        self.features = np.array(features)
        return self.features

    def extract_labels(self) -> np.ndarray:
        """Extract labels for training.

        Returns:
            Label array (1 for noise, 0 for signal).

        """
        if self.data is None:
            self.load()

        # Label as noise if:
        # 1. Marked as false positive
        # 2. Resolved very quickly (< 5 minutes)
        # 3. Low severity and outside business hours

        labels = []

        for _, row in self.data.iterrows():
            is_noise = 0

            # Check false positive flag
            if row.get("false_positive", False):
                is_noise = 1

            # Check quick resolution
            if row.get("resolved", False) and "resolved_at" in row:
                resolution_time = (row["resolved_at"] - row["created_at"]).total_seconds()
                if resolution_time < 300:  # 5 minutes
                    is_noise = 1

            # Check low severity off-hours
            if row["severity"].lower() in ["info", "debug"]:
                hour = row["created_at"].hour if hasattr(row["created_at"], "hour") else 12
                weekday = (
                    row["created_at"].weekday() if hasattr(row["created_at"], "weekday") else 3
                )
                if hour < 9 or hour > 17 or weekday >= 5:
                    is_noise = 1

            labels.append(is_noise)

        self.labels = np.array(labels)
        return self.labels

    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for training.

        Returns:
            Features and labels.

        """
        X = self.extract_features()
        y = self.extract_labels()

        # Remove NaN values
        mask = ~np.isnan(X).any(axis=1)
        X = X[mask]
        y = y[mask]

        return X, y

    def get_info(self) -> Dict:
        """Get dataset information.

        Returns:
            Dataset metadata.

        """
        if self.data is None:
            self.load()

        if self.features is None:
            self.extract_features()

        if self.labels is None:
            self.extract_labels()

        return {
            "total_size": len(self.data),
            "feature_count": self.features.shape[1],
            "noise_ratio": self.labels.mean(),
            "severity_distribution": self.data["severity"].value_counts().to_dict(),
            "source_count": self.data["source"].nunique(),
            "time_range": {
                "start": (
                    self.data["created_at"].min().isoformat() if not self.data.empty else None
                ),
                "end": (self.data["created_at"].max().isoformat() if not self.data.empty else None),
            },
        }

    def split_by_time(self, test_days: int = 7) -> Tuple["AlertDataset", "AlertDataset"]:
        """Split dataset by time for temporal validation.

        Args:
            test_days: Number of recent days for test set

        Returns:
            Train and test datasets.

        """
        if self.data is None:
            self.load()

        cutoff_date = self.data["created_at"].max() - pd.Timedelta(days=test_days)

        train_data = self.data[self.data["created_at"] < cutoff_date].copy()
        test_data = self.data[self.data["created_at"] >= cutoff_date].copy()

        train_dataset = AlertDataset(self.source)
        train_dataset.data = train_data

        test_dataset = AlertDataset(self.source)
        test_dataset.data = test_data

        return train_dataset, test_dataset

# CLI interface for testing
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Alert Dataset Loader")
    parser.add_argument("--source", required=True, help="Database URI or CSV file")
    parser.add_argument("--info", action="store_true", help="Show dataset info")

    args = parser.parse_args()

    dataset = AlertDataset(args.source)

    if args.info:
        info = dataset.get_info()
        import json
        print(json.dumps(info, indent=2))
    else:
        X, y = dataset.prepare_training_data()
        print(f"Features shape: {X.shape}")
        print(f"Labels shape: {y.shape}")
        print(f"Noise ratio: {y.mean():.2%}")
