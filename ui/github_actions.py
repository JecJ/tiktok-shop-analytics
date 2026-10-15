"""Small GitHub Actions variable updater for the local dashboard."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OWNER = "JecJ"
REPOSITORY = "tiktok-shop-analytics"
API_ROOT = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/actions/variables"
SUPPORTED_MARKETS = {"US", "TH", "MX", "BR", "VN", "PH", "MY", "ID", "SG", "JP", "GB", "ES", "DE", "IT", "FR"}


def _request(token: str, method: str, url: str, payload: dict | None = None) -> int:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, method=method, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "tiktok-shop-analytics-local-dashboard",
    })
    try:
        with urlopen(req, timeout=15) as response:
            return response.status
    except HTTPError as exc:
        if exc.code == 404 and method == "PATCH":
            return _request(token, "POST", API_ROOT, {
                "name": url.rsplit("/", 1)[-1],
                "value": payload["value"],
            })
        if exc.code in (401, 403):
            raise RuntimeError("GitHub Token 无效或没有仓库 Actions 变量的写入权限（需要 Actions: write）。") from exc
        raise RuntimeError(f"GitHub 返回 HTTP {exc.code}，请检查仓库权限和网络。") from exc
    except URLError as exc:
        raise RuntimeError(f"无法连接 GitHub API：{exc.reason}") from exc


def sync_daily_settings(token: str, region: str, keywords: str) -> None:
    token = token.strip()
    if not token:
        raise ValueError("请粘贴 GitHub Fine-grained Token。")
    region = region.strip().upper()
    if region not in SUPPORTED_MARKETS:
        raise ValueError(f"暂不支持市场代码：{region}")
    keywords = ",".join(part.strip() for part in keywords.split(",") if part.strip())
    if not keywords:
        raise ValueError("请至少填写一个英文搜索关键词。")
    if len(keywords) > 500:
        raise ValueError("关键词总长度不能超过 500 个字符。")
    for name, value in (("DAILY_MARKET", region), ("DAILY_KEYWORDS", keywords)):
        _request(token, "PATCH", f"{API_ROOT}/{name}", {"value": value})
