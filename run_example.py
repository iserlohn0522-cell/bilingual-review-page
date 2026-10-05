"""Run the complete fictional example pipeline, without network access."""
import argparse
from pathlib import Path
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path, default=Path(__file__).parent / 'examples', help='Example directory containing authored translations')
    args = parser.parse_args()
    home = Path(__file__).resolve().parent
    examples = args.examples.resolve()
    def run(script, *argv):
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(home / script), *map(str, argv)], check=True)
    run('examples/make_examples.py', '--directory', examples)
    for version in (1, 2):
        config = examples / f'config_v{version}.json'
        run('extract_blocks.py', '--config', config)
        if version == 2: run('diff_blocks.py', '--config', config)
        for script in ('prepare_translations.py', 'merge_translations.py', 'build_review_page.py'):
            run(script, '--config', config)

if __name__ == '__main__': main()
