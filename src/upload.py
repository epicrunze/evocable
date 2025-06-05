import os
import subprocess
import shutil
import sys


def upload_to_s3(local_dir, bucket):
    """Upload directory to S3 bucket using AWS CLI."""
    subprocess.run([
        'aws', 's3', 'sync', local_dir, f's3://{bucket}/', '--delete'
    ], check=True)

def upload_with_rclone(local_dir, remote):
    """Upload directory to remote using rclone."""
    subprocess.run([
        'rclone', 'sync', local_dir, remote, '--delete-during'
    ], check=True)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='/data/input')
    parser.add_argument('--bucket', default=None)
    parser.add_argument('--remote', default=None)
    args = parser.parse_args()
    if args.bucket:
        upload_to_s3(args.input, args.bucket)
    elif args.remote:
        upload_with_rclone(args.input, args.remote)
    # Clean up temp files
    for fname in os.listdir(args.input):
        fpath = os.path.join(args.input, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
        elif os.path.isdir(fpath):
            shutil.rmtree(fpath)

if __name__ == '__main__':
    main() 