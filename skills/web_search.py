import re
import textwrap
from typing import List, Dict, Any

try:
    from duckduckgo_search import DDGS  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    DDGS = None  # type: ignore


def extract_search_query(command: str) -> str:
    """
    Try to pull a web search query from natural language commands.
    Returns an empty string when no query is detected.
    """
    if not command:
        return ""

    original = command.strip()
    lowered = original.lower()

    # Ignore file-related search commands
    if any(phrase in lowered for phrase in ["search in file", "search file", "search within file"]):
        return ""

    trigger_phrases = (
        "search",
        "lookup",
        "look up",
        "find info",
        "find information",
        "google search",
        "search google",
    )
    if not any(trigger in lowered for trigger in trigger_phrases):
        return ""

    patterns = [
        r"(?:search\s+google|google\s+search)\s+(?:for|about)?\s*(.+)",
        r"search\s+(?:the\s+web\s+)?(?:for|about)?\s*(.+)",
        r"look\s*up\s+(.+)",
        r"find\s+(?:info|information)\s+(?:about|on)?\s*(.+)",
        r"google\s+(?:for|about)\s+(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, original, flags=re.IGNORECASE)
        if match:
            query = match.group(1).strip(" ?!.\"'")
            return query

    # Fallback: if command starts with "search", take everything after it
    if lowered.startswith("search "):
        return original[original.lower().find("search") + len("search"):].strip(" ?!.\"'")

    return ""


def _perform_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    if DDGS is None:
        raise RuntimeError(
            "duckduckgo-search package is required. Install with 'pip install duckduckgo-search'."
        )

    with DDGS() as ddgs:
        results_iter = ddgs.text(
            query,
            region="wt-wt",
            safesearch="moderate",
            max_results=max_results,
        )
        results = list(results_iter) if results_iter else []
    return results


def search_web(query: str) -> str:
    """Return formatted search results for the provided query."""
    query = query.strip()
    if not query:
        return "❌ Please specify what you want me to search for. Example: 'search google for MERN stack'."

    try:
        results = _perform_search(query)
    except RuntimeError as exc:
        return f"❌ Web search unavailable: {exc}"
    except Exception as exc:  # pragma: no cover - network issues
        return f"❌ Web search failed: {exc}"

    if not results:
        return f"❌ No web results found for '{query}'."

    lines: List[str] = [f"🔎 Web results for '{query}':"]
    for idx, item in enumerate(results, start=1):
        title = (item.get("title") or "Untitled result").strip()
        snippet = (item.get("body") or item.get("description") or "").strip()
        url = item.get("href") or item.get("url") or ""

        if snippet:
            snippet = textwrap.shorten(snippet, width=180, placeholder="...")

        lines.append(f"{idx}. {title}")
        if snippet:
            lines.append(f"   {snippet}")
        if url:
            lines.append(f"   {url}")

    lines.append("Tip: Say 'open <site>' if you want me to open one of these results.")
    return "\n".join(lines)


def handle(command: str) -> str:
    """Public entry point for brain.py to use."""
    query = extract_search_query(command)
    if not query:
        return "❌ Please specify what to search for. Example: 'search google for MERN stack'."
    return search_web(query)


