import os
import sys
import chardet
import pdfplumber
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image


def detect_encoding(file_path):
    """Detect file encoding for TXT files."""
    with open(file_path, 'rb') as f:
        raw = f.read(4096)
    return chardet.detect(raw)['encoding'] or 'utf-8'


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber and OCR for images."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + '\n'
            else:
                im = page.to_image(resolution=300).original
                text += pytesseract.image_to_string(im) + '\n'
    return text


def extract_text_from_epub(epub_path):
    """Extract text from EPUB using ebooklib and BeautifulSoup."""
    book = epub.read_epub(epub_path)
    text = ""
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text += soup.get_text() + '\n'
    return text


def extract_text_from_txt(txt_path):
    """Extract text from TXT, normalizing encoding."""
    encoding = detect_encoding(txt_path)
    with open(txt_path, 'r', encoding=encoding) as f:
        return f.read()


def main():
    """Main extraction entrypoint."""
    input_dir = '/data/input'
    output_dir = '/data/output'
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(input_dir):
        fpath = os.path.join(input_dir, fname)
        if fname.lower().endswith('.pdf'):
            text = extract_text_from_pdf(fpath)
        elif fname.lower().endswith('.epub'):
            text = extract_text_from_epub(fpath)
        elif fname.lower().endswith('.txt'):
            text = extract_text_from_txt(fpath)
        else:
            continue
        # Simple chapter marker: split by 'Chapter' or every 10k chars
        chapters = text.split('Chapter') if 'Chapter' in text else [text[i:i+10000] for i in range(0, len(text), 10000)]
        for idx, chapter in enumerate(chapters):
            out_path = os.path.join(output_dir, f'chapter_{idx+1}.txt')
            with open(out_path, 'w', encoding='utf-8') as out:
                out.write(chapter.strip())

if __name__ == '__main__':
    if '--healthcheck' in sys.argv:
        sys.exit(0)
    main() 