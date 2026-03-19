"""
Streamlit dashboard: Trending Manhwa & Webtoons
------------------------------------------------
• Reads the *latest* processed clean_counts.csv created by extract.py
• Sidebar filters: minimum mentions, search phrase, sort by column
• Weighted “Surprise me” button (score‑weighted random pick)
• Optional trend sparkline: when user selects a title it aggregates
  mentions across all processed folders and shows a 30‑day line chart.

To run locally (in the project root):
    streamlit run app.py
"""
from __future__ import annotations
import os
import random
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

DATA_ROOT = Path("data/processed")
DEFAULT_MIN_MENTIONS = 3

st.set_page_config(page_title="Trending Manhwa on Reddit", layout="wide")

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def latest_clean_csv() -> Path | None:
    """Return path to the most recent clean_counts.csv (or None)."""
    files = sorted(DATA_ROOT.glob("*/clean_counts.csv"), key=os.path.getmtime)
    return files[-1] if files else None


SENTIMENT_EMOJI = {
    "positive": "✅",
    "negative": "❌",
    "mixed":    "⚠️",
    "noise":    "🔇",
    "unknown":  "❓",
}


def load_df(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # ensure expected cols
    for col in ["title", "mentions", "unique_commenters", "subreddit_count", "score"]:
        if col not in df.columns:
            raise ValueError(f"{path} missing column {col}")
    return df


def get_historical_series(title: str, days: int = 30) -> pd.Series:
    """Return mentions per day for the past `days` (filled with 0)."""
    cutoff = datetime.now(timezone.utc).date().toordinal() - days
    series = {}
    for csv in sorted(DATA_ROOT.glob("*/clean_counts.csv")):
        date_str = csv.parent.name  # folder name YYYY-MM-DD
        try:
            day_ord = datetime.strptime(
                date_str, "%Y-%m-%d").date().toordinal()
        except ValueError:
            continue
        if day_ord < cutoff:
            continue
        df = pd.read_csv(csv, usecols=["title", "mentions"])
        row = df[df["title"].str.lower() == title.lower()]
        series[day_ord] = int(row["mentions"].iloc[0]) if not row.empty else 0
    if not series:
        return pd.Series(dtype=int)
    idx = range(min(series), max(series) + 1)
    return pd.Series(series).reindex(idx, fill_value=0).rename("mentions")


# -----------------------------------------------------------------------------
# Load latest data
# -----------------------------------------------------------------------------
latest_csv = latest_clean_csv()
if latest_csv is None:
    st.error("No processed CSVs found. Run `extract.py` first.")
    st.stop()

df = load_df(latest_csv)

# -----------------------------------------------------------------------------
# Sidebar controls
# -----------------------------------------------------------------------------
st.sidebar.header("Filters")
min_mentions = st.sidebar.slider("Min mentions", 1, int(
    df["mentions"].max()), DEFAULT_MIN_MENTIONS)
search_text = st.sidebar.text_input("Search title contains")
col_choice = st.sidebar.radio(
    "Sort by", ["score", "mentions", "unique_commenters"], index=0)
ascending = st.sidebar.checkbox("Ascending sort", value=False)

has_sentiment = "ai_sentiment" in df.columns
sentiment_filter = None
if has_sentiment:
    sentiment_filter = st.sidebar.multiselect(
        "AI sentiment filter",
        options=["positive", "mixed", "negative", "noise", "unknown"],
        default=["positive", "mixed", "unknown"],
        help="Show only titles with these AI-assigned sentiment labels"
    )
    st.sidebar.caption(
        "**Signal legend**\n"
        "✅ positive — recommended\n"
        "⚠️ mixed — praise & criticism\n"
        "❌ negative — criticized\n"
        "🔇 noise — not a real title\n"
        "❓ unknown — unclassified"
    )

filtered = df[df["mentions"] >= min_mentions].copy()
if search_text:
    filtered = filtered[filtered["title"].str.contains(
        search_text, case=False, na=False)]
if has_sentiment and sentiment_filter:
    filtered = filtered[filtered["ai_sentiment"].isin(sentiment_filter)]

filtered = filtered.sort_values(
    col_choice, ascending=ascending).reset_index(drop=True)

# -----------------------------------------------------------------------------
# Main table
# -----------------------------------------------------------------------------
st.title("\U0001F4CA  Trending Manhwa on Reddit (last scrape)")
st.caption(
    f"Dataset: **{latest_csv.parent.name}**  –  {len(df)} titles   |   {len(filtered)} after filters")

display = filtered[["title", "mentions", "unique_commenters", "subreddit_count", "score"]].copy()
display = display.rename(columns={"unique_commenters": "uniq_comments", "subreddit_count": "subs"})
if has_sentiment:
    display.insert(0, "signal", filtered["ai_sentiment"].map(SENTIMENT_EMOJI).fillna("❓"))

st.dataframe(display, use_container_width=True)

# -----------------------------------------------------------------------------
# Surprise‑me button
# -----------------------------------------------------------------------------
if st.button("🎲 Surprise me (weight by score)"):
    pick = random.choices(filtered["title"].tolist(), weights=filtered["score"].tolist())[0]
    st.success(f"**Your next read → {pick}**")

# -----------------------------------------------------------------------------
# Trend sparkline
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("📈  Mentions over time (last 30 days)")
sel_title = st.selectbox("Pick a title to see its trend",
                         options=filtered["title"].tolist())
if sel_title is not None:
    series = get_historical_series(sel_title)
    if not series.empty:
        st.line_chart(series)
    else:
        st.info("No historical data for this title yet. Keep running the scraper daily!")
