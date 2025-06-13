#!/usr/bin/env python3
"""Manual Niche Scout Workflow Script.

This script directly uses the YouTube API to perform a niche analysis
for YouTube content. It bypasses the usual platform services and
provides a direct way to analyze trends.
"""

import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timedelta

# Check if we have the required libraries
try:
    import googleapiclient.discovery
import matplotlib.pyplot as plt
except ImportError:
    print("Installing required dependencies...")
    os.system("pip install aiohttp google-api-python-client matplotlib numpy")
    import googleapiclient.discovery

import matplotlib.pyplot as plt

# API Key from environment or direct input
API_KEY = os.environ.get("YOUTUBE_API_KEY", "AIzaSyDG7o4pRFOjRQzGcsNrc-fmF-O77EbfZDM")
# Enhanced category and subcategory definitions
CATEGORY_MAPPING = {
    "kids": {
        "kids.nursery": [
            "nursery rhymes for kids",
            "baby songs nursery rhymes",
            "kids learning songs",
            "alphabet song for children",
            "counting songs for toddlers",
            "nursery rhymes compilation",
            "lullabies for babies",
            "children's educational songs",
            "phonics songs for kids",
            "shapes and colors for toddlers",
            "popular nursery rhymes 2023",
            "baby shark nursery rhymes",
        ],
        "kids.toys": [
            "toy unboxing for kids",
            "popular toys review",
            "kids toy channels",
            "educational toys for children",
            "sensory toys for toddlers",
            "LEGO building for kids",
            "top toys 2023",
            "children's toy reviews",
            "toy play videos",
            "pretend play with toys",
        ],
        "kids.learning": [
            "educational videos for kids",
            "learning videos for toddlers",
            "kids math learning",
            "children's science videos",
            "kids learn to read",
            "spelling for kids",
            "interactive learning for children",
            "homeschool learning videos",
            "preschool learning at home",
            "kids bilingual learning",
        ],
    },
    "tech": {
        "tech.gadgets": [
            "latest tech gadgets review",
            "smartphone reviews 2023",
            "tech unboxing videos",
            "best budget gadgets",
            "tech comparison videos",
            "wearable tech reviews",
            "smart home devices",
            "gaming hardware reviews",
            "tech accessories",
            "upcoming tech trends",
        ],
        "tech.programming": [
            "programming tutorials for beginners",
            "python coding projects",
            "web development tutorial",
            "mobile app development",
            "data science programming",
            "learn javascript",
            "full stack development",
            "coding challenges",
            "software engineering career",
            "machine learning tutorial",
        ],
        "tech.ai": [
            "artificial intelligence tutorials",
            "machine learning for beginners",
            "AI tools demonstration",
            "neural network explanation",
            "ChatGPT tutorials",
            "AI art generation",
            "deep learning projects",
            "AI for business",
            "future of artificial intelligence",
            "learn prompt engineering",
        ],
    },
    "finance": {
        "finance.investing": [
            "stock market investing for beginners",
            "dividend investing strategy",
            "ETF investing guide",
            "cryptocurrency investment",
            "real estate investing tips",
            "passive income investing",
            "retirement planning strategy",
            "value investing explained",
            "index fund investing",
            "portfolio diversification strategy",
        ],
        "finance.personalfinance": [
            "personal finance management",
            "budgeting tips and tricks",
            "debt payoff strategies",
            "saving money challenges",
            "financial independence tips",
            "credit score improvement",
            "money management for beginners",
            "frugal living advice",
            "financial planning for families",
            "emergency fund building",
        ],
        "finance.crypto": [
            "cryptocurrency explained",
            "bitcoin investing strategy",
            "altcoin analysis",
            "crypto trading tutorial",
            "blockchain technology explained",
            "NFT investing guide",
            "defi protocol review",
            "crypto market analysis",
            "web3 technology explained",
            "crypto wallet setup",
        ],
    },
    "health": {
        "health.fitness": [
            "home workout routines",
            "weight loss exercise plan",
            "strength training for beginners",
            "HIIT workout videos",
            "yoga for flexibility",
            "cardio exercise routines",
            "bodyweight training at home",
            "muscle building workout",
            "fitness challenge 30 day",
            "beginner gym guide",
        ],
        "health.nutrition": [
            "healthy meal prep ideas",
            "weight loss diet plan",
            "nutrition for muscle building",
            "plant-based diet recipes",
            "intermittent fasting guide",
            "keto diet for beginners",
            "healthy eating on a budget",
            "meal planning tutorial",
            "anti-inflammatory diet",
            "protein-rich meal ideas",
        ],
        "health.mentalhealth": [
            "anxiety relief techniques",
            "meditation for beginners",
            "stress management strategies",
            "mindfulness practices daily",
            "mental health self-care",
            "therapy techniques at home",
            "improving sleep quality",
            "burnout prevention tips",
            "positive psychology techniques",
            "depression coping strategies",
        ],
    },
}

