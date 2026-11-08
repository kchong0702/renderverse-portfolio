from typing import Annotated

from pydantic import AfterValidator, HttpUrl

Url = Annotated[str, AfterValidator(lambda url: str(HttpUrl(url)))]
"""An http or https URL as text"""
