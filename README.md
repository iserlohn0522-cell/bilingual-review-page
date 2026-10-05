# Bilingual Review Page

Turn your Word documents and your own translations into a standalone, offline HTML review page. Read the source beside a short summary and a strict translation, mark review decisions, and export comments for revision.

The interface uses Chinese controls. Source and translation column labels are configurable; the defaults are English → 中文. No translation service, API key, account, server or network connection is needed to build or open a page.

## Features

- Ordered Word extraction: titles, headings, paragraphs, captions, simple tables, embedded pictures, references and existing Word comments.
- Optional PDF page hints through PyMuPDF; optional comparison with a previous edition, including a list of deleted blocks.
- Reuse of exactly unchanged source translations; changed and new blocks receive a translation worklist with previous translations for reference.
- Per-block review status and notes; selected-text highlights with their own notes in source text, translated text, summaries and tables.
- Browser localStorage persistence, review progress, table of contents, main/supporting-document tabs, summary/translation views, changed-only and status filters.
- Word-by-word revision panels, image zoom and responsive narrow-screen layouts.
- Markdown and JSON export and import. Markdown includes a hidden machine-readable state block for round trips.

## Install

Python 3.10 or later is required. From the package directory:

```sh
python -m venv .venv
# Activate the environment using the command appropriate for your shell.
python -m pip install -r requirements.txt
```

For optional PDF page hints:

```sh
python -m pip install PyMuPDF
```

Node 18 or later and Playwright are used only by the browser check:

```sh
npm install playwright
npx playwright install chromium
```

`playwright` is declared as a development dependency in `package.json`. Installation downloads packages and a browser; building and reviewing do not require internet access. The HTML includes its CSS, JavaScript and extracted pictures.

## Try the fictional example

```sh
python run_example.py
python -m unittest discover -s tests -v
node check_review_page.cjs --config examples/config_v2.json --out examples/output/browser-check
```

Open `examples/output/example_review.html` in a browser. The example generator uses python-docx and the Python standard library to create both editions of a short story and a supporting note, a table, an original geometric picture and a fictional reference. Chinese translations and summaries are provided in `examples/translations_v1.json` and `examples/translations_v2.json`. Everything in this example is invented.

The browser check exercises marking, source/translation/table highlights, reload persistence, filters, comparison panels, document switching, image zoom, both export/import formats, malformed imports and narrow-screen overflow. It writes screenshots and a result JSON. If a sandbox refuses to launch Chromium, run the same command in a normal terminal. An optional `--executable-path` selects an installed Chromium executable. A launch failure is not a passed browser check.

Generated example documents, extracted data, HTML and test output are ignored by version control. Re-run `python run_example.py` after a fresh clone to create them. Only copy the package directory when publishing; keep private input documents and any private leak patterns elsewhere.

A prebuilt copy of the example page is included at `examples/demo/example_review.html`. Open it in Chrome or Edge to try the interface (status marks, comments, highlights, change view, export and import) before installing anything.

## Configure your own review

Copy an example configuration into your own working directory. **All input and output paths resolve relative to the JSON configuration file**, not the shell's current directory. Use a different `storage_key` for each document edition or review project; reuse a key only for identical block content.

```json
{
  "title": "Library Guide v2",
  "languages": {"source": "English", "target": "中文"},
  "storage_key": "my-library-guide-v2",
  "page_notes": "review_notes.md",
  "documents": {
    "main": {"label": "Main text", "docx": "guide_v2.docx"},
    "si": {"label": "Supporting notes", "docx": "notes_v2.docx"}
  },
  "blocks": "output/v2/blocks.json",
  "previous_blocks": "output/v1/blocks.json",
  "diff": "output/v2/diff_map.json",
  "previous_strict": "output/v1/strict.json",
  "previous_summary": "output/v1/summary.json",
  "translation_work": "output/v2/translation_work.json",
  "authored": ["translations.json"],
  "strict": "output/v2/strict.json",
  "summary": "output/v2/summary.json",
  "html": "output/review.html"
}
```

Only `main` is required in `documents`; omit `si` for a single document. To locate PDF pages, add `"pdf": "guide_v2.pdf"` to the corresponding document entry. Supply a PDF exported from the exact Word edition. Page locations are text-match hints, not a guarantee of edition identity or correct layout. PDF links remain external relative links, so keep those files in the same relative positions when moving the HTML.

`page_notes` is optional. It accepts a small, escaped Markdown subset: headings, paragraphs, simple tables, lists, bold and inline code; links render as text. Omit it when no notes are needed. Omit `previous_blocks`, `diff`, `previous_strict` and `previous_summary` to build without an earlier version. Previous translation maps may also be omitted when only a visual comparison is wanted. Do not point output fields at original input files.

