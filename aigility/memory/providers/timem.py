"""TiMEM implementation of the provider-neutral AIGility memory seam."""

import inspect
import logging
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from ..._optional import import_optional
from ..contracts import (
    MemoryCapabilities,
    MemoryError,
    MemoryRecord,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStatus,
    MemoryWriteRequest,
    MemoryWriteResult,
)
from .base import BaseMemoryProvider

logger = logging.getLogger(__name__)


class TimemMemoryProvider(BaseMemoryProvider):
    """Map AIGility's generic contracts to the TiMEM high-level SDK.

    Only the stable conversation write and semantic retrieval operations are
    part of this adapter's common surface.  TiMEM-specific administration and
    L1-L5 controls can be added later as optional capabilities without changing
    ``BaseMemoryProvider``.
    """

    provider_name = "timem"
    capabilities = MemoryCapabilities(
        conversation_write=True,
        semantic_search=True,
    )

    def __init__(
        self,
        config: Any,
        client_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        super().__init__(config)
        self.api_key = config.get_api_key()
        self.base_url = config.get_base_url()
        self._client_factory = client_factory
        self._client: Optional[Any] = None
        self.enabled = False
        self._unavailable_status = MemoryStatus.DISABLED
        self._unavailable_error = MemoryError(
            code="provider_disabled",
            message="Memory provider 未启用",
        )

        if not config.enabled:
            return
        if not self.api_key:
            raise ValueError(
                "TiMEM memory is enabled but no API key was provided. "
                "Set TIMEM_API_KEY or pass api_key in MemoryProviderConfig."
            )

        if self._client_factory is None:
            timem = import_optional(
                "timem",
                feature="TiMEM memory",
                extra="timem",
                dependency="timem-ai",
            )
            self._client_factory = timem.AsyncMemory

        self._client = self._create_client()
        self.enabled = True
        logger.info("TiMEM memory provider initialized")

    def _create_client(self) -> Any:
        """Instantiate an SDK client without leaking provider options upward."""

        sdk_options = self.config.kwargs.get("sdk_options", {})
        if not isinstance(sdk_options, Mapping):
            raise ValueError("kwargs.sdk_options 必须是映射类型")

        client_kwargs: Dict[str, Any] = dict(sdk_options)
        client_kwargs.update(
            {
                "api_key": self.api_key,
                "base_url": self.base_url.rstrip("/") if self.base_url else None,
                "timeout": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
            }
        )
        if self._client_factory is None:
            raise RuntimeError("TiMEM client factory 未初始化")
        return self._client_factory(**client_kwargs)

    async def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        """Write a conversation with TiMEM's stable ``AsyncMemory.add`` API."""

        if not self._client:
            return MemoryWriteResult(
                status=self._unavailable_status,
                provider=self.provider_name,
                error=self._unavailable_error,
            )

        add_kwargs: Dict[str, Any] = {
            "messages": list(request.messages),
            "user_id": request.scope.identity.user_id,
            "character_id": request.scope.identity.agent_id,
            "session_id": request.scope.session_id,
        }
        if request.metadata:
            add_kwargs["metadata"] = dict(request.metadata)
        self._copy_supported_options(
            add_kwargs,
            request.provider_options,
            {"domain", "memory_levels", "manual_complete", "format"},
        )

        try:
            raw_result = await self._client.add(**add_kwargs)
        except Exception as exc:
            status, error = self._classify_exception(exc)
            logger.warning(
                "TiMEM write failed: status=%s error_type=%s",
                status.value,
                type(exc).__name__,
            )
            return MemoryWriteResult(
                status=status,
                provider=self.provider_name,
                error=error,
            )

        return self._normalize_write_result(raw_result)

    async def retrieve(self, request: MemorySearchRequest) -> MemorySearchResult:
        """Retrieve memories with TiMEM's semantic search API."""

        if not self._client:
            return MemorySearchResult(
                status=self._unavailable_status,
                provider=self.provider_name,
                error=self._unavailable_error,
            )

        search_kwargs: Dict[str, Any] = {
            "query": request.query,
            "user_id": request.identity.user_id,
            "character_id": request.identity.agent_id,
            "limit": request.limit,
            "include_context": request.include_context,
        }
        if request.session_id:
            search_kwargs["session_id"] = request.session_id
        if request.filters:
            search_kwargs["filters"] = dict(request.filters)
        self._copy_supported_options(
            search_kwargs,
            request.provider_options,
            {
                "start_time",
                "end_time",
                "layer",
                "keywords",
                "search_mode",
                "score_threshold",
                "format",
            },
        )

        try:
            raw_result = await self._client.search(**search_kwargs)
        except Exception as exc:
            status, error = self._classify_exception(exc)
            logger.warning(
                "TiMEM retrieve failed: status=%s error_type=%s",
                status.value,
                type(exc).__name__,
            )
            return MemorySearchResult(
                status=status,
                provider=self.provider_name,
                error=error,
            )

        return self._normalize_search_result(raw_result, request.limit)

    async def close(self) -> None:
        """Close either current or older SDK client variants safely."""

        if not self._client:
            return

        close_method = getattr(self._client, "aclose", None) or getattr(
            self._client, "close", None
        )
        if close_method is None:
            return

        try:
            close_result = close_method()
            if inspect.isawaitable(close_result):
                await close_result
        except Exception as exc:
            logger.warning("TiMEM close failed: error_type=%s", type(exc).__name__)
        finally:
            self._client = None
            self.enabled = False

    def _normalize_write_result(self, raw_result: Any) -> MemoryWriteResult:
        if self._response_failed(raw_result):
            status, error = self._classify_response_failure(raw_result)
            return MemoryWriteResult(
                status=status,
                provider=self.provider_name,
                error=error,
            )

        records = self._extract_records(raw_result)
        payload = raw_result if isinstance(raw_result, Mapping) else {}
        memory_ids = self._extract_memory_ids(payload, records)
        return MemoryWriteResult(
            status=MemoryStatus.SUCCESS,
            provider=self.provider_name,
            records=records,
            memory_id=self._optional_string(payload.get("memory_id")),
            memory_ids=memory_ids,
            task_id=self._optional_string(payload.get("task_id")),
            message=self._optional_string(payload.get("message")) or "",
        )

    def _normalize_search_result(
        self, raw_result: Any, limit: int
    ) -> MemorySearchResult:
        if self._response_failed(raw_result):
            status, error = self._classify_response_failure(raw_result)
            return MemorySearchResult(
                status=status,
                provider=self.provider_name,
                error=error,
            )

        return MemorySearchResult(
            status=MemoryStatus.SUCCESS,
            provider=self.provider_name,
            records=self._extract_records(raw_result)[:limit],
        )

    @staticmethod
    def _copy_supported_options(
        target: Dict[str, Any],
        options: Mapping[str, Any],
        supported_options: Collection[str],
    ) -> None:
        for key in supported_options:
            if key in options and options[key] is not None:
                target[key] = options[key]

    @staticmethod
    def _response_failed(raw_result: Any) -> bool:
        return isinstance(raw_result, Mapping) and raw_result.get("success") is False

    def _classify_response_failure(
        self, raw_result: Any
    ) -> Tuple[MemoryStatus, MemoryError]:
        status_code = self._extract_status_code(raw_result)
        status = self._status_from_code(status_code) or MemoryStatus.FAILED
        return status, self._error_for_status(status, status_code)

    def _classify_exception(self, exc: Exception) -> Tuple[MemoryStatus, MemoryError]:
        status_code = self._extract_status_code(exc)
        status = self._status_from_code(status_code)
        exception_name = type(exc).__name__.lower()
        exception_text = str(exc).lower()

        if status is None:
            if "authentication" in exception_name or "auth" in exception_name:
                status = MemoryStatus.UNAUTHORIZED
            elif "validation" in exception_name:
                status = MemoryStatus.INVALID_REQUEST
            elif "rate" in exception_name or "429" in exception_text:
                status = MemoryStatus.RATE_LIMITED
            elif "timeout" in exception_name or "timeout" in exception_text:
                status = MemoryStatus.UNAVAILABLE
            else:
                status = MemoryStatus.FAILED
        return status, self._error_for_status(status, status_code)

    @staticmethod
    def _status_from_code(status_code: Optional[int]) -> Optional[MemoryStatus]:
        if status_code == 401:
            return MemoryStatus.UNAUTHORIZED
        if status_code == 402:
            return MemoryStatus.BLOCKED
        if status_code == 422:
            return MemoryStatus.INVALID_REQUEST
        if status_code == 429:
            return MemoryStatus.RATE_LIMITED
        if status_code is not None and (status_code == 408 or status_code >= 500):
            return MemoryStatus.UNAVAILABLE
        return None

    @staticmethod
    def _error_for_status(
        status: MemoryStatus, status_code: Optional[int]
    ) -> MemoryError:
        messages = {
            MemoryStatus.BLOCKED: (
                "provider_blocked",
                "TiMEM 服务当前无可用权益",
                False,
            ),
            MemoryStatus.UNAUTHORIZED: ("unauthorized", "TiMEM 认证失败", False),
            MemoryStatus.INVALID_REQUEST: (
                "invalid_request",
                "TiMEM 请求参数无效",
                False,
            ),
            MemoryStatus.RATE_LIMITED: ("rate_limited", "TiMEM 请求受限", True),
            MemoryStatus.UNAVAILABLE: ("unavailable", "TiMEM 服务暂不可用", True),
        }
        code, message, retryable = messages.get(
            status,
            ("provider_failure", "TiMEM 操作失败", False),
        )
        return MemoryError(
            code=code,
            message=message,
            retryable=retryable,
            provider_status_code=status_code,
        )

    @staticmethod
    def _extract_status_code(value: Any) -> Optional[int]:
        candidates: List[Any] = []
        if isinstance(value, Mapping):
            candidates.extend(
                [
                    value.get("status_code"),
                    value.get("status"),
                    value.get("code"),
                ]
            )
        else:
            candidates.extend(
                [
                    getattr(value, "status_code", None),
                    getattr(value, "status", None),
                    getattr(value, "code", None),
                ]
            )
            response = getattr(value, "response", None)
            candidates.append(getattr(response, "status_code", None))

        for candidate in candidates:
            try:
                if candidate is not None:
                    return int(candidate)
            except (TypeError, ValueError):
                continue
        return None

    def _extract_records(self, raw_result: Any) -> List[MemoryRecord]:
        items = self._extract_items(raw_result)
        records: List[MemoryRecord] = []
        for item in items:
            record = self._normalize_record(item)
            if record is not None:
                records.append(record)
        return records

    @staticmethod
    def _extract_items(raw_result: Any) -> List[Any]:
        if isinstance(raw_result, list):
            return raw_result
        if not isinstance(raw_result, Mapping):
            return []

        for key in ("memories", "results"):
            candidate = raw_result.get(key)
            if isinstance(candidate, list):
                return candidate
            if isinstance(candidate, Mapping):
                return [candidate]

        data = raw_result.get("data")
        if isinstance(data, Mapping):
            for key in ("memories", "results"):
                candidate = data.get(key)
                if isinstance(candidate, list):
                    return candidate
                if isinstance(candidate, Mapping):
                    return [candidate]
        if isinstance(data, list):
            return data
        return []

    @classmethod
    def _normalize_record(cls, item: Any) -> Optional[MemoryRecord]:
        if isinstance(item, str):
            return MemoryRecord(content=item)
        if not isinstance(item, Mapping):
            return None

        nested_data = item.get("data")
        data = nested_data if isinstance(nested_data, Mapping) else {}
        content = (
            item.get("memory")
            or item.get("content")
            or item.get("summary")
            or data.get("memory")
            or data.get("content")
            or ""
        )
        metadata = item.get("metadata")
        if not isinstance(metadata, Mapping):
            metadata = data.get("metadata") if isinstance(data, Mapping) else {}
        if not isinstance(metadata, Mapping):
            metadata = {}

        score = metadata.get("score", item.get("score", data.get("score")))
        try:
            normalized_score = float(score) if score is not None else None
        except (TypeError, ValueError):
            normalized_score = None

        return MemoryRecord(
            content=str(content),
            id=cls._optional_string(item.get("id") or item.get("memory_id")),
            score=normalized_score,
            layer=cls._optional_string(
                item.get("layer") or item.get("layer_type") or item.get("level")
            ),
            metadata=dict(metadata),
            created_at=cls._optional_string(item.get("created_at")),
            updated_at=cls._optional_string(item.get("updated_at")),
        )

    @classmethod
    def _extract_memory_ids(
        cls, payload: Mapping[str, Any], records: Sequence[MemoryRecord]
    ) -> List[str]:
        raw_ids = payload.get("memory_ids", [])
        if not isinstance(raw_ids, list):
            raw_ids = []
        memory_ids = [str(memory_id) for memory_id in raw_ids if memory_id]
        if not memory_ids:
            single_id = cls._optional_string(payload.get("memory_id"))
            if single_id:
                memory_ids.append(single_id)
        if not memory_ids:
            memory_ids = [record.id for record in records if record.id]
        return memory_ids

    @staticmethod
    def _optional_string(value: Any) -> Optional[str]:
        if value is None:
            return None
        value = str(value)
        return value if value else None


__all__ = ["TimemMemoryProvider"]
