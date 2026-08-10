#!/usr/bin/env python3
"""Build both outputs from the shared body template.

artifact  : body only. The artifact host injects the document wrapper.
site      : a complete, valid HTML document for GitHub Pages, which injects nothing.
"""
import html, json, pathlib, re, sys

ROOT = pathlib.Path("/Users/mlvpatel/Downloads/enen project")
REPO = ROOT / "open-weight-agent-stack"
HERE = pathlib.Path(__file__).parent  # scripts/ holds the body template alongside this builder

SITE_URL = "https://mlvpatel.github.io/open-weight-agent-stack/"
DESCRIPTION = ("A performance-first build manual for agentic AI on open-weight models: hardware and "
               "serving, retrieval, memory, identity, security, and operations.")

def build():
    body = (HERE / "artifact2.html").read_text()
    theme = json.loads((REPO / "assets" / "mermaid-theme.json").read_text())
    init = "%%{init: " + json.dumps(theme, separators=(",", ":")) + "}%%\n"
    manual = (REPO / "MANUAL.md").read_text()
    blocks = re.findall(r"```mermaid\n(.*?)```", manual, re.S)
    if len(blocks) != 18:
        sys.exit(f"expected 18 mermaid blocks, found {len(blocks)}")

    out = body
    for ph in list(range(16)) + [17]:
        tag = f"<!--DIAGRAM:{ph}-->"
        if tag not in out:
            sys.exit(f"missing placeholder {tag}")
        out = out.replace(tag, f'<pre class="mermaid">{html.escape(init + blocks[ph], quote=False)}</pre>')
    if re.search(r"<!--DIAGRAM:\d+-->", out):
        sys.exit("unfilled diagram placeholder remains")

    (ROOT / "ai-agent-architecture-page.html").write_text(out)

    title = "The Open-Weight Agent Stack, Build Manual"

    # title and style must live in <head>; pull them out of the body template
    out = re.sub(r"<title>.*?</title>\s*", "", out, count=1, flags=re.S)
    style = ""
    m = re.search(r"<style>.*?</style>", out, re.S)
    if m:
        style = m.group(0)
        out = out[:m.start()] + out[m.end():]
    out = re.sub(r"[ \t]+$", "", out, flags=re.M)

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{DESCRIPTION}">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:image" content="{SITE_URL}preview.png">
<meta name="twitter:card" content="summary_large_image">
{style}\n<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14' font-size='14'>&#9889;</text></svg>">
</head>
<body>
{out}
<script src="mermaid.min.js"></script>
<script>
(function () {{
  try {{ if (window.mermaid) {{ window.mermaid.initialize({{ startOnLoad: true }}); }} }} catch (e) {{}}
}})();
</script>
</body>
</html>
"""
    (REPO / "site" / "index.html").write_text(doc)
    print(f"built: artifact {len(out)} bytes, site {len(doc)} bytes")

if __name__ == "__main__":
    build()
