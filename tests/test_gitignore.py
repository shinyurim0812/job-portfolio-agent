"""Private material must be ignored by git; code must not be."""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def is_ignored(rel: str) -> bool:
    r = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT)
    return r.returncode == 0


@pytest.mark.parametrize("path", [
    "data/experiences.json",
    "data/jobs/job-001/jd.txt",
    "data/config.json",
    "output/job-001/portfolio-plugin.zip",
    "resume.pdf",
    "samples/cover.docx",
    ".claude/settings.local.json",
])
def test_private_paths_are_ignored(path):
    assert is_ignored(path), f"{path} would be committed"


@pytest.mark.parametrize("path", [
    "tools/check_analysis.py",
    "tests/test_gitignore.py",
    ".claude/skills/job-apply/SKILL.md",
    ".claude/agents/jd-analyzer.md",
    "samples/jd.txt",
    "README.md",
])
def test_code_paths_are_tracked(path):
    assert not is_ignored(path), f"{path} is ignored but should be committed"
