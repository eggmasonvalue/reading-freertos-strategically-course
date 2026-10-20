#!/usr/bin/env python3
"""Validate the already-built, public static site without rewriting it.

Run from any directory with ``python scripts/check-site.py``. This is a
validator, not a renderer: citation links and line-numbered source views are
checked in place and are never regenerated.
"""
from __future__ import annotations

import argparse
import os
import posixpath
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, unquote, urlsplit

SITE_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT_FILES = {
    ".source-commit",  # identifies the private authoring-workspace revision
    "COURSEWARE-STANDARD.md",
    "MISSION.md",
    "NOTES.md",
    "RESOURCES.md",
    "ROADMAP.md",
}
PRIVATE_PATH_COMPONENTS = {
    ".agents",
    ".pi",
    "learning-records",
    "private-prompts",
    "teacher-prompts",
}
PROMPT_CLASSES = {"private-prompt", "teacher-prompt", "author-only"}
PRIVATE_META_NAMES = {
    "authoring-workspace",
    "private-prompt",
    "source-commit",
    "teacher-prompt",
}
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
LINK_ATTRIBUTES = {"href", "src", "poster", "action", "data"}


@dataclass
class Citation:
    source: str | None
    lines: str | None
    hrefs: list[str] = field(default_factory=list)


@dataclass
class ParsedPage:
    links: list[tuple[str, str]] = field(default_factory=list)
    ids: set[str] = field(default_factory=set)
    citations: list[Citation] = field(default_factory=list)
    has_untransformed_source_ref: bool = False
    privacy_errors: list[str] = field(default_factory=list)


class PageParser(HTMLParser):
    """Collect local links, fragment identifiers, and citation metadata."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = ParsedPage()
        self.stack: list[tuple[str, Citation | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, push=True)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, push=False)

    def _start(
        self, tag: str, attrs: list[tuple[str, str | None]], *, push: bool
    ) -> None:
        attributes = {name.lower(): value or "" for name, value in attrs}
        classes = set(attributes.get("class", "").split())

        for name in ("id", "name"):
            if attributes.get(name):
                self.page.ids.add(attributes[name])

        for name in LINK_ATTRIBUTES:
            value = attributes.get(name)
            if value:
                self.page.links.append((name, value))

        if tag.lower() == "meta":
            meta_name = (attributes.get("name") or attributes.get("property") or "").lower()
            if meta_name in PRIVATE_META_NAMES:
                self.page.privacy_errors.append(f"private metadata field {meta_name!r}")

        if "data-private" in attributes or "data-teacher-prompt" in attributes:
            self.page.privacy_errors.append("private/prompt marker attribute")
        if classes & PROMPT_CLASSES:
            self.page.privacy_errors.append(
                f"private/prompt marker class {sorted(classes & PROMPT_CLASSES)!r}"
            )
        if tag.lower() == "div" and "ask" in classes:
            self.page.privacy_errors.append("unremoved teacher prompt <div class=ask>")
        if "source-ref" in classes and tag.lower() == "span":
            self.page.has_untransformed_source_ref = True

        active_citation = next(
            (citation for _, citation in reversed(self.stack) if citation is not None),
            None,
        )
        citation = active_citation
        if tag.lower() == "p" and "filecite" in classes:
            citation = Citation(
                attributes.get("data-source"), attributes.get("data-lines")
            )
            self.page.citations.append(citation)
        elif tag.lower() == "a" and citation is not None and "code-ref" in classes:
            href = attributes.get("href")
            if href:
                citation.hrefs.append(href)

        if push and tag.lower() not in VOID_ELEMENTS:
            self.stack.append((tag.lower(), citation if citation is not active_citation else None))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def html_files(root: Path) -> list[Path]:
    """Return site HTML pages, excluding Git's internal object database."""
    paths: list[Path] = []
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories[:] = sorted(name for name in subdirectories if name != ".git")
        base = Path(directory)
        paths.extend(base / name for name in filenames if name.lower().endswith(".html"))
    return sorted(paths)


def site_paths(root: Path):
    """Yield all paths except Git's internal metadata."""
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories[:] = sorted(name for name in subdirectories if name != ".git")
        base = Path(directory)
        for name in filenames:
            if name != ".git":
                yield base / name
        for name in subdirectories:
            yield base / name


