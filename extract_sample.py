import re
import json
import random
from pathlib import Path

import pandas as pd
import pdfplumber

PDF_DIR = Path('TCE/TCE/pdf-files-2006-2026')
OUT_PATH = Path('processed\sample_6.parquet')

# Right column starts consistently at x ~311 across all documents.
# Splitting at page_width/2 (~297) cleanly isolates it from the counselor roster.
INDICE_ENTRY = re.compile(r'^(.+?)\s*\.{3,}\s*(\d+)\s*$')


def find_pdfs_with_indice():
    pdfs = {}
    for pdf in PDF_DIR.rglob('*.pdf'):
        m = re.search(r'doe_tceal_(\d+)\.pdf', pdf.name)
        if m:
            sid = int(m.group(1))
            if sid >= 1990:
                pdfs[sid] = pdf
    return pdfs


def parse_indice(page):
    """
    Crop to the right column of page 1 then extract índice entries.
    The counselor roster lives entirely in the left half (x < page.width/2),
    so cropping eliminates the bleed-through entirely.

    Bold detection: pdfplumber exposes fontname per character. Any line where
    the majority of characters use a font containing 'Bold' is marked bold=True.
    Bold entries are section/organ/counselor headers; regular entries are act types.
    """
    x_split = page.width / 2
    right_col = page.crop((x_split, 0, page.width, page.height))

    # Build a map of y-bucket → {words, bold_char_count, total_char_count}
    lines: dict[int, dict] = {}
    for w in right_col.extract_words(keep_blank_chars=True):
        bucket = round(w['top'] / 5) * 5
        lines.setdefault(bucket, {'words': [], 'bold': 0, 'total': 0})
        lines[bucket]['words'].append(w['text'])

    # Count bold vs total chars per line using character-level font data
    for ch in right_col.chars:
        bucket = round(ch['top'] / 5) * 5
        if bucket in lines:
            lines[bucket]['total'] += 1
            if 'Bold' in ch.get('fontname', ''):
                lines[bucket]['bold'] += 1

    entries = []
    for bucket in sorted(lines):
        line = ' '.join(lines[bucket]['words']).strip()
        m = INDICE_ENTRY.match(line)
        if m:
            total = lines[bucket]['total']
            bold = lines[bucket]['bold'] > 0 and (lines[bucket]['bold'] / total) > 0.4
            entries.append({
                "act": m.group(1).strip(),
                "page": int(m.group(2)),
                "bold": bold,
            })

    return entries


def extract_pdf(source_id, pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        pages_text = []
        
        for page in pdf.pages:
            x_split = page.width / 2
            
            # Recorta a página nas metades esquerda e direita
            left_col = page.crop((0, 0, x_split, page.height))
            right_col = page.crop((x_split, 0, page.width, page.height))
            
            # Extrai o texto de forma isolada, coluna por coluna
            left_text = left_col.extract_text() or ''
            right_text = right_col.extract_text() or ''
            
            # Junta os textos: primeiro a esquerda, depois uma quebra de linha, depois a direita
            page_full_text = f"{left_text}\n{right_text}".strip()
            pages_text.append(page_full_text)

        # O índice ainda precisa do crop específico dele na primeira página
        indice = parse_indice(pdf.pages[0])

    # O resto continua igual
    full_text = '\n\n--- PAGE BREAK ---\n\n'.join(pages_text)

    header = pages_text[0][:300]
    date_match = re.search(r'\d{1,2} de \w+ de \d{4}', header)
    edition_match = re.search(r'Nº\s*(\d+)', header)

    return {
        'source_id': source_id,
        'pdf_path': str(pdf_path),
        'total_pages': total_pages,
        'edition_number': edition_match.group(1) if edition_match else None,
        'header_date_raw': date_match.group(0) if date_match else None,
        'has_indice': len(indice) > 0,
        'indice': json.dumps(indice, ensure_ascii=False),
        'full_text': full_text,
    }


def main():
    all_pdfs = find_pdfs_with_indice()
    print(f'Available PDFs with índice (source_id >= 1990): {len(all_pdfs)}')

    random.seed(99)
    sample_ids = sorted(random.sample(sorted(all_pdfs.keys()), 6))
    print(f'Selected source_ids: {sample_ids}\n')

    records = []
    for sid in sample_ids:
        path = all_pdfs[sid]
        print(f'Extracting source_id={sid} ({path.name})...')
        record = extract_pdf(sid, path)
        indice = json.loads(record['indice'])
        print(f'  pages={record["total_pages"]} | date={record["header_date_raw"]} | indice_entries={len(indice)} | text_chars={len(record["full_text"]):,}')
        for entry in indice:
            bold_marker = '●' if entry.get('bold') else '○'
            print(f'    p.{entry["page"]:>3}  {bold_marker}  {entry["act"]}')
        records.append(record)

    df = pd.DataFrame(records)
    df.to_parquet(OUT_PATH, index=False)
    print(f'\nSaved → {OUT_PATH}')
    print(df[['source_id', 'edition_number', 'header_date_raw', 'total_pages', 'has_indice']].to_string())


if __name__ == '__main__':
    main()
