
from pathlib import Path

from loomaa.compiler import compile_model
from loomaa import cli


def test_compile_model(tmp_path, monkeypatch):
	project_dir = tmp_path / "demo_project"
	monkeypatch.chdir(tmp_path)

	cli.init("demo_project")
	monkeypatch.chdir(project_dir)

	compile_model()

	tmdl_path = Path("compiled") / "model.tmdl"
	json_path = Path("compiled") / "model.json"

	assert tmdl_path.exists()
	assert json_path.exists()

	content = tmdl_path.read_text(encoding="utf-8")
	assert "table Sales" in content
	assert "measure Total Sales" in content
