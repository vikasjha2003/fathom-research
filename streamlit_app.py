import re
import streamlit as st

# Importing is safe: main.py only runs its demo under if __name__ == "__main__".
from main import app as research_app

st.set_page_config(
    page_title="Fathom Research",
    page_icon="🌊",
    layout="wide"
)


# ============================================================
# Helpers
# ============================================================

def new_state(topic: str) -> dict:
    return {
        "topic": topic,
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


def parse_score(review: str):
    """
    Extract score from:
    Score: 8/10
    Score: 8.5/10
    """
    m = re.search(
        r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10",
        review or "",
        re.I
    )

    return f"{m.group(1)}/10" if m else None


def format_report(text: str) -> str:
    """
    Fix common formatting issues in LLM-generated Markdown.

    In particular:
        a. First point b. Second point c. Third point

    becomes:

        a. First point

        b. Second point

        c. Third point
    """

    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # --------------------------------------------------------
    # Fix alphabetic subpoints:
    #
    # "a. Point one b. Point two c. Point three"
    #
    # ->
    #
    # "a. Point one
    #
    # b. Point two
    #
    # c. Point three"
    # --------------------------------------------------------

    text = re.sub(
        r"(?<!\n)\s+([a-z])\.\s+",
        r"\n\n\1. ",
        text
    )

    # --------------------------------------------------------
    # Fix numbered points:
    #
    # "1. Point one 2. Point two 3. Point three"
    # --------------------------------------------------------

    text = re.sub(
        r"(?<!\n)\s+(\d+)\.\s+",
        r"\n\n\1. ",
        text
    )

    # --------------------------------------------------------
    # Fix bullet points accidentally placed on same line:
    #
    # "- Point one - Point two"
    # --------------------------------------------------------

    text = re.sub(
        r"(?<!\n)\s+-\s+",
        r"\n\n- ",
        text
    )

    # --------------------------------------------------------
    # Avoid excessive blank lines
    # --------------------------------------------------------

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def tool_call_args(update: dict, key: str):
    """Pull argument values (queries / urls) from tool calls."""
    out = []

    for msg in update.get("messages", []):
        for call in getattr(msg, "tool_calls", None) or []:
            val = call.get("args", {}).get(key)

            if val:
                out.append(val)

    return out


def slugify(text: str) -> str:
    return (
        re.sub(r"[^a-z0-9]+", "-", text.lower())
        .strip("-")[:50]
        or "report"
    )


# ============================================================
# Run Pipeline
# ============================================================

def run_pipeline(topic: str, status) -> dict:

    state = new_state(topic)

    for event in research_app.stream(
        state,
        config={"recursion_limit": 50},
        stream_mode="updates"
    ):

        for node, update in event.items():

            if not update:
                continue

            # Update our local state
            for key, value in update.items():
                if key != "messages":
                    state[key] = value

            # ------------------------------------------------
            # Searcher
            # ------------------------------------------------

            if node == "searcher":

                queries = tool_call_args(update, "query")

                if queries:
                    status.update(
                        label="Searching the web…"
                    )

                    status.write(
                        "🔎 **Searching:** "
                        + " · ".join(
                            f"`{q}`" for q in queries
                        )
                    )

            # ------------------------------------------------
            # Search tool
            # ------------------------------------------------

            elif node == "search_tool":

                status.write(
                    "✅ Search results received"
                )

            # ------------------------------------------------
            # Reader
            # ------------------------------------------------

            elif node == "reader":

                urls = tool_call_args(update, "url")

                if urls:

                    status.update(
                        label="Reading sources…"
                    )

                    status.write(
                        "📖 **Reading:**\n"
                        + "\n".join(
                            f"- {u}" for u in urls
                        )
                    )

            # ------------------------------------------------
            # Reader tool
            # ------------------------------------------------

            elif node == "read_tool":

                status.write(
                    "✅ Sources read"
                )

            # ------------------------------------------------
            # Writer
            # ------------------------------------------------

            elif node == "writer":

                status.update(
                    label="Writing report…"
                )

                status.write(
                    f"✍️ Draft {state['attempt']} written"
                )

                status.update(
                    label="Reviewing draft…"
                )

            # ------------------------------------------------
            # Critic
            # ------------------------------------------------

            elif node == "critic":

                score = (
                    parse_score(state["critic"])
                    or "n/a"
                )

                if state["is_approved"]:

                    status.write(
                        f"🧐 Review: **{score}**, approved"
                    )

                elif state["attempt"] >= 3:

                    status.write(
                        f"🧐 Review: **{score}**, "
                        "not approved "
                        "(attempt limit reached)"
                    )

                else:

                    status.write(
                        f"🧐 Review: **{score}**, "
                        "revision requested"
                    )

                    status.update(
                        label="Revising report…"
                    )

    return state


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.markdown("### 🌊 Fathom Research")

    st.caption(
        "A multi-agent research pipeline."
    )

    st.markdown(
        """
        1. **Searcher** finds sources
        2. **Reader** scrapes the best ones
        3. **Writer** drafts the report
        4. **Critic** reviews it and the writer revises
        """
    )


# ============================================================
# Header
# ============================================================

st.title("🌊 Fathom Research")

st.caption(
    "Enter a topic and a team of agents will "
    "search, read, write and review a report."
)


# ============================================================
# Input
# ============================================================

with st.form("topic_form"):

    topic = st.text_input(
        "Research topic",
        placeholder=(
            "e.g. Impact of AI agents on "
            "software development"
        ),
    )

    submitted = st.form_submit_button(
        "Start research",
        type="primary"
    )


# ============================================================
# Run
# ============================================================

if submitted:

    if not topic.strip():

        st.warning(
            "Please enter a topic first."
        )

    else:

        st.session_state.pop(
            "result",
            None
        )

        st.session_state.pop(
            "topic",
            None
        )

        with st.status(
            "Starting…",
            expanded=True
        ) as status:

            try:

                result = run_pipeline(
                    topic.strip(),
                    status
                )

                st.session_state["result"] = result
                st.session_state["topic"] = topic.strip()

                status.update(
                    label="Research complete",
                    state="complete",
                    expanded=False
                )

            except Exception as e:

                status.update(
                    label="Something went wrong",
                    state="error",
                    expanded=True
                )

                st.error(
                    f"{type(e).__name__}: {e}"
                )


# ============================================================
# Results
# ============================================================

result = st.session_state.get("result")


if result:

    score = parse_score(
        result["critic"]
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Status",
        "Approved"
        if result["is_approved"]
        else "Not approved"
    )

    c2.metric(
        "Drafts",
        result["attempt"]
    )

    c3.metric(
        "Critic score",
        score or "n/a"
    )


    # --------------------------------------------------------
    # Tabs
    # --------------------------------------------------------

    tab_report, tab_review, tab_search, tab_read = st.tabs(
        [
            "📄 Report",
            "🧐 Critic review",
            "🔎 Search results",
            "📖 Source reading"
        ]
    )


    # ========================================================
    # Report
    # ========================================================

    with tab_report:

        report = format_report(
            result["writer"]
        )

        st.markdown(report)

        st.download_button(
            "Download report (.md)",
            data=report,
            file_name=(
                f"{slugify(
                    st.session_state.get(
                        'topic',
                        'report'
                    )
                )}.md"
            ),
            mime="text/markdown",
        )


    # ========================================================
    # Critic
    # ========================================================

    with tab_review:

        critic = format_report(
            result["critic"]
        )

        st.markdown(critic)


    # ========================================================
    # Search Results
    # ========================================================

    with tab_search:

        st.text(
            result["searcher"]
            or "No search results."
        )


    # ========================================================
    # Source Reading
    # ========================================================

    with tab_read:

        st.text(
            result["reader"]
            or "No pages were read."
        )