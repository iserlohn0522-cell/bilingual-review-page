"""Generate two fictional Word editions, translations and portable configurations."""
import argparse
import json
import struct
import zlib
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def draw_png(path):
    # Original geometric illustration, generated with the Python standard library.
    width, height = 320, 100
    raw = b''.join(b'\x00' + b''.join(bytes((50, 105, 160) if 25 < x < 290 and 25 < y < 75 else (240, 245, 250)) for x in range(width)) for y in range(height))
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))

def document(path, version, image, supplement=False):
    doc = Document()
    doc.core_properties.author = 'Example Author'
    doc.core_properties.last_modified_by = 'Example Author'
    doc.core_properties.comments = 'Fictional test fixture'
    for name in ('Normal', 'Title', 'Heading 1', 'Caption'):
        doc.styles[name].font.name = 'Calibri'
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
    doc.styles['Normal'].font.size = Pt(11)
    if supplement:
        doc.add_heading('Lantern Library Notes', 0)
        doc.add_paragraph('These notes describe an imaginary reading room.')
        doc.add_paragraph('The spare key stays in a blue box.' if version == 1 else 'The spare key stays in a green box.')
    else:
        doc.add_heading('The Lantern Library', 0)
        doc.add_heading('Opening the room', 1)
        doc.add_paragraph('In the imaginary village of Bellwick, a tiny library opens every Friday.' if version == 1 else 'In the imaginary village of Bellwick, a tiny library opens every Saturday.')
        doc.add_paragraph('Visitors leave a paper star beside the book they enjoyed most.')
        if version == 2:
            doc.add_paragraph('A quiet corner now holds a basket of illustrated maps.')
        doc.add_paragraph('Table 1. The fictional shelf plan.', style='Caption')
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        for cell, text in zip(table.rows[0].cells, ('Shelf', 'Books')): cell.text = text
        for values in [('River', '8'), ('Cloud', '6' if version == 1 else '9')]:
            for cell, text in zip(table.add_row().cells, values): cell.text = text
        doc.add_picture(str(image), width=Inches(3.5))
        doc.add_paragraph('Figure 1. An imaginary blue reading bench.', style='Caption')
        doc.add_heading('References', 1)
        doc.add_paragraph('1. Robin Vale. A Guide to Imaginary Libraries. Fictional Press, 2025.')
    doc.save(path)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True, help='Example directory to populate')
    args = parser.parse_args()
    dest = args.directory.resolve()
    generated = dest / 'generated'
    generated.mkdir(parents=True, exist_ok=True)
    draw_png(generated / 'bench.png')
    for version in (1, 2):
        document(generated / f'story_v{version}.docx', version, generated / 'bench.png')
        document(generated / f'notes_v{version}.docx', version, generated / 'bench.png', True)
        config = {'title': f'The Lantern Library v{version}', 'languages': {'source': 'English', 'target': '中文'},
                  'storage_key': f'lantern-library-demo-v{version}', 'page_notes': 'page_notes.md',
                  'documents': {'main': {'label': '正文', 'docx': f'generated/story_v{version}.docx'},
                                'si': {'label': '补充材料', 'docx': f'generated/notes_v{version}.docx'}},
                  'blocks': f'output/v{version}/blocks.json', 'translation_work': f'output/v{version}/translation_work.json',
                  'authored': [f'translations_v{version}.json'], 'strict': f'output/v{version}/strict.json',
                  'summary': f'output/v{version}/summary.json', 'html': 'output/example_review.html' if version == 2 else 'output/v1/review.html'}
        if version == 2:
            config.update(previous_blocks='output/v1/blocks.json', previous_strict='output/v1/strict.json',
                          previous_summary='output/v1/summary.json', diff='output/v2/diff_map.json')
        write(dest / f'config_v{version}.json', config)
    print('Created fictional fixtures and configurations.')

if __name__ == '__main__': main()
