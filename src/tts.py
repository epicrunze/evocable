import os
from concurrent.futures import ThreadPoolExecutor
from TTS.api import TTS


def synthesize_ssml(ssml_path, wav_path, tts):
    """Render SSML file to WAV using TTS."""
    with open(ssml_path, encoding='utf-8') as f:
        ssml = f.read()
    wav = tts.tts(ssml, speaker=tts.speakers[0], language=tts.languages[0], ssml=True)
    tts.save_wav(wav, wav_path)


def main():
    input_dir = '/data/input'
    output_dir = '/data/output'
    os.makedirs(output_dir, exist_ok=True)
    tts = TTS(model_name='tts_models/en/ljspeech/tacotron2-DDC', gpu=True)
    files = [f for f in os.listdir(input_dir) if f.endswith('.ssml')]
    with ThreadPoolExecutor(max_workers=1) as executor:
        for fname in files:
            in_path = os.path.join(input_dir, fname)
            out_path = os.path.join(output_dir, fname.replace('.ssml', '.wav'))
            executor.submit(synthesize_ssml, in_path, out_path, tts)

if __name__ == '__main__':
    main() 