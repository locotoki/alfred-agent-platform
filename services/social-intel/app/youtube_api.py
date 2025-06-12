"""YouTube API Integration Module.

This module provides functions to interact with the YouTube Data API v3 for fetching
trends, statistics, and channel data.
"""

# type: ignore
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

logger = structlog.get_logger(__name__)
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(Exception):
    """Exception raised for YouTube API errors"""


async def search_videos(
    query: str,
    max_results: int = 10,
    order: str = "relevance",
    video_type: str = "any",
    region_code: str = "US",
) -> List[Dict[str, Any]]:
    """Search for videos using the YouTube API.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 10)
        order: Order of results (default: relevance)
        video_type: Type of videos to include (default: any)
        region_code: Region code for results (default: US)

    Returns:
        List of video objects with snippet information

    Raises:
        YouTubeAPIError: If the API request fails.
    """
    if not YOUTUBE_API_KEY:
        raise YouTubeAPIError("YouTube API key is not configured")

    # Prepare URL and parameters
    url = f"{YOUTUBE_API_BASE_URL}/search"
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": max_results,
        "order": order,
        "type": "video",
        "videoType": video_type,
        "regionCode": region_code,
        "key": YOUTUBE_API_KEY,
    }

    try:
        logger.info("youtube_api_search_request", query=query, max_results=max_results)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await responsetext()
                    logger.error(
                        "youtube_api_search_error",
                        status=response.status,
                        error=error_text,
                    )
                    raise YouTubeAPIError(f"YouTube API error: {error_text}")

                data = await responsejson()

        logger.info(
            "youtube_api_search_success",
            items_count=len(data.get("items", [])),
            query=query,
        )

        return data.get("items", [])

    except aiohttp.ClientError as e:
        logger.error("youtube_api_network_error", error=str(e))
        raise YouTubeAPIError(f"Network error: {str(e)}")


async def get_video_details(video_ids: List[str]) -> List[Dict[str, Any]]:
    """Get detailed information about specific videos.

    Args:
        video_ids: List of YouTube video IDs

    Returns:
        List of video details including statistics

    Raises:
        YouTubeAPIError: If the API request fails.
    """
    if not YOUTUBE_API_KEY:
        raise YouTubeAPIError("YouTube API key is not configured")

    if not video_ids:
        return []

    # Convert list of IDs to comma-separated string
    video_id_str = ",".join(video_ids)

    # Prepare URL and parameters
    url = f"{YOUTUBE_API_BASE_URL}/videos"
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": video_id_str,
        "key": YOUTUBE_API_KEY,
    }

    try:
        logger.info("youtube_api_video_details_request", video_ids=video_ids)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await responsetext()
                    logger.error(
                        "youtube_api_video_details_error",
                        status=response.status,
                        error=error_text,
                    )
                    raise YouTubeAPIError(f"YouTube API error: {error_text}")

                data = await responsejson()

        logger.info("youtube_api_video_details_success", items_count=len(data.get("items", [])))

        return data.get("items", [])

    except aiohttp.ClientError as e:
        logger.error("youtube_api_network_error", error=str(e))
        raise YouTubeAPIError(f"Network error: {str(e)}")


async def get_channel_details(channel_ids: List[str]) -> List[Dict[str, Any]]:
    """Get detailed information about specific channels.

    Args:
        channel_ids: List of YouTube channel IDs

    Returns:
        List of channel details including statistics

    Raises:
        YouTubeAPIError: If the API request fails.
    """
    if not YOUTUBE_API_KEY:
        raise YouTubeAPIError("YouTube API key is not configured")

    if not channel_ids:
        return []

    # Convert list of IDs to comma-separated string
    channel_id_str = ",".join(channel_ids)

    # Prepare URL and parameters
    url = f"{YOUTUBE_API_BASE_URL}/channels"
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": channel_id_str,
        "key": YOUTUBE_API_KEY,
    }

    try:
        logger.info("youtube_api_channel_details_request", channel_ids=channel_ids)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await responsetext()
                    logger.error(
                        "youtube_api_channel_details_error",
                        status=response.status,
                        error=error_text,
                    )
                    raise YouTubeAPIError(f"YouTube API error: {error_text}")

                data = await responsejson()

        logger.info(
            "youtube_api_channel_details_success",
            items_count=len(data.get("items", [])),
        )

        return data.get("items", [])

    except aiohttp.ClientError as e:
        logger.error("youtube_api_network_error", error=str(e))
        raise YouTubeAPIError(f"Network error: {str(e)}")


