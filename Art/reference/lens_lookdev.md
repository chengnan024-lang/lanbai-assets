# 蓝白 / Lanbai: look-dev, materials and atmosphere

Lens: look-dev / materials / atmosphere. Written for the synthesizer, who turns it into the Chinese bible, and for the Unity implementer (Unity 2022.3, Built-in RP, PPv2, baked lighting, UdonSharp).

Companion files, all in `art/`:
- `lookdev_colour_script.png`: the per-scene swatches as display targets.
- `lookdev_sign_mock.png`: the 蓝白 sign in zh and ja, each shown three ways: flat albedo, lit by the 藍白 tube we chose, and lit by a warm 2400K bulb for comparison.
- `work/colors.py`: blackbody and spectral → sRGB conversions (CIE 1931 fit).
- `work/sign_mock.py`: the sign generator. The cloud side grows this into the real texture.
- `work/colour_script.py`: draws the colour-script strip.

All hex values are sRGB. "Display" means the value a screenshot should sample *after* PPv2. "Enter" means the value typed into a colour field. The two differ because of ACES (see §1.1).

---

## 0. Three ideas behind every material decision

1. **藍白 is a colour, and the world starts and ends in it.** 藍白 (aijiro) is the palest stage of indigo dyeing; its traditional value is **#EBF6F7**. It appears in three places:
   - the enamel field of the stop sign;
   - the fluorescent light of the stop and of the bus cabin;
   - the final white-out.

   The player therefore meets the name as a colour before they read it, and leaves in it. Every warm colour in the world (sodium, the radio dial, dawn, dusk, the vermilion palace) is there to push against it.
2. **Every reflective surface folds sky and sea into each other.** This is 庄子's 其视下也，亦若是 made into materials. The mirrors follow one another through the ride:
   - wet asphalt at the stop;
   - flooded fields;
   - the calm sea;
   - the sea's underside;
   - the mirror-symmetric dusk sky;
   - the bronze mirrors of 星海;
   - the sea hanging over the false-awakening road;
   - the still puddles at the end.

   Wherever a surface can reflect, it is made to.
3. **Photoreal comes from value discipline, wet speculars and atmosphere, not from texture resolution.** What made the previous build look stylised was flat values and missing aerial perspective, not low texel density. The rules in §1 matter more than any single asset.

**Rule: the only writing anywhere in the world is 蓝白, the poems and the credits.** That means:
- no brands, route numbers, licence plates, stickers or posters;
- no legible text on the timetable, the radio dial or the gauges.

This keeps the dream placeless and makes the three pieces of writing that do exist feel deliberate.

---

## 1. Pipeline rules (apply to every scene)

### 1.1 Tonemapper and exposure reference
- Linear colour space, HDR camera. PPv2 Colour Grading in **High Definition Range** mode with the **ACES** tonemapper.
  - Why ACES: bright emissives (the tube, the lamps, the tear, the sun) desaturate toward white the way film does. Neutral keeps them flat and cartoon-saturated.
- **EV0 = PPv2 Post Exposure +0.7.** Every value below is given at EV0. Per-scene offsets are only for transitions (plunge, white-out) plus two small fixed offsets (dawn −0.3, stars +0.3).
- Scene-linear (after exposure) → display, approximated with the Hill ACES fit; verify on screenshots:

| scene-linear at EV0 | 0.01 | 0.02 | 0.05 | 0.10 | 0.18 | 0.30 | 0.50 | 1.0 | 2.0 | 4.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| display sRGB (0–255) | 8 | 20 | 49 | 85 | 125 | 163 | 195 | 226 | 242 | 249 |

- **The ACES toe crushes everything below 0.01 to black (display < 8).** In night scenes, anything that must read (tree lines against the sky, the tentacle bodies, the deep water) has to sit at scene-linear 0.012–0.035, not at 0.003. This is the most common way night scenes go muddy under ACES.
- ACES also desaturates brights. To get a near-white *tinted* display colour you must enter a more saturated colour than you want. Example: display 藍白 #EBF6F7 needs roughly enter **#B5F5FF × 3.1** (HDR).

### 1.2 The Built-in light-intensity trap
Built-in RP by default treats `Light.intensity` in gamma space: effective linear = (sRGB colour × intensity)^2.2. So intensity 2 is ≈ 4.6× linear, not 2×.
- VRChat clients run with that default, so do not depend on `lightsUseLinearIntensity`.
- To get a linear ratio R between two lights of the same colour, set their intensity ratio to R^(1/2.2). Examples: 2× linear = ×1.37; 4× = ×1.88; 1 stop darker = ×0.73.
- Every light ratio below is given in **stops (linear)**. Convert with the rule above.

### 1.3 White balance and light colours
Author night scenes (1–4, 11, 12) as if the camera were white-balanced to **4000K**, and day scenes (6–8) to **5600K**. That turns the physical light temperatures into the classic cinematic night palette of amber / white / cyan / blue without any grading. The hex values are computed with CIE 1931 (`work/colors.py`); type them straight into `Light.color`.

| Source | K | Night (WB 4000K) | Day (WB 5600K) |
|---|---|---|---|
| High-pressure sodium streetlamp | 2050 | **#FFAE32** | – |
| Bronze-lamp flame (deep sea) | 2200 | **#FFB74D** | – |
| Old incandescent (radio dial, notice case) | 2400 | **#FFC369** | – |
| Halogen headlight | 3400 | **#FFEDD0** | – |
| **藍白 tube (triphosphor ~5000K)** | – | **#CFEAF0** (computed #D7F3FF, pulled toward 藍白) | – |
| Moon (cinema convention) | 9000 | **#8AAEFF**; use **#9DB8FF** for the rim | – |
| Dawn sun at 5–8° elevation | 3000 | – | **#FFC57B** |
| Dusk sun at 1–3° elevation | 2500 | – | **#FFB153** |
| Clear-sky fill | 10000 | – | **#B7D0FF** |
| Firefly (562 nm) | – | **#C8FF3C** (gamut-clipped) | – |
| Bioluminescence (480 nm) | – | **#39C8FF** (display target; raw #0092FF is too pure) | – |

### 1.4 Every emissive or unlit asset must be scene-referred
The cloud cards were delivered **already tonemapped** (Khronos PBR Neutral). Through ACES they get tonemapped twice, which darkens and oversaturates them.
- **Decision:** the cloud side re-exports every card and strip *scene-referred*: no tonemap, exposure −1 EV, straight alpha, sRGB PNG. The shader multiplies by 2. `make_clouds.py --repost` can do this from the kept EXRs.
- The cloud side also **re-lights the cards with the chosen HDRIs**. The implementer pushes a 1024×512 `.hdr` downsample of each HDRI to the repo; Cycles uses it as world light. Cards and sky then match exactly.
  - This also fixes the AD note on the current dawn cards, whose shadowed sides read muddy.
- One shader, **`Lanbai/UnlitCardHDR`**, for all cards, haze, shafts, halos and glows. Properties:
  - `_Tint` (HDR colour), `_Intensity`;
  - `_SoftFade` (m, soft-particle depth fade) and `_CamFadeNear/Far` (m);
  - `_FogMode`: 0 = none, 1 = Unity fog, 2 = custom attenuation `exp(-d·_Atten)`;
  - Blend: straight-alpha Fade or Additive, selected by keyword.

### 1.5 Fog rules (Built-in fog is the aerial perspective)
- **The fog colour must equal the sky's radiance at the horizon, before tonemapping.** Sample the skybox horizon in the Scene view with post off; that is the fog colour. When they differ, silhouettes glow or cut out against the sky.
- The skybox is never fogged in Built-in. Distant emissive points (town lights, city lights, palace lamps) must not use Unity fog either; they use `_FogMode 2`, so they stay visible as dim points long after surfaces have disappeared. That is how real night atmosphere looks.
- Scene fog is set by Udon on every scene change (`RenderSettings.fogColor`, `fogDensity`, `fogMode`) and cross-faded over 2–6 s, never cut.

### 1.6 Global PBR ranges (Unity Standard, metallic workflow)
- **Non-metal albedo:** linear 0.03–0.80 (sRGB 48–231). Deliberate exceptions:
  - tentacle skin and ink: 0.004–0.012 (sRGB 13–28);
  - wet asphalt and black rubber: 0.02–0.035.
  - Nothing is brighter than 0.85 (sRGB 237).
- **Metallic is 0 or 1.** Values in between appear only in mask transitions 1–2 px wide (chips, rust).
- **Smoothness reference** (perceptual, as in Unity):

| material | smoothness |
|---|---|
| dry asphalt | 0.15–0.25 |
| wet asphalt film | 0.72–0.85 |
| puddle | 0.96–0.98 |
| porcelain enamel | 0.88–0.93 |
| old car paint (sides) | 0.45–0.62 |
| old car paint (oxidised roof) | 0.25–0.35 |
| vinyl seats | 0.42–0.70 |
| rubber | 0.20–0.35 |
| stainless steel | 0.55–0.82 |
| chrome | 0.85–0.92 |
| glass | 0.97 |
| cloth | 0.10–0.25 |
| lacquer | 0.78–0.86 |
| cowrie shell | 0.92 |
| nacre | 0.86 |
| polished bronze mirror | 0.94 |
| patina | 0.30–0.35 |
| wet leaves | 0.55–0.65 |
| wet bark | 0.45 |

