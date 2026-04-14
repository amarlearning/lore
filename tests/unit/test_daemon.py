from fastapi.testclient import TestClient
from unittest.mock import patch
from lore_daemon.server import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("lore_daemon.hooks.prompt.handle")
def test_hook_prompt(mock_handle):
    mock_handle.return_value = {"context": "injected"}
    payload = {"prompt": "test prompt", "cwd": "/tmp"}
    response = client.post("/hooks/prompt", json=payload)
    assert response.status_code == 200
    assert response.json() == {"context": "injected"}
    mock_handle.assert_called_once_with(payload)


@patch("lore_daemon.hooks.tool.handle")
def test_hook_tool(mock_handle):
    payload = {"tool": "Write", "file": "app.py"}
    response = client.post("/hooks/tool", json=payload)
    assert response.status_code == 200
    assert response.json() == {}
    mock_handle.assert_called_once_with(payload)


@patch("lore_daemon.hooks.compact.handle")
def test_hook_compact(mock_handle):
    payload = {"reasoning": "some reasoning"}
    response = client.post("/hooks/compact", json=payload)
    assert response.status_code == 200
    assert response.json() == {}
    mock_handle.assert_called_once_with(payload)


@patch("lore_daemon.hooks.stop.handle")
def test_hook_stop(mock_handle):
    payload = {"status": "finished"}
    response = client.post("/hooks/stop", json=payload)
    assert response.status_code == 200
    assert response.json() == {}
    mock_handle.assert_called_once_with(payload)


@patch("lore_daemon.hooks.pre_tool.handle")
def test_hook_pre_tool(mock_handle):
    mock_handle.return_value = {"additionalContext": "some history"}
    payload = {"tool": "Edit", "file": "main.py"}
    response = client.post("/hooks/pre-tool", json=payload)
    assert response.status_code == 200
    assert response.json() == {"additionalContext": "some history"}
    mock_handle.assert_called_once_with(payload)
