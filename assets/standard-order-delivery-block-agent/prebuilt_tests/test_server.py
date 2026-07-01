"""Tests for agent server startup and A2A endpoints."""

import json
import urllib.error
import urllib.request

import pytest


@pytest.mark.server
class TestServerStartup:
    def test_server_starts(self, start_agent):
        assert start_agent["process"].poll() is None, "Server process should be running"
        assert start_agent["port"] > 0, "Server should have a valid port"


@pytest.mark.server
class TestA2AEndpoints:
    def test_agent_card_endpoint(self, start_agent):
        port = start_agent["port"]
        url = f"http://localhost:{port}/.well-known/agent.json"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                raw = resp.read().decode()
                status = resp.status
        except urllib.error.URLError as e:
            pytest.fail(f"Could not connect to server on port {port}: {e}")
        assert status == 200, f"Agent card endpoint returned status {status}"
        try:
            card_data = json.loads(raw)
        except ValueError as e:
            pytest.fail(f"Agent card endpoint returned invalid JSON: {e}\nResponse text: {raw[:200]}")
        assert "name" in card_data or "agentName" in card_data, (
            "Agent card should have a 'name' or 'agentName' field"
        )
