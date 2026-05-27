from __future__ import annotations

import json
import os
import re
import tomllib
from collections import Counter
from pathlib import Path

from pathspec import GitIgnoreSpec

from research_agent.logging_setup import get_logger
from research_agent.schemas import ManifestInfo, ScanResult

log = get_logger(__name__)


IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git", ".hg", ".svn",
        "node_modules", ".pnpm-store", "bower_components",
        ".venv", "venv", "env", "__pycache__", ".pytest_cache",
        ".mypy_cache", ".ruff_cache",
        "target", "build", "dist", "out", ".next", ".nuxt", ".svelte-kit",
        "vendor",
        "lib", "broadcast", "cache", "artifacts",
        ".idea", ".vscode",
        ".chroma_cache",
    }
)

IGNORE_FILE_REGEX = re.compile(r"\.(lock|min\.(js|css)|map)$")

EXT_TO_LANG: dict[str, str] = {
    ".py": "Python", ".pyi": "Python",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".rs": "Rust",
    ".go": "Go",
    ".sol": "Solidity",
    ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".swift": "Swift",
    ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir",
    ".c": "C", ".h": "C",
    ".cpp": "C++", ".hpp": "C++", ".cc": "C++",
}

DEP_TO_FRAMEWORK: dict[str, str] = {
    "next": "Next.js",
    "react": "React",
    "vue": "Vue",
    "svelte": "Svelte",
    "@sveltejs/kit": "SvelteKit",
    "nuxt": "Nuxt",
    "express": "Express",
    "fastify": "Fastify",
    "@nestjs/core": "NestJS",
    "vite": "Vite",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "starlette": "Starlette",
    "transformers": "HuggingFace Transformers",
    "axum": "Axum",
    "actix-web": "Actix",
    "rocket": "Rocket",
    "tokio": "Tokio",
    "rails": "Rails",
    "laravel/framework": "Laravel",
    "flutter": "Flutter",
    "phoenix": "Phoenix",
}

GO_PKG_TO_FRAMEWORK: dict[str, str] = {
    "github.com/gin-gonic/gin": "Gin",
    "github.com/labstack/echo": "Echo",
    "github.com/gofiber/fiber": "Fiber",
}


def _load_gitignore(root: Path) -> GitIgnoreSpec | None:
    gi = root / ".gitignore"
    if not gi.is_file():
        return None
    try:
        lines = gi.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return GitIgnoreSpec.from_lines(lines)


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return True
    return b"\x00" in chunk


def _count_lines(path: Path) -> int:
    try:
        with path.open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def _parse_package_json(path: Path) -> ManifestInfo | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            for k, v in section.items():
                if isinstance(k, str) and isinstance(v, str):
                    deps[k] = v
    scripts = {k: v for k, v in (data.get("scripts") or {}).items() if isinstance(v, str)}
    return ManifestInfo(path=str(path), kind="npm", dependencies=deps, scripts=scripts)


def _parse_pyproject(path: Path) -> ManifestInfo | None:
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    deps: dict[str, str] = {}
    proj = data.get("project") or {}
    for item in proj.get("dependencies") or []:
        if isinstance(item, str):
            name, _, ver = item.partition(">=" if ">=" in item else "==")
            deps[name.strip().split("[")[0]] = ver.strip() or "*"
    poetry = (data.get("tool") or {}).get("poetry") or {}
    for name, ver in (poetry.get("dependencies") or {}).items():
        if isinstance(name, str):
            deps[name] = ver if isinstance(ver, str) else "*"
    return ManifestInfo(path=str(path), kind="python", dependencies=deps)


def _parse_requirements(path: Path) -> ManifestInfo | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    deps: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = re.split(r"[<>=!~\s]", line, maxsplit=1)[0]
        if name:
            deps[name.split("[")[0]] = line[len(name):].strip() or "*"
    return ManifestInfo(path=str(path), kind="pip", dependencies=deps)


