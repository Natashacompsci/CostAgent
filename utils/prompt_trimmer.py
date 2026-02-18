import tiktoken
from langchain_text_splitters import TokenTextSplitter


class PromptTrimmer:
    """Trim prompt text to a hard token limit using langchain-text-splitters."""

    def __init__(self, encoding_name: str = "cl100k_base", max_tokens: int = 2000):
        self._encoding_name = encoding_name
        self._max_tokens = max_tokens
        self._splitter = TokenTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=0,
            encoding_name=encoding_name,
        )

    def trim_to_token_limit(self, text: str, max_tokens: int | None = None) -> str:
        """Return text trimmed to at most max_tokens tokens (first chunk only)."""
        if max_tokens and max_tokens != self._max_tokens:
            splitter = TokenTextSplitter(
                chunk_size=max_tokens,
                chunk_overlap=0,
                encoding_name=self._encoding_name,
            )
        else:
            splitter = self._splitter
        chunks = splitter.split_text(text)
        return chunks[0] if chunks else ""

    def count_tokens(self, text: str) -> int:
        """Return the exact token count for text using the configured encoding."""
        enc = tiktoken.get_encoding(self._encoding_name)
        return len(enc.encode(text))


if __name__ == "__main__":
    trimmer = PromptTrimmer(max_tokens=10)
    long_text = "This is a fairly long sentence that should exceed ten tokens easily."
    print("Original tokens:", trimmer.count_tokens(long_text))
    trimmed = trimmer.trim_to_token_limit(long_text)
    print("Trimmed tokens: ", trimmer.count_tokens(trimmed))
    print("Trimmed text:   ", trimmed)
