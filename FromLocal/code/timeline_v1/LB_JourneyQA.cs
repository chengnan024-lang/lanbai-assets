// ═══════════════════════════════════════════════════════════════════
//  蓝白 · 时间轴的检查工具（只在编辑器里用，不进世界）
//    State —— Play 里读一帧的状态：幕、t、声音（在不在放、音量、播放位置、滤波）、后处理权重、雾、各组开关和位置、
//             管灯、车门、路灯、诗（文字、透明度、实际的方位 / 仰角 / 距离 / 字高）。小助手跳到某一秒之后调它，对照圣经。
// ═══════════════════════════════════════════════════════════════════
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using TMPro;
using UnityEngine;
using UnityEngine.Rendering.PostProcessing;
using VRC.Udon;

namespace Lanbai.EditorTools
{
    public static class LB_JourneyQA
    {
        static string F(float v, string fmt = "0.###") { return v.ToString(fmt, CultureInfo.InvariantCulture); }

        static GameObject Find(string name)
        {
            GameObject inactive = null;
            foreach (var t in Resources.FindObjectsOfTypeAll<Transform>())
            {
                if (t == null || t.hideFlags != HideFlags.None || !t.gameObject.scene.IsValid() || t.name != name) continue;
                if (t.gameObject.activeInHierarchy) return t.gameObject;
                if (inactive == null) inactive = t.gameObject;
            }
            return inactive;
        }

        static string On(GameObject g) { return g == null ? "—" : (g.activeInHierarchy ? "开" : (g.activeSelf ? "开(父关)" : "关")); }

        public static string State(string arg)
        {
            var sb = new StringBuilder();
            var jGo = Find("Journey");
            var ub = jGo != null ? jGo.GetComponent<UdonBehaviour>() : null;
            if (ub != null)
                sb.Append("t=").Append(ub.GetProgramVariable("dbgT")).Append("  幕=").Append(ub.GetProgramVariable("dbgSeg")).Append("  诗=").Append(ub.GetProgramVariable("dbgPoem"))
                  .Append("  圣经调色=").Append(ub.GetProgramVariable("useGrades")).Append(" ΔEV=").Append(ub.GetProgramVariable("dbgDEV")).Append(" b=").Append(ub.GetProgramVariable("dbgB")).Append('\n');
            // ── 声音 ──
            foreach (var n in new[] { "Radio", "RadioNoise", "World", "Insects", "Rain", "Splash" })
            {
                var g = Find(n);
                var a = g != null ? g.GetComponent<AudioSource>() : null;
                if (a == null) continue;
                sb.Append(n).Append(a.isPlaying ? " ▶" : " ■").Append(" vol ").Append(F(a.volume, "0.0000"));
                if (a.clip != null && a.isPlaying) sb.Append(" 「").Append(a.clip.name).Append("」 ").Append(F(a.time, "0.00")).Append('s');
                sb.Append(" 3D ").Append(F(a.spatialBlend, "0.00"));
                var lp = g.GetComponent<AudioLowPassFilter>(); if (lp != null) sb.Append(" LP ").Append(F(lp.cutoffFrequency, "0"));
                var hp = g.GetComponent<AudioHighPassFilter>(); if (hp != null) sb.Append(" HP ").Append(F(hp.cutoffFrequency, "0"));
                sb.Append('\n');
            }
            // ── 后处理、雾 ──
            var pr = Find("PostProcess");
            if (pr != null)
            {
                sb.Append("后处理");
                foreach (var v in pr.GetComponentsInChildren<PostProcessVolume>(true))
                    if (v.weight > 0.0005f && v.name != "PP_Base") sb.Append(' ').Append(v.name.Replace("PP_", "")).Append('=').Append(F(v.weight));
                sb.Append('\n');
            }
            sb.Append("雾 ").Append(F(RenderSettings.fogDensity, "0.#####")).Append(" #").Append(ColorUtility.ToHtmlStringRGB(RenderSettings.fogColor))
              .Append("  环境 #").Append(ColorUtility.ToHtmlStringRGB(RenderSettings.ambientLight)).Append('\n');
            // ── 各组 ──
            foreach (var n in new[] { "Road", "RoadRoot", "BusStop", "LightSea", "CloudSea", "Gate", "GateRoot", "Sky", "Deep", "SeaA", "SeaB", "RainIdle", "RainMoving" })
            {
                var g = Find(n);
                if (g == null) continue;
                sb.Append(n).Append(' ').Append(On(g));
                if (g.activeInHierarchy && (n == "RoadRoot" || n == "LightSea" || n == "CloudSea" || n == "SeaA" || n == "SeaB")) sb.Append(" y=").Append(F(g.transform.localPosition.y, "0.#"));
                if (g.activeInHierarchy && (n == "GateRoot" || n == "LightSea")) sb.Append(" z=").Append(F(g.transform.localPosition.z, "0.#"));
                sb.Append("  ");
            }
            sb.Append('\n');
            // ── 路灯：亮着的有几盏、最远的一盏在车前方多远 ──
            int lit = 0; float far = -999f;
            foreach (var t in Resources.FindObjectsOfTypeAll<Transform>())
            {
                if (t == null || !t.gameObject.scene.IsValid() || t.name != "Lamp" || t.parent == null || t.parent.name != "Lamps") continue;
                if (!t.gameObject.activeInHierarchy) continue;
                lit++; far = Mathf.Max(far, t.position.z);
            }
            sb.Append("路灯 ").Append(lit).Append(" 盏").Append(lit > 0 ? "，最远 z=" + F(far, "0") : "");
            // ── 管灯、车门 ──
            sb.Append("   管灯");
            foreach (var t in Resources.FindObjectsOfTypeAll<Light>())
                if (t != null && t.gameObject.scene.IsValid() && t.name == "CabinLight") sb.Append(' ').Append(F(t.intensity, "0.00"));
            var door = Find("Door1");
            if (door != null) sb.Append("   门 ").Append(F(Mathf.DeltaAngle(0f, door.transform.localEulerAngles.y), "0")).Append('°');
            sb.Append('\n');
            // ── 诗：实际摆在哪里（相对主座位的眼睛） ──
            var pg = Find("Poem");
            var tmp = pg != null ? pg.GetComponent<TextMeshPro>() : null;
            if (tmp != null && tmp.color.a > 0.001f)
            {
                Vector3 eye = LB_Udon.HERO_EYE;
                var bus = Find("Bus");
                if (bus != null) eye = bus.transform.TransformPoint(eye);
                Vector3 d = pg.transform.position - eye;
                float dist = d.magnitude;
                float az = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg, el = Mathf.Asin(d.y / Mathf.Max(dist, 0.001f)) * Mathf.Rad2Deg;
                float em = pg.transform.localScale.y;       // 字号 10 = 1 m → 缩放就是 em 的米数
                string txt = Regex.Replace(tmp.text, "<alpha=#00>.*", "", RegexOptions.Singleline);
                txt = Regex.Replace(txt, "<[^>]*>", "").Replace("\n", " / ");
                sb.Append("诗 α ").Append(F(tmp.color.a, "0.00")).Append(" 方位 ").Append(F(az, "0.0")).Append("° 仰角 ").Append(F(el, "0.0")).Append("° 距离 ").Append(F(dist, "0.0"))
                  .Append(" m 字高 ").Append(F(Mathf.Atan2(em, dist) * Mathf.Rad2Deg, "0.00")).Append("° #").Append(ColorUtility.ToHtmlStringRGB(tmp.color)).Append("「").Append(txt).Append("」\n");
            }
            else sb.Append("诗 （无）\n");
            return sb.ToString().TrimEnd();
        }
    }
}