def _parse_cargo(path: Path) -> ManifestInfo | None:
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    deps: dict[str, str] = {}
    for section in ("dependencies", "dev-dependencies"):
        for k, v in (data.get(section) or {}).items():
            if isinstance(k, str):
                deps[k] = v if isinstance(v, str) else "*"
    return ManifestInfo(path=str(path), kind="cargo", dependencies=deps)


def _parse_go_mod(path: Path) -> ManifestInfo | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    deps: dict[str, str] = {}
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block and line == ")":
            in_block = False
            continue
        if in_block or line.startswith("require "):
            parts = line.replace("require ", "").split()
            if len(parts) >= 2:
                deps[parts[0]] = parts[1]
    return ManifestInfo(path=str(path), kind="go", dependencies=deps)


def _parse_foundry(path: Path) -> ManifestInfo:
    return ManifestInfo(path=str(path), kind="foundry", dependencies={})


def _parse_hardhat(path: Path) -> ManifestInfo:
    return ManifestInfo(path=str(path), kind="hardhat", dependencies={})


def _parse_gemfile(path: Path) -> ManifestInfo | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    deps: dict[str, str] = {}
    for m in re.finditer(r"gem\s+['\"]([^'\"]+)['\"]\s*(?:,\s*['\"]([^'\"]+)['\"])?", text):
        deps[m.group(1)] = m.group(2) or "*"
    return ManifestInfo(path=str(path), kind="ruby", dependencies=deps)


def _parse_composer(path: Path) -> ManifestInfo | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    deps: dict[str, str] = {}
    for key in ("require", "require-dev"):
        for k, v in (data.get(key) or {}).items():
            if isinstance(k, str) and isinstance(v, str):
                deps[k] = v
    return ManifestInfo(path=str(path), kind="composer", dependencies=deps)


def _parse_pubspec(path: Path) -> ManifestInfo:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ManifestInfo(path=str(path), kind="pubspec", dependencies={})
    deps: dict[str, str] = {}
    for m in re.finditer(r"^\s{2}([a-zA-Z0-9_]+):\s*([^\s#]+)?", text, re.MULTILINE):
        name = m.group(1)
        if name not in {"dependencies", "dev_dependencies", "flutter"}:
            deps[name] = (m.group(2) or "*").strip()
    if "flutter" in text:
        deps.setdefault("flutter", "*")
    return ManifestInfo(path=str(path), kind="pubspec", dependencies=deps)


def _parse_mix_exs(path: Path) -> ManifestInfo:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ManifestInfo(path=str(path), kind="mix", dependencies={})
    deps: dict[str, str] = {}
    for m in re.finditer(r"\{:([a-z_]+)\s*,\s*\"([^\"]+)\"", text):
        deps[m.group(1)] = m.group(2)
    return ManifestInfo(path=str(path), kind="mix", dependencies=deps)


MANIFEST_PARSERS: dict[str, callable] = {
    "package.json": _parse_package_json,
    "pyproject.toml": _parse_pyproject,
    "requirements.txt": _parse_requirements,
    "Cargo.toml": _parse_cargo,
    "go.mod": _parse_go_mod,
    "foundry.toml": _parse_foundry,
    "Gemfile": _parse_gemfile,
    "composer.json": _parse_composer,
    "pubspec.yaml": _parse_pubspec,
    "mix.exs": _parse_mix_exs,
}


