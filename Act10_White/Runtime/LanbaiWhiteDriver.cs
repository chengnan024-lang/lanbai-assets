// 蓝白 · 第 12 面 → 白 → 第 10 幕 → 白收缩进灯里：驱动（UdonSharp）。
// !!! NOT COMPILED IN UNITY / UdonSharp: Roslyn type-check (Common/Tools~/compile_check/check_cs.sh) + U# stubs only. !!!
//
// Exposure: compute-only (总工程师意见 第 1 轮 + 总导演 10-23). This driver never writes PPv2 volumes:
//   LanbaiGrade(t) = {dEV on EXPO_UP, WHITE_SAT weight, WHITE_BLOOM weight, desktop lens multiplier}, summed by the
//   dispatcher; LB_Journey.ApplyGrades is the one writer of exposure.
// Overlay: this driver OWNS Lanbai_Overlay v2 inside its window (Overlay/README_Overlay.md §2-§3: each act's driver calls
//   Set* every frame, Hide() when done; review r1 #2): the 3-s mask, the 29.15-s white with its breath, the shrink into
//   the lamps (lobes: tubes 0 s, street lamps +1.5 s, the sea +3 s; the rest +3 s).  The fill compensation 2^-dEV is
//   done by the overlay component from the dEV passed in, which is this driver's own dEV (in this window the white is
//   the only exposure event).
// Needs Director v1.3 (W4): LanbaiSpawnFade(since) before every LanbaiTick, LanbaiOverlayWindow(), LanbaiWritesAtmosphere().
// Every number comes from Act10_White/WhiteSchedule.json (bible §6·9→10, §6·10, §6·10→11): the field defaults ARE those numbers.
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

namespace Lanbai.Act10
{
    [UdonBehaviourSyncMode(BehaviourSyncMode.None)]
    public class LanbaiWhiteDriver : UdonSharpBehaviour
    {
        [Header("Labels (timeline s, WhiteSchedule.json labels)")]
        public float tMirror12 = 1137.58f;
        public float tImpactEnd = 1138.78f;
        public float tSwellEnd = 1144.78f;
        public float tMaskStart = 1144.11f;          // C1 = B (总导演 10-25), softened 10-25: side-up +30 deg 1 s <= 0.95 EV
        public float tF16 = 1149.31f;
        public float tSilenceEnd = 1178.46f;
        public float tShrinkEnd = 1186.46f;

        [Header("Curves (linear knots)")]
        public float[] evT = new float[] { 1137.58f, 1138.78f, 1144.78f, 1146.31f, 1149.31f };
        public float[] evV = new float[] { 0f, 1f, 2.4f, 2.4f, 2.4f };
        public float[] satT = new float[] { 1137.58f, 1138.78f, 1144.78f };
        public float[] satV = new float[] { 0f, 0.42f, 1f };
        public float[] bloomT = new float[] { 1137.58f, 1138.78f, 1144.78f, 1146.31f, 1149.31f };
        public float[] bloomV = new float[] { 0f, 0.5f, 1f, 1f, 0f };
        public float lensFadeStart = 1138.78f;
        public float lensFadeEnd = 1144.78f;

