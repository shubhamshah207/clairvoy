"""
Tests for documentation integrity, screenshot asset presence, and GitHub specification compliance.
"""

import re
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


def test_project_level_skill_exists():
    """Verifies that viral-readme skill exists at project level."""
    skill_path = REPO_ROOT / ".agents" / "skills" / "viral-readme" / "SKILL.md"
    assert skill_path.is_file(), "Project-level skill .agents/skills/viral-readme/SKILL.md must exist"
