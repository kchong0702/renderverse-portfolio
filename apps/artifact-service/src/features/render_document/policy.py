import re
from collections.abc import Iterator
from typing import Any

import tinycss2

from src.features.render_document.exceptions import RenderError

_UNSAFE_TAG = re.compile(r"\{\{\s*[>=&{]")
"""Mustache tags a template may not use

- `{{> name}}`: a partial, which chevron loads from a file on disk
- `{{=<% %>=}}`: a delimiter change, which could hide a partial behind new delimiters
- `{{{name}}}` and `{{& name}}`: unescaped output, which lets content inject HTML
"""

_FORBIDDEN_AT_RULES = {"page", "import", "font-face"}
"""At-rules template css may not use, at any depth

- `@page`: the renderer owns the page size and margins, and last_page_fill is
  measured against them
- `@import`: could load a second stylesheet from a data: url, past this check
- `@font-face`: fonts come from presentation.fonts, each a checked woff2 asset
"""

_URL_STRING_FUNCTIONS = {"url", "src", "image-set", "-webkit-image-set"}
"""CSS functions whose string arguments are urls, not text"""

_ASSET_URL = re.compile(r"^asset:[0-9a-f]{64}$")
"""The only url template css may use: an asset of the document, inlined by the
renderer. Anything else is either a data: url that skips the asset checks or an
address the blocked network cannot load"""

_STYLE_ELEMENT = re.compile(r"<(?:style|link)[\s>/]", re.IGNORECASE)
"""A <style> or <link> start tag in the rendered body, which would add css that
was never checked. Content is escaped by Mustache, so only the template can
produce one"""

_STYLE_END = re.compile(r"</style[\s>/]", re.IGNORECASE)
"""A </style> end tag in template css, which would close the renderer's <style>
element early and turn the rest of the css into html"""


def _urls(values: list[Any]) -> Iterator[str]:
    for value in values:
        if isinstance(value, tinycss2.ast.URLToken):
            yield value.value
        elif isinstance(value, tinycss2.ast.FunctionBlock):
            if value.lower_name in _URL_STRING_FUNCTIONS:
                yield from (
                    arg.value
                    for arg in value.arguments
                    if isinstance(arg, tinycss2.ast.StringToken)
                )
            yield from _urls(value.arguments)
        elif getattr(value, "content", None) is not None:
            yield from _urls(value.content)


def _find_css_violation(rules: list[Any]) -> str | None:
    """The first rule the css breaks, as a message, or None when it breaks none"""
    for rule in rules:
        if (
            isinstance(rule, tinycss2.ast.AtRule)
            and rule.lower_at_keyword in _FORBIDDEN_AT_RULES
        ):
            return f"may not use @{rule.lower_at_keyword}"
        if isinstance(rule, tinycss2.ast.Declaration) and rule.name.startswith("--"):
            return f"may not declare {rule.name}, tokens belong in the template tokens"
        values = getattr(rule, "prelude", None) or getattr(rule, "value", None) or []
        for url in _urls(values):
            if not _ASSET_URL.match(url):
                return f"may only use url(asset:<sha256>), not {url[:40]!r}"
        if getattr(rule, "content", None) is not None:
            nested = tinycss2.parse_blocks_contents(
                rule.content, skip_comments=True, skip_whitespace=True
            )
            if (violation := _find_css_violation(nested)) is not None:
                return violation
    return None


def check_template_html(html: str) -> None:
    """Refuse Mustache tags that read files or print unescaped html"""
    if _UNSAFE_TAG.search(html):
        raise RenderError(
            "template uses partials, delimiter changes or unescaped output"
        )


def check_template_css(css: str) -> None:
    """Refuse css that could set the page, load fonts or files, or declare tokens"""
    if _STYLE_END.search(css):
        raise RenderError("template css may not contain </style>")
    rules = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
    if (violation := _find_css_violation(rules)) is not None:
        raise RenderError(f"template css {violation}")


def check_rendered_body(body: str) -> None:
    """Refuse stylesheets the template added to the page, past the css checks"""
    if _STYLE_ELEMENT.search(body):
        raise RenderError(
            "template html may not add <style> or <link> elements,"
            " styles belong in the template css"
        )
