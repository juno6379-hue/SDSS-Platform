"""제출 PDF를 변경하지 않고 페이지별 원문과 검색 인덱스를 만든다."""
import hashlib
import json
from pathlib import Path
import pymupdf as fitz

root = Path('tmp/proposal')
keywords = ['LCLUC', 'MLOps', 'SDSS', 'Dynamic World', 'WorldCover', 'TECH-4', 'GeoAI', 'downscal', 'biodiversity', 'subsidence', 'RDTR', 'RAG', 'U-Net', 'Sentinel', 'accuracy', 'schedule']
index = []
for path in root.glob('*.pdf'):
    doc = fitz.open(path)
    pages = []
    hits = []
    for number, page in enumerate(doc, 1):
        text = page.get_text()
        pages.append(f'\n\n===== PDF PAGE {number} =====\n{text}')
        matched = [word for word in keywords if word.lower() in text.lower()]
        if matched:
            hits.append({'page': number, 'keywords': matched, 'excerpt': text[:300]})
    (root / (path.stem + '.txt')).write_text(''.join(pages), encoding='utf-8')
    index.append({'file': path.name, 'pages': len(doc), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'hits': hits})
(root / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(index, ensure_ascii=True, indent=2))
