#!/usr/bin/env python3
"""Says which installed copies of the persona kit are behind this one, and which apps declare
themselves for the chat feed.

    python3 persona/check.py [folder ...]     default: ~/Documents

There is no list of apps to read: it looks for `persona/core.py` (or any `core.py` beside an
`adapters/change_page.py`) under each folder and compares its VERSION line with this repo's.
For each copy it also says whether the app has its settings file (`docs/personas/kit.json`),
which is what switches the chat feed on. Exit code 1 when a copy is behind.
To update a copy: copy this `persona/` folder over it, then run that app's own tests."""
import os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from adapters import tmux  # noqa: E402

SKIP = {"node_modules", ".git", ".venv", "venv", "__pycache__", "worktrees", "site-packages", "dist", "build"}
DEPTH = 6


def version(path):
    try:
        m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)', Path(path).read_text(), re.M)
    except OSError:
        return None
    return m.group(1) if m else None


def copies(roots):
    """[(path to core.py, version)] for every installed copy under the roots, this repo's own left out."""
    out = []
    for root in roots:
        root = Path(root).expanduser()
        base = len(root.parts)
        for d, dirs, files in os.walk(root):
            p = Path(d)
            dirs[:] = [x for x in dirs if x not in SKIP and len(p.parts) - base < DEPTH]
            if "core.py" in files and (p / "adapters" / "change_page.py").is_file() and p.resolve() != HERE:
                out.append((p / "core.py", version(p / "core.py") or "?"))
    return sorted(out)


def declared(core_py):
    """Does the app this copy sits in have its settings file, so chats there feed its personas?"""
    return tmux.find_app(str(Path(core_py).parent)) is not None


def main():
    mine = version(HERE / "core.py")
    found = copies(sys.argv[1:] or [Path.home() / "Documents"])
    behind = 0
    for path, v in found:
        ok = v == mine
        behind += not ok
        feed = "declares itself" if declared(path) else f"no {tmux.SETTINGS} (chat feed off)"
        print(f"{'ok    ' if ok else 'BEHIND'} {v:>6}  {path.parent}  · {feed}")
    print(f"this repo: {mine} · {len(found)} installed, {behind} behind" if found else f"this repo: {mine} · no installed copies found")
    return 1 if behind else 0


if __name__ == "__main__":
    sys.exit(main())
