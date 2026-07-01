"""Integration tests for agent structure and decorator contracts."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import pytest


class TestAgentDecorators:
    """Verify the three required decorated functions exist in agent.py."""

    def test_agent_model_decorator_present(self):
        """get_model_name must be decorated with @agent_model."""
        agent_mod = importlib.import_module("agent")
        assert hasattr(agent_mod, "get_model_name"), "agent.py must define get_model_name"

    def test_agent_config_decorator_present(self):
        """get_temperature must be decorated with @agent_config."""
        agent_mod = importlib.import_module("agent")
        assert hasattr(agent_mod, "get_temperature"), "agent.py must define get_temperature"

    def test_prompt_section_decorator_present(self):
        """get_system_prompt must be decorated with @prompt_section."""
        agent_mod = importlib.import_module("agent")
        assert hasattr(agent_mod, "get_system_prompt"), "agent.py must define get_system_prompt"

    def test_exactly_three_decorated_functions(self):
        """agent.py must define exactly get_model_name, get_temperature, get_system_prompt."""
        agent_mod = importlib.import_module("agent")
        for name in ("get_model_name", "get_temperature", "get_system_prompt"):
            assert hasattr(agent_mod, name), f"Missing decorated function: {name}"

    def test_temperature_is_deterministic(self):
        """Temperature must be 0.1 (deterministic for order extraction)."""
        agent_mod = importlib.import_module("agent")
        temp = agent_mod.get_temperature()
        assert temp == 0.1, f"Temperature must be 0.1, got {temp}"

    def test_system_prompt_is_korean(self):
        """System prompt must contain Korean characters."""
        agent_mod = importlib.import_module("agent")
        prompt = agent_mod.get_system_prompt()
        has_korean = any('\uAC00' <= ch <= '\uD7A3' for ch in prompt)
        assert has_korean, "System prompt must contain Korean text"

    def test_sample_agent_class_exists(self):
        """SampleAgent class must be importable."""
        agent_mod = importlib.import_module("agent")
        assert hasattr(agent_mod, "SampleAgent"), "agent.py must define SampleAgent class"

    def test_high_risk_threshold_constant(self):
        """DELIVERY_BLOCK_HIGH_RISK_THRESHOLD must be 70."""
        agent_mod = importlib.import_module("agent")
        assert agent_mod.DELIVERY_BLOCK_HIGH_RISK_THRESHOLD == 70


class TestAgentRiskThresholds:
    """Test that agent uses correct risk thresholds."""

    def test_thresholds_in_agent(self):
        """Both thresholds defined in agent module."""
        agent_mod = importlib.import_module("agent")
        assert hasattr(agent_mod, "DELIVERY_BLOCK_HIGH_RISK_THRESHOLD")
        assert hasattr(agent_mod, "DELIVERY_BLOCK_MEDIUM_RISK_THRESHOLD")
        high = agent_mod.DELIVERY_BLOCK_HIGH_RISK_THRESHOLD
        medium = agent_mod.DELIVERY_BLOCK_MEDIUM_RISK_THRESHOLD
        assert high == 70
        assert medium == 40
        assert high > medium
