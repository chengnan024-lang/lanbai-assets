# 蓝白 / Lanbai: VR + Unity feasibility, performance and comfort (lens: tech)

Role: feasibility and comfort lead. For every scene this file says how to build the look cheaply and robustly in
**Unity 2022.3 Built-in RP + PPv2 + VRChat SDK Worlds + UdonSharp**, what it costs at **PC VR 90 Hz**, and what keeps a
seated rider **safe and comfortable** (photosensitivity, luminance ramps, vection, stereo, text). Where this file
disagrees with `lens_cine.md` or `lens_lookdev.md`, section 9 lists the conflict and my resolution for the
synthesizer. I do not re-specify colours or materials: those belong to the other lenses. I give the limits they must
fit inside, and the mechanism that renders them.

Companion files (all in `art/lens_tech/`):

| file | what it is |
|---|---|
| `flashcheck.py` | photosensitivity + luminance-ramp checker. Run it on desktop captures of the risky passages (section 3.1) |
| `synth_tests.py` | synthetic seat-view sequences that test the specs of all three lenses with `flashcheck.py` |
| `flicker_schedule.py` → `out/FlickerTable.cs`, `out/flicker_schedule.json` | the scene-4 tube flicker, precomputed, safe by construction, as UdonSharp arrays |
| `out/ramps_compare.png` | the three big brightenings: sibling specs vs the ramp law |
| `out/check_*.png`, `out/selftest_reports.json` | checker output for each synthetic case |
| `shaders/LanbaiVR.cginc` | shared helpers: stereo macros, specular AA, minimum-width inflation, stereo-safe dither, inverse Neutral, edge-on and near-eye fades |
| `shaders/Lanbai_Overlay.shader` | the fade sphere (plunge black, the 藍白 white, spawn fade) |
| `shaders/Lanbai_PointSprites.shader` | stars, town lights, the sea of lights, palace specks: never sub-pixel, never shimmering |

All shaders were **written without a Unity compiler**. The implementer compiles them and checks them in a headset.

---

## 0. The twelve decisions (read these if you read nothing else)

1. **The bus never moves.** The bus, the player's station and the colliders stay at the world origin for all 20
   minutes. The world moves past the bus. The story says so, and it is also the most robust build: no floating-point
   jitter, no station judder, no player falling off a moving vehicle, and lightmaps, probes and colliders on the bus
   stay valid. (§2.1)
2. **No `VRCMirrorReflection` anywhere in the ride.** Four cheaper tools give every mirror in this world: a cube
   lookup for content at infinity, mirrored duplicates behind a stencil for still water, analytic GGX lamps for wet
   and rippled surfaces, and box-projected baked probes for near gloss. (§2.6)
3. **One skybox material, `Lanbai/Sky`, for the whole ride**: two cubemap slots with a directional blend mask, a
   procedural night, a mirror mode and a sun clamp. Udon animates its properties. `RenderSettings.skybox` is never
   swapped. (§2.4)
4. **No light probes in the world.** In Built-in, objects outside a probe hull extrapolate from the nearest
   tetrahedron, so probes baked at the rainy stop would light the player's hands at dawn 3 km up. Ambient is
   Trilight, set per scene by Udon. The cabin is lightmapped and gets the sky fill through its own shader. (§1, §2.5)
5. **Per-scene baked reflection cubes**, children of the static bus, switched by Udon, plus the global
   `_Udon_ReflCube` for hero shaders. They are baked in the editor, not rendered at runtime. (§2.6)
6. **Fog: Exponential only**, enabled in the scene at build time, "off" means density 0, and the other fog variants
   are stripped. (§2.5)
7. **Tonemapper: Neutral** (I vote with `lens_cine`). One tonemapper everywhere, because PPv2 cannot blend it. The
   lifted Neutral black also protects OLED headsets from black smear. (§9)
8. **The grade is 14 parametric PPv2 profiles crossfaded by volume weight** from Udon. There are no external LUTs,
   no auto exposure, and no screen-locked lens effects in VR. (§2.3)
9. **Every point of light is geometry** (stars, town lights, the sea of lights, palace specks): a Gaussian sprite
   never narrower than 1.4 px FWHM. A texel never stands in for a light point. (§3.6)
10. **Photosensitivity: at most 2 flashes in any second, anywhere** (WCAG 2.3.1 allows 3; VR fills the field, so we
    keep a margin). The tube flicker plays from a precomputed table that passes this by construction. The only
    authored flash is the tear entry, capped at +1.5 EV over 0.4 s. (§3.1)
11. **The ramp law: full-field brightening at most 1 EV/s** (at most 0.5 EV in any 0.25 s, at most 1.8 EV in any 2 s),
    measured above a mesopic floor. Ramps are exponential in luminance, never linear in alpha. The VR white is
    `#D7E3E8`, not `#E8F1F5`. (§3.2, §3.3)
12. **Comfort geometry:** the horizon never tilts, yaw stays at most 3°/s, speed changes take at least 4 s, a rest
    frame (seat, floor patch, invisible colliders) always exists, nothing comes within 0.3 m of the eyes, and poems
    are world-locked at a chosen angle and distance. (§3.4, §3.7)

---

## 1. Platform facts and the traps they set

