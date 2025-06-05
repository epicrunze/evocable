import os
import spacy

nlp = spacy.load('en_core_web_sm')

SSML_BREAK = '<break time="500ms"/>'
SSML_EMPHASIS = '<emphasis level="moderate">{}</emphasis>'


def chunk_text(text, chunk_size=1000):
    """Chunk text into ~chunk_size character segments."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


def ssmlify(text):
    """Insert SSML tags for breaks and emphasis."""
    doc = nlp(text)
    out = ''
    for sent in doc.sents:
        sent_text = sent.text
        if sent_text.strip():
            out += SSML_EMPHASIS.format(sent_text.strip()) + SSML_BREAK
    return out


def main():
    input_dir = '/data/input'
    output_dir = '/data/output'
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(input_dir):
        with open(os.path.join(input_dir, fname), encoding='utf-8') as f:
            text = f.read()
        ssml = ssmlify(text)
        for idx, chunk in enumerate(chunk_text(ssml)):
            with open(os.path.join(output_dir, f'{fname}_chunk{idx+1}.ssml'), 'w', encoding='utf-8') as out:
                out.write(chunk)

if __name__ == '__main__':
    main() 