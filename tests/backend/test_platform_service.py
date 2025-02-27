import os
import tempfile
import pytest
import asyncio
from pathlib import Path

from volttron_installer.backend.models import AgentDefinition, PlatformConfig, PlatformDefinition
from volttron_installer.backend.services.platform_service import PlatformService

@pytest.fixture
def temp_platform_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def platform_service(temp_platform_dir):
    return PlatformService(platform_dir=temp_platform_dir)

@pytest.mark.asyncio
async def test_create_platform(platform_service):
    platform_config = PlatformConfig(instance_name="test_instance", vip_address="tcp://127.0.0.1:22916")
    platform_definition = PlatformDefinition(config=platform_config)
    await platform_service.create_platform(platform_definition)
    assert await platform_service.get_platform("test_instance") is not None

@pytest.mark.asyncio
async def test_get_platform(platform_service):
    platform_config = PlatformConfig(instance_name="test_instance", vip_address="tcp://127.0.0.1:22916")
    platform_definition = PlatformDefinition(config=platform_config)
    await platform_service.create_platform(platform_definition)
    retrieved_platform = await platform_service.get_platform("test_instance")
    assert retrieved_platform is not None
    assert retrieved_platform.config.instance_name == "test_instance"

@pytest.mark.asyncio
async def test_update_platform(platform_service):
    platform_config = PlatformConfig(instance_name="test_instance", vip_address="tcp://127.0.0.1:22916")
    platform_definition = PlatformDefinition(config=platform_config)
    await platform_service.create_platform(platform_definition)
    updated_config = PlatformConfig(instance_name="test_instance", vip_address="tcp://127.0.0.1:22917")
    updated_definition = PlatformDefinition(config=updated_config)
    await platform_service.update_platform("test_instance", updated_definition)
    retrieved_platform = await platform_service.get_platform("test_instance")
    assert retrieved_platform.config.vip_address == "tcp://127.0.0.1:22917"

@pytest.mark.asyncio
async def test_delete_platform(platform_service):
    platform_config = PlatformConfig(instance_name="test_instance", vip_address="tcp://127.0.0.1:22916")
    platform_definition = PlatformDefinition(config=platform_config)
    await platform_service.create_platform(platform_definition)
    await platform_service.delete_platform("test_instance")
    assert await platform_service.get_platform("test_instance") is None

@pytest.mark.asyncio
async def test_list_platform_instance_names(platform_service):
    platform_config1 = PlatformConfig(instance_name="instance1", vip_address="tcp://127.0.0.1:22916")
    platform_definition1 = PlatformDefinition(config=platform_config1)
    await platform_service.create_platform(platform_definition1)
    platform_config2 = PlatformConfig(instance_name="instance2", vip_address="tcp://127.0.0.1:22917")
    platform_definition2 = PlatformDefinition(config=platform_config2)
    await platform_service.create_platform(platform_definition2)
    instance_names = await platform_service.get_platform_instance_names()
    assert "instance1" in instance_names
    assert "instance2" in instance_names

@pytest.mark.asyncio
async def test_create_agent_in_platform(platform_service):
    platform_config = PlatformConfig(instance_name="test_instance", vip_address="tcp://127.0.0.1:22916")
    platform_definition = PlatformDefinition(config=platform_config)
    await platform_service.create_platform(platform_definition)
    agent_definition = AgentDefinition(identity="test_agent", source="some_source")
    platform_definition.agents["test_agent"] = agent_definition
    await platform_service.update_platform("test_instance", platform_definition)
    retrieved_platform = await platform_service.get_platform("test_instance")
    assert "test_agent" in retrieved_platform.agents
    assert retrieved_platform.agents["test_agent"].identity == "test_agent"

@pytest.mark.asyncio
async def test_remove_agent_from_platform(platform_service):
    platform_config = PlatformConfig(instance_name="test_instance", vip_address="tcp://127.0.0.1:22916")
    platform_definition = PlatformDefinition(config=platform_config)
    await platform_service.create_platform(platform_definition)
    agent_definition = AgentDefinition(identity="test_agent", source="some_source")
    platform_definition.agents["test_agent"] = agent_definition
    await platform_service.update_platform("test_instance", platform_definition)
    platform_definition.agents.pop("test_agent")
    await platform_service.update_platform("test_instance", platform_definition)
    retrieved_platform = await platform_service.get_platform("test_instance")
    assert "test_agent" not in retrieved_platform.agents

@pytest.mark.asyncio
async def test_update_agent_in_platform(platform_service):
    platform_config = PlatformConfig(instance_name="test_instance", vip_address="tcp://127.0.0.1:22916")
    platform_definition = PlatformDefinition(config=platform_config)
    await platform_service.create_platform(platform_definition)
    agent_definition = AgentDefinition(identity="test_agent", source="some_source")
    platform_definition.agents["test_agent"] = agent_definition
    await platform_service.update_platform("test_instance", platform_definition)
    updated_agent_definition = AgentDefinition(identity="test_agent", source="updated_source")
    platform_definition.agents["test_agent"] = updated_agent_definition
    await platform_service.update_platform("test_instance", platform_definition)
    retrieved_platform = await platform_service.get_platform("test_instance")
    assert retrieved_platform.agents["test_agent"].source == "updated_source"
