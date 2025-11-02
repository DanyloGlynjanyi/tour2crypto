from __future__ import annotations

import importlib
from pathlib import Path


def test_config_reads_env_and_overrides(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("FEATURE_ENABLED=true\nNUMBER=7\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    config = importlib.import_module("t2c_core.config")
    importlib.reload(config)

    assert config.get("FEATURE_ENABLED") == "true"
    assert config.get_bool("FEATURE_ENABLED") is True
    assert config.get_int("NUMBER", 0) == 7

    monkeypatch.setenv("FEATURE_ENABLED", "false")
    assert config.get_bool("FEATURE_ENABLED", True) is False

    monkeypatch.delenv("FEATURE_ENABLED")
    assert config.get("MISSING", "fallback") == "fallback"
