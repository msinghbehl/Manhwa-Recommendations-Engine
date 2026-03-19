# 📊 Manhwa Trending on Reddit

> A pipeline that scrapes Reddit, extracts manhwa title mentions from community discussions, ranks them with a weighted scoring formula, and uses AI to validate whether each title is being genuinely recommended — or just criticized.

Built as a personal learning project at the intersection of **data engineering**, **API integration**, and **AI-powered enrichment**. It also solves a real problem: finding the next great manhwa to read without manually sifting through thousands of Reddit comments.

---

## What It Does

Every run of this pipeline:

1. **Collects** posts and comments from r/manhwa, r/manhwarecommendations, and r/webtoons matching recommendation-intent queries
2. **Extracts** manhwa title mentions using regex pattern matching (bold, italic, quoted, and list-formatted titles)
3. **Scores** each title using a weighted formula that accounts for recency, post quality, unique commenters, and cross-community presence
4. **Validates** each title using Claude AI to distinguish genuine recommendations from criticism, noise, and false positives
5. **Displays** the results in an interactive Streamlit dashboard with sentiment badges and filters

---

## Features

- **Multi-subreddit coverage** — searches 3 communities × 5 query types = 15 search combinations per run
- **Weighted scoring** — recency decay + post upvote quality weighting, not just raw mention counts
- **Fuzzy title deduplication** — "God of Highschool" and "The God of Highschool" are merged automatically
- **AI sentiment classification** — Claude Haiku labels each title as ✅ positive, ⚠️ mixed, ❌ negative, or 🔇 noise based on actual comment context
- **Parallel comment fetching** — 5x faster than sequential fetching via ThreadPoolExecutor
- **Interactive dashboard** — filter by sentiment, search by title, sort by any column, get a weighted-random pick
- **Historical trend charts** — 30-day sparkline per title across multiple runs
- **Fully optional AI step** — pipeline works without an Anthropic API key; AI labels are a bonus layer

---

## Architecture

```
Reddit API (PRAW)
      │
      ▼
┌─────────────┐
│  collect.py  │  ← searches 3 subs × 5 queries, fetches comments in parallel
└─────────────┘
      │ posts.jsonl + comments.jsonl
      ▼
┌─────────────┐
│  extract.py  │  ← regex extraction → noise filter → weighted scoring → fuzzy dedup
└─────────────┘
      │
      ▼
┌──────────────┐
│  validate.py  │  ← one Claude Haiku API call, batches 150 candidates with context
└──────────────┘
      │ clean_counts.csv (with ai_sentiment column)
      ▼
┌─────────┐
│  app.py  │  ← Streamlit dashboard with sentiment filter + trend charts
└─────────┘
```

### Scoring Formula

```
score = weighted_mentions + 0.5 × unique_commenters + 1.2 × subreddit_count

where:
  weighted_mentions = Σ (0.9^days_old × log(1 + post_upvotes))
```

- `subreddit_count` weighted highest (1.2×) — cross-community appeal is the strongest signal
- Recency decay means trending titles surface over older ones with higher raw counts
- `log(1 + upvotes)` boosts quality discussions without letting one viral post dominate

---

## Tech Stack

| Layer | Technology |
|---|---|
| Reddit API | [PRAW](https://praw.readthedocs.io/) (Python Reddit API Wrapper) |
| Data storage | JSONL (raw) + CSV (processed) |
| Text processing | `re`, `rapidfuzz` |
| Data analysis | `pandas` |
| AI validation | [Anthropic Claude Haiku](https://www.anthropic.com/) |
| Dashboard | [Streamlit](https://streamlit.io/) |
| Parallelism | `concurrent.futures.ThreadPoolExecutor` |

---

## Setup

### Prerequisites

- Python 3.9+
- A Reddit account with a [script-type app](https://www.reddit.com/prefs/apps) (free)
- An Anthropic API key (optional — only needed for AI sentiment labels)

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/manhwa-recommendations-reddit.git
cd manhwa-recommendations-reddit

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
USER_AGENT=ManhwaRecBot/1.0 by u/your_reddit_username
LOOKBACK_DAYS=7

# Optional — enables AI sentiment validation
ANTHROPIC_API_KEY=your_anthropic_key
```

To get Reddit credentials: go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps), click "create another app", choose **script**, and copy the client ID and secret.

---

## Usage

Run the three steps in order:

```bash
# Step 1 — Scrape Reddit (7-day window, up to 60 posts, 40 comments each)
python3 collect.py -d 7 --post-limit 60 --comment-limit 40

# Step 2 — Extract titles, score, and run AI validation
python3 extract.py

# Step 3 — Launch the dashboard
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

> **Tip:** Run Steps 1 and 2 on a schedule (e.g., weekly) to build up historical trend data. The dashboard's 30-day sparkline becomes useful after a few runs.

---

## Project Structure

```
manhwa-recommendations-reddit/
├── .env.example            # Template — copy to .env and fill in your credentials
├── requirements.txt        # pip dependencies
│
├── config.py               # Subreddits, query terms, shared paths
├── reddit_client.py        # PRAW auth + search_posts() + fetch_comments()
├── collect.py              # Step 1: scrape Reddit → data/raw/YYYY-MM-DD/
├── extract.py              # Step 2: extract, score, rank → data/processed/YYYY-MM-DD/
├── validate.py             # Step 2.5: AI sentiment classification via Claude
├── app.py                  # Step 3: Streamlit dashboard
└── data/
    ├── blacklist.txt       # Phrases to always reject (generic words, stop phrases)
    └── whitelist.txt       # Titles to always include (handles edge cases)
```

---

## Dashboard Preview

The dashboard shows a ranked table of trending manhwa with:

- **Signal column** — AI sentiment badge per title
- **Sidebar filters** — min mentions, title search, sort order, sentiment filter
- **Signal legend** — ✅ positive · ⚠️ mixed · ❌ negative · 🔇 noise · ❓ unknown
- **Surprise me button** — score-weighted random recommendation
- **Trend chart** — 30-day mention history for any selected title

---

## Design Decisions Worth Noting

**Why not just count mentions?**
Raw counts are easy to game and don't distinguish quality. A title mentioned once in a 500-upvote thread by an active community member is a stronger signal than the same title mentioned 10 times by the same person in a low-engagement post.

**Why AI for validation, but not for scraping or ranking?**
AI was added only where rules genuinely fail. Scraping is a solved problem (PRAW handles it). Deduplication is a solved problem (fuzzy string matching handles it). Ranking is an interpretable formula that's tunable. The one thing rules *cannot* do is read tone — distinguishing "you should read Solo Leveling" from "Solo Leveling is overrated" requires understanding language context. That's the one job Claude does here.

**Why JSONL for raw data?**
Append-friendly and crash-safe. If the collector dies mid-run, everything written so far is valid. CSV would produce a partially-written, unparseable file.

---

## Background

I'm a Technical Program Manager who decided to build something real to develop hands-on skills in Python, APIs, and AI integration. This project let me apply concepts I'd managed in engineering teams — data pipelines, API rate limiting, parallel processing, LLM integration — by building them myself from scratch.

It also happens to solve a problem I actually have: there are thousands of Reddit threads about manhwa recommendations and no good way to surface the signal from the noise. This pipeline does that automatically.

---

## License

MIT — feel free to fork, adapt, and build on it.