def _detect_frameworks(manifests: list[ManifestInfo]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        if name not in seen:
            seen.add(name)
            found.append(name)

    for m in manifests:
        if m.kind == "foundry":
            _add("Foundry")
        if m.kind == "hardhat":
            _add("Hardhat")
        for dep in m.dependencies:
            if dep in DEP_TO_FRAMEWORK:
                _add(DEP_TO_FRAMEWORK[dep])
            if m.kind == "go":
                for pkg, fw in GO_PKG_TO_FRAMEWORK.items():
                    if dep.startswith(pkg):
                        _add(fw)
    return found


def _build_directory_tree(root: Path, max_entries: int = 50) -> str:
    lines: list[str] = [root.name + "/"]
    entries = 0
    try:
        top = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return root.name + "/"

    for level1 in top:
        if entries >= max_entries:
            lines.append("  ... (truncated)")
            break
        if level1.name in IGNORE_DIRS or level1.name.startswith("."):
            continue
        marker = "/" if level1.is_dir() else ""
        lines.append(f"  {level1.name}{marker}")
        entries += 1

        if level1.is_dir():
            try:
                sub = sorted(level1.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except OSError:
                continue
            for level2 in sub:
                if entries >= max_entries:
                    break
                if level2.name in IGNORE_DIRS or level2.name.startswith("."):
                    continue
                m2 = "/" if level2.is_dir() else ""
                lines.append(f"    {level2.name}{m2}")
                entries += 1

    return "\n".join(lines)


def _read_git_remote(root: Path) -> str | None:
    cfg = root / ".git" / "config"
    if not cfg.is_file():
        return None
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r'\[remote "origin"\][^\[]*url\s*=\s*(\S+)', text)
    return m.group(1) if m else None


def _read_readme(root: Path) -> str | None:
    for name in ("README.md", "README.MD", "README.rst", "README.txt", "README"):
        p = root / name
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="replace")[:2000]
            except OSError:
                return None
    return None


def scan(path: str | Path, *, max_files: int = 5000) -> ScanResult:
    root = Path(path).expanduser().resolve()
    warnings: list[str] = []

    if not root.exists():
        return ScanResult(root_path=str(root), warnings=[f"path does not exist: {root}"])
    if not root.is_dir():
        return ScanResult(root_path=str(root), warnings=[f"path is not a directory: {root}"])

    gitignore = _load_gitignore(root)
    languages: Counter[str] = Counter()
    manifests: list[ManifestInfo] = []
    build_tools: set[str] = set()
    file_count = 0
    line_count = 0
    truncated = False

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        dir_path = Path(dirpath)
        for filename in filenames:
            if file_count >= max_files:
                truncated = True
                break

            if IGNORE_FILE_REGEX.search(filename):
                continue

            full = dir_path / filename
            try:
                rel = full.relative_to(root).as_posix()
            except ValueError:
                continue

            if gitignore and gitignore.match_file(rel):
                continue

            file_count += 1
            ext = full.suffix.lower()
            if ext in EXT_TO_LANG:
                languages[EXT_TO_LANG[ext]] += 1
                if not _is_binary(full):
                    line_count += _count_lines(full)

            if filename in MANIFEST_PARSERS:
                parser = MANIFEST_PARSERS[filename]
                parsed = parser(full)
                if parsed is not None:
                    manifests.append(parsed)

            if filename.startswith("hardhat.config."):
                manifests.append(_parse_hardhat(full))
                build_tools.add("Hardhat")
            if filename == "foundry.toml":
                build_tools.add("Foundry")
            if filename == "Dockerfile":
                build_tools.add("Docker")
            if filename == "Makefile":
                build_tools.add("Make")
            if filename == "docker-compose.yml" or filename == "docker-compose.yaml":
                build_tools.add("Docker Compose")
            if filename == "remappings.txt":
                build_tools.add("Foundry")

        if truncated:
            warnings.append(f"scan truncated at {max_files} files")
            break

    primary = languages.most_common(1)[0][0] if languages else None
    frameworks = _detect_frameworks(manifests)
    tree = _build_directory_tree(root)
    git_remote = _read_git_remote(root)
    readme = _read_readme(root)

    return ScanResult(
        root_path=str(root),
        languages=dict(languages.most_common(10)),
        primary_language=primary,
        frameworks=frameworks,
        manifests=manifests,
        build_tools=sorted(build_tools),
        directory_tree=tree,
        file_count=file_count,
        line_count_estimate=line_count,
        readme_excerpt=readme,
        git_remote=git_remote,
        warnings=warnings,
    )
