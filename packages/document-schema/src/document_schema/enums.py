from enum import StrEnum


class Align(StrEnum):
    LEFT = "left"
    CENTER = "center"
    JUSTIFY = "justify"


class Region(StrEnum):
    TOP = "top"
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    MAIN = "main"
    SIDE = "side"
