import os
import subprocess

def hls_segment(input_audio, output_dir, base_name):
    """Segment audio into HLS .ts and .m3u8 playlist."""
    os.makedirs(output_dir, exist_ok=True)
    playlist = os.path.join(output_dir, f'{base_name}.m3u8')
    cmd = [
        'ffmpeg', '-y', '-i', input_audio,
        '-c:a', 'aac', '-b:a', '96k',
        '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, f'{base_name}_%03d.ts'),
        playlist
    ]
    subprocess.run(cmd, check=True)

def main():
    input_dir = '/data/input'
    output_dir = '/data/output'
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(input_dir):
        if fname.endswith('.aac'):
            base = fname[:-4]
            hls_segment(os.path.join(input_dir, fname), output_dir, base)

if __name__ == '__main__':
    main() 