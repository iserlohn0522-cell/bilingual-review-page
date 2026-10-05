"""Scan a release tree using a private external list of forbidden patterns.

Reports rule identifiers, not matched source text. ZIP members and embedded image
data are inspected. No files or directories are silently excluded from a scan.
"""
import argparse
import base64
import io
import json
import re
import zipfile
from pathlib import Path

def text_views(blob, name):
    if zipfile.is_zipfile(io.BytesIO(blob)):
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            for member in archive.infolist():
                if not member.is_dir():
                    yield from text_views(archive.read(member), name + '!' + member.filename)
        return
    # UTF-8 text and printable binary metadata. Random binary is not natural language.
    if b'\x00' not in blob[:256]:
        value = blob.decode('utf-8', errors='replace')
        yield name, value
        for i, m in enumerate(re.finditer(r'data:image/[^;,]+;base64,([A-Za-z0-9+/=]+)', value)):
            yield from text_views(base64.b64decode(m.group(1)), name + f'!image-{i}')
    else:
        for i, token in enumerate(re.findall(rb'[\x20-\x7e]{12,}', blob)):
            yield name + f'!metadata-{i}', token.decode('ascii')

def scan(root, patterns):
    root = Path(root).resolve()
    rules = [(item, re.compile(item['pattern'], re.IGNORECASE if item.get('ignore_case', True) else 0)) for item in patterns]
    findings, inspected = [], []
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            findings.append({'file': path.relative_to(root).as_posix(), 'rule': 'symlink-not-allowed'})
            continue
        if not path.is_file(): continue
        name = path.relative_to(root).as_posix()
        inspected.append(name)
        views = [(name + '!filename', name), *text_views(path.read_bytes(), name)]
        for member, text in views:
            for rule, regex in rules:
                for match in regex.finditer(text):
                    # A narrow public copyright attribution may be explicitly allowed.
                    if any(a['file'] == name and a['text'] in text and
                           any(start <= match.start() < start + len(a['text']) for start in [text.find(a['text'])])
                           for a in rule.get('allow', [])):
                        continue
                    findings.append({'file': member, 'rule': rule['id'], 'line': text.count('\n', 0, match.start()) + 1})
    return {'status': 'passed' if not findings else 'failed', 'files_scanned': len(inspected), 'rules': len(patterns),
            'findings': findings, 'files': inspected,
            'limits': 'Pattern scan, ZIP text and printable image metadata; no OCR or semantic privacy certification.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Release directory to scan')
    parser.add_argument('--patterns', type=Path, required=True, help='Private JSON list outside the release directory')
    parser.add_argument('--report', type=Path, required=True, help='JSON report destination outside the release directory')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.patterns.resolve().is_relative_to(root) or args.report.resolve().is_relative_to(root):
        parser.error('Keep the private pattern list and scan report outside the release directory.')
    report = scan(root, json.loads(args.patterns.read_text(encoding='utf-8-sig')))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'files_scanned', 'rules')} | {'finding_count': len(report['findings'])}, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'passed' else 1)

if __name__ == '__main__': main()
