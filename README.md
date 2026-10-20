# Reading FreeRTOS Strategically

A self-paced course in **strategic programming judgment**, using the FreeRTOS kernel as a reading specimen. The lessons teach you to look at code, APIs, types, and boundaries and explain precisely why an abstraction is strong or weak.

**Start learning:** [open the course](https://eggmasonvalue.github.io/reading-freertos-strategically-course/)

## What is here

- **19 self-contained lessons** with retrieval quizzes, from tactical vs. strategic programming through consistency and obvious code.
- **A reference shelf** with the glossary, connascence cheat sheet, API review checklist, and pinned FreeRTOS Kernel and Kernel Book snapshots.
- **Line-numbered source views** so lesson citations open at the exact code they discuss.
- **A responsive reading experience** with a dark theme that follows your operating system or browser preference, plus a light/dark toggle that remembers your choice.

You can read the course online, or clone this repository and open `index.html` locally. The site is plain static HTML, CSS, and JavaScript; no build step is needed to browse it.

## Provenance and licensing

The original course code is licensed under the [MIT License](LICENSE). The original lessons, explanations, examples, and other educational prose are licensed under [CC BY 4.0](LICENSE-CONTENT). Please preserve attribution when reusing or adapting them.

The pinned upstream snapshots and their licenses are retained under [`reference/`](reference/). See [`reference/PROVENANCE.md`](reference/PROVENANCE.md) for the upstream repositories, exact commits, and snapshot rationale. Third-party material remains under its own license.

## Maintaining the site

This repository is the source of truth for the published site. Edit the static pages in `lessons/`, shared files in `assets/`, and the pinned source material in `reference/` and `reference-source/` directly. Citation links and line-numbered source views are already part of the static pages; do not run a private-workspace generator to rebuild them.

The site is plain static HTML, CSS, and JavaScript. Validate local links, citation line bounds, and public-content hygiene with the standard-library-only checker:

```sh
python scripts/check-site.py
```

GitHub Actions runs this check on pushes and pull requests. Hosting remains the existing GitHub Pages deployment from the `main` branch root; the workflow validates the checked-in site and does not build or deploy it.
