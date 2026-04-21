# When should we publish?

Standalone tool that generates a teammate-ready HTML report answering: **what day of the week should we publish for maximum views?** Leads with a clear recommendation, backs it with three focused charts, and tucks methodology and per-video details behind collapsible sections.

Separate from the main dashboard app — does not touch it.

---

## Quick start

From the repo root:

```bash
source .venv/bin/activate
python weekday-weekend/analyze.py
open weekday-weekend/report.html
```

Out of the box, the script reads the most recent `Lifetime snapshot*.xlsx` in the repo root (same file the main dashboard uses). You'll get the publish-day analysis immediately.

To unlock the viewing-day and launch-curve analyses, you'll need a second file — the **daily views export** from YouTube Studio (see [Adding viewing data](#adding-viewing-data) below).

---

## What teammates see

The report is structured for at-a-glance consumption:

1. **Recommendation hero** — the best publish day + one-sentence justification + three headline stats. All computed dynamically from your data.
2. **Three focused charts** with auto-generated captions:
   - *When the audience watches* — daily views by day of week.
   - *How videos perform by publish day* — avg lifetime views per video. Best day highlighted. Filter pills for All / Long-form / Shorts.
   - *Why the best day works* — 8-day launch curve. Best day in bold indigo, other days muted for context.
3. **Collapsible details** — caveats/methodology and the full sortable video table, out of the way but one click away.

Re-running `analyze.py` refreshes everything: the recommendation, captions, and highlighted day all update to match the latest data.

---

## Data sources

### Option A (recommended): Live YouTube Data API v3

Uses an **API key only** — no OAuth, no Brand Account limitations. Always gives fresh lifetime view/like/comment totals.

1. [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) → enable **YouTube Data API v3** → **Create credentials → API key**.
2. Find your channel ID (starts with `UC`) in [YouTube Studio → Settings → Channel → Advanced settings](https://studio.youtube.com).
3. Add to the repo root `.env`:
   ```env
   YOUTUBE_API_KEY=AIzaSy...
   YOUTUBE_CHANNEL_ID=UCxxxxxxxxxxxxxxxxxxxxxx
   ```
4. Re-run. The header will show **Source: YouTube Data API v3 (live)**.

### Option B: XLSX fallback (no setup)

Drop a `Lifetime snapshot*.xlsx` export into the repo root (see the main dashboard README for how to produce it). The script picks it up automatically. Good for offline / no-API-key use.

---

## Adding viewing data

The Data API doesn't expose daily view counts, so the "when viewers watch" and "launch-week" charts require a second XLSX — channel-wide daily views from YouTube Studio.

### Export from YouTube Studio

1. Open [YouTube Studio → Analytics](https://studio.youtube.com).
2. Click **Advanced mode** (top right — this is the key step; the basic Overview page doesn't expose a usable export).
3. Set the dimension to **Date** (so each row = one day) and the date range to **Last 365 days** or **Lifetime**.
4. Click the **download icon** (top right of the data table) → **Google Sheets** or **.csv**.
5. If you got a CSV or Google Sheet, save as `.xlsx`.

The file must contain a `Date` column and a `Views` column. Other columns are ignored.

### Point the script at it

```env
DAILY_XLSX=weekday-weekend/daily-views.xlsx
```

Re-run `analyze.py`. The "when viewers watch" section appears, and the launch-week curve becomes available.

---

## Interpreting the output (for teammates)

A couple of things to keep in mind before quoting numbers in a meeting:

- **"Weekend watching" is audience-specific.** Many channels see a weekend viewing peak. This one currently shows the opposite (Tue–Fri peak, Sat–Sun dip), which reads as a professional/workweek audience. Your recommendation will be different from a consumer-entertainment channel's. Don't assume — check the *When the audience watches* chart first.
- **Small samples are flagged.** Days with fewer than 3 videos are faded in the charts — treat them as directional, not conclusive.
- **Lifetime views confound video age.** Older videos have had more time to accumulate views. If one publish day skews toward your oldest (or newest) content, its average can be misleading.
- **Publish-day rankings can reflect selection, not day effect.** If the team reserves top content for a specific day, that day's high average may be content-quality-driven rather than day-driven. The caveats section in the report spells this out.

The launch-curve chart and the filter pills are the quickest ways to pressure-test a claim.

---

## File layout

```
weekday-weekend/
├── analyze.py        # fetches data + writes report.html
├── template.html     # HTML shell with Chart.js (do not rename)
├── README.md         # this file
└── report.html       # generated output (gitignored)
```

---

## Troubleshooting

- **`No data source available`** — set `YOUTUBE_API_KEY` + `YOUTUBE_CHANNEL_ID` in `.env`, or drop a `Lifetime snapshot*.xlsx` in the repo root.
- **`API channels failed: 403`** — API key isn't enabled for YouTube Data API v3, or has referrer/IP restrictions blocking your machine.
- **`API channels failed: 400`** — channel ID is wrong. Must start with `UC` and belong to the target channel.
- **Launch-curve / viewing sections missing** — `DAILY_XLSX` isn't set, the file isn't found, or it's missing a `Date` / `Views` column. Check the script's log output; if headers differ from defaults it'll log them.
- **`.env` changes aren't picked up** — make sure the file is saved (not just edited in your IDE) before re-running.
- **Shorts detection is slow** — normal; it probes `youtube.com/shorts/{id}` for each video concurrently. ~5–10 s for a few hundred videos.
