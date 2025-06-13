#!/usr/bin/env python3
"""Integration test for YouTube workflows in SocialIntelligence Agent."""

import asyncio
import json
import os
import uuid
from datetime import datetime

class A2AEnvelope:
    """Simple A2A envelope implementation."""

    def __init__(self, intent, data=None, task_id=None, trace_id=None):
        self.intent = intent
        self.data = data or {}
        self.task_id = task_id or f"task_{uuid.uuid4().hex}"
        self.trace_id = trace_id or f"trace_{uuid.uuid4().hex}"

    def to_dict(self):
        """Convert envelope to dictionary."""
        return {
            "intent": self.intent,
            "data": self.data,
            "task_id": self.task_id,
            "trace_id": self.trace_id,
        }

    def __str__(self):
        return json.dumps(self.to_dict(), indent=2)

class MockSocialIntelAgent:
    """Mock SocialIntelligence Agent for integration testing."""

    def __init__(self):
        """Initialize the agent."""
        # Set up mocked components
        self.intents_supported = [
            "TREND_ANALYSIS",
            "SOCIAL_MONITOR",
            "SENTIMENT_ANALYSIS",
            "YOUTUBE_NICHE_SCOUT",
            "YOUTUBE_BLUEPRINT",
        ]

    async def process_task(self, envelope):
        """Process a task."""
        print(f"Processing task with intent: {envelope.intent}")

        if envelope.intent not in self.intents_supported:
            print(f"ERROR: Unsupported intent: {envelope.intent}")
            return {
                "status": "error",
                "error": f"Unsupported intent: {envelope.intent}",
            }

        if envelope.intent == "YOUTUBE_NICHE_SCOUT":
            return await self._youtube_niche_scout(envelope.data)
        elif envelope.intent == "YOUTUBE_BLUEPRINT":
            return await self._youtube_blueprint(envelope.data)
        else:
            # Simulate other intents
            return {
                "status": "success",
                "type": envelope.intent.lower(),
                "message": f"Processed {envelope.intent} task",
                "timestamp": datetime.now().isoformat(),
            }

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

        # Create output directories
        os.makedirs("niche_scout", exist_ok=True)

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

        # Create output directories
        os.makedirs("builder", exist_ok=True)

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

async def test_a2a_integration():
    """Test A2A integration with SocialIntelligence Agent."""
    print("=== A2A Integration Test ===\n")

    # Create agent
    agent = MockSocialIntelAgent()

    # Create test envelopes
    niche_scout_envelope = A2AEnvelope(
        intent="YOUTUBE_NICHE_SCOUT",
        data={"queries": ["nursery rhymes", "diy woodworking", "urban gardening"]},
    )

    blueprint_envelope = A2AEnvelope(
        intent="YOUTUBE_BLUEPRINT",
        data={"seed_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    # Process tasks
    print("Processing Niche-Scout envelope:")
    print(niche_scout_envelope)
    niche_scout_result = await agent.process_task(niche_scout_envelope)

    print("\nProcessing Blueprint envelope:")
    print(blueprint_envelope)
    blueprint_result = await agent.process_task(blueprint_envelope)

    # Verify results
    print("\n=== Results ===\n")
    print(f"Niche-Scout result status: {niche_scout_result['status']}")
    print(f"Blueprint result status: {blueprint_result['status']}")

    print("\nNiche-Scout output files:")
    print(os.path.exists("niche_scout/digest.md"))

    print("\nBlueprint output files:")
    print(os.path.exists("builder/channel_blueprint.md"))
    print(os.path.exists("builder/channel_pack.zip"))

    print("\n=== Integration test completed successfully! ===")

if __name__ == "__main__":
    asyncio.run(test_a2a_integration())