## Step-by-step workflow

Use the same configuration for each step. The following commands assume it is named `config.json` in the current directory.

1. Extract the Word document(s):

   ```sh
   python extract_blocks.py --config config.json
   ```

   This writes the configured block JSON and an adjacent `assets/` folder. Basic emphasis, subscript and superscript are retained. Word headings control the outline. References start at a heading named `References` or `Bibliography`; set `reference_headings` to a list of other heading texts within a document configuration if needed.

2. Compare editions, if configured:

   ```sh
   python diff_blocks.py --config config.json
   ```

   Matching is one-to-one, kind-aware and order-preserving. Exact source matches are found first; fuzzy matching within remaining spans is a heuristic. Review ambiguous alignments. Deleted blocks stay in the diff file and appear in a separate page panel.

3. Prepare translation work:

   ```sh
   python prepare_translations.py --config config.json
   ```

   Read the `pending` list at the configured `translation_work` path. Write manual or model-assisted translations into the JSON files listed in `authored`. Do not fill changed blocks by blindly copying the old translation. Missing previous translations are requested even if the source is unchanged.

4. Merge and validate:

   ```sh
   python merge_translations.py --config config.json
   ```

   This recomputes source reuse, requires complete nonempty coverage, and rejects unknown IDs, duplicate authored IDs and unsupported fields. It writes separate strict-translation and summary maps. Authored values may override a reused value. Keep one authored record per ID across all files.

5. Build the page:

   ```sh
   python build_review_page.py --config config.json
   ```

   The output is the configured HTML plus an adjacent `.audit.json` with build counts. Open the HTML locally. The browser checker is specifically an example regression suite, not an automatic semantic acceptance check for arbitrary documents.

All Python entry points offer `--help`. `common.py`, `rendering.py` and `word_helpers.py` are internal libraries. The JavaScript checker uses Node's built-in `parseArgs` and supports `--help`.

## JSON formats

Block files have `version`, `docs` and `blocks`. Paths in `docs` are relative to the block file. IDs are extraction-order identifiers, not permanent paragraph identities:

```json
{
  "version": 1,
  "docs": {"main": {"name": "Main text", "docx": "../../guide.docx", "docx_sha256": "...", "pdf": null, "pdf_available": false, "pdf_pages": 0}},
  "blocks": [{"id": "M-003", "doc": "main", "kind": "text", "label": "text 3", "en": "The room opens on Saturday.", "match": "The room opens on Saturday.", "html": "The room opens on Saturday.", "page": null, "page_end": null}]
}
```

`kind` is `title`, `heading`, `text`, `caption`, `table`, `image`, `reference` or `math`. Tables add `rows`, a nested array of `{text, html}` cells. Images add `file` (under adjacent `assets/`), `content_type`, `alt` and `sha256`. Headings add `level`. Existing Word comments, when extracted, appear in `word_comments` as `{author, text}`. Treat block files as trusted local build inputs; do not render third-party hand-edited HTML fields.

The diff is keyed by current IDs. Each value has `status` (`same`, `changed`, `new`), `prev` (previous ID or null) and `ratio`. `_dropped_main` and `_dropped_si` contain complete deleted blocks. Similarity scores are alignment aids, not evidence that meaning was preserved.

Translation work contains `strict` and `summary` maps for reusable values plus a `pending` array. Each pending item includes `id`, `kind`, `source`, optional table `rows`, `needed`, `previous_source`, `previous_strict` and `previous_summary`.

Author translations using this shape:

```json
{
  "M-003": {"strict": "阅览室周六开放。", "summary": "开放日为周六。"},
  "M-007": {"summary": "表格列出书架及图书数量。"}
}
```

Titles/headings need `strict`; paragraphs/captions need both fields; tables/math need `summary`; pictures/references need neither. Tables retain original text. The final `strict` and `summary` files are simple `{block_id: string}` maps. Translation strings are plain text, escaped during rendering; they are not HTML.

Review exports have `format: "bilingual-review-marks"`, `version: 1`, `storageKey`, document metadata, human-readable `marks` and the full browser `state`. `state.blocks` stores status, note, highlight ranges, source snippet and document ID. Import requires the same storage key and merges by ID, with imported entries taking precedence. Unmatched entries are retained as orphan marks. JSON is the recommended archival format. Markdown can be imported while its `bilingual-review-state` comment remains intact; editing only the visible Markdown does not edit that hidden state.

## Producing translations

Translate manually or use any language model with this template. Replace the language names and attach only the pending items you intend to share:

