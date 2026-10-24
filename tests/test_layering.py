import ast
from pathlib import Path

SRC = Path(__file__).parents[1] / "src" / "fantasy_bot"

# Which top-level fantasy_bot packages each package may import (besides itself).
ALLOWED = {
    "models": set(),
    "calculations": {"models"},
    "repositories": {"models"},
    "clients": {"models"},
    "services": {"models", "calculations", "repositories", "clients"},
    "bot": {"models", "services"},
    "config": set(),
}


def imports_of(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_imports_only_point_down() -> None:
    violations = []
    for path in SRC.rglob("*.py"):
        package = path.relative_to(SRC).parts[0].removesuffix(".py")
        if package not in ALLOWED:
            continue  # main.py and __init__.py wire everything together
        for name in imports_of(path):
            parts = name.split(".")
            if parts[0] == "discord" and package != "bot":
                violations.append(f"{path.relative_to(SRC)} imports discord")
            if parts[0] == "fantasy_bot" and parts[1] not in ALLOWED[package] | {package}:
                violations.append(f"{path.relative_to(SRC)} imports {name}")
    assert violations == []
