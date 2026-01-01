"""
Tests for configuration management
"""

import pytest
import os
from pathlib import Path
from ping_monitor.config import Config


def test_config_defaults():
    """Test default configuration values"""
    config = Config()

    assert config.site_name == "default"
    assert config.dd_site == "datadoghq.com"
    assert config.ping_interval == 60
    assert config.ping_count == 3
    assert config.ping_timeout == 2
    assert config.max_workers == 20


def test_config_has_rails_api():
    """Test has_rails_api property"""
    # Without configuration
    config1 = Config()
    assert config1.has_rails_api is False

    # With only URL
    config2 = Config(rails_api_url="https://api.example.com")
    assert config2.has_rails_api is False

    # With both URL and secret
    config3 = Config(rails_api_url="https://api.example.com", site_secret="test-secret")
    assert config3.has_rails_api is True


def test_config_has_datadog():
    """Test has_datadog property"""
    config1 = Config()
    assert config1.has_datadog is False

    config2 = Config(dd_api_key="test-dd-key")
    assert config2.has_datadog is True


def test_config_validate_no_outputs():
    """Test validation fails without any outputs"""
    config = Config()

    with pytest.raises(ValueError, match="At least one output must be configured"):
        config.validate()


def test_config_validate_datadog_only():
    """Test validation passes with Datadog only"""
    config = Config(dd_api_key="test-dd-key")

    # Should not raise
    config.validate()


def test_config_validate_rails_only():
    """Test validation passes with Rails API only"""
    config = Config(rails_api_url="https://api.example.com", site_secret="test-secret")

    # Should not raise
    config.validate()


def test_config_validate_invalid_interval():
    """Test validation fails with invalid ping interval"""
    config = Config(dd_api_key="test", ping_interval=5)

    with pytest.raises(ValueError, match="PING_INTERVAL must be at least 10 seconds"):
        config.validate()


def test_config_validate_invalid_count():
    """Test validation fails with invalid ping count"""
    config = Config(dd_api_key="test", ping_count=0)

    with pytest.raises(ValueError, match="PING_COUNT must be at least 1"):
        config.validate()


def test_config_from_env(monkeypatch):
    """Test loading configuration from environment variables"""
    monkeypatch.setenv("SITE_NAME", "test-site")
    monkeypatch.setenv("DD_API_KEY", "test-dd-key")
    monkeypatch.setenv("DD_SITE", "datadoghq.eu")
    monkeypatch.setenv("PING_INTERVAL", "120")
    monkeypatch.setenv("PING_COUNT", "5")

    config = Config.from_env()

    assert config.site_name == "test-site"
    assert config.dd_api_key == "test-dd-key"
    assert config.dd_site == "datadoghq.eu"
    assert config.ping_interval == 120
    assert config.ping_count == 5
