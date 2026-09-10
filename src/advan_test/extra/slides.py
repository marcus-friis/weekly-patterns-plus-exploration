"""Build a slideshow PDF from saved matplotlib figures using Typst.

Usage:
    python make_slideshow.py [--figures-dir DIR] [--output OUT.pdf] [--title TITLE]

Requires the `typst` CLI to be installed and on PATH:
    https://github.com/typst/typst#installation
    e.g.
      brew install typst
      cargo install --locked typst-cli
      winget install --id Typst.Typst
      uv tool install typst   (via the `typst-cli` PyPI wrapper, if you prefer)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from advan_test.utils import project_root

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".svg"}


def _title_from_stem(stem: str) -> str:
    """Turn 'plot_pois_by_dimension_region_10' into 'Plot Pois By Dimension Region 10'."""
    return stem.replace("_", " ").replace("-", " ").title()


def _escape_typst(text: str) -> str:
    # Typst treats certain characters specially inside content mode; escape the risky ones.
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("#", "\\#")


def build_typst_source(image_paths: list[Path], title: str) -> str:
    lines = [
        '#set page(width: 13.33in, height: 7.5in, margin: 1in, fill: rgb("#fafafa"))',
        '#set text(font: "Helvetica Neue", size: 20pt)',
        "",
        "#align(center + horizon)[",
        f'  #text(size: 40pt, weight: "bold")[{_escape_typst(title)}]',
        "]",
        "#pagebreak()",
        "",
    ]

    for path in image_paths:
        slide_title = _escape_typst(_title_from_stem(path.stem))
        # Typst resolves image paths relative to the .typ file's own directory,
        # so we generate the .typ file alongside the images and use bare filenames.
        rel_path = path.name
        # A grid with an `auto` title row and a `1fr` image row keeps both
        # on the same page: the image is constrained to whatever space is
        # left after the title, rather than overflowing onto the next page.
        lines.append(
            f'#grid(\n'
            f'  rows: (auto, 1fr),\n'
            f'  row-gutter: 0.4in,\n'
            f'  align(center)[= {slide_title}],\n'
            f'  align(center + horizon)[#image("{rel_path}", height: 100%, width: 100%, fit: "contain")],\n'
            f')'
        )
        lines.append("#pagebreak()")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=project_root() / "figures",
        help="Directory containing saved figure images (default: <project_root>/figures)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root() / "figures" / "slideshow.pdf",
        help="Output PDF path",
    )
    parser.add_argument(
        "--title",
        default="Weekly Patterns — Figures",
        help="Title slide text",
    )
    args = parser.parse_args()

    if shutil.which("typst") is None:
        sys.exit(
            "error: `typst` CLI not found on PATH.\n"
            "Install it first, e.g.:\n"
            "  brew install typst\n"
            "  cargo install --locked typst-cli\n"
            "  winget install --id Typst.Typst\n"
            "See https://github.com/typst/typst#installation"
        )

    if not args.figures_dir.is_dir():
        sys.exit(f"error: figures directory not found: {args.figures_dir}")

    images = sorted(
        p for p in args.figures_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTS
    )
    if not images:
        sys.exit(f"error: no images found in {args.figures_dir}")

    typ_source = build_typst_source(images, args.title)
    typ_path = args.figures_dir / "_slideshow.typ"
    typ_path.write_text(typ_source, encoding="utf-8")

    print(f"Wrote Typst source: {typ_path}")
    print(f"Found {len(images)} figure(s): {', '.join(p.name for p in images)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["typst", "compile", str(typ_path), str(args.output)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"typst compile failed:\n{result.stdout}\n{result.stderr}")

    print(f"Slideshow saved to: {args.output}")


if __name__ == "__main__":
    main()
