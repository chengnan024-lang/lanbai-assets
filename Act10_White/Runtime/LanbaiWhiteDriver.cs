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
        public float tMaskStart = 1146.31f;
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
        public Vector3[] lobeDir = new Vector3[] { new Vector3(0f, 0.6f, 0.8f), new Vector3(1f, 0.15f, 0f), new Vector3(0f, 1f, 0f) };
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
        public float lSceneMask = 0.13f;             // EvOverlayAlpha's scalar Lscene for the 3-s mask: the DARKEST view (looking up, APL ~100; E17, review r2)
        public float lScene11 = 0.012f;              // act 11 APL 30 -> relative luminance
        public float breathAmount = 0.02f;
        public float breathHz = 0.1f;
        public float shrinkSeconds = 5f;             // each direction; lobes lead 0 / 1.5 / 3 s -> 8 s in all
        public float afterSilenceEV = 1f;
        public float afterSilenceDecay = 4f;

        private float[] grade = new float[4];
        private bool isVR;
        private bool vrKnown;

        public float[] LanbaiWindow()
        {
            return new float[] { tMirror12 - 1f, tShrinkEnd + 1f };
        }

        public void LanbaiActivate(bool on)
        {
            lobesSet = false;                       // D-33 #6: everything is rebuilt from t on the next tick (late joiners, scrubbing)
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
            DriveOverlay(t);                        // after the VR check: the first frame already uses the right white
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
        }

        private void DriveOverlay(float t)
        {
            if (overlay == null)
                return;
            float lw = isVR ? lWhiteVR : lWhite;
            if (t < tMaskStart || t >= tShrinkEnd)
            {
                Release();                          // outside our three parts: write nothing unless we must let go
                return;
            }
            ownsOverlay = true;
            if (t < tF16)
            {
                // 3-s mask, ONE curve built for the darkest view (E17); WHITE_BLOOM falls with it (LanbaiGrade)
                overlay.SetBreath(0f);
                overlay.SetCurve(overlay.PickFill(fillMaskDesktop, fillMaskVR), Lin(evT, evV, t), t - tMaskStart, tF16 - tMaskStart, lSceneMask, lw, lSceneMask, lw);
            }
            else if (t < tSilenceEnd)
            {
                overlay.SetBreath(breathAmount);
                overlay.SetFlat(overlay.PickFill(fillWhiteDesktop, fillWhiteVR), 1f, 0f);
            }
            else
            {
                if (!lobesSet)
                {
                    overlay.ClearLobes();
                    for (int i = 0; i < 3 && i < lobeDir.Length; i++)
                        overlay.SetLobe(i, lobeDir[i].normalized, lobeHalfAngle[i], lobeLead[i]);
                    overlay.SetLeadElse(leadElse, 30f);
                    lobesSet = true;
                }
                overlay.SetBreath(0f);
                float dEV = afterSilenceEV * Mathf.Clamp01(1f - (t - tSilenceEnd) / afterSilenceDecay);
                overlay.SetCurve(overlay.PickFill(fillShrinkDesktop, fillShrinkVR), dEV, t - tSilenceEnd, shrinkSeconds, lw, lScene11, lScene11, lw);
            }
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
                return EvOverlayAlpha((t - tMaskStart) / (tF16 - tMaskStart), lSceneMask, lw, lSceneMask, lw);
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
