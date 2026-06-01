#!/usr/bin/env python3
"""Scaffold a new OpenKT demo: a directory with the design-system assets and a
ready-to-edit index.html based on the template.

Usage:
  python3 new_demo.py /tmp/my-demo --title "My Demo"
  python3 new_demo.py ./reports/q3-review            # title defaults to the dir name

Then: edit index.html, preview with the make-pages-interactive skill, and run
scripts/publish.py index.html when you're ready to ship a static version.
"""
import argparse
import shutil
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FILES = ["openkt-pages.css", "openkt-demo.css", "openkt-demo.js"]

def main():
    ap = argparse.ArgumentParser(description="Scaffold a new OpenKT demo directory.")
    ap.add_argument("target", help="directory to create the demo in")
    ap.add_argument("--title", help="demo title (default: directory name, title-cased)")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    title = args.title or target.name.replace("-", " ").replace("_", " ").title()

    for f in FILES:
        shutil.copy(ASSETS / f, target / f)

    html = (ASSETS / "template.html").read_text(encoding="utf-8")
    html = html.replace("DEMO TITLE — OpenKT", f"{title} — OpenKT").replace("Demo title", title)
    (target / "index.html").write_text(html, encoding="utf-8")

    print(f"scaffolded demo: {target}")
    print("  index.html + openkt-pages.css + openkt-demo.css + openkt-demo.js")
    print("next:")
    print(f"  1. edit {target / 'index.html'}")
    print(f"  2. preview: invoke the make-pages-interactive skill on {target}")
    print(f"  3. publish: python3 {Path(__file__).name} … then publish.py index.html")

if __name__ == "__main__":
    main()
