#!/bin/bash
# Runtime configuration loader
# Encoded env block is decoded at container start
if [ -f /app/config.dat ]; then
  eval "$(base64 -d < /app/config.dat)"
fi
exec /pentaract
