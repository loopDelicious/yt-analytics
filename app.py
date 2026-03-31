import io
import os
import glob
import re
from datetime import datetime, timedelta
from functools import wraps

import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from openpyxl import load_workbook
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(32).hex())

SITE_PASSWORD = os.getenv("SITE_PASSWORD", "changeme")
DATA_URL = os.getenv("DATA_URL", "")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def find_latest_snapshot():
    """Find the most recent 'Lifetime snapshot' xlsx in the working directory."""
    pattern = os.path.join(os.path.dirname(__file__) or ".", "Lifetime snapshot*.xlsx")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def download_remote_snapshot():
    """Download xlsx from DATA_URL. Returns (BytesIO, filename) or (None, None)."""
    if not DATA_URL:
        return None, None
    try:
        resp = requests.get(DATA_URL, timeout=30)
        resp.raise_for_status()
        disposition = resp.headers.get("Content-Disposition", "")
        match = re.search(r'filename="?([^";\n]+)', disposition)
        filename = match.group(1).strip() if match else "Remote snapshot.xlsx"
        return io.BytesIO(resp.content), filename
    except Exception:
        return None, None


def parse_publish_date(date_str):
    """Parse 'Mon DD, YYYY' format into a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%b %d, %Y")
    except ValueError:
        return None


def load_video_data():
    """Load video data from a local xlsx or a remote DATA_URL."""
    filepath = find_latest_snapshot()

    if filepath:
        filename = os.path.basename(filepath)
        wb = load_workbook(filepath)
    else:
        remote_data, filename = download_remote_snapshot()
        if remote_data is None:
            return [], "", None
        wb = load_workbook(remote_data)

    match = re.search(r"Lifetime snapshot (.+)\.xlsx", filename or "")
    snapshot_date_str = match.group(1) if match else (filename or "Unknown")
    ws = wb["Table data"]

    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]

    SHORTS_MAX_DURATION = 60

    videos = []
    for row in ws.iter_rows(min_row=3, values_only=True):
        video_id = row[0]
        if not video_id or video_id == "Total":
            continue
        duration = row[3] or 0
        views = row[8] or 0
        subscribers = row[9] or 0
        videos.append({
            "id": video_id,
            "title": row[1] or "",
            "publish_time": row[2] or "",
            "publish_date": parse_publish_date(row[2]),
            "duration_sec": duration,
            "is_short": duration <= SHORTS_MAX_DURATION,
            "likes": row[4] or 0,
            "comments": row[5] or 0,
            "avg_pct_viewed": row[6] or 0,
            "like_ratio": row[7] or 0,
            "views": views,
            "subscribers": subscribers,
            "subs_views_ratio": round(subscribers / views * 100, 2) if views else 0,
            "impressions": row[10] or 0,
            "ctr": row[11] or 0,
        })

    totals_row = list(ws.iter_rows(min_row=2, max_row=2, values_only=True))[0]
    totals = {
        "likes": totals_row[4] or 0,
        "comments": totals_row[5] or 0,
        "avg_pct_viewed": totals_row[6] or 0,
        "like_ratio": totals_row[7] or 0,
        "views": totals_row[8] or 0,
        "subscribers": totals_row[9] or 0,
        "impressions": totals_row[10] or 0,
        "ctr": totals_row[11] or 0,
    }

    wb.close()
    return videos, snapshot_date_str, totals


def compute_averages(videos):
    """Compute per-video averages across all lifetime videos for color-coding."""
    if not videos:
        return {}
    n = len(videos)
    keys = ["likes", "comments", "avg_pct_viewed", "like_ratio",
            "views", "subscribers", "impressions", "ctr", "subs_views_ratio"]
    return {k: round(sum(v[k] for v in videos) / n, 2) for k in keys}


def filter_by_timespan(videos, days):
    """Filter videos published within the last N days."""
    if days is None:
        return videos
    cutoff = datetime.now() - timedelta(days=days)
    return [v for v in videos if v["publish_date"] and v["publish_date"] >= cutoff]


def filter_by_format(videos, fmt):
    """Filter by video format: 'all', 'shorts', or 'long'."""
    if fmt == "shorts":
        return [v for v in videos if v["is_short"]]
    if fmt == "long":
        return [v for v in videos if not v["is_short"]]
    return videos


def sort_videos(videos, tab, sort):
    """Sort videos descending by the primary metric for the given tab/sort."""
    if tab == "subscribers" and sort == "ratio":
        return sorted(videos, key=lambda v: v["subs_views_ratio"], reverse=True)
    if tab == "likability":
        return sorted(videos, key=lambda v: (v["like_ratio"], v["likes"]), reverse=True)
    sort_keys = {
        "subscribers": "subscribers",
        "engagement": "avg_pct_viewed",
    }
    key = sort_keys.get(tab, "subscribers")
    return sorted(videos, key=lambda v: v[key], reverse=True)


def format_number(n):
    """Format large numbers with commas."""
    if isinstance(n, float) and n == int(n):
        n = int(n)
    if isinstance(n, int):
        return f"{n:,}"
    return str(n)


def format_duration(seconds):
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if not seconds:
        return "0:00"
    seconds = int(seconds)
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}"
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


app.jinja_env.filters["fmt_num"] = format_number
app.jinja_env.filters["fmt_dur"] = format_duration


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == SITE_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        flash("Incorrect password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    tab = request.args.get("tab", "subscribers")
    timespan = request.args.get("timespan", "lifetime")
    sort = request.args.get("sort", "default")
    fmt = request.args.get("fmt", "all")

    if tab not in ("subscribers", "likability", "engagement"):
        tab = "subscribers"
    if sort not in ("default", "ratio"):
        sort = "default"
    if fmt not in ("all", "shorts", "long"):
        fmt = "all"

    days_map = {
        "lifetime": None,
        "7": 7,
        "28": 28,
        "90": 90,
        "365": 365,
    }
    days = days_map.get(timespan)

    videos, snapshot_date, totals = load_video_data()
    averages = compute_averages(videos)
    filtered = filter_by_timespan(videos, days)
    filtered = filter_by_format(filtered, fmt)
    sorted_videos = sort_videos(filtered, tab, sort)

    if filtered:
        filtered_totals = {
            "likes": sum(v["likes"] for v in filtered),
            "comments": sum(v["comments"] for v in filtered),
            "avg_pct_viewed": round(sum(v["avg_pct_viewed"] for v in filtered) / len(filtered), 2),
            "like_ratio": round(sum(v["like_ratio"] for v in filtered) / len(filtered), 2),
            "views": sum(v["views"] for v in filtered),
            "subscribers": sum(v["subscribers"] for v in filtered),
            "impressions": sum(v["impressions"] for v in filtered),
            "ctr": round(sum(v["ctr"] for v in filtered) / len(filtered), 2),
        }
    else:
        filtered_totals = totals

    display_totals = filtered_totals if days is not None else totals

    return render_template(
        "dashboard.html",
        videos=sorted_videos,
        tab=tab,
        sort=sort,
        fmt=fmt,
        timespan=timespan,
        snapshot_date=snapshot_date,
        totals=display_totals,
        averages=averages,
        video_count=len(sorted_videos),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