        [Header("Overlay (Lanbai_Overlay v2; directions of the 10 -> 11 lobes come from act 11's layout)")]
        public LanbaiOverlay overlay;
        public Vector3[] lobeDir = new Vector3[] { new Vector3(0f, 0.6f, 0.8f), new Vector3(-1f, 0.15f, 0f), new Vector3(0f, 1f, 0f) };   // street lamps on the LEFT shoulder (bible act 11; M-10)
        public float[] lobeHalfAngle = new float[] { 30f, 40f, 35f };
        public float[] lobeLead = new float[] { 0f, 1.5f, 3f };
        public float leadElse = 3f;
        public Color fillMaskDesktop = new Color(0.998257f, 1.355517f, 1.484524f, 1f);
        public Color fillMaskVR = new Color(0.693643f, 0.960718f, 1.042466f, 1f);
        public Color fillWhiteDesktop = new Color(1.780479f, 2.331652f, 2.675855f, 1f);
        public Color fillWhiteVR = new Color(1.157995f, 1.549016f, 1.777685f, 1f);
        public Color fillShrinkDesktop = new Color(1.528658f, 2.078365f, 2.297397f, 1f);
        public Color fillShrinkVR = new Color(1.040287f, 1.442772f, 1.580083f, 1f);
        public float lWhite = 0.86f;                 // relative luminance of the white the mask goes to (#E8F1F5 desktop)
        public float lWhiteVR = 0.74f;               // #D7E3E8
        public float lSceneMask = 0.06f;             // EvOverlayAlpha's Lscene for the mask: the DARKEST view measured (side-up +30 deg, L 0.058-0.060; C1)
        public float maskSeconds = 5.2f;             // 1144.11 -> 1149.31 for every direction outside the forward lobe (full white at F16)
        public Vector3 maskLobeDir = new Vector3(0f, 0.1f, 1f);   // forward (the bus's travel direction, +6 deg)
        public float maskLobeHalfAngle = 25f;
        public float maskLobeLead = 1.00f;           // forward first shows the white at 1146.32 (on the beat); 0.31 EV left at the F16 cut
        public float lScene11 = 0.012f;              // act 11 APL 30 -> relative luminance
        public float breathAmount = 0.02f;
        public float breathHz = 0.1f;
        public float shrinkSeconds = 5f;             // each direction; lobes lead 0 / 1.5 / 3 s -> 8 s in all
        public float afterSilenceEV = 1f;
        public float afterSilenceDecay = 4f;

        [Header("Late joiners (总导演终审 r3 #4: the spawn fade first, then black -> white at <= 0.85 EV/s)")]
        public float joinFromL = 0.004f;             // the black the joiner's ramp starts from (EvOverlayAlpha's floor)
        public float joinMaxEVps = 0.8f;             // <= 0.85 (D-43) with margin: log2(0.86 / 0.004) / 0.8 = 9.7 s on desktop
        public float lBrightest11 = 1.0f;            // W2: the brightest non-white view of act 11 (relative luminance); 1.0 until act 11 gives Lb
        public float joinMargin = 0.5f;              // D-43 #7: the window ends a full rise + this after the last hand-over

        [Header("Fog (M-9: bible 10 -> 11; RenderSettings, Exponential only)")]
        public bool writeRenderSettings = true;      // Director v1.1: this driver writes fog in its window (F16 -> the shrink's end)
        public Color fogWhite = new Color(0.827f, 0.933f, 1f, 1f);       // #D3EEFF, the white's fog
        public float fogWhiteDensity = 0.2f;
        public Color fog11 = new Color(0.051f, 0.059f, 0.082f, 1f);      // #0D0F15, act 11's night fog (bible act 11 atmosphere)
        public float fog11Density = 0.006f;

        private float[] grade = new float[4];
        private bool isVR;
        private bool vrKnown;
        private float spawnSince = 1e6f;             // seconds since the local spawn fade ended (-1 while it runs); no call = long ago
        private float sinceIn = 1e6f;                // what the dispatcher last passed
        private float prevT = -1f;
        private int zeroFrames;

        // Director v1.2 (总导演 10-25, like 门内 and act 6): the dispatcher calls this before every LanbaiTick with the
        // seconds since LB_Journey's spawn fade ended, latched by the dispatcher; -1 while it runs. While it runs this
        // driver writes no overlay (the spawn fade owns it; under our overlay the dispatcher holds the spawn black).
        public void LanbaiSpawnFade(float since)
        {
            sinceIn = since;
        }