def build_youtube_client():
    """Build and return a YouTube API client."""
    return googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

def parse_duration(duration_str):
    """Parse ISO 8601 duration string to seconds."""
    import re

# Parse the duration string
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, duration_str)
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds

def calculate_freshness_score(published_at):
    """Calculate a freshness score based on publish date."""
    try:
        published_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now().astimezone()
        age_days = (now - published_date).days

        # Newer content gets higher scores (scale 0-1)
        if age_days <= 7:  # Last week
            return 1.0
        elif age_days <= 30:  # Last month
            return 0.8
        elif age_days <= 90:  # Last quarter
            return 0.6
        elif age_days <= 365:  # Last year
            return 0.4
        else:
            return 0.2
    except Exception:
        return 0.5  # Default if we can't parse date

async def search_videos(query, max_results=10, youtube=None, published_after=None):
    """Search for videos using YouTube API."""
    print(f"Searching for: {query}...")

    if not youtube:
        youtube = build_youtube_client()

    # Set default published_after to 1 year ago if not provided
    if published_after is None:
        one_year_ago = datetime.now() - timedelta(days=365)
        published_after = one_year_ago.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Execute search request
    search_params = {
        "q": query,
        "part": "id,snippet",
        "maxResults": max_results,
        "type": "video",
        "regionCode": "US",
        "relevanceLanguage": "en",
        "publishedAfter": published_after,
        "safeSearch": "strict" if "kids" in query.lower() else "moderate",
        "order": "relevance",
    }

    search_response = youtube.search().list(**search_params).execute()

    # Extract video IDs
    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

    if not video_ids:
        print(f"No videos found for query: {query}")
        return []

    # Get detailed video information
    videos_response = (
        youtube.videos()
        .list(part="snippet,contentDetails,statistics", id=",".join(video_ids))
        .execute()
    )

    videos = []
    for item in videos_response.get("items", []):
        # Extract statistics with safe defaults
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})

        # Calculate engagement rate
        view_count = int(stats.get("viewCount", 0))
        like_count = int(stats.get("likeCount", 0))
        comment_count = int(stats.get("commentCount", 0))
        engagement_rate = ((like_count + comment_count) / view_count * 100) if view_count > 0 else 0

        # Calculate freshness score
        freshness = calculate_freshness_score(snippet.get("publishedAt", ""))

        video_data = {
            "id": item["id"],
            "title": snippet.get("title", "Unknown"),
            "channel_id": snippet.get("channelId", ""),
            "channel_title": snippet.get("channelTitle", "Unknown"),
            "published_at": snippet.get("publishedAt", ""),
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "duration": parse_duration(item.get("contentDetails", {}).get("duration", "PT0S")),
            "tags": snippet.get("tags", []),
            "description": snippet.get("description", ""),
            "engagement_rate": round(engagement_rate, 2),
            "freshness": freshness,
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        }
        videos.append(video_data)

    return videos

