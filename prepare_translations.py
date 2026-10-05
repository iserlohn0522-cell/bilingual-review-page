"""Prepare missing or changed translations, including previous reference translations."""
from common import cli, path_for, read, write, STRICT, SUMMARY
from diff_blocks import signature

def prepare(c):
    blocks_path = path_for(c, 'blocks')
    blocks = read(blocks_path)['blocks']
    previous_path = path_for(c, 'previous_blocks', False)
    old = {b['id']: b for b in read(previous_path)['blocks']} if previous_path else {}
    diff_path = path_for(c, 'diff', False)
    diff = read(diff_path) if diff_path else {}
    def optional(key):
        path = path_for(c, key, False)
        return read(path) if path else {}
    old_strict, old_summary = optional('previous_strict'), optional('previous_summary')
    strict, summary, pending = {}, {}, []
    for b in blocks:
        kind, bid = b['kind'], b['id']
        if kind not in STRICT | SUMMARY: continue
        d = diff.get(bid, {})
        prev = old.get(d.get('prev'))
        same = bool(prev and d.get('status') == 'same' and prev['kind'] == kind and
                    signature(prev, previous_path.parent) == signature(b, blocks_path.parent))
        needed = []
        for field, kinds, before, target in [('strict', STRICT, old_strict, strict), ('summary', SUMMARY, old_summary, summary)]:
            if kind not in kinds: continue
            value = before.get(prev['id']) if prev else None
            if same and isinstance(value, str) and value.strip(): target[bid] = value
            else: needed.append(field)
        if needed:
            pending.append({'id': bid, 'kind': kind, 'source': b.get('en', b.get('match', '')), 'rows': b.get('rows'),
                            'needed': needed, 'previous_source': prev.get('en', prev.get('match')) if prev else None,
                            'previous_strict': old_strict.get(prev['id']) if prev else None,
                            'previous_summary': old_summary.get(prev['id']) if prev else None})
    return {'strict': strict, 'summary': summary, 'pending': pending}

def main():
    c = cli(__doc__)
    write(path_for(c, 'translation_work'), prepare(c))

if __name__ == '__main__': main()
