#!/usr/bin/env python3
"""Smoke-test the installed core wheel from outside the source checkout."""

import json
from importlib import metadata
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap


SOURCE_ROOT = Path(__file__).resolve().parents[1]
OPTIONAL_ROOTS = {
    "chromadb",
    "dashscope",
    "docx",
    "faiss",
    "jieba",
    "langchain_chroma",
    "langchain_community",
    "langchain_huggingface",
    "langchain_milvus",
    "langchain_text_splitters",
    "lxml",
    "markdown_it",
    "nltk",
    "openpyxl",
    "pandas",
    "pdfplumber",
    "pymilvus",
    "pypdf",
    "qdrant_client",
    "rank_bm25",
    "scipy",
    "sklearn",
    "timem",
    "zai",
}
STATEMENTS = [
    "import aigility",
    (
        "import sys; import aigility; "
        "assert 'aigility.chat' not in sys.modules; "
        "assert 'aigility.memory' not in sys.modules; "
        "assert 'aigility.rag' not in sys.modules"
    ),
    "from aigility import ADKClient",
    "from aigility.chat import ChatAgent",
    (
        "import sys; from aigility.chat import ChatAgent; "
        "assert 'aigility.chat.service' not in sys.modules; "
        "assert 'aigility.chatflow' not in sys.modules"
    ),
    "from aigility.memory import MemoryConfig",
    (
        "import sys; from aigility.memory import MemoryConfig; "
        "assert 'aigility.memory.providers.timem' not in sys.modules"
    ),
    "from aigility.memory import TimemMemoryProvider",
    "from aigility.memory.providers import TimemMemoryProvider",
    "from aigility.rag import RAGConfig, TimeMRAGClient",
    (
        "import sys; from aigility.rag import RAGConfig, TimeMRAGClient; "
        "assert 'aigility.rag.service' not in sys.modules; "
        "assert 'aigility.rag.ingestion' not in sys.modules"
    ),
    "from aigility.rag import IngestionManager, RAGService",
    "from aigility import *",
    "from aigility.chat import *",
    "from aigility.memory import *",
    "from aigility.rag import *",
    "import aigility.rag.markdown_splitter",
    "import aigility.rag.hybrid_search",
]
EXPECTED_OPTIONAL_REQUIREMENTS = {
    "dashscope": (
        ("embedding-dashscope", "rerank-dashscope"),
        ">=1.16.0",
    ),
    "jieba": "nlp",
    "langchain-huggingface": "embedding-huggingface",
    "langchain-text-splitters": "rag",
    "markdown-it-py": "doc-markdown",
    "openpyxl": "doc-excel",
    "pandas": "doc-excel",
    "pdfplumber": "doc-pdf",
    "python-docx": "doc-word",
    "rank-bm25": "rag",
    "scikit-learn": "nlp",
    "sentence-transformers": "embedding-huggingface",
    "timem-ai": ("timem", ">=0.1.6"),
}
EXPECTED_ALL_EXTRA_REFERENCES = {
    "anthropic",
    "embedding-dashscope",
    "rag-local",
    "rerank-dashscope",
    "timem-rag",
    "vectorstore-faiss",
    "vectorstore-milvus",
    "vectorstore-qdrant",
    "zai",
}
EXPECTED_CORE_REQUIREMENTS = {
    "python-dotenv": ">=1.0.0",
}
EXPECTED_REQUIRES_PYTHON = ">=3.9"


