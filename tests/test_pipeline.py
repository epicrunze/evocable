import os
import shutil
import subprocess
import pytest

def setup_module(module):
    os.makedirs('test_input', exist_ok=True)
    with open('test_input/sample.txt', 'w', encoding='utf-8') as f:
        f.write('Hello world. This is a test chapter.\nChapter 2. Another test.')
    os.makedirs('test_output', exist_ok=True)

def teardown_module(module):
    shutil.rmtree('test_input', ignore_errors=True)
    shutil.rmtree('test_output', ignore_errors=True)

def test_pipeline_smoke():
    # Extraction
    subprocess.run(['python', 'src/extract.py'], check=True)
    # Segmentation
    subprocess.run(['python', 'src/segment.py'], check=True)
    # TTS (mocked)
    for fname in os.listdir('test_output'):
        if fname.endswith('.ssml'):
            with open(os.path.join('test_output', fname.replace('.ssml', '.wav')), 'wb') as f:
                f.write(b'RIFF....WAVEfmt ')  # Minimal WAV header
    # Postproc
    subprocess.run(['python', 'src/postproc.py'], check=True)
    # Packaging
    subprocess.run(['python', 'src/package.py'], check=True)
    # Upload (mocked)
    subprocess.run(['python', 'src/upload.py', '--input', 'test_output'], check=True)
    assert True 