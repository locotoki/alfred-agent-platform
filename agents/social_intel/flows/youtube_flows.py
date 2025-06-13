"""Prefect flows for YouTube workflows in SocialIntelligence Agent"""

# asyncio module is used via methods like asyncio.sleep
import asyncio
import json
import os
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
import sklearn.cluster as skc
import structlog
import umap
from prefect import flow, get_run_logger, task
from prefect.utilities.asyncutils import sync_compatible
from sentence_transformers import SentenceTransformer

from ..models.youtube_api import YouTubeAPI
from ..models.youtube_models import (
    
,
    BlueprintResult,
    NicheScoutResult,
    YouTubeBlueprint,
    YouTubeChannel,
    YouTubeGap,
    YouTubeNiche,
)
from ..models.youtube_vectors import YouTubeVectorStorage

logger = structlog.get_logger(__name__)
# Initialize sentence transformer for embeddings
@task(name="initialize_sentence_transformer")
def initialize_sentence_transformer():
    """Initialize the sentence transformer model for embeddings"""
    return SentenceTransformer("all-MiniLM-L6-v2")

# --- Niche Scout Flow Tasks ---

@task(name="harvest_youtube_signals")
async def harvest_youtube_signals(queries: List[str]) -> pd.DataFrame:
    """Harvest signals from YouTube and Google Trends"""
    youtube_api = YouTubeAPI()  # Used for API calls
    rows = []
    today = datetime.now().date().isoformat()

    for q in queries:
        # Get videos for this query
        videos = await youtube_api.search_videos(q, limit=100)

        # Calculate total views
        view_sum = sum(
            (
                int(v.get("viewCount", {}).get("text", "0").replace(",", ""))
                if isinstance(v.get("viewCount"), dict)
                else 0
            )
            for v in videos
        )

        # Get trend data
        trend_data = await youtube_api.get_trend_data(q)
        rsv = trend_data["current_value"] if trend_data else 0

        # Add to results
        rows.append((today, q, view_sum, rsv))

        # Sleep to avoid rate limiting
        await asyncio.sleep(1)

    # Create DataFrame
    df = pd.DataFrame(rows, columns=["date", "query", "view_sum", "rsv"])

    # Store in DuckDB for persistence
    duckdb.sql("CREATE TABLE IF NOT EXISTS signals(date, query, view_sum, rsv)")
    duckdb.sql("INSERT INTO signals VALUES (?, ?, ?, ?)", rows)

    return df

@task(name="score_cluster_niches")
def score_cluster_niches(signals_df: pd.DataFrame) -> pd.DataFrame:
    """Score and cluster the niches"""
    # Get latest date data
    latest = signals_df[signals_df.date == signals_df.date.max()].copy()

    # Rank niches
    latest["view_rank"] = latest.view_sum.rank(ascending=False)
    latest["rsv_rank"] = latest.rsv.rank(ascending=False)

    # Calculate combined score (weighted)
    latest["score"] = 0.6 * latest["view_rank"] + 0.4 * latest["rsv_rank"]

    # Create UMAP embeddings for visualization and clustering
    embeddings = umap.UMAP(n_components=2, random_state=42).fit_transform(
        pd.get_dummies(latest["query"])
    )

    latest[["x", "y"]] = embeddings

    # Cluster similar niches
    n_clusters = min(10, len(latest))
    if n_clusters > 1:  # Ensure we have enough data to cluster
        clusters = skc.KMeans(n_clusters=n_clusters).fit(embeddings)
        latest["niche"] = clusters.labels_
    else:
        latest["niche"] = 0

    # Save to CSV
    os.makedirs("niche_scout", exist_ok=True)
    latest.to_csv("niche_scout/trending_niches.csv", index=False)

    return latest

@task(name="store_niche_vectors")
async def store_niche_vectors(
    niches_df: pd.DataFrame, vector_storage: YouTubeVectorStorage, sentence_transformer
):
    """Store niche vectors in the vector database"""
    # Generate embeddings
    niche_texts = [
        f"YouTube niche: {row.query}. Views: {row.view_sum}. Trend score: {row.rsv}"
        for _, row in niches_df.iterrows()
    ]

    niche_embeddings = sentence_transformer.encode(niche_texts)

    # Store vectors
    for i, (_, niche) in enumerate(niches_df.iterrows()):
        niche_id = f"niche_{niche.query.replace(' ', '_').lower()}_{uuid.uuid4().hex[:8]}"

        # Convert to dict for storage
        niche_data = niche.to_dict()

        # Store in Qdrant
        await vector_storage.store_niche_vector(niche_id, niche_data, niche_embeddings[i])

    logger.info("niche_vectors_stored", count=len(niches_df))

