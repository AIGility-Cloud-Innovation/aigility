"""IngestionConfig 在默认两层切分下约束父段、子段和重叠。"""

import pytest
from pydantic import ValidationError

from aigility.rag.config import IngestionConfig


def test_default_small2big_sizes_stay_valid():
    config = IngestionConfig()
    assert config.enable_small2big is True
    assert config.parent_chunk_size == 1024
    assert config.child_chunk_size == 256
    assert config.child_chunk_overlap == 64
    assert config.chunk_overlap == 100


def test_child_must_be_shorter_than_parent():
    with pytest.raises(ValidationError, match="child_chunk_size"):
        IngestionConfig(parent_chunk_size=256, child_chunk_size=256)


def test_parent_overlap_must_be_shorter_than_parent():
    with pytest.raises(ValidationError, match="chunk_overlap"):
        IngestionConfig(parent_chunk_size=1024, chunk_overlap=1024)


def test_child_overlap_must_be_shorter_than_child():
    with pytest.raises(ValidationError, match="child_chunk_overlap"):
        IngestionConfig(child_chunk_size=256, child_chunk_overlap=256)


def test_single_layer_uses_chunk_size_for_overlap():
    config = IngestionConfig(enable_small2big=False, chunk_size=500, chunk_overlap=100)
    assert config.chunk_size == 500
    with pytest.raises(ValidationError, match="chunk_overlap"):
        IngestionConfig(enable_small2big=False, chunk_size=500, chunk_overlap=500)
