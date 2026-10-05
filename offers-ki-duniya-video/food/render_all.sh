#!/bin/sh
# Renders every food shot used in the video (about 2 hours on 4 CPU cores), then grades them.
set -e
cd "$(dirname "$0")"
python3 cheese_pull.py renders/pull_exr frames=60 w=864 h=1536 samples=28
python3 pizza_scene.py hero renders/hero.exr w=1080 h=1920 samples=64 elev=26 dist=2.7
python3 pizza_scene.py top renders/top.exr w=1080 h=1080 samples=48
python3 grade.py renders/pull_exr renders/pull exposure=-0.9 sat=1.28 warm=0.06 contrast=1.22 bloom=0.18
# the hero is lit brighter than the pull, so it is graded down to match it
python3 grade.py renders/hero.exr renders/hero.jpg exposure=-1.15 contrast=1.3 sat=1.35 warm=0.06 bloom=0.15
python3 grade.py renders/top.exr renders/top.jpg sat=1.3 warm=0.06 bloom=0.1
