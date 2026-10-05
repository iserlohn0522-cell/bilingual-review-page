"""Configuration and JSON helpers shared by the command line tools."""
import argparse
import hashlib
import json
from pathlib import Path

STRICT = {'title', 'heading', 'text', 'caption'}
SUMMARY = {'text', 'caption', 'table', 'math'}

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def path_for(config, key, required=True):
    value = config.get(key)
    if not value:
        if required:
            raise ValueError(f'Missing configuration field: {key}')
        return None
    return (config['_base'] / value).resolve()

def load_config(path):
    config = read(path)
    config['_base'] = Path(path).resolve().parent
    config.setdefault('title', 'Bilingual review')
    config.setdefault('languages', {'source': 'English', 'target': '中文'})
    if not isinstance(config.get('storage_key'), str) or not config['storage_key'].strip():
        raise ValueError('Set a unique, nonempty storage_key for this review.')
    if 'main' not in config.get('documents', {}) or set(config['documents']) - {'main', 'si'}:
        raise ValueError('documents must contain main and may contain si.')
    return config

def cli(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--config', required=True, help='JSON configuration; paths are relative to this file')
    return load_config(parser.parse_args().config)

def validate_translations(blocks, strict, summary):
    for label, data, kinds in [('strict', strict, STRICT), ('summary', summary, SUMMARY)]:
        expected = {b['id'] for b in blocks if b['kind'] in kinds}
        missing, extra = expected - set(data), set(data) - expected
        empty = [k for k, v in data.items() if not isinstance(v, str) or not v.strip()]
        if missing or extra or empty:
            raise ValueError(f'{label}: missing={sorted(missing)}, extra={sorted(extra)}, empty={empty}')