        // W3: a Director that clamps since at 0 and latches once would hold every player at "just joined" forever; two frames
        // in a row with since == 0 while t moves = the latch is broken: treat it as long ago
        private void UpdateSince(float t)
        {
            if (sinceIn == 0f && prevT >= 0f && t != prevT)
                zeroFrames++;
            else if (sinceIn != 0f)
                zeroFrames = 0;
            spawnSince = zeroFrames >= 2 ? 1e6f : sinceIn;
            prevT = t;
        }

        // the rise from black to act 11 (W2: built for act 11's BRIGHTEST non-white view, not its APL)
        private float SceneRampSeconds()
        {
            return Mathf.Log(Mathf.Max(lBrightest11, joinFromL * 1.01f) / joinFromL, 2f) / joinMaxEVps;
        }

        // control ends once a player handed over at the shrink's end has been fully raised (+ margin)
        public float[] LanbaiWindow()
        {
            return new float[] { tMirror12 - 1f, tShrinkEnd + SceneRampSeconds() + joinMargin };
        }

        // D-43 #7: report the overlay window only up to the last hand-over this driver can still raise completely (its own
        // control end - one full rise - margin = the shrink's end). Later joiners belong to LB_Journey's fade.
        public float[] LanbaiOverlayWindow()
        {
            return new float[] { tMaskStart, tShrinkEnd };
        }

        public bool LanbaiWritesAtmosphere()
        {
            return writeRenderSettings;
        }

        public void LanbaiActivate(bool on)
        {
            lobesSet = false;                       // D-33 #6: everything is rebuilt from t on the next tick (late joiners, scrubbing)
            maskLobeSet = false;
            if (!on)
                Release();                          // only if WE hold the overlay (review r2 #1: never clear the spawn black)
        }

        public void LanbaiTick(float t)
        {
            if (!vrKnown)
            {
                VRCPlayerApi lp = Networking.LocalPlayer;
                if (lp != null)
                {
                    isVR = lp.IsUserInVR();
                    vrKnown = true;
                }
            }
            UpdateSince(t);
            DriveOverlay(t);                        // after the VR check: the first frame already uses the right white
            DriveFog(t);
        }

        public float[] LanbaiGrade(float t)
        {
            if (t < tMirror12 || t > tSilenceEnd + afterSilenceDecay)
                return null;
            float ev, sat, bloom, lens;
            if (t < tF16)
            {
                ev = Lin(evT, evV, t);
                sat = Lin(satT, satV, t);
                bloom = Lin(bloomT, bloomV, t);
                lens = 1f - Mathf.Clamp01((t - lensFadeStart) / (lensFadeEnd - lensFadeStart));
            }
            else if (t < tSilenceEnd)
            {
                ev = 0f; sat = 0f; bloom = 0f; lens = 0f;          // act 10: S10 neutral, the overlay carries the colour
            }
            else
            {
                // 10 -> 11: hard cut S10 -> S11 under the full mask, +1 EV with the fill x 2^-1 (white unchanged), then decay
                ev = afterSilenceEV * Mathf.Clamp01(1f - (t - tSilenceEnd) / afterSilenceDecay);
                sat = 0f; bloom = 0f; lens = 1f;
            }
            grade[0] = ev; grade[1] = sat; grade[2] = bloom; grade[3] = lens;
            return grade;
        }

        // ---------------------------------------------------------------------------------------- overlay
        private bool lobesSet;
        private bool maskLobeSet;
        private bool ownsOverlay;                   // set by our own Set*; we Hide() only what we drew (review r2 #1)

        private void Release()
        {
            if (!ownsOverlay || overlay == null)
                return;
            overlay.ClearLobes();
            overlay.SetBreath(0f);
            overlay.Hide();
            ownsOverlay = false;
            lobesSet = false;
            maskLobeSet = false;
        }

