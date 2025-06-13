"""A2A adapters for SocialIntelligence Agent."""

from datetime import datetime
from typing import Any, Dict

class YouTubeNicheScoutAdapter:
    """Adapter for YouTube Niche Scout A2A integration"""

    @staticmethod
    def envelope_to_payload(envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Convert A2A envelope to Niche Scout payload"""
        content = envelope.get("data", {}) or envelope.get("content", {})

        return {
            "queries": content.get(
                "queries",
                [
                    "nursery rhymes",
                    "diy woodworking",
                    "urban gardening",
                    "ai news",
                    "budget travel",
                ],
            ),
            "run_id": content.get("run_id", f"niche_scout_{datetime.utcnow().isoformat()}"),
        }

    @staticmethod
    def payload_to_envelope(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Niche Scout result to A2A envelope"""
        return {
            "trending_niches": payload.get("trending_niches", []),
            "top_niches": payload.get("top_niches", []),
            "digest": payload.get("digest", ""),
            "timestamp": payload.get("timestamp", datetime.utcnow().isoformat()),
        }

class YouTubeBlueprintAdapter:
    """Adapter for YouTube Blueprint A2A integration"""

    @staticmethod
    def envelope_to_payload(envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Convert A2A envelope to Blueprint payload"""
        content = envelope.get("data", {}) or envelope.get("content", {})

        return {
            "seed_url": content.get("seed_url"),
            "auto_niche": content.get("auto_niche", False),
            "run_id": content.get("run_id", f"blueprint_{datetime.utcnow().isoformat()}"),
        }

    @staticmethod
    def payload_to_envelope(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Blueprint result to A2A envelope"""
        return {
            "seed_url": payload.get("seed_url", ""),
            "top_channels": payload.get("top_channels", []),
            "gap_analysis": payload.get("gap_analysis", []),
            "blueprint": payload.get("blueprint", {}),
            "blueprint_url": payload.get("blueprint_url", ""),
            "timestamp": payload.get("timestamp", datetime.utcnow().isoformat()),
        }

def map_intent_to_adapter(intent: str):
    """Map intent to appropriate adapter"""
    adapters = {
        "YOUTUBE_NICHE_SCOUT": YouTubeNicheScoutAdapter,
        "YOUTUBE_BLUEPRINT": YouTubeBlueprintAdapter,
    }

    return adapters.get(intent)