async def get_trends_by_category(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    region_code: str = "US",
    max_results: int = 20,
) -> Dict[str, Any]:
    """Get trending videos and statistics based on category/subcategory.

    Args:
        category: Main content category (e.g., "tech", "kids")
        subcategory: Specific subcategory (e.g., "kids.nursery")
        region_code: Region code for results (default: US)
        max_results: Maximum number of results to return (default: 20)

    Returns:
        Dictionary with trending videos, statistics, and analysis

    Raises:
        YouTubeAPIError: If the API request fails
    """
    # Generate search query based on category/subcategory
    search_queries = []

    # Map categories to relevant search queries
    category_queries = {
        "education": ["educational videos", "tutorials", "how to", "lessons"],
        "entertainment": ["entertainment", "funny videos", "comedy", "shows"],
        "tech": ["technology", "gadgets", "smartphones", "tech reviews"],
        "lifestyle": ["lifestyle", "fashion", "health tips", "home decor"],
        "business": ["business tips", "entrepreneurship", "investing", "finance"],
        "arts": ["art tutorials", "digital art", "creative process", "drawing"],
        "travel": ["travel guides", "travel vlog", "destinations", "tourism"],
        "sports": [
            "sports highlights",
            "fitness routine",
            "workout tips",
            "extreme sports",
        ],
        "kids": [
            "kids videos",
            "children's content",
            "family friendly",
            "educational for kids",
        ],
    }

    # Map subcategories to more specific search queries
    subcategory_queries = {
        "kids.nursery": [
            "nursery rhymes",
            "baby songs",
            "toddler music",
            "kids learning songs",
            "alphabet songs",
            "counting songs",
            "lullaby for babies",
        ],
        "tech.gaming": [
            "gaming tips",
            "gameplay walkthrough",
            "game review",
            "gaming setup",
        ],
        "lifestyle.food": [
            "cooking tutorial",
            "easy recipes",
            "food review",
            "cooking tips",
        ],
        "education.courses": [
            "online course",
            "skill tutorial",
            "programming tutorial",
            "learning guide",
        ],
    }

    # Build search queries
    if subcategory and subcategory in subcategory_queries:
        # Use more specific subcategory queries
        search_queries = subcategory_queries[subcategory]
    elif category and category in category_queries:
        # Use category-level queries
        search_queries = category_queries[category]
    else:
        # Default queries for trending content
        search_queries = ["trending", "viral videos", "popular content", "new videos"]

    # Execute searches for each query
    all_videos = []
    for query in search_queries:
        try:
            videos = await search_videos(
                query=query, max_results=10, order="relevance", region_code=region_code
            )
            all_videos.extend(videos)
        except YouTubeAPIError as e:
            logger.warning("search_query_failed", query=query, error=str(e))

    # Extract video IDs
    video_ids = [video["id"]["videoId"] for video in all_videos]

    # Get detailed video information
    video_details = await get_video_details(video_ids)

    # Extract channel IDs for further analysis
    channel_ids = list(set(video["snippet"]["channelId"] for video in video_details))

    # Get channel details
    channel_details = await get_channel_details(channel_ids[:10])  # Limit to top 10 channels

    # Create mapping of channel IDs to channel data
    channel_map = {channel["id"]: channel for channel in channel_details}

    # Process video details to extract trends
    niche_data = []
    for video in video_details:
        # Basic video data
        video_id = video["id"]
        title = video["snippet"]["title"]
        channel_id = video["snippet"]["channelId"]

        # Extract statistics
        statistics = video.get("statistics", {})
        view_count = int(statistics.get("viewCount", 0))
        like_count = int(statistics.get("likeCount", 0))
        comment_count = int(statistics.get("commentCount", 0))

        # Calculate engagement ratio (likes + comments per view)
        engagement_ratio = (like_count + comment_count) / view_count if view_count > 0 else 0

        # Get channel data if available
        channel_data = channel_map.get(channel_id, {})
        channel_name = video["snippet"]["channelTitle"]
        subscriber_count = int(channel_data.get("statistics", {}).get("subscriberCount", 0))

        # Calculate video performance relative to channel size
        performance_score = view_count / subscriber_count if subscriber_count > 0 else 0

        # Add to niche data
        niche_data.append(
            {
                "title": title,
                "video_id": video_id,
                "channel_id": channel_id,
                "channel_name": channel_name,
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "engagement_ratio": engagement_ratio,
                "subscriber_count": subscriber_count,
                "performance_score": performance_score,
            }
        )

    # Sort by performance score and engagement
    niche_data.sort(key=lambda x: (x["performance_score"], x["engagement_ratio"]), reverse=True)

    # Identify top niches by clustering similar videos
    niches = []
    keywords = set()

    for video in niche_data[:20]:  # Analyze top 20 videos
        title_words = video["title"].lower().split()
        key_phrases = []

        # Extract 2-3 word phrases for niche identification
        for i in range(len(title_words) - 1):
            phrase = " ".join(title_words[i : i + 2])
            if len(phrase) > 5 and phrase not in [
                "official video",
                "official music",
                "music video",
            ]:
                key_phrases.append(phrase)

            if i < len(title_words) - 2:
                phrase = " ".join(title_words[i : i + 3])
                if len(phrase) > 8 and phrase not in [
                    "official music video",
                    "official video lyrics",
                ]:
                    key_phrases.append(phrase)

        # Add to niches if unique enough
        for phrase in key_phrases:
            if phrase not in keywords and len(phrase) > 5:
                keywords.add(phrase)

                # For each niche, find related videos
                related_videos = []
                for v in niche_data:
                    if phrase.lower() in v["title"].lower():
                        related_videos.append(v)

                if len(related_videos) >= 2:
                    # Calculate average statistics
                    avg_views = sum(v["view_count"] for v in related_videos) / len(related_videos)
                    avg_engagement = sum(v["engagement_ratio"] for v in related_videos) / len(
                        related_videos
                    )

                    # Add as a niche if relevant
                    niches.append(
                        {
                            "query": phrase,
                            "view_sum": sum(v["view_count"] for v in related_videos),
                            "engagement": avg_engagement,
                            "score": avg_views * avg_engagement * 100,  # Custom score metric
                            "videos": [v["video_id"] for v in related_videos[:3]],
                            "top_channels": [
                                {
                                    "name": v["channel_name"],
                                    "subs": v["subscriber_count"],
                                }
                                for v in related_videos[:2]
                            ],
                        }
                    )

    # Sort niches by score
    niches.sort(key=lambda x: x["score"], reverse=True)

    # Limit to top 10 niches
    niches = niches[:10]

    # Add placeholder values for compatibility with existing UI
    for niche in niches:
        niche["rsv"] = niche["score"] / 100  # Relative search volume (approximation)
        niche["growth_rate"] = 75 + (niche["score"] / 1000)  # Growth rate (approximation)
        niche["competition_level"] = "High" if niche["view_sum"] > 1000000 else "Medium"
        niche["shorts_friendly"] = True  # Assume most content is shorts-friendly
        niche["view_rank"] = niches.index(niche) + 1
        niche["rsv_rank"] = niches.index(niche) + 1
        niche["niche"] = niches.index(niche) // 3  # Group similar niches

        # Add x, y coordinates for visualization (placeholder values)
        niche["x"] = (niches.index(niche) % 5) * 2 - 5
        niche["y"] = (niches.index(niche) // 5) * 2 - 2

    # Create analysis of results
    analysis = {
        "fastest_growing": niches[0]["query"] if niches else "",
        "most_shorts_friendly": next(
            (n["query"] for n in niches if n.get("shorts_friendly", False)),
            niches[0]["query"] if niches else "",
        ),
        "lowest_competition": next(
            (n["query"] for n in niches if n.get("competition_level") == "Medium"),
            niches[0]["query"] if niches else "",
        ),
    }

    # Build recommendations
    recommendations = []
    if niches:
        recommendations.append(f"Focus on {niches[0]['query']} for highest growth potential")
        recommendations.append("Create content under 60 seconds for optimal Shorts performance")
        recommendations.append(
            "Target trending topics with high search volume but moderate competition"
        )

    # Compile final results
    results = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "query": search_queries[0] if search_queries else None,
        "category": category,
        "subcategory": subcategory,
        "trending_niches": niches,
        "top_niches": niches[:5] if len(niches) > 5 else niches,
        "analysis_summary": analysis,
        "recommendations": recommendations,
    }

    return results
