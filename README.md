# YT Analytics

A password-protected internal dashboard for viewing YouTube Studio analytics. Reads a "Lifetime snapshot" `.xlsx` export and presents top-performing videos across three lenses: **Subscribers**, **Likability**, and **Engagement**.

## Features

- **Password gate** — simple shared-password login to keep the dashboard internal
- **Three metric tabs**
  - **Subscribers** — ranked by subscribers gained (with a sub-tab for subs-to-views conversion ratio)
  - **Likability** — ranked by like-to-dislike ratio, then by total likes as a tiebreaker
  - **Engagement** — ranked by average percentage viewed
- **Time filters** — Lifetime, 365 days, 90 days, 28 days, 7 days (filters by video publish date)
- **Format filter** — All / Shorts / Long-form
- **Color-coded metrics** — green for above the lifetime per-video average, amber for below
- **Clickable column headers** — sort any column locally in ascending or descending order
- **Video thumbnails** — pulled from YouTube for easy visual scanning
- **Auto-detects the latest snapshot** — drop a new `.xlsx` in the project root and refresh

## Prerequisites

- Python 3.10+

## Setup

1. **Clone the repo**

   ```bash
   git clone <repo-url>
   cd YTanalytics
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Copy the example file and set your values:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```
   SITE_PASSWORD=your-chosen-password
   SECRET_KEY=any-random-string
   ```

4. **Add your data**

   Export a "Lifetime" snapshot from [YouTube Studio Analytics](https://studio.youtube.com/) (Content tab → Advanced mode → Export → Excel) and place the `.xlsx` file in the project root. The file must be named like:

   ```
   Lifetime snapshot <date>.xlsx
   ```

   The app automatically picks the most recently modified file matching that pattern.

## Run

```bash
source .venv/bin/activate
python app.py
```

Open [http://localhost:5000](http://localhost:5000) and enter your password.

## Updating data

To refresh the dashboard with newer analytics:

1. Export a new Lifetime snapshot from YouTube Studio
2. Drop the `.xlsx` file into the project root (you can keep old ones or remove them)
3. Reload the page — the app always reads the most recently modified snapshot

## Expected spreadsheet format

The app reads the **Table data** sheet from the `.xlsx` file. It expects these columns in order:

| Column | Field |
|--------|-------|
| A | Content (video ID) |
| B | Video title |
| C | Video publish time |
| D | Duration (seconds) |
| E | Likes |
| F | Comments added |
| G | Average percentage viewed (%) |
| H | Likes (vs. dislikes) (%) |
| I | Views |
| J | Subscribers |
| K | Impressions |
| L | Impressions click-through rate (%) |

Row 2 should contain the totals. Video data starts at row 3.

## Project structure

```
YTanalytics/
├── .env.example        # Template for environment variables
├── .gitignore
├── README.md
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
└── templates/
    ├── login.html      # Password gate
    └── dashboard.html  # Main analytics view
```

## License

Internal use.
