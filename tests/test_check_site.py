"""Regression tests for public-site course navigation validation."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check-site.py"
SPEC = importlib.util.spec_from_file_location("public_site_checker", CHECKER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load site checker at {CHECKER_PATH}")
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)

LESSONS = [
    ("0001-first.html", "Lesson 1 — First"),
    ("0002-middle.html", "Lesson 2 — Middle"),
    ("0003-last.html", "Lesson 3 — Last"),
]
CONTENTS = '<a href="../index.html#course-map">Course contents</a>'


class CourseNavigationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "lessons").mkdir()
        self.write_index()
        self.write_valid_lessons()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_index(self) -> None:
        entries = "\n".join(
            f'<li><a href="lessons/{filename}">{title}</a></li>'
            for filename, title in LESSONS
        )
        (self.root / "index.html").write_text(
            f'<h2 id="course-map">Lessons</h2><ol>{entries}</ol>', encoding="utf-8"
        )

    def write_valid_lessons(self) -> None:
        first, middle, last = [filename for filename, _ in LESSONS]
        pages = {
            first: (
                f'<nav class="nav" aria-label="Lesson navigation">{CONTENTS}'
                f'<a rel="next" href="{middle}">{LESSONS[1][1]} →</a></nav>'
            ),
            middle: (
                f'<nav class="nav" aria-label="Lesson navigation">'
                f'<a rel="prev" href="{first}">← Lesson 1</a>{CONTENTS}'
                f'<a rel="next" href="{last}">{LESSONS[2][1]} →</a></nav>'
            ),
            last: (
                f'<nav class="nav" aria-label="Lesson navigation">'
                f'<a rel="prev" href="{middle}">← Lesson 2</a>{CONTENTS}'
                '<span>End of currently published lessons</span></nav>'
            ),
        }
        for filename, html in pages.items():
            (self.root / "lessons" / filename).write_text(html, encoding="utf-8")

    def page(self, number: int) -> Path:
        return self.root / "lessons" / LESSONS[number - 1][0]

    def errors(self) -> list[str]:
        return checker.validate(self.root)

    def replace(self, path: Path, old: str, new: str) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_valid_site_passes(self) -> None:
        self.assertEqual([], self.errors())

    def test_missing_next_is_rejected(self) -> None:
        self.replace(
            self.page(1),
            f'<a rel="next" href="{LESSONS[1][0]}">{LESSONS[1][1]} →</a>',
            "",
        )
        self.assertTrue(any("rel=next must link" in error for error in self.errors()))

    def test_wrong_next_is_rejected(self) -> None:
        self.replace(
            self.page(1),
            f'href="{LESSONS[1][0]}"',
            f'href="{LESSONS[2][0]}"',
        )
        self.assertTrue(any("rel=next must link" in error for error in self.errors()))

    def test_missing_previous_is_rejected(self) -> None:
        self.replace(
            self.page(2),
            f'<a rel="prev" href="{LESSONS[0][0]}">← Lesson 1</a>',
            "",
        )
        self.assertTrue(any("rel=prev must link" in error for error in self.errors()))

    def test_missing_contents_link_is_rejected(self) -> None:
        self.replace(self.page(2), CONTENTS, "")
        self.assertTrue(
            any("Course contents link" in error for error in self.errors())
        )

    def test_missing_course_index_entry_is_rejected(self) -> None:
        self.replace(
            self.root / "index.html",
            f'<li><a href="lessons/{LESSONS[1][0]}">{LESSONS[1][1]}</a></li>',
            "",
        )
        self.assertTrue(any("course map must list" in error for error in self.errors()))

    def test_last_lesson_cannot_claim_a_next_module(self) -> None:
        self.replace(
            self.page(3),
            "<span>End of currently published lessons</span>",
            '<a rel="next" href="../index.html#course-map">Module E next →</a>',
        )
        self.assertTrue(
            any("misleading Module E next" in error for error in self.errors())
        )

    def test_numbered_lesson_sequence_must_be_contiguous(self) -> None:
        lesson_dir = self.root / "lessons"
        (lesson_dir / LESSONS[1][0]).rename(lesson_dir / "0004-middle.html")
        self.assertTrue(any("not contiguous" in error for error in self.errors()))


if __name__ == "__main__":
    unittest.main()
