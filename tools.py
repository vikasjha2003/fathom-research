import os
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from langchain.tools import tool

from dotenv import load_dotenv
load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def clean_text(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(" ", strip=True)


@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic.
    Returns title, url and snippet.
    """

    results = tavily.search(
        query=query,
        max_results=5
    )

    out = []

    for r in results["results"]:
        snippet = clean_text(r["content"][:3000])

        out.append(
            f"Title: {clean_text(r['title'])}\n"
            f"URL: {r['url']}\n"
            f"Snippet: {snippet}"
        )

    return "\n----\n".join(out)


@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper reading."""

    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        text = soup.get_text(" ", strip=True)

        return text[:3000]

    except Exception as e:
        return f"Could not scrape URL: {str(e)}"