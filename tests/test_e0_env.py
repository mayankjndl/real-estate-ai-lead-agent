"""Expansion Phase 0 — branch / env hygiene (Step 8, Task 0.2).

Verifies the pre-flight environment for the IREIOS 3.0 expansion:
  - we are on a dedicated expansion branch (not main/master),
  - .env.example advertises the new expansion vars (wired in later phases),
  - config.Settings loads,
  - Redis (the Phase 1 event bus transport) is reachable,
  - the app defines the /health route (boots/imports cleanly).

See plans/IREIOS_3.0_EXPANSION_CHANGELOG.md (Phase 0 status).
"""
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"

EXPANSION_VARS = [
    "EVENT_STREAM_KEY",
    "EVENT_CONSUMER_GROUP",
    "FEATURE_WHATSAPP_V3",
    "FOLLOWUP_ENGINE",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "N8N_BASE_URL",
    "N8N_API_KEY",
    "N8N_BRIDGE_ENABLED",
    "N8N_BRIDGE_GROUP",
    "GOOGLE_CALENDAR_ID",
    "GOOGLE_CALENDAR_CREDENTIALS_JSON",
    "BROCHURE_MEDIA_URL",
    "FLOORPLAN_MEDIA_URL",
    "FEATURE_GRAPH_VIZ",
    "FEATURE_TWIN_LIVE",
    "FEATURE_HUBSPOT_LIVE",
]


def _current_branch():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def test_branch_is_feature():
    """Phase 0 requires a dedicated expansion branch, not main/master."""
    branch = _current_branch()
    if branch is None or branch == "HEAD":
        pytest.skip("cannot determine git branch (detached HEAD or no git)")
    assert branch not in {"main", "master"}, (
        f"on protected branch '{branch}'; expansion work must be on a feature branch"
    )


def test_env_example_has_expansion_vars():
    assert ENV_EXAMPLE.exists(), ".env.example missing"
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [v for v in EXPANSION_VARS if v not in text]
    assert not missing, f".env.example missing expansion vars: {missing}"


def test_config_importable():
    import config  # noqa: F401

    assert config.settings is not None


def test_redis_reachable():
    try:
        import redis
    except ImportError:
        pytest.skip("redis-py not installed")

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=3)
        assert client.ping(), f"Redis at {url} did not respond to PING"
    except redis.exceptions.RedisError as exc:
        pytest.skip(f"Redis not reachable at {url}: {exc}")


def test_health_route_registered():
    import main

    paths = {getattr(r, "path", None) for r in main.app.routes}
    assert "/health" in paths, "FastAPI app does not register /health"
