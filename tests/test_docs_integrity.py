"""
Tests for documentation integrity, screenshot asset presence, and GitHub specification compliance.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_readme_exists_and_within_github_size_budget():
    """Verifies README.md exists and is well under GitHub's 500 KiB truncation limit."""
    readme_path = REPO_ROOT / "README.md"
    assert readme_path.is_file(), "README.md must exist in repository root"
    size_bytes = readme_path.stat().st_size
    assert size_bytes < 500 * 1024, f"README.md exceeds GitHub 500 KiB limit: {size_bytes} bytes"


def test_readme_screenshots_exist():
    """Ensures all screenshots referenced in README.md exist on disk and are non-empty."""
    readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    # Match <img src="docs/assets/screenshots/...">
    html_img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', readme_content)
    # Match markdown ![alt](path)
    md_img_matches = re.findall(r'!\[.*?\]\((.*?)\)', readme_content)

    all_images = html_img_matches + md_img_matches
    # Filter local asset paths
    local_images = [img for img in all_images if not img.startswith("http")]

    assert len(local_images) >= 3, f"Expected at least 3 embedded screenshots, found: {local_images}"

    for img_rel in local_images:
        img_path = (REPO_ROOT / img_rel).resolve()
        assert img_path.is_file(), f"Screenshot referenced in README not found on disk: {img_rel}"
        assert img_path.stat().st_size > 1000, f"Screenshot appears empty or truncated: {img_rel}"


def test_readme_relative_links_valid():
    """Ensures relative links in README.md point to valid existing files."""
    readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    # Find [link text](relative/path)
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', readme_content)
    for text, target in links:
        # Ignore external URLs, anchors (#), and badge links
        if target.startswith("http") or target.startswith("#") or target == "":
            continue

        target_clean = target.split("#")[0]
        target_path = (REPO_ROOT / target_clean).resolve()
        assert target_path.exists(), f"Broken relative link in README: [{text}]({target})"


def test_screenshot_generation_script_exists():
    """Verifies that the automated screenshot script is present in scripts/."""
    script_path = REPO_ROOT / "scripts" / "capture_screenshots.py"
    assert script_path.is_file(), "scripts/capture_screenshots.py must exist"


def test_project_level_skills_exist():
    """Verifies that viral-readme, diagrams-as-code, and maintaining-agents-md skills exist."""
    skill_readme = REPO_ROOT / ".agents" / "skills" / "viral-readme" / "SKILL.md"
    assert skill_readme.is_file(), "Project-level skill .agents/skills/viral-readme/SKILL.md must exist"

    skill_diagrams = REPO_ROOT / ".agents" / "skills" / "diagrams-as-code" / "SKILL.md"
    assert skill_diagrams.is_file(), "Project-level skill .agents/skills/diagrams-as-code/SKILL.md must exist"

    skill_maintaining = REPO_ROOT / ".agents" / "skills" / "maintaining-agents-md" / "SKILL.md"
    assert skill_maintaining.is_file(), "Project-level skill .agents/skills/maintaining-agents-md/SKILL.md must exist"


def test_architecture_diagram_and_generator_exist():
    """Verifies that architecture.svg and its generation script exist and are valid."""
    script_path = REPO_ROOT / "scripts" / "generate_architecture_diagram.py"
    assert script_path.is_file(), "scripts/generate_architecture_diagram.py must exist"

    svg_path = REPO_ROOT / "docs" / "assets" / "diagrams" / "architecture.svg"
    assert svg_path.is_file(), "docs/assets/diagrams/architecture.svg must exist"
    assert svg_path.stat().st_size > 5000, "architecture.svg appears truncated"


def test_agent_readiness_and_progressive_disclosure():
    """
    Verifies that the package is AI-agent-ready according to progressive disclosure principles:
    - Root AGENTS.md exists, stays within instruction budget (< 15KB).
    - CLAUDE.md and agents.md symlinks exist and resolve to AGENTS.md.
    - Progressive disclosure subdocs exist (ARCHITECTURE.md, PLUGINS.md, TESTING.md).
    """
    agents_path = REPO_ROOT / "AGENTS.md"
    assert agents_path.is_file(), "AGENTS.md must exist in repo root"
    assert agents_path.stat().st_size < 15 * 1024, "AGENTS.md exceeds instruction budget limit"

    # Verify symlinks
    claude_path = REPO_ROOT / "CLAUDE.md"
    assert claude_path.exists(), "CLAUDE.md symlink must exist"
    assert claude_path.resolve() == agents_path.resolve(), "CLAUDE.md must resolve to AGENTS.md"

    agents_lower = REPO_ROOT / "agents.md"
    assert agents_lower.exists(), "agents.md symlink must exist"
    assert agents_lower.resolve() == agents_path.resolve(), "agents.md must resolve to AGENTS.md"

    # Verify progressive disclosure subdocs
    for subdoc in ["docs/ARCHITECTURE.md", "docs/PLUGINS.md", "docs/TESTING.md"]:
        subdoc_path = REPO_ROOT / subdoc
        assert subdoc_path.is_file(), f"Progressive disclosure document {subdoc} must exist"
        assert subdoc_path.stat().st_size > 500, f"{subdoc} appears too sparse or empty"


def test_agent_guard_behavior():
    """
    Verifies that scripts/agent_guard.py exists and correctly enforces guardrails.
    """
    import subprocess
    guard_path = REPO_ROOT / "scripts" / "agent_guard.py"
    assert guard_path.is_file(), "scripts/agent_guard.py must exist"

    # Test dangerous git push blocked (exit code 2)
    res_push = subprocess.run([sys.executable, str(guard_path), "git push origin main"], capture_output=True)
    assert res_push.returncode == 2, "Dangerous git push was not blocked by agent_guard"
    assert b"GUARDRAIL BLOCKED" in res_push.stderr

    # Test dangerous git reset blocked (exit code 2)
    res_reset = subprocess.run([sys.executable, str(guard_path), "git reset --hard HEAD~1"], capture_output=True)
    assert res_reset.returncode == 2, "Dangerous git reset was not blocked by agent_guard"

    # Test safe git status allowed (exit code 0)
    res_safe = subprocess.run([sys.executable, str(guard_path), "git status"], capture_output=True)
    assert res_safe.returncode == 0, "Safe command was incorrectly blocked by agent_guard"

