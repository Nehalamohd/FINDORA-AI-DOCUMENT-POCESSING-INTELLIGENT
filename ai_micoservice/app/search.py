from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 10) -> list[str]:
    """
    Performs a web search using DuckDuckGo and returns a list of result snippets.
    """
    results = []
    print(f"[DEBUG] Performing web search for: {query}")
    try:
        with DDGS() as ddgs:
            # Using region='wt-wt' for global and timelimit='d' for recent results if needed
            ddgs_results = ddgs.text(query, max_results=max_results)
            for r in ddgs_results:
                snippet = f"Title: {r['title']}\nSnippet: {r['body']}\nSource: {r['href']}"
                results.append(snippet)
                # print(f"[DEBUG] Found snippet: {r['title']}")
    except Exception as e:
        print(f"Error performing web search: {e}")
        return ["Error: Could not retrieve web search results."]
    
    print(f"[DEBUG] Total snippets found: {len(results)}")
    return results
