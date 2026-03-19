# validate.py
"""
AI-powered validation of extracted manhwa title candidates.

Classifies each candidate's sentiment using comment context — distinguishing
genuine recommendations from criticisms, references, and false positives.

Requires ANTHROPIC_API_KEY in .env. If the key is absent or the call fails,
the function returns an empty dict and the rest of the pipeline is unaffected.
"""
import json
import os

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None


def ai_validate(candidates: dict[str, list[str]], max_candidates: int = 150) -> dict[str, str]:
    """
    Classify manhwa title candidates using Claude.

    Args:
        candidates: {title: [comment snippet, ...]} — titles mapped to the
                    comment bodies where they appeared (used as context)
        max_candidates: max titles to send in one batch (keeps cost low)

    Returns:
        {title: label} where label is one of:
            "positive" — users are recommending or praising it
            "negative" — users are criticizing or warning against it
            "mixed"    — both praise and criticism present
            "noise"    — not a manhwa title (generic phrase, false positive)
        Returns empty dict if API key is missing or the call fails.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {}

    if _anthropic is None:
        print("[AI] anthropic package not installed. Run: pip install anthropic")
        return {}

    # Limit batch size and truncate snippets to control prompt size
    items = list(candidates.items())[:max_candidates]

    batch_lines = []
    for i, (title, snippets) in enumerate(items, 1):
        short = [s[:200].replace("\n", " ") for s in snippets[:3]]
        snippet_text = " | ".join(short) if short else "(no context available)"
        batch_lines.append(f'{i}. Title: {title}\n   Comments: {snippet_text}')

    prompt = f"""You are reviewing candidate titles extracted from Reddit comments in manhwa and webtoon recommendation threads.

For each numbered entry, I show a candidate title and the comment snippets where it appeared.
Classify each with ONE label:
- "positive"  — users are recommending, praising, or saying it is worth reading
- "negative"  — users are criticizing, warning against, or saying they dropped/disliked it
- "mixed"     — both positive and negative sentiment present in the snippets
- "noise"     — this is NOT a manhwa/webtoon title (generic phrase, question, reaction, common word, etc.)

Respond ONLY with a valid JSON array using the entry number as the id, in the same order:
[{{"id": 1, "label": "positive|negative|mixed|noise"}}, {{"id": 2, "label": "..."}}, ...]

Titles and comment context:

{chr(10).join(batch_lines)}"""

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()  # type: ignore[union-attr]

        # Strip markdown code fences if present
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]

        results = json.loads(raw.strip())
        # Map numeric id back to the original title by position
        return {
            items[r["id"] - 1][0]: r["label"]
            for r in results
            if "id" in r and "label" in r and 1 <= r["id"] <= len(items)
        }

    except Exception as e:
        print(f"[AI] Validation failed: {e}. Continuing without AI labels.")
        return {}
