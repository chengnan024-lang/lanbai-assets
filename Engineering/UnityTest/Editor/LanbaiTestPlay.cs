// 蓝白 · Unity 测试工具 · Play 阶段（工具 1.2.0，D-44 #4；总工程师 2026-10-25）
// !!! NOT COMPILED IN UNITY: Roslyn type-check only (Common/Tools~/compile_check). Never run in Play mode yet. !!!
//
// 测试定义里有 "play" 的（tests/transitions_sweep.json、tests/flicker_probe.json）：编辑模式的那一半照常（预检、开场景、
// build），然后工具把这次运行的状态存进输出文件夹的 _state/，进 Play 模式（ClientSim 照常起来，旅程照常走），在
// EditorApplication.update 里：
//   1. 用旅程的调试跳转把时间轴拨到某一段的开头前 settle_s 秒（默认 LB_Journey.debugSeekSeconds + _DebugSeekVar，
//      和本地的旅程进度面板一样），等时间走到这一段；
//   2. 时间轴每走过一个要拍的时刻，用工具自己的相机（挂在车上：默认 LB_Journey.busRoot 的局部坐标里的
//      LB_Journey.heroEye，主座位）拍一张：遮罩球先挪到这台相机的位置（它平时跟着玩家的头），拍完放回；
//   3. 每张记“要的时刻 / 实际的时刻”（时间轴是实时走的，编辑器一帧拍不完就会晚一点：照实记，不补）、平均对数亮度
//      mean(log2(max(L, 0.004)))（L = 线性亮度，从 8 位 sRGB 读回来换算）和 APL；
//   4. 全部拍完，存结果，退出 Play。reload 以后读回状态，查检查项，照常写报告。
// 编辑器里普通相机，不是头显、不是 SPS-I；时间轴是实时走的，所以每次跑出来的帧时刻会差几毫秒。
// Play 模式中途被人退出、或者 Play 里脚本重新编译（reload）了：这次算工具异常（退出码 3），报告照写。
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Lanbai.Test
{
    [InitializeOnLoad]
    public static class PlayPhase
    {
        public const int Deferred = -1000;
        const string Key = "Lanbai.Test.Play";
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;
        static Run _run;

        static PlayPhase() { EditorApplication.update += Tick; }

        public static bool Wants(Ctx ctx) { return TJson.M(ctx.T("play")) != null; }

        /// <summary>编辑模式这一半做完以后调：存状态、进 Play。返回 Deferred（收尾由 Tick 在退出 Play 以后做）。</summary>
        public static int Begin(Ctx ctx)
        {
            foreach (var e in ctx.undo.RollbackTo(0)) ctx.Warn(e);
            if (ctx.undo.Failed.Count > 0) throw new BlockedException("进 Play 之前有改回失败的：" + string.Join("、", ctx.undo.Failed.ToArray()));
            var plan = Plan.Build(ctx);                      // 定义写错了在编辑模式里就停
            ctx.Info("Play 阶段：" + plan.segs.Count + " 段、" + plan.segs.Sum(s => s.samples.Count) + " 个时刻；进 Play 模式");
            if (Application.isBatchMode) ctx.Warn("批处理下进 Play 模式没在阿白的机器上试过；不行就用菜单跑");
            try { EditorUtility.ClearProgressBar(); } catch { }
            ctx.log.Stop();
            Store.Save(ctx);
            Runner.ClearPending();
            SetState(ctx.outDir, "enter", ctx.mode, ctx.testId, null);
            EditorApplication.isPlaying = true;
            return Deferred;
        }

        static void SetState(string outDir, string phase, string mode, string test, string err)
        {
            var d = new Dictionary<string, object> { { "out", outDir }, { "phase", phase }, { "mode", mode }, { "test", test }, { "at", EditorApplication.timeSinceStartup } };
            if (err != null) d["error"] = err;
            SessionState.SetString(Key, TJson.Write(d, false));
        }

        static void Tick()
        {
            string s = SessionState.GetString(Key, "");
            if (string.IsNullOrEmpty(s)) return;
            Dictionary<string, object> st;
            try { st = TJson.M(TJson.Parse(s)); } catch { SessionState.EraseString(Key); return; }
            string outDir = TJson.S(TJson.G(st, "out")), phase = TJson.S(TJson.G(st, "phase")), mode = TJson.S(TJson.G(st, "mode")), test = TJson.S(TJson.G(st, "test"));
            double at = TJson.G(st, "at") is double ? (double)TJson.G(st, "at") : 0;
            try
            {
                switch (phase)
                {
                    case "enter":
                        if (EditorApplication.isPlaying)
                        {
                            _run = new Run(outDir);
                            SetState(outDir, "capture", mode, test, null);
                        }
                        else if (!EditorApplication.isPlayingOrWillChangePlaymode && EditorApplication.timeSinceStartup - at > 20)
                            SetState(outDir, "finish", mode, test, "没进 Play 模式（编译错误？场景里缺东西？看 Console）");
                        break;
                    case "capture":
                        if (!EditorApplication.isPlaying)
                        {
                            if (!EditorApplication.isPlayingOrWillChangePlaymode)
                                SetState(outDir, "finish", mode, test, "Play 模式中途被退出了（有人点了停止，或者 Unity 自己退出了 Play）");
                            return;
                        }
                        if (_run == null)
                        {
                            // Play 里 reload 了（脚本重新编译）：拍到一半的状态没了
                            SetState(outDir, "exit", mode, test, "Play 模式里编辑器 reload 了（脚本重新编译？），拍到一半的没了");
                            EditorApplication.isPlaying = false;
                            return;
                        }
                        _run.Step();
                        if (_run.done)
                        {
                            string err = _run.Save();
                            _run = null;
                            SetState(outDir, "exit", mode, test, err);
                            EditorApplication.isPlaying = false;
                        }
                        break;
                    case "exit":
                        if (!EditorApplication.isPlaying && !EditorApplication.isPlayingOrWillChangePlaymode)
                            SetState(outDir, "finish", mode, test, TJson.S(TJson.G(st, "error")));
                        break;
                    case "finish":
                        if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling) return;
                        SessionState.EraseString(Key);
                        Finish(outDir, mode, test, TJson.S(TJson.G(st, "error")));
                        break;
                    default:
                        SessionState.EraseString(Key);
                        break;
                }
            }
            catch (Exception e)
            {
                Debug.LogError(LogCapture.TAG + " Play 阶段自己出错：" + e);
                _run = null;
                if (EditorApplication.isPlaying) { SetState(outDir, "exit", mode, test, "Play 阶段的工具代码出错：" + e.GetType().Name + ": " + e.Message); EditorApplication.isPlaying = false; }
                else { SessionState.EraseString(Key); try { Finish(outDir, mode, test, "Play 阶段的工具代码出错：" + e.Message); } catch (Exception e2) { Debug.LogError(LogCapture.TAG + " 收尾也出错：" + e2); } }
            }
        }

        static void Finish(string outDir, string mode, string test, string err)
        {
            var ctx = Store.Load(outDir);
            ctx.log.Start();
            int exit = 0;
            if (!string.IsNullOrEmpty(err))
            {
                ctx.error = err;
                exit = 3;
                if (err.StartsWith("没进 Play", StringComparison.Ordinal)) { ctx.blockedReason = err; ctx.error = null; exit = 2; }
            }
            Runner.FinishFromPlay(ctx, exit, Runner.DoneFor(mode, test, false));
        }

        // ─────────────────────────────────────────────────────────────
        //  要拍什么（从测试定义算出来）
        // ─────────────────────────────────────────────────────────────
        public sealed class Seg
        {
            public string group, id, name, kind, note, variant;
            public float tc, t0, t1;
            public List<float> samples = new List<float>();
            public List<object> toggles = new List<object>();
        }

        public sealed class Plan
        {
            public List<Seg> segs = new List<Seg>();
            public Dictionary<string, object> play, cam;
            public float settle;

            public static Plan Build(Ctx ctx)
            {
                var p = new Plan { play = TJson.M(ctx.T("play")) };
                p.cam = TJson.M(TJson.G(p.play, "camera")) ?? new Dictionary<string, object>();
                p.settle = TJson.F(TJson.G(p.play, "settle_s"), 2f);
                var sw = TJson.M(TJson.G(p.play, "sweep"));
                if (sw != null)
                {
                    var rows = TJson.L(TJson.G(sw, "transitions"));
                    string table = TJson.S(TJson.G(sw, "table"));
                    if (table != null)
                    {
                        string path = Path.Combine(Path.GetDirectoryName(ctx.testFile), table);
                        if (!File.Exists(path)) throw new StepException("sweep.table 找不到：" + path);
                        rows = TJson.L(TJson.G(TJson.Parse(File.ReadAllText(path)), "transitions"));
                    }
                    var only = TJson.Sa(TJson.G(sw, "only"));
                    float pre = TJson.F(TJson.G(sw, "pre_s"), 7f), post = TJson.F(TJson.G(sw, "post_s"), 7f);
                    float cf = TJson.F(TJson.G(sw, "coarse_fps"), 1f), fs = TJson.F(TJson.G(sw, "fine_s"), 1f), ff = TJson.F(TJson.G(sw, "fine_fps"), 10f);
                    foreach (var o in rows)
                    {
                        var r = TJson.M(o);
                        string id = TJson.S(TJson.G(r, "id"));
                        if (id == null || !TJson.Has(r, "t")) throw new StepException("交接表的每一行要有 id 和 t");
                        if (only.Count > 0 && !only.Contains(id)) continue;
                        float tc = TJson.F(TJson.G(r, "t"));
                        var s = new Seg { group = "sweep", id = id, name = TJson.S(TJson.G(r, "name"), id), kind = TJson.S(TJson.G(r, "kind"), "check"), note = TJson.S(TJson.G(r, "note")), tc = tc, t0 = tc - pre, t1 = tc + post };
                        for (int i = 0; i * (1f / cf) <= pre + post + 1e-4f; i++) Add(s.samples, s.t0 + i / cf);
                        for (int i = 0; i * (1f / ff) <= 2f * fs + 1e-4f; i++) Add(s.samples, tc - fs + i / ff);
                        s.samples.Sort();
                        p.segs.Add(s);
                    }
                }
                foreach (var o in TJson.L(TJson.G(p.play, "probes")))
                {
                    var pr = TJson.M(o);
                    string id = TJson.S(TJson.G(pr, "id"), "probe");
                    float t0 = TJson.F(TJson.G(pr, "t0"), 1016f), t1 = TJson.F(TJson.G(pr, "t1"), 1042f), fps = TJson.F(TJson.G(pr, "fps"), 30f);
                    if (t1 <= t0 || fps <= 0) throw new StepException("probe " + id + "：要 t1 > t0、fps > 0");
                    var vars = TJson.L(TJson.G(pr, "variants"));
                    if (vars.Count == 0) vars = new List<object> { new Dictionary<string, object> { { "id", "as_is" } } };
                    foreach (var vo in vars)
                    {
                        var v = TJson.M(vo);
                        var s = new Seg { group = "probe", id = id, variant = TJson.S(TJson.G(v, "id"), "v"), name = TJson.S(TJson.G(v, "why"), ""), kind = "probe", tc = t0, t0 = t0, t1 = t1, toggles = TJson.L(TJson.G(v, "toggles")) };
                        foreach (var tg in s.toggles) Toggles.Validate(TJson.M(tg));
                        int n = Mathf.RoundToInt((t1 - t0) * fps);
                        for (int i = 0; i <= n; i++) s.samples.Add(t0 + i / fps);
                        p.segs.Add(s);
                    }
                }
                if (p.segs.Count == 0) throw new StepException("play 里没有要拍的（sweep 或 probes）");
                return p;
            }

            static void Add(List<float> l, float t) { if (!l.Any(x => Math.Abs(x - t) < 1e-3f)) l.Add(t); }
        }

        // ─────────────────────────────────────────────────────────────
        //  每帧临时改的东西（只在 Play 里；退出 Play 自己就没了）。拍每一张之前都再设一次（旅程可能每帧改回去）
        // ─────────────────────────────────────────────────────────────
        public static class Toggles
        {
            static readonly string[] Kinds = { "set_active", "set_renderer", "set_components_enabled", "field_objects_active", "field_renderers", "udon_var", "global_float", "global_vector" };

            public static void Validate(Dictionary<string, object> t)
            {
                string k = TJson.S(TJson.G(t, "type"));
                if (!Kinds.Contains(k)) throw new StepException("toggle 的 type 只能是 " + string.Join(" / ", Kinds) + "，现在是 " + k);
                if (k == "global_float" || k == "global_vector")
                {
                    string n = TJson.S(TJson.G(t, "name"), "");
                    if (!n.StartsWith("_Udon_", StringComparison.Ordinal)) throw new StepException("global_* 只改 _Udon_ 全局量，现在是 " + n);
                }
            }

            /// <summary>做一遍；返回做了什么（第一次记进步骤）。找不到的：optional 就跳过，不然报错。</summary>
            public static string Apply(Ctx ctx, Dictionary<string, object> t)
            {
                string k = TJson.S(TJson.G(t, "type"));
                bool opt = TJson.B(TJson.G(t, "optional"));
                bool v = TJson.B(TJson.G(t, "value"));
                switch (k)
                {
                    case "set_active":
                        {
                            var tr = Scenes.Find(TJson.S(TJson.G(t, "path")));
                            if (tr == null) { if (opt) return "没有 " + TJson.S(TJson.G(t, "path")) + "（optional，跳过）"; throw new StepException("找不到 " + TJson.S(TJson.G(t, "path"))); }
                            if (tr.gameObject.activeSelf != v) tr.gameObject.SetActive(v);
                            return Scenes.PathOf(tr) + " active = " + v;
                        }
                    case "set_renderer":
                        {
                            var tr = Scenes.Find(TJson.S(TJson.G(t, "path")));
                            var r = tr != null ? tr.GetComponent<Renderer>() : null;
                            if (r == null) { if (opt) return "没有 " + TJson.S(TJson.G(t, "path")) + " 的 Renderer（optional，跳过）"; throw new StepException("找不到 " + TJson.S(TJson.G(t, "path")) + " 的 Renderer"); }
                            r.enabled = v;
                            return Scenes.PathOf(tr) + " Renderer.enabled = " + v;
                        }
                    case "set_components_enabled":
                        {
                            string cn = TJson.S(TJson.G(t, "component"));
                            var ty = Preflight.FindType(cn);
                            if (ty == null) { if (opt) return "没有类型 " + cn + "（optional，跳过）"; throw new StepException("找不到类型 " + cn); }
                            int n = 0; var where = new List<string>();
                            foreach (var c in Object.FindObjectsOfType(ty, true))
                            {
                                var b = c as Behaviour; var r = c as Renderer;
                                if (b != null) { b.enabled = v; n++; where.Add(Scenes.PathOf(b.transform)); }
                                else if (r != null) { r.enabled = v; n++; where.Add(Scenes.PathOf(r.transform)); }
                            }
                            if (n == 0 && !opt) throw new StepException("场景里没有 " + cn);
                            return cn + " × " + n + " enabled = " + v + (where.Count > 0 ? "（" + string.Join("、", where.Take(8).ToArray()) + "）" : "");
                        }
                    case "field_objects_active":
                    case "field_renderers":
                        {
                            // 组件（编辑模式里的 U# 代理，字段就是场景里存的引用）上这些字段指着的物体 / renderer：
                            //   field_objects_active  {"component": "LB_Journey", "fields": ["seaA", "seaB"], "value": false}
                            //   field_renderers       {"component": "LB_Journey", "fields": ["busRenderers"], "enabled": true, "mpb_float": {"_Alpha": 1}}
                            string cn = TJson.S(TJson.G(t, "component"));
                            var ty = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript(cn) ?? Preflight.FindType(cn);
                            var comp = ty != null ? Object.FindObjectsOfType(ty, true).FirstOrDefault() as Component : null;
                            if (comp == null) { if (opt) return "没有 " + cn + "（optional，跳过）"; throw new StepException("找不到 " + cn); }
                            var targets = new List<Object>();
                            foreach (var fn in TJson.Sa(TJson.G(t, "fields")))
                            {
                                var fi = comp.GetType().GetField(fn, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                                if (fi == null) { if (opt) continue; throw new StepException(cn + " 没有字段 " + fn); }
                                object val = fi.GetValue(comp);
                                if (val is Array) { foreach (var o in (Array)val) if (o as Object != null) targets.Add((Object)o); }
                                else if (val as Object != null) targets.Add((Object)val);
                            }
                            int n = 0;
                            var mpbF = TJson.M(TJson.G(t, "mpb_float"));
                            foreach (var o in targets)
                            {
                                if (k == "field_objects_active")
                                {
                                    var go = o is GameObject ? (GameObject)o : o is Component ? ((Component)o).gameObject : null;
                                    if (go != null) { if (go.activeSelf != v) go.SetActive(v); n++; }
                                }
                                else
                                {
                                    var rr = o as Renderer;
                                    if (rr == null) continue;
                                    if (TJson.Has(t, "enabled")) rr.enabled = TJson.B(TJson.G(t, "enabled"));
                                    if (mpbF != null)
                                    {
                                        var mpb = new MaterialPropertyBlock();
                                        rr.GetPropertyBlock(mpb);
                                        foreach (var kv in mpbF) mpb.SetFloat(kv.Key, TJson.F(kv.Value));
                                        rr.SetPropertyBlock(mpb);
                                    }
                                    n++;
                                }
                            }
                            return cn + "." + string.Join("/", TJson.Sa(TJson.G(t, "fields")).ToArray()) + "：" + n + " 个" + (k == "field_objects_active" ? " active = " + v : (TJson.Has(t, "enabled") ? " enabled = " + TJson.B(TJson.G(t, "enabled")) : "") + (mpbF != null ? " MPB " + TJson.Write(mpbF, false) : ""));
                        }
                    case "udon_var":
                        {
                            string cn = TJson.S(TJson.G(t, "component")), var = TJson.S(TJson.G(t, "var"));
                            var ub = Udon.Behaviour(cn);
                            if (ub == null) { if (opt) return "没有 " + cn + "（optional，跳过）"; throw new StepException("找不到 " + cn + " 背后的 UdonBehaviour"); }
                            object val = TJson.G(t, "value");
                            if (val is double) val = (float)(double)val;
                            Udon.Set(ub, var, val);
                            return cn + "." + var + " = " + TJson.Write(TJson.G(t, "value"), false);
                        }
                    case "global_float":
                        Shader.SetGlobalFloat(TJson.S(TJson.G(t, "name")), TJson.F(TJson.G(t, "value")));
                        return TJson.S(TJson.G(t, "name")) + " = " + TJson.F(TJson.G(t, "value")).ToString("0.###", IC);
                    case "global_vector":
                        {
                            var a = TJson.Fa(TJson.G(t, "value")) ?? new float[0];
                            var vec = new Vector4(a.Length > 0 ? a[0] : 0, a.Length > 1 ? a[1] : 0, a.Length > 2 ? a[2] : 0, a.Length > 3 ? a[3] : 0);
                            Shader.SetGlobalVector(TJson.S(TJson.G(t, "name")), vec);
                            return TJson.S(TJson.G(t, "name")) + " = " + vec;
                        }
                }
                throw new StepException("不认识的 toggle " + k);
            }
        }

        // ─────────────────────────────────────────────────────────────
        //  UdonBehaviour（反射：工具不引用 Udon 的程序集）
        // ─────────────────────────────────────────────────────────────
        public static class Udon
        {
            public static Component Behaviour(string proxyType)
            {
                var ty = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript(proxyType) ?? Preflight.FindType(proxyType);
                if (ty == null) return null;
                var proxy = Object.FindObjectsOfType(ty, true).FirstOrDefault() as Component;
                if (proxy == null) return null;
                var util = Preflight.FindType("UdonSharpEditor.UdonSharpEditorUtility");
                var m = util != null ? util.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(x => x.Name == "GetBackingUdonBehaviour" && x.GetParameters().Length == 1) : null;
                if (m != null)
                {
                    try { var ub = m.Invoke(null, new object[] { proxy }) as Component; if (ub != null) return ub; } catch { }
                }
                // 退路：同一个物体上程序名一样的 UdonBehaviour
                var ubt = Preflight.FindType("VRC.Udon.UdonBehaviour");
                return ubt != null ? proxy.GetComponents(ubt).FirstOrDefault() : null;
            }
            public static object Get(Component ub, string name)
            {
                var m = ub.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance).FirstOrDefault(x => x.Name == "GetProgramVariable" && !x.IsGenericMethod && x.GetParameters().Length == 1);
                return m != null ? m.Invoke(ub, new object[] { name }) : null;
            }
            public static void Set(Component ub, string name, object v)
            {
                var m = ub.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance).FirstOrDefault(x => x.Name == "SetProgramVariable" && !x.IsGenericMethod && x.GetParameters().Length == 2);
                if (m == null) throw new StepException("UdonBehaviour 没有 SetProgramVariable");
                m.Invoke(ub, new object[] { name, v });
            }
            public static void Send(Component ub, string ev)
            {
                var m = ub.GetType().GetMethod("SendCustomEvent", BindingFlags.Public | BindingFlags.Instance, null, new[] { typeof(string) }, null);
                if (m == null) throw new StepException("UdonBehaviour 没有 SendCustomEvent");
                m.Invoke(ub, new object[] { ev });
            }
        }

        // ─────────────────────────────────────────────────────────────
        //  Play 里一帧一帧走的拍摄
        // ─────────────────────────────────────────────────────────────
        sealed class Run
        {
            public bool done;
            readonly Ctx ctx;
            readonly Plan plan;
            readonly string clockType, timeVar, seekVar, seekEvent;
            Component clock;
            Capture.Renderer2 r;
            Transform anchor, overlayTr;
            Vector3 eyeLocal; Quaternion rotLocal;
            int w, h, segIdx = -1, sampleIdx;
            string state = "next";
            double stateAt;
            Seg seg;
            SegData data;
            string fatal;
            static readonly float[] Lin = BuildLin();

            public Run(string outDir)
            {
                ctx = Store.Load(outDir);
                ctx.log.Start();
                plan = Plan.Build(ctx);
                var ck = TJson.M(TJson.G(plan.play, "clock")) ?? new Dictionary<string, object>();
                clockType = TJson.S(TJson.G(ck, "component"), "LB_Journey");
                timeVar = TJson.S(TJson.G(ck, "time_var"), "dbgT");
                seekVar = TJson.S(TJson.G(ck, "seek_var"), "debugSeekSeconds");
                seekEvent = TJson.S(TJson.G(ck, "seek_event"), "_DebugSeekVar");
                ctx.Info("Play 阶段开始：" + plan.segs.Count + " 段");
            }

            static float[] BuildLin()
            {
                var l = new float[256];
                for (int i = 0; i < 256; i++) { float c = i / 255f; l[i] = c <= 0.04045f ? c / 12.92f : Mathf.Pow((c + 0.055f) / 1.055f, 2.4f); }
                return l;
            }

            float Now()
            {
                object v = Udon.Get(clock, timeVar);
                return v is float ? (float)v : (v is double ? (float)(double)v : -1f);
            }

            void Setup()
            {
                clock = Udon.Behaviour(clockType);
                if (clock == null) throw new StepException("Play 里找不到 " + clockType + " 背后的 UdonBehaviour（时间轴从它读）");
                // 相机：挂在车上（默认 LB_Journey.busRoot 局部坐标里的 heroEye），朝向 yaw / pitch / roll（度，车的局部坐标）
                var c = plan.cam;
                object rel = TJson.G(c, "relative_to");
                var proxyType = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript(clockType) ?? Preflight.FindType(clockType);
                var proxy = proxyType != null ? Object.FindObjectsOfType(proxyType, true).FirstOrDefault() as Component : null;
                if (rel is string) anchor = Scenes.Find((string)rel);
                else
                {
                    string f = TJson.S(TJson.G(rel, "field"), "busRoot");
                    var fi = proxy != null ? proxy.GetType().GetField(f, BindingFlags.Public | BindingFlags.Instance) : null;
                    anchor = fi != null ? fi.GetValue(proxy) as Transform : null;
                }
                if (anchor == null) throw new StepException("找不到相机挂的车（camera.relative_to）");
                if (TJson.Has(c, "eye")) { var e = TJson.Fa(TJson.G(c, "eye")); eyeLocal = new Vector3(e[0], e[1], e[2]); }
                else
                {
                    var fi = proxy != null ? proxy.GetType().GetField(TJson.S(TJson.G(c, "eye_field"), "heroEye"), BindingFlags.Public | BindingFlags.Instance) : null;
                    if (fi == null || fi.FieldType != typeof(Vector3)) throw new StepException("camera 没写 eye，" + clockType + " 上也没有 heroEye");
                    eyeLocal = (Vector3)fi.GetValue(proxy);
                }
                rotLocal = Quaternion.Euler(-TJson.F(TJson.G(c, "pitch"), 0f), TJson.F(TJson.G(c, "yaw"), 0f), TJson.F(TJson.G(c, "roll"), 0f));
                w = TJson.I(TJson.G(c, "w"), 640); h = TJson.I(TJson.G(c, "h"), 360);
                var cam = new Capture.Cam { id = "play", eye = anchor.TransformPoint(eyeLocal), rot = anchor.rotation * rotLocal, hfov = TJson.F(TJson.G(c, "hfov"), 90f), w = w, h = h, ss = 1, def = c };
                r = new Capture.Renderer2(ctx, cam, w, h, Math.Max(1, TJson.I(TJson.G(c, "ss"), 1)), true);
                if (TJson.B(TJson.G(plan.play, "overlay_follow_camera"), true))
                {
                    var ot = Preflight.FindType("LanbaiOverlay");
                    var oc = ot != null ? Object.FindObjectsOfType(ot, true).FirstOrDefault() as Component : null;
                    overlayTr = oc != null ? oc.transform : null;
                    if (overlayTr == null) ctx.Warn("场景里没有 LanbaiOverlay：遮罩球不挪（拍到的画面里可能没有黑 / 白）");
                }
            }

            public void Step()
            {
                if (done) return;
                try
                {
                    if (clock == null) Setup();
                    double now = EditorApplication.timeSinceStartup;
                    switch (state)
                    {
                        case "next":
                            if (data != null) data.Finish(ctx);
                            data = null;
                            segIdx++;
                            if (segIdx >= plan.segs.Count) { done = true; return; }
                            seg = plan.segs[segIdx];
                            data = new SegData(seg, w, h);
                            foreach (var tg in seg.toggles) data.toggleLog.Add(Toggles.Apply(ctx, TJson.M(tg)));
                            Udon.Set(clock, seekVar, Math.Max(0f, seg.t0 - plan.settle));
                            Udon.Send(clock, seekEvent);
                            sampleIdx = 0;
                            state = "settle"; stateAt = now;
                            EditorUtility.DisplayProgressBar("蓝白测试 · Play", (seg.group == "sweep" ? "交接 " + seg.id + " " + seg.name : "探测 " + seg.id + " / " + seg.variant) + "（" + (segIdx + 1) + "/" + plan.segs.Count + "）", (segIdx + 0.5f) / plan.segs.Count);
                            return;
                        case "settle":
                            {
                                float t = Now();
                                if (t >= seg.samples[0] - 1e-3f) { state = "capture"; goto case "capture"; }
                                if (now - stateAt > plan.settle + 30.0) throw new StepException("跳到 " + (seg.t0 - plan.settle).ToString("0.##", IC) + " 以后时间轴 30 秒没走到 " + seg.samples[0].ToString("0.##", IC) + "（现在 " + t.ToString("0.##", IC) + "）：调试跳转没起作用？");
                                return;
                            }
                        case "capture":
                            {
                                float t = Now();
                                if (sampleIdx >= seg.samples.Count || t > seg.t1 + 0.5f) { data.missed += seg.samples.Count - sampleIdx; state = "next"; return; }
                                if (t < seg.samples[sampleIdx] - 1e-3f)
                                {
                                    if (now - stateAt > (seg.t1 - seg.t0) + plan.settle + 60.0) throw new StepException("时间轴停在 " + t.ToString("0.##", IC) + "，没走到 " + seg.samples[sampleIdx].ToString("0.##", IC));
                                    return;
                                }
                                float target = seg.samples[sampleIdx];
                                int skipped = 0;
                                while (sampleIdx + 1 < seg.samples.Count && seg.samples[sampleIdx + 1] <= t + 1e-3f) { sampleIdx++; skipped++; }
                                data.missed += skipped;
                                foreach (var tg in seg.toggles) Toggles.Apply(ctx, TJson.M(tg));
                                var px = Shoot();
                                data.Add(ctx, target, t, px, Lin);
                                sampleIdx++;
                                return;
                            }
                    }
                }
                catch (Exception e)
                {
                    var inner = e is TargetInvocationException && e.InnerException != null ? e.InnerException : e;
                    if (!(inner is StepException)) ctx.ToolError("Play 阶段", inner);
                    fatal = inner.Message;
                    if (seg != null) ctx.steps.Add(new Dictionary<string, object> { { "phase", "play" }, { "type", seg.group }, { "desc", seg.id + (seg.variant != null ? "/" + seg.variant : "") }, { "status", "error" }, { "error", inner.Message } });
                    if (data != null) { try { data.Finish(ctx); } catch { } data = null; }
                    done = true;
                }
            }

            Color32[] Shoot()
            {
                var pos = anchor.TransformPoint(eyeLocal);
                r.go.transform.position = pos;
                r.go.transform.rotation = anchor.rotation * rotLocal;
                Vector3 old = Vector3.zero;
                if (overlayTr != null) { old = overlayTr.position; overlayTr.position = pos; }
                try { return r.Frame(1); }
                finally { if (overlayTr != null) overlayTr.position = old; }
            }

            /// <summary>存结果（ctx 连同 Play 里的 Console）；返回要当成工具异常的那句话（没有 = null）。</summary>
            public string Save()
            {
                try { EditorUtility.ClearProgressBar(); } catch { }
                if (r != null) r.Dispose();
                PlayReport.Summaries(ctx);
                ctx.log.Stop();
                Store.Save(ctx);
                return fatal;
            }
        }

        /// <summary>一段的数据：每帧的数，缩略图，探测的逐像素统计。</summary>
        sealed class SegData
        {
            readonly Seg seg; readonly int w, h, N;
            public int missed;
            public readonly List<string> toggleLog = new List<string>();
            readonly List<double[]> rows = new List<double[]>();          // target, t, meanLog, apl, diffMean
            readonly List<KeyValuePair<float, Color32[]>> thumbs = new List<KeyValuePair<float, Color32[]>>();
            float[] prevY, lastY; int[] flips; float[] maxDiff;
            readonly List<KeyValuePair<double, string>> top = new List<KeyValuePair<double, string>>();
            const int TW = 160, TH = 90;

            public SegData(Seg s, int w, int h) { seg = s; this.w = w; this.h = h; N = w * h; }

            string Dir { get { return seg.group == "sweep" ? "sweep/" + seg.id : "probe/" + seg.id + "/" + seg.variant; } }

            public void Add(Ctx ctx, float target, float t, Color32[] px, float[] lin)
            {
                double sumLog = 0, sumY = 0;
                var y = new float[N];
                for (int k = 0; k < N; k++)
                {
                    var c = px[k];
                    float L = 0.2126f * lin[c.r] + 0.7152f * lin[c.g] + 0.0722f * lin[c.b];
                    sumLog += Math.Log(Math.Max(L, 0.004f), 2.0);
                    float yy = Img.Luma(c);
                    y[k] = yy; sumY += yy;
                }
                double diffMean = double.NaN;
                if (seg.group == "probe")
                {
                    if (flips == null) { flips = new int[N]; maxDiff = new float[N]; }
                    if (prevY != null)
                    {
                        double sd = 0;
                        var heat = new float[N];
                        for (int k = 0; k < N; k++)
                        {
                            float d = Math.Abs(y[k] - prevY[k]);
                            heat[k] = d; sd += d;
                            if (d > maxDiff[k]) maxDiff[k] = d;
                            if (d > 24f) flips[k]++;
                        }
                        diffMean = sd / N;
                        // 相邻帧差最大的几张（默认 8）原样存下来：差图 + 这一帧
                        if (top.Count < 8 || diffMean > top.Min(x => x.Key))
                        {
                            string name = Dir + "/diff_" + t.ToString("0000.000", CultureInfo.InvariantCulture);
                            Img.SavePng(Img.Heat(heat, y, 64f), w, h, ctx.Out(name + "_heat.png"));
                            Img.SavePng(px, w, h, ctx.Out(name + "_frame.png"));
                            top.Add(new KeyValuePair<double, string>(diffMean, name));
                            if (top.Count > 8)
                            {
                                var drop = top.OrderBy(x => x.Key).First();
                                top.Remove(drop);
                                try { File.Delete(ctx.Out(drop.Value + "_heat.png")); File.Delete(ctx.Out(drop.Value + "_frame.png")); } catch { }
                            }
                        }
                    }
                    prevY = y;
                }
                lastY = y;
                rows.Add(new[] { target, t, sumLog / N, sumY / N, diffMean });
                if (seg.group == "sweep") thumbs.Add(new KeyValuePair<float, Color32[]>(target, Img.Resample(px, w, h, TW, TH)));
            }

            public void Finish(Ctx ctx)
            {
                string pre = seg.group == "sweep" ? "sweep." + seg.id : "probe." + seg.id + "." + seg.variant;
                var rec = new Dictionary<string, object>
                {
                    { "group", seg.group }, { "id", seg.id }, { "variant", seg.variant }, { "name", seg.name }, { "kind", seg.kind }, { "note", seg.note },
                    { "t", (double)seg.tc }, { "t0", (double)seg.t0 }, { "t1", (double)seg.t1 }, { "samples", (double)seg.samples.Count }, { "captured", (double)rows.Count },
                    { "missed", (double)missed }, { "toggles", toggleLog.Cast<object>().ToList() }, { "dir", Dir }
                };
                var csv = new StringBuilder("target_t,t,mean_log2_L,apl,diff_mean\n");
                foreach (var r in rows) csv.AppendLine(string.Join(",", r.Select(x => double.IsNaN(x) ? "" : x.ToString("0.#####", CultureInfo.InvariantCulture)).ToArray()));
                File.WriteAllText(ctx.Out(Dir + "/frames.csv"), csv.ToString(), new UTF8Encoding(false));
                ctx.AddFile(Dir + "/frames.csv");
                ctx.Metric(pre + ".captured", rows.Count);
                ctx.Metric(pre + ".missed", missed, "要拍、但编辑器那一帧已经走过去了的时刻（时间轴是实时走的）");
                if (rows.Count >= 2)
                {
                    // 相邻两张的对数亮度差（只算间隔 ≤ 0.15 s 的）、0.25 / 1 / 2 s 窗口里最多升了多少 EV（圣经 §1.8 的三个窗口，这里是全画面的平均）
                    double maxStep = 0, maxStepAt = 0;
                    for (int i = 1; i < rows.Count; i++)
                    {
                        double dt = rows[i][1] - rows[i - 1][1];
                        if (dt <= 0 || dt > 0.15) continue;
                        double d = Math.Abs(rows[i][2] - rows[i - 1][2]);
                        if (d > maxStep) { maxStep = d; maxStepAt = rows[i][1]; }
                    }
                    ctx.Metric(pre + ".max_step_ev", maxStep, "相邻两张（间隔 ≤ 0.15 s）平均对数亮度 mean(log2(max(L, 0.004))) 的最大差（EV，升降都算）");
                    rec["max_step_at"] = maxStepAt;
                    foreach (var win in new[] { 0.25, 1.0, 2.0 })
                    {
                        double best = 0;
                        for (int i = 0; i < rows.Count; i++)
                            for (int j = i + 1; j < rows.Count && rows[j][1] - rows[i][1] <= win + 1e-6; j++)
                                best = Math.Max(best, rows[j][2] - rows[i][2]);
                        ctx.Metric(pre + ".rise_" + (win == 0.25 ? "025" : win.ToString("0", CultureInfo.InvariantCulture)), best,
                            win.ToString("0.##", CultureInfo.InvariantCulture) + " s 窗口里平均对数亮度最多升了多少 EV（圣经 §1.8：≤ " + (win == 0.25 ? "0.5" : win == 1.0 ? "1.0" : "1.8") + "，那里是每个视向，这里是全画面平均）");
                    }
                    Img.SavePng(PlayReport.Plot(rows, seg), PlayReport.PW, PlayReport.PH, ctx.Out(Dir + "/curve.png"));
                    ctx.AddFile(Dir + "/curve.png");
                }
                if (seg.group == "sweep" && thumbs.Count > 0)
                {
                    float fs = 1.0001f;
                    var coarse = thumbs.Where(x => Math.Abs(x.Key - seg.tc) > fs || Math.Abs((x.Key - seg.t0) - Mathf.Round(x.Key - seg.t0)) < 1e-3f).ToList();
                    var fine = thumbs.Where(x => Math.Abs(x.Key - seg.tc) <= fs).ToList();
                    Img.SavePng(PlayReport.Sheet(coarse.Select(x => x.Value).ToList(), 5, TW, TH, out int cw, out int ch), cw, ch, ctx.Out(Dir + "/strip_1s.png"));
                    Img.SavePng(PlayReport.Sheet(fine.Select(x => x.Value).ToList(), 7, TW, TH, out int fw, out int fh), fw, fh, ctx.Out(Dir + "/strip_fine.png"));
                    ctx.AddFile(Dir + "/strip_1s.png"); ctx.AddFile(Dir + "/strip_fine.png");
                    rec["strip_1s"] = Dir + "/strip_1s.png"; rec["strip_fine"] = Dir + "/strip_fine.png";
                    rec["strip_1s_times"] = coarse.Select(x => (object)(double)x.Key).ToList();
                    rec["strip_fine_times"] = fine.Select(x => (object)(double)x.Key).ToList();
                }
                if (seg.group == "probe" && flips != null && lastY != null)
                {
                    int stepsOver = 0;
                    for (int i = 1; i < rows.Count; i++) if (Math.Abs(rows[i][2] - rows[i - 1][2]) > 0.1) stepsOver++;
                    ctx.Metric(pre + ".steps_over_01ev", stepsOver, "相邻两帧平均对数亮度差 > 0.1 EV 的次数");
                    int flick = flips.Count(x => x >= 4);
                    ctx.Metric(pre + ".flicker_px_frac", flick / (double)N, "这一段里相邻两帧亮度差 > 24（0–255）的次数 ≥ 4 的像素占比（局部的闪看这个和 flicker_count.png）");
                    float mx = Math.Max(4f, flips.Max());
                    Img.SavePng(Img.Heat(flips.Select(x => (float)x).ToArray(), lastY, mx), w, h, ctx.Out(Dir + "/flicker_count.png"));
                    Img.SavePng(Img.Heat(maxDiff, lastY, 128f), w, h, ctx.Out(Dir + "/max_diff.png"));
                    ctx.AddFile(Dir + "/flicker_count.png"); ctx.AddFile(Dir + "/max_diff.png");
                    rec["top_diffs"] = top.OrderByDescending(x => x.Key).Select(x => (object)x.Value).ToList();
                    rec["flicker_count_max"] = (double)flips.Max();
                }
                PlayReport.Records(ctx).Add(rec);
            }
        }

        // ─────────────────────────────────────────────────────────────
        //  运行状态存取（reload 前后）
        // ─────────────────────────────────────────────────────────────
        public static class Store
        {
            static string P(string outDir, string n) { string d = Path.Combine(outDir, "_state"); Directory.CreateDirectory(d); return Path.Combine(d, n); }

            public static void Save(Ctx c)
            {
                var d = new Dictionary<string, object>
                {
                    { "testId", c.testId }, { "testFile", c.testFile }, { "testSha", c.testSha }, { "runId", c.runId }, { "outDir", c.outDir }, { "projectDir", c.projectDir },
                    { "mode", c.mode }, { "test", c.test }, { "started", c.started.ToString("o", IC) }, { "scenePath", c.scenePath }, { "gitStatus", c.gitStatus },
                    { "sync", c.sync }, { "consent", c.consent }, { "writes", c.writes }, { "blockedReason", c.blockedReason }, { "error", c.error }, { "errorStack", c.errorStack },
                    { "sandboxReady", c.sandboxReady }, { "preflightOnly", c.preflightOnly },
                    { "metrics", c.metrics.ToDictionary(kv => kv.Key, kv => (object)kv.Value) },
                    { "metricNotes", c.metricNotes.ToDictionary(kv => kv.Key, kv => (object)kv.Value) },
                    { "preflight", c.preflight.Cast<object>().ToList() }, { "preconditions", c.preconditions.Cast<object>().ToList() }, { "steps", c.steps.Cast<object>().ToList() },
                    { "checks", c.checks.Cast<object>().ToList() }, { "shots", c.shots.Cast<object>().ToList() }, { "sequences", c.sequences.Cast<object>().ToList() },
                    { "perf", c.perf.Cast<object>().ToList() }, { "textures", c.textures.Cast<object>().ToList() }, { "settings", c.settings.Cast<object>().ToList() },
                    { "play", c.play.Cast<object>().ToList() },
                    { "warnings", c.warnings.Cast<object>().ToList() }, { "files", c.files.Cast<object>().ToList() },
                    { "toolErrors", c.toolErrors.Cast<object>().ToList() }, { "toolTouched", c.toolTouched.Cast<object>().ToList() },
                };
                if (c.before != null)
                    d["before"] = new Dictionary<string, object>
                    {
                        { "assets", c.before.assets.ToDictionary(kv => kv.Key, kv => (object)new List<object> { (double)kv.Value.Key, kv.Value.Value.ToString(IC) }) },
                        { "settings", c.before.settings.ToDictionary(kv => kv.Key, kv => (object)kv.Value) },
                    };
                File.WriteAllText(P(c.outDir, "ctx.json"), TJson.Write(d, false), new UTF8Encoding(false));
                c.log.WriteJsonl(P(c.outDir, "console.jsonl"));
            }

            public static Ctx Load(string outDir)
            {
                var d = TJson.M(TJson.Parse(File.ReadAllText(P(outDir, "ctx.json"), Encoding.UTF8)));
                var c = new Ctx
                {
                    testId = TJson.S(TJson.G(d, "testId")), testFile = TJson.S(TJson.G(d, "testFile")), testSha = TJson.S(TJson.G(d, "testSha")), runId = TJson.S(TJson.G(d, "runId")),
                    outDir = TJson.S(TJson.G(d, "outDir")), projectDir = TJson.S(TJson.G(d, "projectDir")), mode = TJson.S(TJson.G(d, "mode")),
                    test = TJson.M(TJson.G(d, "test")), scenePath = TJson.S(TJson.G(d, "scenePath")), gitStatus = TJson.S(TJson.G(d, "gitStatus")),
                    sync = TJson.M(TJson.G(d, "sync")), consent = TJson.M(TJson.G(d, "consent")), writes = TJson.M(TJson.G(d, "writes")),
                    blockedReason = TJson.S(TJson.G(d, "blockedReason")), error = TJson.S(TJson.G(d, "error")), errorStack = TJson.S(TJson.G(d, "errorStack")),
                    sandboxReady = TJson.B(TJson.G(d, "sandboxReady")), preflightOnly = TJson.B(TJson.G(d, "preflightOnly")),
                };
                DateTime st;
                if (DateTime.TryParse(TJson.S(TJson.G(d, "started"), ""), IC, DateTimeStyles.RoundtripKind, out st)) c.started = st;
                foreach (var kv in TJson.M(TJson.G(d, "metrics")) ?? new Dictionary<string, object>()) c.metrics[kv.Key] = TJson.D(kv.Value, 0);
                foreach (var kv in TJson.M(TJson.G(d, "metricNotes")) ?? new Dictionary<string, object>()) c.metricNotes[kv.Key] = TJson.S(kv.Value, "");
                Fill(c.preflight, d, "preflight"); Fill(c.preconditions, d, "preconditions"); Fill(c.steps, d, "steps"); Fill(c.checks, d, "checks");
                Fill(c.shots, d, "shots"); Fill(c.sequences, d, "sequences"); Fill(c.perf, d, "perf"); Fill(c.textures, d, "textures"); Fill(c.settings, d, "settings");
                Fill(c.play, d, "play");
                c.warnings.AddRange(TJson.Sa(TJson.G(d, "warnings"))); c.files.AddRange(TJson.Sa(TJson.G(d, "files")));
                c.toolErrors.AddRange(TJson.Sa(TJson.G(d, "toolErrors"))); c.toolTouched.AddRange(TJson.Sa(TJson.G(d, "toolTouched")));
                var b = TJson.M(TJson.G(d, "before"));
                if (b != null)
                {
                    c.before = new WriteGuard.Snapshot();
                    foreach (var kv in TJson.M(TJson.G(b, "assets")) ?? new Dictionary<string, object>())
                    {
                        var l = TJson.L(kv.Value);
                        long sz = l.Count > 0 ? (long)TJson.D(l[0], 0) : 0, tk = 0;
                        if (l.Count > 1) long.TryParse(TJson.S(l[1], "0"), NumberStyles.Integer, IC, out tk);
                        c.before.assets[kv.Key] = new KeyValuePair<long, long>(sz, tk);
                    }
                    foreach (var kv in TJson.M(TJson.G(b, "settings")) ?? new Dictionary<string, object>()) c.before.settings[kv.Key] = TJson.S(kv.Value, "");
                }
                string logPath = P(outDir, "console.jsonl");
                if (File.Exists(logPath))
                {
                    var rows = new List<Dictionary<string, object>>();
                    foreach (var line in File.ReadAllLines(logPath, Encoding.UTF8)) if (line.Trim().Length > 0) { var r = TJson.M(TJson.Parse(line)); if (r != null) rows.Add(r); }
                    c.log.Preload(rows);
                }
                return c;
            }

            static void Fill(List<Dictionary<string, object>> dst, Dictionary<string, object> d, string k)
            {
                foreach (var o in TJson.L(TJson.G(d, k))) { var m = TJson.M(o); if (m != null) dst.Add(m); }
            }
        }
    }

    /// <summary>Play 阶段的图（曲线、缩略图拼版）和 summary.md 里的那一节。</summary>
    public static class PlayReport
    {
        public const int PW = 960, PH = 320;
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        public static List<Dictionary<string, object>> Records(Ctx ctx) { return ctx.play; }

        public static void Summaries(Ctx ctx)
        {
            // 探测：每个探测的几个变体并排比（同一个 id）
            foreach (var g in ctx.play.Where(r => (string)r["group"] == "probe").GroupBy(r => (string)r["id"]))
            {
                var vs = g.ToList();
                if (vs.Count < 2) continue;
                string baseV = (string)vs[0]["variant"];
                double b;
                if (!ctx.metrics.TryGetValue("probe." + g.Key + "." + baseV + ".max_step_ev", out b)) continue;
                foreach (var v in vs.Skip(1))
                {
                    double x;
                    if (ctx.metrics.TryGetValue("probe." + g.Key + "." + (string)v["variant"] + ".max_step_ev", out x))
                        ctx.Metric("probe." + g.Key + "." + (string)v["variant"] + ".max_step_vs_" + baseV, x - b, "这个变体的 max_step_ev 减去第一个变体（" + baseV + "）的：明显变小 = 关掉的那一样和闪有关");
                }
            }
        }

        /// <summary>曲线：横轴时间，纵轴平均对数亮度（−8 … 0 EV，每 1 EV 一条线），中间那条竖线是交接时刻。</summary>
        public static Color32[] Plot(List<double[]> rows, PlayPhase.Seg seg)
        {
            var img = new Color32[PW * PH];
            var bg = new Color32(18, 18, 22, 255); var grid = new Color32(48, 48, 56, 255); var mark = new Color32(200, 80, 80, 255);
            var line = new Color32(240, 220, 120, 255); var dot = new Color32(255, 255, 255, 255);
            for (int i = 0; i < img.Length; i++) img[i] = bg;
            double x0 = seg.t0, x1 = Math.Max(seg.t1, seg.t0 + 0.1);
            Func<double, int> X = t => (int)Math.Round((t - x0) / (x1 - x0) * (PW - 1));
            Func<double, int> Y = v => (int)Math.Round((Math.Max(-8.0, Math.Min(0.0, v)) + 8.0) / 8.0 * (PH - 1));
            for (int e = -8; e <= 0; e++) HLine(img, Y(e), grid);
            for (double t = Math.Ceiling(x0); t <= x1; t += 1) VLine(img, X(t), grid);
            if (seg.group == "sweep") VLine(img, X(seg.tc), mark);
            for (int i = 1; i < rows.Count; i++) Line(img, X(rows[i - 1][1]), Y(rows[i - 1][2]), X(rows[i][1]), Y(rows[i][2]), line);
            foreach (var r in rows) { int x = X(r[1]), y = Y(r[2]); for (int dy = -1; dy <= 1; dy++) for (int dx = -1; dx <= 1; dx++) Put(img, x + dx, y + dy, dot); }
            return img;
        }

        static void Put(Color32[] img, int x, int y, Color32 c) { if (x >= 0 && x < PW && y >= 0 && y < PH) img[y * PW + x] = c; }
        static void HLine(Color32[] img, int y, Color32 c) { for (int x = 0; x < PW; x++) Put(img, x, y, c); }
        static void VLine(Color32[] img, int x, Color32 c) { for (int y = 0; y < PH; y++) Put(img, x, y, c); }
        static void Line(Color32[] img, int xa, int ya, int xb, int yb, Color32 c)
        {
            int dx = Math.Abs(xb - xa), dy = -Math.Abs(yb - ya), sx = xa < xb ? 1 : -1, sy = ya < yb ? 1 : -1, err = dx + dy;
            for (int guard = 0; guard < 4 * (PW + PH); guard++)
            {
                Put(img, xa, ya, c);
                if (xa == xb && ya == yb) break;
                int e2 = 2 * err;
                if (e2 >= dy) { err += dy; xa += sx; }
                if (e2 <= dx) { err += dx; ya += sy; }
            }
        }

        /// <summary>缩略图拼版：cols 列，从左上开始按时间排（Texture2D 的行 0 在最下面，所以从最上一行往下放）。</summary>
        public static Color32[] Sheet(List<Color32[]> tiles, int cols, int tw, int th, out int w, out int h)
        {
            int n = Math.Max(1, tiles.Count), rows = (n + cols - 1) / cols, gap = 4;
            w = cols * tw + (cols + 1) * gap; h = rows * th + (rows + 1) * gap;
            var img = new Color32[w * h];
            for (int i = 0; i < img.Length; i++) img[i] = new Color32(10, 10, 12, 255);
            for (int i = 0; i < tiles.Count; i++)
            {
                int cx = i % cols, cy = rows - 1 - i / cols;
                int ox = gap + cx * (tw + gap), oy = gap + cy * (th + gap);
                for (int y = 0; y < th; y++) for (int x = 0; x < tw; x++) img[(oy + y) * w + ox + x] = tiles[i][y * tw + x];
            }
            return img;
        }

        /// <summary>summary.md 里 Play 阶段的那一节。</summary>
        public static void Section(Ctx ctx, StringBuilder sb)
        {
            if (ctx.play.Count == 0) return;
            Func<string, string> M = k => { double v; return ctx.metrics.TryGetValue(k, out v) ? v.ToString("0.00", IC) : "—"; };
            var sweeps = ctx.play.Where(r => (string)r["group"] == "sweep").ToList();
            if (sweeps.Count > 0)
            {
                sb.AppendLine("## 交接扫描（Play 模式，主座位；全画面的平均对数亮度）");
                sb.AppendLine("每个交接前后各 7 s：每秒一张（`strip_1s.png`），交接点前后 1 s 每 0.1 s 一张（`strip_fine.png`），曲线 `curve.png`（红线 = 交接时刻，纵轴 −8 … 0 EV）。**有意的**（剪 1–3、第 5 幕的黑、U9 的闪、FLASH_TEAR）单独标出，不算技术跳变。圣经 §1.8 的限速是每个视向的，这里是全画面平均，只用来找“哪里跳了”，不是验收。");
                sb.AppendLine();
                sb.AppendLine("| # | 交接 | t | 类别 | 相邻两张最大差 EV | 0.25 s 升 | 1 s 升 | 2 s 升 | 漏拍 | 图 |");
                sb.AppendLine("|---|---|---|---|---|---|---|---|---|---|");
                foreach (var r in sweeps)
                {
                    string id = (string)r["id"], p = "sweep." + id, kind = (string)r["kind"];
                    string tag = kind == "check" ? "" : kind == "cut" ? "**硬切（有意）**" : kind == "black" ? "**第 5 幕的黑（有意）**" : kind == "flash" ? "**授权的闪（有意）**" : kind;
                    double r025; ctx.metrics.TryGetValue(p + ".rise_025", out r025);
                    double r1; ctx.metrics.TryGetValue(p + ".rise_1", out r1);
                    double r2; ctx.metrics.TryGetValue(p + ".rise_2", out r2);
                    bool hot = kind == "check" && (r025 > 0.5 || r1 > 1.0 || r2 > 1.8);
                    sb.AppendLine("| " + id + " | " + (string)r["name"] + " | " + ((double)r["t"]).ToString("0.##", IC) + " | " + tag + " | " + M(p + ".max_step_ev") + " | " +
                                  (hot && r025 > 0.5 ? "⚠️ " : "") + M(p + ".rise_025") + " | " + (hot && r1 > 1.0 ? "⚠️ " : "") + M(p + ".rise_1") + " | " + (hot && r2 > 1.8 ? "⚠️ " : "") + M(p + ".rise_2") + " | " +
                                  M(p + ".missed") + " | `" + (string)r["dir"] + "/` |");
                }
                sb.AppendLine();
            }
            var probes = ctx.play.Where(r => (string)r["group"] == "probe").ToList();
            if (probes.Count > 0)
            {
                sb.AppendLine("## 闪烁探测（Play 模式，30 fps）");
                sb.AppendLine("一次跑一组变体：每个变体把同一段重拍一遍，只差 `toggles` 里关掉的那一样。看 `max_step_ev` 和 `flicker_px_frac` 哪个变体明显变小；局部的闪看每个变体的 `flicker_count.png`（相邻帧差 > 24 的次数）和 `diff_*_heat.png`（差最大的 8 对）。**探测不改、不删任何东西**：退出 Play 就全回去了。");
                sb.AppendLine();
                sb.AppendLine("| 探测 | 变体 | 关了什么 | 相邻两帧最大差 EV | > 0.1 EV 的次数 | 局部闪的像素占比 | 拍了 / 漏拍 | 图 |");
                sb.AppendLine("|---|---|---|---|---|---|---|---|");
                foreach (var r in probes)
                {
                    string p = "probe." + (string)r["id"] + "." + (string)r["variant"];
                    var tg = TJson.Sa(r["toggles"]);
                    sb.AppendLine("| " + (string)r["id"] + " | " + (string)r["variant"] + " | " + (tg.Count == 0 ? "（都开着）" : string.Join("；", tg.ToArray()).Replace("|", "/")) + " | " +
                                  M(p + ".max_step_ev") + " | " + M(p + ".steps_over_01ev") + " | " + M(p + ".flicker_px_frac") + " | " + M(p + ".captured") + " / " + M(p + ".missed") + " | `" + (string)r["dir"] + "/` |");
                }
                sb.AppendLine();
            }
        }
    }
}
