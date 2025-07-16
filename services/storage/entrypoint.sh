#!/bin/bash
set -e

# Ensure /data/meta is owned by the app user
chown -R app:app /data/meta
chmod -R 755 /data/meta

# Optionally fix other /data subdirs
chown -R app:app /data/text /data/wav /data/ogg || true
chmod -R 755 /data/text /data/wav /data/ogg || true

# Run the main application (as app user)
exec "$@" 