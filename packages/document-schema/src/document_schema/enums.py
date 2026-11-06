from enum import StrEnum


class Align(StrEnum):
    LEFT = "left"
    """Lines start at the left"""

    CENTER = "center"
    """Lines are centred"""

    JUSTIFY = "justify"
    """Lines fill the width"""


class Region(StrEnum):
    TOP = "top"
    """Header across the page"""

    TOP_LEFT = "top-left"
    """Left of the header"""

    TOP_CENTER = "top-center"
    """Middle of the header"""

    TOP_RIGHT = "top-right"
    """Right of the header"""

    MAIN = "main"
    """Main column"""

    SIDE = "side"
    """Side column"""


class Font(StrEnum):
    INTER = "inter"
    """Inter, a neutral sans"""

    LATO = "lato"
    """Lato, a warm sans"""

    SOURCE_SANS = "source-sans-3"
    """Source Sans 3, a plain sans"""

    SOURCE_SERIF = "source-serif-4"
    """Source Serif 4, a sturdy serif"""

    MERRIWEATHER = "merriweather"
    """Merriweather, a wide serif for screens and print"""

    EB_GARAMOND = "eb-garamond"
    """EB Garamond, a classic book serif"""
