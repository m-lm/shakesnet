#!/bin/sh
set -e
python3 \
    -W ignore::FutureWarning \
    -m cProfile -s tottime -o perf.log \
    shakesnet.py --op "$@"