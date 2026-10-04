#!/bin/sh
# Rebuilds every file in brand/: the pizza-% mark (icon.js), the lockups with their text
# converted to outlines (make_logo.py: needs `pip install uharfbuzz fonttools brotli`),
# then the PNGs (export_png.mjs, using the video project's Playwright).
set -e
cd "$(dirname "$0")"
npm install --no-audit --no-fund
node --input-type=module -e "import { iconSVG } from './icon.js'; import { writeFileSync } from 'node:fs'; writeFileSync('icon.svg', iconSVG())"
python3 make_logo.py
node export_png.mjs
