# Imports
import re
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import ToolMessage, AIMessage
from groq import BadRequestError
from langchain_google_genai import ChatGoogleGenerativeAI
from rich import print

import tools as custom_tools
import prompts
from dotenv import load_dotenv
load_dotenv()

# Tools
searcher_tools = [custom_tools.web_search]
reader_tools = [custom_tools.scrape_url]

MAX_TOOL_ROUNDS = 1
MAX_WRITE_ATTEMPTS = 3
APPROVAL_SCORE = 7 


# State
class State(TypedDict):
    topic: str
    messages: Annotated[list, add_messages]

    searcher: str
    reader: str
    writer: str
    critic: str

    is_approved: bool
    attempt: int
    search_attempts: int
    read_attempts: int
    reader_start: int  


# Model / LLM
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3)
searcher_llm = llm.bind_tools(tools=searcher_tools)
reader_llm = llm.bind_tools(tools=reader_tools)
writer_llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.7)
critic_llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.2)


def safe_tool_invoke(model, messages):
    """Invoke a tool-bound model. If the model tries to call a tool that
    isn't in our list (gpt-oss has built-ins like web_open), Groq returns a
    400 'tool_use_failed'. Treat that as 'no more tool calls'."""
    try:
        return model.invoke(messages)
    except BadRequestError as e:
        if "tool_use_failed" in str(e):
            return AIMessage(content="Finished gathering information.")
        raise


# Nodes
def searcher_node(state: State):
    prompt_msgs = prompts.SEARCH_PROMPT.invoke({"topic": state["topic"]}).to_messages()
    attempts = state.get("search_attempts", 0)

    if attempts >= MAX_TOOL_ROUNDS:
        return {
            "messages": [AIMessage(content="Search complete.")],
            "search_attempts": attempts + 1,
        }

    response = safe_tool_invoke(searcher_llm, prompt_msgs + state["messages"])

    return {
        "messages": [response],
        "search_attempts": attempts + 1,
    }


searcher_tool_node = ToolNode(tools=searcher_tools)


def extract_search_results_node(state: State):
    search_results = [
        m.content for m in state["messages"] if isinstance(m, ToolMessage)
    ]

    return {
        "searcher": "\n\n".join(search_results),
        "reader_start": len(state["messages"]),
    }


def reader_node(state: State):
    prompt_msgs = prompts.READER_PROMPT.invoke({
        "topic": state["topic"],
        "search_results": state["searcher"],
    }).to_messages()

    attempts = state.get("read_attempts", 0)
    history = state["messages"][state.get("reader_start", 0):]

    if attempts >= MAX_TOOL_ROUNDS:
        return {
            "messages": [AIMessage(content="Reading complete.")],
            "read_attempts": attempts + 1,
        }

    response = safe_tool_invoke(reader_llm, prompt_msgs + history)

    return {
        "messages": [response],
        "read_attempts": attempts + 1,
    }


reader_tool_node = ToolNode(tools=reader_tools)


def extract_reader_results_node(state: State):
    reader_results = [
        m.content
        for m in state["messages"]
        if isinstance(m, ToolMessage) and m.name == "scrape_url"
    ]

    return {"reader": "\n\n---\n\n".join(reader_results)}


def writer_node(state: State):
    research = (
        f"SEARCH RESULTS:\n\n"
        f"{state['searcher']}\n\n"
        f"DETAILED READING:\n\n"
        f"{state['reader']}"
    )

    messages = prompts.WRITER_PROMPT.invoke({
        "topic": state["topic"],
        "research": research,
        "critique": state["critic"],
        "previous_draft": state["writer"],
    })

    response = writer_llm.invoke(messages)

    return {
        "writer": response.content,
        "attempt": state["attempt"] + 1,
    }


def critic_node(state: State):
    messages = prompts.CRITIC_PROMPT.invoke({"report": state["writer"]})

    response = critic_llm.invoke(messages)

    if isinstance(response.content, str):
        review_text = response.content.strip()
    else:
        review_text = "\n".join(
            block.get("text", "")
            for block in response.content
            if isinstance(block, dict)
        ).strip()

    m = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", review_text, re.I)
    score = float(m.group(1)) if m else 0.0

    return {
        "critic": review_text,
        "is_approved": score >= APPROVAL_SCORE,
    }


# Routers 
def searcher_router(state: State):
    if getattr(state["messages"][-1], "tool_calls", None):
        return "search_tool"
    return "extract_search_result"


def reader_router(state: State):
    if getattr(state["messages"][-1], "tool_calls", None):
        return "read_tool"
    return "extract_read_result"


def critic_router(state: State):
    if state["is_approved"] or state["attempt"] >= MAX_WRITE_ATTEMPTS:
        return "end"
    return "revise"


# Graph creation
graph = StateGraph(State)

# Adding nodes
graph.add_node("searcher", searcher_node)
graph.add_node("search_tool", searcher_tool_node)
graph.add_node("extract_search_result", extract_search_results_node)

graph.add_node("reader", reader_node)
graph.add_node("read_tool", reader_tool_node)
graph.add_node("extract_read_result", extract_reader_results_node)

graph.add_node("writer", writer_node)
graph.add_node("critic", critic_node)

# Adding edges
graph.add_edge(START, "searcher")

graph.add_conditional_edges(
    "searcher",
    searcher_router,
    {
        "search_tool": "search_tool",
        "extract_search_result": "extract_search_result",
    },
)
graph.add_edge("search_tool", "searcher")
graph.add_edge("extract_search_result", "reader")

graph.add_conditional_edges(
    "reader",
    reader_router,
    {
        "read_tool": "read_tool",
        "extract_read_result": "extract_read_result",
    },
)
graph.add_edge("read_tool", "reader")
graph.add_edge("extract_read_result", "writer")

graph.add_edge("writer", "critic")

graph.add_conditional_edges(
    "critic",
    critic_router,
    {
        "revise": "writer",
        "end": END,
    },
)

app = graph.compile()


if __name__ == "__main__":
    initial_state = {
        "topic": "Impact of AI agents on software development",
        "messages": [],
        "searcher": "",
        "reader": "",
        "writer": "",
        "critic": "",
        "is_approved": False,
        "attempt": 0,
        "search_attempts": 0,
        "read_attempts": 0,
        "reader_start": 0,
    }

    result = app.invoke(initial_state, config={"recursion_limit": 50})

    print("\n" + "=" * 60)
    print("SEARCH RESULTS")
    print("=" * 60)
    print(result["searcher"])

    print("\n" + "=" * 60)
    print("RESEARCH / READER RESULTS")
    print("=" * 60)
    print(result["reader"])

    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(result["writer"])

    print("\n" + "=" * 60)
    print("FINAL CRITIC REVIEW")
    print("=" * 60)
    print(result["critic"])

    print("\n" + "=" * 60)
    print("WORKFLOW STATUS")
    print("=" * 60)
    print(f"Approved : {result['is_approved']}")
    print(f"Attempts : {result['attempt']}")