"""Build a standalone offline HTML review page from configured inputs."""
import json
import os
from pathlib import Path
from urllib.parse import quote
import rendering as r
from common import cli, read, write, path_for, validate_translations

def script_json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

def main():
    c = cli(__doc__)
    block_path = path_for(c, 'blocks')
    data, strict, summary = read(block_path), read(path_for(c, 'strict')), read(path_for(c, 'summary'))
    blocks, docs = data['blocks'], data['docs']
    validate_translations(blocks, strict, summary)
    r.ASSETS = block_path.parent / 'assets'
    r.CHG.clear()
    dp, pp = path_for(c, 'diff', False), path_for(c, 'previous_blocks', False)
    deleted = []
    if dp:
        if not pp: raise ValueError('diff requires previous_blocks')
        old = {b['id']: b for b in read(pp)['blocks']}
        diff = read(dp)
        for key, value in diff.items():
            if key.startswith('_dropped_'): deleted.extend(value)
        for b in blocks:
            d = diff[b['id']]
            if d['status'] == 'same': continue
            entry = dict(d)
            if d['status'] == 'changed':
                o = old[d['prev']]
                entry['old_html'] = o.get('html', '')
                if b['kind'] in ('text', 'caption'):
                    entry['diff'] = r.word_diff(o['html'], b['html'])
            r.CHG[b['id']] = entry
    output = path_for(c, 'html')
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf_rel = {k: quote(os.path.relpath(block_path.parent / d['pdf'], output.parent).replace(os.sep, '/'), safe='/.:')
               if d.get('pdf_available') and d.get('pdf') else '' for k, d in docs.items()}
    sections, contents, tabs = [], [], []
    for key, doc in docs.items():
        rows, toc, section = [], [], ''
        for b in (b for b in blocks if b['doc'] == key):
            if b['kind'] in ('title', 'heading'):
                section = b['id']
                toc.append(f'<a href="#{b["id"]}" data-target="{b["id"]}"><span class="t">{r.esc(strict[b["id"]])}</span><span class="cnt"></span></a>')
            rows.append(r.render_row(b, section, summary, strict, pdf_rel))
        hidden = '' if key == 'main' else ' hidden'
        source, target = r.esc(c['languages']['source']), r.esc(c['languages']['target'])
        info = 'PDF 页码为文字匹配提示，请核对版本和位置。' if pdf_rel[key] else '未配置 PDF；不显示页码。'
        sections.append(f'<section class="doc" data-doc="{key}"{hidden}><div class="doc-info">{r.esc(doc["name"])} · {info}</div>'
                        f'<div class="colhead"><div>{source}</div><div>{target}：大意 ／ 严格翻译</div><div>标记 · 批注</div></div>{"".join(rows)}</section>')
        contents.append(f'<div class="toc-doc" data-doc="{key}"{hidden}><h4>{r.esc(doc["name"])}</h4>{"".join(toc)}</div>')
        tabs.append(f'<button type="button" data-doc="{key}" class="{"on" if key == "main" else ""}">{r.esc(doc["name"])}</button>')
    notes_path = path_for(c, 'page_notes', False)
    notes = (f'<details class="rev" id="rev" open><summary>页面说明</summary>{r.md_to_html(notes_path.read_text(encoding="utf-8"))}</details>' if notes_path else '')
    if deleted:
        notes += '<details class="rev"><summary>上一版中删除的块</summary><ul>' + ''.join(f'<li>{r.esc(b["id"])} · {r.esc(b.get("en", b.get("match", b["kind"])))}</li>' for b in deleted) + '</ul></details>'
    meta = {'title': c['title'], 'languages': c['languages'], 'docs': {k: {'name': d['name']} for k, d in docs.items()},
            'sources': {k: {'docxName': Path(d['docx']).name, 'docxSha': d['docx_sha256']} for k, d in docs.items()},
            'suggestedFolder': 'review_marks'}
    home = Path(__file__).resolve().parent
    js = (home / 'review.js').read_text(encoding='utf-8').replace('__KEY__', script_json(c['storage_key'])).replace('__META__', script_json(meta))
    css = (home / 'review.css').read_text(encoding='utf-8')
    options = ''.join(f'<option value="{key}">{label}</option>' for key, label in r.CHIPS)
    page = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{r.esc(c['title'])}</title><style>{css}</style></head><body data-view="both">
<header class="topbar" id="topbar"><button class="icon-btn" id="tocToggle" title="目录">☰</button>
<div class="brand">{r.esc(c['title'])}<span>双语审阅</span></div><div class="seg" id="docTabs">{''.join(tabs)}</div>
<div class="seg" id="viewSeg"><button data-view="both" class="on">大意＋翻译</button><button data-view="sum">只看大意</button><button data-view="strict">只看翻译</button></div>
<label class="chk"><input type="checkbox" id="fMarked">只看已标记</label>
<label class="chk"><input type="checkbox" id="fTodo">只看未定状态</label>
<label class="chk"><input type="checkbox" id="fChg">只看有改动</label>
<label class="chk"><input type="checkbox" id="fOpen">展开改动对比</label>
<label class="chk">状态 <select id="fStatus"><option value="">全部</option>{options}</select></label>
<span class="progress" id="progress"></span><span class="saved" id="saved"></span>
<button class="btn primary" id="expMd">导出 Markdown</button><button class="btn" id="expJson">导出 JSON</button>
<label class="btn" for="impFile">导入</label><input type="file" id="impFile" accept=".json,.md,application/json,text/markdown" hidden>
<button class="btn" id="helpShow">?</button><button class="btn danger" id="clearAll">清空</button></header>
<div class="layout"><nav class="toc" aria-label="目录">{''.join(contents)}</nav><main>{notes}
<div class="help" id="help"><button class="btn close" id="helpClose">知道了</button><b>怎么用</b><ol>
<li>右栏可标记状态、写整段批注；再次点同一状态可取消。标题、图片和参考文献点“＋ 标记”展开。</li>
<li>在原文、译文、大意或表格中选中文字，再点“高亮并批注”。</li>
<li>批注只存在当前浏览器。请定期导出 JSON 或 Markdown 备份；导入可继续审阅。Markdown 的隐藏状态块不可删除。</li>
<li>改动对比中绿底表示新增，红色删除线表示删去。自动配对可能有误，请核对。</li>
<li>表格保留原文；译文由使用者提供，须人工校对。所有示例故事均为虚构。</li></ol></div>
<div class="orphans" id="orphans" hidden></div>{''.join(sections)}</main></div>
<div class="sel-pop" id="selPop" hidden><button id="popMark">高亮并批注</button></div>
<div class="lightbox" id="lightbox" hidden><img id="lbImg" alt="放大的图"></div><div class="toast" id="toast" hidden></div>
<script>{js}</script></body></html>'''
    output.write_text(page, encoding='utf-8', newline='\n')
    write(output.with_suffix('.audit.json'), {'rows': len(blocks), 'strict': len(strict), 'summary': len(summary),
                                             'changes': {s: sum(v['status'] == s for v in r.CHG.values()) for s in ('changed', 'new')},
                                             'deleted': len(deleted)})
    print(f'Built {output.name}')

if __name__ == '__main__': main()
