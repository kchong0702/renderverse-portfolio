from typing import Annotated

from pydantic import StringConstraints

FactRef = Annotated[str, StringConstraints(pattern=r"^fact:[A-Za-z0-9_-]{1,64}$")]
"""A profile fact cited as fact:<id>"""