        private void DriveOverlay(float t)
        {
            if (overlay == null)
                return;
            float lw = isVR ? lWhiteVR : lWhite;
            float tJoinReady = t - spawnSince;      // the latched end of the spawn fade, on the timeline
            bool joinedLate = tJoinReady >= tMaskStart;
            float rampT = Mathf.Log(lw / joinFromL, 2f) / joinMaxEVps;
            // D-43: a joiner whose rise to the white would run into the shrink (or who joined in it) stays black until the
            // shrink is over, then rises EV-linearly from black to act 11: ONE brightening, never white then a drop
            bool toScene = joinedLate && tJoinReady + rampT > tSilenceEnd;
            float sceneRampT = SceneRampSeconds();
            float t0s = Mathf.Max(tShrinkEnd, tJoinReady);   // W1: the rise to act 11 starts at the hand-over, never earlier
            if (spawnSince < 0f)
                return;                             // W5: the spawn black is the dispatcher's: neither draw nor Hide
            if (t < tMaskStart || (!toScene && t >= tShrinkEnd) || (toScene && t >= t0s + sceneRampT))
            {
                Release();                          // outside our parts: write nothing (we let go only of what we drew)
                return;
            }
            if (toScene)
            {
                ownsOverlay = true;
                if (lobesSet) { overlay.ClearLobes(); lobesSet = false; }
                overlay.SetBreath(0f);
                // fully black while the white / the shrink is behind it; from the shrink's end a black veil that starts at the
                // floor (0.004) and lets act 11 up EV-linearly at <= joinMaxEVps (every view rises by the same EV)
                if (t < t0s)
                    overlay.SetFlat(Color.black, 1f, 0f);
                else
                    overlay.SetCurve(Color.black, 0f, t - t0s, sceneRampT, joinFromL, lBrightest11, lBrightest11, 0f);
                return;
            }
            bool ramping = joinedLate && t < tJoinReady + rampT;
            ownsOverlay = true;
            if (t < tSilenceEnd && lobesSet)
            {
                overlay.ClearLobes();               // scrubbed back from the shrink (F5)
                lobesSet = false;
                maskLobeSet = false;
            }
            if ((ramping || t >= tF16) && maskLobeSet)
            {
                overlay.ClearLobes();               // the mask's forward lobe is only for the mask
                maskLobeSet = false;
            }
            overlay.SetBreath(0f);                  // the breath is applied here, phased by t, not by the shader's _Time (F5)
            if (ramping)
            {
                // opaque the whole time (whatever is behind stays hidden); the FILL goes from black to the white,
                // EV-linear: fill x (floor / white)^(1 - x). The rise is >= 8.9 s, so it always ends after F16, where the
                // normal state is the flat white at alpha 1: no seam.
                bool inMask = t < tF16;
                Color f = inMask ? overlay.PickFill(fillMaskDesktop, fillMaskVR) : overlay.PickFill(fillWhiteDesktop, fillWhiteVR);
                float x = Mathf.Clamp01((t - tJoinReady) / rampT);
                float k = Mathf.Pow(joinFromL / lw, 1f - x);
                overlay.SetFlat(f * (Breath(t) * k), 1f, inMask ? Lin(evT, evV, t) : 0f);
            }
            else if (t < tF16)
            {
                // the mask (C1 = B): ONE curve built for the darkest view (Lscene 0.06, E17), 4.5 s from the in-breath for
                // every direction, the forward lobe 0.46 s behind (forward first shows white at 1146.32, on the beat)
                if (!maskLobeSet)
                {
                    overlay.ClearLobes();
                    overlay.SetLobe(0, maskLobeDir.normalized, maskLobeHalfAngle, maskLobeLead);
                    overlay.SetLeadElse(0f, 30f);
                    maskLobeSet = true;
                }
                overlay.SetCurve(overlay.PickFill(fillMaskDesktop, fillMaskVR), Lin(evT, evV, t), t - tMaskStart, maskSeconds, lSceneMask, lw, lSceneMask, lw);
            }
            else if (t < tSilenceEnd)
            {
                overlay.SetFlat(overlay.PickFill(fillWhiteDesktop, fillWhiteVR) * Breath(t), 1f, 0f);
            }
            else
            {
                if (!lobesSet)
                {
                    maskLobeSet = false;
                    overlay.ClearLobes();
                    for (int i = 0; i < 3 && i < lobeDir.Length; i++)
                        overlay.SetLobe(i, lobeDir[i].normalized, lobeHalfAngle[i], lobeLead[i]);
                    overlay.SetLeadElse(leadElse, 30f);
                    lobesSet = true;
                }
                float dEV = afterSilenceEV * Mathf.Clamp01(1f - (t - tSilenceEnd) / afterSilenceDecay);
                overlay.SetCurve(overlay.PickFill(fillShrinkDesktop, fillShrinkVR), dEV, t - tSilenceEnd, shrinkSeconds, lw, lScene11, lScene11, lw);
            }
        }

