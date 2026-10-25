// 蓝白 · Unity 测试工具 · Play 阶段（工具 1.2.1；1.2.0 D-44 #4，1.2.1 总导演复核 E1–E12；总工程师 2026-10-25）
// !!! NOT COMPILED IN UNITY: Roslyn type-check only (Common/Tools~/compile_check). Never run in Play mode yet. !!!
//
// 测试定义里有 "play" 的（tests/transitions_sweep.json、tests/flicker_probe.json）：编辑模式的那一半照常（预检、开场景、
// build），然后工具把这次运行的状态存进输出文件夹的 _state/，进 Play 模式（ClientSim 照常起来，旅程照常走），在
// EditorApplication.update 里：
//   0. 等准备好（1.2.1，E2）：本地玩家有了、旅程的 ready_vars 都为 true（默认 _journeyReady、_spawnFadeEnded）、分发层
//      的 spawnFadeSince ≥ 0（出生淡入结束）、再过至少 2 帧；60 s 还没好记 BLOCKED。然后把玩家放到主座位（E4），
//      开 / 关 PPv2 各渲一张核对 PPv2 生效（E5），核对 Udon 变量的名字和类型（E8）；
//   1. 用旅程的调试跳转把时间轴拨到某一段的开头前 settle_s 秒，等时间走到这一段；
//   2. 时间轴每走过一个要拍的时刻，用工具自己的相机（挂在车上：LB_Journey.busRoot 局部坐标里的 camera.eye，默认 D-28
//      的主座位 (0.55, 1.70, 2.05)）拍一张：遮罩球先挪到这台相机的位置，拍完放回；记相机和玩家头的距离；
//   3. 每张记“要的时刻 / 实际的时刻”、平均对数亮度、APL；帧间的量只用间隔 ≤ 1.5 × 安排的间隔、中间没漏拍的相邻两张
//      （E3）；记 achieved_fps、missed_frac，超过门槛算 fail；PNG 都在一段拍完以后才写（拍的循环里不写盘）；
//   4. 探测的每个变体之前把上一个变体改过的东西逆序还原（E1）；收尾和所有中断路径也还原（全局量 Play 退出后还在，E7）；
//   5. 全部拍完，存结果，退出 Play。reload 以后读回状态，查检查项，照常写报告；_state/ 删掉（E11）。
// reload 前后的 Console 都接上（E9：reload 之前把没存的行写进 _state/console_bridge.jsonl）；Error Pause 停住 Play 时
// 工具把它恢复并记下（E10）；收尾出错也照样写结果行（E6），整个 Play 阶段有总超时。
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
        static readonly LogCapture _bridge = new LogCapture();   // E9：两次 reload 之间、没有 ctx 的时候的 Console

        static PlayPhase()
        {
            EditorApplication.update += Tick;
            AssemblyReloadEvents.beforeAssemblyReload += FlushBridge;
            if (!string.IsNullOrEmpty(SessionState.GetString(Key, ""))) _bridge.Start();
        }

        public static bool Wants(Ctx ctx) { return TJson.M(ctx.T("play")) != null; }

        static string OutOfState()
        {
            var st = TJson.M(TJson.Parse(SessionState.GetString(Key, "{}")));
            return TJson.S(TJson.G(st, "out"));
        }

        /// <summary>E9：reload 之前，桥里的 Console 行追加进 _state/console_bridge.jsonl（reload 以后的那一半由新的桥接着记）。</summary>
        static void FlushBridge()
        {
            try
            {
                string outDir = string.IsNullOrEmpty(SessionState.GetString(Key, "")) ? null : OutOfState();
                if (outDir == null) return;
                _bridge.Stop();
                var rows = _bridge.Rows();
                if (rows.Count == 0) return;
                var sb = new StringBuilder();
                foreach (var r in rows) sb.Append(TJson.Write(r, false)).Append('\n');
                File.AppendAllText(Store.P(outDir, "console_bridge.jsonl"), sb.ToString(), new UTF8Encoding(false));
                _bridge.Clear();
            }
            catch (Exception) { }
        }

        /// <summary>编辑模式这一半做完以后调：存状态、进 Play。返回 Deferred（收尾由 Tick 在退出 Play 以后做）。</summary>
        public static int Begin(Ctx ctx)
        {
            foreach (var e in ctx.undo.RollbackTo(0)) ctx.Warn(e);
            if (ctx.undo.Failed.Count > 0) throw new BlockedException("进 Play 之前有改回失败的：" + string.Join("、", ctx.undo.Failed.ToArray()));
            var plan = Plan.Build(ctx);                      // 定义写错了在编辑模式里就停
            ctx.Info("Play 阶段：" + plan.segs.Count + " 段、" + plan.segs.Sum(s => s.samples.Count) + " 个时刻，总超时 " + plan.timeout.ToString("0", IC) + " s；进 Play 模式");
            if (Application.isBatchMode) ctx.Warn("批处理下进 Play 模式没在阿白的机器上试过；不行就用菜单跑");
            try { EditorUtility.ClearProgressBar(); } catch { }
            ctx.log.Stop();
            Store.Save(ctx);
            Runner.ClearPending();
            SetState(ctx.outDir, "enter", ctx.mode, ctx.testId, null, false);
            _bridge.Clear();
            _bridge.Start();
            EditorApplication.isPlaying = true;
            return Deferred;
        }

        static void SetState(string outDir, string phase, string mode, string test, string err, bool blocked)
        {
            var d = new Dictionary<string, object> { { "out", outDir }, { "phase", phase }, { "mode", mode }, { "test", test }, { "at", EditorApplication.timeSinceStartup } };
            if (err != null) { d["error"] = err; d["blocked"] = blocked; }
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
            string err = TJson.S(TJson.G(st, "error"));
            bool blocked = TJson.B(TJson.G(st, "blocked"));
            try
            {
                switch (phase)
                {
                    case "enter":
                        if (EditorApplication.isPlaying)
                        {
                            _run = new Run(outDir, TakeBridge());
                            SetState(outDir, "capture", mode, test, null, false);
                        }
                        else if (!EditorApplication.isPlayingOrWillChangePlaymode && EditorApplication.timeSinceStartup - at > 20)
                            SetState(outDir, "finish", mode, test, "没进 Play 模式（编译错误？场景里缺东西？看 Console）", true);
                        break;
                    case "capture":
                        if (!EditorApplication.isPlaying)
                        {
                            if (!EditorApplication.isPlayingOrWillChangePlaymode)
                            {
                                if (_run != null) { _run.Abort("Play 模式中途被退出了"); _run = null; }
                                SetState(outDir, "finish", mode, test, "Play 模式中途被退出了（有人点了停止，或者 Unity 自己退出了 Play）", false);
                            }
                            return;
                        }
                        if (_run == null)
                        {
                            // Play 里 reload 了（脚本重新编译）：拍到一半的状态没了（拍到一半时还原用的原值也没了：退出 Play 场景会回去，全局量不会）
                            SetState(outDir, "exit", mode, test, "Play 模式里编辑器 reload 了（脚本重新编译？），拍到一半的没了", false);
                            EditorApplication.isPlaying = false;
                            return;
                        }
                        // E10：Console 的 Error Pause 把 Play 停住了：恢复，记下；一直停就算出错
                        if (EditorApplication.isPaused) { _run.Paused(); EditorApplication.isPaused = false; }
                        _run.Step();
                        if (_run.done)
                        {
                            var r = _run; _run = null;
                            string e2 = r.Save(out bool bl);
                            _bridge.Clear(); _bridge.Start();
                            SetState(outDir, "exit", mode, test, e2, bl);
                            EditorApplication.isPlaying = false;
                        }
                        break;
                    case "exit":
                        if (!EditorApplication.isPlaying && !EditorApplication.isPlayingOrWillChangePlaymode)
                            SetState(outDir, "finish", mode, test, err, blocked);
                        break;
                    case "finish":
                        if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling) return;
                        SessionState.EraseString(Key);
                        Finish(outDir, mode, test, err, blocked);
                        break;
                    default:
                        SessionState.EraseString(Key);
                        break;
                }
            }
            catch (Exception e)
            {
                Debug.LogError(LogCapture.TAG + " Play 阶段自己出错：" + e);
                if (_run != null) { try { _run.Abort("Play 阶段的工具代码出错"); } catch { } _run = null; }
                if (EditorApplication.isPlaying) { SetState(outDir, "exit", mode, test, "Play 阶段的工具代码出错：" + e.GetType().Name + ": " + e.Message, false); EditorApplication.isPlaying = false; }
                else { SessionState.EraseString(Key); Finish(outDir, mode, test, "Play 阶段的工具代码出错：" + e.Message, false); }
            }
        }

        static List<Dictionary<string, object>> TakeBridge()
        {
            _bridge.Stop();
            var rows = _bridge.Rows();
            _bridge.Clear();
            return rows;
        }

        /// <summary>退出 Play、reload 以后：读回状态，照常收尾。出错也一定写结果行（E6）。</summary>
        static void Finish(string outDir, string mode, string test, string err, bool blocked)
        {
            var done = Runner.DoneFor(mode, test, false);
            Ctx ctx = null;
            try
            {
                ctx = Store.Load(outDir);
                ctx.log.Append(TakeBridge());
                ctx.log.Start();
                int exit = 0;
                if (!string.IsNullOrEmpty(err))
                {
                    if (blocked) { ctx.blockedReason = err; exit = 2; }
                    else { ctx.error = err; exit = 3; }
                }
                Runner.FinishFromPlay(ctx, exit, done);
                Store.Delete(outDir);                    // E11：_state/ 不留在输出里
            }
            catch (Exception e)
            {
                Debug.LogError(LogCapture.TAG + " Play 阶段收尾出错：" + e);
                Runner.Emergency(outDir, test, "Play 阶段收尾出错：" + e.GetType().Name + ": " + e.Message + (err != null ? "（之前：" + err + "）" : ""), done);
            }
        }

        // ─────────────────────────────────────────────────────────────
        //  要拍什么（从测试定义算出来）
        // ─────────────────────────────────────────────────────────────
        public sealed class Seg
        {
            public string group, id, name, kind, note, variant;
            public float tc, t0, t1, fineFrom = 1e9f, fineTo = -1e9f;
            public List<float> samples = new List<float>();
            public List<object> toggles = new List<object>();
        }

        public sealed class Plan
        {
            public List<Seg> segs = new List<Seg>();
            public Dictionary<string, object> play, cam;
            public float settle, timeout, maxMissed;

            public static Plan Build(Ctx ctx)
            {
                var p = new Plan { play = TJson.M(ctx.T("play")) };
                p.cam = TJson.M(TJson.G(p.play, "camera")) ?? new Dictionary<string, object>();
                p.settle = TJson.F(TJson.G(p.play, "settle_s"), 2f);
                p.maxMissed = TJson.F(TJson.G(p.play, "max_missed_frac"), 0.1f);
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
                        var s = new Seg { group = "sweep", id = id, name = TJson.S(TJson.G(r, "name"), id), kind = TJson.S(TJson.G(r, "kind"), "check"), note = TJson.S(TJson.G(r, "note")), tc = tc, t0 = tc - pre, t1 = tc + post, fineFrom = tc - fs, fineTo = tc + fs };
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
                // E6：总超时 = 每段的长度 + settle + 20 s，加上准备的 60 s 和 60 s 余量（测试定义可以用 timeout_s 改）
                p.timeout = TJson.F(TJson.G(p.play, "timeout_s"), p.segs.Sum(x => x.t1 - x.t0 + p.settle + 20f) + 120f);
                return p;
            }

            static void Add(List<float> l, float t) { if (!l.Any(x => Math.Abs(x - t) < 1e-3f)) l.Add(t); }
        }

        // ─────────────────────────────────────────────────────────────
        //  还原（E1、E7）：每样东西第一次改之前记下原值；下一个变体之前、收尾、中断时逆序还原
        // ─────────────────────────────────────────────────────────────
        public sealed class Restorer
        {
            readonly List<KeyValuePair<string, Action>> _l = new List<KeyValuePair<string, Action>>();
            readonly HashSet<string> _keys = new HashSet<string>();
            public void Remember(string key, Action restore) { if (_keys.Add(key)) _l.Add(new KeyValuePair<string, Action>(key, restore)); }
            public List<string> RestoreAll()
            {
                var errs = new List<string>();
                for (int i = _l.Count - 1; i >= 0; i--)
                {
                    try { _l[i].Value(); } catch (Exception e) { errs.Add("还原 " + _l[i].Key + " 失败：" + e.Message); }
                }
                _l.Clear(); _keys.Clear();
                return errs;
            }
        }

        // ─────────────────────────────────────────────────────────────
        //  每帧临时改的东西（只在 Play 里）。拍每一张之前都再设一次（旅程可能每帧改回去）
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

            static string Id(Object o) { return o.GetInstanceID().ToString(IC); }

            /// <summary>做一遍；返回做了什么。找不到的：optional 就跳过，不然报错。第一次改每样东西之前把原值交给 rs。</summary>
            public static string Apply(Ctx ctx, Dictionary<string, object> t, Restorer rs)
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
                            var go = tr.gameObject; bool old = go.activeSelf;
                            rs.Remember("active " + Id(go), () => { if (go != null) go.SetActive(old); });
                            if (go.activeSelf != v) go.SetActive(v);
                            return Scenes.PathOf(tr) + " active = " + v;
                        }
                    case "set_renderer":
                        {
                            var tr = Scenes.Find(TJson.S(TJson.G(t, "path")));
                            var r = tr != null ? tr.GetComponent<Renderer>() : null;
                            if (r == null) { if (opt) return "没有 " + TJson.S(TJson.G(t, "path")) + " 的 Renderer（optional，跳过）"; throw new StepException("找不到 " + TJson.S(TJson.G(t, "path")) + " 的 Renderer"); }
                            bool old = r.enabled;
                            rs.Remember("renderer " + Id(r), () => { if (r != null) r.enabled = old; });
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
                                if (b != null) { bool old = b.enabled; rs.Remember("behaviour " + Id(b), () => { if (b != null) b.enabled = old; }); b.enabled = v; n++; where.Add(Scenes.PathOf(b.transform)); }
                                else if (r != null) { bool old = r.enabled; rs.Remember("renderer " + Id(r), () => { if (r != null) r.enabled = old; }); r.enabled = v; n++; where.Add(Scenes.PathOf(r.transform)); }
                            }
                            if (n == 0 && !opt) throw new StepException("场景里没有 " + cn);
                            return cn + " × " + n + " enabled = " + v + (where.Count > 0 ? "（" + string.Join("、", where.Take(8).ToArray()) + "）" : "");
                        }
                    case "field_objects_active":
                    case "field_renderers":
                        {
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
                                    if (go == null) continue;
                                    bool old = go.activeSelf;
                                    rs.Remember("active " + Id(go), () => { if (go != null) go.SetActive(old); });
                                    if (go.activeSelf != v) go.SetActive(v);
                                    n++;
                                }
                                else
                                {
                                    var rr = o as Renderer;
                                    if (rr == null) continue;
                                    if (TJson.Has(t, "enabled"))
                                    {
                                        bool old = rr.enabled;
                                        rs.Remember("renderer " + Id(rr), () => { if (rr != null) rr.enabled = old; });
                                        rr.enabled = TJson.B(TJson.G(t, "enabled"));
                                    }
                                    if (mpbF != null)
                                    {
                                        var before = new MaterialPropertyBlock();
                                        rr.GetPropertyBlock(before);
                                        rs.Remember("mpb " + Id(rr), () => { if (rr != null) rr.SetPropertyBlock(before); });
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
                            var vt = Udon.TypeOf(ub, var);
                            if (vt == null) throw new StepException(cn + " 没有 Udon 变量 " + var + "（名字写错了？）");
                            object val = Udon.Convert(TJson.G(t, "value"), vt);
                            object old = Udon.Get(ub, var);
                            rs.Remember("udon " + Id(ub) + "." + var, () => { if (ub != null) Udon.Set(ub, var, old); });
                            Udon.Set(ub, var, val);
                            return cn + "." + var + " = " + TJson.Write(TJson.G(t, "value"), false);
                        }
                    case "global_float":
                        {
                            string n = TJson.S(TJson.G(t, "name"));
                            float old = Shader.GetGlobalFloat(n);
                            rs.Remember("global " + n, () => Shader.SetGlobalFloat(n, old));
                            Shader.SetGlobalFloat(n, TJson.F(TJson.G(t, "value")));
                            return n + " = " + TJson.F(TJson.G(t, "value")).ToString("0.###", IC);
                        }
                    case "global_vector":
                        {
                            string n = TJson.S(TJson.G(t, "name"));
                            var a = TJson.Fa(TJson.G(t, "value")) ?? new float[0];
                            var vec = new Vector4(a.Length > 0 ? a[0] : 0, a.Length > 1 ? a[1] : 0, a.Length > 2 ? a[2] : 0, a.Length > 3 ? a[3] : 0);
                            Vector4 old = Shader.GetGlobalVector(n);
                            rs.Remember("global " + n, () => Shader.SetGlobalVector(n, old));
                            Shader.SetGlobalVector(n, vec);
                            return n + " = " + vec;
                        }
                }
                throw new StepException("不认识的 toggle " + k);
            }
        }

        // ─────────────────────────────────────────────────────────────
        //  UdonBehaviour、本地玩家（反射：工具不引用 Udon / VRC SDK 的程序集）
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
                var ubt = Preflight.FindType("VRC.Udon.UdonBehaviour");
                return ubt != null ? proxy.GetComponents(ubt).FirstOrDefault() : null;
            }
            public static object Get(Component ub, string name)
            {
                var m = ub.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance).FirstOrDefault(x => x.Name == "GetProgramVariable" && !x.IsGenericMethod && x.GetParameters().Length == 1);
                return m != null ? m.Invoke(ub, new object[] { name }) : null;
            }
            /// <summary>E8：变量的类型（没有这个变量 = null；读不到类型的 SDK = typeof(object)）。</summary>
            public static Type TypeOf(Component ub, string name)
            {
                var m = ub.GetType().GetMethod("GetProgramVariableType", BindingFlags.Public | BindingFlags.Instance, null, new[] { typeof(string) }, null);
                if (m == null) return typeof(object);
                return m.Invoke(ub, new object[] { name }) as Type;
            }
            public static object Convert(object json, Type t)
            {
                if (t == typeof(float)) return TJson.F(json);
                if (t == typeof(int)) return TJson.I(json);
                if (t == typeof(bool)) return TJson.B(json);
                if (t == typeof(double)) return TJson.D(json, 0);
                if (t == typeof(string)) return TJson.S(json);
                return json is double ? (object)(float)(double)json : json;
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

        public static class Player
        {
            public static object Local()
            {
                var net = Preflight.FindType("VRC.SDKBase.Networking");
                var p = net != null ? net.GetProperty("LocalPlayer", BindingFlags.Public | BindingFlags.Static) : null;
                try { return p != null ? p.GetValue(null) : null; } catch { return null; }
            }
            public static Vector3? Head(object lp)
            {
                if (lp == null) return null;
                try
                {
                    var tdt = lp.GetType().GetNestedType("TrackingDataType");
                    var m = lp.GetType().GetMethod("GetTrackingData");
                    if (tdt == null || m == null) return null;
                    object td = m.Invoke(lp, new[] { Enum.Parse(tdt, "Head") });
                    var f = td.GetType().GetField("position");
                    return f != null ? (Vector3?)(Vector3)f.GetValue(td) : null;
                }
                catch { return null; }
            }
            public static Vector3? Position(object lp)
            {
                try { var m = lp.GetType().GetMethod("GetPosition", Type.EmptyTypes); return m != null ? (Vector3?)(Vector3)m.Invoke(lp, null) : null; } catch { return null; }
            }
            public static bool Teleport(object lp, Vector3 pos, Quaternion rot)
            {
                try
                {
                    var m = lp.GetType().GetMethod("TeleportTo", new[] { typeof(Vector3), typeof(Quaternion) });
                    if (m == null) return false;
                    m.Invoke(lp, new object[] { pos, rot });
                    return true;
                }
                catch { return false; }
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
            readonly string clockType, timeVar, seekVar, seekEvent, dispatcherType;
            readonly List<string> readyVars;
            Component clock, dispatcher;
            Capture.Renderer2 r;
            Transform anchor, overlayTr;
            Vector3 eyeLocal; Quaternion rotLocal;
            int w, h, segIdx = -1, sampleIdx, readyFrames, pauses;
            string state = "ready";
            double stateAt, startedAt;
            Seg seg;
            SegData data;
            string fatal; bool fatalBlocked;
            readonly Restorer rs = new Restorer();
            float headCamMax = -1f;
            static readonly float[] Lin = BuildLin();

            public Run(string outDir, List<Dictionary<string, object>> bridged)
            {
                ctx = Store.Load(outDir);
                ctx.log.Append(bridged);
                ctx.log.Start();
                plan = Plan.Build(ctx);
                var ck = TJson.M(TJson.G(plan.play, "clock")) ?? new Dictionary<string, object>();
                clockType = TJson.S(TJson.G(ck, "component"), "LB_Journey");
                timeVar = TJson.S(TJson.G(ck, "time_var"), "dbgT");
                seekVar = TJson.S(TJson.G(ck, "seek_var"), "debugSeekSeconds");
                seekEvent = TJson.S(TJson.G(ck, "seek_event"), "_DebugSeekVar");
                readyVars = TJson.Has(ck, "ready_vars") ? TJson.Sa(TJson.G(ck, "ready_vars")) : new List<string> { "_journeyReady", "_spawnFadeEnded" };
                dispatcherType = TJson.S(TJson.G(plan.play, "dispatcher"), "LanbaiActDispatcher");
                startedAt = stateAt = EditorApplication.timeSinceStartup;
                ctx.Info("Play 阶段开始：" + plan.segs.Count + " 段");
            }

            static float[] BuildLin()
            {
                var l = new float[256];
                for (int i = 0; i < 256; i++) { float c = i / 255f; l[i] = c <= 0.04045f ? c / 12.92f : Mathf.Pow((c + 0.055f) / 1.055f, 2.4f); }
                return l;
            }

            public void Paused()
            {
                pauses++;
                ctx.Warn("Console 的 Error Pause 把 Play 停住了（第 " + pauses + " 次）：工具恢复了它；看 Console 里那条 Error");
                if (pauses > 20) Fail("Error Pause 停了 20 次以上：Console 里一直在报 Error，拍不下去", false);
            }

            float Now()
            {
                object v = Udon.Get(clock, timeVar);
                return v is float ? (float)v : (v is double ? (float)(double)v : -1f);
            }

            void Fail(string msg, bool blocked)
            {
                if (fatal == null) { fatal = msg; fatalBlocked = blocked; }
                done = true;
            }

            /// <summary>E2：本地玩家、旅程准备好、出生淡入结束、至少 2 帧。</summary>
            bool Ready(double now)
            {
                if (now - stateAt > 60.0)
                {
                    Fail("进 Play 以后 60 s 还没准备好（本地玩家 / " + string.Join(" / ", readyVars.ToArray()) + " / 出生淡入结束）：ClientSim 没起来？", true);
                    return false;
                }
                if (Player.Local() == null) { readyFrames = 0; return false; }
                if (clock == null) clock = Udon.Behaviour(clockType);
                if (clock == null) { readyFrames = 0; return false; }
                foreach (var v in readyVars)
                {
                    var t = Udon.TypeOf(clock, v);
                    if (t == null) { Fail(clockType + " 没有 Udon 变量 " + v + "（ready_vars 写错了，或者本地的旅程不一样）", true); return false; }
                    if (!(Udon.Get(clock, v) is bool) || !(bool)Udon.Get(clock, v)) { readyFrames = 0; return false; }
                }
                if (dispatcher == null) dispatcher = Udon.Behaviour(dispatcherType);
                if (dispatcher != null)
                {
                    object sf = Udon.Get(dispatcher, "spawnFadeSince");
                    if (sf is float && (float)sf < 0f) { readyFrames = 0; return false; }
                }
                return ++readyFrames >= 2;
            }

            void Setup()
            {
                // E8：时间轴的变量名字和类型
                foreach (var v in new[] { timeVar, seekVar })
                {
                    var t = Udon.TypeOf(clock, v);
                    if (t == null) throw new BlockedPlay(clockType + " 没有 Udon 变量 " + v + "（clock 写错了，或者本地的旅程不一样）");
                    if (t != typeof(object) && t != typeof(float)) throw new BlockedPlay(clockType + "." + v + " 是 " + t.Name + "，要 float");
                }
                // 相机：挂在车上，camera.eye（车的局部坐标；默认 D-28 的主座位 (0.55, 1.70, 2.05)），朝向 yaw / pitch / roll
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
                if (anchor == null) throw new BlockedPlay("找不到相机挂的车（camera.relative_to）");
                var e = TJson.Fa(TJson.G(c, "eye")) ?? new[] { 0.55f, 1.70f, 2.05f };
                eyeLocal = new Vector3(e[0], e[1], e[2]);
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
                SeatPlayer();
                // E5：开 / 关 PPv2 各渲一张，不一样才算生效
                bool dummy;
                var a = Shoot();
                var b = Capture.RenderOnce(ctx, cam, w, h, 1, false, out dummy);
                double diff = 0;
                for (int i = 0; i < a.Length && i < b.Length; i++) diff += Math.Abs(Img.Luma(a[i]) - Img.Luma(b[i]));
                diff /= Math.Max(1, a.Length);
                ctx.Metric("play.ppv2_layer", r.hasPP ? 1 : 0, "Play 里参考相机上有 PostProcessLayer、工具的相机 Init 成功");
                ctx.Metric("play.ppv2_diff", diff, "Play 里同一机位开 / 关 PPv2 的平均亮度差（sRGB 0–255）");
                ctx.Metric("play.ppv2_effective", r.hasPP && diff > 0.5 ? 1 : 0, "Play 里 PPv2 真的生效了（曲线是调过色的画面）");
                if (!(r.hasPP && diff > 0.5)) ctx.Warn("Play 里 PPv2 好像没生效（开 / 关差 " + diff.ToString("0.00", IC) + "）：曲线是没调色的画面");
            }

            /// <summary>E4：ClientSim 的玩家放到主座位（头对准相机）；记下头和相机的距离。</summary>
            void SeatPlayer()
            {
                if (!TJson.B(TJson.G(plan.play, "seat_player"), true)) return;
                var lp = Player.Local();
                var head = Player.Head(lp); var pos = Player.Position(lp);
                var camPos = anchor.TransformPoint(eyeLocal);
                if (lp == null || head == null || pos == null) { ctx.Warn("读不到本地玩家的头 / 位置：玩家没挪到主座位（遮罩球照样挪到相机这里）"); return; }
                Vector3 off = head.Value - pos.Value;
                if (!Player.Teleport(lp, camPos - off, Quaternion.Euler(0f, (anchor.rotation * rotLocal).eulerAngles.y, 0f)))
                    ctx.Warn("TeleportTo 调不了：玩家没挪到主座位");
            }

            void TrackHead()
            {
                var hd = Player.Head(Player.Local());
                if (hd == null) return;
                float d = Vector3.Distance(hd.Value, anchor.TransformPoint(eyeLocal));
                if (d > headCamMax) headCamMax = d;
            }

            public void Step()
            {
                if (done) return;
                try
                {
                    double now = EditorApplication.timeSinceStartup;
                    if (now - startedAt > plan.timeout) { Fail("Play 阶段超过总超时 " + plan.timeout.ToString("0", IC) + " s", false); return; }
                    switch (state)
                    {
                        case "ready":
                            if (!Ready(now)) return;
                            Setup();
                            state = "next";
                            return;
                        case "next":
                            if (data != null) data.Finish(ctx, plan);
                            data = null;
                            foreach (var er in rs.RestoreAll()) ctx.Warn(er);      // E1：上一个变体改的东西逆序还原
                            segIdx++;
                            if (segIdx >= plan.segs.Count) { done = true; return; }
                            seg = plan.segs[segIdx];
                            data = new SegData(seg, w, h);
                            foreach (var tg in seg.toggles) data.toggleLog.Add(Toggles.Apply(ctx, TJson.M(tg), rs));
                            Udon.Set(clock, seekVar, Math.Max(0f, seg.t0 - plan.settle));
                            Udon.Send(clock, seekEvent);
                            sampleIdx = 0;
                            state = "settle"; stateAt = now;
                            EditorUtility.DisplayProgressBar("蓝白测试 · Play", (seg.group == "sweep" ? "交接 " + seg.id + " " + seg.name : "探测 " + seg.id + " / " + seg.variant) + "（" + (segIdx + 1) + "/" + plan.segs.Count + "）", (segIdx + 0.5f) / plan.segs.Count);
                            return;
                        case "settle":
                            {
                                float t = Now();
                                if (t >= seg.samples[0] - 1e-3f) { SeatPlayer(); state = "capture"; stateAt = now; goto case "capture"; }
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
                                int skipped = 0;
                                while (sampleIdx + 1 < seg.samples.Count && seg.samples[sampleIdx + 1] <= t + 1e-3f) { sampleIdx++; skipped++; }
                                data.missed += skipped;
                                float target = seg.samples[sampleIdx];
                                foreach (var tg in seg.toggles) Toggles.Apply(ctx, TJson.M(tg), rs);
                                TrackHead();
                                var px = Shoot();
                                data.Add(sampleIdx, target, t, px, Lin);
                                sampleIdx++;
                                return;
                            }
                    }
                }
                catch (Exception e)
                {
                    var inner = e is TargetInvocationException && e.InnerException != null ? e.InnerException : e;
                    bool bl = inner is BlockedPlay;
                    if (!(inner is StepException) && !bl) ctx.ToolError("Play 阶段", inner);
                    if (seg != null) ctx.steps.Add(new Dictionary<string, object> { { "phase", "play" }, { "type", seg.group }, { "desc", seg.id + (seg.variant != null ? "/" + seg.variant : "") }, { "status", "error" }, { "error", inner.Message } });
                    if (data != null) { try { data.Finish(ctx, plan); } catch { } data = null; }
                    Fail(inner.Message, bl);
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

            /// <summary>中断（Play 被退出、工具出错）：能还原的还原（全局量退出 Play 后还在）。</summary>
            public void Abort(string why)
            {
                foreach (var er in rs.RestoreAll()) ctx.Warn(er);
                if (fatal == null) fatal = why;
                try { Save(out bool _); } catch { }
            }

            /// <summary>存结果（ctx 连同 Play 里的 Console）；返回要记的那句话（没有 = null），blocked = 算 BLOCKED。</summary>
            public string Save(out bool blocked)
            {
                foreach (var er in rs.RestoreAll()) ctx.Warn(er);
                try { EditorUtility.ClearProgressBar(); } catch { }
                if (r != null) { r.Dispose(); r = null; }
                if (headCamMax >= 0f) ctx.Metric("play.head_cam_dist_max", headCamMax, "拍的时候玩家的头离工具相机最远多少米（遮罩球每张都挪到相机这里；这个数大说明玩家没坐到主座位）");
                ctx.Metric("play.error_pauses", pauses, "Error Pause 停住 Play 的次数（工具每次都恢复了）");
                PlayReport.Summaries(ctx);
                ctx.log.Stop();
                Store.Save(ctx);
                blocked = fatalBlocked;
                return fatal;
            }
        }

        sealed class BlockedPlay : Exception { public BlockedPlay(string m) : base(m) { } }

        /// <summary>一段的数据：每帧的数，缩略图，探测的逐像素统计。PNG 都在 Finish 里才写（E3）。</summary>
        sealed class SegData
        {
            readonly Seg seg; readonly int w, h, N;
            public int missed;
            public readonly List<string> toggleLog = new List<string>();
            readonly List<double[]> rows = new List<double[]>();          // index, target, t, meanLog, apl, diffMean
            readonly List<KeyValuePair<float, Color32[]>> thumbs = new List<KeyValuePair<float, Color32[]>>();
            float[] prevY, lastY; int[] flips; float[] maxDiff; double prevT = double.NaN, prevTarget; int prevIdx = -10;
            readonly List<Top> top = new List<Top>();
            int validPairs;
            const int TW = 160, TH = 90, TOPK = 8;

            sealed class Top { public double score; public float t; public float[] heat, y; public Color32[] px; }

            public SegData(Seg s, int w, int h) { seg = s; this.w = w; this.h = h; N = w * h; }

            string Dir { get { return seg.group == "sweep" ? "sweep/" + seg.id : "probe/" + seg.id + "/" + seg.variant; } }

            /// <summary>E3：相邻两张只在中间没漏拍、实际间隔 ≤ 1.5 × 安排的间隔时才算帧间的量。</summary>
            bool ValidPair(int idx, float target, float t)
            {
                if (prevIdx != idx - 1 || double.IsNaN(prevT)) return false;
                double sched = target - prevTarget;
                return sched > 0 && t - prevT <= 1.5 * sched + 1e-4;
            }

            public void Add(int idx, float target, float t, Color32[] px, float[] lin)
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
                bool valid = ValidPair(idx, target, t);
                if (valid) validPairs++;
                double diffMean = double.NaN;
                if (seg.group == "probe")
                {
                    if (flips == null) { flips = new int[N]; maxDiff = new float[N]; }
                    if (prevY != null && valid)
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
                        // 相邻帧差最大的几张（默认 8）留在内存里，一段拍完再写盘
                        if (top.Count < TOPK || diffMean > top.Min(x => x.score))
                        {
                            top.Add(new Top { score = diffMean, t = t, heat = heat, y = y, px = (Color32[])px.Clone() });
                            if (top.Count > TOPK) top.Remove(top.OrderBy(x => x.score).First());
                        }
                    }
                    prevY = y;
                }
                lastY = y;
                rows.Add(new double[] { idx, target, t, sumLog / N, sumY / N, diffMean, valid ? 1 : 0 });
                prevT = t; prevTarget = target; prevIdx = idx;
                if (seg.group == "sweep") thumbs.Add(new KeyValuePair<float, Color32[]>(target, Img.Resample(px, w, h, TW, TH)));
            }

            public void Finish(Ctx ctx, Plan plan)
            {
                string pre = seg.group == "sweep" ? "sweep." + seg.id : "probe." + seg.id + "." + seg.variant;
                var rec = new Dictionary<string, object>
                {
                    { "group", seg.group }, { "id", seg.id }, { "variant", seg.variant }, { "name", seg.name }, { "kind", seg.kind }, { "note", seg.note },
                    { "t", (double)seg.tc }, { "t0", (double)seg.t0 }, { "t1", (double)seg.t1 }, { "samples", (double)seg.samples.Count }, { "captured", (double)rows.Count },
                    { "missed", (double)missed }, { "valid_pairs", (double)validPairs }, { "toggles", toggleLog.Cast<object>().ToList() }, { "dir", Dir }
                };
                var csv = new StringBuilder("index,target_t,t,mean_log2_L,apl,diff_mean,valid_pair\n");
                foreach (var r in rows) csv.AppendLine(string.Join(",", r.Select(x => double.IsNaN(x) ? "" : x.ToString("0.#####", CultureInfo.InvariantCulture)).ToArray()));
                File.WriteAllText(ctx.Out(Dir + "/frames.csv"), csv.ToString(), new UTF8Encoding(false));
                ctx.AddFile(Dir + "/frames.csv");
                double missedFrac = seg.samples.Count > 0 ? 1.0 - rows.Count / (double)seg.samples.Count : 1.0;
                double span = rows.Count >= 2 ? rows[rows.Count - 1][2] - rows[0][2] : 0;
                ctx.Metric(pre + ".captured", rows.Count);
                ctx.Metric(pre + ".missed", seg.samples.Count - rows.Count, "要拍、但编辑器那一帧已经走过去了的时刻（时间轴是实时走的）");
                ctx.Metric(pre + ".missed_frac", missedFrac, "漏拍的比例；超过 play.max_missed_frac（默认 0.1）算 fail");
                ctx.Metric(pre + ".achieved_fps", span > 0 ? (rows.Count - 1) / span : 0, "实际拍到的帧率（张数 / 时间轴秒）");
                rec["max_missed_frac"] = (double)plan.maxMissed;
                if (rows.Count >= 2)
                {
                    // 帧间：只用有效的相邻两张（E3）
                    double maxStep = 0, maxStepAt = 0;
                    for (int i = 1; i < rows.Count; i++)
                    {
                        if (rows[i][6] < 0.5) continue;
                        double d = Math.Abs(rows[i][3] - rows[i - 1][3]);
                        if (d > maxStep) { maxStep = d; maxStepAt = rows[i][2]; }
                    }
                    ctx.Metric(pre + ".max_step_ev", maxStep, "有效的相邻两张（中间没漏拍、间隔 ≤ 1.5 × 安排的间隔）平均对数亮度 mean(log2(max(L, 0.004))) 的最大差（EV，升降都算）");
                    rec["max_step_at"] = maxStepAt;
                    foreach (var win in new[] { 0.25, 1.0, 2.0 })
                    {
                        double best = 0;
                        for (int i = 0; i < rows.Count; i++)
                            for (int j = i + 1; j < rows.Count && rows[j][2] - rows[i][2] <= win + 1e-6; j++)
                                best = Math.Max(best, rows[j][3] - rows[i][3]);
                        ctx.Metric(pre + ".rise_" + (win == 0.25 ? "025" : win.ToString("0", CultureInfo.InvariantCulture)), best,
                            win.ToString("0.##", CultureInfo.InvariantCulture) + " s 窗口里平均对数亮度最多升了多少 EV（圣经 §1.8：≤ " + (win == 0.25 ? "0.5" : win == 1.0 ? "1.0" : "1.8") + "，那里是每个视向，这里是全画面平均）");
                    }
                    Img.SavePng(PlayReport.Plot(rows, seg), PlayReport.PW, PlayReport.PH, ctx.Out(Dir + "/curve.png"));
                    ctx.AddFile(Dir + "/curve.png");
                }
                if (seg.group == "sweep" && thumbs.Count > 0)
                {
                    var coarse = thumbs.Where(x => x.Key < seg.fineFrom - 1e-3f || x.Key > seg.fineTo + 1e-3f || Math.Abs((x.Key - seg.t0) - Mathf.Round(x.Key - seg.t0)) < 1e-3f).ToList();
                    var fine = thumbs.Where(x => x.Key >= seg.fineFrom - 1e-3f && x.Key <= seg.fineTo + 1e-3f).ToList();
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
                    for (int i = 1; i < rows.Count; i++) if (rows[i][6] > 0.5 && Math.Abs(rows[i][3] - rows[i - 1][3]) > 0.1) stepsOver++;
                    ctx.Metric(pre + ".steps_over_01ev", stepsOver, "有效的相邻两帧平均对数亮度差 > 0.1 EV 的次数");
                    int flick = flips.Count(x => x >= 4);
                    ctx.Metric(pre + ".flicker_px_frac", flick / (double)N, "这一段里有效的相邻两帧亮度差 > 24（0–255）的次数 ≥ 4 的像素占比（局部的闪看这个和 flicker_count.png）");
                    float mx = Math.Max(4f, flips.Max());
                    Img.SavePng(Img.Heat(flips.Select(x => (float)x).ToArray(), lastY, mx), w, h, ctx.Out(Dir + "/flicker_count.png"));
                    Img.SavePng(Img.Heat(maxDiff, lastY, 128f), w, h, ctx.Out(Dir + "/max_diff.png"));
                    ctx.AddFile(Dir + "/flicker_count.png"); ctx.AddFile(Dir + "/max_diff.png");
                    var names = new List<object>();
                    foreach (var tp in top.OrderByDescending(x => x.score))
                    {
                        string name = Dir + "/diff_" + tp.t.ToString("0000.000", CultureInfo.InvariantCulture);
                        Img.SavePng(Img.Heat(tp.heat, tp.y, 64f), w, h, ctx.Out(name + "_heat.png"));
                        Img.SavePng(tp.px, w, h, ctx.Out(name + "_frame.png"));
                        names.Add(name);
                    }
                    rec["top_diffs"] = names;
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
            public static string P(string outDir, string n) { string d = Path.Combine(outDir, "_state"); Directory.CreateDirectory(d); return Path.Combine(d, n); }

            public static void Delete(string outDir)
            {
                try { string d = Path.Combine(outDir, "_state"); if (Directory.Exists(d)) Directory.Delete(d, true); } catch (Exception) { }
            }

            /// <summary>E11：Console 去重：同一来源、类型、内容、堆栈的行只留第一条，记次数（镜子的报错每帧一条）。</summary>
            public static List<Dictionary<string, object>> Dedupe(List<Dictionary<string, object>> rows)
            {
                var o = new List<Dictionary<string, object>>();
                var seen = new Dictionary<string, Dictionary<string, object>>();
                foreach (var r in rows)
                {
                    string k = TJson.S(TJson.G(r, "source"), "") + "\u0001" + TJson.S(TJson.G(r, "type"), "") + "\u0001" + TJson.S(TJson.G(r, "msg"), "") + "\u0001" + TJson.S(TJson.G(r, "stack"), "");
                    Dictionary<string, object> first;
                    if (seen.TryGetValue(k, out first)) { first["repeat"] = TJson.D(TJson.G(first, "repeat"), 1) + TJson.D(TJson.G(r, "repeat"), 1); continue; }
                    seen[k] = r; o.Add(r);
                }
                return o;
            }

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
                    // E12：逐字节写回的原文件（edit_json / set_material 的豁免核对要用），reload 以后还要
                    { "restoredBytes", c.restoredBytes.ToDictionary(kv => kv.Key, kv => (object)System.Convert.ToBase64String(kv.Value)) },
                };
                if (c.before != null)
                    d["before"] = new Dictionary<string, object>
                    {
                        { "assets", c.before.assets.ToDictionary(kv => kv.Key, kv => (object)new List<object> { (double)kv.Value.Key, kv.Value.Value.ToString(IC) }) },
                        { "settings", c.before.settings.ToDictionary(kv => kv.Key, kv => (object)kv.Value) },
                    };
                File.WriteAllText(P(c.outDir, "ctx.json"), TJson.Write(d, false), new UTF8Encoding(false));
                var sb = new StringBuilder();
                foreach (var r in Dedupe(c.log.Rows())) sb.Append(TJson.Write(r, false)).Append('\n');
                File.WriteAllText(P(c.outDir, "console.jsonl"), sb.ToString(), new UTF8Encoding(false));
                string br = P(c.outDir, "console_bridge.jsonl");
                if (File.Exists(br)) File.Delete(br);           // 已经并进 ctx.log 了
            }

            static List<Dictionary<string, object>> ReadJsonl(string path)
            {
                var rows = new List<Dictionary<string, object>>();
                if (!File.Exists(path)) return rows;
                foreach (var line in File.ReadAllLines(path, Encoding.UTF8))
                    if (line.Trim().Length > 0) { try { var r = TJson.M(TJson.Parse(line)); if (r != null) rows.Add(r); } catch { } }
                return rows;
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
                foreach (var kv in TJson.M(TJson.G(d, "restoredBytes")) ?? new Dictionary<string, object>())
                    try { c.restoredBytes[kv.Key] = System.Convert.FromBase64String(TJson.S(kv.Value, "")); } catch { }
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
                // E9：存下的 Console + reload 之前桥里没存的那一段，按顺序接上（去重）
                var rows = ReadJsonl(P(outDir, "console.jsonl"));
                rows.AddRange(ReadJsonl(P(outDir, "console_bridge.jsonl")));
                c.log.Preload(Dedupe(rows));
                return c;
            }

            static void Fill(List<Dictionary<string, object>> dst, Dictionary<string, object> d, string k)
            {
                foreach (var o in TJson.L(TJson.G(d, k))) { var m = TJson.M(o); if (m != null) dst.Add(m); }
            }
        }
    }

    public static class PlayReport
    {
        public const int PW = 960, PH = 320;
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        public static List<Dictionary<string, object>> Records(Ctx ctx) { return ctx.play; }

        /// <summary>1.2.1：Play 阶段的检查项（Checks.Evaluate 调）：PPv2 生效、每段漏拍不超过门槛。</summary>
        public static List<Dictionary<string, object>> CheckDefs(Ctx ctx)
        {
            var l = new List<Dictionary<string, object>>();
            if (ctx.play.Count == 0 && !ctx.metrics.ContainsKey("play.ppv2_effective")) return l;
            l.Add(new Dictionary<string, object> { { "id", "play_ppv2_effective" }, { "metric", "play.ppv2_effective" }, { "op", "==" }, { "value", 1.0 }, { "gate", true }, { "why", "Play 里拍的画面经过了 PPv2（开 / 关各渲一张，要不一样）；没生效，曲线就是没调色的画面" } });
            foreach (var r in ctx.play)
            {
                string pre = (string)r["group"] == "sweep" ? "sweep." + (string)r["id"] : "probe." + (string)r["id"] + "." + (string)r["variant"];
                double mx = r.ContainsKey("max_missed_frac") ? TJson.D(r["max_missed_frac"], 0.1) : 0.1;
                l.Add(new Dictionary<string, object> { { "id", pre.Replace('.', '_') + "_missed" }, { "metric", pre + ".missed_frac" }, { "op", "<=" }, { "value", mx }, { "gate", true }, { "why", "漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信" } });
            }
            return l;
        }

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
            for (int i = 1; i < rows.Count; i++) Line(img, X(rows[i - 1][2]), Y(rows[i - 1][3]), X(rows[i][2]), Y(rows[i][3]), line);
            foreach (var r in rows) { int x = X(r[2]), y = Y(r[3]); for (int dy = -1; dy <= 1; dy++) for (int dx = -1; dx <= 1; dx++) Put(img, x + dx, y + dy, dot); }
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
                sb.AppendLine("| # | 交接 | t | 类别 | 相邻两张最大差 EV | 0.25 s 升 | 1 s 升 | 2 s 升 | 漏拍比例 | 图 |");
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
                                  M(p + ".missed_frac") + " | `" + (string)r["dir"] + "/` |");
                }
                sb.AppendLine();
            }
            var probes = ctx.play.Where(r => (string)r["group"] == "probe").ToList();
            if (probes.Count > 0)
            {
                sb.AppendLine("## 闪烁探测（Play 模式，30 fps）");
                sb.AppendLine("帧间的量只用有效的相邻两帧（中间没漏拍、实际间隔 ≤ 1.5 × 1/fps）；每个变体之前，上一个变体关掉的东西逆序还原。一次跑一组变体：每个变体把同一段重拍一遍，只差 `toggles` 里关掉的那一样。看 `max_step_ev` 和 `flicker_px_frac` 哪个变体明显变小；局部的闪看每个变体的 `flicker_count.png`（相邻帧差 > 24 的次数）和 `diff_*_heat.png`（差最大的 8 对）。**探测不改、不删任何东西**：退出 Play 就全回去了。");
                sb.AppendLine();
                sb.AppendLine("| 探测 | 变体 | 关了什么 | 相邻两帧最大差 EV | > 0.1 EV 的次数 | 局部闪的像素占比 | 实际帧率 / 漏拍比例 | 图 |");
                sb.AppendLine("|---|---|---|---|---|---|---|---|");
                foreach (var r in probes)
                {
                    string p = "probe." + (string)r["id"] + "." + (string)r["variant"];
                    var tg = TJson.Sa(r["toggles"]);
                    sb.AppendLine("| " + (string)r["id"] + " | " + (string)r["variant"] + " | " + (tg.Count == 0 ? "（都开着）" : string.Join("；", tg.ToArray()).Replace("|", "/")) + " | " +
                                  M(p + ".max_step_ev") + " | " + M(p + ".steps_over_01ev") + " | " + M(p + ".flicker_px_frac") + " | " + M(p + ".achieved_fps") + " / " + M(p + ".missed_frac") + " | `" + (string)r["dir"] + "/` |");
                }
                sb.AppendLine();
            }
        }
    }
}