def _probe(statement):
    probe = textwrap.dedent(
        """
        import builtins
        import contextlib
        import importlib
        import io
        import json
        import logging
        import os
        from pathlib import Path
        import sys
        import time
        import tracemalloc
        import warnings

        blocked = set(json.loads(os.environ["AIGILITY_BLOCKED_MODULES"]))
        statement = os.environ["AIGILITY_IMPORT_STATEMENT"]
        attempted = []
        real_import = builtins.__import__
        real_import_module = importlib.import_module

        def direct_caller():
            frame = sys._getframe(2)
            return frame.f_globals.get("__name__", "")

        def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split(".", 1)[0]
            importer = (globals or {}).get("__name__", "")
            if level == 0 and importer.startswith("aigility") and root in blocked:
                attempted.append({"importer": importer, "module": name})
                error = ModuleNotFoundError("blocked optional dependency: " + root)
                error.name = root
                raise error
            return real_import(name, globals, locals, fromlist, level)

        def traced_import_module(name, package=None):
            root = name.split(".", 1)[0]
            importer = direct_caller()
            if (
                not name.startswith(".")
                and importer.startswith("aigility")
                and root in blocked
            ):
                attempted.append({"importer": importer, "module": name})
                error = ModuleNotFoundError("blocked optional dependency: " + root)
                error.name = root
                raise error
            return real_import_module(name, package)

        builtins.__import__ = traced_import
        importlib.import_module = traced_import_module
        before_env = dict(os.environ)
        before_path = list(sys.path)
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        caught_logs = []
        caught_warnings = []
        warning_events = []
        error = None

        real_warn = warnings.warn

        def traced_warn(
            message,
            category=None,
            stacklevel=1,
            source=None,
            **kwargs,
        ):
            frame = sys._getframe(1)
            warning_category = (
                type(message)
                if isinstance(message, Warning)
                else (category or UserWarning)
            )
            warning_events.append({
                "category": warning_category.__name__,
                "emitter": frame.f_globals.get("__name__", ""),
                "message": str(message),
            })
            return real_warn(
                message,
                category=category,
                stacklevel=stacklevel + 1,
                source=source,
                **kwargs,
            )

        warnings.warn = traced_warn

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                caught_logs.append({
                    "level": record.levelname,
                    "lineno": record.lineno,
                    "message": record.getMessage(),
                    "name": record.name,
                    "pathname": record.pathname,
                })

        root_logger = logging.getLogger()
        original_level = root_logger.level
        capture_handler = CaptureHandler()
        root_logger.addHandler(capture_handler)
        root_logger.setLevel(logging.DEBUG)

        tracemalloc.start()
        started = time.perf_counter()
        with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stderr):
            with warnings.catch_warnings(record=True) as records:
                warnings.simplefilter("always")
                try:
                    exec(statement, {})
                except BaseException as exc:
                    error = "{}: {}".format(type(exc).__name__, exc)
                unmatched_events = list(warning_events)
                for record in records:
                    category_name = type(record.message).__name__
                    message = str(record.message)
                    emitter = ""
                    for index, event in enumerate(unmatched_events):
                        if (
                            event["category"] == category_name
                            and event["message"] == message
                        ):
                            emitter = event["emitter"]
                            unmatched_events.pop(index)
                            break
                    caught_warnings.append({
                        "category": category_name,
                        "emitter": emitter,
                        "filename": record.filename,
                        "lineno": record.lineno,
                        "message": message,
                    })
        warnings.warn = real_warn
        elapsed_ms = (time.perf_counter() - started) * 1000
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        root_logger.removeHandler(capture_handler)
        root_logger.setLevel(original_level)
        module = sys.modules.get("aigility")
        package_file = getattr(module, "__file__", None)
        package_root = Path(package_file).resolve().parent if package_file else None
        aigility_logs = []
        external_logs = []
        for record in caught_logs:
            try:
                Path(record["pathname"]).resolve().relative_to(package_root)
            except (TypeError, ValueError):
                emitted_by_aigility = record["name"].startswith("aigility")
            else:
                emitted_by_aigility = True
            if emitted_by_aigility:
                aigility_logs.append(record)
            else:
                external_logs.append(record)
        aigility_warnings = []
        external_warnings = []
        for warning in caught_warnings:
            if warning["emitter"]:
                if warning["emitter"].startswith("aigility"):
                    aigility_warnings.append(warning)
                else:
                    external_warnings.append(warning)
                continue
            try:
                Path(warning["filename"]).resolve().relative_to(package_root)
            except (TypeError, ValueError):
                warning["emitter"] = "unknown"
                external_warnings.append(warning)
            else:
                warning["emitter"] = "aigility"
                aigility_warnings.append(warning)
        ignored_env = {"AIGILITY_BLOCKED_MODULES", "AIGILITY_IMPORT_STATEMENT"}
        env_changes = {
            key: [before_env.get(key), os.environ.get(key)]
            for key in set(before_env) | set(os.environ)
            if key not in ignored_env and before_env.get(key) != os.environ.get(key)
        }
        print(json.dumps({
            "attempted": attempted,
            "elapsed_ms": round(elapsed_ms, 3),
            "env_changes": env_changes,
            "error": error,
            "logs": aigility_logs,
            "package_file": package_file,
            "path_changed": before_path != sys.path,
            "peak_kib": round(peak_bytes / 1024, 1),
            "stderr": captured_stderr.getvalue(),
            "stdout": captured_stdout.getvalue(),
            "external_warnings": external_warnings,
            "external_logs": external_logs,
            "warnings": aigility_warnings,
        }, ensure_ascii=False))
        """
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["AIGILITY_BLOCKED_MODULES"] = json.dumps(sorted(OPTIONAL_ROOTS))
    env["AIGILITY_IMPORT_STATEMENT"] = statement
    with tempfile.TemporaryDirectory(prefix="aigility-wheel-smoke-") as workdir:
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
    if completed.stderr:
        raise AssertionError(
            "probe emitted unexpected stderr for {!r}: {}".format(
                statement, completed.stderr
            )
        )
    return json.loads(completed.stdout)


def main():
    failures = []
    metrics = []
    requirements_entries = [
        line.strip()
        for line in (SOURCE_ROOT / "requirements.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if requirements_entries != ["-e ."]:
        failures.append(
            {
                "reason": "requirements.txt must delegate to pyproject.toml",
                "requirements_entries": requirements_entries,
            }
        )
    requirements = metadata.distribution("aigility").requires or []
    requires_python = metadata.metadata("aigility").get("Requires-Python")
    if requires_python != EXPECTED_REQUIRES_PYTHON:
        failures.append(
            {
                "expected_requires_python": EXPECTED_REQUIRES_PYTHON,
                "requires_python": requires_python,
            }
        )

    for dependency, expected in EXPECTED_OPTIONAL_REQUIREMENTS.items():
        if isinstance(expected, tuple):
            extras, minimum = expected
        else:
            extras, minimum = expected, None
        if isinstance(extras, str):
            extras = (extras,)
        matching = [
            requirement
            for requirement in requirements
            if requirement.lower().startswith(dependency)
        ]
        missing_extras = [
            extra
            for extra in extras
            if not any(
                'extra == "{}"'.format(extra) in requirement
                for requirement in matching
            )
        ]
        if not matching or missing_extras:
            failures.append(
                {
                    "dependency": dependency,
                    "expected_extras": extras,
                    "missing_extras": missing_extras,
                    "requirements": matching,
                }
            )
        if any("extra ==" not in requirement for requirement in matching):
            failures.append(
                {
                    "dependency": dependency,
                    "reason": "optional dependency leaked into core requirements",
                    "requirements": matching,
                }
            )
        if minimum and not any(minimum in requirement for requirement in matching):
            failures.append(
                {
                    "dependency": dependency,
                    "expected_minimum": minimum,
                    "requirements": matching,
                }
            )

    for referenced_extra in sorted(EXPECTED_ALL_EXTRA_REFERENCES):
        requirement_prefix = "aigility[{}]".format(referenced_extra)
        matching = [
            requirement
            for requirement in requirements
            if requirement.lower().startswith(requirement_prefix)
            and 'extra == "all"' in requirement
        ]
        if not matching:
            failures.append(
                {
                    "bundle": "all",
                    "missing_extra_reference": referenced_extra,
                }
            )

    for dependency, minimum in EXPECTED_CORE_REQUIREMENTS.items():
        matching = [
            requirement
            for requirement in requirements
            if requirement.lower().startswith(dependency)
        ]
        if not matching or not any(minimum in requirement for requirement in matching):
            failures.append(
                {
                    "core_dependency": dependency,
                    "expected_minimum": minimum,
                    "requirements": matching,
                }
            )
        if any("extra ==" in requirement for requirement in matching):
            failures.append(
                {
                    "core_dependency": dependency,
                    "reason": "core dependency is incorrectly guarded by an extra",
                    "requirements": matching,
                }
            )

    expected = {
        "attempted": [],
        "env_changes": {},
        "error": None,
        "logs": [],
        "path_changed": False,
        "stderr": "",
        "stdout": "",
        "warnings": [],
    }
    for statement in STATEMENTS:
        result = _probe(statement)
        external_warnings = result.pop("external_warnings")
        external_logs = result.pop("external_logs")
        metrics.append(
            {
                "statement": statement,
                "elapsed_ms": result.pop("elapsed_ms"),
                "external_warnings": external_warnings,
                "external_logs": external_logs,
                "peak_kib": result.pop("peak_kib"),
            }
        )
        package_file = result.pop("package_file")
        source_package = (SOURCE_ROOT / "aigility").resolve()
        package_path = Path(package_file).resolve() if package_file else None
        try:
            package_path.relative_to(source_package)
        except (AttributeError, ValueError):
            loaded_from_source = False
        else:
            loaded_from_source = True
        if not package_file or loaded_from_source:
            failures.append(
                {
                    "statement": statement,
                    "reason": "source checkout shadowed installed wheel",
                    "package_file": package_file,
                }
            )
        if result != expected:
            failures.append({"statement": statement, "result": result})

    if failures:
        raise AssertionError(json.dumps(failures, ensure_ascii=False, indent=2))
    print(
        "core artifact import smoke passed ({} isolated imports, {} extra mappings)".format(
            len(STATEMENTS), len(EXPECTED_OPTIONAL_REQUIREMENTS)
        )
    )
    print("import metrics: " + json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()