def parse_page(path: Path, cache: dict[Path, ParsedPage], errors: list[str]) -> ParsedPage | None:
    if path in cache:
        return cache[path]
    try:
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
    except (OSError, UnicodeError) as error:
        errors.append(f"cannot read HTML {path}: {error}")
        return None
    cache[path] = parser.page
    return parser.page


def parse_line_spec(spec: str, line_count: int, source: str) -> tuple[int, ...]:
    starts: list[int] = []
    parts = spec.split(",")
    if not spec.strip() or not parts:
        raise ValueError(f"empty line range for {source}")
    for part in parts:
        match = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", part)
        if not match:
            raise ValueError(f"invalid line range {spec!r} for {source}")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < start or end > line_count:
            raise ValueError(
                f"line range {spec!r} is outside {source} (1-{line_count})"
            )
        starts.append(start)
    return tuple(starts)


def read_source_lines(source: Path, relative: str, errors: list[str]) -> int | None:
    try:
        return len(source.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeError) as error:
        errors.append(f"cannot read citation source {relative}: {error}")
        return None


def source_path(root: Path, relative: str) -> Path:
    """Resolve a citation only within the public reference/ source tree."""
    posix = PurePosixPath(relative)
    if not relative or posix.is_absolute() or "\\" in relative or ".." in posix.parts:
        raise ValueError(f"unsafe citation source path {relative!r}")
    base = root / "reference"
    source = base.joinpath(*posix.parts)
    try:
        source.resolve().relative_to(base.resolve())
    except ValueError as error:
        raise ValueError(f"citation source escapes reference/: {relative!r}") from error
    return source


def check_citation(
    root: Path,
    page_path: Path,
    citation: Citation,
    errors: list[str],
) -> None:
    relative_page = page_path.relative_to(root).as_posix()
    if not citation.source or not citation.lines:
        errors.append(f"{relative_page}: filecite is missing data-source or data-lines")
        return
    try:
        source = source_path(root, citation.source)
    except ValueError as error:
        errors.append(f"{relative_page}: {error}")
        return
    if not source.is_file():
        errors.append(f"{relative_page}: citation source does not exist: {citation.source}")
        return

    line_count = read_source_lines(source, citation.source, errors)
    if line_count is None:
        return
    try:
        starts = parse_line_spec(citation.lines, line_count, citation.source)
    except ValueError as error:
        errors.append(f"{relative_page}: {error}")
        return

    viewer = root / "reference-source" / f"{citation.source}.html"
    if not viewer.is_file():
        errors.append(
            f"{relative_page}: missing prebuilt source view for citation {citation.source}"
        )
    if not citation.hrefs:
        errors.append(f"{relative_page}: citation has no transformed code-ref link")
        return

    matched = False
    for href in citation.hrefs:
        parts = urlsplit(href)
        query_lines = parse_qs(parts.query, keep_blank_values=True).get("lines", [])
        if (
            parts.scheme
            or parts.netloc
            or len(query_lines) != 1
            or query_lines[0] != citation.lines
        ):
            continue
        target_text = unquote(parts.path)
        if target_text.startswith("/"):
            target = root.joinpath(*PurePosixPath(target_text.lstrip("/")).parts)
        else:
            rel_parent = page_path.parent.relative_to(root).as_posix()
            target_rel = posixpath.normpath(posixpath.join(rel_parent, target_text))
            if target_rel == ".." or target_rel.startswith("../"):
                continue
            target = root.joinpath(*PurePosixPath(target_rel).parts)
        if target.resolve() == viewer.resolve() and parts.fragment == f"L{starts[0]}":
            matched = True
            break
    if not matched:
        errors.append(
            f"{relative_page}: citation link does not match {citation.source} lines {citation.lines}"
        )


