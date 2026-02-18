import pytest

from core.semantic_compressor import SemanticCompressor


@pytest.fixture
def compressor():
    return SemanticCompressor()


def test_compress_removes_stopwords(compressor):
    result = compressor.compress("This is a test of the compressor")
    words = result.split()
    assert "is" not in words
    assert "the" not in words
    assert "a" not in words


def test_compress_collapses_whitespace(compressor):
    result = compressor.compress("  hello   world  ")
    assert "  " not in result
    assert result == "hello world"


def test_compress_with_max_tokens_truncates(compressor):
    text = "word " * 100
    result = compressor.compress(text, max_tokens=5)
    assert len(result.split()) <= 5


def test_compress_empty_string(compressor):
    assert compressor.compress("") == ""


def test_compress_preserves_content_words(compressor):
    result = compressor.compress("quantum computing neural networks")
    assert "quantum" in result
    assert "computing" in result
    assert "neural" in result
    assert "networks" in result
