"""docs/VLC-bilingual-subtitles.md -> site/vlc.html (HTML fragment loaded by the app)."""
import html, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
md = (ROOT / "docs" / "VLC-bilingual-subtitles.md").read_text(encoding="utf-8")
out, inlist, intable, incode = [], None, False, False
def inline(s):
    s = html.escape(s); s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s); return re.sub(r"`(.+?)`", r"<code>\1</code>", s)
for line in md.split("\n"):
    if line.strip().startswith("```"):
        out.append("</pre>" if incode else "<pre>"); incode = not incode; continue
    if incode: out.append(html.escape(line.strip())); continue
    if line.startswith("|"):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "): continue
        tag = "td" if intable else "th"
        if not intable: out.append("<table>"); intable = True
        out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>"); continue
    if intable: out.append("</table>"); intable = False
    m = re.match(r"^(\s*)(\d+\.|-) (.*)", line)
    if m:
        tag = "ol" if m.group(2)[0].isdigit() else "ul"
        if inlist != tag:
            if inlist: out.append(f"</{inlist}>")
            out.append(f"<{tag}>"); inlist = tag
        out.append(f"<li>{inline(m.group(3))}</li>"); continue
    if inlist and not line.strip(): out.append(f"</{inlist}>"); inlist = None
    if line.startswith("#"):
        n = len(line) - len(line.lstrip("#")); out.append(f"<h{n}>{inline(line[n:].strip())}</h{n}>")
    elif line.strip() and not line.startswith("   "): out.append(f"<p>{inline(line)}</p>")
if inlist: out.append(f"</{inlist}>")
if intable: out.append("</table>")
(ROOT / "site" / "vlc.html").write_text("\n".join(out), encoding="utf-8")
