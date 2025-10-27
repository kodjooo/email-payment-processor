import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT_DIR / "email-processor"
SRC_DIR = PROJECT_DIR / "src"

for path in (SRC_DIR, PROJECT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import config.config as config_module
import webhook_sender as webhook_sender_module


def reload_modules():
    global config_module, webhook_sender_module
    config_module = importlib.reload(config_module)
    webhook_sender_module = importlib.reload(webhook_sender_module)
    return config_module, webhook_sender_module


def test_webhook_headers_without_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("WEBHOOK_TOKEN", raising=False)
    monkeypatch.delenv("WEBHOOK_BASIC_USERNAME", raising=False)
    monkeypatch.delenv("WEBHOOK_BASIC_PASSWORD", raising=False)

    config_mod, _ = reload_modules()
    webhook_cfg = config_mod.AppConfig().webhook

    assert "Authorization" not in webhook_cfg.webhook_headers


def test_webhook_headers_with_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WEBHOOK_TOKEN", "secret-token")
    monkeypatch.delenv("WEBHOOK_BASIC_USERNAME", raising=False)
    monkeypatch.delenv("WEBHOOK_BASIC_PASSWORD", raising=False)

    config_mod, _ = reload_modules()
    webhook_cfg = config_mod.AppConfig().webhook

    assert webhook_cfg.webhook_headers.get("Authorization") == "Bearer secret-token"


def test_webhook_basic_auth(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("WEBHOOK_TOKEN", raising=False)
    monkeypatch.setenv("WEBHOOK_BASIC_USERNAME", "user")
    monkeypatch.setenv("WEBHOOK_BASIC_PASSWORD", "pass")

    _, sender_mod = reload_modules()
    sender = sender_mod.WebhookSender()

    assert sender.session.auth == ("user", "pass")
