#!/bin/bash
cd "$(dirname "$0")"
for s in U6 U7 U8; do python3 render_tear.py $s 1920 1080 32 final/Tear_$s 2>&1 | grep -E "render |rror"; done
python3 render_tear.py U6 1920 1080 32 final/Tear_U6_detail --set=hfov:26,aim:5.2 2>&1 | grep -E "render |rror"
python3 render_tear.py U7 1920 1080 32 final/Tear_U7_detail --set=hfov:40,aim:8.6 2>&1 | grep -E "render |rror"
echo ALLDONE
