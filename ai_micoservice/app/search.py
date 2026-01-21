from duckduckgo_search import DDGS
from app.logger import logger

#take search query from user 
#ssearch intrnt using ddg

def web_search(query: str, max_results: int = 10) -> list[str]:
    """
    Performs a web search using DuckDuckGo and returns a list of result snippets.
    """
    #store search result
    results = []
    #print what query we are searching
    logger.debug(f"Performing web search for: {query}")
    try:
        with DDGS() as ddgs:
            # Reverting to default region but keeping English priority in search query
            ddgs_results = ddgs.text(query, max_results=max_results)
            for r in ddgs_results:
                snippet = f"Title: {r['title']}\nSnippet: {r['body']}\nSource: {r['href']}"
                results.append(snippet)
                # print(f"[DEBUG] Found snippet: {r['title']}")
    except Exception as e:
        logger.error(f"Error performing web search: {e}", exc_info=True)
        return ["Error: Could not retrieve web search results."]
    
    logger.info(f"Total snippets found: {len(results)}")
    if results:
        logger.info(f"First Snippet: {results[0][:200]}...")
    return results
