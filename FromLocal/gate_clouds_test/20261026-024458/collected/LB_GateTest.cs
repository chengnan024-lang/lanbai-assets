// ═══════════════════════════════════════════════════════════════════
//  蓝白 · 触手之门 · Unity 导入测试（2026-10-08）
//  只在测试场景 Assets/Lanbai/Tests/GateTest.unity 里做；主场景和现有系统一概不碰。
//
//  数据源：Assets/Lanbai/Gate/GateLayout_v2.json（云端的门，唯一的数据源）
//          + Gate/README_GateLayout.md、Tear/README_Tear.md（材质表）、Tentacles/README_Tentacles.md（贴图）
//  这个脚本只做"照着 JSON 搭起来"：不改模型、不换贴图、不调颜色 / 雾 / 光的数值。
//  JSON 里没有写、只在 README 里写了规则的（贴图平铺、_VariantDims），按 README 的规则从网格里量出来，写进报告。
//
//  给远程小助手调用（全部返回字符串）：
//    Lanbai.Tests.LB_GateTest.NewScene("")          建空的测试场景 + ReferenceCamera（已有就打开）
//    Lanbai.Tests.LB_GateTest.Build("155.1")        按 JSON 搭门（材质存在 Tests/GateTest_Materials），然后 Apply
//    Lanbai.Tests.LB_GateTest.Apply("155.1")        把时间定在 t：GateRoot、每个实例的位姿、reveal、裂口、全局量
//    Lanbai.Tests.LB_GateTest.Verify("")            核对报告（shader 报错、FBX 结构、布局 FBX 对照、LOD、材质参数）
//    Lanbai.Tests.LB_GateTest.Shoot("cam=U7;t=155.1;w=1920;h=1080;ss=2;file=…png")
//    Lanbai.Tests.LB_GateTest.Perf("cam=U7;t=155.1")  帧时间、draw call、三角面
// ═══════════════════════════════════════════════════════════════════
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using Unity.Profiling;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.PostProcessing;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace Lanbai.Tests
{
    public static partial class LB_GateTest
    {
        public const string SCENE = "Assets/Lanbai/Tests/GateTest.unity";
        public const string GATE = "Assets/Lanbai/Gate";
        public const string TENT = "Assets/Lanbai/Tentacles";
        public const string TEAR = "Assets/Lanbai/Tear";
        public const string MATS = "Assets/Lanbai/Tests/GateTest_Materials";
        public const string MAIN_SCENE = "Assets/Lanbai/Scenes/Lanbai.unity";
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        // ─────────────────────────────────────────────────────────────
        //  极小的 JSON 读取器（Dictionary / List / double / string / bool / null）
        // ─────────────────────────────────────────────────────────────
        sealed class JReader
        {
            readonly string s; int i;
            JReader(string text) { s = text; i = 0; }
            public static object Parse(string text) { var r = new JReader(text); r.Ws(); var v = r.Val(); return v; }
            void Ws() { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }
            object Val()
            {
                Ws();
                if (i >= s.Length) throw new Exception("JSON 意外结束");
                char c = s[i];
                if (c == '{') return Obj();
                if (c == '[') return Arr();
                if (c == '"') return Str();
                if (c == 't' && string.CompareOrdinal(s, i, "true", 0, 4) == 0) { i += 4; return true; }
                if (c == 'f' && string.CompareOrdinal(s, i, "false", 0, 5) == 0) { i += 5; return false; }
                if (c == 'n' && string.CompareOrdinal(s, i, "null", 0, 4) == 0) { i += 4; return null; }
                if (c == 'N' && string.CompareOrdinal(s, i, "NaN", 0, 3) == 0) { i += 3; return double.NaN; }
                return Num();
            }
            Dictionary<string, object> Obj()
            {
                var d = new Dictionary<string, object>();
                i++; Ws();
                if (s[i] == '}') { i++; return d; }
                while (true)
                {
                    Ws(); string k = Str(); Ws();
                    if (s[i] != ':') throw new Exception("JSON：缺冒号 @" + i);
                    i++; d[k] = Val(); Ws();
                    if (s[i] == ',') { i++; continue; }
                    if (s[i] == '}') { i++; return d; }
                    throw new Exception("JSON：对象里意外的字符 @" + i);
                }
            }
            List<object> Arr()
            {
                var a = new List<object>();
                i++; Ws();
                if (s[i] == ']') { i++; return a; }
                while (true)
                {
                    a.Add(Val()); Ws();
                    if (s[i] == ',') { i++; continue; }
                    if (s[i] == ']') { i++; return a; }
                    throw new Exception("JSON：数组里意外的字符 @" + i);
                }
            }
            string Str()
            {
                if (s[i] != '"') throw new Exception("JSON：应该是字符串 @" + i);
                i++;
                var sb = new StringBuilder();
                while (i < s.Length)
                {
                    char c = s[i++];
                    if (c == '"') return sb.ToString();
                    if (c != '\\') { sb.Append(c); continue; }
                    char e = s[i++];
                    switch (e)
                    {
                        case 'n': sb.Append('\n'); break;
                        case 't': sb.Append('\t'); break;
                        case 'r': sb.Append('\r'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'u': sb.Append((char)Convert.ToInt32(s.Substring(i, 4), 16)); i += 4; break;
                        default: sb.Append(e); break;
                    }
                }
                throw new Exception("JSON：字符串没有结束");
            }
            object Num()
            {
                int st = i;
                while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
                if (i == st) throw new Exception("JSON：意外的字符 '" + s[i] + "' @" + i);
                return double.Parse(s.Substring(st, i - st), NumberStyles.Float, IC);
            }
        }

        static Dictionary<string, object> M(object o) { return o as Dictionary<string, object>; }
        static List<object> L(object o) { return o as List<object>; }
        static object G(object o, string k) { var d = M(o); object v; return d != null && d.TryGetValue(k, out v) ? v : null; }
        static bool Has(object o, string k) { var d = M(o); return d != null && d.ContainsKey(k); }
        static float F(object o, float def = 0f) { return o is double ? (float)(double)o : (o is bool ? ((bool)o ? 1f : 0f) : def); }
        static string S(object o) { return o as string; }
        static Vector3 V3(object o)
        {
            var a = L(o);
            return a == null || a.Count < 3 ? Vector3.zero : new Vector3(F(a[0]), F(a[1]), F(a[2]));
        }
        static Vector4 V4(object o)
        {
            var a = L(o);
            var v = Vector4.zero;
            if (a == null) return v;
            for (int k = 0; k < 4 && k < a.Count; k++) v[k] = F(a[k]);
            return v;
        }
        static Quaternion Q(object o)
        {
            var a = L(o);
            if (a == null || a.Count < 4) return Quaternion.identity;
            var q = new Quaternion(F(a[0]), F(a[1]), F(a[2]), F(a[3]));
            float n = Mathf.Sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
            return n > 1e-6f ? new Quaternion(q.x / n, q.y / n, q.z / n, q.w / n) : Quaternion.identity;
        }
        static string Fs(float v, string f = "0.###") { return v.ToString(f, IC); }
        static string Vs(Vector3 v) { return "(" + Fs(v.x, "0.##") + ", " + Fs(v.y, "0.##") + ", " + Fs(v.z, "0.##") + ")"; }

        static Dictionary<string, object> _json;
        static Dictionary<string, object> Json()
        {
            if (_json != null) return _json;
            string p = GATE + "/GateLayout_v2.json";
            if (!File.Exists(p)) throw new Exception("没找到 " + p);
            _json = M(JReader.Parse(File.ReadAllText(p, Encoding.UTF8)));
            return _json;
        }
        static List<object> Instances() { return L(G(Json(), "instances")); }

        // ─────────────────────────────────────────────────────────────
        //  时间轴（README_GateLayout §2；和 JSON timeline.samples_every_0_5_s 核对过：z / y / H / 张开 误差 ≤ 0.05）
        // ─────────────────────────────────────────────────────────────
        static float Cue(string k) { return F(G(G(G(Json(), "timeline"), "cues"), k)); }
        static float U6 { get { return Cue("U6"); } }
        static float U7 { get { return Cue("U7"); } }
        static float U7b { get { return Cue("U7b"); } }
        static float U8 { get { return Cue("U8"); } }
        static float U9 { get { return Cue("U9"); } }
        static float VG { get { return F(G(G(Json(), "timeline"), "v_g_m_per_s"), 59.0164f); } }

        static float SS(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }
        static float HBus(float t)
        {
            if (t <= U6) return 40f;
            if (t < 160.50f) return 40f + 20f * SS((t - U6) / (160.50f - U6));
            return 60f + 90f * SS((t - 160.50f) / (U9 - 160.50f));
        }
        static Vector3 GatePos(float t) { return new Vector3(0f, 150f - HBus(t), VG * (U9 - t)); }
        static float TearOpen(float t)
        {
            if (t <= U6) return 0f;
            if (t < U7) return 0.333f * SS((t - U6) / (U7 - U6));
            return 0.333f + 0.667f * SS((t - U7) / (U8 - U7));
        }
        static float Rip(float t) { return SS((t - U7) / 16f); }

        /// <summary>单调 PCHIP（Fritsch–Carlson，与 scipy 的 PchipInterpolator 一样）过 timeline.tear_H_knots。</summary>
        static float TearH(float t)
        {
            var ks = L(G(G(Json(), "timeline"), "tear_H_knots"));
            int n = ks.Count;
            var x = new double[n]; var y = new double[n];
            for (int k = 0; k < n; k++) { x[k] = F(G(ks[k], "t")); y[k] = F(G(ks[k], "H")); }
            if (t <= x[0]) return (float)y[0];
            if (t >= x[n - 1]) return (float)y[n - 1];
            var h = new double[n - 1]; var dl = new double[n - 1];
            for (int k = 0; k < n - 1; k++) { h[k] = x[k + 1] - x[k]; dl[k] = (y[k + 1] - y[k]) / h[k]; }
            var d = new double[n];
            for (int k = 1; k < n - 1; k++)
            {
                if (dl[k - 1] * dl[k] <= 0) d[k] = 0;
                else
                {
                    double w1 = 2 * h[k] + h[k - 1], w2 = h[k] + 2 * h[k - 1];
                    d[k] = (w1 + w2) / (w1 / dl[k - 1] + w2 / dl[k]);
                }
            }
            d[0] = PchipEdge(h[0], h[1], dl[0], dl[1]);
            d[n - 1] = PchipEdge(h[n - 2], h[n - 3], dl[n - 2], dl[n - 3]);
            int i = 0;
            while (i < n - 2 && t > x[i + 1]) i++;
            double s = (t - x[i]) / h[i];
            double h00 = 2 * s * s * s - 3 * s * s + 1, h10 = s * s * s - 2 * s * s + s, h01 = -2 * s * s * s + 3 * s * s, h11 = s * s * s - s * s;
            return (float)(h00 * y[i] + h10 * h[i] * d[i] + h01 * y[i + 1] + h11 * h[i] * d[i + 1]);
        }
        static double PchipEdge(double h0, double h1, double m0, double m1)
        {
            double dv = ((2 * h0 + h1) * m0 - h0 * m1) / (h0 + h1);
            if (Math.Sign(dv) != Math.Sign(m0)) dv = 0;
            else if (Math.Sign(m0) != Math.Sign(m1) && Math.Abs(dv) > Math.Abs(3 * m0)) dv = 3 * m0;
            return dv;
        }

        /// <summary>关键帧之间 smoothstep（JSON 里所有 keys 的约定）。valueKey = "value" / "x" / "gain"。</summary>
        static float KeyAt(List<object> keys, float t, string valueKey)
        {
            if (keys == null || keys.Count == 0) return 1f;
            float t0 = F(G(keys[0], "t")), v0 = F(G(keys[0], valueKey));
            if (t <= t0) return v0;
            for (int k = 0; k < keys.Count - 1; k++)
            {
                float a = F(G(keys[k], "t")), b = F(G(keys[k + 1], "t"));
                if (t >= a && t <= b)
                {
                    float va = F(G(keys[k], valueKey)), vb = F(G(keys[k + 1], valueKey));
                    return va + (vb - va) * SS((t - a) / Mathf.Max(1e-4f, b - a));
                }
            }
            return F(G(keys[keys.Count - 1], valueKey));
        }

        /// <summary>动画的缓动（每条 anim 的 ease 字段）：ss / trap / beta。</summary>
        static float Ease(object a, float t)
        {
            float t0 = F(G(a, "t0")), t1 = F(G(a, "t1"));
            float s = Mathf.Clamp01((t - t0) / Mathf.Max(1e-4f, t1 - t0));
            string p = S(G(a, "profile")) ?? "ss";
            if (p == "trap")
            {
                float e = F(G(a, "ease_e"), 0.25f), vm = 1f / (1f - e);
                if (s < e) return vm * s * s / (2f * e);
                if (s <= 1f - e) return vm * (s - e / 2f);
                return 1f - vm * (1f - s) * (1f - s) / (2f * e);
            }
            if (p == "beta")
            {
                float b = F(G(a, "beta_b"), 3.5f);
                return 1f - Mathf.Pow(1f - s, b) * (1f + b * s);
            }
            return s * s * (3f - 2f * s);
        }

        /// <summary>实例在 t 的位姿（GateRoot 本地；frame = bus 的是世界）。rise → lean → track → close，和 JSON 的 position_U7b / rotation_U7b 核对过。</summary>
        static void Pose(object it, float t, out Vector3 p, out Quaternion q)
        {
            Vector3 fin = V3(G(it, "position"));
            Quaternion qf = Q(G(it, "rotation_xyzw"));
            p = fin; q = qf;
            bool bus = S(G(it, "frame")) == "bus";
            float vrel = 0f, tref = 0f;
            var anims = L(G(it, "anim"));
            if (anims != null)
                foreach (var a in anims)
                {
                    string ty = S(G(a, "type"));
                    if (ty == "rise")
                    {
                        Vector3 ps = V3(G(a, "position_start"));
                        p = Vector3.LerpUnclamped(ps, fin, Ease(a, t));
                    }
                    else if (ty == "lean")
                    {
                        q = Quaternion.Slerp(Q(G(a, "rotation_start_xyzw")), qf, Ease(a, t));
                    }
                    else if (ty == "track")
                    {
                        var ks = L(G(a, "keys"));
                        if (ks == null || ks.Count == 0) continue;
                        float ta = F(G(ks[0], "t"));
                        if (t < ta) continue;
                        if (t >= F(G(ks[ks.Count - 1], "t"))) { q = Q(G(ks[ks.Count - 1], "rotation_xyzw")); continue; }
                        for (int k = 0; k < ks.Count - 1; k++)
                        {
                            float a0 = F(G(ks[k], "t")), a1 = F(G(ks[k + 1], "t"));
                            if (t >= a0 && t <= a1)
                            {
                                q = Quaternion.Slerp(Q(G(ks[k], "rotation_xyzw")), Q(G(ks[k + 1], "rotation_xyzw")), SS((t - a0) / Mathf.Max(1e-4f, a1 - a0)));
                                break;
                            }
                        }
                    }
                    else if (ty == "close")
                    {
                        if (t > F(G(a, "t0"))) q = Quaternion.Slerp(q, Q(G(a, "rotation_end_xyzw")), Ease(a, t));
                    }
                    else if (ty == "drift")
                    {
                        vrel = F(G(a, "v_rel_m_per_s")); tref = F(G(a, "t_ref"));
                    }
                }
            if (bus)   // 近处 3 条：世界位置 = (x, −h_bus(t) + y, z + v_rel·(t − t_ref))
                p = new Vector3(p.x, -HBus(t) + p.y, p.z + vrel * (t - tref));
        }

        /// <summary>月盘增益（moon.disc_gain_keys；U7b + 1.5 起 2 s 淡出——这次的两个时刻都在淡出之前）。</summary>
        static float MoonDisc(float t)
        {
            float g = KeyAt(L(G(G(Json(), "moon"), "disc_gain_keys")), t, "gain");
            float f0 = U7b + 1.5f;
            if (t > f0) g *= 1f - SS((t - f0) / 2f);
            return g;
        }

        // ─────────────────────────────────────────────────────────────
        //  机位（JSON cameras；unity_euler_deg = (−pitch, yaw, 0)，hfov 是水平视角）
        // ─────────────────────────────────────────────────────────────
        public struct Cam { public string name; public float t, hfov, aspect; public Vector3 eye, fwd; public bool shell; }
        static Cam GetCam(string name)
        {
            var c = G(G(Json(), "cameras"), name);
            if (c == null) throw new Exception("JSON 里没有机位 " + name);
            var cam = new Cam
            {
                name = name,
                t = F(G(c, "t")),
                hfov = F(G(c, "hfov_deg"), 90f),
                aspect = F(G(c, "aspect"), 1.7778f),
                eye = V3(G(c, "eye_bus_relative")),
                shell = G(c, "bus_shell") is bool && (bool)G(c, "bus_shell"),
            };
            Vector3 e = V3(G(c, "unity_euler_deg"));
            cam.fwd = Quaternion.Euler(e) * Vector3.forward;
            return cam;
        }
        static float VFov(float hfov, float aspect) { return 2f * Mathf.Rad2Deg * Mathf.Atan(Mathf.Tan(0.5f * hfov * Mathf.Deg2Rad) / aspect); }

        // ─────────────────────────────────────────────────────────────
        //  小工具
        // ─────────────────────────────────────────────────────────────
        static Dictionary<string, string> Args(string arg)
        {
            var d = new Dictionary<string, string>();
            if (string.IsNullOrEmpty(arg)) return d;
            foreach (var part in arg.Split(';'))
            {
                int k = part.IndexOf('=');
                if (k > 0) d[part.Substring(0, k).Trim()] = part.Substring(k + 1).Trim();
                else if (part.Trim().Length > 0) d[part.Trim()] = "";
            }
            return d;
        }
        static float ArgF(Dictionary<string, string> a, string k, float def)
        {
            string v; float f;
            return a.TryGetValue(k, out v) && float.TryParse(v, NumberStyles.Float, IC, out f) ? f : def;
        }
        static float ParseT(string arg, float def)
        {
            float f;
            if (!string.IsNullOrEmpty(arg) && float.TryParse(arg.Trim(), NumberStyles.Float, IC, out f)) return f;
            var a = Args(arg);
            return ArgF(a, "t", def);
        }
        static Color Hex(string h)
        {
            Color c;
            return ColorUtility.TryParseHtmlString(h, out c) ? c : Color.magenta;
        }
        static Transform FindDeep(Transform t, string name)
        {
            if (t.name == name) return t;
            for (int k = 0; k < t.childCount; k++) { var r = FindDeep(t.GetChild(k), name); if (r != null) return r; }
            return null;
        }
        static GameObject Root(string name)
        {
            foreach (var g in SceneManager.GetActiveScene().GetRootGameObjects()) if (g.name == name) return g;
            return null;
        }
        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
        static void RequireTestScene()
        {
            var sc = SceneManager.GetActiveScene();
            if (sc.path == SCENE) return;
            if (!File.Exists(SCENE)) throw new Exception("测试场景还没建：先调 NewScene");
            if (sc.isDirty && !string.IsNullOrEmpty(sc.path)) throw new Exception("当前场景 " + sc.path + " 有没保存的改动——不替它保存也不丢掉，先停下");
            EditorSceneManager.OpenScene(SCENE, OpenSceneMode.Single);
        }
    }
}
