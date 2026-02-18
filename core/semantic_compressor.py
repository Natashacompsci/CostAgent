import re

class SemanticCompressor:
    def __init__(self):
        # 可扩展 stopwords 列表
        self.stopwords = {"the", "a", "an", "and", "of", "in", "to", "is", "on"}

    def compress(self, prompt_text, max_tokens=None):
        """
        压缩文本：
        1. 去掉多余空格、换行
        2. 去 stopwords
        3. 截断到 max_tokens（如果提供）
        """
        # 去换行、连续空格
        text = re.sub(r'\s+', ' ', prompt_text).strip()
        # 去 stopwords
        words = [w for w in text.split() if w.lower() not in self.stopwords]
        compressed_text = ' '.join(words)

        # 截断到 max_tokens
        if max_tokens:
            compressed_text = ' '.join(compressed_text.split()[:max_tokens])

        return compressed_text

# 测试
if __name__ == "__main__":
    compressor = SemanticCompressor()
    text = "This is an example of a very long prompt that could be sent to a language model."
    compressed = compressor.compress(text, max_tokens=10)
    print("Original:", text)
    print("Compressed:", compressed)


