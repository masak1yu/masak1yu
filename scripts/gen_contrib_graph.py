#!/usr/bin/env python3
"""GitHub contribution history area chart generator (Dracula theme)"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

TOKEN = os.environ["METRICS_TOKEN"]
USERNAME = os.environ.get("GITHUB_ACTOR", "masak1yu")

QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

def fetch_contributions():
    payload = json.dumps({"query": QUERY, "variables": {"username": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for week in weeks:
        for day in week["contributionDays"]:
            days.append((day["date"], day["contributionCount"]))
    days.sort()
    return days


def render_svg(days, output="metrics.contrib.svg"):
    W, H = 800, 180
    PAD_L, PAD_R, PAD_T, PAD_B = 40, 20, 30, 40

    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B

    counts = [c for _, c in days]
    max_c = max(counts) if counts else 1

    def x(i):
        return PAD_L + i * chart_w / (len(days) - 1)

    def y(c):
        return PAD_T + chart_h - (c / max_c) * chart_h

    # build polyline points for area fill
    pts = " ".join(f"{x(i):.1f},{y(c):.1f}" for i, (_, c) in enumerate(days))
    # close area path
    area_path = (
        f"M {x(0):.1f},{y(0):.1f} "
        + " ".join(f"L {x(i):.1f},{y(c):.1f}" for i, (_, c) in enumerate(days))
        + f" L {x(len(days)-1):.1f},{PAD_T + chart_h:.1f}"
        + f" L {x(0):.1f},{PAD_T + chart_h:.1f} Z"
    )

    # x-axis month labels (show ~6 labels)
    month_labels = []
    prev_month = None
    for i, (date_str, _) in enumerate(days):
        m = date_str[:7]  # YYYY-MM
        if m != prev_month:
            month_labels.append((i, datetime.strptime(date_str, "%Y-%m-%d").strftime("%b")))
            prev_month = m

    step = max(1, len(month_labels) // 6)
    month_labels = month_labels[::step]

    # y-axis labels
    y_labels = [(0, str(max_c)), (chart_h // 2, str(max_c // 2)), (chart_h, "0")]

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        '<defs>',
        '  <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">',
        '    <stop offset="0%" stop-color="#bd93f9" stop-opacity="0.5"/>',
        '    <stop offset="100%" stop-color="#bd93f9" stop-opacity="0.05"/>',
        '  </linearGradient>',
        '</defs>',
        f'<rect width="{W}" height="{H}" fill="#282a36" rx="8"/>',
        # title
        f'<text x="{PAD_L}" y="18" fill="#f8f8f2" font-size="12" font-family="monospace">Contributions (past year) — {USERNAME}</text>',
        # grid lines
        *[
            f'<line x1="{PAD_L}" y1="{PAD_T + gy:.1f}" x2="{W - PAD_R}" y2="{PAD_T + gy:.1f}" stroke="#44475a" stroke-width="0.5"/>'
            for gy, _ in y_labels
        ],
        # area fill
        f'<path d="{area_path}" fill="url(#grad)"/>',
        # line
        f'<polyline points="{pts}" fill="none" stroke="#bd93f9" stroke-width="1.5"/>',
        # x-axis
        f'<line x1="{PAD_L}" y1="{PAD_T + chart_h}" x2="{W - PAD_R}" y2="{PAD_T + chart_h}" stroke="#6272a4" stroke-width="1"/>',
        # month labels
        *[
            f'<text x="{x(i):.1f}" y="{PAD_T + chart_h + 14}" fill="#6272a4" font-size="10" font-family="monospace" text-anchor="middle">{label}</text>'
            for i, label in month_labels
        ],
        # y-axis labels
        *[
            f'<text x="{PAD_L - 4}" y="{PAD_T + gy + 4:.1f}" fill="#6272a4" font-size="10" font-family="monospace" text-anchor="end">{label}</text>'
            for gy, label in y_labels
        ],
        '</svg>',
    ]

    with open(output, "w") as f:
        f.write("\n".join(svg_parts))
    print(f"Written {output}")


if __name__ == "__main__":
    days = fetch_contributions()
    render_svg(days)
