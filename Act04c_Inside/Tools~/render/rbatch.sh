#!/bin/bash
# (copied from the session scratch; paths assume the repo at /home/user/lanbai-assets and the harness from pkg/engineering extracted to Engineering/)
# usage: RUN=r03 NOTE="..." rbatch.sh "t cam" ...
H=/home/user/lanbai-assets/Engineering/render_harness/lbh_render.py
S=/home/user/lanbai-assets/Act04c_Inside/Docs~/lookdev/scene_4c.py
AMB=${AMB:-0.045,0.052,0.068}
for spec in "$@"; do
  set -- $spec
  ~/bpy/bin/python $H --scene $S --cam $2 --t $1 --grade S4c --act 04c --lens clean --interior-ambient $AMB --glass --res ${RES:-960x540} --samples ${SPP:-16} --out /tmp/claude-0/r/${RUN}_${1}_$2 --note "$NOTE" 2>&1 | grep '\[lbh\]'
done
