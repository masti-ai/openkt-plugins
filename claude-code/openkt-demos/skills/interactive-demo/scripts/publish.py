#!/usr/bin/env python3
"""Static export: turn an interactive OpenKT demo into ONE self-contained .html
fit for public hosting (your website, a blog, a gist).

What it does:
  - inlines local <link rel="stylesheet" href="*.css"> into <style> blocks
  - inlines local <script src="*.js"></script> into inline <script> blocks
  - strips the make-pages-interactive feedback tags (/lib/feedback.css|js) so the
    page has no dependency on the local comment server
  - LEAVES remote assets (https://… CDN, e.g. vis-network) untouched — they load
    fine from any host. Pass --vendor to download them inline for offline pages.

Usage:
  python3 publish.py path/to/demo/index.html                 # -> index.static.html beside it
  python3 publish.py path/to/demo/index.html -o out/demo.html
  python3 publish.py path/to/demo/index.html --vendor         # also inline remote CDN scripts
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.request import urlopen

FEEDBACK_LINK = re.compile(r'[ \t]*<link[^>]+/lib/feedback\.css[^>]*>\s*', re.I)
FEEDBACK_SCRIPT = re.compile(r'[ \t]*<script[^>]+/lib/feedback\.js[^>]*>\s*</script>\s*', re.I)
LINK_CSS = re.compile(r'<link\b[^>]*\brel=["\']stylesheet["\'][^>]*\bhref=["\']([^"\']+)["\'][^>]*>', re.I)
LINK_CSS2 = re.compile(r'<link\b[^>]*\bhref=["\']([^"\']+\.css)["\'][^>]*\brel=["\']stylesheet["\'][^>]*>', re.I)
SCRIPT_SRC = re.compile(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*>\s*</script>', re.I)

def is_remote(url: str) -> bool:
    return url.startswith(("http://", "https://", "//"))

def inline_css(html: str, base: Path) -> str:
    def repl(m):
        href = m.group(1)
        if is_remote(href):
            return m.group(0)
        f = (base / href).resolve()
        if not f.exists():
            print(f"  ! css not found, leaving as-is: {href}", file=sys.stderr)
            return m.group(0)
        return f"<style>/* {href} */\n{f.read_text(encoding='utf-8')}\n</style>"
    html = LINK_CSS.sub(repl, html)
    html = LINK_CSS2.sub(repl, html)
    return html

def inline_js(html: str, base: Path, vendor: bool) -> str:
    def repl(m):
        src = m.group(1)
        if is_remote(src):
            if not vendor:
                return m.group(0)
            try:
                body = urlopen(src, timeout=30).read().decode("utf-8")
                print(f"  · vendored {src}")
                return f"<script>/* vendored {src} */\n{body}\n</script>"
            except Exception as e:
                print(f"  ! vendor failed ({e}); leaving CDN ref: {src}", file=sys.stderr)
                return m.group(0)
        f = (base / src).resolve()
        if not f.exists():
            print(f"  ! js not found, leaving as-is: {src}", file=sys.stderr)
            return m.group(0)
        return f"<script>/* {src} */\n{f.read_text(encoding='utf-8')}\n</script>"
    return SCRIPT_SRC.sub(repl, html)

def main():
    ap = argparse.ArgumentParser(description="Static export an OpenKT demo to one self-contained HTML file.")
    ap.add_argument("html", help="path to the demo's index.html")
    ap.add_argument("-o", "--out", help="output path (default: <name>.static.html beside the input)")
    ap.add_argument("--vendor", action="store_true", help="also inline remote CDN scripts (offline-safe, larger file)")
    args = ap.parse_args()

    src = Path(args.html).resolve()
    if not src.exists():
        sys.exit(f"no such file: {src}")
    base = src.parent
    html = src.read_text(encoding="utf-8")

    html = FEEDBACK_LINK.sub("", html)
    html = FEEDBACK_SCRIPT.sub("", html)
    html = inline_css(html, base)
    html = inline_js(html, base, args.vendor)

    out = Path(args.out).resolve() if args.out else src.with_suffix(".static.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) / 1024
    print(f"wrote {out}  ({kb:.0f} KB, self-contained)")

if __name__ == "__main__":
    main()
