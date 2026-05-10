"""
highscore.py
Handles loading and saving the all-time high score to a plain text file.

Keeping file I/O in one dedicated module means no other part of the
codebase ever touches files directly — a clean separation of concerns.
"""

import os

# High score file sits alongside the game scripts
_FILE = os.path.join(os.path.dirname(__file__), "highscore.txt")


def load() -> int:
    """Read and return the saved high score.
    Returns 0 if the file does not exist or contains invalid data."""
    try:
        with open(_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save(score: int) -> None:
    """Write score to file only if it beats the current record."""
    if score > load():
        with open(_FILE, "w") as f:
            f.write(str(score))