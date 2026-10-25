"""The folder layout as rules the build checks, so it can't quietly drift.

1. Each folder imports only the folders below it (ALLOWED); main.py and discord_bot.py wire
   everything together, so they may import anything.
2. Only controllers/ and discord_bot.py import discord.
3. Only services/chart_drawing.py imports matplotlib.
"""

import ast
from pathlib import Path

SRC = Path(__file__).parents[1] / "src" / "fantasy_bot"

ALLOWED = {
    "controllers": {"services", "models"},
    "services": {"repositories", "clients", "models"},
    "repositories": {"database", "models"},
    "clients": {"contracts", "models"},
    "models": set(),
    "contracts": set(),
    "config": set(),
    "database": set(),
}
ONLY_IN = {
    "discord": ("controllers", "discord_bot.py"),
    "matplotlib": ("services/chart_drawing.py",),
}


def imports_of(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def violations() -> list[str]:
    found = []
    for path in sorted(SRC.rglob("*.py")):
        where = path.relative_to(SRC).as_posix()
        folder = where.split("/")[0]
        for name in imports_of(path):
            target = name.split(".")
            for library, places in ONLY_IN.items():
                if target[0] == library and not where.startswith(places):
                    found.append(f"{where} imports {library}")
            if target[0] != "fantasy_bot" or len(target) < 2 or folder not in ALLOWED:
                continue
            if target[1] != folder and target[1] not in ALLOWED[folder]:
                found.append(f"{where} imports {name}")
    return found


def test_layout_rules_hold() -> None:
    assert violations() == []


def test_every_folder_is_covered_by_the_rules() -> None:
    folders = {p.name for p in SRC.iterdir() if p.is_dir() and p.name != "__pycache__"}
    assert folders == set(ALLOWED)
