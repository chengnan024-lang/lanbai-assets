# 蓝白 / Lanbai: story, poetry and music dramaturgy

Lens: story / poems / music. Written for the synthesizer (who produces the Chinese bible) and for the Unity implementer.

This file sits on top of two others:
- `lens_lookdev.md`: what things look like (materials, light values, typography).
- `lens_cine/grades.json`: the PPv2 profiles.

This file says **when** things happen, **why**, and **what the viewer must feel**. Anything I add or change against those two files is tagged **[NEW]** or **[CHANGE]**; §10 collects them all.

**Conventions**
- **Bus space.**
  - Azimuth 0° is the bus's forward axis; + is to the right (the door side).
  - Elevation 0° is the true horizon. The bus is always level (law 6).
- **Cue labels.**
  - `U3` is a labelled event in the Urlicht audio file (§1.2).
  - `F13` is a labelled event in the finale file (§1.3).
  - `U 3:30` is an estimated time position inside the Urlicht file.
  - The implementer taps the real positions of all cues (§1.4).
- **Hero seat.** First row on the right, directly behind the door. Every key image is tuned for it and must still work from any other seat.

---

## 0. The spine (read this if nothing else)

**Thesis.** 蓝白 is a dream that undyes the night.
- It starts in the deepest indigo of a rainy bus stop.
- It is torn open to the white under the dye.
- It falls through every sky and sea.
- It ends in 藍白, the palest indigo: almost white, never quite.
- Then everything vast comes home small: the Milky Way as fireflies, the bronze mirrors as a puddle, the tear as one tube lamp.

**The grandeur is the journey. The tears are the return.**

**Seven laws** (every scene obeys them):
1. **Music is the clock.** Every image event lands on a musical event: a word, an entry or a cadence. Never on an arbitrary second.
2. **A trough before every peak.** Each awe peak comes after at least 10 s of visual intensity ≤ 3 (§2). Restraint is what makes 震撼 possible. A world that is grand all the time is grand nowhere.
3. **Image first, word second.**
   - A poem appears 4–12 s after its image has landed.
   - It never appears together with its image and never on a peak.
   - There are three deliberate exceptions (Rilke, the Urlicht voice lines, 天问); each is explained where it occurs.
4. **Huge things are silent and slow.**
   - No creature sounds, and no rumble effects over Mahler.
   - Colossal motion stays at or below 0.5°/s angular speed.
   - Scale is felt through slowness and parallax, not through noise.
5. **Nothing touches you.** No tentacle, mirror edge or wave ever touches the bus. The only things that pass through it are bands of light.
   - This is Rilke's point: beauty is terror "because it serenely disdains to destroy us".
6. **The bus never tilts, never shakes, and has no engine.**
   - Pitch and roll are 0° for the whole ride.
   - Yaw changes at most 3°/s.
   - Linear acceleration is at most 1.5 m/s².
   - This is VR comfort, and it is also the clue: the bus never moved.
7. **One continuous shot.** There are no cuts except into darkness (the plunge, 3 s) and into light (the two whites). Every transition is a passage through something:
   - the crest of a hill;
   - a cloud;
   - the tear;
   - the water surface;
   - the sea floor;
   - the mirrors;
   - the white.

---

## 1. The music is the clock

### 1.1 Two recordings, two worlds
- **Urlicht (Ferrier / Klemperer 1951, mono) is the voice in the box.**
  - It belongs to the bus: localised at the radio, narrow-band, human.
  - It is a prayer overheard by one passenger at night.
- **The finale (Walter / NYP 1958, stereo) is the voice of the world.**
  - It has no source. After the plunge the radio is dark and the whole sky sings.
- **The seam between them is the plunge: 3.0 s of true silence.**
  - In the symphony, Urlicht runs straight into the finale's opening scream.
  - **We replace the scream with silence.** We already had the terror at the gate; the fall itself is silent. Add no sound here.

### 1.2 Urlicht cue map
The whole movement is about 5 min. Times are estimates (±20 s); tap the real ones (§1.4).

| Cue | ≈ time | Sung text (meaning) | Image event |
|---|---|---|---|
| U0 | 0:00 | *O Röschen rot!* (O little red rose) | Player seated. The bus is still at the stop, door open, rain. The voice arrives through 2–4 s of radio static. |
| U1 | 0:15 | brass chorale, no voice | **The bus glides off.** No engine: only tyre hiss and rain on the roof. Village stretch, a sodium sweep every 2.5 s. |
| U2 | ≈ 0:50 | the chorale's last phrases | **Dark stretch.** The lamps end and the road climbs. Outside is black; the glass shows only the cabin's own reflection. |
| U3 | ≈ 1:05 | *Der Mensch liegt in größter Not! … in größter Pein!* (Man lies in greatest need, in greatest pain) | **Lift-off at the crest** (§5.3). The sound opens (§1.5). The sea of lights is revealed. Humanity's pain = all those lit windows, seen from above as we leave them. |
| U4 | ≈ 1:55 | *Je lieber möcht' ich im Himmel sein* (I would rather be in heaven) | Climbing toward the orange-lit cloud ceiling. |
| U5 | ≈ 2:35 | orchestral transition | Into the cloud (3–8 s). |
| U6 | ≈ 2:45 | key change, *Etwas bewegter*; *Da kam ich auf einen breiten Weg* (Then I came upon a broad road) | **Break-out into moonlight.** The broad road is the moon's silver glade across the cloud plain, leading to the tear. |
| U7 | ≈ 3:00 | *Da kam ein Engelein und wollt' mich abweisen* (A little angel came and wanted to turn me away) | **The surge.** Tentacles rise and close over the tear. |
| U8 | ≈ 3:15 | *Ach nein! Ich ließ mich nicht abweisen!* (Ah no! I would not be turned away!) | Threading between colossi; the nearest fly-bys; tubes flicker 3/s. |
| U9 | ≈ 3:30 | *Ich bin von Gott und will wieder zu Gott!* (I am from God and will return to God) | **Entry.** The tubes flash to 150% and die. The bus crosses the first rim. |
| U10 | ≈ 3:55 | *Der liebe Gott wird mir ein Lichtchen geben* (Dear God will give me a little light) | Inside the tear. The radio dial, **the Lichtchen**, brightens. |
| U11 | ≈ 4:20 | *wird leuchten mir bis in das ewig selig Leben!* (will light my way into eternal blessed life) | The rims grow brighter; the light ahead grows through the long note on *Leben*. |
| U12 | ≈ 5:00 | the final chord dies away | The light ahead fills the view → FLASH_TEAR (cine helper) → black. |

### 1.3 Finale cue map
The finale is mapped by musical events. Durations differ between performances, so tap them.

| Cue | Musical event | Image event |
|---|---|---|
| F0 | first offstage horn call of *Der große Appell* | The dawn begins to rise 1.0 s after the note: the call comes first, the light answers. |
| F1 | flute and piccolo birdsong over distant brass. Mahler's own programme: *"a far, far-off nightingale, like a last trembling echo of earthly life"* | Falling into the cloud canyon; the sea's glitter below. |
| F2 | the last bird call, then the hush | The glassy sea mirrors the sky. **Water entry on the last bird call.** 1–2 s of underwater quiet. |
| F3 | chorus a cappella, ppp: *Aufersteh'n, ja aufersteh'n wirst du, mein Staub, nach kurzer Ruh'* (Rise again, yes, you will rise again, my dust, after a short rest) | Under the surface. Snell's window overhead; marine snow rising past the windows. |
| F4 | the soprano floats up out of the chorus (*Unsterblich Leben*, immortal life) | The first bioluminescent trail flares along the hull. |
| F5 | orchestral interlude before the alto | The first bronze lamp, far below. |
| F6 | alto: *O glaube, mein Herz, o glaube* (O believe, my heart) | The palace; the main hall's open doors. |
| F7 | *Es geht dir nichts verloren! … Dein, was du geliebt* (Nothing is lost to you … yours is what you loved) | The bus's nearest pass to the doors. |
| F8 | chorus: *Was entstanden ist, das muss vergehen … Bereite dich zu leben!* (What has come into being must perish … prepare yourself to live) | Over the terrace edge; a rose glow below. |
| F9 | duet: *O Schmerz! … O Tod! … Nun bist du bezwungen!* (O pain … O death … now you are conquered) | The fall toward the inverted surface. **Exit into dusk on the orchestral swell after *bezwungen*.** |
| F10 | duet: *Mit Flügeln, die ich mir errungen* (With wings that I have won) | Dusk. The curtains spread like wings; the sea ceiling fades. |
| F11 | chorus: *Mit Flügeln … werde ich entschweben* (… I shall soar away) | On *entschweben*, the curtains let go of their rails and fly off. |
| F12 | *Sterben werd' ich, um zu leben!* (I shall die in order to live) | The sun-line contracts and goes out; night; 天问. |
| F13 | *Aufersteh'n, ja aufersteh'n wirst du, mein Herz, in einem Nu!* (… my heart, in an instant). Organ, fff. | **The Milky Way ignites in one second.** |
| F14 | *Was du geschlagen, zu Gott wird es dich tragen!* (What you have fought for will carry you to God) | The mirrors accelerate. |
| F15 | orchestral peroration with bells and tam-tams | Mirror crossings land on bell strokes. |
| F16 | the final chord | The last mirror reaches the player's eyes → white. |

