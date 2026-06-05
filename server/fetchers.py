import re
from dataclasses import dataclass
from typing import Optional

import httpx
import instaloader


@dataclass
class CountResult:
    platform: str
    username: str
    followers: Optional[int]
    error: Optional[str] = None


def _format_count(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,}"


def fetch_instagram(username: str) -> CountResult:
    try:
        loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )
        profile = instaloader.Profile.from_username(loader.context, username)
        return CountResult("instagram", username, profile.followers)
    except instaloader.exceptions.ProfileNotExistsException:
        return CountResult("instagram", username, None, "Profile not found")
    except Exception as exc:  # noqa: BLE001
        return CountResult("instagram", username, None, str(exc))


def fetch_tiktok(username: str) -> CountResult:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(f"https://www.tiktok.com/@{username}", headers=headers)
            response.raise_for_status()
            html = response.text

        match = re.search(r'"followerCount":(\d+)', html)
        if match:
            return CountResult("tiktok", username, int(match.group(1)))

        match = re.search(r'"stats":\{"followerCount":(\d+)', html)
        if match:
            return CountResult("tiktok", username, int(match.group(1)))

        return CountResult("tiktok", username, None, "Could not parse follower count from page")
    except Exception as exc:  # noqa: BLE001
        return CountResult("tiktok", username, None, str(exc))


def result_to_dict(result: CountResult) -> dict:
    payload = {
        "platform": result.platform,
        "username": result.username,
        "followers": result.followers,
        "display": _format_count(result.followers) if result.followers is not None else None,
    }
    if result.error:
        payload["error"] = result.error
    return payload
