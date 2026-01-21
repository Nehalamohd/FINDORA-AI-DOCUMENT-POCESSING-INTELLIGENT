from duckduckgo_search import DDGS
from app.logger import logger

#take search query from user 
#ssearch intrnt using ddg

def web_search(query: str, max_results: int = 10) -> list[str]:
    """
    Performs a web search using DuckDuckGo and returns a list of result snippets.
    Falls back to Wikipedia if DuckDuckGo fails (common on AWS).
    """
    results = []
    logger.debug(f"Performing web search for: {query}")
    
    # 1. Try DuckDuckGo
    try:
        with DDGS() as ddgs:
            ddgs_results = ddgs.text(query, max_results=max_results)
            for r in ddgs_results:
                snippet = f"Title: {r['title']}\nSnippet: {r['body']}\nSource: {r['href']}"
                results.append(snippet)
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed/blocked: {e}")

    # 2. Wikipedia Fallback (Very reliable on AWS)
    if not results:
        logger.info(f"No results from DDG. Trying Wikipedia fallback for: {query}")
        try:
            import httpx
            # Use Wikipedia Search API
            wiki_url = "https://en.wikipedia.org/w/api.php"
            wiki_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 3
            }
            resp = httpx.get(wiki_url, params=wiki_params, timeout=5.0)
            if resp.status_code == 200:
                search_data = resp.json().get("query", {}).get("search", [])
                for r in search_data:
                    title = r['title']
                    snippet = r['snippet'].replace('<span class="searchmatch">', '').replace('</span>', '')
                    url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    results.append(f"Title: {title} (Wikipedia)\nSnippet: {snippet}\nSource: {url}")
        except Exception as wiki_e:
            logger.error(f"Wikipedia fallback failed: {wiki_e}")

    if not results:
        logger.info("Both DDG and Wikipedia returned 0 results.")
    else:
        logger.info(f"Total snippets found: {len(results)}")
        
    return results
