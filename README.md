# Fathom Research

Fathom Research is a Python-based multi-agent research assistant built with LangGraph and LangChain. It automates the end-to-end research workflow:

- searches the web for relevant sources,
- reads the best candidate pages,
- writes a structured research report,
- and then has a critic agent review the draft and iterate until it is good enough.

The project is designed to feel like a lightweight research team with a clear handoff between specialized agents.

## Why this project exists

This repo turns a classic research workflow into a graph-based agent pipeline. Instead of having a single model perform everything at once, it breaks the process into multiple roles:

1. Searcher: finds relevant information and URLs.
2. Reader: chooses a small set of high-value sources and scrapes them.
3. Writer: drafts a research report grounded in the evidence gathered.
4. Critic: scores the report and advises revisions.

That architecture makes the workflow easier to reason about, easier to tune, and closer to how a human research team might work.

## Core capabilities

- Web search via Tavily
- URL scraping with BeautifulSoup and requests
- LLM-based agent orchestration using LangGraph
- Iterative revision loop with a quality gate
- Streamlit-based UI for interactive use
- Report output in markdown form with downloadable files

## Architecture overview

The project is intentionally compact but conceptually rich. The main logic is defined in `main.py` and the agents are coordinated through a `StateGraph`.

### Graph flow

The workflow proceeds like this:

- Start
- Searcher node generates search queries
- Search tool executes those queries
- Extract search results
- Reader node selects relevant URLs
- Read tool scrapes pages
- Extract reading results
- Writer creates a report
- Critic reviews the draft
- If the score is below the threshold, the writer revises the report
- Stop when approved or retry limit is reached

This yields a closed loop that balances exploration, evidence gathering, and quality control.

## Project structure

```text
fathom-research/
├── main.py                 # Core LangGraph research workflow
├── prompts.py              # Search, reader, writer, and critic prompts
├── tools.py                # Tavily search and page scraping tools
├── streamlit_app.py        # Interactive web interface
├── requirements.txt        # Python dependencies
├── .gitignore              # Project ignores
└── README.md               # Project documentation
```

## Key files

### `main.py`

This is the orchestration hub of the project.

It contains:

- the shared state schema,
- LLM model setup,
- tool adapters for the search and read steps,
- node logic for each agent,
- conditional routing for the graph,
- and a demo runner used when invoked directly.

Notable details:

- The project uses `ChatGroq` with `openai/gpt-oss-120b` for search and reading.
- The writer uses a Groq model with higher creativity.
- The critic uses `ChatGoogleGenerativeAI` with Gemini for scoring.
- The system has hard limits on search and read attempts via `MAX_TOOL_ROUNDS` and `MAX_WRITE_ATTEMPTS`.
- It uses a safety wrapper around tool invocation to handle certain unsupported tool-use errors gracefully.

### `prompts.py`

This file defines the core instructions for each agent.

- `SEARCH_PROMPT`: directs the searcher to issue focused, distinct web queries.
- `READER_PROMPT`: tells the reader to scrape the best URLs from search results.
- `WRITER_PROMPT`: instructs the writer to produce a factual, well-structured report with attribution.
- `CRITIC_PROMPT`: instructs the critic to score the report and provide concise revision guidance.

The prompt design is one of the main strengths of this repo: it encourages evidence-based writing and explicit attribution.

### `tools.py`

This file implements the actual tools used by the agents:

#### `web_search(query: str) -> str`

- uses Tavily to search the web,
- returns title, URL, and snippet,
- cleans HTML content and normalizes text.

#### `scrape_url(url: str) -> str`

- fetches a web page with a browser-like user agent,
- strips scripts/styles/navigation/footer noise,
- extracts meaningful text,
- returns the first ~3000 characters for downstream reading.

The tool layer is intentionally small and focused, which makes the research workflow easy to extend.

### `streamlit_app.py`

This is the project’s user-facing interface.

It provides:

- a text input for a research topic,
- a status panel that shows the progression of the workflow,
- metrics for approval state, draft count, and critic score,
- tabs for report, critic review, search results, and source reading,
- a markdown report download button.

In other words, this is the driving UI that makes the research pipeline usable to a human operator.

## How the agents collaborate

The pipeline is built around a strong division of labor:

### Searcher

The searcher does not read the full web; it identifies promising directions and fetches candidate sources. It is prompted to do 2–3 distinct searches on different angles of the topic.

### Reader

The reader consumes the search results and picks the best sources. This is important because it prevents the writer from being overloaded by noisy results. It applies a “few, strong sources” policy instead of trying to read everything.

### Writer

The writer compiles evidence into a structured report. It is constrained to use only the facts included in the research and to attribute claims inline to the source site.

### Critic

The critic acts like a review gate. It evaluates the report for specificity, attribution, and coherence, then either approves it or gives explicit improvements for the next rewrite.

This “writer + critic + revision” loop is the heart of the system.

## Data and state model

The system stores a shared state dictionary with fields such as:

- `topic`
- `messages`
- `searcher`
- `reader`
- `writer`
- `critic`
- `is_approved`
- `attempt`
- `search_attempts`
- `read_attempts`
- `reader_start`

This is enough to keep the research context consistent across nodes while still allowing the graph to branch and iterate.

## Environment and configuration

This project expects API keys and environment variables.

Create a `.env` file in the project root with values like:

```bash
TAVILY_API_KEY=your_tavily_key
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_google_api_key
```

These are loaded by:

- `tools.py` for Tavily
- `main.py` for model access
- `python-dotenv` at startup

## Dependencies

The project relies on the following major libraries:

- `langgraph`
- `langchain`
- `langchain-groq`
- `langchain-core`
- `langchain-tavily`
- `langchain-google-genai`
- `tavily-python`
- `requests`
- `beautifulsoup4`
- `streamlit`
- `python-dotenv`
- `rich`

See `requirements.txt` for the complete dependency list.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the app

Start the Streamlit app:

```bash
streamlit run streamlit_app.py
```

Then open the local URL shown in the terminal and enter a topic such as:

- "Impact of AI agents on software development"
- "Recent progress in autonomous coding agents"
- "Trends in AI-assisted developer tooling"

## Running the pipeline directly

You can also run the graph in a console-style demo mode:

```bash
python main.py
```

When executed directly, the script initializes a sample topic and prints:

- search results,
- read results,
- final report,
- critic review,
- and workflow status.

## Limitations and considerations

This repo is a strong prototype, but it has a few practical constraints:

- It depends on external APIs and will fail without valid credentials.
- The scraper is intentionally shallow and may not handle highly dynamic sites well.
- The text returned from scraped pages is limited to around 3000 characters per source.
- The system is built for research tasks rather than broad autonomous web crawling.
- The LLM has a fixed attempt budget, which prevents runaway loops.

## Example use cases

This project is useful for:

- market research and trend summarization,
- competitive analysis,
- quick synthesis of current knowledge,
- report drafting for topic exploration,
- experiments in multi-agent LLM workflows.

## Strengths of the implementation

- clear separation between research roles,
- iterative quality control via a critic,
- small and understandable codebase,
- good fit for experimentation and extension,
- straightforward UI for non-technical users.

## Summary

Fathom Research is a compact but thoughtful agentic research system. It demonstrates how a multi-agent workflow can organize search, reading, writing, and evaluation into a single coherent pipeline.

For a practical research assistant, it balances simplicity and power: a graph-driven architecture, external search and scraping, and a built-in review loop that tries to keep the output factual and readable.

## Notes

This project is built as a research/demo system and is best suited for experimentation and learning. It is not a production-grade web crawler or a full research platform out of the box, but it is a strong foundation for a more advanced workflow.

