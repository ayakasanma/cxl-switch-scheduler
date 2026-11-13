"""Render the corrected CGOF hardware SVG to a vector PDF via headless Chrome.

Run from the repository root; the HTML/PDF intermediates stay in the ignored
.setup-logs/implementation/figure-v5-render-20261108/ directory.
"""

from pathlib import Path

import re


svg_path = Path("docs/final-report/generated/figures/improvement/cgof-hardware.svg")
out_dir = Path(".setup-logs/implementation/figure-v5-render-20261108")
out_dir.mkdir(parents=True, exist_ok=True)
svg = svg_path.read_text(encoding="utf-8")
match = re.search(r"<svg\b.*?</svg>", svg, re.S)
if not match:
    raise SystemExit("no <svg> element")
body = match.group(0)
html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
@page {{ size: 7.1in 3.75in; margin: 0; }}
html, body {{ margin: 0; padding: 0; width: 7.1in; height: 3.75in; overflow: hidden; background: white; }}
svg {{ width: 7.1in; height: 3.75in; display: block; }}
</style></head><body>
{body}
</body></html>
"""
(out_dir / "cgof-hardware.html").write_text(html, encoding="utf-8")
print(out_dir / "cgof-hardware.html")
