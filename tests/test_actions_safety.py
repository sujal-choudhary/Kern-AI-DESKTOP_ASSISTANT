import os

from core.actions import execute_task, validate_path
from config import BASE_DIR


def test_validate_path_blocks_traversal():
    try:
        validate_path("..")
        assert False, "Expected ValueError for traversal path"
    except ValueError:
        assert True


def test_execute_unknown_task():
    result = execute_task("not_real_task", {})
    assert result["ok"] is False
    assert "Unknown task" in result["message"]


def test_create_and_delete_file_roundtrip():
    target_dir = os.path.join(BASE_DIR, "tests_tmp")
    os.makedirs(target_dir, exist_ok=True)
    relative = "tests_tmp"
    filename = "tmp_test_file.txt"
    create = execute_task("create_file", {"path": relative, "name": filename, "content": "hello"})
    assert create["ok"] is True
    delete = execute_task("delete_file", {"path": f"{relative}\\{filename}"})
    assert delete["ok"] is True
