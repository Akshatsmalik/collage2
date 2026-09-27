from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
import json
import subprocess

from file_tools import (
    abs_project_path,
    delete_file,
    edit_file,
    list_files,
    read_file,
    run_command,
    run_tests,
    search_files,
    write_file,
)

MODEL = "qwen3.5:2b"
REVIEW_MODEL = "qwen3.5:4b"
MAX_ATTEMPTS = 3
MAX_STALLS = 3


@tool
def list_project_files():
    """List all files available in the project workspace."""
    return list_files()


@tool
def search_project_files(query: str):
    """Search the project files for a specific text."""
    return search_files(query)


@tool
def read_project_file(path: str):
    """Read the contents of a project file."""
    return read_file(path)


@tool
def write_project_file(path: str, content: str):
    """Create a new file or completely overwrite an existing project file."""
    return write_file(path, content)


@tool
def edit_project_file(path: str, old_text: str, new_text: str):
    """Replace existing text inside a project file."""
    if old_text == new_text:
        return (
            "Error: old_text and new_text are identical — no change was made. "
            "You must provide an actual fix."
        )
    return edit_file(path, old_text, new_text)


@tool
def delete_project_file(path: str):
    """Delete a project file."""
    return delete_file(path)


@tool
def execute_project_command(command: str):
    """Execute a shell command inside the project workspace."""
    return run_command(command)


@tool
def run_project_tests():
    """Run the project's pytest test suite."""
    return run_tests()


tools = [
    list_project_files,
    search_project_files,
    read_project_file,
    write_project_file,
    edit_project_file,
    delete_project_file,
    execute_project_command,
    run_project_tests,
]

llm = ChatOllama(
    model=MODEL,
    temperature=0,
    num_ctx=8192,
    num_predict=10000,
    num_gpu=999,
    reasoning=True,
)
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

review_llm = ChatOllama(
    model=REVIEW_MODEL,
    num_ctx=8192,
    temperature=0,
    num_predict=2000,
    num_gpu=999,
)
summary_llm = ChatOllama(
    model=REVIEW_MODEL,
    num_ctx=8192,
    temperature=0,
    num_predict=10000,
    num_gpu=999,
)

SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a coding agent with access to file tools in a sandboxed workspace.\n"
        "Use tools to inspect and change files. Prefer write_project_file for new files "
        "or full rewrites. After you write a file, stop calling tools and wait for "
        "syntax, lint, and logic feedback. Never repeat a tool call with the same arguments."
    )
)

WRITE_TOOLS = {"write_project_file", "edit_project_file"}


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    target_path: str
    validated: bool
    logic_validated: bool
    attempts: int
    stalls: int


def message_text(msg) -> str:
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("text"):
                parts.append(str(part["text"]))
        return "".join(parts)
    return str(content or "")


def run_pylint(filepath: str) -> dict:
    abs_path = abs_project_path(filepath)
    proc = subprocess.run(
        ["pylint", abs_path, "--output-format=json"],
        capture_output=True,
        text=True,
        cwd=abs_project_path("."),
    )
    try:
        issues = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        issues = []
    errors = [i for i in issues if i.get("type") in ("error", "fatal")]
    return {"errors": errors, "passed": len(errors) == 0}


