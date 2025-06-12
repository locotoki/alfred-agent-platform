"""Configuration settings for Alfred ML components"""

import os

class Settings:
    """Application settings with environment variable support"""

    # Database configuration
    ALERT_DB_URI: str = os.getenv(
        "ALERT_DB_URI", "sqlite:///./alerts.db"  # Default to local SQLite for testing
    )

    # ML configuration
    ML_MODEL_DIR: str = os.getenv("ML_MODEL_DIR", "/tmp/alfred-models")
    ML_BATCH_SIZE: int = int(os.getenv("ML_BATCH_SIZE", "32"))
    ML_TRAINING_DAYS: int = int(os.getenv("ML_TRAINING_DAYS", "30"))

    # Feature flags
    ENABLE_ML_TRAINING: bool = os.getenv("ENABLE_ML_TRAINING", "true").lower() == "true"

    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL with safety checks"""
        if not cls.ALERT_DB_URI:
            raise ValueError("ALERT_DB_URI environment variable not set")
        return cls.ALERT_DB_URI

# Singleton instance
settings = Settings()