@task(name="generate_niche_scout_digest")
def generate_niche_scout_digest(trending_niches: pd.DataFrame) -> str:
    """Generate a digest of the top niches"""
    # Sort by score and get top 10
    top_niches = trending_niches.sort_values("score", ascending=False).head(10)

    # Create summary text
    summary = [
        f"# YouTube Niche Scout - {datetime.now().strftime('%Y-%m-%d')}\n\n",
        "## Top 10 Trending Niches\n\n",
    ]

    for i, (_, niche) in enumerate(top_niches.iterrows(), 1):
        summary.append(
            f"{i}. **{niche.query}** - Score: {niche.score:.2f} - "
            f"Views: {niche.view_sum:,} - Trend Value: {niche.rsv:.2f}\n"
        )

    # Add cluster information
    summary.append("\n## Niche Clusters\n\n")

    clusters = trending_niches.groupby("niche")
    for cluster_id, group in clusters:
        top_in_cluster = group.sort_values("score", ascending=False).head(3)

        summary.append(f"Cluster {cluster_id}: ")
        summary.append(", ".join(top_in_cluster.query.tolist()))
        summary.append("\n")

    return "".join(summary)

# --- Blueprint Flow Tasks ---

@task(name="get_top_video_for_niche")
async def get_top_video_for_niche(niche: str) -> str:
    """Get the top video for a given niche"""
    youtube_api = YouTubeAPI()  # Used for API calls
    videos = await youtube_api.search_videos(niche, limit=10)

    if not videos:
        raise ValueError(f"No videos found for niche: {niche}")

    # Sort by view count
    sorted_videos = sorted(
        videos,
        key=lambda v: (
            int(v.get("viewCount", {}).get("text", "0").replace(",", ""))
            if isinstance(v.get("viewCount"), dict)
            else 0
        ),
        reverse=True,
    )

    # Get the top video URL
    top_video = sorted_videos[0]
    video_id = top_video.get("id")

    return f"https://www.youtube.com/watch?v={video_id}"

@task(name="ingest_seed_video")
async def ingest_seed_video(seed_url: str) -> Dict[str, Any]:
    """Ingest metadata for the seed video"""
    youtube_api = YouTubeAPI()

    # Get video metadata
    video_data = await youtube_api.get_video_metadata(seed_url)

    if not video_data:
        raise ValueError(f"Failed to retrieve data for seed video: {seed_url}")

    # Create output directory
    os.makedirs("builder", exist_ok=True)

    # Save to JSON file
    with open("builder/seed.json", "w") as f:
        json.dump(video_data, f, indent=2)

    return video_data

@task(name="build_query_list")
def build_query_list(seed_data: Dict[str, Any]) -> List[str]:
    """Build a list of queries from the seed video data"""
    # Extract title and tags
    title = seed_data.get("title", "")
    tags = seed_data.get("tags", [])

    # Simple tokenization of title
    title_words = [w.lower() for w in title.split() if len(w) > 3]

    # Combine title words and tags, remove duplicates
    all_terms = set(title_words + [t.lower() for t in tags])

    # Limit to 30 terms
    query_list = list(all_terms)[:30]

    # Save to file
    with open("builder/query_list.txt", "w") as f:
        for query in query_list:
            f.write(f"{query}\n")

    return query_list

@task(name="harvest_rank_channels")
async def harvest_rank_channels(query_list: List[str]) -> pd.DataFrame:
    """Harvest and rank channels related to the queries"""
    youtube_api = YouTubeAPI()  # Used for API calls
    all_channels = {}

    # Search for each query
    for query in query_list:
        channels = await youtube_api.search_channels(query, limit=20)

        for channel in channels:
            channel_id = channel.get("id")

            if not channel_id or channel_id in all_channels:
                continue

            # Parse subscriber count
            subscriber_text = channel.get("subscribers", "0")
            if isinstance(subscriber_text, str):
                # Handle abbreviations like '1.5M'
                if "M" in subscriber_text:
                    subscribers = float(subscriber_text.replace("M", "")) * 1_000_000
                elif "K" in subscriber_text:
                    subscribers = float(subscriber_text.replace("K", "")) * 1_000
                else:
                    # Remove non-numeric characters
                    subscribers = int("".join(c for c in subscriber_text if c.isdigit()) or 0)
            else:
                subscribers = 0

            # Store channel data
            all_channels[channel_id] = {
                "channel_id": channel_id,
                "channel_name": channel.get("title", ""),
                "subscribers": subscribers,
                "total_views": 0,  # Will need to be fetched separately
                "video_count": 0,  # Will need to be fetched separately
                "recent_upload_count": 0,
                "thirty_day_delta": 0.0,
                "primary_topics": query_list[:5],  # Using query list as proxy for topics
            }

        # Sleep to avoid rate limiting
        await asyncio.sleep(1)

    # Convert to DataFrame
    channels_df = pd.DataFrame(list(all_channels.values()))

    # Sort by subscribers and get top 100
    channels_df = channels_df.sort_values("subscribers", ascending=False).head(100)

    # Save to CSV
    channels_df.to_csv("builder/top_channels.csv", index=False)

    return channels_df

