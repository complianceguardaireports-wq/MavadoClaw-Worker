"""
Tests for MavadoClaw Worker
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config_loads():
    from app import load_config
    config = load_config()
    assert isinstance(config, dict)


def test_plugin_dir_exists():
    from pathlib import Path
    plugin_dir = Path(__file__).parent.parent / "plugins"
    assert plugin_dir.is_dir()


def test_ai_infrastructure_import():
    from plugins.ai_infrastructure import AutonomousAIInfrastructure, AIInfrastructureConfig
    config = AIInfrastructureConfig()
    infra = AutonomousAIInfrastructure(config)
    assert infra is not None
    assert infra.config.primary_provider == "omniroute"


def test_omniroute_client_import():
    from plugins.omniroute_plugin import OmniRouteClient, OmniRouteConfig
    config = OmniRouteConfig()
    client = OmniRouteClient(config)
    assert client is not None
    assert client.config.base_url == "http://omniroute:3000"


def test_ninerouter_client_import():
    from plugins.ninerouter_plugin import NineRouterFailoverManager, NineRouterClient
    manager = NineRouterFailoverManager()
    assert manager is not None
    assert manager.stats["primary"] == 0


def test_openhands_team_import():
    from plugins.openhands_team import OpenHandsTeam
    team = OpenHandsTeam()
    assert team is not None
    assert team.stats["tasks_assigned"] == 0


def test_cloudflare_edge_import():
    from plugins.cloudflare_edge import CloudflareEdgeClient, CloudflareConfig
    config = CloudflareConfig()
    client = CloudflareEdgeClient(config)
    assert client is not None


def test_hf_spaces_import():
    from plugins.hf_spaces import HuggingFaceClient, HuggingFaceConfig
    config = HuggingFaceConfig()
    client = HuggingFaceClient(config)
    assert client is not None


def test_lightning_import():
    from plugins.lightning_ai import LightningClient, LightningConfig
    config = LightningConfig()
    client = LightningClient(config)
    assert client is not None


def test_config_template_valid():
    from pathlib import Path
    template_path = Path(__file__).parent.parent / "config.json.template"
    assert template_path.exists()
    with open(template_path, "r") as f:
        config = json.load(f)
    assert "model" in config
    assert "plugin_config" in config
    assert "omniroute" in config["plugin_config"]
    assert "ninerouter" in config["plugin_config"]


def test_supervisor_script_exists():
    from pathlib import Path
    script = Path(__file__).parent.parent / "supervisor.sh"
    assert script.exists()


def test_dockerfile_exists():
    from pathlib import Path
    dockerfile = Path(__file__).parent.parent / "Dockerfile"
    assert dockerfile.exists()


def test_docker_compose_exists():
    from pathlib import Path
    compose = Path(__file__).parent.parent / "docker-compose.local.yml"
    assert compose.exists()


def test_cloudflare_worker_exists():
    from pathlib import Path
    worker = Path(__file__).parent.parent / "cloudflare-worker" / "src" / "index.js"
    assert worker.exists()


def test_hf_space_exists():
    from pathlib import Path
    space = Path(__file__).parent.parent / "hf-space" / "app.py"
    assert space.exists()


def test_free_api_providers_documented():
    """Verify all free API providers are documented in config."""
    from pathlib import Path
    template = Path(__file__).parent.parent / "config.json.template"
    with open(template, "r") as f:
        config = json.load(f)
    plugin_config = config.get("plugin_config", {})
    assert "omniroute" in plugin_config
    assert "ninerouter" in plugin_config
    assert "cloudflare_edge" in plugin_config
    assert "hf_spaces" in plugin_config
    assert "lightning_ai" in plugin_config


def test_pandastack_config_valid():
    from pathlib import Path
    toml_path = Path(__file__).parent.parent / "pandastack.toml"
    assert toml_path.exists()
    content = toml_path.read_text()
    assert "omniroute" in content
    assert "9router" in content
    assert "openhands" in content
    assert "mavado" in content
