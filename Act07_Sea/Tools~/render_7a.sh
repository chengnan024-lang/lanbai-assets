#!/bin/bash
# Act 7a reference frames (README_Act07a §5). Run from the repo root:  bash Act07_Sea/Tools~/render_7a.sh [frame-name ...]
# Outputs Act07_Sea/Docs~/iterations/<NN_name>/ (graded.png, metrics.json, note.txt; the big linear files are removed).
cd "$(dirname "$0")/../.."
IT="Act07_Sea/Docs~/iterations"
mkdir -p "$IT"
grade() { python3 -c "t=$1; w=min(max((t-474.36)/(644.96-474.36),0),1); print('S7a' if w<=0 else ('S7b' if w>=1 else 'S7a+S7b=%.3f'%w))"; }
amb() { python3 -c "
import sys; sys.path.insert(0,'Act07_Sea/Tools~'); import act07_motion as AM
d=AM.depth($1); f=min(max(d/60,0),1)
a=[0.0723,0.1351,0.2219]; b=[0.0048*0.3,0.0129*0.3,0.0296*0.3]
print(','.join('%.4f'%(x*(1-f)+y*f) for x,y in zip(a,b)))"; }
R() {
  n=$1; t=$2; shift 2
  ~/bpy/bin/python Engineering/render_harness/lbh_render.py --scene "Act07_Sea/Docs~/lookdev/scene_7a.py" --t $t --grade "$(grade $t)" --act 07a \
      --interior-ambient "$(amb $t)" --out "$IT/$n" "$@" > "/tmp/act07_$n.log" 2>&1
  rm -rf "${IT:?}/${n:?}/linear.exr" "${IT:?}/${n:?}/linear.npy" "${IT:?}/${n:?}/stranger"
  echo "$n $(grep -o 'APL [0-9.]* (target [0-9]*' /tmp/act07_$n.log) $(grep -m1 -i 'Traceback\|Error:' /tmp/act07_$n.log)"
}
want() { [ $# -eq 0 ] && return 0; for x in "$@"; do [ "$x" = "$CUR" ] && return 0; done; return 1; }
ARGS=("$@")
run() { CUR=$1; want "${ARGS[@]}" && R "$@"; }
run 01_F3_up60      367.21 --cam hero --pitch 60 --bus bible_v2 --note "F3 367.21: Snell's window through the skylight (roof still whole), hero eye, pitch 60" &
run 02_F3_fwd       367.21 --cam hero --pitch 0 --bus bible_v2 --note "F3 367.21 forward: shafts slanting down, snow rising past (APL target 85)" &
run 03_387_vr_auto  387.0  --cam vr_left_fwd --pitch 90 --bus bible_v2 --vr --set vr=1 --set roofhole=auto --note "387 VR straight up, roof eroded by t (el >= 70 - 120 x erosion), VR window ceiling by erosion (D-23 #2)" &
wait
run 04_387_vr_worst 387.0  --cam vr_left_fwd --pitch 90 --bus bible_v2 --vr --set vr=1 --set roofhole=40 --note "387 VR straight up, WORST case: the whole roof above el 40 gone (az -180..180), VR ceiling: D-09 APL <= 150" &
run 05_F4_trails    448.2  --cam hero --yaw 115 --pitch -15 --bus bible_v2 --note "F4 446.01+: the first bioluminescence runs along the hull, three lines receding to the rear (right side window, looking back)" &
run 06_F4p_gather   462.36 --cam hero --pitch 35 --bus bible_v2 --note "F4p 462.36: the shafts gathered into the skylight hole" &
wait
run 06b_F4p_side_up 461.0  --cam hero --yaw 80 --pitch 30 --bus bible_v2 --note "F4p gathering (461, the gather ~97 %): from the right side window looking up, the shafts converge on the roof outside the bus" &
wait
run 07_F3e1_last    512.0  --cam hero --pitch 40 --bus bible_v2 --note "F3e1 512.0: the window shrinking (gain x ~0.24 on the way to 0.04 at 514.36), the last wide shaft over the seats" &
run 07b_F3e1_509    509.0  --cam hero --yaw 150 --pitch 55 --bus bible_v2 --set roofhole=auto --note "F3e1 509: the last wide shaft sweeping past overhead, up and back through the eroded roof (el >= 70 - 120 x erosion)" &
wait
run 07c_F3e1_515    515.0  --cam hero --pitch 75 --bus bible_v2 --set roofhole=54 --note "F3e1 515: straight up through the eroded roof, the Snell window is a dark coin (gain x 0.04)" &
run 07a_F3e1_505    505.0  --cam hero --pitch 75 --bus bible_v2 --set roofhole=54 --note "F3e1 505 (just before): the same view, the window still bright: compare 07c" &
run 08_F3e2_ridge   532.36 --cam hero --yaw 75 --pitch 5 --bus bible_v2 --note "F3e2 532.36: the ridge wall rising past the right window, edged by the hull light" &
run 08b_ridge_top   520.36 --cam hero --yaw 70 --pitch 20 --bus bible_v2 --note "F3e2 enters (520.36): the ridge top rising past the right window, el ~20 (review r1 #8)" &
run 09_F3e3_dark    556.36 --cam hero --pitch 0 --bus bible_v2 --note "F3e3 556.36: the last blue goes out (APL target 25)" &
wait
run 10_seeding      612.0  --cam hero --pitch 10 --bus bible_v2 --note "seeding (F3i ->): cold lights sown one by one, fixed in the water" &
run 11_F5_warm      647.0  --cam hero --yaw -22 --pitch -10 --bus bible_v2 --note "F5 644.96: far below, one warm point among the cold seeds (APL target 16)" &
wait
# ---- act 7c (README §9): the mirror below, the inverted window, the fog by time (scene_7a's 7c branch)
run 13_F8a_down      848.86 --cam hero --yaw 90 --pitch -35 --bus bible_v2 --note "F8a 848.86: far below, the dark mirror appears (110 m, mostly fog), the palace lamps reflected in it" &
run 14_F8b_fwd       877.96 --cam hero --pitch 0 --bus bible_v2 --note "F8b 877.96 forward: the trembling stops; APL target 20" &
run 15_897_side_down 897.96 --cam hero --yaw 90 --pitch -35 --bus bible_v2 --note "897.96 out of the right side window, looking down: the dark mirror with the palace lamps, the window's rim at the bottom" &
wait
run 16_897_down_nobus 897.96 --cam hero --pitch -45 --bus none --note "897.96 straight-ish down, no bus (the D-23 stranger frame): the inverted window = a dusk sky in the water below" &
run 12_7c_897_fwd    897.96 --cam hero --pitch 0 --bus bible_v2 --note "D-23: 897.96 forward through the windscreen (7c, before surfacing): the dark dip must stay APL 30-34" &
run 17_910_down_nobus 910.0 --cam hero --pitch -60 --bus none --note "F8c+ 910: the fog thinning, the window clearer (no bus)" &
wait
run 18_921_fwd       921.4  --cam hero --pitch 0 --bus bible_v2 --note "921.4 forward: the last of the dip, APL target 34 (bible: the dusk does not light up before the exit)" &
run 19_921_side_down 921.4  --cam hero --yaw 90 --pitch -40 --bus bible_v2 --note "921.4 right side window down: the mirror 1.4 m below, the window under the bus" &
wait
# D-26: the floor hole in front of the main seat (README §9.1): az -22..22, el -70..-38 from the main eye
run 20_897_floorhole 897.96 --cam hero --pitch -52 --bus bible_v2 --set floorhole=-22,22,-70,-38 --note "D-26 897.96: down through the eroded floor in front of the main seat (az -22..22, el -70..-38): the inverted window's warm ring and rose-gold arc ahead, the indigo core near the feet" &
run 21_921_floorhole 921.4  --cam hero --pitch -52 --bus bible_v2 --set floorhole=-22,22,-70,-38 --note "D-26 921.4: the same hole, the mirror 1.4 m below the eye: the same angles (the window is a cone), the fog thinner" &
wait
