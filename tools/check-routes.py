#!/usr/bin/env python3
"""Assert that the static site serves its SiteSkin routes and local HTML references.

The manifest is guarded by a canonical checksum and by Webora's validator, but neither can prove
that every route or asset actually exists in this repository. This offline guard checks two layers:

1. every origin-relative route/asset named by `.well-known/siteskin.json`;
2. every same-origin `href`/`src` reference discovered in the site's HTML files.

The second layer matters for ordinary web journeys that are intentionally outside the SiteSkin
manifest, such as `/catalog/happy-days/`: if the page, a stylesheet, or one of its local bouquet
images disappears, CI should fail instead of letting a broken demo deploy. Linked WebP assets are
also checked as RIFF containers so a truncated binary cannot pass merely because the path exists.

Usage: python3 tools/check-routes.py [repo-root]
Exit 0 when the manifest and local HTML references all resolve; exit 1 otherwise.
"""

import json
import posixpath
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

MANIFEST = Path(".well-known/siteskin.json")

# NET-003, the browser's decode budget for a brand asset. Duplicated here as the numbers a site
# owner must respect rather than as an import, because this repository has no dependency on Webora.
MAX_LOGO_BYTES = 512 * 1024
MAX_AXIS_PIXELS = 1024
MAX_TOTAL_PIXELS = 1_048_576

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
WEBP_RIFF = b"RIFF"
WEBP_SIGNATURE = b"WEBP"


class LocalReferenceParser(HTMLParser):
    """Collect local navigation/resource attributes without executing any page code."""

    ATTRIBUTES = {
        "a": "href",
        "img": "src",
        "link": "href",
        "script": "src",
        "source": "src",
    }

    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        wanted = self.ATTRIBUTES.get(tag)
        if wanted is None:
            return
        for name, value in attrs:
            if name == wanted and value:
                self.references.append(value)


def manifest_paths(manifest):
    """Every origin-relative path the manifest names, as (json-pointer, path) pairs."""
    found = []

    site = manifest.get("site", {})
    if "homeUrl" in site:
        found.append(("/site/homeUrl", site["homeUrl"]))

    branding = manifest.get("branding", {})
    if "logoUrl" in branding:
        found.append(("/branding/logoUrl", branding["logoUrl"]))

    for collection in ("bottomNavigation", "menu", "quickActions"):
        for index, item in enumerate(manifest.get(collection, [])):
            pointer = f"/{collection}/{index}"
            action = item.get("action", {})
            if action.get("type") == "internal_url" and "url" in action:
                found.append((f"{pointer}/action/url", action["url"]))
            for match_index, pattern in enumerate(item.get("match", [])):
                literal = pattern.split("*", 1)[0]
                found.append((f"{pointer}/match/{match_index}", literal))

    return found


def served_file(root, path):
    """The file a static host would serve for an origin-relative path, or None."""
    relative = path.lstrip("/")
    if not relative:
        candidates = [root / "index.html"]
    else:
        base = root / relative
        candidates = [base, base / "index.html"]

    for candidate in candidates:
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            continue
        if resolved.is_file():
            return resolved
    return None


def page_route(root, html_file):
    """Return the origin path that corresponds to one HTML file in the static layout."""
    relative = html_file.relative_to(root).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + relative[: -len("index.html")]
    return "/" + relative


def resolve_local_reference(base_route, raw_reference):
    """Resolve an HTML href/src to an origin path, or None for external/non-file references."""
    parsed = urlsplit(raw_reference)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None

    if parsed.path.startswith("/"):
        return parsed.path

    base_directory = base_route if base_route.endswith("/") else posixpath.dirname(base_route) + "/"
    resolved = posixpath.normpath(posixpath.join(base_directory, parsed.path))
    if not resolved.startswith("/"):
        resolved = "/" + resolved
    return resolved


def html_references(root):
    """Yield (source-file, raw-reference, resolved-origin-path) for same-origin HTML links/assets."""
    for html_file in sorted(root.rglob("*.html")):
        # `.git` is never expected under a normal checkout, but keep repository metadata out if this
        # script is pointed at an unusual worktree layout.
        if ".git" in html_file.parts:
            continue

        parser = LocalReferenceParser()
        parser.feed(html_file.read_text(encoding="utf-8"))
        route = page_route(root, html_file)
        for reference in parser.references:
            resolved = resolve_local_reference(route, reference)
            if resolved is not None:
                yield html_file.relative_to(root).as_posix(), reference, resolved


