"""The gate frames (single source for gate_scene.py, gate_plan.py, gate_metrics.py and gate_export.py).
t = timeline seconds; eye = Unity bus-relative; yaw = azimuth from the tear direction (+ right); pitch up +.
Round 2: U8 split into U8a (up through the skylight), U8b (down the aisle at the skylight spot), U8side (a gate
pillar sliding past the side window) and U8fwd (straight ahead, yaw 0 / pitch 0 / FOV 90: the bible's acceptance
frame); the key art camera is pitch 7 / hfov 82 (horizon ~1/3 up, the void in the top quarter)."""
import gate_layout as G

SHOTS = {
    'U6': dict(t=G.CUE['U6'] + 13.0, cue='U6 + 13 s (last second of the Rilke line; colossus 2 rising left of the moon)',
               eye=G.EYE_SEATED, yaw=0.0, pitch=0.0, hfov=90.0, aspect=16 / 9, bus=True,
               note='U6_approach: tear ~14 deg tall inside the windscreen; Rilke line space +20/+3 left clear'),
    'U7': dict(t=G.CUE['U7b'], cue='U7b ...und wollt mich abweisen', eye=G.EYE_SEATED, yaw=0.0, pitch=0.0,
               hfov=90.0, aspect=16 / 9, bus=True,
               note='U7_engelein (the hero): the hands closing, the Engel bending over, colossus 2 taking the moon'),
    'U8fwd': dict(t=G.CUE['U8'] + 3.5, cue='U8 + 3.5 s, straight ahead (bible acceptance frame)', eye=G.EYE_SEATED,
                  yaw=0.0, pitch=0.0, hfov=90.0, aspect=16 / 9, bus=True,
                  note='U8_forward: the wound has outgrown the windscreen; the gate pillars have just passed'),
    'U8a': dict(t=G.CUE['U8'] + 3.5, cue='U8 + 3.5 s (Ach nein! ... Ich liess mich nicht abweisen), looking up',
                eye=G.EYE_SEATED, yaw=8.0, pitch=40.0, hfov=82.0, aspect=16 / 9, bus=True, look=dict(tubes=0.45),
                note='U8a_ach_nein: the skylight (>= 18 % of the frame) full of the wound, which continues in the '
                     'windscreen below'),
    'U8b': dict(t=G.CUE['U9'] - 4.0, cue='U9 - 4 s: the skylight spot has walked up the aisle to the seats',
                eye=G.EYE_AISLE, yaw=6.0, pitch=-13.0, hfov=90.0, aspect=16 / 9, bus=True, look=dict(spot=1.0, tubes=0.22),
                note='U8b_spot: down the aisle: the wound\'s light falling through the skylight at your feet, its beam '
                     'in the cabin dust'),
    'U8side': dict(t=G.CUE['U8'] + 0.3, cue='U8 + 0.3 s: the right gate pillar slides past the side windows (abeam)',
                   eye=G.EYE_SEATED, yaw=112.0, pitch=13.0, hfov=84.0, aspect=16 / 9, bus=True,
                   look=dict(tubes=0.45, collars=0.0),
                   note='U8_side (round 3): the right gate pillar abeam-behind: its foot, its cloud dome and sleeve in the side '
                        'glass, the body rising and cut by the window header (side deck impostor side3)'),
    'rear': dict(t=G.CUE['U9'] - 2.0, cue='U9 - 2 s (just before Ich bin von Gott): the hand closes behind',
                 eye=G.EYE_STAND_REAR, yaw=180.0, pitch=2.0, hfov=84.0,
                 # round 3 (tech M9): global look except the rear deck's exposure calibration (front-lit plain L* ~40
                 # near -> 25 at the horizon, the awe critique's target; Unity: the moon cloud cards seen front-lit)
                 look=dict(shaft=0.0, halo=0.0, wedge=0.0, deck_gain=1.6, deck_tag='rear4', glory=2.5,
                           cloud_top_col=(0.10, 0.11, 0.13)),      # the front-lit plain behind: the roots fade into IT
                 aspect=16 / 9, bus=True, note='rear_window: the Orpheus shot, arms closing behind the bus over a front-lit silver plain (moon behind '
                         'the viewer, the arms\' long shadows run to the horizon)'),
    'key': dict(t=G.CUE['U7b'] - 0.6, cue='U7b - 0.6 s (key art: colossus 2 has taken ~87 % of the moon, a sliver '
                'remains)', eye=G.EYE_SEATED, yaw=6.0, pitch=7.0, hfov=82.0,
                aspect=2560 / 1072, bus=False, note='keyart_239: the U7 moment without the bus shell'),
}
SHOTS['U8'] = SHOTS['U8a']          # (compat: the run-2 name)
