import pytest
from pathlib import Path

@pytest.fixture
def test_playbook_dir():
    return Path("tests/fixtures/playbooks")

@pytest.fixture(autouse=True)
def setup_test_env(tmp_path):
    """Setup test environment with temporary directories"""
    # Create test playbook directory if it doesn't exist
    playbook_dir = Path("tests/fixtures/playbooks")
    playbook_dir.mkdir(parents=True, exist_ok=True)

    # Create a test playbook file
    test_playbook = playbook_dir / "test.yml"
    if not test_playbook.exists():
        test_playbook.write_text("""
---
- hosts: all
  tasks:
    - name: Test task
      debug:
        msg: "Test playbook"
""")
