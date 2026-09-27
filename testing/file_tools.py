from pathlib import Path
import subprocess

ROOT = (Path(__file__).resolve().parent / "workspace").resolve()
SKIP_DIR_NAMES = {"__pycache__", ".git", ".venv", "node_modules"}


def _safe_path(path: str) -> Path:
    """Resolve a relative path and keep it inside ROOT."""
    ROOT.mkdir(parents=True, exist_ok=True)
    full_path = (ROOT / path).resolve()
    if not full_path.is_relative_to(ROOT):
        raise ValueError("Access denied: path is outside the project directory.")
    return full_path


def abs_project_path(path: str) -> str:
    """Absolute path inside the workspace, for linters and compilers."""
    return str(_safe_path(path))


def _iter_files():
    ROOT.mkdir(parents=True, exist_ok=True)
    if not ROOT.exists():
        return
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        yield path


def list_files():
    files = [str(path.relative_to(ROOT)) for path in _iter_files()]
    if not files:
        return "No files found."
    return "\n".join(sorted(files))


def search_files(query: str):
    results = []
    for path in _iter_files():
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        if query in content:
            results.append(str(path.relative_to(ROOT)))
    if not results:
        return f"No files found containing: {query}"
    return "\n".join(results)


def read_file(path: str):
    file_path = _safe_path(path)
    if not file_path.exists():
        return f"File not found: {path}"
    if not file_path.is_file():
        return f"Not a file: {path}"
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Cannot read binary file: {path}"


def write_file(path: str, content: str):
    file_path = _safe_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {path}"


def edit_file(path: str, old_text: str, new_text: str):
    file_path = _safe_path(path)
    if not file_path.exists():
        return f"File not found: {path}"
    content = file_path.read_text(encoding="utf-8")
    if old_text not in content:
        return "The old_text was not found in the file."
    file_path.write_text(content.replace(old_text, new_text), encoding="utf-8")
    return f"Successfully edited {path}"


def delete_file(path: str):
    file_path = _safe_path(path)
    if not file_path.exists():
        return f"File not found: {path}"
    if not file_path.is_file():
        return f"Not a file: {path}"
    file_path.unlink()
    return f"Successfully deleted {path}"


def run_command(command: str):
    ROOT.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return (
            f"Exit code: {result.returncode}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )
    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds."
    except Exception as e:
        return f"Command failed: {str(e)}"


def run_tests():
    return run_command("pytest")
