import pytest
from fastapi.testclient import TestClient
from click.testing import CliRunner

from nexus.api.main import app
from nexus.cli.main import cli

client = TestClient(app)

def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "nexus"}

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Nexus Agent Evaluation CLI" in result.output
