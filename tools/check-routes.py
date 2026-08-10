#!/usr/bin/env python3
"""Assert that this repository serves every path its SiteSkin manifest names.

The manifest is already guarded two ways: a checksum pins it byte-for-byte against the conformance
fixture in denrzv/webora, and that repository's test suite proves it validates and that every URL
in it resolves inside the serving origin. Neither guard knows whether the paths those URLs resolve
*to* exist. A manifest whose Catalog tab leads to a 404 passes both.

So this is the third guard, and the only one that can see the filesystem. It runs offline, with no
network and no cross-repository checkout, which is what lets it be a required check rather than an
advisory one.

Every checked path is derived from the manifest and the filesystem. There is deliberately no list
of expected routes in this file: a hand-maintained list is the same assertion the corpus already
fails to make, restated somewhere it can rot quietly. Renaming `catalog/index.html` must fail this
check, and it does so because nothing here mentions the catalog.

Usage: python3 tools/check-routes.py [repo-root]
Exit 0 when the site and its manifest agree; exit 1 with one line per disagreement.
"""

import json
import struct
import sys
from pathlib import Path

MANIFEST = Path(".well-known/siteskin.json")

# NET-003, the browser's decode budget for a brand asset. Duplicated here as the numbers a site
# owner must respect rather than as an import, because this repository has no dependency on the
# browser and gains nothing by growing one.
MAX_LOGO_BYTES = 512 * 1024
MAX_AXIS_PIXELS = 1024
MAX_TOTAL_PIXELS = 1_048_576

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def manifest_paths(manifest):
    """Every origin-relative path the manifest names, as (json-pointer, path) pairs.

    `match` patterns contribute their literal prefix -- the part before the first glob token. A
    pattern is a description of many URLs and cannot be resolved to one file, but its literal
    prefix is a route the site had better serve, or the item is describing pages that do not exist.
    """
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
    """The file a static host would serve for `path`, or None.

    Mirrors the directory layout this site is built for: `/catalog` and `/catalog/` are both served
    by `catalog/index.html`, because a static host redirects the first spelling to the second. A
    layout of flat `catalog.html` files would resolve on GitHub Pages and 404 under
    `python3 -m http.server`, which is why it is not the layout here.
    """
    relative = path.lstrip("/")
    if relative in ("", "/"):
        candidates = [root / "index.html"]
    else:
        base = root / relative
        candidates = [base, base / "index.html"]

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def png_dimensions(data):
    """Width and height from an 8-byte-signature PNG's IHDR, or None if this is not a PNG."""
    if not data.startswith(PNG_SIGNATURE) or len(data) < 24 or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def check_logo(root, url, failures):
    """The browser refuses a brand asset outside NET-003's budget, so refuse it here first."""
    path = served_file(root, url)
    if path is None:
        return  # already reported as a missing route

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


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    manifest_file = root / MANIFEST
    if not manifest_file.is_file():
        print(f"[routes] no manifest at {MANIFEST}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    paths = manifest_paths(manifest)
    failures = []

    # A manifest that named nothing would pass every assertion below without checking anything.
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

    logo = manifest.get("branding", {}).get("logoUrl")
    if logo:
        check_logo(root, logo, failures)

    if failures:
        print(f"[routes] {len(failures)} problem(s):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"[routes] OK -- {len(paths)} manifest path(s) all resolve to served files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
