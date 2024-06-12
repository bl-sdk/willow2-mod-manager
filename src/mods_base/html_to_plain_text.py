# ruff: noqa: D102

from dataclasses import dataclass
from functools import cache
from html.parser import HTMLParser


@dataclass
class OrderedList:
    num: int = 1


@dataclass
class UnorderedList:
    pass


class PlainTextHTMLConverter(HTMLParser):
    plain_text: str
    list_item_stack: list[OrderedList | UnorderedList]

    def __init__(self) -> None:
        super().__init__()

        self.plain_text = ""
        self.list_item_stack = []

    def handle_data(self, data: str) -> None:
        self.plain_text += data

    def handle_starttag(  # noqa: C901 - imo the match is rated too highly
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        match tag.lower():
            case "br":
                self.plain_text += "\n"

            case "ol":
                self.plain_text += "\n"
                self.list_item_stack.append(OrderedList())

            case "ul":
                self.plain_text += "\n"
                self.list_item_stack.append(UnorderedList())

            case "li":
                if len(self.list_item_stack) >= 1:
                    list_state = self.list_item_stack[-1]
                    match list_state:
                        case OrderedList():
                            self.plain_text += f"{list_state.num}. "
                            list_state.num += 1
                        case UnorderedList():
                            self.plain_text += "- "

            case "img":
                for name, val in attrs:
                    if name.lower() == "alt" and val is not None:
                        self.plain_text += val
                        break

            case _:
                pass

    def handle_endtag(self, tag: str) -> None:
        match tag.lower():
            case "ol":
                if isinstance(self.list_item_stack[-1], OrderedList):
                    self.list_item_stack.pop()

            case "ul":
                if isinstance(self.list_item_stack[-1], UnorderedList):
                    self.list_item_stack.pop()

            case "li":
                self.plain_text += "\n"

            case _:
                pass


@cache
def html_to_plain_text(html: str) -> str:
    """
    Extracts plain text from HTML-containing text. This is *NOT* input sanitisation.

    Removes most tags in place, and decodes entities - `<b>&amp;</b>` becomes `&`.

    A few tags are substituted for plain text equivalents:
    - `<br>` becomes a newline
    - `<ol><li>` becomes `1. ` (incrementing with each list item)
    - `<ul><li>` becomes `- `
    - `<img alt='xyz'>` becomes it's alt text

    Intended for use when accessing a mod name/description/option/etc., which may contain HTML tags,
    but in a situation where such tags would be inappropriate.

    Args:
        html: The HTML-containing text.
    Returns:
        The extracted plain text.
    """
    parser = PlainTextHTMLConverter()
    parser.feed(html)
    return parser.plain_text
