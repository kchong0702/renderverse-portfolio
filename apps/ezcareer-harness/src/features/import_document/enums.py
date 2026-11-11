from enum import StrEnum


class Trait(StrEnum):
    ACCENT_BAND = "accent_band"
    """A coloured band down one side of the page"""

    PHOTO = "photo"
    """A photo on the first page"""

    TINTED_HEADINGS = "tinted_headings"
    """Headings on tinted strips"""

    RULED_HEADINGS = "ruled_headings"
    """Headings over or under a rule"""

    SERIF_FONT = "serif_font"
    """Body text in a serif font"""

    COLOURED_NAME = "coloured_name"
    """The name in a colour"""
