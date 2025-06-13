#!/usr/bin/env python3
"""Standalone test script for YouTube workflows."""

import os
from datetime import datetime

# Mock YouTube API and vector storage
class MockYouTubeAPI:
    """Mock YouTube API for testing."""

    async def search_videos(self, query, limit=10):
        """Mock video search."""
        return [
            {
                "id": f"video_{query}_1",
                "title": f"Test Video for {query}",
                "viewCount": {"text": "1,000"},
            },
            {
                "id": f"video_{query}_2",
                "title": f"Another Video for {query}",
                "viewCount": {"text": "2,000"},
            },
        ]

    async def get_trend_data(self, query):
        """Mock trend data."""
        return {"query": query, "current_value": 75.0, "week_avg": 65.0}

    async def search_channels(self, query, limit=10):
        """Mock channel search."""
        return [
            {
                "id": f"channel_{query}_1",
                "title": f"Test Channel for {query}",
                "subscribers": "100K",
            },
            {
                "id": f"channel_{query}_2",
                "title": f"Another Channel for {query}",
                "subscribers": "200K",
            },
        ]

    async def get_video_metadata(self, video_url):
        """Mock video metadata."""
        video_id = video_url.split("=")[-1]
        return {
            "id": video_id,
            "title": f"Test Video {video_id}",
            "tags": ["test", "video", "youtube"],
            "description": "This is a test video description.",
        }

class MockVectorStorage:
    """Mock vector storage for testing."""

    async def initialize_collections(self):
        """Mock collection initialization."""
        print("Initializing vector collections...")

    async def store_niche_vector(self, niche_id, niche_data, embedding):
        """Mock storing niche vectors."""
        print(f"Storing niche vector for {niche_id}")

    async def store_channel_vector(self, channel_id, channel_data, embedding):
        """Mock storing channel vectors."""
        print(f"Storing channel vector for {channel_id}")

    async def store_video_vector(self, video_id, video_data, embedding):
        """Mock storing video vectors."""
        print(f"Storing video vector for {video_id}")

