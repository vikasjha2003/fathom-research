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

Previous draft (empty if this is the first draft):
{previous_draft}

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
- If a critique is given, revise the previous draft: fix every issue it raises and keep its strong parts unchanged.
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
        """Rate this research report from 1 to 10 for an intelligent general reader.

Scoring guide:
- 9-10: exceptional; specific, well-sourced, insightful
- 7-8: solid; clear structure, specific findings, claims attributed to sources, only minor gaps
- 5-6: noticeable problems such as vague findings, missing attribution or thin analysis
- 1-4: major problems

Notes:
- You cannot see the source material, so judge specificity, attribution and internal
  consistency, not whether facts are true.

Report:
{report}

Reply in exactly this format:

Score: X/10
Strengths: <max 2 short bullets>
Fixes: <only changes that would materially improve the report, max 3 short bullets, or "None">"""
    ),
])