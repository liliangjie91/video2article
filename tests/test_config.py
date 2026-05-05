"""Tests for config.py — config loading (no mock, reads real config.ini)."""

import pytest
from config import get_config, get_client_config, model_name


class TestGetConfig:
    def test_returns_configparser(self):
        cfg = get_config()
        assert cfg.sections()  # should have at least the default sections

    def test_has_fast_section(self):
        cfg = get_config()
        assert "fast" in cfg

    def test_has_best_section(self):
        cfg = get_config()
        assert "best" in cfg


class TestGetClientConfig:
    def test_fast_has_model_and_provider(self):
        cfg = get_client_config("fast")
        assert "model" in cfg
        assert "provider" in cfg

    def test_best_has_model_and_provider(self):
        cfg = get_client_config("best")
        assert "model" in cfg
        assert "provider" in cfg

    def test_may_have_fallback(self):
        cfg = get_client_config("fast")
        # fallback is optional, just verify it doesn't crash
        assert "model" in cfg


class TestModelName:
    @pytest.mark.parametrize(
        ("input_str", "expected"),
        [
            ("deepseek/deepseek-v4-flash", "deepseek-v4-flash"),
            ("openai/gpt-4o", "gpt-4o"),
            ("naked-model", "naked-model"),
        ],
    )
    def test_model_name_extraction(self, input_str, expected):
        assert model_name(input_str) == expected
