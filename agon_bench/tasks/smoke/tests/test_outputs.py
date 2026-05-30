"""Smoke task verification — check that hello.txt was created correctly."""
import os
from pathlib import Path
def test_hello_file_exists():
    """Verify hello.txt exists."""
    hello = Path.cwd() / "hello.txt"
    assert hello.exists(), f"Expected hello.txt to exist at {hello}"
def test_hello_file_content():
    """Verify hello.txt contains the exact expected content."""
    hello = Path.cwd() / "hello.txt"
    content = hello.read_text()
    expected = "Hello from Lenos!\n"
    assert content == expected, (
        f"File content mismatch.\n"
        f"Expected: {expected!r}\n"
        f"Got:      {content!r}"
    )
def test_hello_file_no_extra_whitespace():
    """Verify no trailing whitespace beyond the single newline."""
    hello = Path.cwd() / "hello.txt"
    content = hello.read_text()
    # Should end with exactly one newline
    assert content.endswith("\n"), "File should end with a newline"
    assert not content.endswith("\n\n"), "File should not have extra newlines"