def resolve_local_target(
    root: Path, page_path: Path, raw_url: str
) -> tuple[Path | None, str, str | None]:
    """Return (target, fragment, error); None target means an external URL."""
    parts = urlsplit(raw_url)
    if parts.scheme or parts.netloc:
        return None, parts.fragment, None
    decoded_path = unquote(parts.path)
    if "\\" in decoded_path:
        return None, parts.fragment, f"backslash in local URL {raw_url!r}"
    if decoded_path.startswith("/"):
        relative = decoded_path.lstrip("/")
    elif decoded_path:
        relative = posixpath.join(page_path.parent.relative_to(root).as_posix(), decoded_path)
    else:
        relative = page_path.relative_to(root).as_posix()
    normalized = posixpath.normpath(relative)
    if normalized in {"", "."}:
        normalized = "index.html"
    if normalized == ".." or normalized.startswith("../"):
        return None, parts.fragment, f"local URL escapes site root: {raw_url!r}"
    target = root.joinpath(*PurePosixPath(normalized).parts)
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError:
        return None, parts.fragment, f"local URL resolves outside site root: {raw_url!r}"
    if target.is_dir():
        target = target / "index.html"
    return target, parts.fragment, None


def check_privacy(root: Path, errors: list[str]) -> None:
    for path in site_paths(root):
        relative = path.relative_to(root)
        parts = relative.parts
        if parts and parts[0] in PRIVATE_ROOT_FILES:
            errors.append(f"private authoring metadata published: {relative.as_posix()}")
        forbidden = PRIVATE_PATH_COMPONENTS.intersection(parts)
        if forbidden:
            errors.append(
                f"private authoring path published: {relative.as_posix()} "
                f"({', '.join(sorted(forbidden))})"
            )


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    if not root.is_dir():
        return [f"site root is not a directory: {root}"]
    check_privacy(root, errors)
    parsed: dict[Path, ParsedPage] = {}
    pages = html_files(root)

    for page_path in pages:
        page = parse_page(page_path, parsed, errors)
        if page is None:
            continue
        relative_page = page_path.relative_to(root).as_posix()
        for message in page.privacy_errors:
            errors.append(f"{relative_page}: {message}")
        if page.has_untransformed_source_ref:
            errors.append(f"{relative_page}: untransformed span.source-ref citation")

        for citation in page.citations:
            check_citation(root, page_path, citation, errors)

        for attribute, raw_url in page.links:
            target, fragment, link_error = resolve_local_target(root, page_path, raw_url)
            if link_error:
                errors.append(f"{relative_page}: {attribute}={raw_url!r}: {link_error}")
                continue
            if target is None:
                continue
            if not target.exists():
                errors.append(f"{relative_page}: broken local {attribute}={raw_url!r}")
                continue

            parts = urlsplit(raw_url)
            line_specs = parse_qs(parts.query, keep_blank_values=True).get("lines")
            if line_specs is not None:
                viewer_root = root / "reference-source"
                try:
                    viewer_relative = target.resolve().relative_to(viewer_root.resolve()).as_posix()
                except ValueError:
                    errors.append(
                        f"{relative_page}: lines query does not target reference-source/: {raw_url!r}"
                    )
                else:
                    if len(line_specs) != 1 or not viewer_relative.endswith(".html"):
                        errors.append(f"{relative_page}: invalid source-view query: {raw_url!r}")
                    else:
                        source_relative = viewer_relative[:-5]
                        try:
                            source = source_path(root, source_relative)
                            if not source.is_file():
                                raise ValueError(f"missing reference/{source_relative}")
                            line_count = read_source_lines(source, source_relative, errors)
                            if line_count is not None:
                                starts = parse_line_spec(line_specs[0], line_count, source_relative)
                                if fragment != f"L{starts[0]}":
                                    errors.append(
                                        f"{relative_page}: source-view fragment does not match lines query: {raw_url!r}"
                                    )
                        except ValueError as error:
                            errors.append(f"{relative_page}: {error}")

            if fragment and target.suffix.lower() == ".html":
                target_page = parse_page(target, parsed, errors)
                if target_page is not None and unquote(fragment) not in target_page.ids:
                    errors.append(
                        f"{relative_page}: missing fragment #{fragment} in "
                        f"{target.relative_to(root).as_posix()}"
                    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=SITE_ROOT,
        help="site root to validate (defaults to this script's parent directory)",
    )
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Site validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"Site validation passed ({len(html_files(args.root.resolve()))} HTML pages checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
