"""Tests for Agent Registry module."""

import pytest
from unittest.mock import patch, MagicMock


class TestAgentRegistry:
    """Tests for AgentRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing."""
        from aiops.agents.registry import AgentRegistry
        return AgentRegistry()

    def test_register_agent(self, registry):
        """Test registering a new agent."""
        registry.register(
            name="test_agent",
            module_path="test.module",
            class_name="TestAgent",
            description="A test agent",
            category="testing",
            tags=["test", "mock"],
        )

        assert registry.is_registered("test_agent")
        assert not registry.is_loaded("test_agent")

    def test_list_agents(self, registry):
        """Test listing all agents."""
        agents = registry.list_agents()

        # Should have built-in agents
        assert len(agents) > 0

        # Check that code_reviewer is registered
        agent_names = [a.name for a in agents]
        assert "code_reviewer" in agent_names

    def test_list_agents_by_category(self, registry):
        """Test filtering agents by category."""
        security_agents = registry.list_agents(category="security")

        # All should be security category
        for agent in security_agents:
            assert agent.category == "security"

        # Should include security scanner
        agent_names = [a.name for a in security_agents]
        assert "security_scanner" in agent_names

    def test_list_agents_by_tags(self, registry):
        """Test filtering agents by tags."""
        code_agents = registry.list_agents(tags=["code"])

        # All should have 'code' tag
        for agent in code_agents:
            assert "code" in agent.tags

    def test_list_categories(self, registry):
        """Test getting all categories."""
        categories = registry.list_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "code_quality" in categories
        assert "security" in categories
        assert "monitoring" in categories

    def test_get_stats(self, registry):
        """Test getting registry statistics."""
        stats = registry.get_stats()

        assert "registered" in stats
        assert "loaded" in stats
        assert "cached_instances" in stats
        assert "categories" in stats

        assert stats["registered"] > 0
        assert stats["loaded"] == 0  # Nothing loaded yet
        assert stats["cached_instances"] == 0

    def test_unload_agent(self, registry):
        """Test unloading an agent."""
        # First, we need to simulate a loaded agent
        registry._classes["test"] = MagicMock()
        registry._instances["test"] = MagicMock()
        registry._registry["test"] = MagicMock()
        registry._registry["test"].is_loaded = True

        result = registry.unload("test")

        assert result is True
        assert "test" not in registry._classes
        assert "test" not in registry._instances

    def test_clear_cache(self, registry):
        """Test clearing instance cache."""
        # Add some cached instances
        registry._instances["agent1"] = MagicMock()
        registry._instances["agent2"] = MagicMock()

        registry.clear_cache()

        assert len(registry._instances) == 0


class TestAgentLoading:
    """Tests for agent lazy loading."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing."""
        from aiops.agents.registry import AgentRegistry
        return AgentRegistry()

    def test_load_class(self, registry):
        """Test loading an agent class."""
        # This test actually imports the module
        agent_class = registry.get_class("code_reviewer")

        assert agent_class is not None
        assert registry.is_loaded("code_reviewer")

    def test_load_nonexistent_agent(self, registry):
        """Test loading a non-existent agent."""
        with pytest.raises(KeyError):
            registry.get_class("nonexistent_agent")

    def test_get_sync(self, registry):
        """Test synchronous agent retrieval."""
        with patch.object(registry, '_load_class') as mock_load:
            mock_class = MagicMock()
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            mock_load.return_value = mock_class

            agent = registry.get_sync("test_agent")

            assert agent == mock_instance
            mock_load.assert_called_once_with("test_agent")

    def test_get_sync_cached(self, registry):
        """Test that get_sync returns cached instances."""
        cached_agent = MagicMock()
        registry._instances["cached_agent"] = cached_agent

        agent = registry.get_sync("cached_agent", use_cache=True)

        assert agent == cached_agent

    def test_get_sync_no_cache(self, registry):
        """Test get_sync with caching disabled."""
        with patch.object(registry, '_load_class') as mock_load:
            mock_class = MagicMock()
            mock_load.return_value = mock_class

            # Add a cached instance
            cached_agent = MagicMock()
            registry._instances["test_agent"] = cached_agent

            # Get with cache disabled should create new instance
            agent = registry.get_sync("test_agent", use_cache=False)

            assert agent != cached_agent
            mock_load.assert_called_once()


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_agent(self):
        """Test get_agent convenience function."""
        from aiops.agents.registry import get_agent, agent_registry

        with patch.object(agent_registry, 'get_sync') as mock_get:
            mock_agent = MagicMock()
            mock_get.return_value = mock_agent

            result = get_agent("test_agent", param="value")

            mock_get.assert_called_once_with("test_agent", param="value")
            assert result == mock_agent

    def test_list_agents(self):
        """Test list_agents convenience function."""
        from aiops.agents.registry import list_agents

        agents = list_agents()

        assert isinstance(agents, list)
        assert len(agents) > 0


class TestAgentInfo:
    """Tests for AgentInfo dataclass."""

    def test_agent_info_creation(self):
        """Test creating AgentInfo."""
        from aiops.agents.registry import AgentInfo

        info = AgentInfo(
            name="test",
            module_path="test.module",
            class_name="TestAgent",
            description="Test description",
            category="testing",
            tags=["test"],
        )

        assert info.name == "test"
        assert info.module_path == "test.module"
        assert info.class_name == "TestAgent"
        assert info.is_loaded is False

    def test_agent_info_defaults(self):
        """Test AgentInfo default values."""
        from aiops.agents.registry import AgentInfo

        info = AgentInfo(
            name="test",
            module_path="test.module",
            class_name="TestAgent",
        )

        assert info.description == ""
        assert info.category == "general"
        assert info.tags == []
        assert info.is_loaded is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
