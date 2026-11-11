import unicodedata


def letters_and_digits(text: str) -> str:
    """The text's letters and digits, case folded, so spacing, dashes, quotes and
    hyphenated line breaks don't count"""
    return "".join(
        ch for ch in unicodedata.normalize("NFKC", text).casefold() if ch.isalnum()
    )
