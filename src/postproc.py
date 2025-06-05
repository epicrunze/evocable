import os
import subprocess

def process_audio(input_wav, output_aac, output_opus):
    """Normalize to –23 LUFS, fade in/out, transcode to AAC and Opus."""
    # Normalize and fade, then transcode
    norm_cmd = [
        'ffmpeg', '-y', '-i', input_wav,
        '-af', 'loudnorm=I=-23:LRA=7:TP=-2,afade=t=in:ss=0:d=0.5,afade=t=out:st=2:d=0.5',
        '-ar', '44100', '-ac', '1', '-f', 'wav', 'pipe:1'
    ]
    # AAC
    with open(output_aac, 'wb') as aac_out:
        subprocess.run(norm_cmd + ['-c:a', 'aac', '-b:a', '96k', '-f', 'adts', output_aac], check=True)
    # Opus
    with open(output_opus, 'wb') as opus_out:
        subprocess.run(norm_cmd + ['-c:a', 'libopus', '-b:a', '64k', output_opus], check=True)

def main():
    input_dir = '/data/input'
    output_dir = '/data/output'
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(input_dir):
        if fname.endswith('.wav'):
            in_path = os.path.join(input_dir, fname)
            base = fname[:-4]
            process_audio(in_path, os.path.join(output_dir, base + '.aac'), os.path.join(output_dir, base + '.opus'))

if __name__ == '__main__':
    main() 