"""Compare versions using ordered, kind-aware alignment; retain deleted blocks."""
import difflib
import re
from common import cli, read, write, path_for, digest

def signature(b, directory):
    if b['kind'] == 'image':
        return digest(directory / 'assets' / b['file'])
    if b['kind'] == 'table':
        value = ' | '.join(c['text'] for r in b['rows'] for c in r)
    else:
        value = b.get('en', '')
    return re.sub(r'\s+', ' ', value).strip()

def compare(old_data, new_data, old_dir, new_dir):
    result = {}
    for doc in new_data['docs']:
        old = [b for b in old_data['blocks'] if b['doc'] == doc]
        new = [b for b in new_data['blocks'] if b['doc'] == doc]
        a = [(b['kind'], signature(b, old_dir)) for b in old]
        b = [(b['kind'], signature(b, new_dir)) for b in new]
        matched = {}
        # Dynamic programming within replacement spans preserves order for fuzzy matches too.
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag == 'equal':
                for oi, ni in zip(range(i1, i2), range(j1, j2)):
                    matched[ni] = (oi, 1.0)
            elif tag == 'replace':
                m, n = i2 - i1, j2 - j1
                scores = [[0.0] * (n + 1) for _ in range(m + 1)]
                steps = {}
                for i in range(1, m + 1):
                    for j in range(1, n + 1):
                        oi, ni = i1 + i - 1, j1 + j - 1
                        ratio = 0.0
                        if a[oi][0] == b[ni][0]:
                            ratio = 0.5 if a[oi][0] == 'image' else difflib.SequenceMatcher(None, a[oi][1], b[ni][1], autojunk=False).ratio()
                        options = [(scores[i-1][j], 'old'), (scores[i][j-1], 'new')]
                        if ratio >= 0.45:
                            options.append((scores[i-1][j-1] + ratio, 'pair'))
                        scores[i][j], step = max(options, key=lambda item: item[0])
                        steps[i, j] = step, ratio
                i, j = m, n
                while i and j:
                    step, ratio = steps[i, j]
                    if step == 'pair':
                        matched[j1+j-1] = (i1+i-1, ratio)
                        i -= 1; j -= 1
                    elif step == 'old': i -= 1
                    else: j -= 1
        used = {oi for oi, ratio in matched.values()}
        for ni, block in enumerate(new):
            pair = matched.get(ni)
            result[block['id']] = {'status': ('same' if a[pair[0]] == b[ni] else 'changed') if pair else 'new',
                                  'prev': old[pair[0]]['id'] if pair else None, 'ratio': pair[1] if pair else 0}
        result['_dropped_' + doc] = [o for i, o in enumerate(old) if i not in used]
    return result

def main():
    c = cli(__doc__)
    current, previous = path_for(c, 'blocks'), path_for(c, 'previous_blocks')
    write(path_for(c, 'diff'), compare(read(previous), read(current), previous.parent, current.parent))

if __name__ == '__main__': main()
