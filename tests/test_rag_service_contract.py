"""Public runtime contract tests for ``RAGService`` environment loading."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _FakeEmbeddingModel:
    def embed_documents(self, texts):
        return [[] for _ in texts]

    def embed_query(self, text):
        return []


class _FakeVectorStore:
    def add_documents(self, documents):
        return []

    def similarity_search(self, query, k=4):
        return []


def _replace_external_provider_boundaries(monkeypatch, service_module) -> None:
    monkeypatch.setattr(
        service_module.EmbeddingFactory,
        "get_embedding_model",
        staticmethod(lambda config: _FakeEmbeddingModel()),
    )
    monkeypatch.setattr(
        service_module.VectorStoreFactory,
        "get_vector_store",
        staticmethod(lambda config, embedding: _FakeVectorStore()),
    )


def test_importing_rag_service_does_not_load_dotenv(tmp_path: Path) -> None:
    probe_name = "AIGILITY_RAG_IMPORT_DOTENV_PROBE"
    script = textwrap.dedent(
        f"""
        import os
        import sys
        import types

        dotenv = types.ModuleType("dotenv")
        dotenv.find_dotenv = lambda **kwargs: ".env"

        def load_dotenv(*args, **kwargs):
            os.environ[{probe_name!r}] = "loaded-at-import"
            return True

        dotenv.load_dotenv = load_dotenv
        sys.modules["dotenv"] = dotenv

        import aigility.rag.service

        assert {probe_name!r} not in os.environ
        """
    )
    env = os.environ.copy()
    env.pop(probe_name, None)
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(PROJECT_ROOT), env.get("PYTHONPATH")))
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_default_construction_loads_dotenv_before_default_config(
    tmp_path: Path, monkeypatch
) -> None:
    from aigility.rag import service as service_module

    probe_name = "AIGILITY_RAG_DEFAULT_CONFIG_DOTENV_PROBE"
    (tmp_path / ".env").write_text(
        f"{probe_name}=loaded-before-default-config\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(probe_name, raising=False)
    _replace_external_provider_boundaries(monkeypatch, service_module)

    real_config_type = service_module.RAGConfig
    observed = {}

    def create_default_config():
        observed["value"] = os.environ.get(probe_name)
        return real_config_type()

    monkeypatch.setattr(service_module, "RAGConfig", create_default_config)

    service_module.RAGService()

    assert observed == {"value": "loaded-before-default-config"}


def test_default_construction_loads_dotenv_without_overriding_environment(
    tmp_path: Path, monkeypatch
) -> None:
    from aigility.rag import service as service_module

    existing_name = "AIGILITY_RAG_EXISTING_ENV_PROBE"
    new_name = "AIGILITY_RAG_NEW_DOTENV_PROBE"
    (tmp_path / ".env").write_text(
        f"{existing_name}=from-dotenv\n{new_name}=loaded-from-dotenv\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(existing_name, "from-environment")
    monkeypatch.delenv(new_name, raising=False)
    _replace_external_provider_boundaries(monkeypatch, service_module)

    service_module.RAGService()

    assert os.environ[existing_name] == "from-environment"
    assert os.environ[new_name] == "loaded-from-dotenv"


def test_explicit_rerank_initialization_failure_is_not_silently_downgraded(
    tmp_path: Path, monkeypatch
) -> None:
    from aigility.rag import RAGConfig, RerankConfig
    from aigility.rag import service as service_module

    monkeypatch.chdir(tmp_path)
    _replace_external_provider_boundaries(monkeypatch, service_module)
    rerank_error = RuntimeError("rerank constructor failed")

    def fail_rerank(config):
        raise rerank_error

    monkeypatch.setattr(
        service_module.RerankFactory,
        "get_reranker",
        staticmethod(fail_rerank),
    )

    with pytest.raises(RuntimeError) as caught:
        service_module.RAGService(
            RAGConfig(rerank=RerankConfig(enabled=True, api_key="test-key"))
        )

    assert caught.value is rerank_error
