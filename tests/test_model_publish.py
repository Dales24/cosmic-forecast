"""Tests for app/model_publish.py and scripts/publish_model.py.

Nothing here touches the network: the Hugging Face client is stubbed. The
failure paths matter more than the happy one — this is the code that would
otherwise publish the wrong thing, or publish nothing while claiming success.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.model_publish import (
    CARD_FILENAME,
    MODEL_FILENAME,
    PUBLISHABLE_MODELS,
    TOKEN_ENV_VAR,
    build_model_card,
    get_model,
    model_artifact,
    publish_model,
    resolve_token,
)
from scripts.publish_model import main

_AT = datetime(2026, 8, 2, tzinfo=timezone.utc)


@pytest.fixture
def trained(tmp_path, monkeypatch):
    """A project root with a saved classifier, as training would leave it."""
    directory = tmp_path / PUBLISHABLE_MODELS["classifier"].directory
    directory.mkdir(parents=True)
    (directory / MODEL_FILENAME).write_bytes(b"fake weights")
    monkeypatch.setattr("app.paths.PROJECT_ROOT", tmp_path)
    return tmp_path


# ── Model registry ────────────────────────────────────────────────────────────


def test_every_registered_model_declares_its_caveats():
    """A model card without its limitations would misrepresent the model."""
    for model in PUBLISHABLE_MODELS.values():
        assert model.caveats, f"{model.key} has no caveats"
        assert model.task and model.summary


def test_unknown_model_lists_the_valid_choices():
    with pytest.raises(ValueError, match="classifier"):
        get_model("nope")


# ── Artifact resolution ───────────────────────────────────────────────────────


def test_missing_artifact_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError, match="No trained classifier model"):
        model_artifact(PUBLISHABLE_MODELS["classifier"], root=tmp_path)


def test_artifact_found_once_training_has_saved_one(trained):
    path = model_artifact(PUBLISHABLE_MODELS["classifier"], root=trained)
    assert path.is_file()
    assert path.name == MODEL_FILENAME


# ── Token handling ────────────────────────────────────────────────────────────


def test_token_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_from_env")
    assert resolve_token() == "hf_from_env"


def test_an_explicit_token_wins(monkeypatch):
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_from_env")
    assert resolve_token("hf_explicit") == "hf_explicit"


def test_missing_token_names_the_variable_to_set(monkeypatch):
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
    with pytest.raises(ValueError, match=TOKEN_ENV_VAR):
        resolve_token()


def test_blank_token_is_not_a_token(monkeypatch):
    monkeypatch.setenv(TOKEN_ENV_VAR, "   ")
    with pytest.raises(ValueError):
        resolve_token()


# ── Model card ────────────────────────────────────────────────────────────────


def test_card_carries_every_caveat():
    model = PUBLISHABLE_MODELS["classifier"]
    card = build_model_card(model, "daley30/cosmic-classifier", _AT)
    for caveat in model.caveats:
        assert caveat in card


def test_card_says_the_classifier_is_synthetic():
    """The single most misleading thing to omit."""
    card = build_model_card(PUBLISHABLE_MODELS["classifier"], "x/y", _AT)
    assert "synthetic" in card.lower()


def test_card_has_hugging_face_front_matter():
    card = build_model_card(PUBLISHABLE_MODELS["trajectory"], "x/y", _AT)
    assert card.startswith("---\n")
    assert "pipeline_tag: time-series-forecasting" in card


def test_card_usage_snippet_points_at_the_target_repo():
    card = build_model_card(PUBLISHABLE_MODELS["classifier"], "daley30/demo", _AT)
    assert 'hf_hub_download("daley30/demo"' in card


# ── Publishing ────────────────────────────────────────────────────────────────


def test_dry_run_uploads_nothing(trained, monkeypatch):
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_token")
    with patch("app.model_publish._hub_api") as hub:
        plan = publish_model(
            "classifier", "daley30/demo", root=trained, dry_run=True, now=_AT
        )
    hub.assert_not_called()
    assert plan.uploaded is False
    assert plan.card


def test_dry_run_needs_no_token(trained, monkeypatch):
    """You should be able to preview a publish before holding credentials."""
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
    plan = publish_model(
        "classifier", "daley30/demo", root=trained, dry_run=True, now=_AT
    )
    assert plan.uploaded is False


def test_publish_uploads_weights_and_card(trained, monkeypatch):
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_token")
    api = MagicMock()
    with patch("app.model_publish._hub_api", return_value=api):
        plan = publish_model("classifier", "daley30/demo", root=trained, now=_AT)

    assert plan.uploaded is True
    api.create_repo.assert_called_once()
    uploaded = {call.kwargs["path_in_repo"] for call in api.upload_file.call_args_list}
    assert uploaded == {MODEL_FILENAME, CARD_FILENAME}


def test_repos_are_private_unless_asked_otherwise(trained, monkeypatch):
    """Making a model public should be a deliberate act."""
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_token")
    api = MagicMock()
    with patch("app.model_publish._hub_api", return_value=api):
        publish_model("classifier", "daley30/demo", root=trained, now=_AT)
    assert api.create_repo.call_args.kwargs["private"] is True


def test_public_is_opt_in(trained, monkeypatch):
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_token")
    api = MagicMock()
    with patch("app.model_publish._hub_api", return_value=api):
        publish_model(
            "classifier", "daley30/demo", root=trained, private=False, now=_AT
        )
    assert api.create_repo.call_args.kwargs["private"] is False


def test_missing_artifact_stops_before_creating_a_repo(tmp_path, monkeypatch):
    """A failed publish must not leave an empty repository behind."""
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_token")
    with patch("app.model_publish._hub_api") as hub:
        with pytest.raises(FileNotFoundError):
            publish_model("classifier", "daley30/demo", root=tmp_path)
    hub.assert_not_called()


def test_missing_token_stops_before_creating_a_repo(trained, monkeypatch):
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
    with patch("app.model_publish._hub_api") as hub:
        with pytest.raises(ValueError):
            publish_model("classifier", "daley30/demo", root=trained)
    hub.assert_not_called()


def test_absent_dependency_explains_how_to_install_it(trained, monkeypatch):
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_token")
    with patch.dict("sys.modules", {"huggingface_hub": None}):
        with pytest.raises(ImportError, match="huggingface_hub"):
            publish_model("classifier", "daley30/demo", root=trained)


# ── CLI ───────────────────────────────────────────────────────────────────────


def test_cli_defaults_to_a_dry_run(trained, monkeypatch, capsys):
    monkeypatch.chdir(trained)
    with patch("app.model_publish._hub_api") as hub:
        code = main(["classifier", "--repo", "daley30/demo"])
    assert code == 0
    hub.assert_not_called()
    out = capsys.readouterr().out
    assert "Dry run" in out and "nothing uploaded" in out


def test_cli_push_uploads(trained, monkeypatch, capsys):
    monkeypatch.chdir(trained)
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_token")
    with patch("app.model_publish._hub_api", return_value=MagicMock()):
        code = main(["classifier", "--repo", "daley30/demo", "--push"])
    assert code == 0
    assert "Published classifier" in capsys.readouterr().out


def test_cli_reports_a_missing_model_without_a_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["classifier", "--repo", "daley30/demo", "--push"])
    assert code == 1
    assert "error:" in capsys.readouterr().err


def test_cli_rejects_an_unknown_model(trained, monkeypatch):
    monkeypatch.chdir(trained)
    with pytest.raises(SystemExit):  # argparse rejects it before we run
        main(["nonsense", "--repo", "daley30/demo"])


def test_cli_requires_a_repo(trained, monkeypatch):
    monkeypatch.chdir(trained)
    with pytest.raises(SystemExit):
        main(["classifier"])


def test_cli_public_flag_reaches_the_publisher(trained, monkeypatch):
    monkeypatch.chdir(trained)
    monkeypatch.setenv(TOKEN_ENV_VAR, "hf_token")
    api = MagicMock()
    with patch("app.model_publish._hub_api", return_value=api):
        main(["classifier", "--repo", "daley30/demo", "--push", "--public"])
    assert api.create_repo.call_args.kwargs["private"] is False


def test_card_points_at_a_module_that_exists():
    """The card told readers to look at `app/classifier`, which is not a file."""
    for model in PUBLISHABLE_MODELS.values():
        assert Path(model.module).is_file(), model.module
        card = build_model_card(model, "x/y", _AT)
        assert model.module in card
