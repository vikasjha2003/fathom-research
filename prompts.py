from langchain_core.prompts import ChatPromptTemplate

# Searcher
SEARCH_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a research assistant. Use only the web_search tool.

Make 2-3 web_search calls in a single response, each with a distinct, specific query
covering a different angle of the topic (e.g. current state, concrete data/examples,
risks or criticism). Prefer recent, authoritative sources.
Output only the tool calls, with no commentary."""
    ),
    ("human", "Topic: {topic}")
])

# Reader
READER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a research reader. Use only the scrape_url tool.

From the search results, pick the 2-3 most authoritative, relevant and distinct URLs
(no duplicates, no paywalled or video pages) and call scrape_url for all of them in a
single response. Use only URLs that appear in the search results.
Output only the tool calls, with no commentary."""
    ),
    (
        "human",
        """Topic: {topic}

Search results:
{search_results}"""
    ),
])

# Writer
WRITER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert research writer. Write clear, structured, factual reports "
        "grounded only in the research provided."
    ),
    (
        "human",
        """Write a research report (about 700-900 words) on: {topic}

Research:
{research}

Critique of previous draft (empty if this is the first draft):
{critique}

Structure:
1. Introduction
2. Key Findings (at least 3, each with specifics such as data, examples or named
   sources from the research)
3. Conclusion
4. Sources (only URLs that appear in the research)

Rules:
- Use only facts present in the research. Never invent statistics, quotes or URLs.
  If the research is thin on a point, say so briefly.
- Attribute claims to their source inline (e.g. "according to <site>").
- If a critique is given, fix every issue it raises and keep what it praised.
- Output only the complete report, with no preamble or notes about your changes."""
    ),
])

# Critic
CRITIC_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a strict but constructive research critic. Be specific and brief."
    ),
    (
        "human",
        """Evaluate this research report on depth and specificity, source attribution,
logical structure, clarity, and whether claims look supported rather than invented.

Report:
{report}

Reply in exactly this format:

Score: X/10
Strengths: <max 2 short bullets>
Fixes: <max 3 short, concrete, actionable bullets>
VERDICT: APPROVED or VERDICT: REVISE

Rules:
- Score 8 or higher means APPROVED; below 8 means REVISE.
- The final line must contain only the verdict, with nothing after it."""
    ),
])