from duckduckgo_search import DDGS
import sys

def test_search(query):
    print(f"Testing search for: '{query}'")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                print("FAILED: No results returned.")
            else:
                print(f"SUCCESS: Found {len(results)} results.")
                for i, r in enumerate(results):
                    print(f"{i+1}. {r['title']} ({r['href']})")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What is Python?"
    test_search(q)
