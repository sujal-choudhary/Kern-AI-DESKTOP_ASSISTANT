# Menu Assistant - Search Patterns Guide

This document lists all supported search patterns for the Menu desktop assistant.

## Supported Search Platforms

### YouTube Search
Search for videos on YouTube.
- **Commands:**
  - "search [query] on youtube"
  - "find [query] on youtube"
  - "youtube search [query]"

**Example:** `search python tutorial on youtube`

---

### Google Search
General web search using Google.
- **Commands:**
  - "google [query]"
  - "search [query]" (default if no specific platform)

**Example:** `google python programming`

---

### Google News
Search for news articles.
- **Commands:**
  - "news [query]"
  - "google news [query]"
  - "search news for [query]"

**Example:** `news artificial intelligence`

---

### Google Maps
Search for locations and places on Google Maps.
- **Commands:**
  - "maps [query]"
  - "map [query]"
  - "find on maps [query]"
  - "search maps for [query]"

**Example:** `maps nearest coffee shop`
**Example:** `find on maps Pizza restaurant`

---

### Wikipedia Search
Look up information on Wikipedia.
- **Commands:**
  - "wiki [query]"
  - "wikipedia [query]"
  - "search wikipedia for [query]"

**Example:** `wiki machine learning`

---

### Amazon Search (India)
Search for products on Amazon India.
- **Commands:**
  - "amazon [query]"
  - "search amazon for [query]"

**Example:** `amazon laptop`

---

### Hotstar Search
Search for movies and shows on Hotstar.
- **Commands:**
  - "hotstar [query]"
  - "search hotstar for [query]"

**Example:** `hotstar avengers`

---

### Spotify Search
Search for music on Spotify.
- **Commands:**
  - "spotify [query]"
  - "search spotify for [query]"
  - "play [song name]"
  - "search music [query]"

**Example:** `spotify bohemian rhapsody`
**Example:** `play hotel california`

---

### Gaana Search
Search for music on Gaana (Indian music platform).
- **Commands:**
  - "gaana [query]"
  - "search gaana for [query]"

**Example:** `gaana bollywood music`
**Example:** `gaana latest songs`

---

### LinkedIn Search
Search for profiles, jobs, and content on LinkedIn.
- **Commands:**
  - "linkedin [query]"
  - "search linkedin for [query]"

**Example:** `linkedin software engineer`

---

### GitHub Search
Search for repositories and code on GitHub.
- **Commands:**
  - "github [query]"
  - "search github for [query]"

**Example:** `github python framework`

---

### PyPI Search
Search for Python packages on PyPI.
- **Commands:**
  - "pypi [query]"
  - "python package [query]"
  - "search pypi for [query]"

**Example:** `pypi requests library`
**Example:** `python package flask`

---

### Twitter Search
Search for tweets and trends on Twitter/X.
- **Commands:**
  - "twitter [query]"
  - "search twitter for [query]"

**Example:** `twitter artificial intelligence`

---

## Implementation Details

All search functions are implemented with URL encoding to handle special characters and spaces properly:
- Spaces are replaced with appropriate encodings (`+`, `%20`, or `_` depending on the platform)
- Special characters are safely handled
- URLs are opened in the default web browser

## Usage Examples

```
"google what is machine learning"
"wikipedia artificial intelligence"
"amazon smartphone 2024"
"youtube python for beginners"
"hotstar latest series"
"spotify beautiful day"
"gaana hindi songs"
"linkedin data scientist jobs"
"github flask web framework"
"twitter python programming"
"pypi numpy library"
"news latest technology updates"
"maps pizza restaurants near me"
```

## Adding New Search Platforms

To add a new search platform:

1. **Add search function in `core/actions.py`:**
   ```python
   def platform_search(query: str) -> TaskResult:
       """Search [Platform] for content."""
       try:
           encoded_query = query.strip().replace(" ", "[encoding]")
           url = f"https://[platform-url]/search?q={encoded_query}"
           webbrowser.open(url)
           return _ok(f"Searched [Platform] for: {query}")
       except Exception as exc:
           logging.error("[platform]_search failed: %s", exc)
           return _err("Failed to search [Platform]", str(exc))
   ```

2. **Add task dispatcher in `core/actions.py`'s `execute_task()` function:**
   ```python
   if task == "[platform]_search":
       return platform_search(params["query"])
   ```

3. **Add command parser in `core/commands.py`'s `_parse_single()` function:**
   ```python
   platform_match = re.search(r"(?:[platform]|search\s+[platform])\s+(?:for\s+)?(.+?)$", lowered)
   if platform_match:
       query = platform_match.group(1).strip().strip("'\"")
       return _single("[platform]_search", {"query": query})
   ```

## Search URL Reference

Quick reference for all search URLs:

| Platform | URL Pattern |
|----------|------------|
| YouTube | `https://www.youtube.com/results?search_query={query}` |
| Google | `https://www.google.com/search?q={query}` |
| Google News | `https://news.google.com/search?q={query}` |
| Google Maps | `https://www.google.com/maps/search/{query}` |
| Wikipedia | `https://en.wikipedia.org/wiki/{query}` |
| Amazon (India) | `https://www.amazon.in/s?k={query}` |
| Hotstar | `https://www.hotstar.com/in/explore?search_query={query}` |
| Spotify | `https://open.spotify.com/search/{query}` |
| Gaana | `https://gaana.com/search/{query}` |
| LinkedIn | `https://www.linkedin.com/search/results/all/?keywords={query}` |
| GitHub | `https://github.com/search?q={query}` |
| PyPI | `https://pypi.org/search/?q={query}` |
| Twitter | `https://twitter.com/search?q={query}` |

