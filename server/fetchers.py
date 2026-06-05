import re
import time
from dataclasses import dataclass
from typing import Optional

import httpx


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


def _parse_instagram_profile_response(response: httpx.Response, username: str) -> CountResult:
    if response.status_code == 404:
        return CountResult("instagram", username, None, "Profile not found")

    if response.status_code == 429:
        return CountResult("instagram", username, None, "Rate limited by Instagram")

    response.raise_for_status()
    data = response.json()
    user = data.get("data", {}).get("user")
    if not user:
        return CountResult("instagram", username, None, "Profile not found")

    followers = user.get("edge_followed_by", {}).get("count")
    if followers is None:
        return CountResult("instagram", username, None, "Could not parse follower count")

    return CountResult("instagram", username, int(followers))


def fetch_instagram(username: str) -> CountResult:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
    }
    endpoints = [
        "https://www.instagram.com/api/v1/users/web_profile_info/",
        "https://i.instagram.com/api/v1/users/web_profile_info/",
    ]

    last_error = "Could not fetch Instagram profile"

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            for attempt in range(3):
                for endpoint in endpoints:
                    response = client.get(
                        endpoint,
                        params={"username": username},
                        headers=headers,
                    )
                    result = _parse_instagram_profile_response(response, username)

                    if result.followers is not None:
                        return result

                    if result.error:
                        last_error = result.error

                    if response.status_code == 429:
                        time.sleep(2 ** attempt)

        return CountResult("instagram", username, None, last_error)
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
