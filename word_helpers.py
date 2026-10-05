"""Small OOXML extraction helpers. No document content is bundled here."""
import html
import re
import unicodedata
from pathlib import Path
from docx.oxml.ns import qn
ASSETS = Path('.')
M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
A_BLIP = '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'
R_EMBED = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'
WP_DOCPR = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr'
def flag(rpr, tag: str) -> bool:
    if rpr is None:
        return False
    el = rpr.find(qn(tag))
    return el is not None and el.get(qn("w:val")) not in ("0", "false", "none")

def run_format(r) -> tuple:
    rpr = r.find(qn("w:rPr"))
    va = None
    if rpr is not None and rpr.find(qn("w:vertAlign")) is not None:
        va = rpr.find(qn("w:vertAlign")).get(qn("w:val"))
    return (flag(rpr, "w:b"), flag(rpr, "w:i"), va, False)

def paragraph_content(p_el, part, doc_key: str, counters: dict):
    """Return (pieces, images, comment_ids); pieces are (text, format) in document order."""
    pieces: list[tuple[str, tuple]] = []
    images: list[dict] = []
    comment_ids: list[str] = []

    def walk(el):
        for ch in el:
            tag = ch.tag
            if tag == qn("w:r"):
                fmt = run_format(ch)
                for sub in ch:
                    if sub.tag == qn("w:t"):
                        pieces.append((sub.text or "", fmt))
                    elif sub.tag == qn("w:tab"):
                        pieces.append((" ", fmt))
                    elif sub.tag == qn("w:br") and sub.get(qn("w:type")) != "page":
                        pieces.append(("\n", fmt))
                    elif sub.tag == qn("w:drawing"):
                        alt = ""
                        for pr in sub.iter(WP_DOCPR):
                            alt = pr.get("descr") or pr.get("name") or ""
                        for blip in sub.iter(A_BLIP):
                            target = part.related_parts[blip.get(R_EMBED)]
                            counters["fig"] += 1
                            ext = Path(str(target.partname)).suffix or ".png"
                            name = f"{doc_key}_fig{counters['fig']}{ext}"
                            (ASSETS / name).write_bytes(target.blob)
                            images.append({"file": name, "alt": alt, "content_type": target.content_type})
                    elif sub.tag == qn("w:commentReference"):
                        comment_ids.append(sub.get(qn("w:id")))
            elif tag in (qn("w:hyperlink"), qn("w:smartTag"), qn("w:ins")):
                walk(ch)
            elif tag in (f"{{{M_NS}}}oMath", f"{{{M_NS}}}oMathPara"):
                pieces.append(("".join(t.text or "" for t in ch.iter(f"{{{M_NS}}}t")), (False, False, None, True)))
            elif tag == qn("w:commentRangeStart"):
                comment_ids.append(ch.get(qn("w:id")))

    walk(p_el)
    return pieces, images, list(dict.fromkeys(comment_ids))

def pieces_to_html(pieces) -> str:
    merged: list[list] = []
    for text, fmt in pieces:
        if merged and merged[-1][1] == fmt:
            merged[-1][0] += text
        else:
            merged.append([text, fmt])
    out = []
    for text, (bold, italic, va, math) in merged:
        h = html.escape(text, quote=False).replace("\n", "<br>")
        if va == "subscript":
            h = f"<sub>{h}</sub>"
        elif va == "superscript":
            h = f"<sup>{h}</sup>"
        if italic:
            h = f"<em>{h}</em>"
        if bold:
            h = f"<strong>{h}</strong>"
        if math:
            h = f'<span class="math">{h}</span>'
        out.append(h)
    return "".join(out).strip()

def pieces_to_text(pieces, markers: bool) -> str:
    out = []
    for text, (_b, _i, va, _m) in pieces:
        if markers and va == "subscript" and text.isascii():
            text = "_" + text
        elif markers and va == "superscript" and text.isascii():
            text = "^" + text
        out.append(text)
    return re.sub(r"[ \t]+", " ", "".join(out)).strip()

def read_comments(doc) -> dict[str, dict]:
    comments = {}
    for rel in doc.part.rels.values():
        if rel.reltype.endswith("/comments"):
            root = rel.target_part.element if hasattr(rel.target_part, "element") else None
            if root is None:
                from lxml import etree
                root = etree.fromstring(rel.target_part.blob)
            for c in root.iter(qn("w:comment")):
                comments[c.get(qn("w:id"))] = {
                    "author": c.get(qn("w:author")) or "",
                    "text": " ".join(t.text or "" for t in c.iter(qn("w:t"))).strip(),
                }
    return comments

def norm(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))
