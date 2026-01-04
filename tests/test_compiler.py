
from pathlib import Path

from loomaa.cli import init as cli_init
from loomaa.cli import compile as cli_compile


def test_compile_model(tmp_path, monkeypatch):
	project_dir = tmp_path / "demo_project"
	monkeypatch.chdir(tmp_path)

	cli_init("demo_project")
	monkeypatch.chdir(project_dir)

	cli_compile()

	model_json = Path("compiled") / "example" / "model.json"
	model_tmdl = Path("compiled") / "example" / "example.SemanticModel" / "definition" / "model.tmdl"
	roles_dir = Path("compiled") / "example" / "example.SemanticModel" / "definition" / "roles"

	assert model_json.exists()
	assert model_tmdl.exists()
	assert roles_dir.exists()

	content = model_tmdl.read_text(encoding="utf-8")
	assert "ref table" in content
	assert "ref role" in content