| fact (VRChat PC, Unity 2022.3 Built-in) | consequence | what to do |
|---|---|---|
| VR renders with **Single Pass Stereo Instanced** (VRChat moved PC to SPS-I with the Unity 2022 migration; confirm in the current VRChat docs, and write for it either way) | a hand-written vert/frag shader without the stereo macros draws in **one eye only** | every custom shader uses the macros listed at the top of `LanbaiVR.cginc`. Surface shaders are already safe. **Test in a headset**: ClientSim is mono |
| Forward rendering, MSAA chosen by the player (1-8×), HDR camera | no deferred effects (no SSR, no deferred decals). MSAA does not fix shading aliasing | specular AA in every glossy custom shader; alpha-to-coverage for foliage; no TAA |
| **The player owns the quality settings**: pixel light count, shadows (on/off, distance, cascades), LOD bias, soft particles, MSAA | the same world looks different on "Low" | critical lights `Render Mode = Important`. Fill lights `Not Important` (they become cheap SH, §2.5). LOD transitions hidden in fog. Every scene must still read with shadows off |
| `_CameraDepthTexture` exists only when a **realtime directional light with shadows** is active | soft particles and depth-faded cards break when no such light exists | the world-key directional stays enabled with shadows in **every** scene, intensity near 0 where the scene has no key. Custom opaque shaders need a ShadowCaster pass, or they are missing from the depth texture |
| **Light probes extrapolate** outside their hull | probes baked at the stop would light the bus and avatars in every sky scene | **bake no light probes.** Trilight ambient from Udon lights avatars and dynamic objects (`RenderSettings.ambientSkyColor / EquatorColor / GroundColor`) |
| Changing `RenderSettings.skybox` does not update ambient or the default reflection | a swapped sky leaves stale reflections | one skybox material animated by properties (§2.4); reflections from per-scene baked cubes (§2.6) |
| A renderer that is Batching Static cannot move. A lightmapped renderer **can** move and keeps its lightmap | moving scenery cannot be statically batched | moving roots are `Contribute GI` and `Reflection Probe Static` only. Merge meshes offline (the cloud side ships merged kits) |
| float precision: 1 ULP = 0.12 mm at 1 km, 0.49 mm at 4 km, 1.95 mm at 16 km | a cabin 0.5 m from the eye at 16 km from the origin shimmers by about 0.2° | the bus stays at the origin (§2.1). Only far scenery lives beyond ±2 km |
| Fog variants are stripped at build time by the scene's fog setting | fog switched on at runtime draws **no fog at all** | Project Settings → Graphics → Shader stripping → Fog modes = **Custom, Exponential only**. Scene fog = on, Exponential. Every custom shader has `#pragma multi_compile_fog` |
| Udon is slow (roughly 100× C#) | per-frame loops over hundreds of objects blow the CPU budget | one Director `Update` of at most 0.4 ms. No per-object Udon. Sway, flicker shimmer, twinkle and ripples all live in shaders |
| Udon cannot edit PPv2 profile settings at runtime | parameters cannot be animated directly | profiles are baked assets. Udon sets only `PostProcessVolume.weight` (fallback if that is not exposed in your SDK: an Animator per volume) |
| Udon APIs this design relies on | `PostProcessVolume.weight`, `RenderSettings.fog*` and `ambient*`, `Material.Set*`, `VRCShader.PropertyToID` / `SetGlobal*` (names must start with `_Udon`), `Light.*`, `GameObject.SetActive`, `Transform`, `AnimationCurve.Evaluate`, `Networking.LocalPlayer.IsUserInVR()`, `GetTrackingData` | **not relied on**: `ReflectionProbe.RenderProbe`, `AudioSource.GetOutputData`, `DynamicGI.UpdateEnvironment` (all unverified; everything below works without them) |
| Activating a big hierarchy or first-rendering a shader variant hitches for 10-200 ms | a hitch in VR means dropped frames and reprojection judder | switch scene roots **only under cover** (black, white, whiteout, bubble burst). **Warm up all shaders at spawn** behind the 3 s fade-from-black: activate every root in front of the camera for 2 frames, then deactivate |
| 20 minutes of Mahler | as "Decompress On Load" that is 211 MB of RAM | Load Type **Streaming**, Vorbis quality 0.5 (≈ 20 MB) |
| Texture mip streaming | inactive roots get their mips dropped, then the hero textures of the next scene pop in | **Streaming Mipmaps off** everywhere. The world fits in memory (§5.4) |
| Camera clip | the colossi and the 4 km cloud ring must not clip. Depth resolution at 3 km with near 0.05 m is about 11 m | reference camera near **0.05 m**, far **12 000 m**. Nothing intersects anything else beyond 1 km except through soft fades |

---

## 2. Architecture

### 2.1 The static bus and the moving world (the treadmill)

```
World origin (0,0,0) = the bus floor centre. Nothing below ever moves:
  Bus              cabin, exterior, glass, VRCStation(s), colliders (floor, walls, door), lights attached to the bus
  ├─ ProbeSet      one baked ReflectionProbe per scene (children, only one active)        §2.6
  ├─ FadeSphere    Lanbai/Overlay, radius 4 m, centred on the seat eye point               §3.2
  └─ PoemAnchor    yaw-only pivot at the seat eye point; poem text as its child           §3.7
Scene roots (one per world), the ONLY things that move, translated by the Director:
  R_Stop (1, 2 departure, 12)   R_Road (2, 3 rise; the dry variant in 11)   R_Night (3 break-out, 4)
  R_Gate (4)   R_Dawn (6)   R_Sea (7)   R_Dusk (8, 8b)   R_Stars (8b, 9)   R_False (11 extras)
Camera-centred layers (infinite): sky, star sprites, moon, sun, horizon cloud ring (vertical parallax 0.3, horizontal 0)
```

- **Motion is translation only.** The Director holds a virtual bus path P(t) (position, never rotation except gentle
  yaw on the night road) and sets each active root to `root.position = -P(t) + rootOffset`. The rotation of the bus
  relative to the world is expressed by rotating the active root about the origin. The limits are in §3.4.
- **Road treadmill (2, 11):** 8 modules × 60 m (480 m) with lightmaps baked in place. Variants: with sodium lamp,
  without, village. When a module passes −120 m, it jumps ahead by 480 m. Each module's streetlight pool is baked
  into its own asphalt, so it travels with the module and stays correct.
- **Falling (6-9):** the root rises past the bus. The sky and sun never move. Only the near world moves, so the
  dominant surround stays earth-fixed (the best vection mitigation there is, §3.4).
- **Re-centring is never needed** because the bus never leaves the origin. If the current build already moves the
  bus, keep |bus| < 2 km at all times, and re-centre (bus and active root by the same offset, same frame) only
  under cover.
- **Standing up is safe.** The bus colliders (floor, walls, closed door after departure) exist in every scene, even
  when the cabin has visually dissolved. If the local player leaves the bus box (checked by the Director at 2 Hz),
  teleport them back into their seat under a 0.5 s dip of the fade sphere.

### 2.2 The Director (one UdonSharp behaviour, one clock)

- **Clock** = the existing timeline time (the sync logic stays unchanged). The Director reads it and never keeps its
  own clock, so seeking and restarting just work. Every curve is a function of timeline time, not of `deltaTime`.
- **Per frame it sets at most:** 3 volume weights, the overlay colour, fog colour and density, 3 ambient colours,
  about 6 sky material floats, about 12 `_Udon*` globals, the world-key light (intensity and colour; rotation only
  under cover) and 1-3 root positions. That is about 40 extern calls, roughly 0.1 ms. Cache the last value and skip
  unchanged sets.
- **Curves** are `AnimationCurve` fields edited in the inspector, keyed in timeline seconds. Keys come from the cue
  table (`lens_cine` §9 asks the build for the cue times; bind to cues, not to minutes).
- **Root activation** happens only at the cover moments listed per scene (§4). At most 2 scene roots are active
  at any time (outgoing plus incoming during a crossfade).
- **Auto-lite:** during scene 1 (static and quiet), the Director measures frame time for 10 s. If it sustains more
  than 1.25× the headset frame interval (for example it keeps falling to 45 fps reprojection), it sets
  `lite = true`: rain density ×0.5, gate shafts 12 → 6, halos 3 → 2, dust ×0.5, fish 1500 → 700, far tentacles to
  LOD2. The credits board carries a manual toggle too (text is allowed there).

Code sketches for the three Director parts that are easy to get wrong (grade crossfade, EV ramp, flicker playback)
are in Appendix A.

### 2.3 The grade: 14 profiles, weights, and why there are no LUT files

**What "a LUT per scene" means in PPv2 HDR mode.** Every profile (`S1`…`S12` and the helpers in
`lens_cine/grades.json`) *is* a LUT: PPv2 bakes the active, weight-blended parameter set into an internal 32³ LUT
every frame. Blending two profiles by weight therefore blends two LUTs, but in **parameter space**. White balance
goes through the intermediate temperatures, and exposure moves linearly in EV. That looks like a real change of light,
not a slide dissolve. **Do not ship `.cube` or strip LUTs:**
- HDR mode accepts external LUTs only in *External* mode. That replaces the tonemapper and every grading control,
  wants ACES-log input, and can only be authored in an ACES-aware grading tool;
- LDR mode's lookup texture clamps at 1.0 before the LUT, so every sky, sun, tear and bloom highlight would clip.

**Volume rules** (agreeing with `lens_cine` §3.3, plus four additions):
1. One global volume per profile. Priority = timeline order. The crossfade raises the **incoming (higher
   priority)** volume from 0 to 1 while the outgoing one stays at 1, then sets the outgoing one to 0. Never fade one
   down while the other fades up: PPv2 would blend through its defaults and flash an ungraded frame.
2. **Curve by content.** When the transition is mostly an exposure change, the weight is **linear in time** (PPv2
   blends `postExposure` linearly in EV, so linear weight = constant EV/s = the ramp law). When it is mostly a
   colour change, use smoothstep. Visible colour crossfades take at least 8 s. Hidden ones may be anything.
3. **Helpers** (`FLASH_TEAR`, `WHITE_RAMP`, `MIRROR_PULSE`, priority 90-100) override *only* the parameters they
   change. Every scene profile overrides the *full* set (as `lens_cine` says).
4. **Bloom in every profile: `fastMode = true`** (it saves about 30% of the bloom cost at VR resolution. It is a
   bool, so it must be identical in all profiles or it snaps) and **`clamp = 24`**, not 65472. The Poly Haven HDRI
   suns reach linear 10⁴-10⁵, and an unclamped sun floods the whole view with bloom in a headset.
5. **Never in any profile:** Auto Exposure (head turns toward the tear would pump the image), Motion Blur, Depth of
   Field, Chromatic Aberration, Lens Distortion, Ambient Occlusion, SSR, bloom dirt, anamorphic ratio ≠ 0. In VR also
   no Vignette and no Grain: `lens_cine`'s desktop-only `LENS_ARCHIVE` and `LENS_CLEAN` volumes are deactivated when
   `IsUserInVR()` is true. That is correct: a screen-locked pattern sits on the lens in stereo.
6. **PostProcessLayer:** Anti-aliasing None (MSAA from the client), Stop NaN on, dithering on, a user layer named
   `PostProcessing` holding only volumes.

**Deliverable (cloud side, next):** `LanbaiGradeBuilder.cs`, an editor script that reads `grades.json` and writes the
profile assets, the volumes with priorities and the grade test card. It changes no project settings.

### 2.4 Sky system: `Lanbai/Sky`

One skybox material for the whole ride. Its properties are driven by Udon:

| property | role |
|---|---|
| `_CubeA`, `_CubeB`, `_ExpA`, `_ExpB`, `_RotA`, `_RotB` | two HDR cubemaps (dawn HDRI, dusk HDRI, star-glow cube, underwater gradient cube), exposure in EV, yaw rotation |
| `_Blend`, `_BlendMask` | crossfade 0..1 plus a **directional mask**, so a transition moves across the sky the way light does: at the blue hour the anti-sun side and the zenith darken first and the sun side last. Stars appear in the darkest part first. This turns a dissolve into dusk |
| `_Procedural` + zenith / horizon / nadir colours + band | the night skies of 1, 2, 3, 4, 11 and 12 and the underwater gradient (7). No texture needed |
| `_Mirror` | lower hemisphere = upper mirrored at (x, \|y\|, z), with gain and tint (8), plus a 1° soft seam |
| `_SkyClamp` | clamps the HDRI at linear 16 before output. The **sun disc is procedural** (size and colour from `lens_cine`), so the HDRI sun never produces a 10⁵ texel that sparkles in reflections |
| moon | procedural quad in the shader, LRO texture 1024², 1.1-1.2° |
| dither | `LanbaiDitherLinear(color, dir)`: direction-anchored, identical in both eyes, 1.5 LSB |

- **HDRI import:** Texture Shape Cube, Mapping Latitude-Longitude, **2048 per face**, BC6H, sRGB off, mips on,
  Fixup Edge Seams on. That is about 32 MB each with mips.
- **Align the sun directional light to the HDRI sun** (the implementer reads the brightest pixel of the equirect:
  azimuth = u·360° − 180° + `_RotA`, elevation = 90° − v·180°). Rotate the HDRI only under cover.
- **Star glow cube:** the NASA map with the stars removed (median filter, radius 3 px, in `extract_stars.py`),
  **1024 per face** is enough for the glow (8 MB). The stars themselves are sprites (§3.6).

### 2.5 Lighting system (per scene summary in §4 and §5.2)

- **Baked** (Progressive GPU, Lighting mode **Baked Indirect**, no Enlighten): the stop (1, 12), the road modules
  (2, 11), the palace (7) and the cabin with its tubes on (lightmap scaled at runtime by `_Udon_CabinLightmap`, as
  `lens_lookdev` §3.4 designed). Lightmap texels: cabin 40/m with **directional** lightmaps (1024²); stop road 8/m
  and fields 1/m, **non-directional**; road modules 6/m; palace 4/m (2 × 2048²).
- **Realtime, at most 1 shadowed + 3 unshadowed pixel lights touch the bus at any time:**
  - world key: one directional (moon, sun, tear side or near zero), **Important, soft shadows**, strength 0.8-1.
    Culling mask: Bus, Tentacles, Player, PlayerLocal, and the near shadow-casting scenery;
  - the sweep spot (2, 11): Important, no shadows, window cookie, culling mask Bus;
  - one secondary directional in the gate (the tear light): Important, no shadows;
  - every fill light is **Not Important**. Unity then folds it into the per-object SH for free, which is exactly what
    a soft fill (cloud-sea bounce, sea glow) should be.
- **Avatars at the stop:** the baked area light over the stop does not light dynamic objects, so add one realtime spot
  on the lamp, **culling mask Player + PlayerLocal only**, no shadows, 5600 K, matched to the grey card. That gives
  the player's hands the lamp without double-lighting the baked road.
- **Ambient** = Trilight, three colours per scene from `lens_cine` (Udon sets them). This is also the avatars' fill.
- **Fog:** Exponential only (§1). Conversions for the Exp2 values in `lens_lookdev` (equal 50% distance,
  d_exp = 0.8326 × d_exp2): scene 2 Exp2 0.0070 → **Exp 0.0058**; cloud interior Exp2 0.08 → **Exp 0.067** (cine
  uses 0.08 Exp; either is fine); scene 11 Exp2 0.0055 → **Exp 0.0046**. Fog colour and density are keyed curves.
  Density 0 = off. `RenderSettings.fog` is never toggled.

### 2.6 Reflections without mirrors

**Why no `VRCMirrorReflection`:** a VRChat mirror re-renders every layer in its Reflect Layers mask **once per eye per
frame** from the mirrored camera, at up to full eye resolution, with MSAA. On a real scene that is +60-100% GPU. It
also reflects every avatar, which invites people to stop and look at themselves. Nothing in this ride needs it:

| mirror in the story | tool | why it is exact enough |
|---|---|---|
| sea (6), star sea (9), dusk ocean ceiling (8), Snell's window (7) | **cube lookup** in `Lanbai/Sea` with the reflected or refracted view vector: `_Udon_ReflCube` = a per-scene cube **baked in the editor** from the bus position (sky + cloud cards + far scenery) | reflected content is 1-8 km away. The parallax error from a fixed capture point is below 1° |
| the 8 ceiling seen at grazing (rose-gold mirror) | same, cube captured looking down (`ReflCube_DuskLower`) | grazing reflections show the horizon, the farthest content there is |
| still puddles (12), flooded field, the first mirror | **mirrored duplicates behind a stencil**: the puddle shader writes stencil bit 128. The lamp head, tube, pole, sign and bus (LOD1, with lit windows baked) are drawn again, mirrored below the water plane, only where the stencil is set. Fireflies use a mirrored duplicate particle system (lookdev already planned it) | geometry reflections are stereo-correct and exact, for about 8 extra draw calls. Stencil bit 128 stays clear of the low stencil values avatar shaders use |
| reflected stars in the star sea and in the bronze mirrors (9) | a second copy of the **star sprite mesh** with `_MirrorY` on, drawn only through the mirror stencil or below the horizon | crisp reflected stars with no shimmer, 1 draw call |
| wet road streaks (1, 2), sea underside glitter (11), droplet bokeh on glass | **analytic GGX lamps** in the shader: up to 8 lamps in `_Udon_Lamp0..7` (xyz = position, w = intensity; colours in a second set) | the streak is a specular highlight of a small source. Analytic GGX gives the physically right elongation for free, moving with the lamps |
| near gloss (chrome rails, bus paint, wet sign) | **one box-projected baked probe per scene**, a child of the static bus, 256² (512² at the stop), HDR. Udon activates the one for the current scene | Standard, surface-shader and avatar materials pick it up automatically. The bus never leaves its box |

**Baking the cubes:** the cloud side writes `LanbaiReflectionBaker.cs` (editor). For each scene it activates only
that root, sets the sky material state, calls `Lightmapping.BakeReflectionProbe` for the bus probe, and renders
`Camera.RenderToCubemap` for `_Udon_ReflCube` (256 per face, BC6H). That gives 11 cubes, about 6 MB in total.

**Glass without GrabPass.** `lens_lookdev` §3.6 asks for a named GrabPass for droplet refraction. In VR that is a
resolve and copy of both eye buffers every frame, about 0.3 ms at 9 MP, for windows that cover half the view.
Instead, each droplet samples `_Udon_ReflCube` with its refracted vector, plus the analytic lamps with a wide lobe.
That gives exactly what the GrabPass would show at night (inverted points of lamp light) for the price of a texture
lookup.

### 2.7 Transparency, particles and overdraw

- **Unit: FSE (full-screen equivalent)** = transparent coverage summed over both eyes, divided by the eye area. An
  unlit card costs about 0.2 ms per FSE at 9 MP per frame on the reference GPU. A card with a depth fade and inverse
  tonemapping costs about 0.3 ms.
- **Budgets:** at most **4 FSE sustained and 7 FSE peak** (5 s or less); **no pixel under more than 8 layers**;
  at most **5 000 particles alive** per scene in at most 8 systems. Particles use no collision module and no lights
  module.
- **Queues:** sky 1000 (skybox) → opaque → point sprites 2900 (additive) → horizon ring 2980 → far cards 2990 → near
  cards and rain 3000 → glass 3050 → text 3100 → beams and glows 3150 → overlay 4100.
- **Near-eye rule:** every transparent effect fades out between 1.0 and 0.3 m from the camera (`LanbaiNearFade`,
  particle Camera Fading Near 0.3 / Far 1.0). Nothing monocular sits in the face.
- **Flat cards in stereo:** a card 20 m away is visibly flat (disparity resolves about 2 px of depth). Near wisps are
  **2-3 stacked fixed quads** 6-10 m apart at ≥ 25 m, not one billboard. Big far cards face the bus and are not
  billboards: a camera-facing card rotates when the head moves.
- **Edge-on fade** on every god-ray, beam slab and wisp card (`LanbaiEdgeOnFade`, power 1.5).
- **Fast particles are stretched** to their per-frame travel (`length ≥ speed / 90 × 1.5`). There is no motion blur
  in VR, so an unstretched fast particle strobes.
- **Max Particle Size**: 1.0 for the rain and snow systems, 3 for the near cloud system (see `README_Clouds` §4).

### 2.8 LOD, culling, batching, instancing

- **Tentacles:** one material per variant (it carries `_RootRadius`, §4.4). **GPU instancing on** (add
  `#pragma multi_compile_instancing` to the sway shader, enable it on the materials). LODGroup thresholds (screen
  relative height): LOD0 > 12%, LOD1 > 3%, LOD2 > 0.2%, culled below. Colossi: never culled. **No animated
  cross-fade**: dithered crossfade is a screen-space pattern that crawls in VR. Pop the LODs inside fog, where they
  are 10-25% of their contrast.
- **Everything else** that moves is pre-merged per material by the cloud side (palace, road modules, cloud ring,
  shaft fans), because static batching is off for moving roots.
- **No occlusion culling bake.** The ride is outdoors and the occluders move. Frustum culling, LOD and root
  switching are enough.
- **LOD bias is the player's setting.** Place transitions where a factor of 2 either way still hides them.

---

## 3. Comfort and safety law

### 3.1 Photosensitivity

**The rule, for the whole world:**
- **General flash:** a pair of opposing changes in relative luminance of ≥ 0.10 (on 0-1), where the darker state is
  below 0.80, inside any patch the size of 25% of a 10° field (4.4° square). **At most 2 per second** (WCAG 2.3.1
  allows 3). VR makes a 4.4° patch easy to fill: one ceiling tube 1 m from the eye is 60° long and 7° wide.
- **Red flash:** no saturated red (R/(R+G+B) ≥ 0.8 in linear RGB) element larger than 1°² ever changes by more than
  20% in less than 0.5 s. The tail lamps, the palace vermilion and the sodium light are steady. No blinkers or hazard
  lights, ever.
- **Sub-threshold motion is free:** changes smaller than 0.10 of maximum relative luminance are not flashes. That is
  where the life goes: the ±6% tube shimmer, ±2% white breathing and slow twinkles.

**Measured on the synthetic seat view** (`synth_tests.py`, 320×180 frames, 90° hFOV, ten big ceiling tubes, the
tear, the plunge and the dawn; full reports in `out/selftest_reports.json`, plots in `out/check_*.png`):

| case | max flashes in any 1 s | WCAG 2.3.1 | Lanbai (≤ 2) | max EV rise in 0.25 s / 1 s / 2 s |
|---|---|---|---|---|
| **A: lens_tech gate** (FlickerTable, entry flash +1.5 EV/0.4 s, 0.25 s to black, 7 s EV-linear dawn) | **2.0** | PASS | PASS | 0.51* / 0.78 / 1.37 |
| B: lens_cine 5.4-5.5 (stutters to 3/s without a refractory gap, +2 EV/0.25 s flash, 5 s ease-out dawn) | 4.0 | **FAIL** | FAIL | 2.77 / 3.68 / 4.33 |
| C: lens_lookdev 3.2 (each tube its own sequence up to 3/s) | 6.5 | **FAIL** | FAIL | 1.15 / 1.08 / 0.87 |
| D1: 4 Hz strobe (sanity) | 4.0 | FAIL | FAIL | n/a |
| D2: 2.5 Hz strobe (sanity) | 2.5 | PASS | FAIL | n/a |

\* only the authored tear flash exceeds 0.5 EV per 0.25 s, which is its allowed exception.

**The tube flicker (scene 4)** plays from `out/FlickerTable.cs`, generated by `flicker_schedule.py` (seed fixed):
- **42 dips** from the tear reveal (t = −105 s before "Gott") to −1.5 s. The density grows from 0.08/s to 1.1/s over
  the last 20 s, so it *feels* like a dying tube accelerating;
- each dip is **one** flash: level 0.03-0.45, **70-150 ms** long, never a single-frame blink. There are no
  multi-blink bursts: the classic "buzzing stutter" of a broken fluorescent is 10-15 Hz and is exactly what we must
  not show;
- **dip starts ≥ 0.60 s apart across all tubes**, so at most 4 transitions (2 flashes) fall in any second;
- a companion tube (the 30% neighbour correlation `lens_lookdev` wants) dips with the same start and duration, so it
  is still one flash;
- **1.5 s of quiet before the entry**, so the entry flash stands alone;
- on top, a **continuous shimmer in the tube shader: ±6% of tube level, below 2 Hz**. It is below the flash threshold,
  unlimited and cheap, and it carries most of the "dying" feel;
- the tubes' share of the baked cabin light follows the mean tube level (`_Udon_CabinLightmap` = mean). One tube
  dipping moves the cabin by about −0.14 EV: visible, but not a flash.

**Every flashing or pulsing element in the world, and its limit:**

| element | scene | limit |
|---|---|---|
| tube dips | 4 | FlickerTable only; ±6% shimmer in the shader |
| tear entry flash (FLASH_TEAR) | 4→5 | **once**: +1.5 EV max (not +2), rise **0.4 s** EV-linear, hold 0.1 s, fall to black **0.25 s** (not 0.10). Tubes go to 150% with it and die in the fall. Nothing else changes within 1.5 s before it. The afterimage of the tear in the following black is a free, physiological effect: keep the tear's shape bright in the last 0.3 s and the black empty, so the eye paints its own violet ghost |
| mirror crossings (MIRROR_PULSE) | 9 | +0.35 EV max, 0.08 s in / 0.35 s out, **only while crossings are ≥ 1.2 s apart**. When the music drives them closer, the line of light still sweeps and the pulse is dropped |
| last mirror → white | 9→10 | the ramp law (§3.2), not `lens_lookdev`'s +5 EV in 1.5 s |
| sea impact bubble burst | 6→7a | one event, peak APL ≤ 140 (≤ +0.7 EV over the dawn), rise ≥ 0.6 s, total 1.2 s |
| streetlight sweep | 2, 11 | ≤ 0.4 Hz, a sweep and not a blink: already compliant |
| radio dial | 2, 11 | ±10%, ≤ 2 Hz; small area |
| TV window in the village | 2 | ≤ 1 Hz, ≤ 0.5°² |
| city twinkle | 3 | ≤ 1.5 Hz (the sprite shader clamps it), points only |
| plankton twinkle, ambient sparks | 7 | sparks never closer than 5 m, ≤ 3 cm, never more than one inside any 5° cone at a time |
| fireflies | 12 | asynchronous phases, pulse 0.35 s, gap 2-6 s. **Never synchronised** (a synchronised field pulses as one big flash) |
| stop lamp, credits-case light | 1, 12 | steady. The case light switches on once, with a 1.5 s ease |

**The capture protocol for the build** (do it before the user sees the gate):
desktop mode, 1920×1080, hFOV 90°, seated head position. Capture at 60 fps (Unity Recorder or OBS, PNG sequence):
(a) the gate from −60 s to the dawn, looking forward, then again looking **up at the tubes**; (b) 6→7a; (c) 7b→8;
(d) the last 30 s of 9 through 10; (e) 10→11→12. Run
`python flashcheck.py <dir> --fps 60 --hfov 90 --out <name>` for each. Required: `lanbai_flash_rule: PASS`, and
`lanbai_ramp_law: PASS` everywhere except the tear flash.

### 3.2 The luminance ramp law (never slam to white in a headset)

**Definitions.** L = full-field mean relative luminance (linear, 0-1) of what the screen shows. EV = log2(max(L, 0.004)).
The floor 0.004 is about display luma 20, roughly 0.4 nit on a 100-nit headset: below it the eye is mesopic, and
"EV" says nothing about comfort.

**Limits for every authored full-field brightening:** **≤ 0.5 EV in any 0.25 s, ≤ 1.0 EV in any 1 s, ≤ 1.8 EV in any
2 s.** The only exception is the tear flash (§3.1). Darkening is free, except that it counts toward flashes.

**The shape: exponential in luminance, linear in EV.** A linear alpha fade to white delivers almost all of its EV
in the first 10% of its time: that is the slam. Use these:
- **Overlay fades** (fade sphere): `alpha = EvOverlayAlpha(x, Lfrom, Lto, Lscene, Lover)` (Appendix A). The
  composite luminance moves geometrically from Lfrom to Lto.
- **Exposure fades** (volume weight on a profile that differs in `postExposure`): weight linear in time. PPv2 is
  already linear in EV.
- **Spatial wipes** (`lens_lookdev`'s "dawn from the top down"): allowed if each pixel's own ramp lasts ≥ 2 s and
  the full field obeys the law. Use a soft mask edge at least 30° wide.

**Every brightening in the piece, made compliant** (APL values from `lens_cine`'s value score; L ≈ (APL/255)^2.2):

| transition | from → to APL | ΔEV (above the floor) | spec that obeys the law | versus the sibling spec |
|---|---|---|---|---|
| spawn fade from black → 1 | black → 22 | 0.2 | 3 s EV-linear | same |
| 3: road → cloud whiteout | 24 → 62 | 3.4 | ≥ 7 s (cine's 7 s is fine) | ok |
| **4→5 tear flash** | 36 → +1.5 EV | 1.5 | **0.4 s, the one exception** | cine: +2 EV in 0.25 s |
| **5→6 black → dawn** | black → 110 | 5.3 | **7 s EV-linear** from the floor (with a top-down wipe if wanted) | cine: 5 s ease-out cubic = 3.7 EV in its first second |
| 6→7a bubble burst | 110 → ≤ 140 → 85 | 0.7 | rise ≥ 0.6 s | lookdev: 0.4 s at white |
| **7b→8 deep → dusk** | 16 → 75 | 4.3 | **≥ 5 s** (cine says 4 s) | 4 s = 1.07 EV/s |
| 9a→9b accumulation | 30 → 80 | 2.6 over 3.5 min | x^2.5 is fine | ok |
| **9b→10 the white** | 80 → 224 (VR) / 239 (desktop) | 3.2 | **crash**: +1.0 EV over 1.2 s (bloom 5 → 16 carries the impact, spreading light instead of raising the level). **Swell**: +1.0 → +2.4 EV over the next 6 s. **Overlay**: EV-linear to the white over the last 3 s | cine: 5 s cubic + 1 s gives 1.22 EV/1 s and 2.13 EV/2 s |
| 10→11 white → night | 224 → 30 | darkening | 8 s. The **cabin tubes appear first**, then the lamps, then the sea: after 20-30 s of white the eye needs 10-20 s to see a luma-30 scene again, so the bright elements must lead | cine agrees |
| **11→12 "white again"** | 30 → 176 | 5.0 | **6.5 s EV-linear to `#A3B4BE`** (not full white: after a night scene luma 176 reads as white), hold 1.5 s, 4 s back | cine: 2.5 s linear alpha to `#E8F1F5` = **5.3 EV in the first second** |

![ramps](lens_tech/out/ramps_compare.png)

### 3.3 Peak brightness

- **The white of scene 10: VR `#D7E3E8`** (luma ≈ 224, relative luminance ≈ 0.75, the hue of `lens_cine`'s
  `#E8F1F5` at the level of `lens_lookdev`'s VR value). **Desktop `#E8F1F5`.** The Director picks the value by
  `IsUserInVR()`. A 100-nit headset full of 0.75 after 20 minutes of night is overwhelming enough. At 0.87 it becomes
  fatiguing over a held chord of 20-30 s.
- **Hold** the white for ≤ 30 s. Allow ±2% breathing at ≤ 0.1 Hz (the Overlay shader's `_Breath`).
- **Every other scene:** full-field APL ≤ luma 150 in VR. Dawn (110), shallow sea (85) and dusk (75) are all under it.
- Small emitters (sun, tear core, lamp heads, star points) may clip. Area ≤ 2% of the field, as in `lens_cine`
  rule 5.

### 3.4 Vection, horizon and the rest frame (a seated rider while the world falls)

The rider's inner ear says "sitting still". Every visual self-motion is a conflict, so we spend it where the story
needs it.

| rule | number | why |
|---|---|---|
| horizon | **roll = pitch = 0, always**, including the skybox, which never rotates during a scene | roll and pitch vection are the strongest sickness triggers |
| yaw (night road bends) | ≤ **3°/s**, changes ≤ 1.5°/s², bend radius ≥ 250 m at 11 m/s | yaw vection is tolerable only when slow |
| speed changes | ramps ≥ **4 s**, smoothstep. Departure 0 → 11 m/s over 8 s (≤ 1.4 m/s²). Lift-off vertical 0 → 20 m/s over 8 s | visual acceleration without vestibular acceleration is the conflict. Constant speed is nearly free |
| vertical bounce | **zero** (no road bumps, no engine shake) | 1-4 Hz vertical oscillation is the worst frequency band for motion sickness. Sell the old bus with sound and with the curtains' sway |
| the surround | the sky, sun, moon, stars and the horizon ring are earth-fixed. Only near objects move | an earth-fixed surround is the strongest anti-vection cue there is |
| near passes | objects within 20 m pass at ≤ 60°/s at the eye. Tentacle paths never come nearer than **8 m to the eye** | large looming objects trigger a startle and a flinch. 8 m is dramatic, 3 m is a jump scare |
| the plunge (5) | if motes are used: ≤ 150, ≤ 10 m/s (not 25), stretched, only outside the windows, 3 s | a black field with only upward flow is pure vection with no rest frame. 3 s is below most vection onset times at that speed |
| rest frame | until 9: window frames, pillars, the seat ahead, and a **floor patch at least 1.2 × 1.6 m** under the seat. The player's own seat goes last, in the final seconds of 9 | the cockpit effect. Keep the floor under the feet especially in 8, where the cloud sea 1-2 km below is a strong height cue (vertigo) |
| invisible colliders | always (§2.1) | a player who stands up in the stars must not fall |

Scene 9 is safe without a floor because the stars are at infinity, so there is no height cue. The rising mirrors are
object motion, not self-motion, as long as the stars stay still.

### 3.5 Stereo hygiene

- **Nothing screen-locked in VR:** no grain, vignette, lens dirt, chromatic aberration, lens distortion, screen-space
  god rays or radial blur. A screen-locked element is drawn at the same screen position in both eyes, so it fuses at
  the screen plane and reads as dirt on the lenses. Our god rays are world-space cards: correct.
- **Bloom is fine per eye.** A halo is centred on its source in each eye, so it fuses at the source's depth. Keep
  diffusion ≤ 9 and the threshold ≥ 0.9, so no ordinary surface blooms.
- **Dither is direction-anchored** (`LanbaiSkyDither`), the same in both eyes for content at infinity.
- **No ZTest Always except the fade sphere.** Text drawn over a nearer object is a depth conflict: the eyes say
  "behind", the occlusion says "in front". That conflict is the most uncomfortable thing stereo can do.
- **Billboards:** particles face the camera position. Far cards face the bus (fixed orientation). Point sprites
  are Gaussians (orientation-free).
- **Near field:** nothing within 0.3 m of the eyes except the player's own cabin geometry (§2.7).
- **Scale:** the bus is 8 m in the world, but avatars differ in size (a 0.9 m avatar sees a bus the size of a
  hall). Test framing with a 1.2 m and a 1.9 m avatar. Nothing in the design depends on exact eye height, except
  the windscreen composition, which `lens_cine` states relative to the seat.

### 3.6 Shimmer and aliasing (the difference between "photoreal" and "VR game")

| source | fix |
|---|---|
| stars in a cubemap, city lights in a texture tile, palace specks, far lamps | `Lanbai/PointSprites`: Gaussian sprites, FWHM ≥ 1.4 px, brightness conserved when enlarged, twinkle ≤ 1.5 Hz. Stars: about 9 000 to magnitude 6.5 = 1 draw call |
| thin geometry: tentacle tips, tear fibres, wires, stanchions far away | minimum-radius inflation in the vertex shader (`LanbaiInflate`, 1 px), emission and rim scaled by coverage (§4.4) |
| wet highlights on tentacles, chrome rails, wave normals | `LanbaiSpecAA` on every glossy custom shader; Toksvig on the sea (lookdev already asks) |
| alpha-tested foliage (Linluo trees, verge grass), tear fibres | `AlphaToMask On` + alpha sharpening `a = (a − cutoff) / max(fwidth(a), 1e-4) + 0.5`. Tear fibres: **additive, not alpha-tested** |
| far textures at grazing angles (city glow plane, cloud floor, sea) | anisotropic filtering 8-16 on these textures, trilinear |
| dark gradients banding (night skies, fog, the white) | direction-anchored dither in the sky and overlay shaders; PPv2 dithering on |

### 3.7 Text in VR (poems and credits)

**Headset pixel density** (centre of the lens, pixels per degree): Valve Index ≈ 14, Quest 2 ≈ 20, Pico 4 ≈ 20,
Quest 3 ≈ 25, Bigscreen Beyond ≈ 30. Desktop 1080p at the default FOV ≈ 18. **Design for the Index.**

| text | glyph height (em) | Index / Quest 2 pixels | rule |
|---|---|---|---|
| CJK main line (zh / ja) | **2.2°** | 30 / 44 | Source Han Serif Regular is fine at this size; Face Dilate **+0.10 in VR**, +0.05 on desktop (set by Udon) |
| CJK secondary line | **≥ 1.6°** (lookdev's 1.3° gives 18 px on the Index: complex hanzi like 鳞 and 阙 break) | 22 / 32 | Medium weight |
| Latin / German main | 2.0° em (x-height ≈ 0.9°) | 28 / 40 | EB Garamond Regular or Italic |
| Latin secondary, the Keats line | ≥ 1.5° em | 21 / 30 | |
| line length | ≤ 28° (about 12 CJK characters with tracking) | | read with the eyes, not the neck. Break at the caesura |
| vertical position | centre between −6° and +4° from eye level | | never above +10°, never below −15° |
| hold time | ≥ 3 s + 0.3 s per CJK character, or + 0.28 s per Latin word | | before the fade-out starts |
| brightness | ≤ linear 0.85 (no bloom), as in `lens_cine` §7 | | blurred text is unreadable in VR |

**World-locked, never head-locked.** The poem is a child of `PoemAnchor` (a yaw pivot at the seat eye point). At the
cue, the Director places it at the scene's default azimuth (below). If the player's head yaw is more than 50° away
from that at the cue, it places the poem at the head yaw instead (snapped to 15° steps), at the same elevation and
distance. It never follows afterwards. Scene 8 is the exception: the poem always sits ahead on the horizon (the
composition *is* the line).

**Distance per scene.** The text is depth-tested, so anything nearer passes in front of it correctly. The rule is:
put the text *behind* anything that crosses its cone, and *in front of* anything that merely sits behind.

| scene | poem | distance, azimuth, elevation | why |
|---|---|---|---|
| 3 | 李白 我欲因之梦吴越 | 40 m, 0°, +2° | the moon path is the background. Nothing near |
| 4 | Rilke; Urlicht lines | **60 m**, −8° (left of the tear), +4° | near tentacles (10-40 m) pass in front: correct and dramatic. Never over the tear core |
| 6 | 我从天空坠入深海 | 40 m, −20°, −2° | the dark-ink variant needs luminance contrast ≥ 4.5:1 against the sky. `#1F2A3A` on a sky of `#B0C4E0` gives 8:1 |
| 7 | 河伯 | 18 m, 0°, +3° | in front of the palace (20-40 m, below at −25°). Fog-exempt |
| 8 | 庄子 天之苍苍 | 60 m, 0°, **0°** (on the horizon), with the reflection at α 0.5 | the composition. Fixed ahead |
| 9 | 天问 | 50 m, 0°, +10°, **timed into the gap between crossings 1 and 2** (≥ 20 s) | a rising mirror plane occludes everything beyond it while it passes |
| 11 | 庄子 胡蝶 | **6 m**, 0°, −2° | the inverted lamps pass at ±25°+ azimuth. At 6 m the block (±12°) stays clear of them |
| 12 | 李白 惟觉时 + Keats | 15 m, 0°, +2° (over the empty road) | nothing moves there. It stays put if the player stands up |

**Credits board** (read at about 1.2 m): Latin cap height **≥ 18 mm** (0.86°, 12 px on the Index; lookdev's 11 mm gives
7 px), CJK names ≥ 24 mm, title ≥ 50 mm. The Coleridge slip may be smaller (≥ 12 mm cap). VR players lean in. It is an
easter egg.

### 3.8 Dark scenes on real headsets

- **LCD headsets** (Quest 2/3, Index, Pico 4): panel black is about relative 0.001, and there is glow and mura. The
  darkest detail that must read (tentacle bodies at `#0B0C12`…`#15161E`) sits at or under panel black, so it reads by
  rim and specular only. That is the design, so it is fine. Silhouettes that *must* read (tree line, field horizon,
  the bus outline at the stop) need ≥ 1 EV and ≥ 10 codes of separation from their background.
- **OLED headsets:** a true 0 smears when the head moves. `lens_cine`'s lifted floor (input 0 → `#02060C`) prevents
  it. Keep it in every night profile.
- **Link / Air Link / Virtual Desktop** compress the stream, and large smooth dark gradients macroblock. We cannot
  control the encoder. We can avoid huge featureless dark gradients: keep a little structure (overcast texture, haze,
  star glow) in every night sky, and dither.
- **Fresnel-lens glare** (Quest 2, Index): a small bright object on black throws radial glare streaks inside the
  headset. The tear and the stop lamp will do this. It suits both, and it is another reason the tear must sit alone in
  the view.

---

## 4. Scene by scene

Each scene: **realisation** (what renders what), **cost** (planning estimate on the reference GPU, §5.1, ±40%; the
build measures the real numbers), **comfort** (what can go wrong), **cover** (when root switches may happen).

### 4.1 站牌 The stop (spawn → boarding)

**Realisation**
- R_Stop around the origin, fully baked: the lamp as a baked **area light** 1.2 × 0.04 m (as lookdev designs it), the
  cabin spill, the headlight pools (the bus is parked, so they bake), and the sky ambient at bake time.
- The **player-only realtime spot** on the lamp for the avatars (§2.5).
- **Wet road:** `Lanbai/WetSurface` with 8 analytic lamps (lamp tube, 2 headlights, 2 tail lamps, door spill, 2 window
  strips). These give the streaks. The puddles use **stencil mirror copies** of the lamp, tube, pole, sign and bus
  LOD1, plus ripple normals from the rain kit on top. Reflection probe `Refl_S1`: 512², box 48 × 10 × 20 m.
- **Rain:** 1 800 in the lamp cone + 900 in the headlight beams + 600 ambient + about 30 splashes. At most 3 300
  alive, stretched billboards ≥ 3 px long, camera fade 0.3 / 1.2 m, no collision.
- **Mist cards:** ≤ 12, soft fade 3 m, α ≤ 0.14.
- **Trees** (Linluo): alpha-to-coverage. LOD0 < 25 m, LOD1 < 60 m, impostor or billboard to 300 m, merged
  silhouette cards beyond. Wind sway ≤ 0.5 Hz, small.
- **Grass:** mesh clumps only within 20 m of the stop, A2C.
- **Town lights:** `PointSprites` (60-120 points, finite mode, `_Atten` 0.0003).
- **Sky:** `Lanbai/Sky` procedural night plus the overcast texture.

**Cost** ≈ **4.2 ms GPU**, about 250 batches, 3.4 k particles, 2.5 FSE (rain plus mist; the rain is thin).

**Comfort.** Spawn fade from black 3 s. The player walks about 12 m. **Colliders:** road, verge, sign pole, bus
entrance, and a trigger at the door seats the player in the station. The headlights point away from the spawn
view: never blind the arriving player. The lamp is steady (no flicker at the stop: it is the anchor of the world).

**Cover.** Spawn: all roots warm up for 2 frames behind the fade (shader warm-up, §1).

### 4.2 夜路 Night road

**Realisation**
- R_Stop slides back as the bus "pulls away" (0 → 11 m/s over 8 s). R_Road treadmill (§2.1): sodium lamps baked
  into their modules, 35 m spacing through the village, then the dark stretch.
- **Sweep spot** with the window cookie (Important, no shadows, culling mask Bus), driven by the nearest lamp's
  position. Two side-spill spots, Not Important, culling mask Roadside.
- **Road streaks:** the 4 nearest lamps plus the headlights go into `_Udon_Lamp0..7`.
- **Headlights:** one realtime spot with a **two-lobe cookie** (both beams in one light; half the cost of two),
  culling mask Road + Roadside, no shadows. Fake beam cones are additive (2 cones, ≤ 1 FSE).
- **Glass:** `Lanbai/BusGlass` without GrabPass, runners pushed backward (§2.6). Exterior rain: 800 bus-local
  streaks. Their velocity includes the relative wind, so they slant.
- **Radio dial:** emissive, ±10% ≤ 2 Hz.

**Cost** ≈ **4.5 ms**, about 220 batches.

**Comfort.** Yaw ≤ 3°/s on bends. No bounce. Poles pass 4-5 m from the window at up to 150°/s: keep them dark and
unlit (they are), because a bright object at that angular speed strobes.

**Cover.** None needed, the world is continuous.

### 4.3 离地 Lift-off: road → sea of lights → sea of clouds

**Realisation**
- R_Road sinks (vertical 0 → 20 m/s over 8 s, cruise, ease-out into the deck).
- **Sea of lights:** `PointSprites` finite mode, 8 000 points (the cloud side generates `CityLights_Points.fbx`
  procedurally: an organic road network, sodium 55%, warm 25%, LED 15%), plus a **low-frequency glow plane** (the
  2048 macro texture, aniso 16) and 3 haze layers. The points are geometry, so the view down-right stays razor sharp
  and still in VR.
- **Cloud deck** (`citybelow` preset cards) inside fog.
- **The whiteout** (fog Exp 0.067-0.08, 6-8 s) is the **cover**: R_Road off, R_Night on, S2→S3 crossfade
  (`lens_cine`), LENS ARCHIVE → CLEAN (desktop).
- **Break-out:** the horizon ring (8-10 quads, 1.5-4 km radius, bus-centred, queue 2980), the CloudFloor (2 parallax
  layers under the bus, UV scroll = virtual speed), 2-3 Congestus pillars, moon in the sky shader, bright stars as
  sprites with `_FluxCut` (about 200 stars).
- **Wisps** past the right window: stacked 3-quad wisps at ≥ 25 m, at most 2 overlapping near-full-screen wisps at
  a time.

**Cost** ≈ **5.2 ms** (the whiteout wisps are the peak: ≤ 6 FSE for ≤ 4 s).

**Comfort.** Vertical flow happens only below and beside: the cabin is intact, so it is fine. The droplets on the
glass streak sideways in the cloud: glass-local, no vection.

### 4.4 触手之门 The tentacle gate (the hottest scene)

**Realisation**
- R_Gate approaches and descends (the bus climbs toward the tear). Moon directional: Important, soft shadows. Tear
  directional: Important, no shadows. Cloud-sea fill: **Not Important directional from below** (free SH, §2.5).
- **Tentacles** (the cloud library):
  - GPU instanced; LODs per §2.8; **cast shadows only for the near rank** (within 60 m), so a tentacle's shadow can
    slide across the cabin, which is cheap and terrifying;
  - **patch the sway shader** (the cloud side will ship it):
    1. `#pragma multi_compile_instancing`;
    2. `_RootRadius` per variant, and in `vert` `LanbaiInflate(color.b × _RootRadius × scale, dist, 1.0, coverage)`
       along the normal. Pass `coverage` to `surf` and multiply the rim and the tip glow by it, so far threads stay
       one quiet pixel, never a sparkling dash;
    3. `o.Smoothness = LanbaiSpecAA(worldNormal, o.Smoothness)`, which kills the crawling wet streaks on far
       silhouettes;
  - no dithered LOD crossfade;
  - no camera fading on opaque tentacles (`lens_lookdev` §6.3 asks for 2-6 m fading, which needs dithering, which
    crawls in VR). Instead, **paths never come within 8 m**.
- **Tear:** an emissive opaque ribbon plus additive shells. **Fibres additive** with minimum width (600 as lookdev
  specs, 1 mesh). Halos: 2-3 additive cards, faded by camera distance in the last 150 m. **Shafts: ≤ 12 cards, each
  carrying 2-3 shafts in its texture** (not 16-24 single shafts), depth-tested, soft 40 m, edge-on fade. Loose
  threads 150, dust 300.
- **Cloud sea:** moon strips at 60-75%, CloudFloor. The violet tint is one additive quad on the floor plane.
- **Tubes:** FlickerTable plus the shimmer (§3.1).
- **Entry:** FLASH_TEAR (+1.5 EV / 0.4 s), tubes 150%, fall to black 0.25 s, the fade sphere to black.

**Cost** ≈ **6.9 ms peak** (tentacles 1.2, tear, halos and shafts 1.5 at the entry, cloud sea 0.8, cabin 1.0,
shadows 0.6, depth prepass 0.5, PPv2 1.1). Batches about 300. Triangles about 400 k.
**Knobs in order if it runs over:** shafts 12 → 8 → 6; halo layers 3 → 2; mid-rank LOD1 → LOD2 at 400 m;
dust 300 → 150; bloom diffusion 8.5 → 7.5; shadows only on the 3 nearest tentacles.

**Comfort.** Near passes ≥ 8 m, ≤ 60°/s. The Orpheus rear view: dense and closing slowly, never a lunge. The flicker
table and the flash cap. The Rilke text at 60 m.

**Cover.** The entry black (5) switches R_Gate off.

### 4.5 投入 The plunge (3 s)

**Realisation.** Fade sphere black (`#000` → it shows the `#03030B` floor). Everything behind it is **disabled**
(renderers off, R_Gate inactive), so the GPU idles. R_Dawn activates here (the shaders were already warmed up).
Motes: optional, ≤ 150, ≤ 10 m/s (§3.4). The tear's afterimage does the rest.

**Cost** ≈ 1.5 ms.

### 4.6 天空 I Dawn

**Realisation**
- `Lanbai/Sky` `_CubeA` = dawn HDRI (rotated so the sun sits at `lens_cine`'s az +60°, el +6°). Procedural sun
  disc. Sun directional aligned to it: Important, soft shadows. It makes the gold window stripes, the most "cinema"
  thing inside.
- **Beams:** additive slab meshes along the sun direction, parented to the bus. At most 3 overlapping through the
  head. Near fade 0.3 / 1.0 m.
- Dust 300 (particles inside the beam volumes).
- **Clouds:** dawn cards (≤ 30), ring, CloudFloor.
- **Sea below:** `Lanbai/Sea` ABOVE with `ReflCube_Dawn` (editor-baked, includes the cards) and the analytic sun GGX
  with Toksvig.
- **Birds:** one flipbook particle system, ≤ 80.
- Cabin bleach begins.
- The reveal: `EvOverlayAlpha` over 7 s from the floor. If the top-down wipe is used, its soft edge is ≥ 30°.

**Cost** ≈ **5.0 ms** (clouds 0.9, sea 0.5, beams and motes 0.4, cabin 1.0, shadows 0.5, prepass 0.4, PPv2 1.0).

**Comfort.** The brightest sustained scene (APL 110): inside the cap. Beams pass through the head. Additive with a
near fade, so no hard edge at the eye.

### 4.7 海面 → 深海 Sea surface → the deep

**Realisation**
- **Impact** (cover for switching R_Dawn to R_Sea, ≥ 0.8 s): the bubble burst, capped (§3.1). The sky switches to
  underwater gradient mode and the fog to water.
- **Snell's window:** `Lanbai/Sea` BELOW on the surface plane above the bus (the plane rises as the bus sinks),
  sampling `ReflCube_Dawn`.
- **God rays:** ≤ 16 cards (not 24; they are near and wide), edge-on fade, gone by 25 m depth.
- **Particles:** snow 1 200, bio trail about 600 alive, sparks 200 (≥ 5 m away), bubbles 40: about 2 000 total.
- **Palace:** fully baked with its lamps (two baked points per lamp, as lookdev designs it). Pre-merged into ≤ 40
  meshes. POM on the cowries only within 40 m (distance-faded to plain normal map). The flame flipbooks are unlit.
- **Fish:** 1 500 GPU-instanced mesh particles (`Particles/Standard Surface`, instancing on). About 90 k tris.
- **Caustics:** global in the cabin shader.
- Probe `Refl_S7` = the underwater gradient.

**Cost** ≈ **6.4 ms** in the palace stretch (palace 1.2, rays 1.0, particles 0.5, fish 0.3, cabin plus caustics 1.2,
Snell 0.4, prepass and shadows 0.8, PPv2 1.0).
**Knobs:** rays 16 → 10; fish 1 500 → 700; POM off; snow 1 200 → 700.

**Comfort.** Marine snow rising past the windows *is* the sinking cue, with the cabin intact. Good.
Exit (7b→8): **≥ 5 s** of brightening (§3.2). The boil of light is the cover for R_Sea → R_Dusk.

### 4.8 天空 II Dusk (the mirror frame) and 8b, the blue hour

**Realisation**
- `Lanbai/Sky` `_CubeA` = dusk HDRI, `_Mirror` = 1.
- **Ocean ceiling:** `Lanbai/Sea` CEILING on a 12 km plane that starts at +300 m and rises. It fades to sky by
  5-6 km, leaving the 3° slot. Reflection = `ReflCube_DuskLower` (§2.6). **No mirror component.**
- Dusk cards in mirrored pairs (6-10 pairs), wisps, curtains flying (vertex animation), sun directional from dead
  ahead with shadows.
- **8b:** `_CubeB` = the star-glow cube, `_BlendMask` directional (anti-sun and zenith first). The star sprites'
  `_Gain` ramps up in step with the mask. The dusk exposure falls about 3 EV over 45 s. R_Stars activates at gain 0.

**Cost** ≈ **4.5 ms**.

**Comfort.** The floor patch under the seat is **mandatory** here: the cloud sea 1-2 km below is a strong height cue.
The horizon is exactly level and at eye height: any tilt of the mirror seam would be felt as roll.

### 4.9 天空 III / 星海

**Realisation**
- **Stars:** the glow cube (1024/face) plus the star sprites (about 9 000, `_FluxCut` 0 here).
- **The sea below:** the sky shader's mirror mode for the glow, plus the **mirrored sprite copy** below the horizon.
  Both are free. (`lens_cine` wants a mirror sea, `lens_lookdev` a continuous star field below. The build can do
  either: the synthesizer picks.)
- **Bronze mirrors:** disc meshes with LODs. The face shader samples the star cube; the reflected stars come from the
  mirrored sprite copy drawn through the mirror's stencil.
- **Crossing line:** a world-plane slice term in the cabin shader (the 2 cm emissive band).

**Cost** ≈ **2.5 ms**, the cheapest dream scene. Spend the headroom on bloom.

**Comfort.** The stars never move. The crossings accelerate, but the pulse drops out below 1.2 s spacing (§3.1). The
poem goes into a gap between crossings. The seat erodes only at the very end.

**Cover.** The white (10) switches R_Stars off.

### 4.10 白光 The white

**Realisation.** The crash → swell → overlay schedule (§3.2) with WHITE_RAMP (bloom carries the crash). The overlay
colour is `#D7E3E8` (VR) or `#E8F1F5` (desktop) in display terms; enter the value `lens_cine` §5.10 computes for the
chosen target. `_Breath` 0.02 at 0.1 Hz. **Everything behind the sphere is disabled.** R_Road (dry variant) and
R_False activate here.

**Cost** ≈ 1.3 ms.

### 4.11 假醒 False awakening

**Realisation**
- R_Road again with `_Udon_Wetness` = 0 (a dry road from the same modules) and the glass rain at 0.
- R_False adds the **sea ceiling** at 80 m (`Lanbai/Sea` CEILING, 3 Gerstner waves in the vertex shader, plane
  256 × 256 quads within 400 m, a flat far skirt) and the **inverted lamps** hanging from it.
- Their glitter on the sea comes from the analytic lamps (4 nearest). The sweep spot is inverted (it lights the cabin
  ceiling).
- Cabin fade = 0, bleach = 0, tubes steady at 1. Radio dial static at ±10%.

**Cost** ≈ **4.6 ms**.

**Comfort.** The same speeds as scene 2. The first 8 s after the white: the tubes appear first (§3.2).

### 4.12 醒 Awakening and the credits

**Realisation**
- R_Stop back at its original offset (switched under the second white).
- Wetness 0.85, rain systems off, **puddle ripples 0**, so the stencil mirror copies are crisp. The 庄子 mirror with
  stars: the sky cube plus the mirrored sprites in the puddles.
- Fireflies 46-60, with a mirrored duplicate system over the flooded field.
- Credits case: the "light on" is emission on the paper (`_Udon_CaseLight`) plus one Not Important point light. No
  rebake.
- The 藍白 band: a procedural band in the sky shader.
- Colliders on: the player may stand and walk to the board.

**Cost** ≈ **4.0 ms**.

**Comfort.** The second white follows §3.2. The player can leave the bus: the stop colliders and the door are open
again.

---

## 5. Performance budget

### 5.1 Reference and frame budget

**Reference:** RTX 3060 / RX 6600 XT class GPU, a Ryzen 5 3600 class CPU, a Valve Index at SteamVR 100% (2016 × 2240
per eye) or a Quest 2 over Link at 1.0×. About **9 MP per frame at 90 Hz (11.1 ms)**. MSAA 4×.

| slice of 11.1 ms (GPU) | budget |
|---|---|
| world: geometry, transparency, shadows, depth prepass | **≤ 5.3 ms** sustained, ≤ 6.3 ms peak (≤ 5 s) |
| PPv2 (bloom fast mode + uber + LUT bake) | ≤ 1.2 ms |
| VRChat: local avatar + 1-3 guests, UI, nameplates | ~2.0 ms (not ours; assume it) |
| SteamVR compositor, lens-distortion pass, headroom | ~2.6 ms |

CPU (main thread, world share): **Udon ≤ 0.4 ms**, particle simulation ≤ 0.4 ms, batches ≤ 500 including shadow
casters, SetPass ≤ 120, triangles ≤ 1.2 M per frame (SPS-I draws both eyes from one call; vertex work counts twice).

### 5.2 Per scene (planning estimates, ±40%, to be replaced by measurement)

| scene | world + PPv2 GPU (ms) | batches | tris | particles alive | FSE (sustained / peak) | realtime lights: shadowed + pixel | baked | reflections |
|---|---|---|---|---|---|---|---|---|
| 1 stop | 4.2 | 250 | 350 k | 3 400 | 2.5 / 3 | 0 + 1 (avatar spot) + key dir. for depth | stop, cabin | probe 512 + stencil copies + analytic ×8 |
| 2 road | 4.5 | 220 | 300 k | 900 | 2 / 3 | 1 + 2 (sweep, headlights) + 2 NI | modules, cabin | probe + analytic ×8 |
| 3 lift | 5.2 | 180 | 250 k | 600 | 3 / 6 (whiteout) | 1 (moon) + 0 | cabin | probe + cube |
| 4 gate | **6.9** | 300 | 400 k | 450 | 4 / 7 (entry) | 1 (moon) + 1 (tear) + 1 NI | cabin | probe + cube |
| 5 plunge | 1.5 | 30 | 60 k | ≤ 150 | 1 | key ≈ 0 | – | – |
| 6 dawn | 5.0 | 160 | 250 k | 400 | 3.5 / 4.5 | 1 (sun) + 0 | cabin | cube (cards baked in) |
| 7 sea | **6.4** | 350 | 450 k | 2 000 + 1 500 fish | 4 / 6 | 1 (sun, weak) + 1 NI | palace, cabin | cube (underwater) |
| 8 dusk | 4.5 | 150 | 200 k | 300 | 3 / 4 | 1 (sun) + 1 NI | cabin | cube (lower) |
| 9 stars | 2.5 | 60 | 120 k | 0 | 1 / 2 | key ≈ 0 | – | star cube + sprite copy |
| 10 white | 1.3 | 10 | – | 0 | 1 | – | – | – |
| 11 false | 4.6 | 220 | 320 k | 0 | 1.5 / 2 | 1 + 1 (sweep) | modules, cabin | probe + analytic ×4 |
| 12 wake | 4.0 | 240 | 350 k | 150 | 1.5 / 2 | 0 + 1 (avatar spot) + key for depth | stop, cabin | probe + stencil copies |

The previous build ran at 80-140 fps in VR. The two scenes that can drop below 90 are **4 and 7**. Their knob lists
are in §4.4 and §4.7. Auto-lite (§2.2) applies them for slow machines.

### 5.3 Measurement protocol (the implementer)

In a headset, seated, with the world's normal quality settings (VRChat "High"), read the GPU frame time from SteamVR's
frame timing or fpsVR at the named moments: 1 (at the door), 2 (lamp pass), 3 (whiteout, break-out), 4 (−30 s, −5 s,
entry), 6, 7 (palace), 8, 9 (end), 11, 12. Push the table to `FromLocal/perf.md` along with the flashcheck reports.
Any scene above 6.5 ms applies its knobs in order.

### 5.4 Memory and download

| group | VRAM | note |
|---|---|---|
| sky: 2 HDRI cubes 2048 BC6H + star glow cube 1024 | 72 MB | the star cube shrinks from 2048 to 1024: the stars are sprites now |
| per-scene reflection cubes (11 × 256) + probes | 10 MB | |
| lightmaps (stop, modules, palace, cabin) | 35 MB | BC6H "High Quality" |
| everything in `lens_lookdev` §1.8 except the skies | ≈ 430 MB | as specified there |
| Linluo trees, grass | ≤ 60 MB | impostors beyond 60 m |
| fonts, particles, misc. | 15 MB | |
| **total** | **≈ 620 MB (cap 700)** | avatars in the instance need the rest of an 8 GB card |

**Download ≤ 250 MB compressed** (check the VRChat SDK build panel): use **Crunch compression (quality 90-100) on all
DXT1/DXT5 textures** (props, terrain, palace, bus, cabin; normal maps at quality 100). Keep BC7 for the cloud cards
and gradients and BC6H for skies and lightmaps (neither can be crunched). Crunch shrinks the download 3-5× and costs
no VRAM.

---

## 6. VR test checklist (before the user sees any scene in a headset)

1. Every custom shader renders in **both eyes** (close one eye, then the other).
2. Horizon level in every scene (a spirit-level test quad on the debug layer).
3. Nothing within 0.3 m of the eyes except the cabin; no text behind anything it draws over.
4. Poems readable on the lowest-ppd headset available; hold times per §3.7.
5. `flashcheck.py` passes on the captures of §3.1.
6. GPU times within §5.2.
7. Stand up mid-ride in 4, 8 and 9: no fall, no escape, and you are returned to the seat.
8. Desktop: vignette and grain present; VR: absent.
9. Small (1.2 m) and tall (1.9 m) avatar: the windscreen framing still works.
10. One full 20-minute ride seated, by someone prone to motion sickness. Note the minute of any discomfort.

---

## 7. What the cloud side ships to make this easy

**Shipped now** (this lens, `art/lens_tech/`): `flashcheck.py` + `synth_tests.py`, `flicker_schedule.py` →
`FlickerTable.cs`, `LanbaiVR.cginc`, `Lanbai_Overlay.shader`, `Lanbai_PointSprites.shader`, `ramps_compare.png`.

**Next, in priority order** (all uncompiled C#/shaders; the implementer compiles them):

| # | deliverable | form | unblocks |
|---|---|---|---|
| 1 | `LanbaiGradeBuilder.cs`: profiles, volumes and the test card from `grades.json` | editor C# | the grade, the calibration |
| 2 | `LanbaiDirector.cs` skeleton: clock adapter, volume crossfades, `EvOverlayAlpha`, fog, ambient and sky curves, flicker playback, root motion and switching, poem placement, auto-lite, out-of-bus return | UdonSharp | everything time-driven |
| 3 | `Lanbai/Sky`, `Lanbai/UnlitCardHDR` (SPS-I, soft particles, edge-on and near fades) | shaders | every scene |
| 4 | `LanbaiReflectionBaker.cs` (per-scene probes and cubes) + the spawn shader warm-up routine | editor C# + Udon | reflections, hitches |
| 5 | point meshes: `CityLights_Points.fbx` (8 k, procedural), `TownLights_Points.fbx` (120), `PalaceSpecks_Points.fbx`; `extract_stars.py` (the implementer runs it on the NASA EXR: star list + glow cube with the stars removed) | FBX + Python | 1, 3, 9, 11 |
| 6 | tentacle sway shader v2 (instancing, spec AA, minimum width, coverage-scaled rim) | shader | 4 |
| 7 | pre-merged kits as FBX + `layout.json` + `LanbaiLayoutImporter.cs` (instantiates the prefabs at the JSON transforms): cloud ring, shaft fans (12 cards), beam slabs (needs the bus side elevation), road modules (UV2 for lightmaps), stencil mirror copies (needs the stop layout) | FBX + JSON + editor C# | 3, 4, 6, 2, 12 |
| 8 | `Lanbai/WetSurface`, `Lanbai/BusGlass` (no GrabPass), `Lanbai/Sea` with specular AA and SPS-I | shaders | 1, 2, 6-8, 11 |
| 9 | expected screenshots: the grade test card per profile (`lens_cine` has the numbers) | PNG | calibration |

**Not shipped, by decision:** `.cube` LUTs (§2.3) and a mirror prefab (§2.6).

---

## 8. Flags: what I could not verify from here

- ⚑ **SPS-I on VRChat PC**: stated from memory. The macros are harmless either way.
- ⚑ **Udon exposure** of `PostProcessVolume.weight` and `VRCShader.SetGlobal*`: widely used, but check in the
  current SDK. The fallbacks are an Animator per volume and material swaps.
- ⚑ **All GPU numbers are estimates.** §5.3 replaces them.
- ⚑ **Whether the current build moves the bus.** If it does, §2.1's precision rule applies until it is converted.
- ⚑ The flicker and ramp tests are **synthetic** (a crude seat view with large tubes, which is conservative). Real
  captures are the proof.
- ⚑ **Headset ppd values** are nominal centre-of-lens values. Test text on the real headset.

---

## 9. Conflicts with the other lenses, and my resolution (for the synthesizer)

| # | topic | lens_cine | lens_lookdev | lens_tech resolution |
|---|---|---|---|---|
| 1 | tonemapper | Neutral | ACES (EV0 = +0.7) | **Neutral**: one curve all ride (PPv2 cannot blend it); near-identity makes unlit and emissive values predictable for an implementer who cannot see our screen; the lifted floor protects OLED; the ACES toe crushes the dark scenes that dominate this piece |
| 2 | pre-rendered cards | inverse-Neutral in the shader | re-export scene-referred (−1 EV) | either works with Neutral. **Prefer the re-export**: a cheaper shader (no per-pixel quadratic) and exact values |
| 3 | fog mode | Exp everywhere | Exp2 in 2, 3 (cloud), 11 | **Exp only**, converted densities (§2.5) |
| 4 | probes | light probes around the bus | – | **no light probes** (extrapolation) |
| 5 | cloud reflections in the sea | – | runtime `RenderProbe` | **editor-baked cubes** (no API risk, no hitch) |
| 6 | dusk ceiling | "the VRChat mirror / planar reflection" | cube | **cube** (§2.6) |
| 7 | droplet refraction | – | named GrabPass | **analytic lamps + cube** (§2.6) |
| 8 | tube flicker | up to 3/s, 60-200 ms off | per tube up to 3/s | **FlickerTable**: ≤ 2 flashes/s total, 70-150 ms, plus shimmer. Both originals fail WCAG in the synthetic test |
| 9 | tear flash | +2 EV in 0.25 s, snap to black in 0.10 s | 0.5 s white-violet, +2 EV | **+1.5 EV in 0.4 s, 0.1 s hold, 0.25 s to black**, once |
| 10 | black → dawn | 5 s ease-out cubic | 2.5 s top-down wipe | **7 s EV-linear**; a top-down wipe is allowed if each pixel ramps ≥ 2 s |
| 11 | the white | `#E8F1F5` everywhere | desktop `#EBF6F7`, VR `#D8E3E4` | **VR `#D7E3E8`, desktop `#E8F1F5`** |
| 12 | 9b→10 ramp | 5 s cubic + 1 s | +5 EV in 1.5 s | **crash + swell + overlay** (§3.2) |
| 13 | 11→12 white | 2.5 s linear alpha | – | **6.5 s EV-linear to `#A3B4BE`** |
| 14 | mirror pulses | +0.35 EV, ≤ 3/s | +0.5 EV for 0.2 s | **+0.35 EV, only while crossings are ≥ 1.2 s apart** |
| 15 | stars | cube 2048, sub-pixel sharp, no blur | sprites from `extract_stars.py` | **sprites** (FWHM ≥ 1.4 px); the cube carries only the glow, at 1024 |
| 16 | poem distance and size | 6-10 m, lower third | 25-60 m, 2.4° / 1.3° | **per-scene table** (§3.7), 2.2° main, ≥ 1.6° secondary CJK |
| 17 | credits text | – | 11 mm cap at 1.2 m | **≥ 18 mm** |
| 18 | bloom common params | fastMode false, clamp 65472 | – | **fastMode true, clamp 24** in every profile |
| 19 | fade sphere | r 0.6 m around the head | r 1.5 m | **r 4 m around the seat**, parented to the static bus (no head tracking, no lag) |
| 20 | near tentacle fly-bys | 10-40 m | 8-20 m with camera fading | **≥ 8 m, no fading** (opaque fading needs dither, which crawls in VR) |
| 21 | plunge motes | 250 at 15-25 m/s | none | if kept: **≤ 150 at ≤ 10 m/s**; none is also fine |
| 22 | god rays underwater / shafts at the gate | – / 16-24 | 24 / 16 | **≤ 16 underwater; ≤ 12 multi-shaft cards at the gate** |
| 23 | city twinkle | – | ±20% at 1-3 Hz | **≤ 1.5 Hz** (the sprite shader clamps it) |
| 24 | does the bus move? | unstated | unstated | **it never moves** (§2.1) |

---

## Appendix A: Director code that is easy to get wrong (UdonSharp sketches)

```csharp
// --- 1. Grade crossfade: the incoming volume rises while the outgoing stays at 1 ----------------------------
public PostProcessVolume[] vol;   // S1..S12 (+S7a/S7b, S8b, S9a/S9b), timeline order = ascending priority
public float[] fadeStart;         // timeline seconds when vol[i] starts to fade in
public float[] fadeDur;           // seconds
public bool[] smooth;             // true: smoothstep (colour change); false: linear (exposure change = EV-linear)

void UpdateGrade(float t)
{
    int top = -1;                                   // the newest volume that is fully in
    for (int i = 0; i < vol.Length; i++)
    {
        float x = Mathf.Clamp01((t - fadeStart[i]) / Mathf.Max(fadeDur[i], 0.001f));
        float w = smooth[i] ? x * x * (3f - 2f * x) : x;
        vol[i].weight = w;
        if (w >= 1f) top = i;
    }
    for (int i = 0; i < top; i++) vol[i].weight = 0f;   // older ones leave only once the newer one is at 1
}                                                        // stateless: seeking and restarting just work

// --- 2. EV-linear overlay: composite luminance goes geometrically from Lfrom to Lto --------------------------
// Ls = scene APL, Lo = overlay colour luminance (relative, linear). APL targets: L ~ (APL_luma / 255)^2.2.
float EvOverlayAlpha(float x, float Lfrom, float Lto, float Ls, float Lo)
{
    const float FLOOR = 0.004f;
    float a = Mathf.Max(Lfrom, FLOOR);
    float b = Mathf.Max(Lto, FLOOR);
    float L = a * Mathf.Pow(b / a, Mathf.Clamp01(x));        // constant EV per second
    return Mathf.Clamp01((Ls - L) / (Ls - Lo));
}
// black -> dawn over 7 s:  alpha = EvOverlayAlpha(x, Lblack, Ldawn, Ldawn, Lblack)   (1 -> 0)
// scene -> white over 3 s: alpha = EvOverlayAlpha(x, Lscene, Lwhite, Lscene, Lwhite) (0 -> 1)

// --- 3. Tube flicker playback (arrays pasted from out/FlickerTable.cs) --------------------------------------
public float tGott;                                  // timeline time of "Gott"
private int _k; private float _lastTr = -1e9f;
private float[] _lv = new float[10];
private int _idT0, _idT1, _idT2, _idCab;             // VRCShader.PropertyToID("_Udon_TubeLevels0") etc., in Start()

void UpdateTubes(float t)
{
    float tr = t - tGott;
    if (tr < _lastTr) _k = 0;                        // restarted or seeked back
    _lastTr = tr;
    while (_k < _dipT.Length && _dipT[_k] + _dipDur[_k] < tr) _k++;
    for (int i = 0; i < 10; i++) _lv[i] = 1f;
    for (int j = _k; j < _dipT.Length && _dipT[j] <= tr; j++)
    {
        if (tr >= _dipT[j] + _dipDur[j]) continue;
        int m = _dipMask[j];
        for (int i = 0; i < 10; i++) if (((m >> i) & 1) != 0) _lv[i] = Mathf.Min(_lv[i], _dipLevel[j]);
    }
    float mean = 0f; for (int i = 0; i < 10; i++) mean += _lv[i]; mean *= 0.1f;
    VRCShader.SetGlobalVector(_idT0, new Vector4(_lv[0], _lv[1], _lv[2], _lv[3]));
    VRCShader.SetGlobalVector(_idT1, new Vector4(_lv[4], _lv[5], _lv[6], _lv[7]));
    VRCShader.SetGlobalVector(_idT2, new Vector4(_lv[8], _lv[9], mean, 0f));
    VRCShader.SetGlobalFloat(_idCab, mean);          // x the entry envelope (150 % flash, then 0) elsewhere
}
// The tube shader: level = _Udon_TubeLevelsN[tubeId] * (1 + 0.06 * shimmer(t, tubeId)), with tubeId in vertex colour.

// --- 4. Poem placement: world-locked, gaze-aware once ----------------------------------------------------------
void PlacePoem(Transform anchor, float defaultYaw, bool fixedAhead)
{
    Quaternion hr = Networking.LocalPlayer.GetTrackingData(VRCPlayerApi.TrackingDataType.Head).rotation;
    Vector3 f = hr * Vector3.forward;
    float yaw = Mathf.Atan2(f.x, f.z) * Mathf.Rad2Deg;                 // bus heading = +Z (the bus never turns)
    float target = defaultYaw;
    if (!fixedAhead && Mathf.Abs(Mathf.DeltaAngle(yaw, defaultYaw)) > 50f) target = Mathf.Round(yaw / 15f) * 15f;
    anchor.localRotation = Quaternion.Euler(0f, target, 0f);          // the text is a child at (0, h, distance)
}
```
