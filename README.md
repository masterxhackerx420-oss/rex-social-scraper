# Rex's Social Scraper

Ethical multi-platform social reader for 13 platforms. Public posts need no login. Your own account is available only when you add that platform's official API key.

No login bypass. No CAPTCHA bypass. No one else's private data.

**Live page:** https://htmlpreview.github.io/?https://github.com/masterxhackerx420-oss/rex-social-scraper/blob/main/docs/index.html

## Install

| System | Download |
| --- | --- |
| Android | [rex-social-scraper-android.zip](https://github.com/masterxhackerx420-oss/rex-social-scraper/releases/download/v1.0.0/rex-social-scraper-android.zip) |
| Windows | [rex-social-scraper-windows.zip](https://github.com/masterxhackerx420-oss/rex-social-scraper/releases/download/v1.0.0/rex-social-scraper-windows.zip) |
| Linux | [rex-social-scraper-linux.zip](https://github.com/masterxhackerx420-oss/rex-social-scraper/releases/download/v1.0.0/rex-social-scraper-linux.zip) |

Android also installs as an app from the live page: Chrome menu, then Install app or Add to Home screen. The zip is the Termux command-line reader.

Windows: unzip, then run `install/windows.ps1` in PowerShell. Python 3.9 or newer.

Linux, no root:

```sh
unzip rex-social-scraper-linux.zip
sh install/linux.sh
rex-social-scraper --platform bluesky,reddit,mastodon --query python --limit 10
```

## Keys

Copy nothing until you need a platform that requires one. Put them in a `.env` next to the command, or export them in the shell. The live page stores keys only in your browser and sends them only to the official API.

`YOUTUBE_API_KEY` `TWITTER_BEARER_TOKEN` `INSTAGRAM_ACCESS_TOKEN` `FACEBOOK_ACCESS_TOKEN` `TIKTOK_ACCESS_TOKEN` `LINKEDIN_ACCESS_TOKEN` `THREADS_ACCESS_TOKEN` `PINTEREST_ACCESS_TOKEN` `TWITCH_CLIENT_ID` `TWITCH_ACCESS_TOKEN` `TUMBLR_API_KEY` `MASTODON_INSTANCE` `MASTODON_ACCESS_TOKEN` `BLUESKY_HANDLE` `BLUESKY_APP_PASSWORD`

Use `*` as the query for your own feed where the platform allows it (Bluesky app password, Mastodon token, Instagram, Facebook, Threads, your TikTok videos, your Pinterest pins).

## Ethics

Respect each platform's terms and `robots.txt`. The reader waits one second between platforms and stops on HTTP 429. Public data, or your own account through the official API.

MIT. See LICENSE.
