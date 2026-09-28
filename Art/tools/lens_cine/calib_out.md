### Kelvin to Unity light colour (D65-balanced, max channel 255)

| K | hex | K | hex |
|---|---|---|---|
| 2100 | `#FF9624` | 2400 | `#FFA642` |
| 3200 | `#FFC47A` | 4300 | `#FFE0B4` |
| 5600 | `#FFF5E5` | 6500 | `#FFFFFF` |
| 7500 | `#EAF2FF` | 9000 | `#D6E4FF` |

Old fluorescent tube (4300 K + green bump): `#F6E7C0`. Tear violet (preview rig TEAR_COLOR): `#CE8BFF`.

### Grey-card targets (card = Standard shader, albedo #767676 = 0.18 linear, smoothness 0)

| Scene | Light role | Light colour | E (linear) | Unity intensity (directional, gamma rule) | Card reads (sRGB) |
|---|---|---|---|---|---|
| S1 | Key: stop lamp (LED 5600 K), card on the road at the pool centre | `#FFF5E5` | 1.30 | 1.13 | `#818181` |
| S1 | Fill: cabin spill through the open door (tube cream), card on the kerb | `#F6E7C0` | 0.35 | 0.62 | `#3E3E3A` |
| S1 | Headlight pool on the road 10 m ahead (halogen 3200 K) | `#FFC47A` | 0.90 | 0.95 | `#6A5542` |
| S1 | Ambient only (Trilight sky #1A2438), card facing up | `#1A2438` | 1.00 | 1.00 | `#050C17` |
| S2 | Key: cabin tubes, card on a seat cushion | `#F6E7C0` | 0.55 | 0.76 | `#4D4B46` |
| S2 | Streetlight sweep peak (sodium 2100 K), card on a seat | `#FF9624` | 0.90 | 0.95 | `#623D2B` |
| S2 | Headlight pool on the road 10 m ahead | `#FFC47A` | 0.90 | 0.95 | `#645141` |
| S3 | Key: moon (9000 K) directional, intensity reference E = 1 | `#D6E4FF` | 1.00 | 1.00 | `#414C5B` |
| S3 | Cabin tubes after the break-out (half of S2) | `#F6E7C0` | 0.27 | 0.55 | `#242524` |
| S4 | Moon rim source (same moon), card facing the moon | `#D6E4FF` | 1.00 | 1.00 | `#3C4354` |
| S4 | Tear light (violet) directional from the tear, card facing the tear | `#CE8BFF` | 0.80 | 0.90 | `#301C47` |
| S4 | Cloud-sea bounce from below (#5A6488), card facing down | `#5A6488` | 0.24 | 0.53 | `#060713` |
| S4 | Cabin tubes base level before they die | `#F6E7C0` | 0.25 | 0.53 | `#1E1C1D` |
| S6 | Key: dawn sun 3200 K, 6 deg elevation | `#FFC47A` | 3.00 | 1.65 | `#8E6B47` |
| S6 | Sky ambient only (Trilight sky #5A78B8), card facing up | `#5A78B8` | 1.00 | 1.00 | `#102038` |
| S7a | Key: sun through the surface (#A8DCEB), card facing up | `#A8DCEB` | 1.60 | 1.24 | `#3A636B` |
| S7a | Water ambient (Trilight equator #2B7FA8), card facing sideways | `#2B7FA8` | 1.00 | 1.00 | `#002A39` |
| S7b | Palace glow from below (vermilion point light) at the bus | `#FF5A2E` | 0.15 | 0.42 | `#1F090F` |
| S7b | Deep ambient (Trilight sky #0E3050), card facing up | `#0E3050` | 1.00 | 1.00 | `#000D1D` |
| S8 | Key/back: dusk sun 2400 K on the horizon, card facing the sun | `#FFA642` | 2.20 | 1.43 | `#935A24` |
| S8 | Ground ambient: rose-violet cloud sea (#6A4A78), card facing down | `#6A4A78` | 1.00 | 1.00 | `#221629` |
| S8 | Sky ambient: ocean ceiling (#1C3350), card facing up | `#1C3350` | 1.00 | 1.00 | `#000E1B` |
| S9a | Starlight ambient (Trilight sky #1A2A4A), card facing up | `#1A2A4A` | 1.00 | 1.00 | `#031022` |
| S9a | Mirror-crossing pulse light 8000 K (peak) | `#E2EDFF` | 0.30 | 0.58 | `#38414D` |
| S12 | Key: stop lamp (same as S1) | `#FFF5E5` | 1.30 | 1.13 | `#818080` |
| S12 | Ambient only (clearing sky #121C2E), card facing up | `#121C2E` | 1.00 | 1.00 | `#030A15` |
| S3 | white card (albedo 0.80) under the moon: must match moonlit cloud-card tops | `#D6E4FF` | 1.00 | 1.00 | `#8D9CAF` |
| S6 | white card (0.80) in the dawn sun | `#FFC47A` | 3.00 | 1.65 | `#E2C391` |
| S8 | white card (0.80) facing the dusk sun | `#FFA642` | 2.20 | 1.43 | `#E5AC4D` |

### Unlit / emissive / fog: display target -> value to SET in Unity (under that scene's grade)

`#RRGGBB @ +n` means HDR colour: base hex with the HDR picker Intensity = +n (x 2^n). Values without @ are plain colour-picker hex (Unity converts sRGB->linear).

| Scene | Element | Screen must show | Set in Unity |
|---|---|---|---|
| S1 | Fog colour (Exp2) | `#101A2B` | `#151B2C` |
| S1 | Sky zenith (overcast night) | `#070B14` | `#0A080F` |
| S1 | Sky horizon | `#0E1628` | `#131729` |
| S1 | Horizon toward the town (sodium-lit cloud base) | `#231E24` | `#2A1F21` |
| S1 | Town lights (soft sprites, fog-free) | `#CE8058` (nearest reachable: this grade caps saturation) | `#F87A00` |
| S1 | Rain streaks inside the lamp cone | `#9AA8B8` | `#A0ACBF` |
| S1 | Rain streaks elsewhere | `#1E2632` | `#242831` |
| S1 | Lamp cone (fake volumetric) core | `#3A4658` | `#3F4756` |
| S2 | Fog colour | `#0A0F18` | `#0D0E16` |
| S2 | Sky | `#05080F` | `#060406` |
| S2 | Radio dial glow | `#D9926F` (nearest reachable: this grade caps saturation) | `#FF7B00 @ +0.47` |
| S2 | Sodium lamp heads passing | `#EFB78F` (nearest reachable: this grade caps saturation) | `#FF8300 @ +1.22` |
| S3 | Sky zenith | `#08101F` | `#16192B` |
| S3 | Sky horizon (away from the moon) | `#111B30` | `#242A43` |
| S3 | Sky 10 deg around the moon | `#26344F` | `#414B69` |
| S3 | Moon halo (disc of 6 deg) | `#5A6A88` | `#818DB0` |
| S3 | Fog colour above the clouds | `#111B30` | `#242A43` |
| S3 | Town underglow patches on the cloud sea | `#6A4630` | `#95612E` |
| S3 | Cloud-entry whiteout fog | `#4A5568` | `#6C7385` |
| S4 | Sky void | `#070A14` | `#13181E` |
| S4 | Haze fog (far colossi dissolve into it) | `#1B2240` | `#383E60` |
| S4 | Violet halo around the tear | `#6B45C8` | `#9163FF @ +0.49` |
| S4 | Violet light shafts (additive, where two overlap) | `#3A2A70` | `#644B9D` |
| S4 | Cloud sea under the tear (tinted) | `#4E4F7A` | `#7A78A6` |
| S4 | Tear edge glow (just outside the core) | `#C9B2FF` | `#9779FF @ +2.43` |
| S5 | Black overlay | `#03030B` (nearest reachable: this grade caps saturation) | `#000000` |
| S5 | Falling motes | `#2A3550` | `#4C5772` |
| S6 | Zenith | `#3E64A6` | `#678BED` |
| S6 | Earth-shadow band (anti-sun horizon) | `#8C98B8` | `#B9C8FF @ +0.15` |
| S6 | Belt of Venus (above the Earth shadow) | `#D9B3B9` | `#FFBEC4 @ +0.97` |
| S6 | Sun-side horizon | `#F2C79A` | `#FFA96B @ +1.86` |
| S6 | Fog colour (average forward horizon) | `#C4B8C0` | `#FFEBF7 @ +0.40` |
| S6 | Sea far below (mirror, deep blue) | `#1C3D63` | `#395A8B` |
| S7a | Snell window (the sky seen from below) | `#E6F3F8` | `#D8EFFF @ +2.03` |
| S7a | Water fog, shallow | `#2B7FA8` | `#60A1DF` |
| S7a | God-ray cards (additive result) | `#7FC4DD` | `#8ECBFF @ +0.99` |
| S7a | Surface underside outside the window (total reflection) | `#0F3A5A` | `#324C74` |
| S7b | Water fog, 30-60 m | `#16507A` | `#385D86` |
| S7b | Water fog, deep | `#061A30` | `#152237` |
| S7b | Abyss (looking down, before the palace) | `#02070F` | `#040305` |
| S7b | Plankton (bioluminescent points) | `#8FE8FF` | `#77BAFF @ +1.80` |
| S7b | Palace glow, vermilion 朱 | `#F2583F` (nearest reachable: this grade caps saturation) | `#FF4D00 @ +1.27` |
| S7b | Palace glow, violet 紫贝 | `#8A5CFF` | `#6D48FF @ +1.87` |
| S8 | Ocean ceiling, straight overhead (deep water) | `#10263F` | `#1C304F` |
| S8 | Ocean ceiling near the horizon (mirror) | `#C98A7A` | `#FDA692` |
| S8 | Sky slot at the horizon | `#F2A56B` | `#FF8851 @ +1.34` |
| S8 | Cloud-sea shadows below | `#4A3560` | `#564376` |
| S8 | Fog colour | `#B77F78` | `#DB9790` |
| S8b | Blue-hour sky (the purest 蓝 of the piece) | `#2E4F8A` | `#405796` |
| S8b | Blue-hour horizon | `#6F86B0` | `#8093C8` |
| S9a | Sky zenith 紺 | `#0B1A33` | `#11192D` |
| S9a | Sky horizon | `#16294A` | `#1D2741` |
| S9a | Milky Way, brightest diffuse | `#6F82A0` | `#6A758E` |
| S9a | Sea reflection (mirror, -0.3 EV) | `#0A1428` | `#0F1222` |
| S10 | The 藍白 overlay (full field) | `#E8F1F5` | `#D3EEFF @ +1.45` |
| S11 | Sea in the sky, underside | `#0F2438` | `#11283E` |
| S11 | Amber light pools on the sea | `#B16D4F` (nearest reachable: this grade caps saturation) | `#D56B00` |
| S11 | Fog colour | `#0A0F18` | `#0D0E16` |
| S12 | Sky zenith (breaking cloud) | `#070B14` | `#09080D` |
| S12 | Pre-dawn 藍白 band, 0-4 deg above the horizon | `#8FA6BE` | `#94ABCB` |
| S12 | Fog colour (thin) | `#111B2A` | `#161C29` |
| S12 | Fireflies | `#D7E793` (nearest reachable: this grade caps saturation) | `#DCFF00 @ +0.52` |
| S12 | Town lights (now visible) | `#D28450` (nearest reachable: this grade caps saturation) | `#FD8000` |

### Grade test card: 11 unlit grey patches at 0.18 x 2^k (k = -6..+4); screenshot must match (+-3 codes)

| Profile | -6 | -5 | -4 | -3 | -2 | -1 | +0 | +1 | +2 | +3 | +4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | `#070C12` | `#0D1117` | `#161A1F` | `#23272C` | `#363A3F` | `#50545A` | `#72777D` | `#9BA0A6` | `#C5C9CD` | `#E7E9EC` | `#FEFFFF` |
| S2 | `#070B11` | `#0D1116` | `#16191E` | `#23262A` | `#34383C` | `#4D5055` | `#6D7176` | `#95999E` | `#BFC1C5` | `#E2E4E6` | `#FAFBFD` |
| S3 | `#04090F` | `#060C12` | `#0C1117` | `#161A20` | `#24282D` | `#373C41` | `#52575D` | `#757B82` | `#A0A5AB` | `#CACED3` | `#EBEDF0` |
| S4 | `#05050D` | `#07070F` | `#0B0C13` | `#13141B` | `#202027` | `#32333B` | `#4C4E56` | `#70727B` | `#9C9EA8` | `#C8CBD2` | `#ECEDF2` |
| S6 | `#01060B` | `#05090E` | `#0C0F13` | `#16191C` | `#252628` | `#39393B` | `#535455` | `#767678` | `#A09FA1` | `#C9C8C9` | `#EAE9EA` |
| S7a | `#000C0B` | `#00100F` | `#021616` | `#111F20` | `#222E2E` | `#374143` | `#535D5E` | `#768082` | `#9FA7AA` | `#C7CED0` | `#E8ECED` |
| S7b | `#040A11` | `#080E14` | `#10151B` | `#1B2026` | `#2B3036` | `#42484E` | `#62686F` | `#8A9097` | `#B6BBC1` | `#DDE1E4` | `#F8FAFC` |
| S8 | `#020910` | `#080E13` | `#121519` | `#1F2022` | `#313030` | `#484645` | `#686461` | `#8F8986` | `#B8B3AE` | `#DDD8D4` | `#F7F4F1` |
| S8b | `#060B12` | `#0C1117` | `#14191E` | `#21242A` | `#32353B` | `#494D53` | `#686C73` | `#8E9299` | `#B7BAC0` | `#DCDDE2` | `#F6F7F9` |
| S9a | `#070D13` | `#0E1319` | `#181D23` | `#272B31` | `#3C4047` | `#585D65` | `#7E838B` | `#A9ADB4` | `#D2D5DA` | `#F1F2F5` | `#FFFFFF` |
| S9b | `#101419` | `#1B1E23` | `#2A2D32` | `#3E4247` | `#5B5E63` | `#7F8288` | `#A8ABB0` | `#D0D2D6` | `#EFEFF2` | `#FFFFFF` | `#FFFFFF` |
| S10 | `#0A0A0A` | `#121212` | `#1D1D1D` | `#2B2B2B` | `#3E3E3E` | `#575757` | `#767676` | `#9B9B9B` | `#C0C0C0` | `#E0E0E0` | `#F7F7F7` |
| S11 | `#070B11` | `#0D1116` | `#16191E` | `#23262A` | `#34383C` | `#4D5055` | `#6D7176` | `#95999E` | `#BFC1C5` | `#E2E4E6` | `#FAFBFD` |
| S12 | `#070C12` | `#0D1217` | `#171B20` | `#24282D` | `#373B40` | `#51555A` | `#73777D` | `#9B9FA5` | `#C4C7CC` | `#E6E8EB` | `#FDFEFF` |
