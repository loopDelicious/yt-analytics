"""
YouTube API client for fetching channel video data and analytics.

Uses two APIs:
- YouTube Data API v3: video metadata (title, duration, publish date, views, likes, comments)
- YouTube Analytics API: per-video analytics (subscribers gained, impressions, CTR, avg % viewed)

Requires OAuth 2.0 credentials. Run setup_youtube.py once to authorize.
"""

import json
import logging
import os
import re
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def _get_credentials():
    """Load OAuth credentials from env var or token file."""
    token_json = os.getenv("YOUTUBE_TOKEN_JSON", "")
    token_file = os.path.join(os.path.dirname(__file__) or ".", ".youtube_token.json")

    creds = None
    if token_json:
        info = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(info, SCOPES)
    elif os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds:
        return None

    if creds.expired and creds.refresh_token:
        log.info("Refreshing expired YouTube API token...")
        creds.refresh(Request())
        if os.path.exists(token_file):
            with open(token_file, "w") as f:
                f.write(creds.to_json())

    return creds


def _parse_duration(iso_duration):
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    if not iso_duration:
        return 0
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return 0
    h, m, s = (int(g) if g else 0 for g in match.groups())
    return h * 3600 + m * 60 + s


def _get_channel_id(youtube):
    """Get the authenticated user's channel ID."""
    resp = youtube.channels().list(part="id", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        return None
    return items[0]["id"]


def _get_uploads_playlist_id(youtube, channel_id):
    """Get the 'uploads' playlist ID for a channel."""
    resp = youtube.channels().list(
        part="contentDetails", id=channel_id
    ).execute()
    items = resp.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _list_all_video_ids(youtube, playlist_id):
    """Page through a playlist and return all video IDs."""
    video_ids = []
    page_token = None
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in resp.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def _get_video_details(youtube, video_ids):
    """Fetch snippet, contentDetails, and statistics for a list of video IDs."""
    details = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        resp = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(batch),
        ).execute()
        for item in resp.get("items", []):
            vid = item["id"]
            snippet = item["snippet"]
            content = item["contentDetails"]
            stats = item.get("statistics", {})
            details[vid] = {
                "title": snippet.get("title", ""),
                "published_at": snippet.get("publishedAt", ""),
                "duration_sec": _parse_duration(content.get("duration", "")),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
            }
    return details


def _get_analytics(analytics, channel_id, video_ids, start_date="2020-01-01"):
    """Fetch per-video analytics from the YouTube Analytics API."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    results = {}

    for i in range(0, len(video_ids), 200):
        batch = video_ids[i : i + 200]
        filters = "video==" + ",".join(batch)
        try:
            resp = analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate=start_date,
                endDate=end_date,
                metrics="subscribersGained,averageViewPercentage,likes,dislikes,impressions,impressionClickThroughRate",
                dimensions="video",
                filters=filters,
                maxResults=200,
            ).execute()
        except Exception as e:
            log.warning("Analytics API error for batch: %s", e)
            continue

        for row in resp.get("rows", []):
            vid = row[0]
            subs_gained = row[1]
            avg_view_pct = row[2]
            likes = row[3]
            dislikes = row[4]
            impressions = row[5]
            ctr = row[6]
            total_votes = likes + dislikes
            like_ratio = round(likes / total_votes * 100, 2) if total_votes > 0 else 0
            results[vid] = {
                "subscribers": subs_gained,
                "avg_pct_viewed": round(avg_view_pct, 2),
                "like_ratio": like_ratio,
                "impressions": impressions,
                "ctr": round(ctr, 2),
            }

    return results


def is_available():
    """Check if YouTube API credentials are configured."""
    return _get_credentials() is not None


def fetch_channel_data():
    """
    Fetch all video data from the YouTube APIs.
    Returns (videos, snapshot_date_str, totals) matching the xlsx format.
    """
    creds = _get_credentials()
    if not creds:
        log.error("No YouTube API credentials found.")
        return [], "", None

    youtube = build("youtube", "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)

    channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "") or _get_channel_id(youtube)
    if not channel_id:
        log.error("Could not determine channel ID.")
        return [], "", None

    log.info("Fetching videos for channel %s...", channel_id)
    uploads_id = _get_uploads_playlist_id(youtube, channel_id)
    if not uploads_id:
        log.error("Could not find uploads playlist.")
        return [], "", None

    video_ids = _list_all_video_ids(youtube, uploads_id)
    log.info("Found %d videos", len(video_ids))

    video_details = _get_video_details(youtube, video_ids)
    log.info("Fetched details for %d videos", len(video_details))

    analytics_data = _get_analytics(analytics, channel_id, video_ids)
    log.info("Fetched analytics for %d videos", len(analytics_data))

    snapshot_date_str = datetime.now().strftime("%B %d, %Y")
    videos = []
    for vid in video_ids:
        detail = video_details.get(vid)
        if not detail:
            continue
        analytic = analytics_data.get(vid, {})

        published_at = detail["published_at"]
        try:
            pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            publish_time = pub_dt.strftime("%b %d, %Y")
            publish_date = pub_dt.replace(tzinfo=None)
        except (ValueError, AttributeError):
            publish_time = ""
            publish_date = None

        views = detail["views"]
        subscribers = analytic.get("subscribers", 0)

        videos.append({
            "id": vid,
            "title": detail["title"],
            "publish_time": publish_time,
            "publish_date": publish_date,
            "duration_sec": detail["duration_sec"],
            "is_short": False,
            "likes": detail["likes"],
            "comments": detail["comments"],
            "avg_pct_viewed": analytic.get("avg_pct_viewed", 0),
            "like_ratio": analytic.get("like_ratio", 0),
            "views": views,
            "subscribers": subscribers,
            "subs_views_ratio": round(subscribers / views * 100, 2) if views else 0,
            "impressions": analytic.get("impressions", 0),
            "ctr": analytic.get("ctr", 0),
        })

    totals = {
        "likes": sum(v["likes"] for v in videos),
        "comments": sum(v["comments"] for v in videos),
        "avg_pct_viewed": round(sum(v["avg_pct_viewed"] for v in videos) / len(videos), 2) if videos else 0,
        "like_ratio": round(sum(v["like_ratio"] for v in videos) / len(videos), 2) if videos else 0,
        "views": sum(v["views"] for v in videos),
        "subscribers": sum(v["subscribers"] for v in videos),
        "impressions": sum(v["impressions"] for v in videos),
        "ctr": round(sum(v["ctr"] for v in videos) / len(videos), 2) if videos else 0,
    }

    log.info("YouTube API: loaded %d videos, %d total subs gained", len(videos), totals["subscribers"])
    return videos, snapshot_date_str, totals
