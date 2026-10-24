#!/bin/bash
# (copied from the session scratch; paths assume the repo at /home/user/lanbai-assets and the harness from pkg/engineering extracted to Engineering/)
H=/home/user/lanbai-assets/Engineering/render_harness/lbh_render.py
S="/home/user/lanbai-assets/Act04c_Inside/Docs~/lookdev/scene_4c.py"
seq() { name=$1 cam=$2 t0=$3 t1=$4 fps=$5
  mkdir -p /tmp/claude-0/seq_$name
  ~/bpy/bin/python -c "import numpy as np;print('\n'.join('%.4f'%t for t in np.arange($t0,$t1,1/$fps)))" | nl -v0 | while read i t; do
    o=/tmp/claude-0/r/seq_${name}_$i
    ~/bpy/bin/python $H --scene "$S" --cam $cam --t $t --grade S4c --act 04c --lens clean --interior-ambient 0.045,0.052,0.068 --glass --res 320x180 --samples 4 --out $o > /dev/null 2>&1
    cp $o/graded.png /tmp/claude-0/seq_$name/$(printf 'f%05d.png' $i); rm -rf $o
  done
  ~/bpy/bin/python /home/user/lanbai-assets/Art/tools/lens_tech/flashcheck.py /tmp/claude-0/seq_$name --fps $fps --out /tmp/claude-0/seq_$name/report > /dev/null 2>&1
  echo "done $name"
}
seq seam hero 179.60 182.6 30
seq sleeve hero_side 224.0 232.0 15
