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
               hfov=90.0, aspect=16 / 9, bus=True, look=dict(moon_disc_gain=0.6),
               note='U7_engelein (the hero): the hands closing, the Engel bending over, colossus 2 taking the moon'),
    'U8fwd': dict(t=G.CUE['U8'] + 3.5, cue='U8 + 3.5 s, straight ahead (bible acceptance frame)', eye=G.EYE_SEATED,
                  yaw=0.0, pitch=0.0, hfov=90.0, aspect=16 / 9, bus=True,
                  note='U8_forward: the wound has outgrown the windscreen; the gate pillars have just passed'),
    'U8a': dict(t=G.CUE['U8'] + 8.0, cue='U8 + 8.0 s (... Ich liess mich nicht abweisen), looking up through the skylight',
                eye=G.EYE_SEATED, yaw=0.0, pitch=49.0, hfov=50.0, aspect=16 / 9, bus=True,
                # round 8 (awe r4 M3 / tech M7): U8 + 8.5 (the white fills ~70 % of the glass), no dust over the shell or the
                # white, the well's reveal faces lit, a faint glow ring on the ceiling round the opening
                # round 8b: U8 + 8.0 (U8 + 8.5 put the Engel's right-lip coil in the glass as a full black ring, a tyre;
                # at + 8.0 only its arc enters the lower right corner), the flap as dark cloth with a lit torn edge
                look=dict(tubes=0.0, clean_shell=1.0, spot=1.0, beam_gain=0.06, dust_gain=0.0, well_lit=0.55, well_ring=0.35,
                          flap_inner=0.25, flap_sheen=0.1),
                note='U8a_ach_nein (round 4, AD round 3 item 6): the skylight (its glass ~33 % of the frame, centred) full of the '
                     'wound; one clean dark frame; its light falling into the cabin (beam + dust). The shell is a placeholder.'),
    'U8b': dict(t=G.CUE['U9'] - 4.0, cue='U9 - 4 s: the skylight spot has walked up the aisle to the seats',
                eye=G.EYE_AISLE, yaw=6.0, pitch=-13.0, hfov=90.0, aspect=16 / 9, bus=True, look=dict(spot=1.0, tubes=0.22),
                note='U8b_spot: down the aisle: the wound\'s light falling through the skylight at your feet, its beam '
                     'in the cabin dust'),
    'U8side': dict(t=G.CUE['U8'] + 0.3, cue='U8 + 0.3 s: the right gate pillar slides past the side windows (abeam)',
                   eye=G.EYE_SEATED, yaw=112.0, pitch=8.0, hfov=84.0, aspect=16 / 9, bus=True,
                   look=dict(shell_paint='#6A675F', tubes=0.18, collars=0.0),        # round 8 (tech m10): the placeholder B-pillar was the brightest thing
                   note='U8_side (round 3): the right gate pillar abeam-behind: its foot, its cloud dome and sleeve in the side '
                        'glass, the body rising and cut by the window header (side deck impostor side3)'),
    # round 4 (tech m8): no final showed a NEAR arm (8-20 m), the most VR-sensitive element. Near_1 passes the right
    # side windows at 15-16 m from the hero eye (11.5 m from the shell) at U8 + 1.6 .. + 2.2.
    'U8near': dict(t=G.CUE['U8'] + 1.6, cue='U8 + 1.6 s: a near arm surges past the right side windows (11.5 m from the shell)',
                   eye=G.EYE_SEATED, yaw=100.0, pitch=4.0, hfov=84.0, aspect=16 / 9, bus=True, deck='side3',
                   look=dict(shell_paint='#6A675F', tubes=0.18, collars=0.0),
                   note='U8_near (tech m8): Near_1 at ~16 m from the eye: razor rim, wet streaks, sway; the right side glass'),
    'rear': dict(t=G.CUE['U9'] - 2.0, cue='U9 - 2 s (just before Ich bin von Gott): the hand closes behind',
                 eye=G.EYE_STAND_REAR, yaw=180.0, pitch=12.0, hfov=78.0,
                 # round 4 (AD round 3 item 5): no glory ring (it read as a lens smudge / an eye), colossal portcullis arms
                 # round 8 (awe r4 M4 / tech M3): arms darker than the void (albedo x 0.5, fog 0.35) with a 1.5 px moon rim, a
                 # raised back band (L* 12-16 at el 0-6: a silver horizon), a front-lit plain with crests, a window border
                 look=dict(shaft=0.0, halo=0.0, wedge=0.0, deck_tag='rear4', glory=0.0, deck_moonward=0.0,
                           cloud_top_col=(0.10, 0.11, 0.13), rimw_rear=0.0, rim_gain_rear=0.5, alb_rear=0.5,
                           back_band=1.25, deck_fog=0.45, deck_gain=1.3, deck_soft=0.7, deck_soft_px=10.0, deck_hfeather=1.5, rear_frame=0.05, rim_moon_px=1.5,
                           deck_quiet=0.0, mist=0.35),
                 aspect=16 / 9, bus=True, note='rear_window: the Orpheus shot, colossal arms closing behind the bus like a '
                         'portcullis over a front-lit silver plain; rim light only'),
    'key': dict(t=G.CUE['U7b'] - 0.6, cue='U7b - 0.6 s (key art: colossus 2 has taken ~80 % of the moon (ray-cast), '
                'a sliver remains)', eye=G.EYE_SEATED, yaw=6.0, pitch=7.0, hfov=82.0, look=dict(moon_disc_gain=0.6),
                aspect=2560 / 1072, bus=False, note='keyart_239: the U7 moment without the bus shell'),
}
SHOTS['U8'] = SHOTS['U8a']          # (compat: the run-2 name)
