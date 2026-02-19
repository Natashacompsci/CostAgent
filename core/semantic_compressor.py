import re

class SemanticCompressor:
    def __init__(self):
        self.stopwords = {"the", "a", "an", "and", "of", "in", "to", "is", "on"}

    def compress(self, prompt_text, max_tokens=None):
        """Compress text by removing extra whitespace, stopwords, and truncating."""
        # Collapse whitespace and newlines
        text = re.sub(r'\s+', ' ', prompt_text).strip()
        # Remove stopwords
        words = [w for w in text.split() if w.lower() not in self.stopwords]
        compressed_text = ' '.join(words)

        # Truncate to max_tokens if specified
        if max_tokens:
            compressed_text = ' '.join(compressed_text.split()[:max_tokens])

        return compressed_text


if __name__ == "__main__":
    compressor = SemanticCompressor()
    text = "This is an example of a very long prompt that could be sent to a language model."
    compressed = compressor.compress(text, max_tokens=10)
    print("Original:", text)
    print("Compressed:", compressed)


