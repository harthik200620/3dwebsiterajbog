#!/bin/sh
# Renders every food shot used in the video (about 1.5-2 hours on 4 CPU cores), then grades them.
set -e
cd "$(dirname "$0")"
python3 cheese_pull.py renders/pull_exr frames=60 w=720 h=1280 samples=24
python3 pizza_scene.py hero renders/hero.exr w=1080 h=1920 samples=64 elev=26 dist=2.7
python3 pizza_scene.py top renders/top.exr w=1080 h=1080 samples=48
python3 grade.py renders/pull_exr renders/pull
python3 grade.py renders/hero.exr renders/hero.jpg
python3 grade.py renders/top.exr renders/top.jpg
