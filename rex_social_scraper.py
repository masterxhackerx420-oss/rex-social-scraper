#!/usr/bin/env python3
"""Rex's Social Scraper — public posts, or your own account via official APIs.

No login bypass. No CAPTCHA bypass. No one else's private data.
Stdlib only. One second between platforms.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "RexSocialScraper/1.0 (ethical public reader; official APIs only)"
LIMIT_MAX = 100

PLATFORMS = [
    ("bluesky", "none, or BLUESKY_HANDLE + BLUESKY_APP_PASSWORD", "Public AT Protocol. * with an app password reads your timeline."),
    ("reddit", "none", "Public JSON. r/subreddit or a search. * is r/popular."),
    ("mastodon", "none, or MASTODON_ACCESS_TOKEN", "Public tags. Token unlocks home and phrase search. MASTODON_INSTANCE optional."),
    ("youtube", "YOUTUBE_API_KEY", "Data API v3."),
    ("twitter", "TWITTER_BEARER_TOKEN", "API v2 recent public search. * is not supported."),
    ("instagram", "INSTAGRAM_ACCESS_TOKEN", "Graph API — your media. * is your recent media."),
    ("facebook", "FACEBOOK_ACCESS_TOKEN", "Graph API — your feed."),
    ("tiktok", "TIKTOK_ACCESS_TOKEN", "Your videos with *, or Research API for a keyword."),
    ("linkedin", "LINKEDIN_ACCESS_TOKEN", "Your member posts, when the token scope allows."),
    ("threads", "THREADS_ACCESS_TOKEN", "Threads API — your posts."),
    ("pinterest", "PINTEREST_ACCESS_TOKEN", "API v5. * lists your pins."),
    ("twitch", "TWITCH_CLIENT_ID + TWITCH_ACCESS_TOKEN", "Helix search. * lists live streams."),
    ("tumblr", "TUMBLR_API_KEY", "Public tagged posts. * is not supported."),
]


def load_dotenv() -> None:
    path = Path(".env")
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str) -> str:
    return os.environ.get(name, "").strip()


def scrub(text: str, secrets: list[str]) -> str:
    out = " ".join(text.split())
    for secret in secrets:
        if len(secret) > 3:
            out = out.replace(secret, "••••")
    return out[:280]


def request(url: str, method: str = "GET", body: bytes | None = None, headers: dict | None = None, secrets: list[str] | None = None):
    hdrs = {"Accept": "application/json", "User-Agent": UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:180]
        extra = " This network blocked the request." if exc.code == 403 else ""
        raise RuntimeError(scrub(f"HTTP {exc.code}.{extra} {detail}", secrets or [])) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(scrub(str(exc.reason), secrets or [])) from None


def clean_instance(raw: str) -> str:
    host = raw.strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0].split(":")[0]
    blocked = (
        not host
        or host in {"localhost"}
        or host.endswith(".local")
        or host.endswith(".internal")
        or re.match(r"^(127\.|10\.|192\.168\.|169\.254\.|0\.|metadata)", host)
        or re.match(r"^172\.(1[6-9]|2\d|3[0-1])\.", host)
    )
    if blocked or not re.fullmatch(r"[a-z0-9.-]{1,253}", host) or ".." in host:
        return "mastodon.social"
    return host


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()


def post(**kwargs) -> dict:
    return kwargs


def keep(rows: list[dict], query: str, limit: int) -> list[dict]:
    if query and query != "*":
        needle = query.lower()
        rows = [row for row in rows if needle in (row.get("text") or "").lower()]
    return rows[:limit]


def bluesky(query: str, limit: int) -> tuple[list[dict], str]:
    handle, password = env("BLUESKY_HANDLE"), env("BLUESKY_APP_PASSWORD")
    jwt = ""
    via = "public"
    if handle and password:
        session = request(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            "POST",
            json.dumps({"identifier": handle, "password": password}).encode(),
            {"Content-Type": "application/json"},
            [handle, password],
        )
        jwt = session.get("accessJwt") or ""
        via = "your-key"
    headers = {"Authorization": f"Bearer {jwt}"} if jwt else None
    if query == "*" and jwt:
        data = request(f"https://bsky.social/xrpc/app.bsky.feed.getTimeline?limit={limit}", headers=headers, secrets=[password])
        rows = data.get("feed") or []
        posts = []
        for item in rows:
            posts.extend(bsky_post(item.get("post") or {}, via))
        return posts[:limit], via
    if query == "*":
        feed = urllib.parse.quote("at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot")
        data = request(f"https://api.bsky.app/xrpc/app.bsky.feed.getFeed?feed={feed}&limit={limit}")
        return [p for item in data.get("feed") or [] for p in bsky_post(item.get("post") or {}, via)][:limit], via
    data = request(
        f"https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={urllib.parse.quote(query)}&limit={limit}",
        headers=headers,
    )
    return [p for item in data.get("posts") or [] for p in bsky_post(item, via)][:limit], via


def bsky_post(row: dict, via: str) -> list[dict]:
    author = row.get("author") or {}
    record = row.get("record") or {}
    handle = author.get("handle") or ""
    uri = row.get("uri") or ""
    rkey = uri.split("/")[-1] if uri else ""
    text = record.get("text") or ""
    if not text and not uri:
        return []
    return [post(
        platform="bluesky",
        author=author.get("displayName") or handle or "Bluesky",
        handle=f"@{handle}" if handle else "",
        text=text,
        url=f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else "https://bsky.app",
        createdAt=record.get("createdAt"),
        likes=row.get("likeCount"),
        replies=row.get("replyCount"),
        reposts=row.get("repostCount"),
        via=via,
    )]


def reddit(query: str, limit: int) -> tuple[list[dict], str]:
    match = re.fullmatch(r"r/([A-Za-z0-9_]{2,21})", query.strip())
    if query == "*":
        url = f"https://www.reddit.com/r/popular/hot.json?limit={limit}&raw_json=1"
    elif match:
        url = f"https://www.reddit.com/r/{match.group(1)}/hot.json?limit={limit}&raw_json=1"
    else:
        url = f"https://www.reddit.com/search.json?q={urllib.parse.quote(query)}&limit={limit}&sort=new&type=link&raw_json=1"
    try:
        data = request(url)
    except RuntimeError as exc:
        raise RuntimeError(f"{exc} Reddit often blocks datacenters; this build uses your own connection.") from None
    children = ((data.get("data") or {}).get("children") or [])
    rows = []
    for child in children:
        row = child.get("data") or {}
        title = row.get("title") or ""
        body = row.get("selftext") or ""
        permalink = row.get("permalink") or ""
        created = row.get("created_utc")
        rows.append(post(
            platform="reddit",
            author=f"u/{row.get('author')}" if row.get("author") else "Reddit",
            handle=row.get("subreddit_name_prefixed") or "",
            text="\n\n".join(part for part in (title, body) if part),
            url=f"https://www.reddit.com{permalink}" if permalink else "https://www.reddit.com",
            createdAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created)) if created else None,
            likes=row.get("score"),
            replies=row.get("num_comments"),
            reposts=None,
            via="public",
        ))
    return rows[:limit], "public"


def mastodon(query: str, limit: int) -> tuple[list[dict], str]:
    instance = clean_instance(env("MASTODON_INSTANCE") or "mastodon.social")
    token = env("MASTODON_ACCESS_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    via = "your-key" if token else "public"
    tag = re.sub(r"[^A-Za-z0-9_]", "", query.lstrip("#").split()[0] if query.strip() else "")
    if not token and query != "*" and not tag:
        raise RuntimeError("Public Mastodon reads a tag. Add MASTODON_ACCESS_TOKEN to search phrases.")
    posts: list[dict] = []
    max_id = ""
    offset = 0
    while len(posts) < limit:
        size = min(40, limit - len(posts))
        if query == "*" and token:
            url = f"https://{instance}/api/v1/timelines/home?limit={size}"
        elif query == "*":
            url = f"https://{instance}/api/v1/timelines/public?limit={size}"
        elif token:
            url = f"https://{instance}/api/v2/search?type=statuses&limit={size}&offset={offset}&q={urllib.parse.quote(query)}"
        else:
            url = f"https://{instance}/api/v1/timelines/tag/{urllib.parse.quote(tag)}?limit={size}"
        if (query == "*" or not token) and max_id:
            url += f"&max_id={urllib.parse.quote(max_id)}"
        data = request(url, headers=headers, secrets=[token])
        rows = data if isinstance(data, list) else data.get("statuses") or []
        if not rows:
            break
        for row in rows:
            account = row.get("account") or {}
            posts.append(post(
                platform="mastodon",
                author=account.get("display_name") or account.get("username") or "Mastodon",
                handle=f"@{account.get('acct')}" if account.get("acct") else "",
                text=strip_html(row.get("content") or row.get("spoiler_text") or ""),
                url=row.get("url") or account.get("url") or f"https://{instance}",
                createdAt=row.get("created_at"),
                likes=row.get("favourites_count"),
                replies=row.get("replies_count"),
                reposts=row.get("reblogs_count"),
                via=via,
                id=str(row.get("id") or ""),
            ))
        if token and query != "*":
            offset += len(rows)
            if len(rows) < size:
                break
        else:
            nxt = str(rows[-1].get("id") or "")
            if not nxt or nxt == max_id:
                break
            max_id = nxt
    return posts[:limit], via


def youtube(query: str, limit: int) -> tuple[list[dict], str]:
    api_key = env("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("Set YOUTUBE_API_KEY.")
    rows: list[dict] = []
    page = ""
    while len(rows) < limit:
        size = min(50, limit - len(rows))
        if query == "*":
            url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&chart=mostPopular&maxResults={size}&key={urllib.parse.quote(api_key)}"
        else:
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults={size}&q={urllib.parse.quote(query)}&key={urllib.parse.quote(api_key)}"
        if page:
            url += f"&pageToken={urllib.parse.quote(page)}"
        data = request(url, secrets=[api_key])
        items = data.get("items") or []
        if not items:
            break
        for item in items:
            snippet = item.get("snippet") or {}
            video_id = (item.get("id") or {}).get("videoId") if isinstance(item.get("id"), dict) else item.get("id")
            if not video_id:
                continue
            rows.append(post(
                platform="youtube",
                author=snippet.get("channelTitle") or "YouTube",
                handle="",
                text="\n\n".join(part for part in (snippet.get("title"), snippet.get("description")) if part),
                url=f"https://www.youtube.com/watch?v={video_id}",
                createdAt=snippet.get("publishedAt"),
                likes=None, replies=None, reposts=None, via="your-key",
            ))
        page = data.get("nextPageToken") or ""
        if not page:
            break
    return rows[:limit], "your-key"


def twitter(query: str, limit: int) -> tuple[list[dict], str]:
    token = env("TWITTER_BEARER_TOKEN")
    if not token:
        raise RuntimeError("Set TWITTER_BEARER_TOKEN.")
    if query == "*":
        raise RuntimeError("X recent search needs a keyword. A bearer token does not open private accounts.")
    max_results = min(100, max(10, limit))
    url = (
        "https://api.twitter.com/2/tweets/search/recent?tweet.fields=created_at,public_metrics,author_id"
        f"&expansions=author_id&user.fields=name,username&max_results={max_results}&query={urllib.parse.quote(query)}"
    )
    data = request(url, headers={"Authorization": f"Bearer {token}"}, secrets=[token])
    users = {u.get("id"): u for u in ((data.get("includes") or {}).get("users") or [])}
    rows = []
    for row in data.get("data") or []:
        user = users.get(row.get("author_id")) or {}
        metrics = row.get("public_metrics") or {}
        username = user.get("username") or ""
        rows.append(post(
            platform="twitter",
            author=user.get("name") or username or "X",
            handle=f"@{username}" if username else "",
            text=row.get("text") or "",
            url=f"https://x.com/{username}/status/{row.get('id')}" if username else f"https://x.com/i/status/{row.get('id')}",
            createdAt=row.get("created_at"),
            likes=metrics.get("like_count"),
            replies=metrics.get("reply_count"),
            reposts=metrics.get("retweet_count"),
            via="your-key",
        ))
    return rows[:limit], "your-key"


def graph_own(url: str, token: str, platform: str, query: str, limit: int, text_key: str, url_key: str) -> tuple[list[dict], str]:
    data = request(url, secrets=[token])
    rows = []
    for row in data.get("data") or []:
        text = row.get(text_key) or ""
        rows.append(post(
            platform=platform,
            author=row.get("username") or row.get("from", {}).get("name") or platform.title(),
            handle=f"@{row['username']}" if row.get("username") else "",
            text=text,
            url=row.get(url_key) or f"https://www.{platform}.com",
            createdAt=row.get("timestamp") or row.get("created_time"),
            likes=None, replies=None, reposts=None, via="your-key",
        ))
    return keep(rows, query, limit), "your-key"


def instagram(query: str, limit: int) -> tuple[list[dict], str]:
    token = env("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Set INSTAGRAM_ACCESS_TOKEN.")
    url = f"https://graph.instagram.com/me/media?fields=id,caption,permalink,timestamp,username&limit={limit}&access_token={urllib.parse.quote(token)}"
    return graph_own(url, token, "instagram", query, limit, "caption", "permalink")


def facebook(query: str, limit: int) -> tuple[list[dict], str]:
    token = env("FACEBOOK_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Set FACEBOOK_ACCESS_TOKEN.")
    url = f"https://graph.facebook.com/v21.0/me/feed?fields=id,message,created_time,permalink_url,from&limit={limit}&access_token={urllib.parse.quote(token)}"
    return graph_own(url, token, "facebook", query, limit, "message", "permalink_url")


def threads(query: str, limit: int) -> tuple[list[dict], str]:
    token = env("THREADS_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Set THREADS_ACCESS_TOKEN.")
    url = f"https://graph.threads.net/v1.0/me/threads?fields=id,text,timestamp,permalink,username&limit={limit}&access_token={urllib.parse.quote(token)}"
    return graph_own(url, token, "threads", query, limit, "text", "permalink")


def tiktok(query: str, limit: int) -> tuple[list[dict], str]:
    token = env("TIKTOK_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Set TIKTOK_ACCESS_TOKEN.")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if query == "*":
        data = request(
            "https://open.tiktokapis.com/v2/video/list/?fields=id,title,video_description,share_url,create_time",
            "POST",
            json.dumps({"max_count": min(20, limit)}).encode(),
            headers,
            [token],
        )
        videos = ((data.get("data") or {}).get("videos") or [])
        rows = [post(platform="tiktok", author="TikTok", handle="", text=v.get("title") or v.get("video_description") or "", url=v.get("share_url") or "https://www.tiktok.com", createdAt=None, likes=None, replies=None, reposts=None, via="your-key") for v in videos]
        return rows[:limit], "your-key"
    end = time.strftime("%Y%m%d", time.gmtime())
    start = time.strftime("%Y%m%d", time.gmtime(time.time() - 7 * 86400))
    body = {
        "query": {"and": [{"operation": "EQ", "field_name": "keyword", "field_values": [query]}]},
        "max_count": min(20, limit),
        "start_date": start,
        "end_date": end,
    }
    data = request(
        "https://open.tiktokapis.com/v2/research/video/query/?fields=id,video_description,share_url,like_count,comment_count,share_count",
        "POST",
        json.dumps(body).encode(),
        headers,
        [token],
    )
    videos = ((data.get("data") or {}).get("videos") or [])
    rows = [post(platform="tiktok", author="TikTok", handle="", text=v.get("video_description") or "", url=v.get("share_url") or "https://www.tiktok.com", createdAt=None, likes=v.get("like_count"), replies=v.get("comment_count"), reposts=v.get("share_count"), via="your-key") for v in videos]
    return rows[:limit], "your-key"


def linkedin(query: str, limit: int) -> tuple[list[dict], str]:
    token = env("LINKEDIN_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Set LINKEDIN_ACCESS_TOKEN.")
    headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0", "LinkedIn-Version": "202510"}
    me = request("https://api.linkedin.com/v2/userinfo", headers=headers, secrets=[token])
    sub = me.get("sub")
    if not sub:
        raise RuntimeError("LinkedIn did not return a member id for this token.")
    author = urllib.parse.quote(f"urn:li:person:{sub}")
    data = request(f"https://api.linkedin.com/rest/posts?author={author}&q=author&count={limit}", headers=headers, secrets=[token])
    rows = [post(platform="linkedin", author="LinkedIn", handle="", text=item.get("commentary") or "", url="https://www.linkedin.com/feed/", createdAt=None, likes=None, replies=None, reposts=None, via="your-key") for item in data.get("elements") or []]
    return keep(rows, query, limit), "your-key"


def pinterest(query: str, limit: int) -> tuple[list[dict], str]:
    token = env("PINTEREST_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Set PINTEREST_ACCESS_TOKEN.")
    headers = {"Authorization": f"Bearer {token}"}
    if query == "*":
        url = f"https://api.pinterest.com/v5/pins?page_size={limit}"
    else:
        url = f"https://api.pinterest.com/v5/search/pins?page_size={limit}&query={urllib.parse.quote(query)}"
    data = request(url, headers=headers, secrets=[token])
    rows = [post(platform="pinterest", author="Pinterest", handle="", text=item.get("title") or item.get("description") or "", url=item.get("link") or "https://www.pinterest.com", createdAt=item.get("created_at"), likes=None, replies=None, reposts=None, via="your-key") for item in data.get("items") or []]
    return rows[:limit], "your-key"


def twitch(query: str, limit: int) -> tuple[list[dict], str]:
    client, token = env("TWITCH_CLIENT_ID"), env("TWITCH_ACCESS_TOKEN")
    if not client or not token:
        raise RuntimeError("Set TWITCH_CLIENT_ID and TWITCH_ACCESS_TOKEN.")
    headers = {"Client-Id": client, "Authorization": f"Bearer {token}"}
    if query == "*":
        url = f"https://api.twitch.tv/helix/streams?first={limit}"
    else:
        url = f"https://api.twitch.tv/helix/search/channels?first={limit}&query={urllib.parse.quote(query)}"
    data = request(url, headers=headers, secrets=[client, token])
    rows = []
    for row in data.get("data") or []:
        login = row.get("broadcaster_login") or row.get("user_login") or ""
        name = row.get("display_name") or row.get("user_name") or login or "Twitch"
        rows.append(post(platform="twitch", author=name, handle=f"@{login}" if login else "", text=row.get("title") or row.get("game_name") or name, url=f"https://www.twitch.tv/{login}" if login else "https://www.twitch.tv", createdAt=row.get("started_at"), likes=None, replies=None, reposts=None, via="your-key"))
    return rows[:limit], "your-key"


def tumblr(query: str, limit: int) -> tuple[list[dict], str]:
    api_key = env("TUMBLR_API_KEY")
    if not api_key:
        raise RuntimeError("Set TUMBLR_API_KEY.")
    if query == "*":
        raise RuntimeError("Tumblr's tagged API needs a tag.")
    tag = query.lstrip("#").strip()
    data = request(f"https://api.tumblr.com/v2/tagged?tag={urllib.parse.quote(tag)}&limit={limit}&api_key={urllib.parse.quote(api_key)}", secrets=[api_key])
    rows = []
    for row in (data.get("response") or []):
        rows.append(post(
            platform="tumblr",
            author=row.get("blog_name") or "Tumblr",
            handle=f"@{row.get('blog_name')}" if row.get("blog_name") else "",
            text=strip_html(row.get("summary") or row.get("caption") or row.get("title") or ""),
            url=row.get("post_url") or "https://www.tumblr.com",
            createdAt=row.get("date"),
            likes=row.get("note_count"),
            replies=None, reposts=None, via="your-key",
        ))
    return rows[:limit], "your-key"


RUNNERS = {
    "bluesky": bluesky,
    "reddit": reddit,
    "mastodon": mastodon,
    "youtube": youtube,
    "twitter": twitter,
    "instagram": instagram,
    "facebook": facebook,
    "tiktok": tiktok,
    "linkedin": linkedin,
    "threads": threads,
    "pinterest": pinterest,
    "twitch": twitch,
    "tumblr": tumblr,
}


def scrape(platforms: list[str], query: str, limit: int) -> list[dict]:
    posts: list[dict] = []
    for index, name in enumerate(platforms):
        if index:
            time.sleep(1)
        runner = RUNNERS.get(name)
        if not runner:
            posts.append({"platform": name, "error": "Unknown platform", "via": "public"})
            continue
        try:
            rows, via = runner(query, limit)
            print(f"{name}: {len(rows)} posts ({via})", file=sys.stderr)
            posts.extend(rows)
        except RuntimeError as exc:
            print(f"{name}: {exc}", file=sys.stderr)
            posts.append({"platform": name, "error": str(exc), "via": "public", "text": "", "url": ""})
    return posts


def save(posts: list[dict], path: str) -> None:
    if path.endswith(".csv"):
        fields = ["platform", "author", "handle", "createdAt", "likes", "replies", "reposts", "url", "text", "error", "via"]
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(posts)
    else:
        Path(path).write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Rex's Social Scraper — public data or your own official API keys.")
    parser.add_argument("--platform", default="bluesky,mastodon", help="Comma list, or all")
    parser.add_argument("--query", default="python")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", default="")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        for name, auth, note in PLATFORMS:
            print(f"{name:12} {auth:48} {note}")
        return 0
    chosen = [item[0] for item in PLATFORMS] if args.platform.strip() == "all" else [part.strip().lower() for part in args.platform.split(",") if part.strip()]
    if args.platform.strip() == "all":
        chosen = [name for name, _auth, _note in PLATFORMS if name in {"bluesky", "reddit", "mastodon"} or env({
            "youtube": "YOUTUBE_API_KEY",
            "twitter": "TWITTER_BEARER_TOKEN",
            "instagram": "INSTAGRAM_ACCESS_TOKEN",
            "facebook": "FACEBOOK_ACCESS_TOKEN",
            "tiktok": "TIKTOK_ACCESS_TOKEN",
            "linkedin": "LINKEDIN_ACCESS_TOKEN",
            "threads": "THREADS_ACCESS_TOKEN",
            "pinterest": "PINTEREST_ACCESS_TOKEN",
            "twitch": "TWITCH_CLIENT_ID",
            "tumblr": "TUMBLR_API_KEY",
        }.get(name, ""))]
        if env("TWITCH_CLIENT_ID") and not env("TWITCH_ACCESS_TOKEN"):
            chosen = [name for name in chosen if name != "twitch"]
    limit = min(LIMIT_MAX, max(1, args.limit))
    query = args.query.strip()[:200]
    if not query or not chosen:
        print("Need a query and at least one platform.", file=sys.stderr)
        return 2
    posts = scrape(chosen, query, limit)
    text = json.dumps(posts, indent=2, ensure_ascii=False)
    if args.output:
        save(posts, args.output)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