async def get_channel_details(channel_ids, youtube=None):
    """Get detailed information about specific channels."""
    if not channel_ids:
        return []

    print(f"Getting details for {len(channel_ids)} channels...")

    if not youtube:
        youtube = build_youtube_client()

    # Split into batches of 50 (API limit)
    batches = [channel_ids[i : i + 50] for i in range(0, len(channel_ids), 50)]
    channels = []

    for batch in batches:
        channels_response = (
            youtube.channels()
            .list(
                part="snippet,statistics,contentDetails,brandingSettings",
                id=",".join(batch),
            )
            .execute()
        )

        for item in channels_response.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            branding = item.get("brandingSettings", {}).get("channel", {})

            # Calculate engagement metrics
            sub_count = int(stats.get("subscriberCount", 0))
            view_count = int(stats.get("viewCount", 0))
            video_count = int(stats.get("videoCount", 0))

            # Views per video
            views_per_video = view_count / video_count if video_count > 0 else 0

            # Views per subscriber
            views_per_sub = view_count / sub_count if sub_count > 0 else 0

            channel_data = {
                "id": item["id"],
                "title": snippet.get("title", "Unknown"),
                "description": snippet.get("description", ""),
                "custom_url": snippet.get("customUrl", ""),
                "subscribers": sub_count,
                "hidden_subscribers": stats.get("hiddenSubscriberCount", False),
                "video_count": video_count,
                "view_count": view_count,
                "country": snippet.get("country", "Unknown"),
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "views_per_video": int(views_per_video),
                "views_per_sub": round(views_per_sub, 2),
                "keywords": (
                    branding.get("keywords", "").split(",") if branding.get("keywords") else []
                ),
            }
            channels.append(channel_data)

    return channels