```text
Translate the attached review blocks from [source language] into [target language].
Return only a JSON object keyed by the supplied block IDs.
For each ID, supply exactly the fields listed in its "needed" array.
"strict": translate all of the CURRENT source faithfully. Preserve names,
numbers, units, uncertainty, negation, citations and conditional statements.
Do not add evidence, explanation, corrections or stronger claims.
"summary": write a short, faithful gist without introducing new facts.
For tables or equations, summarize what they show; do not replace their data.
Previous source text and translations are references only; follow the current text.
Use plain strings, no HTML and no Markdown code fence. Do not invent IDs.
If a passage is ambiguous, stop and flag it for human review before producing
a final translation. Do not silently resolve ambiguities.
```

Read every translation before merging. Coverage validation checks structure and missing values, not translation accuracy. If using an external model, follow its privacy terms and your document's sharing restrictions; the tools themselves do not send text anywhere.

## Privacy and limitations

- Comments live only in your browser's localStorage. Clearing browser data, private browsing, moving a local file or changing browsers may lose access to them. Export regularly. A save warning means local persistence failed.
- The HTML contains source text, translations, pictures and existing Word comment author names. Exports contain source snippets and notes. Treat both as document copies when sharing. No telemetry, remote fonts or CDN assets are used.
- Word extraction is not a layout renderer. Headers, footers, footnotes, endnotes, text boxes, floating drawings, charts, numbering and complex/merged/nested tables may not be reproduced faithfully. Images in table cells are rejected. Supported pictures are PNG, JPEG, GIF and WebP.
- Tracked insertions are included; tracked deletions are omitted. Resolve tracked changes in a copy before extraction if this is not your intended reading. Word comments are displayed read-only; browser comments do not modify Word files.
- Equations are flattened text rather than typeset mathematics. PDF matching is heuristic and does not use OCR; scanned PDFs and repeated text can remain unlocated. Images do not receive guessed PDF page numbers.
- Changed blocks are paired heuristically. Moved or substantially rewritten paragraphs can appear as deleted/new. Word differences use whitespace tokens, which is less useful for languages without spaces. Paragraph IDs shift after insertion; use explicit version keys and keep old exports.
- The controls remain Chinese even with different language labels. Right-to-left document layouts and full interface localization are not implemented.
- Markdown import supports this tool's exported state marker, not arbitrary Markdown comments. Browser security and local-file storage behavior vary; Chromium is the automated test target.
- Large documents and pictures create large HTML files. This is a local review aid, not collaborative editing or a document-management service.

## Release privacy scan

`tools/leak_scan.py` accepts a private list of regular expressions outside the release directory:

```json
[{"id": "private-name", "pattern": "PrivateExampleName", "ignore_case": true}]
```

```sh
python tools/leak_scan.py --root . --patterns ../private_patterns.json --report ../leak_scan.json
```

The report lists rule IDs and locations without copying matching private text. The scan includes all files, ZIP members and embedded image metadata; it does not perform OCR or prove absence of every possible disclosure. Do not publish your private pattern file or private scan reports.

## 中文使用说明

这是一个离线双语审阅工具。输入自己的 Word、逐块译文和大意，生成可直接在浏览器打开的 HTML。原文与译文并排显示，可逐段标状态、写批注、选中文字高亮批注、筛选改动和状态，并导出或导回 JSON／Markdown。

先安装 Python 3.10+ 与 `python-docx`，再执行 `python run_example.py`，打开 `examples/output/example_review.html`。示例全部虚构。不想安装也可以直接用 Chrome 或 Edge 打开仓库里现成的 `examples/demo/example_review.html` 试用。需要 PDF 页码提示时另装 PyMuPDF；Node 18+ 与 Playwright 仅用于浏览器测试，标准安装命令是 `npm install playwright` 和 `npx playwright install chromium`。

自己的文档使用 JSON 配置；所有路径都相对配置文件，标题、语言标签、存储键、说明 Markdown 与输入输出路径均可改。正文为 `main`，补充材料 `si` 可省略。按“抽取→可选对比→准备翻译→合并译文→生成页面”运行。译文可手写或用任何模型辅助，但必须人工校对；程序只验证覆盖情况，不保证翻译准确。

批注只存在当前浏览器，请定期导出。JSON 最适合完整备份；Markdown 保留隐藏状态块时也可导回，直接改可见文字不会更新隐藏状态。每版文档使用不同存储键，避免串用批注。生成的 HTML 含原文、图片与已有 Word 批注，分享时请按完整文档处理。

## License

MIT; see `LICENSE`.