@task(name="perform_gap_analysis")
async def perform_gap_analysis(
    channels_df: pd.DataFrame, seed_data: Dict[str, Any]
) -> pd.DataFrame:
    """Analyze content gaps between seed video and competing channels"""
    youtube_api = YouTubeAPI()  # Used for API calls

    # Extract keywords from seed video
    seed_title = seed_data.get("title", "").lower()
    seed_tags = [tag.lower() for tag in seed_data.get("tags", [])]
    seed_description = seed_data.get("description", "").lower()

    # Combine for seed keywords
    seed_keywords = set(seed_title.split() + seed_tags + seed_description.split())
    seed_keywords = {k for k in seed_keywords if len(k) > 3}  # Filter short words

    # Initialize gap analysis
    gap_rows = []

    # Analyze top 10 channels
    top_channels = channels_df.head(10)

    for _, channel in top_channels.iterrows():
        channel_id = channel.channel_id

        # Get channel videos
        videos = await youtube_api.get_channel_videos(channel_id, limit=100)

        if not videos:
            continue

        # Extract all words from titles
        all_titles = " ".join([v.get("title", "").lower() for v in videos])
        channel_keywords = set(all_titles.split())
        channel_keywords = {k for k in channel_keywords if len(k) > 3}

        # Find unique keywords in channel not in seed
        # unique_to_channel = channel_keywords - seed_keywords  # Reserved for future use

        # Find unique keywords in seed not in channel
        unique_to_seed = seed_keywords - channel_keywords

        # Calculate opportunity score
        # Higher score = bigger gap opportunity
        opportunity_score = len(unique_to_seed) / max(1, len(seed_keywords))

        # For each keyword in seed, check coverage
        for keyword in seed_keywords:
            coverage = 1.0 if keyword in channel_keywords else 0.0

            gap_rows.append(
                {
                    "keyword": keyword,
                    "seed_coverage": 1.0,  # Always 1.0 for seed keywords
                    "channel_id": channel_id,
                    "channel_name": channel.channel_name,
                    "competitor_coverage": coverage,
                    "opportunity_score": opportunity_score if coverage == 0.0 else 0.0,
                }
            )

        # Sleep to avoid rate limiting
        await asyncio.sleep(1)

    # Convert to DataFrame
    gap_df = pd.DataFrame(gap_rows)

    # Pivot to get keyword x channel coverage
    pivot_df = gap_df.pivot_table(
        index="keyword",
        columns="channel_name",
        values="competitor_coverage",
        fill_value=0.0,
    ).reset_index()

    # Add seed coverage column
    pivot_df["seed_coverage"] = 1.0

    # Calculate average opportunity score per keyword
    keyword_opportunity = gap_df.groupby("keyword")["opportunity_score"].mean().reset_index()

    # Merge with pivot
    result_df = pd.merge(pivot_df, keyword_opportunity, on="keyword")

    # Sort by opportunity score
    result_df = result_df.sort_values("opportunity_score", ascending=False)

    # Save to CSV
    result_df.to_csv("builder/gap_report.csv", index=False)

    return result_df

