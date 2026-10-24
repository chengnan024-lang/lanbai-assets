// 蓝白 · 第 12 面 → 白 → 第 10 幕 → 白收缩进灯里：驱动（UdonSharp）。
// !!! NOT COMPILED IN UNITY / UdonSharp: Roslyn type-check (Common/Tools~/compile_check/check_cs.sh) + U# stubs only. !!!
//
// Compute-only (总工程师意见 第 1 轮 + 总导演 10-23): this driver never writes PPv2 volumes and never colours the overlay
// itself.  The Director's dispatcher calls LanbaiTick(t) / LanbaiGrade(t); LB_Journey.ApplyGrades is the one writer of
// exposure and of the overlay fill compensation (overlay.rgb = fill x 2^-dEV).  What this driver gives it:
//   LanbaiGrade(t) = {dEV on EXPO_UP, WHITE_SAT weight, WHITE_BLOOM weight, desktop lens multiplier}
//   OverlayAlpha(t), OverlayFillRow(t) (0 = S9b+WHITE_SAT row, 1 = S10, 2 = S11 of calib_final §D), OverlayBreath(t)
//   ShrinkProgress(t, lead) for Lanbai_Overlay v2's direction lobes (10 -> 11: the tubes first, the lamps, the sea).
// Every number comes from Act10_White/WhiteSchedule.json (bible §6·9→10, §6·10, §6·10→11), baked by 蓝白/Build/Act10 White.
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

        [Header("Overlay")]
        public float lWhite = 0.86f;                 // relative luminance of the white the mask goes to (#E8F1F5 desktop)
        public float lWhiteVR = 0.74f;               // #D7E3E8
        public float lSceneMask = 0.30f;             // EvOverlayAlpha's scalar Lscene for the 3-s mask (darkest view, see README)
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