- **Wetness** (Lagarde's model), applied by the shaders through the global `_Udon_Wetness` (0–1):
  - **Porous materials** get their albedo multiplied at full wetness: asphalt 0.50, concrete 0.55, bark and wood 0.60, earth 0.55.
  - **Non-porous materials** (paint, enamel, glass, metal, vinyl) keep their albedo.
  - **Film smoothness:** lerp(s, 0.85, wet). Normal strength drops to ×0.6 because water fills the micro relief.
  - **Puddles:** albedo ×0.25, smoothness 0.97, normal ×0.05, plus rain ripples (§2.4).

### 1.7 The small custom shader set (the implementer writes these; the cloud side can draft them)
Standard alone cannot deliver the look. These seven shaders cover the whole world. Scene state is driven through VRChat's `VRCShader.SetGlobal*` (names must start with `_Udon`).

| Shader | Used on | Key parameters |
|---|---|---|
| `Lanbai/Cabin` (Standard-lit surface shader) | every cabin surface | `_Udon_CabinLightmap` (0–1): scales baked GI, for flicker and death. `_Udon_CabinAmbient` (colour): sky fill once the tubes die. `_Udon_CabinBleach` (0–1). `_Udon_CabinFade` (0–1), with local-seat exclusion `_Udon_SeatPos`. `_Udon_Caustics` (0–1). `_Udon_ReflCube` (exterior reflection). |
| `Lanbai/WetSurface` | road, pavement, bench, bus exterior, sign, poles | base PBR + `_WetMask` (R puddle, G wet film) + ripple texture + `_Udon_Wetness`, `_Udon_RainRate`. GGX specular from 4 extra lamps `_Udon_Lamp0..3` (xyz pos, w intensity), for moving sodium streaks without real-time lights. |
| `Lanbai/BusGlass` | all windows and the windscreen | droplets (static + running), `_Udon_RainAmount`, `_Udon_FlowDir`, grime mask, interior reflection cube × `_Udon_CabinLightmap`, optional refraction (one named GrabPass per frame). |
| `Lanbai/Sea` | sea from above, sea from below, the ceiling sea, puddle mirrors | two scrolling FFT normal maps + glassy/rough macro mask. Mode keyword: ABOVE (Fresnel reflect) / BELOW (Snell's window) / CEILING. `_Udon_ReflCube`, sun direction, the 4 lamps. |
| `Lanbai/Sky` (skybox) | every scene | HDRI cube + exposure + rotation, `_Mirror` (0/1: lower hemisphere = mirrored upper), procedural night gradient, star cube gain, moon disc and glow. |
| `Lanbai/UnlitCardHDR` | clouds, haze, shafts, halos, rain, particles | see §1.4 |
| `Lanbai/Tentacle` (cloud side) | tentacles | sway, wet streaks, moon rim, tear rim, tip translucency, height fog (§5) |

**Reflections:** changing `RenderSettings.skybox` at runtime does not update the default reflection cubemap. So every hero reflective surface (wet road, sea, glass, cabin metal, tentacles) samples an **explicit global cubemap `_Udon_ReflCube`**, which Udon sets per scene. It is the scene's sky cubemap, or a baked probe texture for the stop. Standard-shader props elsewhere can live with stale reflections.
- ⚑ Verify Udon exposure of `VRCShader.SetGlobalTexture`. Fallback: swap materials.

### 1.8 Texture budget (targets for the whole world, everything loaded at once)
- **Total texture VRAM ≤ 1.0 GB. Download ≤ 300 MB** (the 20 min of Vorbis audio is about 20 MB).
- **Compression:**
  - opaque albedo: BC1 (DXT1);
  - albedo with alpha, masks and cards: BC7 ("High Quality");
  - normals: High Quality normal compression;
  - single-channel masks: BC4;
  - HDR cubemaps: BC6H;
  - cloud cards: BC7 (DXT5 bands on soft gradients).

| Group | Resolution | ≈ VRAM |
|---|---|---|
| Sky cubemaps: dawn, dusk (HDRI 8K → 2048/face) | 2 × 2048² ×6, BC6H | 66 MB |
| Star glow cube (NASA) 2048/face + star-sprite mesh | BC6H | 33 MB |
| Night skies (stop, gate, false awakening) | procedural in `Lanbai/Sky`, one 1024×512 overcast `.hdr` | 3 MB |
| Cloud cards: 3 presets + city-below preset | per README | 60 MB |
| Cloud floor (top-down, tiling), 3 presets | 2048² BC7 + 1024² height | 20 MB |
| Bus exterior | 4096² albedo + mask, 2048² normal + tiling detail | 55 MB |
| Bus cabin: trim sheet, seats, floor, curtains, glass, radio | see §3.10 | 70 MB |
| Stop: asphalt, wet mask, ripples, sign, poles, bench, field, verge | see §2.10 | 45 MB |
| Sea normals, macro mask, caustics, ripples | 2×1024² + 1024² + 512² flipbook | 12 MB |
| City-lights tile + macro | 2048² + 1024² | 8 MB |
| Tentacles | 2048² set (shared) | 22 MB |
| Tear, threads, shafts, halos | 2048×512 + 1024² atlas | 8 MB |
| Palace kit: lacquer, scales, cowries, stone, bronze | 4 × 2048² sets | 90 MB |
| Bronze mirrors | 2048² front + 2048² back | 22 MB |
| Fonts (TMP SDF) | zh/ja 2048², Latin 1024² ×3 | 10 MB |
| Particles and misc | 1024² atlas | 5 MB |
| **Total** | | **≈ 530 MB**, leaving room for the user's Linluo trees and the Poly Haven props |

**Texel density in the cabin, the surfaces seen for all 20 minutes:**
- ≥ **512 px/m** within 1.5 m of the head: the seat in front, the window frame and sill, the stanchion, the floor at the player's feet;
- 256 px/m elsewhere in the cabin;
- tiling detail normals on top (§3).

### 1.9 Who makes what
**Implementer downloads** (CC0 or public domain, allowed hosts):
- Poly Haven: HDRIs; asphalt, concrete, gravel, soil, grass, bark, rusty and painted metal, leather and fabric textures; streetlamp and pole models.
- ambientCG (CC0) as the fallback for rubber floor, leather and perforated panels.
- NASA SVS: Deep Star Maps 2020 (I believe SVS entry 4851; 16K EXR, celestial) and the CGI Moon Kit (SVS 4720; LRO colour map).
- The user's Linluo trees.
- Fonts (§14).

**Cloud side makes** (procedural, we can't download): full list with priorities in §15. In short:
- the sign and timetable plate; the rain kit (ripples, droplets, streak and splash sprites); the window cookie;
- the overcast night sky; city lights; re-exported and re-lit cloud cards, the city-below preset and the cloud floor;
- the tear kit; FFT sea normals and caustics; the palace kit; the bronze mirrors;
- the star-sprite extraction script; the TMP character sets.

### 1.10 Calibration kit (build this first; it takes 10 minutes)
Put a hidden calibration rig on a layer the implementer can toggle in every scene:
- an 18% grey sphere (albedo sRGB 118) and an 80% white sphere (sRGB 231), Standard, smoothness 0.2;
- a chrome sphere (metallic 1, smoothness 1);
- a black sphere (sRGB 30).

For every scene, screenshot the rig at the bus window with post on, sample it with a colour picker, and compare against the *value maps* below. This is how the numbers here become right without us seeing the build.

---

## 2. Scene 1: 站牌 The stop (rainy rural road at night)

**Picture:** a small, exact, lonely island of 藍白 light in a black-blue rain. One tube lamp, one round enamel sign, a wet road mirroring both, the bus glowing the same cool colour. A warm dome of distant town light sits on the low cloud at the horizon. The world is kept **small and intimate on purpose**, so the grandeur of scenes 3–9 hits harder.

### 2.1 Layout decisions (look-dev consequences)
- **Drop the shelter** (候车亭). Keep only the sign pole, a concrete utility pole with the tube lamp, and a wooden bench. A stop that is only a sign fits "nobody knows where 蓝白 is", gives a stronger silhouette and costs less.
  - If the story lens insists on shelter drips, use drips from the lamp arm instead (§2.6).
- **The lamp is a bare fluorescent tube, not a warm bulb.** See `lookdev_sign_mock.png`: under a 2400K bulb the 藍白 field turns mustard and the name loses its colour. The tube makes the stop the same colour as the bus cabin, so the stop and the bus visibly belong to one other world. The warm things (town glow, headlights, tail lights) are the ordinary world around it.
- **The road beneath the bus is drier** than the rest (a crisp rectangle, smoothness 0.45 against 0.8, albedo ×0.8 instead of ×0.5). The bus has been standing here a long time. The same dry patch is there at the end: quiet evidence that **the bus never moved**.

### 2.2 Sky, fog, distance
- **Sky** (`Lanbai/Sky`, procedural): a low overcast deck with faint structure. The cloud side supplies `Sky_Overcast_Night.hdr` (2048×1024 RGBE): low-frequency cloud-base texture, lit from below toward the town (one azimuth).

| Direction | Display target | Enter (approx.) |
|---|---|---|
| Zenith | #070A0E | #191C21 |
| Horizon, away from town | #121418 | #25272B |
| Town-glow horizon (±25° wide, fading up to 12° elevation) | #1C1E22 → warm #2A221D at the core | – |

- **Fog:** Exp2, density **0.0068** (≈50% at 122 m, 16% at 60 m, 95% at 250 m). Colour enter **#25272B** (display #121418).
- **Silhouette layers**, each separated by ≥ 6 display levels so they read as layers:

| Layer | Distance | Display |
|---|---|---|
| Roadside trees | 15–40 m | 3–6 |
| Tree line | 80–150 m | 9–12 (fogged) |
| Hills: unlit cards, no fog | 600–900 m | 14–16 |
| Sky just above the hills | – | 18–22 |

- **Distant town lights:** 60–150 points in 2–3 clusters at 700–1500 m. Colours: 70% #FFAE32, 20% #FFC369, 10% #E1ECFF.
  - Sprites 2–4 px at 1080p, HDR 1.5–4.0, `_FogMode 2`, `_Atten` 0.0009 (so they dim with distance but stay visible).
  - Slow scintillation: ±15% at 0.5–2 Hz, per-light phase.
  - Over the town, a large soft **light-dome card**: additive, 1.2 km wide, #2A221D display at the core.
- **The distant truck** (synced to the audio cue): a pair of #FFEDD0 headlight sprites plus a faint red pair, crossing a far road at 1.1–1.3 km, taking about 40 s. Its light also sweeps the flooded field (as a reflection sprite).

### 2.3 The sign 「蓝白」 (designed in full)
**Form**
- One **circular porcelain-enamel disc, Ø 600 mm**, 1.2 mm steel with a 6 mm rolled edge, enamel on both sides.
- Mounted by a rear clamp on a **Ø 60 mm galvanised steel pole**; disc centre at **2.25 m**. Pole 2.6 m, set in a 400×400×150 mm concrete footing.
- Round was chosen over rectangular: it is the most universal "bus stop" silhouette (Europe, Japan, old China) without belonging to any one place.
- Below the disc, on the same pole, a **300×420 mm timetable plate** (see below).

**Front face** (outside to centre)
- 38 mm **indigo ring** **#1D3E66**, then a 10 mm field gap, then a 3 mm indigo hairline.
- Field **藍白 #EBF6F7** (linear 0.83/0.92/0.93).
- The two hanzi: **cap height ≈ 175 mm, character box 182 mm**, set horizontally, optical centre 30 mm above the disc centre, letter-space +18 mm.
- Romanisation: cap height 36 mm, 150 mm below centre, tracking +0.30 em.
- All ink is **#1D3E66**.

**Language variants** (Udon swaps the albedo, like the poems; "in a dream the sign speaks your language")

| Player language | Big line | Small line |
|---|---|---|
| zh, and every other language including en | **蓝白** | **LANBAI** |
| ja | **藍白** | **あいじろ** |

The hanzi *are* the name, so English players see 蓝白 + LANBAI, the way real station signs work. A place name is never translated on a sign.

**Typography**
- Hanzi: **Source Han Sans SC Heavy** (思源黑体) for zh; **Source Han Sans JP Heavy** (源ノ角ゴシック) for ja, so 藍 uses JP glyph forms.
- Kana: Source Han Sans JP Medium.
- Latin: **Barlow Semi Condensed SemiBold** (road-sign heritage).
- All SIL OFL.
- Gothic, not Ming, because it is a sign. The poems get the serif (§14).
- The mock uses WenQuanYi Zen Hei as a stand-in; the real Heavy weight is noticeably bolder.

**Material** (1024² set: albedo BC7, normal, MetallicSmoothness)

| Zone | Albedo | Smoothness | Metallic | Notes |
|---|---|---|---|---|
| Enamel field / ink | #EBF6F7 / #1D3E66 | 0.90 (±0.02 low-freq) | 0 | normal: enamel "orange peel" 0.15 + water beads 1–4 mm |
| Chip halo (ground coat) | #22262B | 0.50 | 0 | 1–2 mm ring around every chip |
| Chip core (rust) | #6B3A1E–#8A4A22 | 0.25 (0.45 wet) | 0 | |
| Rust bleed streaks | #8A4524 at α 0.3–0.45 | 0.70 | 0 | 5–15 mm wide, 50–150 mm long, running **down** from chips and the bottom bolt |
| Bolt holes (12 and 6 o'clock) | #0D0D0D | – | 1 | Ø 8 mm with chipping around |
| Grime film | #6B665C at ≤ 10% | – | – | stronger at the bottom third and the rim |

**Wear story**
- **The enamel never fades.** The colours are as crisp as the day it was fired; enamel is glass and resists UV. Only the rim and bolt holes are chipped: 8–12 chips of 4–25 mm, concentrated at the lower rim where water sits.
- The **timetable plate** is the opposite: painted aluminium (#D7D9D4, smoothness 0.30) whose screen-printed times have **faded to ghost rules and illegible marks** (#B9BDBA on #D7D9D4, no readable characters). The name survives; the times do not. Nobody knows when the bus comes.

**Rear face:** plain indigo **#1D3E66** enamel with the clamp and more rust.

**Target at EV0** under the tube:
- field display **#C9DDE2** (185–205 per channel); ink 28–40;
- the disc's specular strip from the tube at 240–255;
- beads glinting.

### 2.4 The road and wet asphalt (the showpiece)
**Road:** 6.5 m two-lane rural asphalt, no kerbs, a 0.8 m gravel and earth shoulder each side.
- **Faded white centre dashes only** (3 m on / 6 m off, 60% worn): white is internationally generic, yellow reads regional.
- A worn **white edge line**, broken, 40% remaining.

**Base texture:** Poly Haven asphalt, **2K tiling at 1 tile per 3 m**. Pick a fine-aggregate, lightly cracked, worn road (not fresh black, not racetrack). The cloud side adds a unique **stop-area mask**:
- `Stop_WetMask` 2048×512 covering 48 m × 12 m.
- R = puddles: 15–25% coverage in the wheel ruts (two longitudinal tracks 1.8 m apart), potholes, the low road edge and the bus's door side.
- G = wet-film variation.
- B = the dry rectangle under the bus.

**Values** (`Lanbai/WetSurface`, wetness 1)

| Zone | Albedo | Smoothness | Normal |
|---|---|---|---|
| Dry reference (only under the bus) | sRGB 70–95 (linear 0.06–0.11) | 0.20 | 1.0 |
| Wet film (most of the road) | ×0.5 → linear 0.03–0.055 | 0.74–0.84 (from G) | 0.6 |
| Puddles | ×0.25 | 0.97 | 0.05 + ripples |
| Paint lines (wet) | linear 0.45 | 0.70 | – |
| Gravel shoulder | linear 0.08 wet | 0.55 | – |

**Why wet film sits at 0.74–0.84 and not 0.95:** GGX at grazing angles stretches a point light's highlight into a long vertical streak toward the viewer, but only when the surface is moderately rough. That streak is what the eye reads as "wet road at night". Mirror-smooth asphalt shows only a dot. The puddles supply the mirror reflections.

**Reflections**
- **One box-projected baked reflection probe** at the stop: 512 res, HDR, box 48×10×20 m. It contains the lit bus, the tube and the sign, so puddles mirror them. Its texture becomes `_Udon_ReflCube` for scenes 1 and 12.
- **The tube lamp is Mixed** (Baked Indirect): real-time direct specular gives the GGX streak on the wet film. The bus headlights and tail lights are real-time spots with no shadows, for their streaks.

**Rain ripples in puddles**
- The cloud side makes `RainRipple_512.png` (RGBA): RG = ring normal, B = per-ripple time offset, A = ring mask; about 40 ripples per tile, tile = 0.8 m.
- The shader animates rings with `frac(_Time·rate + B)`, strength × `_Udon_RainRate`.
- Drizzle: 3–5 ripples/m²/s, rings expand to 4–7 cm radius.

**Target values at EV0**

| Element | Display |
|---|---|
| Wet asphalt in the pool | 10–18 |
| Wet asphalt out of the pool | 2–5 |
| Tube streak | core 255, tail fading over 6–10 m toward the viewer |
| Puddle mirror of the bus windows | 150–200 |
| Tail-light streaks | red 255 core |

### 2.5 Tube lamp, utility pole, wires
- **Pole:** spun-concrete, tapered Ø 280 → 190 mm, 9 m tall. Albedo linear 0.22 dry / 0.12 wet (#8C8B85 → #5E5D59 display under the tube), smoothness 0.35 wet, with vertical rain-streak staining.
- **Fixture:** a steel bracket arm 1.2 m long at 4.2 m height holding a **simple enamel trough reflector**: outside dark green-grey **#3E4A45** (smoothness 0.6, chipped), inside white enamel. Under it, a **bare 1.2 m T8 tube**:
  - emissive display ≈ #F4FCFD; enter **#97E7FF × 7.7** (the ACES desaturation compensation, §1.1);
  - the two tube ends are slightly darker (end-blackening bands, 3 cm, #8C9396).
- **Light:** baked **area light 1.2 × 0.04 m** pointing down, colour **#CFEAF0**, plus a Mixed point light for the real-time specular.
  - Tune the area light until the sign field reads display 185–205 and the road directly below reads 14–18 (wet).
- **Wires:** 3 cables sagging to the next poles 40 m away, black, smoothness 0.6. Near the lamp they catch the tube as thin lines. Beaded drops hang along 2 m of cable near the lamp: 20–30 tiny sprites with a bright specular dot.
- **Moths** around the tube: 6 in the rain (14 at the awakening). Size 1.5–3 cm, erratic orbits of 0.3–0.8 m radius, colour lit #C7D6D8. Noise module strength 1.5, frequency 2.

### 2.6 Rain (drizzle 细雨), mist, drips
The rain is **only visible where it is back-lit or side-lit**. That is the whole cinematic trick; uniform rain everywhere looks like a screensaver.

| System | Volume / emitter | Count | Look |
|---|---|---|---|
| Lamp-cone rain | cone under the tube, r 5 m, h 5 m | **1800** alive | stretched billboards 0.25–0.40 m × 4–6 mm, 5 m/s, 8° wind lean, #E8F6F8 at α 0.30 (display 60–120) |
| Headlight-beam rain | two 25 m beam volumes | **900** | same, tint #FFEDD0 |
| Ambient rain (everywhere else) | 30 m radius around the player | **600** | #9AA4AA at α 0.06 (barely there) |
| Splashes (lit pool) | on the asphalt, 6 m radius | 200/s, life 0.15 s | 3–6 cm crowns (4-frame sprite) |
| Drips from the lamp arm and the sign's lower rim | 3 points | 1 per 1.5–4 s | a drop plus a single ripple ring in the puddle below |
| Ground mist over the fields | 12–16 horizontal cards, 20–40 m wide, 0.4–2 m high | – | `UnlitCardHDR` Fade, α 0.08–0.14, display #16181C, drift 0.2 m/s, soft fade 3 m |
| Tube halo | 1 card round the tube | – | additive, r 1.6 m, #CFEAF0 → 0, α 0.18. Fakes in-scatter in the humid air. |

**Cloud-side rain kit:**
- 4-frame streak atlas (4 × 64×512);
- 4-frame splash atlas (256²);
- a static droplet normal (1024², tile 0.4 m, drops 1–5 mm) plus a running-drop flow texture for the glass (§3.6).

### 2.7 The bus exterior (seen here and in scene 12)
- **Livery (two-tone, 蓝 and 白 once more):**
  - Upper body cream-white **#E6E1D3** (linear 0.78), smoothness 0.55 on the sides, oxidised roof 0.28 and chalky.
  - Lower body faded indigo **#34506E** (linear 0.035/0.08/0.16), smoothness 0.50, lighter and chalky near the roofline and on sun-facing panels.
  - A 20 mm silver pinstripe between them (metallic 1, #BFC2C4, smoothness 0.7).
- **Weathering** (baked by the implementer in Blender from curvature and AO):
  - rain-track grime runs from the corners of every window (#5B574E, α ≤ 0.35);
  - rust bubbles on the wheel arches and door sills (#6B3A1E, smoothness 0.25);
  - mud spatter on the lower 30 cm (#5A4A3A, α ≤ 0.6);
  - chipped paint on door edges down to grey primer #8A8C88.
- **Wet:** vertical panels at smoothness 0.85 with the droplet normal at 0.4 strength; water sheets rather than beads (old paint).
- **Tyres** #1C1C1C, smoothness 0.55 wet. Steel wheels painted cream, rust at the lug nuts.
- **Glass from outside:** `Lanbai/BusGlass` shows the lit cabin through drops. Cabin windows from outside display 200–235 (cool white).
- **Destination blind** (roller blind in the windscreen header): black linen #141414 with **蓝白** in white, cut-through translucent letters, back-lit by the cabin tube:
  - letters display #F2F5F0 (enter HDR ×2.5), linen visible at display 8–12;
  - Source Han Sans SC Heavy, cap height 140 mm, no route number.
  - The glowing 蓝白 in the rain is the second time the player meets the name.
- **Head and tail lights:**
  - Headlights: halogen #FFEDD0; lens emissive HDR ×6; real-time spots, no shadows, range 30 m, 35° cone, with beam rain.
  - Tail lights: **#FF2A12** display, HDR ×3, plus a small lens halo sprite.
  - The headlights are on, which is the uncanny part: "lights on, no driver".
- **Texture:** 4096² albedo + mask, 2048² normal + tiling 1024² detail normal (paint orange-peel, 4 tiles/m).

### 2.8 Fields, verge, trees
- **Flooded field** beside the road, after rain: water between low earth bunds.
  - One water plane using `Lanbai/Sea` in a still-mirror mode: smoothness 0.95, black albedo, `_Udon_ReflCube`, rain ripples at 30% strength.
  - Bunds are dark strips (linear 0.03 wet earth); sparse stubble clumps are alpha cards, 0.3 m, ~400 of them.
  - It mirrors the town glow, the truck and later the fireflies. It is the **first foreshadowing of the mirror sea.**
  - For particles (fireflies, truck), use a **mirrored duplicate particle system** under the water plane at α 0.35.
- **Verge:** dense wet grass clumps only within 4 m of the road (albedo #2B3A22 → reads teal-grey under the tube), smoothness 0.55 wet, alpha cards with vertex wind of 2 cm. Beyond 4 m, a textured ground plane.
- **Linluo trees** (the user's): wet adjustments:
  - bark albedo ×0.6, smoothness 0.45;
  - leaves smoothness 0.6 so the tube throws cool glints on the nearest canopy;
  - far trees are fog-dissolved silhouettes (§2.2).
- **Bench:** two concrete legs, one oak plank 1.6 m long. Albedo wet #3A2E26, smoothness 0.55, moss at the leg bases (#3F4A2A, smoothness 0.2).

### 2.9 Value map, scene 1 (display at EV0)

| Element | Display |
|---|---|
| Sky above the tree line | 18–22 |
| Tree silhouettes | 3–6 |
| Sign field | 185–205 |
| Sign ink | 28–40 |
| Pole under the lamp | 60–80 |
| Wet road in the pool | 10–18 |
| Tube and streak | 255 |
| Bus windows | 200–235 |
| Bus lower indigo panels under the tube | 25–40 |
| Rain in the cone | 60–120 |
| Town dome core | #2A221D |
| Bloom | intensity 1.0, threshold 1.0, soft knee 0.5, diffusion 7 |

### 2.10 Stop texture list
| Asset | Resolution |
|---|---|
| Asphalt set (tiling) | 2048² |
| Stop wet mask | 2048×512 |
| Ripple | 512² |
| Sign ×2 language variants + timetable | 1024² sets |
| Concrete pole (tiling) | 1024² + unique streak mask 256×2048 |
| Enamel trough | 512² |
| Bench | 1024² |
| Field soil / bund | 1024² |
| Grass | 1024² alpha atlas |
| Stubble | 512² |
| Mist and halo | shared particle atlas |

---

## 3. THE BUS CABIN (seen for all 20 minutes)

The cabin is the frame around every scene, so it must look *true* at 0.3 m in VR and must also stay quiet enough that the view outside is the star. **Palette:**
- **oxblood vinyl seats** (humanity, age, warmth);
- **cream** ceiling and walls;
- **pale-indigo cloth curtains** (藍白 once more);
- **stainless** rails;
- **charcoal rubber** floor.

Maroon, cream and pale blue form a split-complementary set that stays beautiful under 藍白 tubes, amber sodium sweeps, gold dawn and rose dusk alike.

### 3.1 Surfaces (Unity Standard values inside `Lanbai/Cabin`)
| Surface | Albedo (sRGB) | Smoothness | Metallic | Normal | Notes and source |
|---|---|---|---|---|---|
| Seat vinyl, base | **#5A2126** (R 78–110, G 28–45, B 30–48) | 0.45 | 0 | fine grain 0.35 | leather-grain texture from Poly Haven / ambientCG, tinted |
| Seat vinyl, polished sit zones (seat pan centre, backrest upper-middle, grab edge) | slightly lighter and desaturated, #6A3434 | **0.62–0.70** | 0 | 0.25 | 30 years of passengers. Bake the mask. |
| Seat vinyl, sun-faded window-side top edge | #7A4A48 | 0.40 | 0 | – | |
| Vinyl cracks and splits at seams | #8A6A60 (exposed backing) | 0.20 | 0 | crack normal 0.8 | 2–5 per seat, at piping and corners |
| Seat grab bar on the backrest top | chrome #CFD1D3 | 0.85, pitted to 0.7 | 1 | – | |
| Seat frames and pedestals | #3A3C3B | 0.35, scuffed to 0.5 | 0 | – | |
| Floor: ribbed or studded rubber (Ø 25 mm studs, 50 mm pitch) | **#2E3230** (linear 0.027–0.032) | 0.22 | 0 | 1.0 (studs 1.5 mm) | aisle lane scuffed lighter #4A4B47, smoothness 0.35; dust in corners #555550 |
| Door step nosing | aluminium, metallic 1, #B8BBBD | 0.5 | 1 | – | yellow safety strip #C9A227 worn through to metal at the centre |
| Lower wall panels | cream enamel paint **#D9D4C5** | 0.45 | 0 | rivet rows every 150 mm (trim sheet) | shoe scuffs #5B5A55 near the floor |
| Ceiling: perforated hardboard/vinyl | **#E2DDCF** (slightly yellowed) | 0.25 | 0 | perforations (Ø 3 mm, 12 mm grid) | the perforations are a strong realism cue at 0.5 m |
| Tube diffusers (opal acrylic, 1.2 m × 120 mm) | off: #D8DBD6 | 0.6 | 0 | – | **dead-insect silhouettes inside the cover** (4–10 dark specks per tube, visible only when lit) |
| Stanchions and ceiling rails, Ø 32 mm stainless | metal **#C0C3C4** (linear ≈ 0.53) | 0.55; **0.80 at grip heights 1.0–1.8 m** | 1 | – | long vertical highlights of the tubes; reflect `_Udon_ReflCube` |
| Window frames | anodised aluminium #B8BBBD | 0.45 | 1 | – | |
| Window gaskets | #1A1A1A | 0.30 | 0 | fine cracking 0.5 | |
| Curtains | §3.5 | | | | |
| Dashboard | #2A2B2C textured plastic | 0.30 | 0 | fine pebble 0.4 | gauges faint green-cyan (#7CFFB0 × 0.3 HDR), no numbers |
| Steering wheel (thin, large, bakelite) | #1E1E1E | 0.45, **0.72 on the worn grip** | 0 | – | |
| Driver's seat | same vinyl, the most worn | 0.70 on the pan | 0 | – | empty; no props, no text |

### 3.2 Tube lights
- **Layout:** two rows × 5 tubes along the ceiling, 1.2 m each.
- **Colour and intensity:**
  - light colour **#CFEAF0**;
  - diffuser emission display ≈ #F4FCFD (enter #97E7FF × ~7.7, same as the stop tube);
  - baked **area lights** 1.2 × 0.12 m, one per tube.
- **Targets at EV0:**

| Surface | Display |
|---|---|
| Ceiling beside the tubes | 200–220 |
| Seat-back tops | ≈ (95, 38, 40) |
| Aisle floor | 30–40 |
| Stanchion highlights | 255 streaks |

- **Mechanism:** the tubes are baked, and dimmed or flickered through `_Udon_CabinLightmap` (scales the baked GI) together with the emission value, driven by the same Udon float so the light and the glowing tube stay in sync.
- **The glass reflection of the interior** (§3.6) is scaled by the same float.
- **Flicker at the tentacle gate** (a dying fluorescent, not a disco):
  - dips to 5–40% lasting 40–120 ms;
  - rate rising from 0.1/s to 3/s as the tear nears;
  - each tube has its own random sequence; neighbours correlate 30%;
  - during a dip the tube's ends glow dull orange (#FF8A50 at 5%).
  - **At the tear entry: one 150% flash, then all tubes die.** They stay off until the false awakening.

### 3.3 The radio (the only warm light inside)
- **Form:** a 1970s–80s transistor radio in a brown leather case, on a bracket beside the driver's seat.

| Part | Albedo | Smoothness | Metallic | Other |
|---|---|---|---|---|
| Leather case | #4A2E1F | 0.45, 0.6 worn | 0 | |
| Grille (brushed aluminium, perforated) | #B8BBBD | 0.55 | 1 | |
| Knobs (knurled chrome) | – | 0.85 | 1 | |
| Dial window | glass over a cream dial face #E8DFC8 | – | – | frequency ruling with **no numerals**, a red needle #C0392B |
| Dial backlight | – | – | – | **#FFB24A** display (entered #FFC369 × 1.5 HDR) |

- **Behaviour:**
  - The dial glows faintly (±8%) with the signal. Implement it as an Udon envelope follower on the Urlicht AudioSource if `GetOutputData` is allowed, otherwise a noise curve.
  - At lift-off, as the sound "opens" out of the radio into the space, the dial **brightens from 1.5 to 3 HDR over 6 s, then settles back**.
  - At the plunge it goes **dark and never returns**. From then on the music belongs to the world, not the radio.
  - In the false awakening it is on again, playing only static, the dial flickering with it.
- **Texture:** 1024² set.

### 3.4 Lighting model through the ride
- **The cabin is baked** with the tubes on, and the bus can still move. Its renderers are Contribute-GI static but **not** Batching-static, so the lightmap stays attached to the moving mesh.
- **Once the tubes die**, the cabin's light comes from:
  1. **`_Udon_CabinAmbient`**: the scene's sky-fill colour × the baked AO (Udon sets it per scene; values in each scene section);
  2. **one real-time directional light** (sun or moon) with hard shadows and 25 m shadow distance, for window-shaped light on the seats. It also gives the depth texture that soft particles need.
- **Night-road sweep:** one real-time **spot light with a window-frame cookie** (512² greyscale, drawn from the bus's real window layout; the implementer sends us the side elevation). It animates front → back as each sodium lamp passes, so no real-time shadows are needed.
  - Colour **#FFAE32**.
  - Peak on the window-side seat tops is **+1.3 stops over the tube light** there, falling to near zero across the aisle.
- **Side spill:** two side spots with the same cookie pointing outward, #CFEAF0, range 12 m, no shadows. The bus's lit windows then slide as cool rectangles over the roadside grass and trunks.
- **Dawn and dusk beams:** extruded window-shape beam meshes along the sun direction, parented to the bus, `UnlitCardHDR` additive:

| | Colour | Alpha |
|---|---|---|
| Dawn | #FFD9A8 | 0.06–0.10 |
| Dusk | #FFB38A | 0.08 |

  - Plus **dust motes**: 300 particles inside the beams only, 1–3 mm, slow Brownian drift, lit (brighter inside the beam mask).
- **Underwater caustics** (scene 7, near the surface): `_Udon_Caustics` projects a scrolling caustic texture onto up-facing cabin surfaces in world XZ.
  - Two layers min-blended, 0.6 m and 1.1 m tiles, 0.3 Hz.
  - Intensity 1 at the surface → 0 at 15 m depth.
  - Once the roof starts eroding, caustics fall through the holes.

### 3.5 Curtains (pale indigo, the cabin's 蓝白)
- **Fabric:** cotton-poly, **#9FB3C3** base, sun-bleached vertical stripes #B7C5CF, a slightly darker hem #8898A8.
  - Smoothness 0.18; weave normal 0.3 (1024² tiling, 3 tiles/m).
  - Unique 512² fade mask.
- **State at the start:** half-drawn and tied at 3 windows, loose at 5, fully open at the player's window.
- **`Lanbai/ThinCloth` lighting** (a variant of `Lanbai/Cabin`): wrap diffuse 0.35 plus **transmission** = saturate(dot(−N, L)) × 0.45 × albedo².
  - Back-lit curtains glow pale blue at dawn and blue-lilac at dusk. This is one of the most beautiful things in the cabin.
- **Vertex motion, per scene** (amplitude / frequency):

| Scene | Motion |
|---|---|
| Stop | 0 |
| Road | 1–2 cm / 0.8 Hz sway |
| Lift-off | 4 cm |
| **Underwater** | **buoyant upward billow 10–20 cm / 0.2 Hz** (curtains float) |
| **Dusk (walls gone)** | **30–60 cm wind billow** |
| Stars | slow 15 cm drift, then fade |

### 3.6 Windows and windscreen (`Lanbai/BusGlass`)
- **Base:** transparent. Tint multiply #E9EFEA (old-glass green), base alpha 0.06, smoothness 0.97, F0 0.04.
- **Grime** (unique 2048² atlas for all windows):
  - lower corners and gasket edges up to α 0.25, #6D6A60; centre 0;
  - windscreen: two **cleaner wiper arcs**, grime outside them.
- **Interior reflection:** a baked cabin cubemap (tubes on), sampled with Fresnel × `_Udon_CabinLightmap`:
  - at night strength 0.6: the player sees the cabin and the tubes reflected over the dark exterior (the essential night-bus look);
  - in day scenes 0.15.
- **Rain states** (`_Udon_RainAmount`, `_Udon_FlowDir`):

| Scene | Rain | Flow |
|---|---|---|
| Stop | 1.0 | static beads + occasional slow runners, 2–5 cm/s, stop-start |
| Road | 1.0 | runners pushed **backward-diagonal 30–60°** by speed |
| Lift-off | 1 → 0 over 20 s | drops streak up and back and thin out; above the cloud tops, drops shrink and vanish (evaporation) |
| Scenes 4–10 | 0 | clean glass |
| Underwater | – | glass alpha → 0.02 (water on both sides) |
| False awakening | 0 | **dry and slightly too clean**: the uncanny normal |
| Awakening | 0.4 | static beads left from the rain |

- **Refraction:** one named GrabPass (`_LanbaiGrab`) per frame for the droplets only, offset 0.02 × drop normal, so drops refract the lamps as tiny inverted bokeh.
  - Fallback if the frame budget is tight: no grab, drops as normal-mapped specular + 8% darkening.

### 3.7 The cabin "slowly fades": you have been falling all along
It is **not** a sci-fi dissolve and **not** a ghostly transparency. The cabin is **bleached by light, then eroded into the sky**, in the colour of whatever sky surrounds it, from the roof and the front toward the player's own seat. The player's seat goes last.

**Mechanism** (all in `Lanbai/Cabin` and `ThinCloth`)
1. **Bleach** (`_Udon_CabinBleach`): albedo moves toward luminance × 0.9, tinted by `_Udon_CabinAmbient`, and smoothness moves toward 0.3. The cabin loses its colour first, like cloth left in the sun.
2. **Erode** (`_Udon_CabinFade`):
   - Clip against 3D world-space FBM noise (blotch scale 0.3–0.8 m) with a bias: threshold = fade − 0.45·(1 − heightNorm) − 0.25·(frontness), so roof and front go first.
   - **Exclude a 0.9 m sphere around the local player's seat** (`_Udon_SeatPos`, set from the occupied station) until the last stage.
   - Eroding edge: 3 cm band emitting `_Udon_CabinAmbient` × 1.5. The edge glows the sky's own colour, **never orange**.
   - Use `clip`, not dithering: VR-stable and cheap on a small cabin.

**Schedule**

| Scene | Lightmap | Bleach | Fade | What the player sees |
|---|---|---|---|---|
| 4 Gate | 1 → flicker → 0 at entry | 0 | 0 | the whole cabin, dying tubes |
| 5 Plunge | 0 | 0 | 0 | darkness |
| 6 Dawn | 0 | 0 → 0.10 | 0 | the intact dark cabin as a silhouette frame around a luminous sky; gold beams, dust |
| 7 Sea | 0 | 0.10 → 0.25 | 0 → 0.25 | roof panels erode; caustics pour through; curtains float; bubbles from seat seams (40 particles) |
| 8 Dusk | 0 | 0.25 → 0.5 | 0.25 → 0.65 | roof and upper walls gone; seats, floor and stanchions remain; curtains fly in the dusk wind on their floating rails |
| 9 Stars | 0 | 0.5 → 0.8 | 0.65 → 0.97 | floor gone except under the player's seat; the other seats vanish; **stanchions last** (thin silver lines against the Milky Way) |
| 9 End, last mirror | 0 | 1 | 0.97 → 1 | the player's own seat erodes; nothing between you and the stars |
| 10 White | – | – | 1 | – |
| 11 False awakening | **1 (steady)** | 0 | **0** | the whole cabin snaps back, intact and ordinary. That is the shock. |
| 12 Awakening | 1 | 0 | 0 | the same |

**Sky-ambient `_Udon_CabinAmbient` values** (enter, linear-ish):

| Dawn | Sea (shallow) | Deep | Dusk | Stars |
|---|---|---|---|---|
| #A9A3C8 × 0.5 | #3E8D95 × 0.6 | #11232C × 0.3 | #9C7FB8 × 0.45 | #232A3A × 0.3 |

⚑ **VR comfort:** keep the floor under the local seat until scene 9, and flag it to the story lens.

### 3.8 Cabin props
- **None**, apart from the radio and the empty driver's seat. No bag, no newspaper, no bead seat cover (too regional), no fare box. Emptiness is the content.

### 3.9 Particles in the cabin
| System | Count |
|---|---|
| Dust motes in beams (dawn, dusk) | 300 |
| Bubbles from seat seams (sea) | 40 |
| Marine snow drifting through the cabin (deep) | inside the §7 system |

### 3.10 Cabin texture list
| Asset | Resolution |
|---|---|
| Trim sheet: panels, rivets, perforation, gaskets, vents | 2048² (albedo, normal, mask) |
| Seat set, shared by all seats | 2048² + wear/polish masks 1024² per seat UV |
| Leather-grain detail normal | 1024², 8 tiles/m |
| Floor rubber (tiling) | 1024², 2 tiles/m + unique aisle dirt mask 2048×512 |
| Curtains | 1024² tiling + 512² fade mask |
| Glass grime atlas | 2048² |
| Droplets | 1024² ×2 |
| Radio | 1024² |
| Dashboard and wheel | 1024² |
| Interior cube | 256/face HDR |
| Window cookie | 512² |
| Caustics | 512² flipbook 16 frames |

---

## 4. Scene 2: 夜路 Night road

**Picture:** the cool cabin as a lit box sliding through rain; amber sodium light sweeps rhythmically through it (the teal-and-amber of cinema, reached physically); the wet road ahead streaked with amber.

- **Streetlamps:** 9 m spun-concrete poles with **cobra-head sodium luminaires** (glass refractor bowl glows #FFAE32 HDR ×4).
  - Spacing: 35 m through the village stretch (≈ 400 m), then a **dark stretch** (600 m, only the bus's own light), then sparse lamps again.
  - Lamp pools: baked; road pool target display 40–60 wet.
  - **Specular streaks** on the wet road come from the 4 nearest lamps fed into `Lanbai/WetSurface` (`_Udon_Lamp0..3`), updated by Udon each frame. That gives live GGX streaks for free.
- **Sweep through the cabin:** §3.4. At 50 km/h with 35 m spacing, one sweep every 2.5 s, each crossing the bus in ≈ 1 s.
- **Village:** 6–10 houses, dark, with 1–3 lit windows each: #FFC369 behind curtains (emissive × 1.5), one cool TV-flicker window (#A6C3FF, random 0.3–1 s luminance changes).
- **Roadside:** wet verge and trees lit only by the side-spill cookie spots (§3.4) and the lamps.
- **Rain:** window rain as in §3.6. Exterior rain only in the headlight beams (900) and inside each lamp cone as the bus passes (a 400-particle system that moves with the nearest lamp).
- **Fog:** Exp2 0.0070, enter #212326 (display #0E1013).
- **Value map:**

| Element | Display |
|---|---|
| Cabin | as §3.2 |
| Sweep peak on seat tops | ≈ (210, 130, 50) |
| Outside, dark stretch | 0–8 (the reflection of the cabin in the glass dominates) |
| Road streaks | 255 core |

---

## 5. Scene 3: 离地 Lift-off (road → sea of lights → sea of clouds)

**Picture:** the ground falls away and becomes a vast field of amber and white lights, far larger than any real town, running to a horizon where it dissolves into a warm haze band **and continues upward as stars**. Up and down stop being different. Then the bus rises through a cloud deck **lit orange from beneath by the city**, and breaks out into silver moonlight over an endless cloud plain.

**Sea of lights (cloud side makes it)**
- `CityLights_Tile_2048.png` (1 km² per tile): an organic road network (not a grid).

| Layer | Share | Colour |
|---|---|---|
| Sodium street lines, 1–2 px | 55% | #FFAE32 |
| Warm building clusters | 25% | #FFC369 |
| Cool LED | 15% | #E1ECFF |
| Rare red aviation dots | – | – |

  - Plus **dark voids**: fields, and **one sinuous river band**, dark and edged by reflected light shimmer (animated in the shader, ±30% at 1 Hz).
- `CityLights_Macro_1024.png` over 40 km: density clusters and dark valleys.
  - The shader tiles with random rotation per tile (hex tiling) to hide repetition.
- **Shader:** `UnlitCardHDR` on a huge plane, emission ×3–6, so the brightest points pass 1.0 and bloom. Fog mode 2, `_Atten` 0.00008, colour-shifted toward the haze.
  - Twinkle: ±20% at 1–3 Hz, only for texels > 5 km away.
- **Light-dome haze:** 3 stacked horizontal haze layers at 50/150/300 m above ground, additive, display #2A211B, α 0.10 each. The glow a city puts on its own air.
- **Horizon:** the lights fade into a 3–5° haze band. The haze band's colour (enter #3A332D) grades into the night sky, where **bright stars only** (mag < 3, about 200) start just above it. The eye cannot tell where lights end and stars begin.

**Clouds**
- **Cloud base, city-lit:** a new cloud-card preset **`citybelow`** from the cloud side. Key light: a large area light under the clouds (#FFAE32), with the moon (#9DB8FF, weak) from above. Types: Strato, Wisp, Bank, plus one CloudSea strip seen from below.
  - Deck at 1200 m; its underside display ≈ **#7A4A2A** at the brightest.
- **Inside the cloud** (3–5 s): fog Exp2 0.08. Colour warm #3A3530 → cool #2B3346 across the traverse. 6–10 Wisp cards pass the windows within 2–4 s (camera fade 1–4 m).
- **Break-out into moonlight:** fog drops to Exp 0.0004, enter #2B3346 (display #18223A).
  - Cloud sea: `moon` cards + `CloudSea_*_moon` strips at 1500–4000 m radius.
  - A new **top-down tiling cloud floor** (cloud side: `CloudFloor_moon`, 2048² RGBA + 1024² height, tile 800 m): two parallax layers 40 m apart directly under the bus. Vertical cards cannot be looked straight down at.
  - Moonlit cloud tops display ≈ **#9FB2D0**.
- **The moon:**
  - NASA LRO colour map on a 1024² disc, desaturated 70%;
  - **angular diameter 1.2°** (2.3× real: reads big and dreamlike without looking cartoonish);
  - disc display 235–245 (maria stay visible, do not clip);
  - glow sprite 8° radius, additive, display ≈ #3A4868 at the edge of the disc falling to 0;
  - position: 35° to the left of the future tear and 50° up, so it back-lights the tentacles without competing with the tear.
- **Moon light:** directional #9DB8FF. It is the key light of scenes 3–4; everything else is expressed relative to it.

---

## 6. Scene 4: 触手之门 The tentacle gate

Composition and scale follow SPEC.md (tear 1–2 km, tentacles from 25 m to 450 m, low camera looking up). This section covers the materials and atmosphere that make it read as awe rather than a render.

### 6.1 The sky is indigo silk, and the tear is a rip in the dye
The concept that gives the tear meaning and a material:
- The night sky is **indigo-dyed cloth**. The tear rips it and shows **the undyed white beneath**: 蓝 torn open to 白.
- The edges are **frayed silk fibres** catching the light. The violet halo already built in the main scene stays, as the glow bleeding through the torn weave.

| Part | Spec |
|---|---|
| **Tear ribbon** | emissive mesh, jagged lens shape, **1.4 km tall, 180 m at its widest**, with 3 inner offset shells (depth). Core display **#FBF8FF**: enter about #E9DFFF × 16 HDR, so it clips to white with bloom. Gradient to **#8A5CFF** within 30–60 m of the edge. |
| **Torn lip** | a 2–6 m bright edge band with 5% jitter, and **600 fibre cards** (alpha-tested strands 2–15 m long, 0.1–0.4 m wide) growing from the lip, curling outward and inward. Emissive white-violet at the root, fading to the indigo sky. Flutter by vertex sway, 0.3 Hz. |
| **Loose threads** | 150 stretched-billboard particles drifting **toward** the tear (every motion leads to it), 3–20 m long, α 0.3 |
| **Violet halo** | 2–3 additive radial cards, 3–4 km across. Display #8A5CFF at the inner edge, falling to the fog colour. **Breathing: period 10 s (0.1 Hz), ±12%.** |
| **Light shafts** | **16 additive shaft cards**, 30–120 m wide, 1.5–3 km long, radiating from the tear down and out between the tentacles. #B79CFF at α 0.025–0.06, noise scroll 0.02 UV/s. **Depth-tested**, so near tentacles occlude them and far ones sit behind them: real parallax as the bus climbs. Soft fade 40 m. |

The cloud side makes: `Tear_Emission_2048x512`, `Tear_Fibres_1024` (atlas of 16 strands), `Shaft_Gradient_256x1024`, `Halo_512`.

### 6.2 Tentacle material ("生 / skin", the judge winner), refined per the AD notes
- **Albedo:** display 14–24 (#0E0F14–#18161E), with a faint blue-violet bias. Never pure black: the ACES toe would erase it.
- **Smoothness:** 0.70–0.88, with **longitudinal streak structure along V** (5–20 cm wide slime streaks at 0.90, drier bands at 0.72). This fakes the broken anisotropic wet highlights the AD asked for, inside an isotropic BRDF.
  - Remove any uniform lacquer: no area wider than 30 cm may have constant smoothness.
- **Normal:** annuli plus fine wrinkles, strength 0.6 at LOD0. Mipmaps flatten it at distance.
  - No Voronoi and no scale patterns (the lizard read).
- **Tip translucency:** transmission = (1 − B)² × tear-light × **#6A3CFF**, where B = normalised radius from vertex colour. The thin whips glow faintly violet like back-lit ears. Cheap, and it makes them flesh.
- **Rims** (custom term in `Lanbai/Tentacle`, not left to the probe):
  - moon side: **#9DB8FF**, pow(1 − N·V, 5) × saturate(0.3 − N·L_moon);
  - tear side: #B48CFF × proximity to the tear (1 at < 200 m, 0 at > 1.2 km).
  - Target: **every near and mid silhouette carries a continuous 1–3 px rim**, blue on the moon side and violet on the tear side.
- **Light balance:** moon to tear light on mid-ground tentacles **1 : 2** (1 stop). On the tentacles nearest the tear, 1 : 4. **Never 1 : 40.** That ratio is why the explore renders lost the cold blue.
- **Height fog** inside the shader: extra density exp(−(y − y_cloudsea)/60 m) × 0.5, so roots dissolve into the cloud sea.

### 6.3 Atmosphere and aerial perspective
- **Fog: Exp (not Exp2), density 0.0006**, enter **#2E384D** (display #1C2744):

| Distance | Fog |
|---|---|
| 100 m | 6% |
| 500 m | 26% |
| 1 km | 45% |
| 3 km | 83% |

  - The colossi at 2–4 km become fog-coloured silhouettes *darker than the halo behind them*. Exp gives the long, graded falloff; Exp2 is too abrupt.
- **Sky:** `Lanbai/Sky` night mode.
  - Zenith display **#0B1426** (enter #1D2737), horizon #1C2744.
  - Stars from the NASA cube at **gain 0.12**: only the bright ones survive under the moon. **Keep the Milky Way for 星海.**
- **Cloud sea:** `moon` cards and strips. Cards within 1.5 km of the tear's foot are tinted violet (#C9B8FF multiplier). Strips at 60–75% brightness (per the Clouds README) so they do not steal from the halo.
- **Near fly-bys:** 25 m tentacles sweep past the windows at 8–20 m. Give them Camera Fading 2–6 m so a body never fills the headset.

### 6.4 Value map, scene 4
| Element | Display |
|---|---|
| Tear core | 255 |
| Halo, inner | #8A5CFF |
| Sky zenith | #0B1426 |
| Near tentacle body | 14–24, with rims 180–240 |
| Far colossi | 30–45, in fog |
| Moonlit cloud sea | 110–140; violet near the tear |
| Cabin | tubes flickering (§3.2) |
| Bloom | intensity 1.4, threshold 1.0, diffusion 8 |

---

## 7. Scene 5: 投入 The plunge (3 s of silence)

- The tear fills the view: **0.5 s** at white-violet (post exposure +2 EV, bloom intensity 6).
- Then a cut to the void: display **#030409**. The cabin is barely visible from the flash's afterglow: `_Udon_CabinAmbient` #0A0C14 × 0.2, decaying to 0 over 2 s.
- **No particles, no stars.** A held breath.
- Then Sky I **dawns from the top of the view downward** over 2.5 s: skybox exposure ramp, top first, through a vertical mask in `Lanbai/Sky`.

---

## 8. Scene 6: 天空 I, dawn light

**Picture:** luminous and silent. Peach-gold at the horizon, pale sky above. The cloud plain far below has **cool lavender shadows, not brown**. Through gaps in the clouds, the sea glints. The intact, unlit cabin is a dark frame around all this light, with gold beams and dust.

- **HDRI** (implementer, Poly Haven *pure sky*, 8K or more). Criteria:
  - sun elevation 3–8°;
  - clear or with high thin cirrus or altocumulus lit gold (scale overhead; our cards supply everything below);
  - **no ground and no buildings** in the upper hemisphere;
  - sun unclipped (≥ 10⁴ : 1).
  - Candidates to check (names from memory; judge by the look): `qwantani_sunrise_puresky`, `kloofendal_48d_partly_cloudy_puresky`, the `belfast_*_puresky` family.
- **Normalise the skybox exposure:**
  - sky 45° up, facing away from the sun, display **#AFC4E0** (scene ≈ 0.4);
  - horizon under the sun #FFE2B8;
  - sun disc clipped.
  - **Scene offset −0.3 EV** (holds the cloud highlights).
- **Sun:** directional **#FFC57B**, aligned exactly with the HDRI sun (the implementer reads the brightest pixel).
  - Lit cloud tops display #F3D2B0; card shadows **#A9A3C8** (re-lit cards, §1.4).
- **Below the horizon:** `Lanbai/Sky` with `_Mirror` 0. The lower hemisphere is a haze gradient from the horizon colour to #6F8FA8 at the nadir.
  - Dawn `CloudFloor` 800–1500 m below, with 25% gaps showing the **sea** (the §9 sea shader, already present at −2000 m) with a gold glitter path.
- **Fog:** Exp 0.00012, enter #E5C4B9 (display #D9C9C2). About 30% at 3 km: aerial perspective on the far cloud pillars.
- **Scale cues:** Congestus cards (400 m) at 6–12 km as far pillars, 3–5 of them. Wisps pass the windows rarely (1 per 20 s): slow, silent.
- **Cabin:** lightmap 0, ambient #A9A3C8 × 0.5, beams #FFD9A8 at α 0.08, 300 dust motes, curtains back-lit pale blue (§3.5).
- **Poem:** dark ink (§14).

---

## 9. Scene 7: 海面 → 深海 Sea surface → deep sea (河伯)

### 9.1 The sea from above (falling toward it)
- **Calm dawn sea.** Wind 3–5 m/s, so **patches of glassy water and rippled water** alternate (cat's paws). This patchwork is the single strongest photoreal cue for a calm sea seen from altitude. It also makes the sea a mirror at the horizon and dark water underneath.
- **`Lanbai/Sea` ABOVE:**
  - F0 0.02 (Schlick);
  - reflection = `_Udon_ReflCube` (the dawn sky cube);
  - body colour display **#1E4C5A** (enter #30535D);
  - back-lit wave-crest scatter #2E8C8A × (sun behind the crest);
  - sun specular at smoothness 0.985 on the wave normals, with **Toksvig roughness from the normal-mip length** so the glitter path widens correctly with distance;
  - glitter display #F6D9A6.
- **Normals** (cloud side, FFT/JONSWAP, seamless):

| Map | Resolution | Tile | Scroll |
|---|---|---|---|
| `SeaN_Large` | 1024² | 64 m | 0.4 m/s, 20° |
| `SeaN_Small` | 1024² | 9 m | 0.9 m/s, −35° |
| `SeaMacro` (glassy ↔ rippled mask) | 1024² | 1.5 km | 0.05 m/s drift |

  - Glassy zones: normal ×0.15; rippled zones: ×1.0.
- **Mirrored cloud reflections:** once, at scene start, render a real-time reflection probe (`RenderProbe`, resolution 256) at the camera position mirrored below the sea plane. That captures the sky *and the cloud cards*, and it becomes `_Udon_ReflCube` for the sea. For kilometre-distant clouds this equals planar reflection at no per-frame cost.
  - ⚑ Verify `ReflectionProbe.RenderProbe` in Udon. Fallback: the sky cube only; clouds do not reflect.
- **Entry:**
  - 400 bubble particles over 1.2 s;
  - white water streaming up the windows for 0.8 s;
  - fog snaps to underwater;
  - `Lanbai/Sky` switches to the underwater gradient (the skybox is never fogged, so it must be replaced).

### 9.2 The sea from below
- **`Lanbai/Sea` BELOW, Snell's window:**
  - refract(view, N, 1/1.33); if total internal reflection, reflect and sample the water colour; otherwise sample the sky cube × (1 − F);
  - the result is a **bright disc of sky ~97° wide overhead**, its edge rippling and sparkling, the dark water mirrored beyond it;
  - near the rim the sky is compressed with a slight chromatic fringe (R/B refraction indices 1.331/1.337).
  - The "moving sky" from the previous build, made physically true.
- **Underwater god rays:** 24 additive shaft cards, 1–4 m wide, 20–40 m long, oriented along the refracted sun, animated streak texture, #9FE6E6 at α 0.04–0.08, fading out by 25 m depth.
- **Caustics** on the cabin and on the bus's exterior roof: §3.4.

### 9.3 The water column (fog carries it)
| Depth | Fog Exp density | Fog enter / (display) | Skybox gradient: up → down |
|---|---|---|---|
| 0–15 m | 0.040 | #3E8D95 (#2F9AA3) | #7FD0D0 → #0A3A52 |
| 15–60 m | 0.030 | #1C4657 (#0A3A52) | #1C6A7A → #03101A |
| Deep, the palace | **0.018** (clearer, darker) | #11232C (#03101A) | #06202C → #010407 |

- **Particles:**
  - **marine snow:** 1200 in a 25 m sphere, 0.8–2.5 cm, #2B4650 at α 0.3–0.6, sinking 1.5 cm/s. They **rise past the windows** as the bus sinks, which is the motion cue;
  - **bioluminescent trail** along the bus hull: 300/s, life 1.5–3 s, #39C8FF × 3 HDR, 1–3 cm with a soft halo;
  - **ambient sparks:** 200 random flashes in a 30 m radius, 0.2 s each.
- **Cabin:** flooded (dream logic). Curtains float, bubbles rise from the seat seams, the roof starts to erode (§3.7).

### 9.4 河伯's palace: how literally? **Literally, but seen the way the deep sea lets you see.**
Build the four things the poem names as real architecture, in **Han / Chu-period style**: heavy straight roofs, 斗拱 brackets, a pair of 阙 gate towers. It must not look like the Forbidden City (Ming/Qing is the theme-park cliché; Han is archaic and dreamlike, and 屈原 was a man of Chu).

Photoreal depth rule: **red is absorbed first in water.** Beyond about 6 m from a light source, vermilion reads black-grey-blue. So the palace is **dark water with islands of warm light**. The vermilion appears only where the bronze lamps burn, and that makes it feel sacred.

**"Lights on, nobody home" echoes the bus:** lamps burn, doors stand open, the hall glows, and no spirit is ever seen. 灵何为兮水中.

**Scale (震撼):**
- the complex is ≈ 220 m long;
- **main hall (朱宫)** 60 m wide, 30 m tall, on a stone terrace (台基) 6 m high;
- **紫贝阙** gate towers 40 m tall;
- **24–30 fish-scale houses** flank the approach.
- The bus sinks slowly past the front of the terrace, 20–40 m from the hall face, then over the terrace's edge (§9.5).

| Element | Material (albedo / smoothness / metallic / normal) | Notes |
|---|---|---|
| **朱宫** vermilion columns, beams, doors | cinnabar lacquer **#A3201E** / 0.80 / 0 / faint brush-stroke 0.1. Black lacquer ground **#141112** at worn edges. | **Chu lacquer detail:** black bands with vermilion 云纹 cloud scrolls on beams (1024² trim). **Silt** on every up-facing surface: world-normal-up × noise mask, 40–70% cover, #5E6259 / 0.10. |
| **龙堂** dragon halls | same lacquer + **gilt-bronze** fittings #C9A56A / 0.60 / 1. Dragon-head ridge ends (鸱吻) in dark bronze #3A332A / 0.5 / 1. Verdigris #3E7A68 / 0.3 / 0 in crevices. | Ridge silhouettes against the faint glow above are the "dragon" read. No literal dragon statues. |
| **鱼鳞屋** fish-scale houses | roofs clad in **overlapping fish-scale tiles** (30–40 cm, round-ended), **nacre**: base #CFCBC4 / 0.86 / 0 + **iridescence**, hue = f(N·V): #E7C9D5 face-on → #C3E3D5 → #B9C6EA at grazing. Walls: dark stone #3B3F3A. | In the dark they are black until a lamp or the bioluminescent trail passes: then they **glint in rolling pearl colours**. That glint echoes the fish school (below). |
| **紫贝阙** purple-shell gate towers | cladding of **cowrie shells** (8–12 cm, domed with the aperture slit), base **#5B2A4E**, dorsal spots #B89AB0, / **0.92** / 0 / domed normal 1.0 + POM 1.5 cm | Cowries are porcelain-glossy: they catch every lamp as a field of tiny highlights. 2048² tiling per 2 m. |
| Stone terrace, steps | #3B3F3A / 0.30 (0.10 under silt) / 0 | seagrass: 30 dark strands, 2–5 m, swaying 0.15 Hz |
| **Bronze lamps** (Han 长信宫灯-type, 1.2–2 m) along the approach and on the terrace | bronze #7A5A3A / 0.55 / 1, patina | **Flames burning under water** (dream logic). 8-frame flipbook emissive **#FFC46A × 5 HDR** with a halo card r 1.5 m: #FFC46A → #1E6F73 → 0, no fog. |

- **Lamp lighting** (baked, the palace is static): each lamp gets **two point lights**:
  1. **warm** #FFB74D, range 4 m;
  2. **teal** #1E6F73, range 12 m, 1.5 stops lower.

  Surfaces near a flame read gold-vermilion and fall to teal with distance: **the water eating the red**, physically motivated, zero run-time cost.
- **The open main-hall doors** spill warm light: interior emissive #FFB74D × 3, plus 3 additive cone cards from the doorways (α 0.06, 20 m long). Warm god rays in cold water, and nobody inside.
- **Fish school:** 1500 silver fish (GPU-instanced mesh particles, 12–20 cm, ≈ 60 tris each).
  - Back #2A3A44, flanks #B8C0C4, smoothness 0.85.
  - Circling the main hall in a slow torus (radius 35 m, 0.03 rev/s).
  - They glint as they turn through lamp light: the moving 鱼鳞.
- **Value map:**

| Element | Display |
|---|---|
| Water background | #03101A |
| Lamp halos, core | 255 |
| Lacquer within 3 m of a flame | ≈ **#B52A1E** |
| Lacquer at 8 m | 20–35, teal-grey |
| Nacre glints | 150–230 |
| Bioluminescence | #39C8FF |

- The cloud side makes all palace meshes (procedural bpy kit: columns, 斗拱 blocks, hip roofs, 阙 towers, terrace, lamps) and their four texture sets. 屈原's text is literal enough to build from.

### 9.5 The bottom of the sea is another sky (transition to scene 8)
- Past the terrace edge the water keeps going down, and it **begins to glow rose from below**. Fog colour shifts #03101A → #2A1E30 over 20 s.
- Below the bus: **the inverse Snell's window**. `Lanbai/Sea` BELOW is flipped: a plane *under* the bus, seen from inside the water looking down.
  - Inside the window: the **dusk sky**.
  - Outside it: total internal reflection **mirrors the dark water and the palace lamps**. The palace appears reflected in the floor of the sea.
  - This is the exact mirror image of scene 7's surface, the same shader inverted. 庄子's line becomes geometry.
- **Exit:** the bus falls *out* of the water, which streams off the windows upward (0.8 s). Fog snaps to dusk.

---

## 10. Scene 8: 天空 II, dusk (the mirror world; the key line)

**Picture:** a **perfectly mirror-symmetric world**. The dusk sky above and **the same sky below**, meeting at a horizon where the sun and its reflection merge into one blazing line. Above you, the underside of the sea you just fell from: a dark, rippling ceiling that reflects rose light at grazing angles and holds the palace lamps as faint gold points far inside. 其视下也，亦若是则已矣.

- **HDRI** (Poly Haven pure sky, 8K+). Criteria:
  - sun at 0–3°, or just set with strong afterglow;
  - **a visible rose belt of Venus** opposite the sun;
  - warm/cool contrast;
  - no ground.
  - Candidates to check: `qwantani_dusk_2_puresky`, `belfast_sunset_puresky`.
- **`Lanbai/Sky` with `_Mirror` = 1:** the lower hemisphere samples the HDRI at (x, |y|, z), then × 0.82 (−0.3 EV) and tinted ×(0.92, 0.95, 1.05), so the eye reads *mirror* rather than *copy*. Add a 1° soft blend band at the horizon so the sun and its reflection fuse.
- **Display targets:**

| Element | Display |
|---|---|
| Sun belt | #FFB070 |
| Rose band | #E7A0A0 |
| Violet mid-sky | #9C7FB8 |
| Zenith | #4B4A86 |
| Nadir (mirror) | #2A2B55 |

- **Sun:** directional #FFB153, intensity −0.5 stop relative to dawn.
- **Clouds:** dusk cards (re-lit, §1.4) placed **mirror-symmetrically**: every card above the horizon has a partner below it, flipped vertically, at 80% brightness. Only 6–10 pairs: sparse, monumental.
- **The sea ceiling:** `Lanbai/Sea` CEILING mode, at +300 m when the scene starts; the bus falls away from it at the scene's pace.
  - Directly overhead: dark water (#101828) with 20–30 gold lamp specks (the palace), fogged with distance.
  - At grazing: F → 1, reflecting the rose horizon.
  - It fades into the upper sky over ≈ 40 s: fog Exp 0.00025, enter #C4929A (display #C9A0A8).
- **Cabin:** ambient #9C7FB8 × 0.45; beams #FFB38A; fade 0.25 → 0.65; **curtains flying**, back-lit rose-lilac. The last of the cabin's colour.
- **Poem:** the 庄子 line is **mirrored in the horizon** (§14). The most important typographic moment of the world.

---

## 11. Scene 9: 天空 III / 星海 (starry night; the mirrors)

**Picture:** a moonless void where the Milky Way forms a **complete ring around you**, above and below; only possible with no ground. Colossal **polished bronze mirrors** rise from beneath, each reflecting the stars in warm gold, passing through the fading cabin faster and faster.

### 11.1 Stars
- **Milky Way glow:** NASA Deep Star Maps 16K EXR → **2048/face BC6H cube** (the glow is low-frequency, so 2048 is enough).
  - Orient it so the **galactic core sits 10–15° above the horizon, ahead and to the left** through the windscreen, with the band arcing overhead and continuing below.
  - Core display **#3A3542**, arms #232A3A, dark sky **#04050A** (enter #13151C).
  - **Scene offset +0.3 EV.**
- **Crisp stars as geometry, not texture** (texture stars blur and shimmer in VR):
  - The cloud side writes `extract_stars.py`, which the implementer runs on the 16K map: threshold local maxima → 5000 stars (to about mag 6.5) with direction, flux and colour sampled from the map.
  - It outputs a point mesh rendered as camera-facing quads: size 0.03°–0.12° by flux, colour from the map, HDR flux × 4 for the brightest 50 (they bloom).
  - **No twinkling**: stillness.
- **The lower hemisphere is the same star field**, not mirrored: this is space, not reflection. The mirroring belongs to the mirrors.

### 11.2 The 星海 mirrors
- **What they are:** ancient-style **speculum-bronze mirrors** (铜镜), disc-shaped, polished face **up**, rising from below.
  - Han bronze mirrors were diagrams of the cosmos, which fits 天问's question "上下未形，何由考之".
  - Keep the decoration restrained; the grandeur comes from size and light.
- **Sizes:** the first mirrors Ø 40–60 m, growing to **Ø 300 m** for the last. Rhythm per the story lens.

| Part | Albedo (metal) | Smoothness | Metallic | Detail |
|---|---|---|---|---|
| **Mirror face** | **#D9C49A** (warm silver-gold) | **0.94** | 1 | faint circular polishing swirls in the smoothness map (±0.02). **Convex by 1.5%**: the reflection normal tilts up to 6° at the rim, so the reflected Milky Way curves like a fisheye |
| Rim band (2% of Ø) | #B8925A | 0.75 | 1 | – |
| **Back** (seen from below as it rises past) | verdigris patina #4F7A66 | 0.35 | 0 | raised concentric rings, central boss (钮), a subtle TLV pattern at normal strength 0.6. Silhouette dark against the stars (display #1E3B34 at best). |

- **Reflection:** `_Udon_ReflCube` = the star cube.
  - Face display: **#C9A76A**-tinted Milky Way, mid 60–120, bright reflected stars 200+.
  - The warm reflection against the cold sky is the scene's colour contrast.
- **Passing through the bus:** where the mirror plane crosses the cabin, a **thin horizontal line of light** sweeps upward (the mirror's cross-section; an emissive slice mask in `Lanbai/Cabin`, 2 cm, #FFFFFF × 4). Add a post-exposure flash of +0.5 EV for 0.2 s.
- **The last mirror:** it fills the whole lower hemisphere, then its face reaches the player. Post exposure ramps +0 → **+5 EV** over 1.5 s, and bloom 1 → 20 → the white (§12).
- **Cabin:** fade 0.65 → 1.0; stanchions last, the player's seat last of all. Ambient #232A3A × 0.3.

---

## 12. Scene 10: 白光 White light

- **The white is 藍白**, the palest indigo, the name of the world. **Not #FFFFFF.**
- **Display target: #EBF6F7 on desktop; #D8E3E4 in VR** (a full-field white at 247 in a headset is fatiguing, and 92% reads just as luminous after 2 s of adaptation).
  - Udon picks the value from `IsUserInVR()`.
- **Implementation:** at the peak of the ramp, fade in an inside-out unlit sphere around the head (r 1.5 m, ZTest Always, queue Overlay). It renders *before* PPv2, so its entered colour must compensate for ACES:
  - start at enter **#B5F5FF × 3.1** (desktop) or #DBFBFF × 1.08 (VR);
  - tune until a screenshot samples the target ±4 per channel.
- **Life inside the white:** ±2% luminance breathing at 0.1 Hz. No shapes.
- **Match-cut out of the white** (my strong recommendation to the story lens): the white does not cut to the next scene, it **contracts into lamps**.
  - Into the false awakening: the white shrinks into the sodium lamps (fade the sphere with a radial mask centred on each lamp's screen position).
  - Into the real awakening: it shrinks into the single 藍白 tube over the stop.
  - Every white becomes a light in the next world.

---

## 13. Scenes 11–12: 假醒 False awakening / 醒 Awakening, and the credits board

### 13.1 Scene 11: 假醒 The false-awakening road
**Picture:** everything normal at first glance: a dry night road, sodium lamps sliding past, the cabin whole and lit, the radio hissing. Then you look up. **A dark sea hangs over the world at 80 m**, and the lamp poles hang *down* out of it. Their amber light glitters, moving, on the underside of the waves.

**Inversions against scenes 1–2:**
- the rain is gone; the **road is dry** (smoothness 0.2, no streaks). **The reflections have moved from the road below to the sea above.**
- The glass is dry and slightly too clean.
- The tubes are steady (no flicker).

**Details:**
- **Lamps:** the same sodium cobra heads at 7 m above the road, facing down. Their **poles rise 73 m and pierce the sea surface**; the tops vanish into the water with a slight fog.
  - Spacing 35 m, the same rhythm as scene 2, so the cabin sweep (§3.4) returns identically.
- **The sea overhead:** `Lanbai/Sea` CEILING mode, facing down.
  - Overhead: dark water display **#05080C** (enter #151A1E).
  - Slow swell: 3 Gerstner waves, wavelengths 60/37/23 m, amplitudes 0.6/0.35/0.15 m, 0.08 Hz.
  - **Glitter from the 4 nearest lamps** through `_Udon_Lamp0..3` (GGX, smoothness 0.97): moving **#FFB85A** streaks that slide as the lamps pass.
  - Easter egg: 6–10 faint gold specks deep inside the water. The palace, very far up.
- **Road:** dry asphalt; lamp pools on it display ≈ #3B3029.
- **Fog:** Exp2 0.0055, enter #212326.
- **Cabin:** everything restored (§3.7); radio dial flickering with static.

### 13.2 Scene 12: 醒 The real awakening at the stop
It is the same place as scene 1, **after the rain**:
- **Puddles perfectly still**, true mirrors: ripple strength 0, rain systems off. The tube and the sign mirror crisp in them.
- **Wetness 0.85** (drying at the crowns of the road: smoothness 0.55 there).
- **Drips** continue from the lamp arm and the sign rim: one every 2–5 s, each with a single ripple ring.
- **Mist:** the field mist cards rise 0.5 m over the scene; opacity ×1.3.
- **Moths:** 14 at the tube.
- **Fireflies:** **46** (40 over the flooded field at 0.3–2 m height, 6 near the stop).
  - Colour **#C8FF3C**; flash is a 0.35 s pulse, dark 2–6 s (random); core sprite 3 cm, emissive ×4, plus a 25 cm halo at α 0.25.
  - **Mirrored in the flooded field** (the duplicate system, §2.8).
- **The first blue before dawn** (proposed to the story lens as the final image):
  - The overcast has broken into 2–3 gaps where a few stars show.
  - On the horizon **opposite** the town glow, a very faint band of pale blue: display ≈ **#1B2229** against sky #08090C, 4° tall.
  - The bus never moved, but the night has ended, and the last colour on screen is 藍白 again.
- **The dry rectangle under the bus is still there.**

### 13.3 The credits board
- **What it is:** a **roadside notice case** on two posts, 3–4 m from the sign.

| Part | Spec |
|---|---|
| Case | 900 × 1200 mm, steel painted indigo **#2B4257** (chalky, chipped to rust at the corners, smoothness 0.35) |
| Glass front | uses `Lanbai/BusGlass` with the droplet state (drops in scene 1, fewer in scene 12) |
| Paper sheets inside | **#E8E3D3**, smoothness 0.1, slight humidity waviness (a normal map of low-frequency cockles, strength 0.4), 4 brass pushpins, a faint water stain on one corner |
| Internal light | a 30 cm tube at the top, **off in scene 1** (you can just see paper in the dark) and **on in scene 12** (#CFEAF0, the case interior at display 170–190). The credits "appear" by being lit. |
| Ink | printed, **#23272E** (never pure black) |
| Coleridge easter egg | a **small slip torn from an old book**, pinned at the lower right, slightly yellowed (#E4D9BE), set as 1816 letterpress (§14): the lines from the preface to "Kubla Khan" about the person from Porlock and the vanished rest of the poem |

- **Readability in VR at 1.2 m:**
  - body text cap height **≥ 11 mm** (0.5°);
  - names 14 mm;
  - title 40 mm.
- **Typographic system:** see §14.4.

---

## 14. Typography

### 14.1 Families (all SIL OFL 1.1)
| Use | Family | Why |
|---|---|---|
| **zh poems** | **Source Han Serif SC** (思源宋体) **Regular**; **Medium** for secondary lines | A classical Song/Ming for classical poetry, with cinematic title-card gravity. Regular (not Light) because hairlines under 2 px shimmer in VR at poem distances. |
| **ja poems** (書き下し) | **Source Han Serif JP** (源ノ明朝) Regular / Medium | The same design DNA as zh, correct JP glyph forms and kana |
| **en / de poems** | **EB Garamond** Regular; **Italic** for German | A literary Garamond with sturdy strokes (Cormorant's hairlines alias in VR), full German support (ß, umlauts) |
| Sign, destination blind | **Source Han Sans SC/JP Heavy** + **Barlow Semi Condensed SemiBold** | Signage gothic; Barlow descends from road signs |
| Credits | Source Han Serif + EB Garamond; heading in Barlow Semi Condensed (echoing the sign) | one voice with the poems |
| Coleridge slip | **IM FELL English** | the irregular impression of real letterpress; period-right texture |

### 14.2 TextMeshPro setup
- **Font assets:** static, containing exactly the needed characters. The cloud side generates the character lists from the poem and credit texts.
  - CJK: SDF32, sampling 90 pt, padding 10, **atlas 2048²**. Latin: 1024².
- **Shader:** `TextMeshPro/Distance Field` (not Mobile).
  - **Face Dilate 0.05** (thickens hairlines for VR).
  - Glow in the scene's key tint: offset 0, inner 0.1, outer 0.35, power 0.6, α 0.35.
  - Underlay only where noted.
- **Size by visual angle** (not metres):
  - main line **character height 2.4°**, which is 1.68 m at 40 m (h = 0.0419 × distance);
  - secondary lines 1.3°;
  - distance 25–60 m, in world space, depth-tested (tentacles and clouds may pass in front), **fog-exempt**.
- **Tracking:** CJK +0.10 em, line spacing 1.6; Latin tracking 0, line spacing 1.35.
- **Line breaks:** break at the caesura (，), one line per hemistich. Drop the final 。 on display lines.
- **Reveal (a focus pull, never a pop):** animate TMP `_OutlineSoftness` from 0.9 to 0, and alpha from 0 to 1, over 2.5 s (ease-out).
  - Exit: drift up 0.2° while fading over 3 s.
  - Stars scene exception: characters ignite one by one, 120 ms stagger, each with a 0.3 s twinkle.

### 14.3 Poem colour per scene (display targets)
| Scene / poem | Text | Glow / treatment |
|---|---|---|
| 3 李白 我欲因之梦吴越 | #F2EEE6 warm white | warm glow |
| 4 Rilke; Urlicht lines (de italic + translation) | #E8E4F4 | violet glow |
| 6 **我从天空坠入深海** | **dark ink #1F2A3A** on the luminous dawn sky, no glow | "written in ink on the dawn". Light text would vanish on a sky at display 170–220. |
| 7 河伯 | #DDF3F6 | teal glow |
| 8 **庄子 天之苍苍** | #FBE8E4 | **centred on the horizon and mirrored below it**: an upside-down reflection at α 0.5, softness 0.3. The typography does what the line says. |
| 9 天问 | #E9EEF8 | per-character ignition |
| 11 庄子 胡蝶 | #FFE3B0 | small and quiet; low contrast |
| 12 李白 惟觉时 + Keats (EB Garamond Italic, 60% size) | #E8F6F8 (藍白) | – |

### 14.4 Credits typographic system
- **Paper:** A-series proportions, margins 8% of the sheet.
- **Heading:** "LANBAI" in Barlow Semi Condensed SemiBold, tracking +0.3 em, echoing the sign. Beneath it, **蓝白** in Source Han Serif SC Medium.
- **Structure:** role (EB Garamond Italic, 11 mm cap) → name in the original language (EB Garamond Regular or Source Han Serif, 14 mm).
- **Layout:** left-aligned on a single column, generous 1.6 line spacing. It is laid out like a timetable, but without times.

---

## 15. Cloud-side production list (what we make next, in priority order)

1. **Sign kit:** zh/en and ja faces, rear face, timetable plate, pole streaks (1024² PBR sets). Starts from `work/sign_mock.py` with real OFL fonts, which the implementer drops into the repo or we fetch if pip allows.
2. **Rain kit:** `RainRipple_512`, droplet normal 1024², running-drop flow 1024², streak atlas, splash atlas, `Stop_WetMask` 2048×512.
3. **Cloud cards v2:** scene-referred re-export (−1 EV, untonemapped), **re-lit with the chosen HDRIs**, new **`citybelow`** preset, **`CloudFloor_{moon,dawn,dusk}`** top-down tiling layers.
4. **Tear kit:** emission ribbon, 16-strand fibre atlas, shaft and halo gradients; tentacle material refinements (§6.2) in `Lanbai/Tentacle`.
5. **Sea kit:** FFT normals ×2, glassy/rippled macro mask, caustic flipbook, god-ray streak texture; draft `Lanbai/Sea` (ABOVE / BELOW / CEILING).
6. **Sky:** `Sky_Overcast_Night.hdr`, draft `Lanbai/Sky` (mirror, night gradient, moon), `extract_stars.py`.
7. **City lights:** tile + macro.
8. **Palace kit** (bpy): meshes plus lacquer, scale, cowrie, stone and bronze sets; lamp flipbook.
9. **Bronze mirrors:** mesh with LODs, face and back sets.
10. **Window cookie** (needs the bus side elevation from the implementer); cabin shader drafts (`Lanbai/Cabin`, `ThinCloth`, `BusGlass`).
11. **TMP character lists** for every font asset.

## 16. Flags: where real screenshots are needed, and the risks
- ⚑ **Every value map** must be checked against screenshots of the calibration rig (§1.10) in each scene. My ACES numbers come from the Hill fit, not PPv2's exact curve (expect ±5–10 display levels).
- ⚑ **Udon API exposure to verify:** `VRCShader.SetGlobalTexture`/`Vector`, `ReflectionProbe.RenderProbe`, `AudioSource.GetOutputData`, `RenderSettings.*` fog. Each has a fallback above.
- ⚑ The **window cookie** and the beam meshes need the real window layout of the rebuilt minibus.
- ⚑ The **HDRI picks** are criteria plus remembered names. The implementer should send us thumbnails (and the 1024×512 downsamples for re-lighting the cards).
- ⚑ **Cabin fade and VR comfort:** keep the floor under the player's seat until scene 9. Test with a seated VR user before shipping.
- ⚑ **Changes to the previous plan** that the synthesizer must surface to the user:
  - no shelter;
  - the stop lamp is a 藍白 tube, not a warm lamp;
  - cloud cards re-exported scene-referred;
  - the tear as torn indigo silk;
  - the palace built in Han/Chu style, lit only by its own lamps;
  - bronze mirrors;
  - the mirrored dusk skybox.
- **Performance watch:**
  - GrabPass for the drops (one per frame);
  - fish-school instancing;
  - overdraw of halo and shaft cards at the gate (≤ 4 layers per pixel);
  - the 5000-star mesh (one draw call).
  - Everything else is baked or unlit.