def identify_video_pattern(videos):
    """Identify patterns in successful videos."""
    if not videos:
        return {}

    # Analyze durations
    durations = [v["duration"] for v in videos]
    avg_duration = sum(durations) / len(durations)

    # Categorize video lengths
    shorts = [d for d in durations if d <= 60]
    medium = [d for d in durations if 60 < d <= 600]
    long = [d for d in durations if d > 600]

    # Analyze titles
    titles = [v["title"].lower() for v in videos]
    title_lengths = [len(title.split()) for title in titles]
    avg_title_length = sum(title_lengths) / len(title_lengths)

    # Look for common phrases in titles
    title_bigrams = []
    for title in titles:
        words = title.split()
        for i in range(len(words) - 1):
            title_bigrams.append(" ".join(words[i : i + 2]))

    # Count bigram frequencies
    bigram_counts = {}
    for bigram in title_bigrams:
        if len(bigram) > 5:
            bigram_counts[bigram] = bigram_counts.get(bigram, 0) + 1

    # Find top 5 bigrams
    top_bigrams = sorted(bigram_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Analyze upload timing
    if all(v.get("published_at") for v in videos):
        days_of_week = {}
        hours_of_day = {}

        for v in videos:
            try:
                date = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
                day = date.strftime("%A")
                hour = date.hour

                days_of_week[day] = days_of_week.get(day, 0) + 1
                hours_of_day[hour] = hours_of_day.get(hour, 0) + 1
            except:
                pass

        top_day = max(days_of_week.items(), key=lambda x: x[1])[0] if days_of_week else "Unknown"
        top_hour = max(hours_of_day.items(), key=lambda x: x[1])[0] if hours_of_day else -1
    else:
        top_day = "Unknown"
        top_hour = -1

    return {
        "avg_duration": round(avg_duration),
        "duration_distribution": {
            "short": len(shorts) / len(durations) if durations else 0,
            "medium": len(medium) / len(durations) if durations else 0,
            "long": len(long) / len(durations) if durations else 0,
        },
        "avg_title_length": round(avg_title_length),
        "common_title_phrases": [phrase for phrase, count in top_bigrams],
        "best_upload_day": top_day,
        "best_upload_hour": top_hour if top_hour != -1 else "Unknown",
    }

def generate_visualization_guide(niches, category, subcategory):
    """Generate a visualization guide based on the analysis."""
    # Create simple bubble chart visualization
    if len(niches) >= 3:
        plt.figure(figsize=(10, 8))

        # Extract data for visualization
        queries = [n["query"] for n in niches[:10]]
        views = [n["avg_views"] for n in niches[:10]]
        engagement = [n["engagement"] for n in niches[:10]]
        scores = [n["score"] * 50 for n in niches[:10]]  # Scale for bubble size

        # Create bubble chart
        plt.scatter(engagement, views, s=scores, alpha=0.7)

        # Add labels to bubbles
        for i, query in enumerate(queries):
            if i < 10:  # Only label top 10 for clarity
                plt.annotate(query, (engagement[i], views[i]))

        plt.title(f"Niche Analysis for {category} > {subcategory}")
        plt.xlabel("Engagement Rate (%)")
        plt.ylabel("Average Views")
        plt.grid(True, linestyle="--", alpha=0.7)

        # Save chart
        chart_file = f"niche-chart-{category}-{subcategory.split('.')[-1]}.png"
        plt.savefig(chart_file)
        plt.close()

        # Create visualization guide with chart reference
        guide = {
            "chart_file": chart_file,
            "interpretation": [
                "The bubble chart visualizes the relationship between engagement rate and average views.",
                "Each bubble represents a potential niche or keyword cluster.",
                "Bubble size indicates the overall opportunity score (larger = better).",
                "The best opportunities are typically in the upper-right quadrant (high views, high engagement).",
                "Consider focusing on niches with moderate competition but high engagement.",
            ],
            "top_recommendations": [
                {
                    "niche": niches[0]["query"],
                    "why": f"Highest opportunity score ({niches[0]['score']}) with good balance of views and engagement",
                },
                {
                    "niche": max(niches[:5], key=lambda x: x["avg_views"])["query"],
                    "why": "Highest average view count, indicating strong audience interest",
                },
                {
                    "niche": max(niches[:5], key=lambda x: x["engagement"])["query"],
                    "why": "Highest engagement rate, suggesting an active and responsive audience",
                },
            ],
            "content_strategy": [
                f"Optimal video length: {identify_video_pattern([v for n in niches[:3] for v in n.get('sample_videos', [])])['avg_duration']} seconds",
                f"Best upload day: {identify_video_pattern([v for n in niches[:3] for v in n.get('sample_videos', [])])['best_upload_day']}",
                "Include these keywords in titles: "
                + ", ".join(
                    [
                        k
                        for k in identify_video_pattern(
                            [v for n in niches[:3] for v in n.get("sample_videos", [])]
                        )["common_title_phrases"][:3]
                    ]
                ),
            ],
        }

        return guide

    return {
        "chart_file": None,
        "interpretation": ["Not enough data to generate visualization"],
        "top_recommendations": [],
        "content_strategy": [],
    }

async def analyze_niche(category, subcategory):
    """Run the full Niche Scout analysis."""
    start_time = time.time()

    print(f"Starting Niche Scout analysis for {category} > {subcategory}")
    print(f"Using YouTube API key: {API_KEY[:5]}...{API_KEY[-5:]}")

    # Get search queries based on category/subcategory
    if category in CATEGORY_MAPPING and subcategory in CATEGORY_MAPPING[category]:
        search_queries = CATEGORY_MAPPING[category][subcategory]
    else:
        # Fallback to generic queries
        search_queries = [
            f"{category} {subcategory.split('.')[-1]}",
            f"popular {subcategory.split('.')[-1]} videos",
            f"trending {category} content",
            f"best {subcategory.split('.')[-1]} channels",
            f"how to {subcategory.split('.')[-1]}",
            f"{subcategory.split('.')[-1]} tutorial",
            f"{subcategory.split('.')[-1]} 2023",
        ]

    youtube = build_youtube_client()
    all_videos = []

    # Gather videos from each query
    for query in search_queries:
        try:
            videos = await search_videos(query, max_results=15, youtube=youtube)
            print(f"Found {len(videos)} videos for '{query}'")
            all_videos.extend(videos)
            # Sleep to avoid quota issues
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error searching for '{query}': {e}")

    # Deduplicate videos by ID
    unique_videos = []
    seen_ids = set()
    for video in all_videos:
        if video["id"] not in seen_ids:
            unique_videos.append(video)
            seen_ids.add(video["id"])

    all_videos = unique_videos
    print(f"Found {len(all_videos)} unique videos across all queries")

    # Extract channel IDs for further analysis
    channel_ids = list(set(video["channel_id"] for video in all_videos))

    # Get channel details
    channels = await get_channel_details(
        channel_ids[:30], youtube=youtube
    )  # Increased from 25 to 30
    channel_map = {channel["id"]: channel for channel in channels}

    # Process videos to extract trends
    niche_keywords = {}

    # Enhanced keyword extraction
    for video in all_videos:
        # Extract keywords from title
        title_words = video["title"].lower().split()

        # Process 2-3 word phrases from title
        for i in range(len(title_words)):
            if i < len(title_words) - 2:
                # Look for 3-word phrases
                phrase = " ".join(title_words[i : i + 3])
                if len(phrase) > 8 and "official" not in phrase and "video" not in phrase:
                    weight = 1.0 + (video["view_count"] / 100000) * 0.5  # Weight by views
                    niche_keywords[phrase] = niche_keywords.get(phrase, 0) + weight

            if i < len(title_words) - 1:
                # Look for 2-word phrases
                phrase = " ".join(title_words[i : i + 2])
                if len(phrase) > 5 and "official" not in phrase and "video" not in phrase:
                    weight = 1.0 + (video["view_count"] / 100000) * 0.3  # Weight by views
                    niche_keywords[phrase] = niche_keywords.get(phrase, 0) + weight

        # Extract from tags
        for tag in video.get("tags", []):
            if 5 < len(tag) < 30 and " " in tag:
                weight = 1.0 + (video["view_count"] / 100000) * 0.4
                niche_keywords[tag.lower()] = niche_keywords.get(tag.lower(), 0) + weight

    # Sort keywords by frequency
    sorted_keywords = sorted(niche_keywords.items(), key=lambda x: x[1], reverse=True)
    top_keywords = sorted_keywords[:20]  # Increased from 15 to 20

    # Analyze top niches
    niches = []
    for keyword, count in top_keywords:
        # Find videos matching this keyword
        matching_videos = [
            v
            for v in all_videos
            if keyword.lower() in v["title"].lower()
            or keyword.lower() in " ".join(v.get("tags", [])).lower()
        ]

        if len(matching_videos) >= 2:
            # Calculate metrics
            avg_views = sum(v["view_count"] for v in matching_videos) / len(matching_videos)
            total_views = sum(v["view_count"] for v in matching_videos)
            avg_likes = (
                sum(v["like_count"] for v in matching_videos) / len(matching_videos)
                if any(v["like_count"] for v in matching_videos)
                else 0
            )
            avg_comments = (
                sum(v["comment_count"] for v in matching_videos) / len(matching_videos)
                if any(v["comment_count"] for v in matching_videos)
                else 0
            )
            engagement = (avg_likes / avg_views * 100) if avg_views > 0 else 0

            # Calculate freshness (recency)
            avg_freshness = sum(v.get("freshness", 0.5) for v in matching_videos) / len(
                matching_videos
            )

            # Calculate competition
            channel_diversity = len(set(v["channel_id"] for v in matching_videos)) / len(
                matching_videos
            )

            # Enhanced scoring formula
            view_factor = (avg_views / 10000) ** 0.5  # Square root to reduce impact of outliers
            engagement_factor = 1 + engagement / 10
            freshness_factor = 0.7 + (avg_freshness * 0.6)  # 0.7-1.3 range
            competition_factor = 0.5 + (channel_diversity * 0.5)  # 0.5-1.0 range

            # Final score calculation
            score = view_factor * engagement_factor * freshness_factor * competition_factor

            # Gather top channels for this niche
            video_channels = [(v["channel_id"], v["channel_title"]) for v in matching_videos]
            channel_counts = {}
            for ch_id, ch_title in video_channels:
                channel_counts[ch_id] = channel_counts.get(ch_id, 0) + 1

            top_channels = []
            for ch_id, count in sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]:  # Increased from 2 to 3
                if ch_id in channel_map:
                    ch_data = channel_map[ch_id]
                    top_channels.append(
                        {
                            "name": ch_data["title"],
                            "subs": ch_data["subscribers"],
                            "videos": ch_data["video_count"],
                            "views_per_video": ch_data.get("views_per_video", "Unknown"),
                            "thumbnail": ch_data.get("thumbnail", ""),
                        }
                    )
                else:
                    # Use title from video if channel details not available
                    for v_ch_id, v_ch_title in video_channels:
                        if v_ch_id == ch_id:
                            top_channels.append(
                                {
                                    "name": v_ch_title,
                                    "subs": "Unknown",
                                    "videos": "Unknown",
                                    "views_per_video": "Unknown",
                                    "thumbnail": "",
                                }
                            )
                            break

            # Identify patterns in video characteristics
            video_patterns = identify_video_pattern(matching_videos)

            niche_data = {
                "query": keyword,
                "video_count": len(matching_videos),
                "view_sum": total_views,
                "avg_views": int(avg_views),
                "avg_comments": int(avg_comments),
                "engagement": round(engagement, 2),
                "freshness": round(avg_freshness, 2),
                "competition": round(channel_diversity, 2),
                "score": round(score, 2),
                "top_channels": top_channels,
                "video_patterns": video_patterns,
                "sample_videos": [
                    {
                        "id": v["id"],
                        "title": v["title"],
                        "views": v["view_count"],
                        "engagement_rate": v.get("engagement_rate", 0),
                        "thumbnail": v.get("thumbnail", ""),
                    }
                    for v in sorted(matching_videos, key=lambda x: x["view_count"], reverse=True)[
                        :3
                    ]
                ],
            }
            niches.append(niche_data)

    # Sort niches by score
    niches.sort(key=lambda x: x["score"], reverse=True)

    # Generate visualization guide
    visualization_guide = generate_visualization_guide(niches, category, subcategory)

    # Format for enhanced NicheScoutResult compatibility
    trend_niches = []
    for idx, niche in enumerate(niches):
        trend_niches.append(
            {
                "query": niche["query"],
                "view_sum": niche["view_sum"],
                "avg_views": niche["avg_views"],
                "avg_comments": niche.get("avg_comments", 0),
                "rsv": niche["score"] * 10,  # Approximate relative search volume
                "engagement": niche["engagement"],
                "freshness": niche.get("freshness", 0.5),
                "competition": niche.get("competition", 0.5),
                "view_rank": idx + 1,
                "rsv_rank": idx + 1,
                "score": niche["score"] * 10,
                # Visualization coordinates
                "x": (idx % 5) * 2 - 5,
                "y": (idx // 5) * 2 - 2,
                "niche": idx // 3,
                "sample_videos": niche["sample_videos"],
                "top_channels": niche["top_channels"],
                "video_patterns": niche.get("video_patterns", {}),
            }
        )

    end_time = time.time()
    processing_time = end_time - start_time

    result = {
        "run_date": datetime.now().isoformat(),
        "category": category,
        "subcategory": subcategory,
        "trending_niches": trend_niches,
        "top_niches": trend_niches[:5],
        "actual_processing_time": round(processing_time, 2),
        "actual_cost": 0.05 * len(search_queries),  # Approximate cost based on API usage
        "videos_analyzed": len(all_videos),
        "channels_analyzed": len(channels),
        "visualization_guide": visualization_guide,
        "content_strategies": {
            "title_tips": [
                "Include the main keyword near the beginning of your title",
                "Keep titles between 6-12 words for optimal CTR",
                "Use numbers when relevant (e.g., '5 Ways to...')",
                "Include emotional triggers or questions to increase curiosity",
            ],
            "optimal_duration": identify_video_pattern(all_videos).get("avg_duration", 0),
            "recommended_upload_times": {
                "day": identify_video_pattern(all_videos).get("best_upload_day", "Unknown"),
                "hour": identify_video_pattern(all_videos).get("best_upload_hour", "Unknown"),
            },
            "keyword_recommendations": [kw for kw, _ in sorted_keywords[:10]],
        },
    }

    # Save result to file
    output_file = f"niche-scout-{category}-{subcategory.split('.')[-1]}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Analysis complete in {processing_time:.2f} seconds!")
    print(f"Found {len(trend_niches)} trending niches")
    print(f"Results saved to {output_file}")

    # Also save in localStorage-compatible format for the viewer
    viewer_data = {"results": [result]}
    with open("viewer-ready-results.json", "w") as f:
        json.dump(viewer_data, f, indent=2)

    print("Viewer-ready results saved to viewer-ready-results.json")
    print("Copy this into your browser console to view:")
    print(f"localStorage.setItem('youtube-results', JSON.stringify({json.dumps([result])}))")

    # Print visualization guide
    if visualization_guide.get("chart_file"):
        print(f"\nVisualization created: {visualization_guide['chart_file']}")
        print("Top niche recommendations:")
        for rec in visualization_guide["top_recommendations"]:
            print(f"- {rec['niche']}: {rec['why']}")

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manual Niche Scout Workflow")
    parser.add_argument(
        "--category",
        default="kids",
        help="Content category (e.g., kids, tech, finance, health)",
    )
    parser.add_argument(
        "--subcategory",
        default="kids.nursery",
        help="Content subcategory (e.g., kids.nursery, tech.programming)",
    )
    parser.add_argument(
        "--api-key",
        help="YouTube API Key (optional, will use env variable if not provided)",
    )

    args = parser.parse_args()

    if args.api_key:
        API_KEY = args.api_key

    # Run the analysis
    asyncio.run(analyze_niche(args.category, args.subcategory))