@task(name="generate_blueprint")
def generate_blueprint(
    channels_df: pd.DataFrame, gap_df: pd.DataFrame, sentence_transformer
) -> Dict[str, Any]:
    """Generate a channel blueprint based on analysis"""
    # Load trending niches if available
    trending_niches_path = Path("niche_scout/trending_niches.csv")
    # trending_niches = None  # Reserved for future use

    if trending_niches_path.exists():
        # trending_niches = pd.read_csv(trending_niches_path)  # Reserved for future use
        pass

    # Extract top opportunity keywords
    top_keywords = gap_df.head(20)["keyword"].tolist()

    # Extract channel formats from top channels
    top_channels = channels_df.head(5)["channel_name"].tolist()

    # Generate content pillars based on keyword clusters
    # Use embeddings to cluster keywords
    keyword_embeddings = sentence_transformer.encode(top_keywords)

    # Use K-means to cluster
    n_clusters = min(5, len(top_keywords))
    if n_clusters > 1:
        kmeans = skc.KMeans(n_clusters=n_clusters).fit(keyword_embeddings)
        clusters = kmeans.labels_
    else:
        clusters = [0] * len(top_keywords)

    # Group keywords by cluster
    content_pillars = {}
    for i, keyword in enumerate(top_keywords):
        cluster = int(clusters[i])
        if cluster not in content_pillars:
            content_pillars[cluster] = []
        content_pillars[cluster].append(keyword)

    # Create pillar names
    pillar_names = []
    for cluster_id, keywords in content_pillars.items():
        pillar_name = (
            f"{keywords[0].title()} & {keywords[1].title()}"
            if len(keywords) > 1
            else keywords[0].title()
        )
        pillar_names.append(pillar_name)

    # Create format mix based on top trending formats
    format_mix = {"long_form": 0.6, "shorts": 0.3, "livestream": 0.1}

    # Create roadmap - 4 weeks, with content for each week
    roadmap = {}
    weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]

    for i, week in enumerate(weeks):
        pillar_idx = i % len(pillar_names)
        pillar = pillar_names[pillar_idx]

        roadmap[week] = [
            f"{pillar}: Deep dive on {top_keywords[i*2]}",
            f"Shorts: Quick tips on {top_keywords[i*2+1]}",
            f"Comparative: {top_channels[0]} vs our approach to {pillar}",
        ]

    # AI production tips
    ai_production_tips = [
        "Use Whisper API for automatic transcription and subtitles",
        "Stable Diffusion for thumbnail concepts (then refine manually)",
        "Bannerbear API for production-ready thumbnails with templates",
        "GPT-4 for script outlines, focusing on hook, value delivery, CTA",
        "Voice consistency checker to maintain brand tone and style",
    ]

    # COPPA checklist
    coppa_checklist = [
        {"item": "Content appropriate for all ages", "status": "Required"},
        {
            "item": "No collection of personal information from children",
            "status": "Required",
        },
        {
            "item": "Comments disabled if targeting children under 13",
            "status": "Required",
        },
        {"item": "Correct audience setting in YouTube Studio", "status": "Required"},
        {
            "item": "No call to actions that lead to external websites",
            "status": "Recommended",
        },
    ]

    # Create positioning statement
    positioning = f"A channel focused on {pillar_names[0]} and {pillar_names[1]}, "
    positioning += f"distinguished by filling the content gap around {top_keywords[0]} "
    positioning += f"that even top creators like {top_channels[0]} haven't fully covered."

    # Create the blueprint
    blueprint = {
        "positioning": positioning,
        "content_pillars": pillar_names,
        "format_mix": format_mix,
        "roadmap": roadmap,
        "ai_production_tips": ai_production_tips,
        "coppa_checklist": coppa_checklist,
    }

    # Save blueprint to markdown file
    with open("builder/channel_blueprint.md", "w") as f:
        f.write("# YouTube Channel Blueprint\n\n")
        f.write(f"## Positioning\n\n{positioning}\n\n")

        f.write("## Content Pillars\n\n")
        for pillar in pillar_names:
            f.write(f"- {pillar}\n")
        f.write("\n")

        f.write("## Format Mix\n\n")
        for format_type, percentage in format_mix.items():
            f.write(f"- {format_type}: {percentage*100:.0f}%\n")
        f.write("\n")

        f.write("## 30-Day Roadmap\n\n")
        for week, content in roadmap.items():
            f.write(f"### {week}\n\n")
            for item in content:
                f.write(f"- {item}\n")
            f.write("\n")

        f.write("## AI Production Tips\n\n")
        for tip in ai_production_tips:
            f.write(f"- {tip}\n")
        f.write("\n")

        f.write("## COPPA Compliance Checklist\n\n")
        for item in coppa_checklist:
            f.write(f"- {item['item']} - **{item['status']}**\n")

    return blueprint

@task(name="package_outputs")
def package_outputs() -> str:
    """Package all outputs into a zip file"""
    # Create output directory if it doesn't exist
    os.makedirs("builder", exist_ok=True)

    # Path for zip file
    zip_path = "builder/channel_pack.zip"

    # Create zip file
    with zipfile.ZipFile(zip_path, "w") as zipf:
        # Add all relevant files
        for file in os.listdir("builder"):
            if file.endswith(".zip"):
                continue

            file_path = os.path.join("builder", file)
            zipf.write(file_path, os.path.basename(file_path))

    return zip_path