### 1.4 The cue sheet (the implementer makes it; everything here depends on it)
1. Open each audio file exactly as the build plays it, in Audacity.
2. Place a label at each cue: U0–U12, F0–F16. For F15, also label every bell stroke.
3. Export the label tracks and paste them into a `float[]` on the timeline UdonBehaviour.
4. Push the label files to `FromLocal/` so the cloud side can check the schedules.

Every schedule in this document is written relative to these labels, never to absolute seconds.

**FLAG, conflict inside WORLD.md.**
- WORLD.md calls 星海 "the last ~9 minutes of chorus".
- Its own scene table, however, puts *O glaube* in scene 7 and *Mit Flügeln* in scene 8. That leaves only about 3.5–4.5 min from F12 to the end.
- **I follow the table.** If the build's audio is edited differently, send the labels and we remap. The beats stay attached to the words, whatever the clock says.

### 1.5 Sound rules (the music dramaturgy the implementer needs)
- **No engine, ever.**
  - The bus glides. You hear only tyre hiss (wet in scene 2, dry in scene 11), rain on the roof, and the wipers.
  - The missing engine is the first quiet wrongness and the first clue that the bus never moved.
- **Wipers** [NEW]:
  - one sweep every 5 s in scene 2, with nobody driving;
  - parked from U4, when the rain has thinned;
  - parked in scenes 11 and 12.
- **The radio before U3**
  - Band-pass 350–3400 Hz.
  - 3D sound: min distance 0.4 m, max 7 m.
  - A crackle bed 26 dB under the music.
  - 2–4 s of tuning static before U0.
- **The opening at U3.** Over 8 s, ease-in-out:
  - low cut 350 → 30 Hz;
  - high cut 3400 → 16 kHz (log ramp);
  - `spatialBlend` 1 → 0;
  - crackle −26 → −60 dB;
  - overall level +4 dB.

  The voice leaves the box as the wheels leave the road. Use `AudioHighPassFilter` / `AudioLowPassFilter` on the source. If they are unavailable, crossfade two pre-filtered copies of the file.
- **Tentacles make no sound.** Only the air moves:
  - when one passes within 30 m, a low whoosh (band 60–400 Hz) at −24 dB under the music;
  - the fear sound is small and near: the dying tubes' 100 Hz buzz and a tick at every dip, at −30 dB.
- **During the finale** only two sound effects exist, each at least 24 dB under the music:
  - the water entry: a muffled low thump low-passed at 400 Hz plus a bubble rush, 1.5 s;
  - the water exit: water streaming off, 1 s.

  The mirror crossings are silent: Mahler's bells are their sound.
- **Never low-pass Mahler underwater.** The "sound rising from under water" is Mahler's own ppp chorus. Only sound effects get the underwater filter.
- **The plunge and the whites are digital silence** (zero), not room tone.
- **False awakening:** radio static at −30 dB, the same texture as the static before U0. The radio is searching and finds nothing. Plus dry tyres. No rain.
- **Awakening:** insects, drips, a nightingale flying away (§7). No music, ever again.

---

## 2. Rhythm: where to hold back so the peaks hit

### 2.1 The intensity curve
Intensity runs from 0 (nothing happens) to 10 (the most overwhelming moment in the world). Durations are typical.

| Segment | Music | ≈ Duration | Intensity | What carries it | Text |
|---|---|---|---|---|---|
| 1 Stop | none | the player decides | **1** | one tube, rain | the sign only |
| 2 Night road | U0–U2 | 65 s | 2 → **1** in the dark stretch | sodium sweeps, then darkness | – |
| 3 Lift-off, sea of lights | U3–U4 | 50 s | **6** | ground falls away | 李白 |
| 3 Cloud ceiling, inside the cloud | U4–U6 | 50 s | 4 → 2 | orange ceiling, fog | – |
| 4a Break-out, moon road, tear | U6–U7 | 15 s | 5 (calm beauty) | the moon's road, the tear, stillness | Rilke |
| 4b Surge | U7–U9 | 30 s | **9 (peak 2)** | tentacles in three depth layers | voice lines (small) |
| 4c Inside the tear | U9–U12 | 90 s | 5 (grace) | nested rims of light | – |
| 5 Plunge | silence | 3 s | **0** | black | – |
| 6 Dawn | F0–F1 | ≈ 2 min | 4 | vastness, dust in the beams | 我从天空坠入深海 |
| 6 Cloud canyon, sea mirror | F1–F2 | ≈ 1 min | **6** | cloud walls rising past | – |
| 7 Under the surface, water column | F3–F5 | ≈ 3–4 min | 3 → 2 | Snell's window, rising snow, the dark | – |
| 7 Palace | F5–F7 | ≈ 2 min | **6** | the lit, empty doors | 河伯 |
| 7 Sea floor becomes sky | F8–F9 | ≈ 2 min | 5 → 7 | rose glow below, the fall out | – |
| 8 Dusk mirror world | F9–F12 | ≈ 2 min | **7 (peak 3, serene)** | perfect symmetry, wings | user's line, 庄子 |
| 9a Night is born | F12–F13 | 15–30 s | **2** | the sun goes out | 天问 |
| 9b Milky Way ignites | F13 | 1 s, then a hold | **9** | the whole sphere of stars at once | – |
| 9c Mirrors | F14–F16 | ≈ 135 s | 7 → **10 (peak 1)** | accelerating mirrors, dissolving cabin | – |
| 10 White | F16 + silence | ≈ 15 s | 0 motion, full light | 藍白 | – |
| 11 False awakening | static | 75 s | 2 | normality, then the sea above | 庄子 胡蝶 |
| 12 Awakening | insects | open-ended | **1** (the emotional peak) | one firefly | 李白, Keats |

### 2.2 Peak hierarchy
1. **The final mirrors of 星海** (10). The only moment allowed to be total.
2. **The gate surge** (9), and **the Milky Way ignition** (9).
3. **The dusk mirror world** (7). Awe as serenity, not force.
4. Lift-off reveal, cloud canyon, palace (6 each).

The emotional peak is **not** an intensity peak: it is the Lichtchen firefly in scene 12, at intensity 1 (§7).

### 2.3 How to build a peak (every peak follows these rules)
1. **Trough first:** at least 10 s at intensity ≤ 3 immediately before. The table above places one before every peak:
   - the dark stretch before lift-off;
   - the moonlit calm before the surge;
   - the plunge before dawn;
   - the dark water column before the palace;
   - the dead sun before the Milky Way.
2. **Reveal by passing an edge, never by fading in.** Each reveal comes from the bus moving past something that hid it:
   - the hill crest;
   - the cloud ceiling;
   - the walls of the cloud canyon;
   - the lip of the tear;
   - the edge of the palace terrace.
3. **A known-scale reference in frame:**
   - the bus's own window frame;
   - a 9 m lamp pole;
   - a 400 m cumulus pillar;
   - the palace's 60 m hall.
4. **Three depth layers with parallax.**

   | Layer | Distance | Angular speed |
   |---|---|---|
   | Near | < 50 m | up to 30°/s |
   | Mid | 0.2–1 km | 1–3°/s |
   | Far | > 2 km, in fog | ≤ 0.5°/s |

5. **One focal point per peak, and everything leads to it:**
   - the tear;
   - the palace doors;
   - the sun-line;
   - the Milky Way core;
   - the last mirror.
6. **Hold for at least 8 s after each reveal** with no new event and no text. VR players need that time to turn their heads and take in the scale.
7. **The frame widens as the grandeur grows.**

   | Scenes | Frame |
   |---|---|
   | 1–6 | windows |
   | 7 | holes in the roof |
   | 8 | the walls are gone |
   | 9 | nothing is left |

   The gate is deliberately seen through windows: a frame you cannot see past is part of the fear.

### 2.4 Where to be restrained (these are decisions, not suggestions)
- **Scene 1 is tiny.** No moon, no stars, no visible sky structure, no reveal. The world's first image must be the smallest.
- **Save the moon** for U6.
- **Save the Milky Way** for F13. Until then, stars appear only as the ~200 bright ones on the horizon over the sea of lights, and at gain 0.12 at the gate.
- **Save the full-field white** for scene 10.
  - The tear's inside is never a uniform white (display ≤ 190 between the rims).
  - The dawn never clips to white, except the sun disc.
- **Save pure symmetry** for dusk. Every earlier mirror is broken or partial: ripples, the dark window glass, the rippled sea.
- **No text during the peaks.** Specifically:
  - the surge carries only the small voice lines;
  - F13 and all the mirrors carry nothing;
  - the white carries nothing.
- **One living species per scene at most:**
  - moths at the stop;
  - the fish school in the sea;
  - fireflies at the end.

  No birds shown, no whales, no spirits, no people. Emptiness is the content: *lights on, nobody home*.

### 2.5 Exposure beats (eye adaptation)
These are PPv2 `postExposure` offsets added by helper volumes on top of each scene profile in `grades.json`.

