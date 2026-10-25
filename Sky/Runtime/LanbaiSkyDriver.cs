// 蓝白 · 天空的驱动（UdonSharp）：按时间轴切换 / 淡变天空预设。
// !!! NOT COMPILED IN UNITY / UdonSharp: Roslyn type-check (Common/Tools~/compile_check/check_cs.sh) only. !!!
//
// Interface (CONTROL_总控.md §5): the Director's dispatcher calls LanbaiTick(t) every frame inside LanbaiWindow(),
// LanbaiActivate(on) only under occlusion. ONE writer per act (Sky/README_Sky.md §「幕 → 驱动」): a span of the
// timeline whose sky an act's own driver writes (e.g. act 9 from 1001.21) is simply not covered by this driver's
// entries, so the two never write the same frame.
//   presets[i] is current on [presetT0[i], presetT1[i]); it fades in from presets[i - 1] over fadeSec[i] seconds after
//   presetT0[i] (smoothstep; 0 = a cut, which must sit under occlusion). Outside every entry it writes nothing.
// Start() applies presets[0] (the t = 0 sky), so the first frame is right before the dispatcher runs.
using UdonSharp;
using UnityEngine;

namespace Lanbai.Sky
{
    [UdonBehaviourSyncMode(BehaviourSyncMode.None)]
    public class LanbaiSkyDriver : UdonSharpBehaviour
    {
        public GameObject root;
        public LanbaiSkyPreset[] presets;
        public float[] presetT0;
        public float[] presetT1;
        public float[] fadeSec;

        private int lastIndex = -2;
        private bool lastWasFade;
        private bool valid;

        void Start()
        {
            // the four arrays come from Sky/SkyPresets.json 'drivers' (蓝白/Sky/Build Sky); a mismatch would throw in
            // LanbaiTick and stop this behaviour for the whole show: refuse to run instead (tech r2 #3)
            int n = (presets != null) ? presets.Length : 0;
            valid = n > 0 && presetT0 != null && presetT1 != null && fadeSec != null
                    && presetT0.Length == n && presetT1.Length == n && fadeSec.Length == n;
            if (!valid)
            {
                Debug.LogError("[LanbaiSkyDriver] " + name + ": presets / presetT0 / presetT1 / fadeSec lengths differ or are empty: not running (re-run 蓝白/Sky/Build Sky)");
                return;
            }
            if (presets[0] != null)
                presets[0].Apply();
        }

        public float[] LanbaiWindow()
        {
            // ONE continuous span per instance (acts 1-3, acts 11-12 are two instances): the dispatcher hands the
            // RenderSettings over by these windows, so a window must not cover acts this driver does not write
            if (presetT0 == null || presetT0.Length == 0 || presetT1 == null || presetT1.Length != presetT0.Length)
                return new float[] { 0f, 0f };
            float a = presetT0[0], b = presetT1[0];
            for (int i = 1; i < presetT0.Length; i++)
            {
                a = Mathf.Min(a, presetT0[i]);
                b = Mathf.Max(b, presetT1[i]);
            }
            return new float[] { a, b };
        }

        public void LanbaiActivate(bool on)
        {
            // other acts own the shared globals while this driver is off: coming back to the same preset index must
            // write its whole state again (阿白, Unity check 2026-10-25: from acts 8 / 9 back to 0 the early sky kept the
            // later values; FromLocal/sky_delivery/20261025-1012)
            if (on) { lastIndex = -2; lastWasFade = false; }
            if (root != null)
                root.SetActive(on);
        }

        public int IndexAt(float t)
        {
            int idx = -1;
            for (int i = 0; i < presetT0.Length; i++)
                if (t >= presetT0[i] && t < presetT1[i])
                    idx = i;                       // the later entry wins where two touch
            return idx;
        }

        public void LanbaiTick(float t)
        {
            if (!valid)
                return;
            int i = IndexAt(t);
            if (i < 0 || presets[i] == null)
            {
                lastIndex = -1;
                return;
            }
            float f = fadeSec[i];
            bool fading = i > 0 && presets[i - 1] != null && f > 0f && t < presetT0[i] + f;
            if (fading)
            {
                // entering a fade fresh (a new index, or the first tick after an activation): the source preset in full
                // first. ApplyBlend skips the names both presets share after its first frame, and its first frame only
                // comes with a new pair, so values another act wrote meanwhile would stay. Apply() also resets that.
                if (i != lastIndex)
                    presets[i - 1].Apply();
                float x = Mathf.Clamp01((t - presetT0[i]) / f);
                presets[i - 1].ApplyBlend(presets[i], x * x * (3f - 2f * x));
            }
            else if (i != lastIndex || lastWasFade)
            {
                presets[i].Apply();                // once per change: the globals stay until someone writes them
            }
            lastIndex = i;
            lastWasFade = fading;
        }
    }
}
