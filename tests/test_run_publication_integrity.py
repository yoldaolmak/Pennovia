"""One-command publishing must never bypass known generation failures.

Synthetic model transport only: no network, no WordPress changes, no paid model.
"""
import sys

import pytest

from pennovia import cli
from pennovia.voice import generator
from tests.test_cli_synthetic_pipeline import SYNTHETIC_DRAFT, demo_corpus


def _invoke_run(monkeypatch, *options):
    monkeypatch.setattr(sys, "argv", [
        "pennovia", "run", "--corpus", str(demo_corpus()),
        "--language", "en", "--topic", "A careful travel guide",
        "--type", "travel_guide", "--backend", "ollama",
        *options,
    ])
    cli.main()


@pytest.mark.parametrize("completion", ["truncated", "unknown"])
def test_unfinished_ollama_cannot_publish_from_one_command(
    monkeypatch, capsys, completion,
):
    calls = []

    def fake_generate(*args, **kwargs):
        assert kwargs["return_metadata"] is True
        return generator.OllamaGeneration(
            SYNTHETIC_DRAFT, completion,
            "length" if completion == "truncated" else None,
            400, 640,
        )

    monkeypatch.setattr(generator, "generate", fake_generate)
    monkeypatch.setattr(cli, "_export_all", lambda *args, **kwargs: calls.append("export"))
    with pytest.raises(SystemExit) as ex:
        _invoke_run(monkeypatch, "--dest", "wordpress", "--publish")
    assert ex.value.code == 1
    assert calls == []
    captured = capsys.readouterr()
    assert "publication blocked" in captured.err
    assert "Exporting" not in captured.out


def test_known_unsafe_claim_marker_blocks_publication_even_with_complete_model(
    monkeypatch, capsys,
):
    calls = []

    def fake_generate(*args, **kwargs):
        return generator.OllamaGeneration(
            SYNTHETIC_DRAFT + "\n\nA traveler pays [Taxi Fare].",
            "complete", "stop", 400, 500,
        )

    monkeypatch.setattr(generator, "generate", fake_generate)
    monkeypatch.setattr(cli, "_export_all", lambda *args, **kwargs: calls.append("export"))
    with pytest.raises(SystemExit) as ex:
        _invoke_run(monkeypatch, "--dest", "wordpress", "--publish")
    assert ex.value.code == 1
    assert calls == []
    assert "unresolved_placeholder" in capsys.readouterr().err


def test_completed_ollama_keeps_explicit_wordpress_publish_contract(monkeypatch):
    recorded = []

    def fake_generate(*args, **kwargs):
        assert kwargs["return_metadata"] is True
        return generator.OllamaGeneration(
            SYNTHETIC_DRAFT, "complete", "stop", 350, 500,
        )

    monkeypatch.setattr(generator, "generate", fake_generate)
    monkeypatch.setattr(
        cli, "_export_all",
        lambda *args, **kwargs: recorded.append((args, kwargs)),
    )
    _invoke_run(monkeypatch, "--dest", "wordpress", "--publish")
    assert len(recorded) == 1
    assert recorded[0][0][3] == "wordpress"
    assert recorded[0][1]["publish"] is True


def test_unfinished_local_draft_remains_exportable_for_editor(monkeypatch, tmp_path):
    def fake_generate(*args, **kwargs):
        return generator.OllamaGeneration(
            SYNTHETIC_DRAFT, "truncated", "length", 350, 640,
        )

    monkeypatch.setattr(generator, "generate", fake_generate)
    _invoke_run(monkeypatch, "--dest", str(tmp_path), "--format", "txt")
    files = list(tmp_path.glob("*.txt"))
    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8") == SYNTHETIC_DRAFT


def test_publish_flag_on_non_wordpress_destination_is_rejected_before_write(
    monkeypatch, capsys, tmp_path,
):
    monkeypatch.setattr(
        generator, "generate", lambda *args, **kwargs: SYNTHETIC_DRAFT,
    )
    with pytest.raises(SystemExit) as ex:
        _invoke_run(monkeypatch, "--dest", str(tmp_path), "--publish")
    assert ex.value.code == 1
    assert not list(tmp_path.iterdir())
    assert "--publish is only valid for WordPress" in capsys.readouterr().err
