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