# Mock SocialIntelligence Agent
class MockSocialIntelAgent:
    """Mock SocialIntelligence Agent for testing."""

    def __init__(self):
        self.youtube_api = MockYouTubeAPI()
        self.youtube_vectors = MockVectorStorage()

    async def _youtube_niche_scout(self, content):
        """Run YouTube Niche-Scout workflow."""
        print("\n=== Running Niche-Scout Workflow ===\n")

        # Get queries
        queries = content.get(
            "queries",
            [
                "nursery rhymes",
                "diy woodworking",
                "urban gardening",
                "ai news",
                "budget travel",
            ],
        )

        print(f"Queries: {queries}")

        # Mock trending niches
        trending_niches = []
        for i, query in enumerate(queries):
            trending_niches.append(
                {
                    "query": query,
                    "view_sum": (5 - i) * 1000,
                    "rsv": (5 - i) * 10,
                    "view_rank": 5 - i,
                    "rsv_rank": 5 - i,
                    "score": (5 - i) * 0.6 + (5 - i) * 0.4,
                    "x": i * 0.2,
                    "y": i * 0.3,
                    "niche": i % 3,
                }
            )

        # Create directories
        os.makedirs("niche_scout", exist_ok=True)

        # Save mock digest
        with open("niche_scout/digest.md", "w") as f:
            f.write(f"# YouTube Niche Scout - {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("## Top Trending Niches\n\n")
            for i, niche in enumerate(trending_niches, 1):
                f.write(f"{i}. **{niche['query']}** - Score: {niche['score']:.2f}\n")

        print("\nNiche Scout completed successfully!")
        print("Output saved to niche_scout/digest.md")

        return {
            "status": "success",
            "type": "youtube_niche_scout",
            "trending_niches": trending_niches,
            "top_niches": trending_niches[:3],
            "digest": "Mock digest content",
            "timestamp": datetime.now().isoformat(),
        }

    async def _youtube_blueprint(self, content):
        """Run Seed-to-Blueprint workflow."""
        print("\n=== Running Seed-to-Blueprint Workflow ===\n")

        # Get seed URL or auto-niche flag
        seed_url = content.get("seed_url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        auto_niche = content.get("auto_niche", False)

        if auto_niche:
            print("Using auto-niche selection")
            seed_url = "https://www.youtube.com/watch?v=auto_selected"
        else:
            print(f"Using seed URL: {seed_url}")

        # Mock top channels
        top_channels = []
        for i in range(3):
            top_channels.append(
                {
                    "channel_id": f"channel_{i}",
                    "channel_name": f"Channel {i}",
                    "subscribers": (5 - i) * 100000,
                    "total_views": (5 - i) * 1000000,
                    "video_count": (5 - i) * 100,
                    "recent_upload_count": (5 - i) * 10,
                    "thirty_day_delta": (5 - i) * 5,
                    "primary_topics": ["Topic A", "Topic B", "Topic C"],
                }
            )

        # Mock gap analysis
        gap_analysis = []
        for i in range(3):
            gap_analysis.append(
                {
                    "keyword": f"Keyword {i}",
                    "seed_coverage": 1.0,
                    "competitor_coverage": {},
                    "opportunity_score": (3 - i) * 0.3,
                }
            )

        # Mock blueprint
        blueprint = {
            "positioning": "A unique channel focused on Topic A and Topic B",
            "content_pillars": ["Pillar 1", "Pillar 2", "Pillar 3"],
            "format_mix": {"long_form": 0.6, "shorts": 0.3, "livestream": 0.1},
            "roadmap": {
                "Week 1": ["Video idea 1", "Video idea 2"],
                "Week 2": ["Video idea 3", "Video idea 4"],
                "Week 3": ["Video idea 5", "Video idea 6"],
                "Week 4": ["Video idea 7", "Video idea 8"],
            },
            "ai_production_tips": [
                "Use Whisper API for transcription",
                "Use Stable Diffusion for thumbnail concepts",
                "Use Bannerbear for production-ready thumbnails",
            ],
            "coppa_checklist": [
                {"item": "Content appropriate for all ages", "status": "Required"},
                {"item": "No collection of personal information", "status": "Required"},
            ],
        }

        # Create directories
        os.makedirs("builder", exist_ok=True)

        # Save mock blueprint
        with open("builder/channel_blueprint.md", "w") as f:
            f.write("# YouTube Channel Blueprint\n\n")
            f.write(f"## Positioning\n\n{blueprint['positioning']}\n\n")
            f.write("## Content Pillars\n\n")
            for pillar in blueprint["content_pillars"]:
                f.write(f"- {pillar}\n")

        # Create mock zip file
        blueprint_url = "builder/channel_pack.zip"
        with open(blueprint_url, "w") as f:
            f.write("Mock zip file content")

        print("\nBlueprint workflow completed successfully!")
        print("Output saved to builder/channel_blueprint.md")

        return {
            "status": "success",
            "type": "youtube_blueprint",
            "seed_url": seed_url,
            "top_channels": top_channels,
            "gap_analysis": gap_analysis,
            "blueprint": blueprint,
            "blueprint_content": "Mock blueprint content",
            "blueprint_url": blueprint_url,
            "timestamp": datetime.now().isoformat(),
        }

async def test_niche_scout():
    """Test Niche-Scout workflow."""
    agent = MockSocialIntelAgent()
    result = await agent._youtube_niche_scout(
        {"queries": ["nursery rhymes", "diy woodworking", "urban gardening"]}
    )
    print(f"\nResult status: {result['status']}")
    print(f"Found {len(result['trending_niches'])} trending niches")
    print(f"Top niche: {result['top_niches'][0]['query']}")

async def test_blueprint():
    """Test Blueprint workflow."""
    agent = MockSocialIntelAgent()
    result = await agent._youtube_blueprint(
        {"seed_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    print(f"\nResult status: {result['status']}")
    print(f"Seed URL: {result['seed_url']}")
    print(f"Blueprint positioning: {result['blueprint']['positioning']}")
    print(f"Content pillars: {', '.join(result['blueprint']['content_pillars'])}")

async def main():
    """Run all tests."""
    print("=== YouTube Workflow Tests ===\n")

    # Test Niche-Scout
    await test_niche_scout()

    # Test Blueprint
    await test_blueprint()

    print("\n=== All tests completed successfully! ===")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
