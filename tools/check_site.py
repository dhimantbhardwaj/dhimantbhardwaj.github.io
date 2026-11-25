"""Check the portfolio's local HTML references and sitemap."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.duplicate_ids: set[str] = set()
        self.references: list[tuple[str, str]] = []
        self.images_without_alt: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)

        for attribute in ("href", "src"):
            value = attributes.get(attribute)
            if value:
                self.references.append((attribute, value))

        if tag == "meta" and attributes.get("property") == "og:image":
            value = attributes.get("content")
            if value:
                self.references.append(("og:image", value))

        if tag == "img" and "alt" not in attributes:
            self.images_without_alt += 1


def main() -> int:
    errors: list[str] = []
    html_path = ROOT / "index.html"
    parser = SiteParser()
    parser.feed(html_path.read_text(encoding="utf-8"))

    for element_id in sorted(parser.duplicate_ids):
        errors.append(f"Duplicate id in index.html: #{element_id}")
    if parser.images_without_alt:
        errors.append(f"{parser.images_without_alt} image(s) are missing an alt attribute")

    checked_local_references = 0
    for attribute, value in parser.references:
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc:
            if parsed.netloc not in {"dhimantbhardwaj.me", "www.dhimantbhardwaj.me"}:
                continue
            site_path = unquote(parsed.path.lstrip("/"))
            relative_path = Path(site_path or "index.html")
            if site_path and parsed.path.endswith("/"):
                relative_path /= "index.html"
            target = ROOT / relative_path
            if not target.is_file():
                errors.append(f"Missing local {attribute}: {value}")
                continue
            checked_local_references += 1
            continue

        if parsed.path:
            site_path = unquote(parsed.path.lstrip("/"))
            relative_path = Path(site_path or "index.html")
            if site_path and parsed.path.endswith("/"):
                relative_path /= "index.html"
            target = ROOT / relative_path
            if not target.is_file():
                errors.append(f"Missing local {attribute}: {value}")
                continue
            checked_local_references += 1

        if parsed.fragment and unquote(parsed.fragment) not in parser.ids:
            errors.append(f"Missing in-page target: #{unquote(parsed.fragment)}")

    sitemap = ROOT / "sitemap.xml"
    try:
        ET.parse(sitemap)
    except ET.ParseError as error:
        errors.append(f"Invalid sitemap.xml: {error}")

    if errors:
        print("Site checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Site checks passed: {checked_local_references} local references, "
        f"{len(parser.ids)} unique ids, image alt text, and sitemap XML."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