        // M-9 (bible 10 -> 11): the white's fog (#D3EEFF, 0.2) from F16 under the full white; at 1178.46, under the full mask,
        // a hard cut to act 11's night fog (#0D0F15, 0.006: occluded, so no cross-fade is needed); held to the shrink's end,
        // where act 11 takes RenderSettings over. Outside [F16, shrink end) this driver never touches RenderSettings.
        private void DriveFog(float t)
        {
            if (!writeRenderSettings || t < tF16 || t >= tShrinkEnd)
                return;
            if (t < tSilenceEnd)
            {
                RenderSettings.fogColor = fogWhite;
                RenderSettings.fogDensity = fogWhiteDensity;
            }
            else
            {
                RenderSettings.fogColor = fog11;
                RenderSettings.fogDensity = fog11Density;
            }
        }

        private float Breath(float t)
        {
            return 1f + breathAmount * Mathf.Sin(6.2831853f * breathHz * (t - tF16));
        }

        public static float EvOverlayAlpha(float x, float lFrom, float lTo, float ls, float lo)
        {
            const float Floor = 0.004f;
            float a = Mathf.Max(lFrom, Floor);
            float b = Mathf.Max(lTo, Floor);
            float l = a * Mathf.Pow(b / a, Mathf.Clamp01(x));
            return Mathf.Clamp01((ls - l) / (ls - lo));
        }

        public float OverlayAlpha(float t)
        {
            float lw = isVR ? lWhiteVR : lWhite;
            if (t < tMaskStart)
                return 0f;
            if (t < tF16)
                return EvOverlayAlpha((t - tMaskStart) / maskSeconds, lSceneMask, lw, lSceneMask, lw);   // outside the forward lobe
            if (t < tSilenceEnd)
                return 1f;
            return ShrinkAlpha(t, 0f);
        }

        // alpha of the shrinking white for a direction that leads by `lead` seconds (Overlay v2 lobes: 0, 1.5, 3 s)
        public float ShrinkAlpha(float t, float lead)
        {
            float lw = isVR ? lWhiteVR : lWhite;
            float x = Mathf.Clamp01((t - tSilenceEnd - lead) / shrinkSeconds);
            return 1f - EvOverlayAlpha(x, lw, lScene11, lw, lScene11);
        }

        public int OverlayFillRow(float t)
        {
            if (t < tF16) return 0;
            if (t < tSilenceEnd) return 1;
            return 2;
        }

        public float OverlayBreath(float t)
        {
            if (t < tF16 || t >= tSilenceEnd)
                return 1f;
            return 1f + breathAmount * Mathf.Sin(6.2831853f * breathHz * (t - tF16));
        }

        public bool IsVR()
        {
            return isVR;
        }

        private float Lin(float[] xs, float[] ys, float t)
        {
            if (t <= xs[0]) return ys[0];
            for (int i = 0; i < xs.Length - 1; i++)
                if (t <= xs[i + 1])
                    return Mathf.Lerp(ys[i], ys[i + 1], (t - xs[i]) / Mathf.Max(xs[i + 1] - xs[i], 1e-6f));
            return ys[ys.Length - 1];
        }
    }
}