def run_eslint(filepath: str) -> dict:
    abs_path = abs_project_path(filepath)
    proc = subprocess.run(
        ["npx", "--yes", "eslint", abs_path, "-f", "json"],
        capture_output=True,
        text=True,
        cwd=abs_project_path("."),
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        return {"messages": [f"ESLint failed to run: {proc.stderr.strip()}"], "passed": False}
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return {"messages": [f"Could not parse ESLint output: {proc.stdout[:300]}"], "passed": False}
    error_count = sum(f.get("errorCount", 0) for f in data)
    messages = [
        f"Line {m.get('line')}: {m.get('message')} ({m.get('ruleId')})"
        for f in data
        for m in f.get("messages", [])
    ]
    return {"messages": messages, "passed": error_count == 0}


def call_llm(state: AgentState):
    response = llm_with_tools.invoke([SYSTEM_PROMPT] + state["messages"])
    return {"messages": [response]}


def capture_write_path(state: AgentState):
    last_ai = next(
        (m for m in reversed(state["messages"]) if isinstance(m, AIMessage)),
        None,
    )
    if last_ai and last_ai.tool_calls:
        for tc in last_ai.tool_calls:
            if tc["name"] in WRITE_TOOLS:
                path = tc.get("args", {}).get("path")
                if path:
                    return {"target_path": path, "validated": False, "logic_validated": False}
    return {}


def validate_node(state: AgentState):
    path = state.get("target_path") or ""
    if not path:
        return {
            "validated": True,
            "messages": [SystemMessage(content="No file path to validate; skipping.")],
        }

    if path.endswith(".py"):
        syntax = run_command(f'python -m py_compile "{path}"')
        syntax_ok = syntax.startswith("Exit code: 0")
        lint = run_pylint(path) if syntax_ok else None

        def format_errors(lint_result):
            return "\n".join(
                f"Line {e['line']}: {e['message']} ({e['symbol']})"
                for e in lint_result["errors"]
            )
    elif path.endswith((".js", ".jsx", ".ts", ".tsx")):
        syntax = run_command(f'node --check "{path}"')
        syntax_ok = syntax.startswith("Exit code: 0")
        lint = run_eslint(path) if syntax_ok else None

        def format_errors(lint_result):
            return "\n".join(lint_result["messages"])
    else:
        return {
            "validated": True,
            "messages": [SystemMessage(content=f"No linter configured for {path}; skipping.")],
        }

    if not syntax_ok:
        attempts = state.get("attempts", 0) + 1
        feedback = (
            f"Syntax check FAILED for {path}. Error:\n\n{syntax}\n\n"
            f"Call write_project_file with the COMPLETE corrected file content."
        )
        return {"messages": [SystemMessage(content=feedback)], "validated": False, "attempts": attempts}

    passed = lint["passed"] if lint else True
    if passed:
        return {
            "messages": [SystemMessage(content=f"Syntax and lint checks PASSED for {path}.")],
            "validated": True,
        }

    attempts = state.get("attempts", 0) + 1
    feedback = (
        f"Lint check FAILED for {path}. Errors:\n\n{format_errors(lint)}\n\n"
        f"Call write_project_file with the COMPLETE corrected file content "
        f"(not edit_project_file — rewrite the whole file). "
        f"Fix each issue listed above."
    )
    return {"messages": [SystemMessage(content=feedback)], "validated": False, "attempts": attempts}


def logic_check_node(state: AgentState):
    path = state.get("target_path") or ""
    code = read_file(path)
    original_request = next(
        (message_text(m) for m in state["messages"] if isinstance(m, HumanMessage)),
        "",
    )
    review_prompt = f"""You are reviewing code for correctness against a user's request.
Check only LOGIC — does the code do what was asked? Ignore style.

User request: {original_request}

File: {path}
Code:
{code}

Respond with exactly one of these formats:
PASS
FAIL: <specific description of the logic bug and what it should do instead>
"""
    resp = review_llm.invoke([HumanMessage(content=review_prompt)])
    verdict = message_text(resp).strip()

    if verdict.upper().startswith("PASS"):
        return {
            "messages": [SystemMessage(content=f"Logic review PASSED for {path}.")],
            "logic_validated": True,
        }

    attempts = state.get("attempts", 0) + 1
    feedback = (
        f"Logic review FAILED for {path}. Reviewer feedback:\n\n{verdict}\n\n"
        f"Call write_project_file with the COMPLETE corrected file content "
        f"(not edit_project_file — rewrite the whole file) to fix this logic issue."
    )
    return {
        "messages": [SystemMessage(content=feedback)],
        "logic_validated": False,
        "attempts": attempts,
    }


def summary_node(state: AgentState):
    resp = summary_llm.invoke(
        state["messages"]
        + [
            HumanMessage(
                content=(
                    "The file passed syntax, lint, and logic validation. Give a short summary "
                    "of what the program does and confirm the work is done."
                )
            )
        ]
    )
    return {"messages": [resp]}


def stall_nudge_node(state: AgentState):
    stalls = state.get("stalls", 0) + 1
    return {
        "messages": [
            SystemMessage(
                content=(
                    "You stopped without calling a tool or giving an answer. "
                    "If you haven't written the file yet, call write_project_file now "
                    "with the complete file content — do not just describe your plan."
                )
            )
        ],
        "stalls": stalls,
    }


def after_llm(state: AgentState):
    lastmsg = state["messages"][-1]
    if getattr(lastmsg, "tool_calls", None):
        return "tools"
    if not message_text(lastmsg).strip():
        if state.get("stalls", 0) >= MAX_STALLS:
            return END
        return "stall_nudge"
    return END


def after_route(state: AgentState):
    last_ai = next(
        (m for m in reversed(state["messages"]) if isinstance(m, AIMessage)),
        None,
    )
    if last_ai and last_ai.tool_calls:
        if any(tc["name"] in WRITE_TOOLS for tc in last_ai.tool_calls):
            return "validate"
    return "llm"


def after_validate(state: AgentState):
    if not state.get("validated"):
        if state.get("attempts", 0) >= MAX_ATTEMPTS:
            return END
        return "llm"
    return "logic_check"


def after_logic_check(state: AgentState):
    if state.get("logic_validated"):
        return "summary"
    if state.get("attempts", 0) >= MAX_ATTEMPTS:
        return END
    return "llm"


graph = StateGraph(AgentState)
graph.add_node("llm", call_llm)
graph.add_node("tools", tool_node)
graph.add_node("route", capture_write_path)
graph.add_node("validate", validate_node)
graph.add_node("logic_check", logic_check_node)
graph.add_node("summary", summary_node)
graph.add_node("stall_nudge", stall_nudge_node)

graph.add_edge(START, "llm")
graph.add_conditional_edges(
    "llm",
    after_llm,
    {"tools": "tools", "stall_nudge": "stall_nudge", END: END},
)
graph.add_edge("tools", "route")
graph.add_conditional_edges("route", after_route, {"validate": "validate", "llm": "llm"})
graph.add_conditional_edges(
    "validate",
    after_validate,
    {"logic_check": "logic_check", "llm": "llm", END: END},
)
graph.add_conditional_edges(
    "logic_check",
    after_logic_check,
    {"summary": "summary", "llm": "llm", END: END},
)
graph.add_edge("stall_nudge", "llm")
graph.add_edge("summary", END)

app = graph.compile()


def initial_state(task: str) -> AgentState:
    return {
        "messages": [HumanMessage(content=task)],
        "target_path": "",
        "validated": False,
        "logic_validated": False,
        "attempts": 0,
        "stalls": 0,
    }


def run_agent(task: str) -> None:
    for stream_type, chunk in app.stream(
        initial_state(task),
        config={"recursion_limit": 40},
        stream_mode=["updates", "messages"],
    ):
        if stream_type == "updates":
            for node_name in chunk:
                print(f"\n[{node_name} finished]")
        elif stream_type == "messages":
            msg_chunk, metadata = chunk
            if metadata.get("langgraph_node") == "llm" and getattr(msg_chunk, "content", None):
                text = message_text(msg_chunk)
                if text:
                    print(text, end="", flush=True)


if __name__ == "__main__":
    user = input("Please enter your task: ")
    run_agent(user)
    print("\nDONE")
