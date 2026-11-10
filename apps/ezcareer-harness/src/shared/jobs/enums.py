from enum import StrEnum


class PostedWithin(StrEnum):
    DAY = "day"
    """Posted in the last day"""

    WEEK = "week"
    """Posted in the last week"""

    MONTH = "month"
    """Posted in the last month"""
