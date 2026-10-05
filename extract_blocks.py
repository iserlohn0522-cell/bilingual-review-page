"""Extract ordered Word blocks and optional heuristic PDF page locations."""
from pathlib import Path
import os
import re
from docx import Document
from docx.oxml.ns import qn
import word_helpers as w
from common import cli, path_for, write, digest

def extract(key, spec, base, destination):
    source = (base / spec['docx']).resolve()
    pdf = (base / spec['pdf']).resolve() if spec.get('pdf') else None
    pages = []
    if pdf:
        import fitz  # Optional dependency, only imported when a PDF is configured.
        with fitz.open(pdf) as doc:
            pages = [w.norm(p.get_text()) for p in doc]
    doc = Document(source)
    comments = w.read_comments(doc)
    counters = {'fig': 0}
    blocks, in_refs = [], False
    for el in doc.element.body:
        if el.tag == qn('w:p'):
            ppr = el.find(qn('w:pPr'))
            style_el = ppr.find(qn('w:pStyle')) if ppr is not None else None
            style = doc.styles.get_by_id(style_el.get(qn('w:val')), 1).name if style_el is not None else 'Normal'
            pieces, images, cids = w.paragraph_content(el, doc.part, key, counters)
            for img in images:
                if img['content_type'] not in ('image/png', 'image/jpeg', 'image/gif', 'image/webp'):
                    raise ValueError('Convert embedded figures to PNG, JPEG, GIF or WebP before extraction.')
                blocks.append({'kind': 'image', **img, 'sha256': digest(w.ASSETS / img['file'])})
            text = w.pieces_to_text(pieces, False)
            if not text:
                continue
            if style == 'Title':
                kind = 'title'
            elif style.startswith('Heading'):
                kind = 'heading'
                in_refs = text.casefold().strip() in [s.casefold() for s in spec.get('reference_headings', ['References', 'Bibliography'])]
            elif in_refs:
                kind = 'reference'
            elif style == 'Caption' or re.match(r'^(Table|Figure)\s+\S+\.', text):
                kind = 'caption'
            elif pieces and all(fmt[3] or not txt.strip() for txt, fmt in pieces):
                kind = 'math'
            else:
                kind = 'text'
            block = {'kind': kind, 'html': w.pieces_to_html(pieces), 'en': w.pieces_to_text(pieces, True), 'match': text}
            if kind == 'heading':
                block['level'] = 2 if style == 'Heading 1' else 3
            if cids:
                block['word_comments'] = [comments[c] for c in cids if c in comments]
            blocks.append(block)
        elif el.tag == qn('w:tbl'):
            rows = []
            for tr in el.findall(qn('w:tr')):
                row = []
                for tc in tr.findall(qn('w:tc')):
                    texts, fragments = [], []
                    for para in tc.findall(qn('w:p')):
                        pieces, images, cids = w.paragraph_content(para, doc.part, key, counters)
                        if images:
                            raise ValueError('Images inside table cells are unsupported; move them to separate paragraphs.')
                        texts.append(w.pieces_to_text(pieces, False))
                        fragments.append(w.pieces_to_html(pieces))
                    row.append({'text': '\n'.join(texts), 'html': '<br>'.join(fragments)})
                rows.append(row)
            if rows:
                blocks.append({'kind': 'table', 'rows': rows, 'match': ' '.join(c['text'] for r in rows for c in r)})
    prefix = 'M' if key == 'main' else 'S'
    for i, b in enumerate(blocks, 1):
        b.update(id=f'{prefix}-{i:03d}', doc=key, label=f'{b["kind"]} {i}', page=None, page_end=None)
        text = w.norm(b.get('match', ''))
        # A unique exact prefix is a location hint, never a layout or edition certification.
        hits = [n + 1 for n, page in enumerate(pages) if text and text[:60] in page]
        if len(hits) == 1:
            b['page'] = hits[0]
            tail_hits = [n + 1 for n, page in enumerate(pages) if text[-60:] in page and n + 1 >= hits[0]]
            b['page_end'] = tail_hits[0] if len(tail_hits) == 1 else None
        b['page_method'] = 'unique-prefix-hint' if b['page'] else 'unlocated'
    relative = lambda p: os.path.relpath(p, destination.parent).replace(os.sep, '/') if p else None
    return blocks, {'name': spec.get('label', key), 'docx': relative(source), 'docx_sha256': digest(source),
                    'pdf': relative(pdf), 'pdf_sha256': digest(pdf) if pdf else '', 'pdf_available': bool(pages),
                    'pdf_pages': len(pages), 'page_method': 'unique-prefix-hint; verify PDF edition manually'}

def main():
    c = cli(__doc__)
    out = path_for(c, 'blocks')
    w.ASSETS = out.parent / 'assets'
    w.ASSETS.mkdir(parents=True, exist_ok=True)
    data = {'version': 1, 'docs': {}, 'blocks': []}
    for key, spec in c['documents'].items():
        blocks, meta = extract(key, spec, c['_base'], out)
        data['blocks'].extend(blocks)
        data['docs'][key] = meta
    write(out, data)
    print(f'Extracted {len(data["blocks"])} blocks.')

if __name__ == '__main__':
    main()