def png_dimensions(data):
    """Width and height from an 8-byte-signature PNG's IHDR, or None if this is not a PNG."""
    if not data.startswith(PNG_SIGNATURE) or len(data) < 24 or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def check_logo(root, url, failures):
    """The browser refuses a brand asset outside NET-003's budget, so refuse it here first."""
    path = served_file(root, url)
    if path is None:
        return

    data = path.read_bytes()
    dimensions = png_dimensions(data)

    if dimensions is None:
        failures.append(
            f"{url}: not a PNG -- the declared logo must carry the PNG signature in its bytes, "
            "since the browser checks the signature and not the file extension"
        )
        return

    width, height = dimensions
    if len(data) > MAX_LOGO_BYTES:
        failures.append(f"{url}: {len(data)} bytes exceeds the {MAX_LOGO_BYTES}-byte budget")
    if width > MAX_AXIS_PIXELS or height > MAX_AXIS_PIXELS:
        failures.append(f"{url}: {width}x{height} exceeds {MAX_AXIS_PIXELS} pixels per axis")
    if width * height > MAX_TOTAL_PIXELS:
        failures.append(f"{url}: {width * height} pixels exceeds the {MAX_TOTAL_PIXELS}-pixel budget")


def check_webp(path, display_path, failures):
    """Reject a linked WebP whose RIFF size or chunk layout proves the binary is truncated."""
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != WEBP_RIFF or data[8:12] != WEBP_SIGNATURE:
        failures.append(f"{display_path}: not a WebP RIFF container")
        return

    declared_size = int.from_bytes(data[4:8], "little") + 8
    if declared_size != len(data):
        failures.append(
            f"{display_path}: WebP RIFF declares {declared_size} bytes but file has {len(data)} bytes"
        )
        return

    position = 12
    while position < len(data):
        if position + 8 > len(data):
            failures.append(f"{display_path}: truncated WebP chunk header at byte {position}")
            return

        chunk_size = int.from_bytes(data[position + 4 : position + 8], "little")
        position += 8
        chunk_end = position + chunk_size
        if chunk_end > len(data):
            failures.append(
                f"{display_path}: WebP chunk overruns the file by {chunk_end - len(data)} byte(s)"
            )
            return
        position = chunk_end + (chunk_size & 1)

    if position != len(data):
        failures.append(f"{display_path}: malformed WebP RIFF padding/chunk layout")


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    manifest_file = root / MANIFEST
    if not manifest_file.is_file():
        print(f"[routes] no manifest at {MANIFEST}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    paths = manifest_paths(manifest)
    failures = []

    if not paths:
        print("[routes] the manifest names no paths -- nothing was checked", file=sys.stderr)
        return 1

    for pointer, path in paths:
        if not path.startswith("/"):
            failures.append(
                f"{pointer}: `{path}` is not origin-relative -- this check only understands the "
                "paths this repository serves"
            )
            continue
        if served_file(root, path) is None:
            failures.append(f"{pointer}: `{path}` is named by the manifest and served by no file")

    references = list(html_references(root))
    checked_webps = set()
    for source, raw_reference, resolved in references:
        local_file = served_file(root, resolved)
        if local_file is None:
            failures.append(
                f"{source}: `{raw_reference}` resolves to `{resolved}`, which is served by no file"
            )
            continue

        if local_file.suffix.lower() == ".webp" and local_file not in checked_webps:
            check_webp(local_file, resolved, failures)
            checked_webps.add(local_file)

    logo = manifest.get("branding", {}).get("logoUrl")
    if logo:
        check_logo(root, logo, failures)

    if failures:
        print(f"[routes] {len(failures)} problem(s):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    unique_references = len({resolved for _, _, resolved in references})
    print(
        f"[routes] OK -- {len(paths)} manifest path(s) and "
        f"{unique_references} linked local route/asset path(s) resolve; "
        f"{len(checked_webps)} linked WebP asset(s) pass RIFF integrity checks"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
