from importlib import import_module
from pathlib import Path

REQUIRED_MODULES = [
    "multimodal_bias",
    "multimodal_bias.cli",
    "multimodal_bias.config",
    "multimodal_bias.schemas",
    "multimodal_bias.exceptions",
    "multimodal_bias.data_loader",
    "multimodal_bias.image_io",
    "multimodal_bias.parsing",
    "multimodal_bias.reasoner",
    "multimodal_bias.verifier",
    "multimodal_bias.arbitration",
    "multimodal_bias.validation",
    "multimodal_bias.compliance",
    "multimodal_bias.submission",
    "multimodal_bias.run_logging",
    "multimodal_bias.run_comparison",
    "multimodal_bias.prompting",
    "multimodal_bias.prompting.templates",
    "multimodal_bias.prompting.guards",
    "multimodal_bias.models",
    "multimodal_bias.models.adapter",
    "multimodal_bias.models.hf_vlm",
    "multimodal_bias.models.minicpm_v",
    "multimodal_bias.models.dummy",
]

REQUIRED_PATHS = [
    "configs/models",
    "configs/prompts",
    "data/raw/open",
    "data/processed",
    "models/snapshots",
    "runs",
    "submissions",
    "tests/fixtures",
    "src/multimodal_bias",
]

SCAFFOLD_PLACEHOLDER_DIRS = [
    Path("data/raw/open"),
    Path("data/processed"),
    Path("models/snapshots"),
    Path("runs"),
    Path("submissions"),
    Path("tests/fixtures"),
]

EXPECTED_GITIGNORE_RULES = {
    ".venv/",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".ruff_cache/",
    "data/raw/open/*",
    "!data/raw/open/.gitkeep",
    "data/processed/*",
    "!data/processed/.gitkeep",
    "models/snapshots/*",
    "!models/snapshots/.gitkeep",
    "runs/*",
    "!runs/.gitkeep",
    "submissions/*",
    "!submissions/.gitkeep",
}


def test_required_package_modules_import() -> None:
    for module_name in REQUIRED_MODULES:
        import_module(module_name)


def test_project_python_runtime_is_pinned_to_310() -> None:
    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.10"
    assert 'requires-python = ">=3.10,<3.11"' in Path("pyproject.toml").read_text(encoding="utf-8")


def test_required_project_directories_exist() -> None:
    for relative_path in REQUIRED_PATHS:
        assert Path(relative_path).is_dir()


def test_generated_cache_and_artifact_outputs_are_ignored() -> None:
    gitignore_rules = set(Path(".gitignore").read_text(encoding="utf-8").splitlines())

    missing_rules = sorted(EXPECTED_GITIGNORE_RULES - gitignore_rules)

    assert missing_rules == []


def test_source_and_test_trees_do_not_contain_cache_artifacts() -> None:
    cache_artifacts = []
    for root in (Path("src"), Path("tests")):
        cache_artifacts.extend(
            path
            for path in root.rglob("*")
            if path.name in {"__pycache__", ".pytest_cache", ".ruff_cache"}
            or path.suffix in {".pyc", ".pyo"}
        )

    assert [path.as_posix() for path in sorted(cache_artifacts)] == []


def test_scaffold_artifact_directories_only_contain_gitkeep() -> None:
    for directory in SCAFFOLD_PLACEHOLDER_DIRS:
        gitkeep_path = directory / ".gitkeep"

        assert gitkeep_path.is_file()
