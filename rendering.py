"""Reusable row renderer and offline browser interface."""
import base64
import difflib
import html
import mimetypes
import re
from pathlib import Path
ASSETS = Path('.')
CHG = {}
REVIEWABLE = {'text', 'caption', 'table', 'math'}
NEEDS_SUMMARY = REVIEWABLE
NEEDS_STRICT = {'title', 'heading', 'text', 'caption'}
CHIPS = [('ok', '通过'), ('minor', '小修'), ('revise', '需修改'), ('question', '存疑'), ('logic', '逻辑/证据'), ('trans', '译文有误')]
NUMERIC = re.compile(r'^[\s\d.,;:/×\-−+–\[\]()%≥≤<>=—]*$')

def esc(s: str) -> str:
    return html.escape(s, quote=False)

def attr(s) -> str:
    return html.escape(str(s), quote=True)

def zh_html(s: str) -> str:
    return esc(s)

def image_uri(name: str) -> str:
    path = ASSETS / name
    mime = mimetypes.guess_type(path.name)[0]
    if mime not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        raise ValueError("Unsupported browser image format")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()

def render_table(rows: list[list[dict]]) -> str:
    head, body = rows[0], rows[1:]
    out = ['<div class="tbl-wrap" data-field="table"><table><thead><tr>']
    out += [f"<th>{re.sub(r'</?strong>', '', c['html'])}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        cells = "".join(
            f'<td class="{"num" if NUMERIC.match(c["text"]) and len(c["text"]) <= 18 else ""}">{c["html"]}</td>' for c in r)
        out.append(f"<tr>{cells}</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)

def _tokens(h: str) -> list[str]:
    """Whitespace tokens of a block's HTML with only sub/sup markup kept (emphasis and line breaks dropped)."""
    h = re.sub(r"</?(?:em|strong|span)[^>]*>", "", h).replace("<br>", " ")
    out = []
    for t in h.split():
        if t.count("<sub>") != t.count("</sub>") or t.count("<sup>") != t.count("</sup>"):
            t = re.sub(r"</?su[bp]>", "", t)
        out.append(t)
    return out

def word_diff(old_html: str, new_html: str) -> str:
    a, b = _tokens(old_html), _tokens(new_html)
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            out.append(" ".join(b[j1:j2]))
            continue
        if i2 > i1:
            out.append("<del>" + " ".join(a[i1:i2]) + "</del>")
        if j2 > j1:
            out.append("<ins>" + " ".join(b[j1:j2]) + "</ins>")
    return " ".join(out)

def chg_badge(b: dict) -> str:
    c = CHG.get(b["id"])
    if not c:
        return ""
    if c["status"] == "new":
        return '<span class="chgtag chg-new">本版 新增</span>'
    return '<span class="chgtag chg-changed">' + ("图已重画" if b["kind"] == "image" else "较上一版有改动") + "</span>"

def chg_panel(b: dict) -> str:
    """Word-level comparison with the previous-version block; sits outside the data-field elements so highlighting is unaffected."""
    c = CHG.get(b["id"])
    if not c or c["status"] != "changed":
        return ""
    if b["kind"] in ("text", "caption"):
        return ('<details class="chg"><summary>较上一版的逐词改动'
                '<span class="lg"><ins>新增</ins><del>删除</del></span></summary>'
                f'<div class="chg-body">{c["diff"]}</div></details>')
    if b["kind"] in ("title", "heading"):
        return f'<div class="chg-h">原标题（上一版）：<del>{c["old_html"]}</del></div>'
    if b["kind"] == "table":
        return '<div class="chg-h">表格内容较上一版有改动，未逐格对比；请直接对照表格本身。</div>'
    if b["kind"] == "image":
        return '<div class="chg-h">图片已更改；请核对源文档。</div>'
    return ""

def mark_column(compact: bool) -> str:
    chips = "".join(
        f'<button type="button" class="chip" data-s="{k}" aria-pressed="false">{v}</button>' for k, v in CHIPS)
    body = (f'<div class="chips" role="group" aria-label="段落状态">{chips}</div>'
            '<textarea class="note" rows="2" placeholder="整段批注…"></textarea>'
            '<ul class="hl-list"></ul>')
    if compact:
        return f'<div class="c-mark compact"><button type="button" class="add-note">＋ 标记</button><div class="mk">{body}</div></div>'
    return f'<div class="c-mark"><div class="mk">{body}</div></div>'

def page_link(b: dict, pdf_rel: dict) -> str:
    pg, pe = b.get("page"), b.get("page_end")
    if not pg or not pdf_rel.get(b["doc"]):
        return ""
    txt = f"p.{pg}" if not pe or pe == pg else f"p.{pg}–{pe}"
    return (f'<a class="pg" href="{attr(pdf_rel[b["doc"]])}#page={pg}" target="_blank" rel="noopener" '
            f'title="在 PDF 中打开第 {pg} 页">{txt}</a>')

def meta_line(b: dict, pdf_rel: dict) -> str:
    return (f'<div class="meta"><span class="lbl">{esc(b["label"])}</span>{page_link(b, pdf_rel)}{chg_badge(b)}'
            f'<span class="bid">{b["id"]}</span></div>')

def word_comments(b: dict) -> str:
    return "".join(
        f'<div class="wc"><b>Word 稿内已有批注（{esc(c["author"] or "?")}）：</b>{esc(c["text"])}</div>'
        for c in b.get("word_comments") or [])

def render_row(b: dict, sec: str, summary: dict, strict: dict, pdf_rel: dict) -> str:
    k = b["kind"]
    attrs = (f'id="{b["id"]}" class="row kind-{k}{" level-" + str(b.get("level")) if b.get("level") else ""}" '
             f'data-doc="{b["doc"]}" data-kind="{k}" data-label="{attr(b["label"])}" data-page="{b.get("page") or ""}" '
             f'data-sec="{sec}" data-reviewable="{1 if k in REVIEWABLE else 0}" data-chg="{CHG.get(b["id"], {}).get("status", "same")}"')
    if k in ("title", "heading"):
        tag = "h1" if k == "title" else f"h{b.get('level', 2)}"
        return (f'<article {attrs}><div class="c-en"><{tag} class="en" data-field="en">{b["html"]}</{tag}>{chg_badge(b)}{chg_panel(b)}{word_comments(b)}</div>'
                f'<div class="c-zh"><{tag} class="zh-h">{zh_html(strict[b["id"]])}</{tag}></div>{mark_column(True)}</article>')
    if k in ("text", "caption"):
        cap = " cap" if k == "caption" else ""
        return (f'<article {attrs}><div class="c-en">{meta_line(b, pdf_rel)}<div class="en{cap}" data-field="en">{b["html"]}</div>{chg_panel(b)}{word_comments(b)}</div>'
                f'<div class="c-zh"><div class="sum"><span class="tag">大意</span><span class="sum-text" data-field="sum">{zh_html(summary[b["id"]])}</span></div>'
                f'<div class="strict"><span class="tag">严格翻译</span><span class="strict-text" data-field="strict">{zh_html(strict[b["id"]])}</span></div></div>'
                f'{mark_column(False)}</article>')
    if k == "math":
        return (f'<article {attrs}><div class="c-en">{meta_line(b, pdf_rel)}<div class="en math-block" data-field="en">{b["html"]}</div></div>'
                f'<div class="c-zh"><div class="sum keep"><span class="tag">说明</span><span class="sum-text" data-field="sum">{zh_html(summary[b["id"]])}</span></div></div>'
                f'{mark_column(False)}</article>')
    if k == "table":
        return (f'<article {attrs}><div class="c-wide">{meta_line(b, pdf_rel)}{render_table(b["rows"])}{chg_panel(b)}'
                f'<div class="sum keep"><span class="tag">这张表看什么</span><span class="sum-text" data-field="sum">{zh_html(summary[b["id"]])}</span></div>'
                f'<div class="tbl-note">表格保留原文，避免翻译改动列名、单位或数值。</div></div>{mark_column(False)}</article>')
    if k == "image":
        return (f'<article {attrs}><div class="c-wide">{meta_line(b, pdf_rel)}{chg_panel(b)}<figure class="fig">'
                f'<img src="{image_uri(b["file"])}" alt="{attr(b.get("alt") or b["label"])}" loading="lazy"></figure></div>'
                f'{mark_column(True)}</article>')
    if k == "reference":
        return (f'<article {attrs}><div class="c-wide">{meta_line(b, pdf_rel)}<div class="en ref" data-field="en">{b["html"]}</div></div>'
                f'{mark_column(True)}</article>')
    raise ValueError(f"unknown kind {k} in {b['id']}")

def md_to_html(text: str) -> str:
    """Small Markdown subset (headings, tables, lists, paragraphs, bold, code, links as text) for the revision card."""
    def inl(s: str) -> str:
        s = esc(s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("# "):
            i += 1
            continue
        if line.startswith("#"):
            out.append(f"<h4>{inl(line.lstrip('#').strip())}</h4>"); i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.fullmatch(r"[\s|:\-]+", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table>" + "".join("<tr>" + "".join(f"<{'th' if n == 0 else 'td'}>{inl(c)}</{'th' if n == 0 else 'td'}>" for c in r) + "</tr>" for n, r in enumerate(rows)) + "</table>")
            continue
        for pattern, tag in ((r"^\d+\. ", "ol"), (r"^- ", "ul")):
            if re.match(pattern, line):
                items = []
                while i < len(lines) and re.match(pattern, lines[i]):
                    items.append(re.sub(pattern, "", lines[i])); i += 1
                out.append(f"<{tag}>" + "".join(f"<li>{inl(x)}</li>" for x in items) + f"</{tag}>")
                break
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||- |\d+\. )", lines[i]):
                para.append(lines[i]); i += 1
            out.append(f"<p>{inl(' '.join(para))}</p>")
    return "\n".join(out)
