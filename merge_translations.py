"""Merge authored JSON translations and validate exact, nonempty coverage."""
from common import cli, path_for, read, write, validate_translations
from prepare_translations import prepare

def main():
    c = cli(__doc__)
    # Recompute reuse so a stale worklist cannot silently release old translations.
    work = prepare(c)
    strict, summary, seen = work['strict'], work['summary'], set()
    files = c.get('authored', [])
    if not isinstance(files, list): raise ValueError('authored must be a list of JSON file paths')
    blocks = read(path_for(c, 'blocks'))['blocks']
    known = {b['id'] for b in blocks}
    for file in files:
        data = read(c['_base'] / file)
        for bid, fields in data.items():
            if bid not in known or bid in seen: raise ValueError(f'Unknown or duplicate authored id: {bid}')
            if not isinstance(fields, dict) or set(fields) - {'strict', 'summary'}: raise ValueError(f'Invalid fields for {bid}')
            seen.add(bid)
            if 'strict' in fields: strict[bid] = fields['strict']
            if 'summary' in fields: summary[bid] = fields['summary']
    validate_translations(blocks, strict, summary)
    write(path_for(c, 'strict'), strict)
    write(path_for(c, 'summary'), summary)
    print(f'Translations complete: strict={len(strict)}, summary={len(summary)}')

if __name__ == '__main__': main()