| Moment | Offset | Envelope | Why |
|---|---|---|---|
| Break-out into moonlight (U6) | +0.6 EV | up in 0.3 s, decays over 3 s | eyes coming out of the dim cloud |
| Entry (U9) | +0.3 EV | 0.2 s, with the tubes' 150% flash | the jolt of crossing |
| End of the tear (U12) | FLASH_TEAR | per cine | the light takes you |
| Dawn (F0 + 1 s) | −1.5 → 0 EV | 6 s ease-out, together with lookdev's top-down reveal | eyes opening |
| Water entry (F2) | −0.5 EV | 1 s dip | the impact |
| Exit into dusk (F9) | +0.8 EV | decays over 4 s | out of the deep into light |
| Mirror crossings | MIRROR_PULSE | per cine | – |
| White | WHITE_RAMP | per cine | – |
| White → scene 11 | +1.0 EV | decays over 4 s | the eyes adjust after the light |
| White → scene 12 | +0.8 EV | decays over 5 s | the same, gentler |

---

## 3. Motifs and how they evolve

Each motif is a chain. The implementer does not need to "show" the chains; placing each link as specified in its scene is enough. They are listed here so nobody breaks a link by accident.

1. **The name 蓝白**
   - **Scene 1:** the enamel sign, read correctly.
   - **Scenes 2–4** [NEW]: the lit destination blind above the windscreen shows 蓝白 **mirror-reversed**, because from inside you read it from behind the backlit cloth. You spend the whole ride reading the name backwards.
   - **The dream:** the name dissolves into the world. 蓝 is the night sky, which the tear rips open to 白.
   - **Scene 10:** the white itself is 藍白 (#EBF6F7), the name as a colour.
   - **Scene 11:** the blind is lit and **blank**. The destination has vanished.
   - **Scene 12:** the sign reads correctly again, and the blind shows reversed 蓝白 again.
   - **The credits board:** LANBAI / 蓝白 in the sign's typeface.
2. **The single lamp, and the Lichtchen**
   - **Scene 1:** one tube over the stop.
   - **Scene 2:** lamps in rhythm, each sweeping through the cabin.
   - **Scene 3:** lamps multiplied without number (the sea of lights).
   - **Scene 4:** one terrible lamp, the tear.
   - **Scene 4c:** the **Lichtchen**. First the radio dial, the only warm light in the dead cabin; then the warm point ahead at the end of the rims.
   - **Scene 6:** the sun.
   - **Scene 7:** bronze lamps burning under the sea (lit for nobody).
   - **Scene 9:** every star at once.
   - **Scene 11:** the lamps hang from the sea.
   - **Scene 12:** one tube again, and **one firefly** that comes to you: the Lichtchen that Urlicht promised, delivered. **One → many → infinite → one.**
3. **The cabin tubes (the human light)**
   - steady (home);
   - flickering (fear, from U7);
   - dead (U9; from then on you are lit by the world: violet, gold, teal caustics, rose, starlight);
   - snapping back perfectly steady (scene 11, too perfect);
   - steady with one tube end faintly shimmering, 3% at 0.5 Hz (scene 12: the real world has flaws).
4. **The radio (the voice in the box)**
   - static, then a prayer (U0);
   - the voice escapes into the whole space at U3;
   - its dial becomes the Lichtchen in the tear (U10);
   - dark at the plunge, for good: the music now belongs to the world;
   - static in the false awakening (searching, finding nothing), then it clicks off by itself;
   - dark and silent at the end: *Fled is that music*.
5. **Open doors, three thresholds** [NEW]
   - The bus door is open at the stop, and **it never closes**. The bus drives off with its door open; rain and night air blow in at the step.
   - The tear is the second door.
   - The palace doors in the sea stand open, lit.
   - The white is the third door.
   - **Only in the false awakening are the doors closed.** Normality is the closed world; that is the tell.
   - In scene 12 the doors are open, as they always were.
6. **Lit and empty.**
   - The bus: lights on, doors open, no driver.
   - The palace in the sea: lamps burning, doors open, no spirit. 灵何为兮水中?
   - The answer, never stated, is at the end: the one sitting in the lit, empty bus is you.
   - Compose the palace doors the way the bus looks from the spawn point (§5.7), so the viewer feels déjà vu without knowing why.
7. **Passing light (a band of light crossing the cabin).** One grammar at four tempos:
   - **sodium sweeps**, every 2.5 s (scene 2, the world);
   - **tear rims**, every ≈ 12 s (4c, grace, decelerating);
   - **bronze mirrors**, from 29 s down to 2.5 s (9c, ecstasy, accelerating);
   - **sodium sweeps** again, every 2.5 s (scene 11, déjà vu).

   One shader feature (the emissive slice mask in `Lanbai/Cabin`, lookdev §11.2) serves all of them.
8. **Water**
   - rain (1–3);
   - cloud (3–4);
   - sea (7);
   - the sea's underside as a sky (8);
   - **天河 / 银河**, the Milky Way, "the river of heaven" (9). 河伯, lord of the river in scene 7, rhymes with the river of heaven in scene 9.
   - the sea hung overhead (11);
   - drips into still puddles (12).
9. **Dust (Mahler's *mein Staub*)**
   - dust motes in the dawn beams (6);
   - marine snow rising past the windows while *Aufersteh'n … mein Staub* is sung (7);
   - star dust (9);
   - fireflies (12).

   Dust rises again: that is the resurrection, made visible at every scale.
10. **Blue → white (undyeing).** The ride walks the indigo-dye ladder backwards:
    - near-black indigo 褐色 at the stop;
    - 紺 on the road;
    - 藍 in the moonlit clouds;
    - **ripped to undyed white** at the tear;
    - pale 瓶覗 / 水浅葱 at dawn;
    - re-dyed as you sink (浅葱 → 藍 → 紺 in the water column);
    - **off the ladder** at dusk: the only warm act in the dream, and the only one that is free;
    - back to near-black at the stars (the darkest dye, full of light);
    - **藍白** at the white;
    - near-black again at the stop, with the first pale blue on the horizon. A new undyeing is beginning.

    The world never reaches #FFFFFF. It stops at *almost*. The dream is the almost.
11. **Mirrors (sky = sea, the key line).** Symmetry climbs to perfect at dusk, turns wrong in the false awakening, and ends small and perfect:
    - **scene 1:** wet asphalt, a broken mirror; every raindrop on the glass holds a tiny upside-down lamp;
    - **scene 2:** the dark glass mirrors the cabin over the night;
    - **scene 3:** the lights below continue as stars above (which is which?);
    - **scene 6:** the glassy sea mirrors the dawn sky just before entry;
    - **scene 7:** Snell's window, the sky seen from under water; then the sea floor opens into a sky;
    - **scene 8:** perfect symmetry, with the text mirrored in it;
    - **scene 9:** the mirrors become objects that carry the sky up through you;
    - **scene 11:** the sea hangs above the road, a mirror in the wrong place;
    - **scene 12:** still puddles, and a drip that breaks the reflection and lets it **restore** (§6).
12. **The curtains (pale indigo, the cabin's 蓝白)**
    - tied and still at the stop;
    - swaying on the road;
    - back-lit pale blue at dawn;
    - floating upward in the sea;
    - **wings** at dusk, released on *entschweben*;
    - tied and still again at the end, exactly as at the start.
13. **The nightingale**
    - Mahler's flute and piccolo in the Great Summons are, in his own programme, "a far, far-off nightingale, a last trembling echo of earthly life".
    - Keats' last line, *Fled is that music:—Do I wake or sleep?*, is the end of his **Ode to a Nightingale**. The stanza it closes reads: *"thy plaintive anthem fades / Past the near meadows, over the still stream, / Up the hill-side …"*.
    - So the real nightingale in scene 12 flies away over the near field and the still water, and Keats names it after it has gone (§7).
14. **The vertical axis**
    - up (lift-off, gate);
    - down (the fall, sinking);
    - down becomes up (the sea floor is a sky);
    - up and down undefined (天问: 上下未形);
    - things rise from below (the mirrors);
    - the sea is above (the false awakening);
    - level ground (the stop).

---

## 4. Poems: how the words appear

### 4.1 Rules
1. **Timing: image first, word second.**
   - A poem fades in 4–12 s after its key image has *landed*, meaning fully revealed.
   - There are three exceptions:
     - **Rilke** comes before the terror, because it is a prophecy;
     - **the Urlicht voice lines** are word-synced to Ferrier, the only place where the shown words and the sung words coincide (at the threshold);
     - **天问** asks its question in the dark, *before* the stars answer it.
2. **No text on a peak.** No text in the first 8 s of any scene, during F13–F16, or during the white. Text may be on screen for at most 40% of a scene's duration.
3. **Hold time:**
   - 3 s + 0.3 s per CJK character (or 0.35 s per Latin word) + 2 s;
   - ×1.3 when a translation line is present;
   - minimum 6 s, maximum 14 s.

   The table in §4.2 already applies this.
4. **Reveal and exit.**
   - Reveal: lookdev §14.2 (a 2.5 s focus pull from outline softness 0.9 → 0, plus an alpha fade).
   - Exit: 3 s, drifting 0.2° **up** by default. Exceptions:
     - the two fall lines drift **down** (the direction of the fall);
     - 庄子's mirrored copies drift away from the horizon both ways;
     - 天问 breaks up into stars.
5. **Placement.**
   - World space, fixed in bus space once spawned (the text never follows the head).
   - Depth-tested against everything outside, so tentacles, fish and clouds may pass in front of it.
   - Drawn after the window glass. Never drawn over cabin interior surfaces.
   - At least **12° away from the scene's focal point**.
   - Within the elevation band a seated passenger can see through the windows (about −30° to +15°) until the roof is gone (scene 7 onward).
6. **Gaze rule** (every player sits somewhere different). Each poem has a default azimuth.
   - If the local player's head yaw at the trigger is within 50° of that default, use the default.
   - Otherwise, spawn at the player's yaw offset 20° toward the default.
   - Poems are **local**: each player gets their own copy, placed for their own seat.
   - If the current build already solves placement well, keep its mechanism and apply only the timing, elevation and side rules here.
7. **Size** (lookdev §14): main line character height 2.4° (1.3° for small lines); translation lines 1.3° (1.0° under small lines). Fonts and colours: lookdev §14.
8. **Languages** **[CHANGE]**: every player sees the **original** as the main line, with their own language underneath.
   - Chinese poems:
     - zh players see the original alone;
     - ja players see the original plus the 書き下し;
     - everyone else sees the original plus English.
   - German and English poems: the original, plus a zh / ja / en translation beneath.
   - The user's two lines from the dream: the Chinese original, plus a translation.
   - Why:
     1. Hanzi are part of the image; for players who cannot read them they are still calligraphy.
     2. The German is what Ferrier is singing at that moment.
     3. Friends riding together see the same main line.

### 4.2 The poems

| Scene | Text | Trigger | Hold | Azimuth / elevation / distance | Size | Treatment |
|---|---|---|---|---|---|---|
| 3 | 李白: 我欲因之梦吴越，一夜飞度镜湖月 | the sea of lights fully revealed ≈ U3 + 20 s | 11 s | +50° / −10° / 40 m, over the lights | 2.4° | warm white, 2 lines broken at the caesura |
| 4a | Rilke: *Denn das Schöne ist nichts als des Schrecklichen Anfang* | U6 + 4 s | 10 s | +20° (right of the tear) / +2° / 45 m | 2.0° German italic + 1.3° translation | violet glow; **the first colossus rises behind it** |
| 4b | Urlicht: *Da kam ein Engelein und wollt' mich abweisen.* / *Ach nein! Ich ließ mich nicht abweisen!* | word-synced to the singing | as sung, then out in 1.5 s | 0° / −6° / 30 m | 1.3° + 1.0° translation | no glow; a whisper, never a title card |
| 6 | the user: 我从天空坠入深海 | at least 12 s after the dawn has fully risen, in a pause between horn calls (≈ F0 + 20 s) | 9 s | −15° / −14° / 40 m (below the horizon, toward the fall) | 2.4° | dark ink #1F2A3A; exits drifting down |
| 7 | 屈原《河伯》: 鱼鳞屋兮龙堂，紫贝阙兮朱宫，灵何为兮水中 | 8 s after the main hall's doors are fully in view | 13 s | −25° (left of the doors) / +6° (above the roofline) / 35 m | 2.0° | teal glow; the fish school passes in front of it once |
| 8 | the user: 自深海坠入另一片天空 | exit into dusk + 6 s | 10 s | **the same place as the dawn line**: −15° / −14° / 40 m | 2.4° | light #FBE8E4 on dark (the photographic negative of the dawn line); exits drifting down |
| 8 | 庄子《逍遥游》: 天之苍苍，其正色邪？其远而无所至极邪？其视下也，亦若是则已矣 | the sea ceiling fully faded (≈ exit + 40 s) | staged, 27 s total | centred 35° from the sun's azimuth, on the horizon, 60 m | 2.0° | **the mirror treatment**, §5.10 |
| 9 | 屈原《天问》: 遂古之初，谁传道之？上下未形，何由考之？ | F12 + 3 s (the sun is out) | until F13, at least 8 s | +30° (where the sun died) / +8° / 50 m | 2.0° | per-character ignition, 120 ms stagger; at F13 the characters break up into the first stars |
| 11 | 庄子《齐物论》: 不知周之梦为胡蝶与，胡蝶之梦为周与 | 28 s into scene 11 | 12 s | 0° / +10° / 35 m, just below the visible sea | 1.8° | #FFE3B0 at 70%, low contrast. **Reading it lifts the eye into the sea just above.** |
| 12 | 李白: 惟觉时之枕席，失向来之烟霞 | 16 s into scene 12 | 11 s | **the same place as the scene 3 李白 line**: +50° / −8° / 30 m, over the field | 2.4° | 藍白 #E8F6F8 |
| 12 | Keats: *Fled is that music:—Do I wake or sleep?* | 70 s into scene 12 | 10 s | +50° / −14° / 25 m | 1.3° italic + 1.0° translation | 藍白, no glow; the last words in the world |

Two pairs rhyme by position:
- **The two 李白 lines** open and close the dream. Both come from the same poem, 《梦游天姥吟留别》. They appear at the same place in bus space: first over the sea of lights, last over the field of fireflies.
- **The user's two dream lines** also share one place in bus space. The dawn one is dark on light; the dusk one is light on dark. They are each other's reflection.

---

## 5. Scene by scene

Each scene gives:
- **Beat:** the dramatic function;
- **Feel:** what the viewer must feel;
- **The image:** the one frame that carries the scene; if it were the poster, this is what it must contain;
- **Poem** and **Mahler:** the rhymes with the words and the music;
- **Do:** choreography and numbers;
- **Restraint.**

### 5.1 Scene 1: 站牌 The stop
**Beat:** invitation. The world is small, wet and quiet, and one light is on for you.

**Feel:** loneliness turning into being expected. A little fear (there is no driver); more tenderness (the light is on).

**The image (the spawn view)** [NEW]
- **Spawn point:** on the right shoulder, 14 m behind the sign pole and 1.8 m off the carriageway, facing the bus's heading. Eye height is the standard one.
- **What is in frame:**
  - the bus's rear and its right flank: red tail lights (#FF2A12) doubled on the wet road, and a row of cool lit windows receding;
  - the single tube and the round 蓝白 sign at 14 m, slightly right of centre: the brightest thing in the world at this moment;
  - a rectangle of door-light on the wet shoulder just before the sign;
  - the flooded field on the right, holding the tube's reflection;
  - the road dissolving into fog ahead.
- **The prologue** is the 10 m walk to the door, along the lit windows, with the empty seats sliding by.

**Sound:**
- rain on the asphalt and leaves;
- insects in the field;
- the tube's faint hum;
- an electrical hum from the open door, but **no engine**;
- the distant truck crossing once.

**Poem:** none. The only writing is the sign. The name is this scene's poem.

**Do:**
- The radio starts only when the local player sits: 2–4 s of static, then U0.
- The bus waits through *O Röschen rot!*. The voice arrives while you are still at the stop with the door open.
- It glides off at U1, accelerating at 0.6 m/s² to 50 km/h (≈ 23 s).
- The door never closes.

**Restraint:**
- Intensity 1. No moon, no stars, no sky structure.
- This is the smallest the world will ever be, so everything after it feels vast.
- Nothing hurries the player: no timer, no prompt.
- **Everything here returns in scene 12, changed by one thing: the rain has stopped.**

### 5.2 Scene 2: 夜路 Night road
**Beat:** being carried.

**Feel:** melancholy and safety at once: a stranger's voice on a radio at night, the rain, the rhythm of the lamps. The prayer is about human suffering; the viewer should feel held by it, not saddened into passivity.

**The image:**
- rows of empty oxblood seats under cool tubes;
- an amber sodium sweep sliding front to back across the seat tops;
- the dark windows holding the cabin's reflection over the night;
- the radio's warm dial beside the empty driver's seat;
- the wipers sweeping the windscreen with nobody at the wheel.

**Poem:** none.

**Mahler:**
- **The chorale (U1) is a hymn and the lamps are its pulse.** Do not sync the 2.5 s sweeps to the chorale; let them drift against it.
- **The lamps stop when the chorale ends (U2).** The last phrases play into darkness. The voice returns (U3) in the dark, at the crest.

**Do:**
- The village (6–10 houses, 1–3 lit windows each, as lookdev §4 specifies), then the dark stretch, climbing a gentle hill: 5% grade over 300 m.
- Look-back reward: the stop's tube stays in the rear window as a single receding point, gone behind a bend at about U 0:40.

**Restraint:** no people anywhere; no sky; no reveal. Intensity 2, dropping to **1** in the dark stretch. That trough is what makes the lift-off feel like flight.

### 5.3 Scene 3: 离地 Lift-off: road → sea of lights → sea of clouds
**Beat:** release; wonder.

**Feel:** the drop in the stomach that comes with wonder; gravity letting go; compassion for the world of people seen from above.

**The image:** through the right-hand windows, the ground falls away and becomes a field of amber lights to the horizon, where it turns into stars. The cabin's reflection lies faintly over it in the glass.

**Poem:** 李白 at U3 + ≈ 20 s. This is the first line of the dream-flight in 《梦游天姥吟留别》.
- **镜湖** means mirror lake. The sea of lights below, mirroring the stars above, is the first mirror lake.
- The literal 镜湖月 arrives ≈ 90 s later, at U6, when the moon appears over the cloud plain. The word is planted here; the image is harvested later.

**Mahler:**
- ***Der Mensch liegt in größter Not / Pein*** sounds over the sea of lights. Every light is someone's window: the contralto sings their pain while we leave them.
- Keep the lights 80% warm (sodium and incandescent) so the scene reads as compassionate, not as a data visualisation of a city.
- ***Je lieber möcht' ich im Himmel sein*** (U4) arrives just as the bus turns toward the cloud ceiling.

**Do:**
- **The crest (U3).**
  - The road bends down and to the right and disappears. The bus goes straight on, level.
  - Vertical speed 0 → 8 m/s over 6 s; forward speed 13.9 → 35 m/s over 30 s.
  - The lights are revealed by the crest edge sliding down the windows.
- **The sound opens** at the same moment (§1.5).
- **Rain on the glass:** the runners slow, stop, then streak up and back. The glass is clear by U4 + 20 s (lookdev §3.6).
- **The tear, first seen** [NEW]
  - A thin violet vertical stroke on the far horizon, dead ahead: about 2° tall at about 40 km. It is steady and fog-exempt.
  - Nothing points it out. Players who notice it carry the gate with them for 100 s, like a lit fuse.
- **The cloud ceiling (U4 → U5).**
  - The underside of the deck, lit orange by the city (≈ #7A4A2A at its brightest), approaches for about 40 s; its texture grows.
  - Then 3–8 s inside the cloud (warm → cool fog), with wisps passing.

**Restraint:** the moon stays hidden until U6. No tentacles anywhere.

### 5.4 Scene 4a: the moon road (U6 → U7, ≈ 15 s)
**Beat:** the calm before; beauty.

**Feel:** breathless. A vast, silent, moonlit plain, and a quiet foreboding.

**The image:**
- The moon (1.2° disc, lookdev §5) low and ahead-left.
- Its silver glade runs across the cloud plain from under the bus toward the horizon. *Da kam ich auf einen breiten Weg*: this glade is the broad road.
- Dead ahead, the tear: a vertical rip of violet-white, 1.4 km tall at about 6 km (≈ 13°), breathing.
- Two or three far congestus clouds for scale.
- No tentacles yet.

**Do:**
- **[CHANGE] Moon placement:** azimuth −22° (left of the tear's axis), elevation **+14°**.
  - A seated passenger sees at most about +15–20° through the windscreen and about +25° through the side windows. At lookdev's +50° the moon would be hidden by the roof for the whole scene.
  - At +14° the glade runs ahead-left toward the tear: the road leads to the gate.
- **Exposure:** +0.6 EV at the break-out, decaying over 3 s.

**Poem, Rilke** (U6 + 4 s, azimuth +20°, 45 m):
- It is the one poem that comes **before** its image, because it is a prophecy.
- During its hold, the first colossus (3.2 km away, same azimuth) begins to rise out of the cloud plain **behind the text**, at 0.2°/s. When the text fades, the terror is standing where the word *Anfang* was.
- Rilke's lines continue, unshown, and they hold the meaning of the gate:

  > *…den wir noch grad ertragen, und wir bewundern es so, weil es gelassen verschmäht, uns zu zerstören. Ein jeder Engel ist schrecklich.*
  > (…which we can only just bear, and we admire it so because it serenely disdains to destroy us. Every angel is terrible.)

  **The tentacles are that angel**, and they are Urlicht's *Engelein* at U7. They are not monsters hunting the bus. They reach for the tear, to close it, and you are beneath their notice. That is more frightening, and more beautiful (law 5).

### 5.5 Scene 4b: the surge (U7 → U9, ≈ 30 s)
**Beat:** terror, and defiance.

**Feel:** awe in the old sense: a small body before colossal things. Then the thrill of *not* being turned away.

**The image:**
- Dozens of black tentacles rising out of the moonlit cloud sea, all bending toward the violet tear. The far ones dissolve into cold blue haze.
- A near one slides past the window, its cold blue rim razor-thin, its tip whipping by 10 m away.

**Choreography:**

| Cue | Event | Visible count | Nearest | Motion |
|---|---|---|---|---|
| U6 + 10 s (during Rilke) | Colossus 1 (≈ 420 m) rises at 3.2 km, +20° | 1 | 3.2 km | ≤ 0.3°/s |
| U7 *Da kam ein Engelein* | Colossi 2–3 at 2.5 km (−35°) and 4 km (+5°). Mid tentacles (60–140 m) break the cloud surface in a ring 400–900 m around the tear's foot: 12 → 30 over 12 s. | 3 + 30 | 400 m | rising, reaching toward the tear |
| U7 *…und wollt' mich abweisen* | The ring bends inward. Tips converge across the tear's lower half, like fingers closing. | ≈ 45 | 250 m | tips 15–20 m/s |
| U8 *Ach nein!* | Three near tentacles (25–40 m) sweep past the windows at 8–20 m (camera fade 2–6 m, lookdev §6.3). The bus passes between two colossi 600 m apart. | ≈ 60 | 8 m | near ones 30–40 m/s |
| U8 *…Ich ließ mich nicht abweisen!* | The gap ahead narrows. The tear fills the windscreen. | ≈ 60 | – | – |
| U9 *Ich bin von Gott* | Entry. | – | – | – |

- **Speed comes from the tentacles, not the bus.** The bus accelerates at most 1.5 m/s²; the feeling of speed comes from near things passing.
- **Tube flicker** (lookdev §3.2), keyed to cues: 0.1 dips/s at U6, 1/s at U7, 3/s at U8. At U9: one 150% flash, then all tubes die.
- **Voice lines** (§4.2): small, low, word-synced, fading 1.5 s after each phrase.
- **Look-back reward.** The story says *you don't look back*. Those who do, through the rear window at U9, see the nearest colossi's tips close over the gap behind the bus, like a hand closing.

**Mahler:**
- This section is the lightest music in Urlicht: glockenspiel, solo violin, a child's tune about a little angel.
- **Do not "fix" that with sound effects.** The mismatch between a child's song and colossal arms *is* the Rilke line: the little angel is terrible.
- The singer's voice is small and steady against all of it: *Ach nein!*

**Restraint:**
- No creature sounds.
- No camera shake.
- No tentacle ever touches the bus.
- No red.
- Tentacle tips vary, per the AD notes (whips, half-curls, frayed ends); never a row of identical spirals.

### 5.6 Scene 4c: inside the tear (U9 → U12, ≈ 90 s) [NEW]
WORLD.md has the bus enter on *Ich bin von Gott*, but Urlicht continues for about 90 s after that line. This is the passage that fills that time.

**Beat:** grace after terror.

**Feel:** the heart slowing; being let in; a light that is kind.

**The image:** nested rims of torn light receding ahead like the inside of a flower. The dark cabin is silhouetted against them, and the radio dial is the only warm thing inside.

**Do:**
- **The rims.** The tear is a rip through a thick cloth of sky (lookdev §6.1: indigo torn to the undyed white beneath), and inside, the rip goes deep.
  - **8 rims**, nested. Each is a lens-shaped torn lip of luminous fibres (reuse `Tear_Emission` and the fibre cards).
  - Height shrinks ×0.78 per rim: 1400 m → ≈ 250 m.
  - Spacing 400 m.
  - Between the rims: a soft violet-white haze.
- **Brightness.**
  - The haze rises from display ≈ 110 at rim 1 to ≈ 190 at rim 8.
  - The lips are 230–250.
  - **Never a full-field white.** That belongs to scene 10 alone.
- **Rim crossings land on phrase starts.** Each crossing sweeps a soft band of light through the cabin, front to back, in 1.2 s: the slow form of the passing-light motif.

  | Rim | Cue |
  |---|---|
  | 1 | U9, *Ich bin von Gott* (the entry) |
  | 2 | *…wieder zu Gott* |
  | 3 | U10, *Der liebe Gott* |
  | 4 | *…ein Lichtchen geben* |
  | 5 | U11, *wird leuchten mir* |
  | 6 | *…bis in das ewig* |
  | 7 | *selig* |
  | 8 | the long *Leben* |

- **Bus speed:** down to 30 m/s after entry (≤ 1.5 m/s²), and to 15 m/s by rim 8. The world is slowing down with the music.
- **The cabin.**
  - The tubes have been dead since U9.
  - Light comes only from the haze through the windows (`_Udon_CabinAmbient` #C9B8FF × 0.35) and from the radio dial.
  - **On *ein Lichtchen geben*, the dial brightens by one stop over 3 s and holds through *Leben*.** The little light is in the cabin with you.
- **Ahead:** a single warm-white point, display #FFF1DC at the core, 0.3° across with a 4° glow. It grows through U11–U12.
- **The exit.** When the final chord releases, the point fills the view → FLASH_TEAR → black. The flash takes the first 0.5 s of the 3 s silence (§5.7).
- **Behind (look back):** the tentacles reach into the first lip and stop, their tips curling back. They cannot follow.

**Restraint:** no tentacles ahead, no stars, no text. This is the trough between the two worlds, and the first time the viewer can breathe.

**FLAG:** if the build's audio is cut at U9, this passage lasts only as long as whatever remains. I strongly recommend playing Urlicht to its end: *ewig selig Leben* is the most beautiful minute of the Ferrier recording.

### 5.7 Scene 5: 投入 The plunge (3.0 s)
**Beat:** death; the held breath.

**Feel:** nothing. Suspension.

**The image:** black #030409. The cabin's afterglow decays over 2 s (lookdev §7).

**Do:**
- Exactly 3.0 s from Urlicht's last audible sample to F0.
- FLASH_TEAR occupies the first 0.5 s. Digital silence throughout.
- **Why silence instead of Mahler's opening scream:** the scream is terror, and we already had the terror. Silence is the fall.

### 5.8 Scene 6: 天空 I, dawn
**Beat:** rebirth: the first morning of the world.

**Feel:** weightless, vast serenity; wonder without fear. Tears of relief may start here.

**The image:**
- The intact, unlit cabin as a dark frame around an immense luminous dawn.
- The sun low ahead-right (+5°, azimuth +35°). Gold beams cross the aisle diagonally, full of dust.
- The cloud plain 800–1500 m below, with lavender shadows (never brown).
- Three to five congestus pillars on the horizon, 6–12 km away, in different directions.

**Poem:** 我从天空坠入深海, the user's own line from the dream. It sits below the horizon, in the direction of the fall, and drifts down as it leaves. Reading it makes you look where you are going.

**Mahler:**
- ***Der große Appell***: horns offstage, far away, from different directions. The visual partners are the far cloud pillars at different azimuths: the callers in the wilderness.
- **The flute and piccolo birdsong** is Mahler's "far, far-off nightingale, a last trembling echo of earthly life". Its visual partner is the dust motes glittering in the gold beams: the tiniest, nearest things. **Show no birds.**
- **Mahler's "dreadful silence" becomes a luminous silence:** a huge empty sky in which nothing moves but dust.

**Do:**
- **The dawn rises** at F0 + 1.0 s: the call first, then the light. Top-down over 2.5 s (lookdev §7), plus exposure −1.5 → 0 EV over 6 s.
- **Fall profile** (a settling, not a crash):

  | Stage | Fall speed |
  |---|---|
  | start | 4 m/s |
  | by F1 | 12 m/s |
  | in the canyon | 25 m/s |
  | last 150 m above the sea | easing to 8 m/s |

- **The cloud canyon** [NEW], at F1, about 40 s.
  - The bus falls through a gap about 600 m wide in the dawn cloud floor.
  - Walls 600–900 m tall slide up past the windows: gold on the sun side, lavender on the shade side.
  - Below, the sea and its glitter path.
  - This is dawn's peak (6): scale through parallax. Falling through a gap rather than a cloud keeps the whites under control.
- **The sea mirror** (F2).
  - For the last 10 s, the glassy patch below reflects the dawn sky, so you seem to fall into sky. This is the first explicit 其视下也.
  - **Water entry on the last bird call, in the hush.**

**Restraint:**
- No visible birds.
- No lens-flare sprites.
- The sky never clips, except the sun disc.
- At most one wisp past the window every 20 s.
- The cabin stays intact and unlit.

### 5.9 Scene 7: 海面 → 深海 Sea surface → deep sea (≈ 7–8 min)

**7a. Under the surface (F3 → F5)**

**Beat:** being received by the sea; a hush.

**Feel:** reverence. The sacred. The body's slowness under water.

**The image:**
- Overhead, Snell's window: the dawn sky compressed into a bright, rippling disc, ringed by mirrored dark water.
- God rays.
- Bubbles and marine snow streaming **up** past the windows while the bus sinks.

**Mahler:**
- *Aufersteh'n, ja aufersteh'n wirst du, **mein Staub***: "rise again, my dust". Marine snow *is* the sea's dust, and it rises past you. Everything rises while you sink: the word and the image move in opposite directions.
- **The soprano (F4)** floats out of the chorus; at that moment the first bioluminescent trail flares along the hull (a voice emerging from the choir = a light emerging from the dark).

**Do:**
- Sink at 2 m/s, slowing to 1 m/s.
- Give the long water column one event every 40–60 s:
  - the disc of sky dims;
  - the god rays fade out by 25 m;
  - darkness with bioluminescent sparks;
  - F5, the first bronze lamp, as a warm point far below.

**7b. The palace (F5 → F7)**

**Beat:** lights on, nobody home.

**Feel:** tenderness, and grief that has been answered: *it was all kept*.

**The image:**
- The main hall's open doors: a lit doorway in the dark sea, warm light spilling across the terrace.
- Bronze lamps burning under water.
- The silver fish school circling.
- Nobody.

**This is the central rhyme of the world.** It is the bus at the stop, drowned: open doors, lights on, no one there.
- Compose it the way the bus looks from the spawn point: a lit vertical opening seen from outside, in the dark, with its light lying on a wet surface in front of it.
- The viewer should feel déjà vu without knowing why.

**Mahler:**
- The alto returns: *O glaube, mein Herz … Es geht dir nichts verloren! Dein ist, ja dein, was du gesehnt!* (O believe, my heart … nothing is lost to you; yours is what you longed for.)
- It is the same voice type as the radio's Urlicht, now without a radio.
- The palace is everything the heart longed for, kept under the sea with its lamps lit.
- Timing: first lamp at F5 (orchestra); the doors come into view at F6 (voice); the nearest pass at F7 (*nichts verloren*).

**Poem, 河伯:**
- The buildings the poem names are all there, built literally in lookdev §9.4:
  - 鱼鳞屋: the nacre roofs, which glint when the bioluminescent trail passes;
  - 龙堂: the ridge silhouettes;
  - 紫贝阙: the cowrie towers;
  - 朱宫: the vermilion hall.
- The poem's question, 灵何为兮水中, is not answered in the sea. It is answered at the stop.

**7c. The sea floor becomes a sky (F8 → F9)**

**Beat:** the ground gives way again.

**The image:**
- Past the terrace edge the water keeps going down, and glows rose from below.
- Beneath the bus, the inverted Snell's window (lookdev §9.5): the dusk sky inside it, the palace lamps reflected in the water's underside around it.

**Mahler:**
- *Was entstanden ist, das muss vergehen / Was vergangen, auferstehen*: the palace recedes above (vergehen); the rose light rises from below (auferstehen).
- *O Schmerz … O Tod … Nun bist du bezwungen!*: the fall toward the surface.
- **The exit comes on the orchestral swell after *bezwungen*:** water streams upward off the windows (0.8 s), then +0.8 EV decaying over 4 s.

**Restraint:** one fish school, no other creatures, no spirits, no statues, no text inside the palace. *Nobody home* is the content.

### 5.10 Scene 8: 天空 II, dusk (the key line)
**Beat:** revelation.

**Feel:** understanding in the body that up and down are the same; freedom; the widest breath of the world.

**The image:**
- Perfect symmetry. The sun and its reflection fused into one blazing line at the horizon.
- The rose belt and the violet sky above, and the same below.
- The dark sea ceiling overhead, fading into sky over 40 s.
- The cabin's roof and walls gone. Pale-indigo curtains streaming on both sides of the player like wings.

**Mahler:** *Mit Flügeln, die ich mir errungen*. **The curtains are the wings.**
- At F10 (the duet) they spread: billow 30 → 60 cm, 0.3 → 0.5 Hz.
- At *entschweben* in F11 (the chorus) they **let go of their floating rails and fly up and away**, dissolving into rose light over 8 s.
- The last of the cabin's colour leaves as wings.
- **[CHANGE]** Lookdev had the curtains drift and fade during the stars.

**Poems:**
1. **自深海坠入另一片天空** at the exit + 6 s, at the dawn line's place in bus space (§4.2).
2. **庄子**, once the sea ceiling has fully faded and the symmetry is complete. Three lines, one at a time, on the horizon, 2.0°, centred 35° from the sun's azimuth (never over the sun-line).

   | Time | Line | Upright copy | Mirror copy |
   |---|---|---|---|
   | 0 | L1 天之苍苍，其正色邪？ | above the horizon | below (α 0.5, softness 0.3) |
   | +6 s | L2 其远而无所至极邪？ | above the horizon | below |
   | +13 s | L3 其视下也，亦若是则已矣 | **below** the horizon (read looking down) | **above** |

   - All three lines hold until +27 s.
   - Exit over 4 s: the upright copies drift up, the mirror copies drift down.
   - **The typography turns over at exactly the words that say looking down is the same as looking up.** This is the most important typographic moment in the world.

**Restraint:**
- 6–10 cloud pairs only.
- Nothing crosses the sun-line.
- No birds.
- The sun-line is the only focal point.

### 5.11 Scene 9: 天空 III / 星海

**9a. Night is born (F12, 15–30 s)**

**Beat:** the death of the sun.

**The image:**
- On *Sterben werd' ich*, the sun-line contracts from ±10° to a point over 6 s and goes out.
- Blue hour (cine S8b) to black in about 15 s.
- The sky is #04050A, with no stars and no horizon. **The only light is 天问.**

**Poem, 天问:** 上下未形，何由考之? ("When above and below had no form yet, how could anyone examine it?")
- It appears in the one moment of the world when above and below truly have no form.
- Each character ignites in turn (120 ms stagger).
- It does not fade. **At F13 its characters break up into the first stars.** The question becomes the sky that answers it.

**9b. In einem Nu (F13)**

**The image:**
- On the fff organ entry, **the Milky Way ignites in 1.0 s** as a complete ring through the zenith and the nadir.
- Two ignition waves start at the zenith and the nadir together and meet at the horizon.
- 5000 geometric stars. *In einem Nu*: in an instant.

**Do:**
- No exposure change: the stars bring the light.
- **Hold at least 10 s before the first mirror.**
- **[CHANGE]** Lookdev had the Milky Way present from the start of scene 9.

**9c. The mirrors (F14 → F16)**

**Beat:** ascension; ecstasy; dissolution.

**Feel:** overwhelmed, carried, letting go. This is the one moment allowed to be total.

**The image:**
- A polished bronze mirror rises from below, its face carrying the Milky Way in gold.
- It rises through the bus: a thin horizontal line of light sweeps up through what remains of the cabin.
- It continues upward, its verdigris back eclipsing stars.
- The next one comes bigger, and sooner.

**Mahler:**
- *Was du geschlagen, zu Gott wird es dich tragen*: what you fought for will carry you. The mirrors carry the sky up through you, and each one lifts a piece of the vessel away.
- *Sterben werd' ich, um zu leben*: the bus dies piece by piece so that you can live.

**Schedule:**
- **13 mirrors.** Count backwards from F16, where the last mirror lands.
- Intervals d_k = 2.5 s × 1.25^(k−1), for k = 1…12: **2.5, 3.1, 3.9, 4.9, 6.1, 7.6, 9.5, 11.9, 14.9, 18.6, 23.3, 29.1 s**. So mirror 1 crosses at F16 − 135 s.
- Snap each crossing to the nearest tapped bell stroke or choral downbeat within ±0.8 s.
- **Photosensitivity:** at least 2.5 s between crossings, far inside cine's cap of 3 pulses per second.

**Sizes and speeds:**
- Diameter 40 m for mirror 1, growing ×1.20 per mirror to about 300 m for mirror 12. Mirror 13 fills the lower hemisphere (diameter ≥ 2 km).
- Rise speed 3 m/s (mirror 1) → 40 m/s (mirror 12).
- Each mirror slows as its face nears the bus, so the Milky Way can be seen in it for at least 2 s before the crossing.

**The cabin erodes in steps** [NEW]:
- Each crossing erodes part of the cabin: `_Udon_CabinFade` += 0.027 over 1.2 s, following the sweeping line (0.65 → 0.97 over 12 crossings).
- The stanchions go last of the fittings: thin silver lines against the Milky Way.
- **Mirror 13 takes the player's own seat, as its face reaches their eyes.**

**Restraint:**
- No text.
- No shooting stars.
- No twinkling.
- No nebula colours beyond the NASA map.
- No sound but Mahler.

### 5.12 Scene 10: 白光 White light
**Beat:** peace; completion.

**The image:** 藍白. Nothing else (lookdev §12).

**Do:**
- WHITE_RAMP over the last 5 s before F16.
- Full white at the attack of the final chord.
- Hold through the chord's decay.
- Then **5 s of white in digital silence**, counted from the moment the audio drops below −60 dBFS. Those 5 s after Mahler are part of the music.

**Restraint:** no logo, no text, no shapes, no "fin". Only ±2% breathing.

### 5.13 Scene 11: 假醒 False awakening (≈ 75 s)
**Beat:** relief, then vertigo.

**Feel:**
1. "It was only a dream" (relief).
2. "Wait…" (unease).
3. 庄子's question, felt in the body.

**The image:** an ordinary cabin, whole and steadily lit, with sodium sweeps passing through it. Above the road, a dark sea with amber glitter; the lamp poles hang down out of it.

**Timeline (from the start of the contraction):**

| t | Event |
|---|---|
| 0–4 s | The white contracts into the sodium lamps (lookdev §12). +1.0 EV decaying over 4 s. Static fades in, −40 → −30 dB. |
| 4–20 s | **Normality.** The sea is there but reads as night sky, because its glitter is off. Let the relief land. |
| 20 s | The glitter streaks switch on (the lamps' light on the water). The ceiling becomes a sea. |
| 28 s | 庄子 胡蝶, at 0° / +10°. Reading it lifts the eye into the sea just above it. |
| 60 s | The radio clicks off by itself. Silence, apart from the tyres. |
| 62 s | **The second white:** soft, 6 s, spreading from the windows inward like light through eyelids. This is waking, not dying: the opposite of the crash in 9c. Hold 3 s at 藍白. |
| 71–75 s | The white contracts into the single tube over the stop → scene 12. |

**The tells, false against real** (the false world is perfect; the real world has flaws):

| | Scene 11 (false) | Scene 12 (real) |
|---|---|---|
| Doors | **closed** | open |
| Road | dry | wet, puddles perfectly still |
| Glass | dry and slightly too clean | beaded |
| Tubes | perfectly steady | steady; one tube end shimmers 3% at 0.5 Hz |
| Radio | static, then clicks off | dark and silent |
| Destination blind | lit and **blank** | 蓝白, reversed from inside |
| Rain | none | stopped; drips |
| Grade | exactly S2 (cine: "normality is the lie") | its own, clean lens |
| Sound | tyres, static | insects, drips, a nightingale leaving |
| Overhead | the sea | a few stars through the breaking overcast; the first blue |

### 5.14 Scene 12: 醒 Awakening
Specified in full in §7, because it is the ending.

---

## 6. The credits board and the Coleridge egg

**Physical design:** lookdev §13.3. A roadside notice case on two posts, 3–4 m past the sign, on the door side. Visible from the hero seat through the open door.

**When it lights** [CHANGE: timing]:
- It stays dark until 95 s into scene 12, after the last poem has faded.
- Then its tube starts the way a real fluorescent does: two or three blinks over 1.2 s, with the starter's tick, then steady.
- The credits "appear" by being lit. It is the only invitation in the ending to leave the bus. No prompt, no arrow.

**The sheet** (English frame, names in their original languages; typography as lookdev §14.4):

```
LANBAI
蓝白

        我从天空坠入深海，
        自深海坠入另一片天空。
                        —— 梦中得句

A dream by          [the dreamer's name, as they wish]

Music
  Gustav Mahler — Symphony No. 2, "Resurrection"
  IV. Urlicht            Kathleen Ferrier · Concertgebouworkest · Otto Klemperer · 1951
  V. (from Der große Appell)
                         Emilia Cundari · Maureen Forrester · Westminster Choir ·
                         New York Philharmonic · Bruno Walter · 1958

Words
  李白                   《梦游天姥吟留别》
  Rainer Maria Rilke     Duineser Elegien, I
  Des Knaben Wunderhorn  Urlicht
  屈原                   《九歌·河伯》《天问》
  庄子                   《逍遥游》《齐物论》
  John Keats             Ode to a Nightingale

Trees                    [the user's credit for the Linluo trees]
Built by                 [names, as the dreamer wishes]
Skies                    Poly Haven (CC0) · NASA SVS Deep Star Maps
Type                     Source Han Serif · Source Han Sans · EB Garamond · Barlow · IM FELL English (SIL OFL)
```

- **The epigraph is the heart of the board.** The user's two lines from the dream, the words they were afraid of forgetting, sit printed on paper under glass at the place where the dream began: **kept**.
  - Set them in Source Han Serif SC Medium, cap height 22 mm, directly under the heading.
  - 梦中得句 is the classical term for lines received in a dream. That is exactly what Coleridge's case was.
- **FLAG:** verify the performer credits against the actual discs or files in the build (dates, soloists, choir).

**The Coleridge slip** (lookdev: yellowed #E4D9BE, IM FELL English, pinned at the lower right):
- A torn half-page from the 1816 edition, 120 × 170 mm.
- Cap height 3.5 mm: readable only by leaning in to about 0.35 m. An easter egg should ask you to lean in.
- The tear starts mid-sentence and ends on the last line of the verse. Text (verify against a scan of the 1816 *Christabel* volume):

> OF THE FRAGMENT OF KUBLA KHAN.
>
> …all the rest had passed away like the images on the surface of a stream into which a stone has been cast, but, alas! without the after restoration of the latter!
>
> Then all the charm
> Is broken—all that phantom-world so fair
> Vanishes, and a thousand circlets spread,
> And each mis-shape the other. Stay awhile,
> Poor youth! who scarcely dar'st lift up thine eyes—
> The stream will soon renew its smoothness, soon
> The visions will return! And lo, he stays,
> And soon the fragments dim of lovely forms
> Come trembling back, unite, and now once more
> The pool becomes a mirror.

**Why this passage:**
- Coleridge says the lost dream vanished like reflections on water struck by a stone, *without* coming back. That is the mirror motif of the whole world, and the user's fear.
- The world answers it at the foot of the board:
  - **a puddle** placed so that someone standing at the case and looking down 30–40° sees the tube and the 蓝白 sign reflected in it;
  - **a drip** from the case's roof edge falls into it every 3.5–6 s (random);
  - a ring spreads to 0.4 m over 1.6 s, and the distortion decays with τ = 0.7 s;
  - **the reflection restores fully within 2.5 s, every time.**
- *The pool becomes a mirror.* What Coleridge was denied, this world grants, over and over, next to his own words.
- Nobody is told. The few who read the slip while watching the puddle will understand.

---

## 7. The ending, designed for tears

**Principle.** The ending is the quietest and longest part of the world, and everything vast comes home small. People cry not at the grandeur but at the moment they recognise that the grandeur has come back to them in a size they can hold.

### 7.1 The journey returns in miniature
Every item on the right is placed in scene 12. Nothing about it is explained.

| In the dream | At the stop |
|---|---|
| The sea of lights; the Milky Way | 46 fireflies over the flooded field, doubled in the water |
| The bronze mirrors; the dusk mirror world | still puddles; the 蓝白 sign doubled |
| The tear; the Lichtchen | one tube lamp; **one firefly that comes to you** |
| The sea of clouds | field mist rising 0.5 m |
| Dawn | a faint first blue on the horizon |
| The white light | the 藍白 of the sign and of the tube |
| Mahler's nightingale (flute and piccolo) | a real nightingale flying away over the field |
| The radio's voice; the chorus | insects |
| The palace: lights on, doors open, nobody home | the bus: lights on, doors open, nobody driving, and you are sitting in it |

### 7.2 The sequence
Times are seconds from the start of the white's contraction into the stop tube.

| t | Event |
|---|---|
| 0–4 | The white contracts into the single tube over the stop. Silence. Exposure +0.8 EV, decaying over 5 s. |
| 4 | One cricket, close, just outside the open door. |
| 6–14 | The insect chorus rises to full. The first drip. |
| 9 | **The nightingale**: a first phrase about 25 m out over the field, to the right. Each following phrase comes from further away: 40 m, 80 m, 160 m, 300 m, toward the hills. Its last audible phrase is at about 40 s. *Thy plaintive anthem fades past the near meadows, over the still stream, up the hill-side.* |
| 16 | 李白: 惟觉时之枕席，失向来之烟霞 (only on waking, the pillow and the mat; gone are the mists and clouds of before). Over the field, at the same place in bus space as the scene 3 李白 line. Loss is named first. |
| 27–30 | It fades. |
| 36 | **The Lichtchen** (§7.3) enters through the open door. |
| ≈ 50 | It leaves through the door toward the field. |
| ≈ 56 | It reaches the field. **The field answers:** all 46 fireflies flash once, in a wave spreading from where it arrived at 12 m/s, each flash 0.35 s, mirrored in the flooded field. Then they return to random flashing. A 星海 you could hold in your hands. |
| 70 | Keats: *Fled is that music:—Do I wake or sleep?* Small. The nightingale is gone and the music is gone, so the line names what has just happened. |
| 80 | It fades. **No more text, ever.** |
| 95 | The credits case's tube starts with a tick and a flicker (§6). |
| from 0, over 8 min | The first-blue band brightens very slowly, #1B2229 → ≈ #252E36 (about +1 display level per minute) [NEW]. The drip interval stretches from 4 s to 10 s: the rain's aftermath fading. |
| 300, then about every 60 s | One far, sleepy bird chirp, a different species from the nightingale. Morning is coming. After the cosmic resurrection, the small real one: a morning. |

### 7.3 The Lichtchen firefly [NEW]
- **Local only:** every player gets their own.
- **Its path.**
  1. It enters at the door's centre, 1.5 m high, drifting at 0.15 m/s.
  2. It comes to rest 1.0 m in front of the local player's head and 0.3 m to the right (never straight at the face), hovering in a 5 cm figure-eight at 0.4 Hz.
  3. **It flashes three times:** 0.35 s pulses, 1.8 s apart.
  4. It leaves at 0.25 m/s, out through the door and on to the field, rising to 1.5 m over about 20 s.
- **Its look.**
  - #C8FF3C, 3 cm core, 25 cm halo at α 0.3.
  - Plus a real-time point light, range 0.7 m, just strong enough to put a visible glint on the nearest stanchion. It is the only real-time light in the scene and worth its cost.
- **Why:**
  - Urlicht promised *Der liebe Gott wird mir ein Lichtchen geben*.
  - The world has been full of light: a tear, a sun, a whole sky of stars. What finally comes to you, close enough to touch, is one very small light.
  - The promise is kept at the smallest possible scale.
  - This, not the mirrors, is the moment designed to make the user cry.

### 7.4 Why this will reach the user
- **The user's fear is forgetting the dream's words.** In this ending:
  - the words are printed at the stop (§6);
  - Coleridge's loss is pinned beside them, and the puddle keeps restoring what his stream did not.
- **Mahler said it an hour earlier:** *Es geht dir nichts verloren* (nothing is lost to you). The ending proves it with small things, not with music.
- **Keats says the opposite:** *Fled is that music*. The ending holds both at once:
  - the music is gone;
  - the insects are enough;
  - the bus is still here with its doors open.

### 7.5 What the ending must never do
- No music. No fade to black. No "THE END". No UI prompt.
- No automatic restart.
  - The world stays in this state as long as anyone is there.
  - A new round begins only when a player gets off, gets back on and sits. The rain then returns over 20 s before the radio crackles.
- No camera or player movement imposed.
- No more text after Keats.
- The bus never drives away: it never moved. The dry rectangle under it (lookdev §2.1) stays there for whoever looks.

---

## 8. Don'ts (the full list, for the implementer's checklist)

**Sound**
- No engine sound, anywhere.
- No creature sounds from the tentacles, and no added roars, booms or risers anywhere.
- No filter on Mahler underwater.
- No music after F16.

**Motion**
- No camera shake, no bus pitch or roll, no cuts other than those in law 7.

**Text**
- No text on a peak.
- No text overlapping a focal point.
- No HUD-locked text.

**Things not to show**
- No birds or people, anywhere.
- No second species in any scene.
- No full-field white before scene 10.
- No stars before U3, and no Milky Way before F13.
- No symbols or ornaments added "for meaning": the meaning is in the placement.

**The tentacles**
- No tentacle touching the bus.
- No row of identical tip-curls (AD note).

**The ending**
- No closed doors except in scene 11.
- No automatic restart, and no fade to black at the end.

---

## 9. Flags: what the cloud side needs back

1. **The cue label files** for U0–U12 and F0–F16 (§1.4), plus all F15 bell strokes. Without them every schedule here is an estimate.
2. **The 星海 duration conflict** in WORLD.md (§1.4). Confirm what the build's audio actually contains between F12 and the end.
3. **Whether the build's Urlicht runs past U9 to the end.** I recommend that it does (§5.6).
4. **The seated-eye window limits of the rebuilt minibus** (elevation range through the windscreen and the side windows, measured from the hero seat and a rear seat). They fix the moon's and every poem's elevation. Send one screenshot per direction.
5. **Radio filtering:** confirm that `AudioLowPassFilter` / `AudioHighPassFilter` work on the radio source in the VRChat build. Otherwise use the two-file crossfade.
6. **Nightingale and night-bird recordings:** the implementer sources CC0 recordings. Check each licence; avoid CC BY-NC material.
7. **Local-only objects:** the Lichtchen, the poems and the look-back rewards are per player. Confirm the timeline supports local-only instances.
8. **VR comfort test** of the stepped cabin erosion in 9c, and of the floor under the seat, with a seated VR player before shipping.
9. **Round reset logic** (§7.5): how a new round starts in the current Udon timeline.

---

## 10. What changes against lookdev / cine (for the synthesizer)

| # | Item | Was | Now | Why |
|---|---|---|---|---|
| 1 | Moon position (scenes 3–4) | +50° up, 35° left of the tear | **+14° up, 22° left** | Visible through the bus windows; its glade becomes Urlicht's "broad road" leading to the tear. |
| 2 | After the tear entry | flash, then the plunge | **Inside the tear:** 8 rims over the rest of Urlicht (≈ 90 s); FLASH_TEAR moves to Urlicht's end | Urlicht continues ≈ 90 s after U9; *ein Lichtchen*; grace after terror. |
| 3 | The bus doors | not specified while driving | **Never close**, except in scene 11 | Invitation motif; the false world is the closed world. |
| 4 | Destination blind | – | **蓝白 mirror-reversed** from inside; **blank** in scene 11 | Mirror motif; the destination vanishes. |
| 5 | Poem languages | one language per player | **Original + the player's language underneath** | Hanzi as image; German matches the singing; shared text in multiplayer. |
| 6 | Curtains | drift and fade in scene 9 | **Wings at dusk, released on *entschweben*** | Mahler's *Mit Flügeln*. |
| 7 | Cabin erosion in 9 | continuous | **Stepped, one step per mirror crossing** | Each mirror carries a piece of the vessel away. |
| 8 | Milky Way | present from the start of 9 | **Ignites in 1 s at F13** | *In einem Nu*; 天问 is asked in the dark first. |
| 9 | Scene 12 horizon | fixed first-blue band | **Brightens slowly over 8 min**, plus far bird chirps | Morning is coming. |
| 10 | Credits case light | on in scene 12 | **Starts at +95 s** with a real starter flicker; **the dream lines as epigraph** | The one invitation to leave the bus; the words kept. |
| 11 | Scene 12 | fireflies | **The Lichtchen firefly, plus one synchronised wave** over the field | The emotional peak of the world. |
| 12 | Scene 12 sound | insects | **A nightingale flying away**, then insects | Mahler's nightingale → Keats. |
| 13 | Scene 12 tubes | steady | steady, with **one tube end shimmering at 3%** | The real world has flaws; the false one did not. |
| 14 | Sound | – | **No engine**; the wipers move by themselves | The bus never moved. |
| 15 | Scene 3 | – | **The tear visible as a thin violet stroke** on the far horizon | A 100 s fuse for the gate. |
| 16 | Scene 6 | cloud floor with gaps | **The bus falls through a cloud canyon** | Dawn's scale peak, revealed by parallax. |
| 17 | Spawn point | – | **Behind the bus**, 14 m from the sign | First image: tail lights, lit windows, one lamp, the sign. |

I agree with lookdev on: no shelter; the stop lamp as a 藍白 tube; the white as 藍白, not #FFFFFF; the white contracting into lamps; the dry rectangle under the bus; the Han/Chu palace lit only by its own lamps; the bronze mirrors. I agree with cine on: S11 = S2 exactly, and the LENS_ARCHIVE / LENS_CLEAN split (the real awakening is seen with a clean lens).
