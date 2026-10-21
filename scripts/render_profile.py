#!/usr/bin/env python3
"""Render self-contained SVG artwork for the GitHub profile README.

Uses the GitHub GraphQL contributions calendar and a public profile avatar.
No personal access token or third-party stats/image service is required.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "haksuperman")
PROFILE_NAME = "Haksu Park"
AVATAR_URL = "https://avatars.githubusercontent.com/u/159994285?v=4"

BG = "#0d1117"
SURFACE = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
GREEN = "#39d353"


def esc(value: object) -> str:
    return html.escape(str(value), quote=False)


def label(x: float, y: float, value: object, size: int = 18,
          color: str = TEXT, anchor: str = "start", extra: str = "") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Consolas,Menlo,monospace" '
        f'font-size="{size}" fill="{color}" text-anchor="{anchor}" {extra}>'
        f'{esc(value)}</text>'
    )


def svg(width: int, height: int, body: str, description: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{html.escape(description, quote=True)}">'
        f'<rect width="{width}" height="{height}" rx="14" fill="{BG}"/>'
        f'{body}</svg>\n'
    )


def calendar_from_github() -> dict:
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN is required (provided by GitHub Actions).")
    if not re.fullmatch(r"[A-Za-z0-9-]+", USERNAME):
        raise ValueError("Unexpected GitHub username")

    query = (
        f'query {{ user(login: "{USERNAME}") {{ contributionsCollection {{ '
        'contributionCalendar { totalContributions weeks { contributionDays { '
        'date contributionCount color } } } } } } }'
    )
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-svg-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError("GitHub GraphQL: " + json.dumps(payload["errors"]))
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def all_days(calendar: dict) -> list[dict]:
    return sorted(
        (day for week in calendar["weeks"] for day in week["contributionDays"]),
        key=lambda day: day["date"],
    )


def render_heatmap(calendar: dict) -> None:
    body = label(26, 33, f"{USERNAME} / contribution activity", 18, GREEN)
    for x, week in enumerate(calendar["weeks"]):
        for day in week["contributionDays"]:
            # Python weekday: Mon=0; GitHub calendar: Sun=0.
            y = (date.fromisoformat(day["date"]).weekday() + 1) % 7
            color = day.get("color", "")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                color = GREEN
            if day["contributionCount"] == 0:
                color = SURFACE
            tooltip = f'{day["date"]}: {day["contributionCount"]} contributions'
            body += (
                f'<rect x="{26 + x * 15}" y="{55 + y * 15}" width="11" '
                f'height="11" rx="2" fill="{color}">'
                f'<title>{esc(tooltip)}</title>'
                f'<animate attributeName="opacity" values=".55;1" '
                f'begin="{x * .018:.3f}s" dur=".5s" fill="freeze"/></rect>'
            )
    body += label(
        26, 194,
        f'{calendar["totalContributions"]} contributions in the past year',
        14, MUTED,
    )
    (ROOT / "contrib-heatmap.svg").write_text(
        svg(860, 215, body, "GitHub contribution calendar"), encoding="utf-8"
    )


def terminal(command: str, height: int = 880) -> str:
    body = (
        f'<rect x=".5" y=".5" width="839" height="{height - 1}" '
        f'rx="12" fill="none" stroke="{BORDER}"/>'
        f'<path d="M0 30H840" stroke="{BORDER}"/>'
    )
    for index, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        body += f'<circle cx="{20 + 16 * index}" cy="15" r="5" fill="{color}"/>'
    body += label(420, 20, f"{USERNAME}@github:~$ {command}", 13, MUTED, "middle")
    return body


def load_avatar() -> Image.Image:
    # Upload source-photo.png in the repository to override the GitHub avatar.
    image_path = ROOT / "source-photo.png"
    if image_path.is_file():
        return Image.open(image_path).convert("RGB")
    request = urllib.request.Request(
        AVATAR_URL, headers={"User-Agent": "profile-svg-generator"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        image_bytes = response.read()
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def render_ascii() -> None:
    portrait = ImageOps.fit(load_avatar().convert("L"), (106, 65))
    ramp = " .,:;irsXA253hMHGS#9B&@"
    body = terminal("./portrait.sh")
    body += label(28, 60, "$ cat ~/portrait.txt", 18, GREEN)
    for y in range(65):
        chars = "".join(
            ramp[round((255 - portrait.getpixel((x, y))) / 255 * (len(ramp) - 1))]
            for x in range(106)
        )
        # Text remains visible even where SVG animation is unsupported.
        body += (
            f'<g>'
            f'{label(30, 90 + y * 10.7, chars, 10, TEXT, extra=' + '"xml:space=\\"preserve\\" textLength=\\"775\\" lengthAdjust=\\"spacing\\""' + ')}'
            f'<animate attributeName="opacity" values=".12;1" '
            f'begin="{y * .024:.3f}s" dur=".45s" fill="freeze"/>'
            '</g>'
        )
    body += f'<path d="M0 825H840" stroke="{BORDER}"/>'
    body += label(26, 855, f"$ whoami  {PROFILE_NAME}  |  @{USERNAME}", 16, GREEN)
    (ROOT / "avatar-ascii.svg").write_text(
        svg(840, 880, body, "Animated ASCII art of the GitHub profile image"),
        encoding="utf-8",
    )


def streaks(days: list[dict]) -> tuple[int, int]:
    today = date.today()
    counts = {
        date.fromisoformat(day["date"]): day["contributionCount"]
        for day in days if date.fromisoformat(day["date"]) <= today
    }
    longest = run = 0
    for day in sorted(counts):
        run = run + 1 if counts[day] else 0
        longest = max(longest, run)

    cursor = today
    if not counts.get(cursor, 0):
        cursor -= timedelta(days=1)
    current = 0
    while counts.get(cursor, 0):
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def render_stats(calendar: dict) -> None:
    today = date.today()
    days = [
        day for day in all_days(calendar)
        if date.fromisoformat(day["date"]) <= today
    ]
    active = [day for day in days if day["contributionCount"] > 0]
    total = sum(day["contributionCount"] for day in days)
    current, longest = streaks(days)
    best = max(days, key=lambda item: item["contributionCount"], default=None)
    avg = round(total / len(active), 1) if active else 0

    cards = [
        ("current streak", current, "days"),
        ("longest streak", longest, "days"),
        ("contributions", total, "past year"),
        ("active days", len(active), f"of {len(days)} days"),
        ("best day", best["contributionCount"] if best else 0,
         best["date"] if best else "none"),
        ("avg / active day", avg, "contributions"),
    ]

    body = terminal("./stats.sh")
    for i, (heading, number, detail) in enumerate(cards):
        x = 20 + (i % 2) * 408
        y = 50 + (i // 2) * 164
        body += (
            f'<rect x="{x}" y="{y}" width="392" height="148" '
            f'rx="9" fill="{SURFACE}" stroke="{BORDER}"/>'
            + label(x + 22, y + 35, "$ " + heading, 20, MUTED)
            + label(x + 22, y + 100, number, 50, GREEN if i == 0 else TEXT)
            + label(x + 22, y + 131, detail, 17, MUTED)
        )

    body += (
        f'<rect x="20" y="548" width="800" height="310" rx="9" '
        f'fill="{SURFACE}" stroke="{BORDER}"/>'
    )
    body += label(43, 586, "$ contributions / month", 20, MUTED)
    totals = defaultdict(int)
    for day in days:
        totals[day["date"][:7]] += day["contributionCount"]
    months = sorted(totals)[-12:]
    maximum = max((totals[month] for month in months), default=0) or 1
    slot = 754 / max(len(months), 1)
    for index, month in enumerate(months):
        contributions = totals[month]
        h = max(2, 190 * contributions / maximum)
        x = 43 + index * slot + slot * .2
        y = 817 - h
        body += (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{slot * .6:.1f}" '
            f'height="{h:.1f}" rx="3" fill="{GREEN}"/>'
        )
        month_text = date.fromisoformat(month + "-01").strftime("%b")
        body += label(x + slot * .3, 842, month_text, 12, MUTED, "middle")

    (ROOT / "stats.svg").write_text(
        svg(840, 880, body, "GitHub contributions and streak statistics"),
        encoding="utf-8",
    )


if __name__ == "__main__":
    calendar_data = calendar_from_github()
    render_heatmap(calendar_data)
    render_ascii()
    render_stats(calendar_data)
    print("Updated contrib-heatmap.svg, avatar-ascii.svg and stats.svg")
