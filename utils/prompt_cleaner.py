import re
import unicodedata


class PromptCleaner:
    """Clean raw prompt text before compression or token counting."""

    def clean(self, text: str) -> str:
        """Apply all cleaning steps in sequence."""
        text = self.strip_html(text)
        text = self.normalize_unicode(text)
        text = self.collapse_whitespace(text)
        return text

    def strip_html(self, text: str) -> str:
        """Remove HTML tags."""
        return re.sub(r"<[^>]+>", "", text)

    def normalize_unicode(self, text: str) -> str:
        """Normalize fancy quotes, em-dashes, ligatures to ASCII equivalents."""
        return unicodedata.normalize("NFKC", text)

    def collapse_whitespace(self, text: str) -> str:
        """Replace any sequence of whitespace with a single space and strip."""
        return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    cleaner = PromptCleaner()
    raw = '  <b>Hello</b>   \u201cworld\u201d\n\n  test  '
    print("Raw:    ", repr(raw))
    print("Cleaned:", repr(cleaner.clean(raw)))