# --- Main Flows ---

@flow(name="YouTube Niche Scout")
@sync_compatible
async def youtube_niche_scout_flow(
    queries: Optional[List[str]] = None,
    vector_storage: Optional[YouTubeVectorStorage] = None,
) -> NicheScoutResult:
    """Run the Niche-Scout workflow"""
    log = get_run_logger()

    if not queries:
        queries = [
            "nursery rhymes",
            "diy woodworking",
            "urban gardening",
            "ai news",
            "budget travel",
        ]

    log.info(f"Starting Niche Scout with {len(queries)} queries")

    # Create output directory
    os.makedirs("niche_scout", exist_ok=True)

    # Run the workflow
    signals_df = await harvest_youtube_signals(queries)
    trending_niches = score_cluster_niches(signals_df)

    # Generate digest
    digest = generate_niche_scout_digest(trending_niches)

    # Write digest to file
    with open("niche_scout/digest.md", "w") as f:
        f.write(digest)

    # Store vectors if storage is provided
    if vector_storage:
        sentence_transformer = initialize_sentence_transformer()
        await store_niche_vectors(trending_niches, vector_storage, sentence_transformer)

    # Convert DataFrame to NicheScoutResult
    result = NicheScoutResult(
        run_date=datetime.now(),
        trending_niches=[YouTubeNiche(**row.to_dict()) for _, row in trending_niches.iterrows()],
        top_niches=[
            YouTubeNiche(**row.to_dict())
            for _, row in trending_niches.sort_values("score", ascending=False).head(10).iterrows()
        ],
        visualization_url=None,  # Would be populated in production
    )

    log.info(f"Niche Scout completed. Found {len(trending_niches)} niches.")

    return result

@flow(name="YouTube Blueprint")
@sync_compatible
async def youtube_blueprint_flow(
    seed_url: Optional[str] = None,
    auto_niche: bool = False,
    vector_storage: Optional[YouTubeVectorStorage] = None,
) -> BlueprintResult:
    """Run the Seed-to-Blueprint workflow"""
    log = get_run_logger()

    # Initialize sentence transformer
    sentence_transformer = initialize_sentence_transformer()

    # Create output directory
    os.makedirs("builder", exist_ok=True)

    # Auto-select from trending niches if requested
    if auto_niche and not seed_url:
        log.info("Auto-selecting from trending niches")

        # Check if trending niches file exists
        trending_niches_path = Path("niche_scout/trending_niches.csv")
        if trending_niches_path.exists():
            trending_df = pd.read_csv(trending_niches_path)
            top_niche = trending_df.sort_values("score", ascending=False).iloc[0]
            seed_url = await get_top_video_for_niche(top_niche.query)
        else:
            # Run niche scout to get trending niches
            log.info("Running Niche Scout to find trending niches")
            niche_result = await youtube_niche_scout_flow(vector_storage=vector_storage)
            top_niche = niche_result.top_niches[0]
            seed_url = await get_top_video_for_niche(top_niche.query)

    if not seed_url:
        raise ValueError("No seed URL provided and auto-niche disabled")

    log.info(f"Starting Blueprint with seed URL: {seed_url}")

    # Run the workflow
    seed_data = await ingest_seed_video(seed_url)
    query_list = build_query_list(seed_data)
    channels_df = await harvest_rank_channels(query_list)
    gap_df = await perform_gap_analysis(channels_df, seed_data)
    blueprint = generate_blueprint(channels_df, gap_df, sentence_transformer)
    zip_path = package_outputs()

    # Convert to BlueprintResult
    result = BlueprintResult(
        run_date=datetime.now(),
        seed_url=seed_url,
        seed_data=seed_data,
        top_channels=[
            YouTubeChannel(**row.to_dict()) for _, row in channels_df.head(10).iterrows()
        ],
        gap_analysis=[
            YouTubeGap(
                keyword=row.keyword,
                seed_coverage=row.seed_coverage,
                competitor_coverage={},  # Would need to convert from pivot
                opportunity_score=row.opportunity_score,
            )
            for _, row in gap_df.head(20).iterrows()
        ],
        blueprint=YouTubeBlueprint(**blueprint),
        blueprint_url=f"file://{os.path.abspath(zip_path)}",
    )

    log.info(f"Blueprint completed. Package available at: {zip_path}")

    return result
