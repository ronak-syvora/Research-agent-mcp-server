from pathlib import Path

from research_agent.tools import codebase_scanner


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_scan_missing_path(tmp_path: Path):
    result = codebase_scanner.scan(tmp_path / "does-not-exist")
    assert result.warnings
    assert "does not exist" in result.warnings[0]


def test_detect_nextjs_project(tmp_path: Path):
    _write(
        tmp_path / "package.json",
        '{"name":"app","dependencies":{"next":"14","react":"18"},"scripts":{"dev":"next dev"}}',
    )
    _write(tmp_path / "pages" / "index.tsx", "export default function P(){return null}")
    result = codebase_scanner.scan(tmp_path)
    assert "Next.js" in result.frameworks
    assert "React" in result.frameworks
    assert result.primary_language == "TypeScript"
    assert any(m.kind == "npm" for m in result.manifests)


def test_detect_foundry_project(tmp_path: Path):
    _write(tmp_path / "foundry.toml", "[profile.default]\nsrc='src'")
    _write(tmp_path / "src" / "Vault.sol", "// SPDX-License-Identifier: MIT\ncontract Vault {}")
    _write(tmp_path / "test" / "Vault.t.sol", "// test\ncontract VaultTest {}")
    result = codebase_scanner.scan(tmp_path)
    assert "Foundry" in result.frameworks
    assert "Foundry" in result.build_tools
    assert result.primary_language == "Solidity"


def test_detect_fastapi_project(tmp_path: Path):
    _write(
        tmp_path / "pyproject.toml",
        '[project]\nname="app"\ndependencies=["fastapi>=0.110","uvicorn>=0.25"]\n',
    )
    _write(tmp_path / "main.py", "from fastapi import FastAPI\napp = FastAPI()\n")
    result = codebase_scanner.scan(tmp_path)
    assert "FastAPI" in result.frameworks
    assert result.primary_language == "Python"
    manifests = [m for m in result.manifests if m.kind == "python"]
    assert manifests and "fastapi" in manifests[0].dependencies


def test_ignore_dirs_skip_node_modules(tmp_path: Path):
    _write(tmp_path / "package.json", '{"name":"x"}')
    _write(tmp_path / "node_modules" / "left-pad" / "index.js", "module.exports={}")
    _write(tmp_path / "app.ts", "export const x = 1")
    result = codebase_scanner.scan(tmp_path)
    assert result.languages.get("TypeScript", 0) == 1
    assert "JavaScript" not in result.languages


def test_gitignore_honored(tmp_path: Path):
    _write(tmp_path / ".gitignore", "secret/\n")
    _write(tmp_path / "src" / "a.py", "x=1")
    _write(tmp_path / "secret" / "b.py", "y=2")
    result = codebase_scanner.scan(tmp_path)
    assert result.languages.get("Python", 0) == 1
