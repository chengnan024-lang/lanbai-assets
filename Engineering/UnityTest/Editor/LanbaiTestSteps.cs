// 蓝白 · Unity 测试工具 · 步骤
// 每一步是测试定义里的一个对象 {"type": ..., ...}，按顺序做；字符串里的 {t} 换成当时的时间。
//   menu          {"path": "蓝白/Gate Clouds/Build"}
//   method        {"name": "Lanbai.Tests.LB_GateTest.Build", "arg": "155.1"}  或 "args": [...]（静态方法；返回 "ERROR" 开头的字符串算失败；
//                 "expect": "solo S6" = 返回的字符串里必须有这几个字）
//   call          {"object": "Act06_Driver", "component": "LanbaiAct06Driver", "method": "Evaluate", "args": ["{t}"]}（场景里组件的方法）
//   set_field     {"object": "**/Act06_Driver", "component": "LanbaiAct06Driver", "field": "writeRenderSettings", "value": true}（公开字段；不存场景）
//   set_active    {"path": "GateRoot/GateClouds/Deck", "value": false}
//   set_field_objects_active {"component": "LB_Journey", "fields": ["gateGroup", "*Group", "seaA"], "value": false, "optional": true}
//                 组件上这些字段（GameObject / GameObject[] / Component / Component[]）指着的物体开关；字段名可以用 *；
//                 optional：场景里没有这个组件 / 字段时只记一句，不算失败
//   set_renderer  {"path": "...", "value": false}
//   set_light     {"path": "Gate_Lights/Fill_from_below", "render_mode": "ForcePixel|ForceVertex|Auto", "culling_mask": 0, "intensity": 1}
//   set_material  {"asset": "...mat" | "find": "M_GateAirSky" | "under": "GateRoot/GateClouds/Cards" | "renderer_name": "Rear_*"（renderer 或它的父物体）, "props": {"_BackBand": 1.25}}
//                 几种选法可以同时写，取并集；只改有这个属性的材质。
//   edit_json     {"asset": "Assets/.../GateClouds_Layout.json", "set": {"deck.quality": "auto_lite"}}（原文件逐字节备份，结束时写回）
//   assert_log    {"contains": "...", "absent": "..."}（这一组步骤开始以后的 Console）
//   assert_active {"path": "...", "value": true} / assert_renderer {"path": "...", "value": false} / assert_object {"path": "..."}
//   assert_no_component {"component": "LanbaiTearParams"}（整个场景里不许有）
//   assert_light  {"path": "...", "culling_mask": 0, "render_mode": "NotImportant", "enabled": true}
//   collect       {"file": "LanbaiReports/xxx.md"} 或 {"script": "LB_GateTest_Run"}：把文件原样拷进输出的 collected/
//   save_scene_copy {"name": "GateTest_play.unity"}：把当前场景另存一份到沙盒（原场景不存、不动）
//   open_scene    {"path": "Assets/_LanbaiTest/GateTest_play.unity"}（只开沙盒里的）
//   add_component {"object": "VRCWorld", "create": true, "component": "VRC.SDK3.Components.VRCSceneDescriptor", "position": [0,0,0]}（只在沙盒里的场景）
//   save_scene    存当前场景（只存沙盒里的）
//   refresh       AssetDatabase.Refresh
//   log           {"text": "..."}
// 共同字段：id、why（写进报告）、restore（true = 结束时改回；build 里默认不改回，截图 / 性能 / 序列的 before 里一律改回）、continue_on_error。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Debug = UnityEngine.Debug;
using Object = UnityEngine.Object;

namespace Lanbai.Test
{
    public static class Steps
    {
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        /// <summary>按顺序跑一组步骤。stopOnError：一步失败就把后面的标成 skipped。forceRestore：改的东西都登记进改回栈（before / 性能状态用，由调用的地方用完后改回）。返回是否全部成功。</summary>
        public static bool RunList(Ctx ctx, List<object> list, string phase, float? t, bool stopOnError, bool forceRestore = false, bool quiet = false)
        {
            bool allOk = true, stopped = false;
            int logMark = ctx.log.Count;
            for (int i = 0; i < list.Count; i++)
            {
                var st = TJson.M(list[i]);
                if (st == null) continue;
                string type = TJson.S(TJson.G(st, "type"), "?");
                var rec = new Dictionary<string, object>
                {
                    { "phase", phase }, { "index", (double)i }, { "type", type }, { "desc", Describe(st, t) }
                };
                if (TJson.Has(st, "id")) rec["id"] = TJson.G(st, "id");
                if (TJson.Has(st, "why")) rec["why"] = TJson.G(st, "why");
                if (t.HasValue) rec["t"] = (double)t.Value;
                if (!quiet) ctx.steps.Add(rec);                  // quiet：序列里每帧定时间的那些步骤，只有失败才记
                if (stopped) { rec["status"] = "skipped"; continue; }
                bool restore = TJson.Has(st, "restore") ? TJson.B(TJson.G(st, "restore")) : (forceRestore || type == "edit_json");
                var sw = Stopwatch.StartNew();
                try
                {
                    EditorUtility.DisplayProgressBar("蓝白测试 " + ctx.testId, phase + " " + (i + 1) + "/" + list.Count + "：" + rec["desc"], (i + 0.5f) / Math.Max(1, list.Count));
                    string outp = One(ctx, st, t, restore, logMark);
                    rec["status"] = "ok";
                    if (!string.IsNullOrEmpty(outp)) rec["out"] = Trim(outp, 6000);
                }
                catch (Exception e)
                {
                    var inner = e is TargetInvocationException && e.InnerException != null ? e.InnerException : e;
                    // 被调的搭建脚本 / 菜单抛的异常（经过反射）和步骤自己判的失败，都算“这一步没过”；工具自己代码里的异常算工具 bug（退出码 3）
                    if (!(inner is StepException) && !(e is TargetInvocationException) && !(e is ArgumentException) && !(e is FormatException)) ctx.ToolError("步骤 " + type, inner);
                    rec["status"] = "error";
                    rec["error"] = (inner is StepException ? "" : inner.GetType().Name + ": ") + inner.Message;
                    if (!(inner is StepException)) rec["stack"] = Trim(inner.StackTrace ?? "", 4000);
                    Debug.LogWarning(LogCapture.TAG + " 步骤失败 " + phase + "[" + i + "] " + rec["desc"] + "：" + rec["error"]);
                    allOk = false;
                    if (quiet) ctx.steps.Add(rec);
                    if (stopOnError && !TJson.B(TJson.G(st, "continue_on_error"))) stopped = true;
                }
                rec["ms"] = Math.Round(sw.Elapsed.TotalMilliseconds, 1);
            }
            return allOk;
        }

        static string Trim(string s, int n) { return s.Length <= n ? s : s.Substring(0, n) + " …（截断，全文看 console.jsonl）"; }

        public static string Fmt(string s, float? t)
        {
            if (s == null) return null;
            return t.HasValue ? s.Replace("{t}", t.Value.ToString("0.###", IC)) : s;
        }

        static string Describe(Dictionary<string, object> st, float? t)
        {
            string type = TJson.S(TJson.G(st, "type"), "?");
            switch (type)
            {
                case "menu": return "菜单 " + TJson.S(TJson.G(st, "path"));
                case "method": return TJson.S(TJson.G(st, "name")) + "(" + Fmt(TJson.S(TJson.G(st, "arg")) ?? string.Join(", ", TJson.Sa(TJson.G(st, "args")).ToArray()), t) + ")";
                case "call": return TJson.S(TJson.G(st, "object")) + "." + TJson.S(TJson.G(st, "component")) + "." + TJson.S(TJson.G(st, "method")) + "(" + Fmt(string.Join(", ", TJson.Sa(TJson.G(st, "args")).ToArray()), t) + ")";
                case "set_material":
                    {
                        string sel = TJson.S(TJson.G(st, "asset")) ?? TJson.S(TJson.G(st, "find")) ?? TJson.S(TJson.G(st, "under")) ?? TJson.S(TJson.G(st, "renderer_name"));
                        var props = TJson.M(TJson.G(st, "props"));
                        return "材质 " + sel + "：" + (props == null ? "" : string.Join("，", props.Select(kv => kv.Key + " = " + TJson.Write(kv.Value, false)).ToArray()));
                    }
                case "edit_json":
                    {
                        var set = TJson.M(TJson.G(st, "set"));
                        return "临时改 " + TJson.S(TJson.G(st, "asset")) + "：" + (set == null ? "" : string.Join("，", set.Select(kv => kv.Key + " = " + TJson.Write(kv.Value, false)).ToArray()));
                    }
                case "log": return TJson.S(TJson.G(st, "text"));
                default: return type + " " + (TJson.S(TJson.G(st, "path")) ?? "") + (TJson.Has(st, "value") ? " = " + TJson.Write(TJson.G(st, "value"), false) : "");
            }
        }

        static string One(Ctx ctx, Dictionary<string, object> st, float? t, bool restore, int logMark)
        {
            string type = TJson.S(TJson.G(st, "type"));
            switch (type)
            {
                case "menu":
                    {
                        string p = TJson.S(TJson.G(st, "path"));
                        if (!EditorApplication.ExecuteMenuItem(p)) throw new StepException("菜单不存在或执行失败：" + p);
                        if (Lanbai.Udon.LanbaiUdonPrograms.Busy)
                            throw new StepException("菜单 " + p + " 在排队等 U# 程序资产初始化，没有马上搭：测试定义的 udon_programs 少列了它要的脚本（看 Console 里 [Lanbai U#] 那一条）");
                        return "执行了菜单 " + p;
                    }
                case "method": return Method(ctx, st, t);
                case "call": return Call(st, t);
                case "set_active":
                    {
                        var tr = Need(TJson.S(TJson.G(st, "path")));
                        bool v = TJson.B(TJson.G(st, "value")), old = tr.gameObject.activeSelf;
                        tr.gameObject.SetActive(v);
                        if (restore) ctx.undo.Push("SetActive " + tr.name, () => { if (tr != null) tr.gameObject.SetActive(old); });
                        return Scenes.PathOf(tr) + " activeSelf " + old + " → " + v;
                    }
                case "set_renderer":
                    {
                        var tr = Need(TJson.S(TJson.G(st, "path")));
                        var r = tr.GetComponent<Renderer>();
                        if (r == null) throw new StepException(Scenes.PathOf(tr) + " 上没有 Renderer");
                        bool v = TJson.B(TJson.G(st, "value")), old = r.enabled;
                        r.enabled = v;
                        if (restore) ctx.undo.Push("Renderer " + tr.name, () => { if (r != null) r.enabled = old; });
                        return Scenes.PathOf(tr) + " Renderer.enabled " + old + " → " + v;
                    }
                case "set_light": return SetLight(ctx, st, restore);
                case "set_field_objects_active": return SetFieldObjectsActive(ctx, st, restore);
                case "set_field": return SetField(ctx, st, restore);
                case "set_material": return SetMaterial(ctx, st, t, restore);
                case "edit_json": return EditJson(ctx, st, restore);
                case "assert_log":
                    {
                        var msgs = new List<string>();
                        foreach (var s in TJson.Sa(TJson.G(st, "contains")))
                            if (!ctx.log.ContainsSince(logMark, s)) throw new StepException("Console 里没有「" + s + "」");
                            else msgs.Add("有「" + s + "」");
                        foreach (var s in TJson.Sa(TJson.G(st, "absent")))
                            if (ctx.log.ContainsSince(logMark, s)) throw new StepException("Console 里出现了「" + s + "」");
                            else msgs.Add("没有「" + s + "」");
                        return string.Join("；", msgs.ToArray());
                    }
                case "assert_object":
                    Need(TJson.S(TJson.G(st, "path")));
                    return "在";
                case "assert_active":
                    {
                        var tr = Need(TJson.S(TJson.G(st, "path")));
                        bool want = TJson.B(TJson.G(st, "value"), true);
                        if (tr.gameObject.activeInHierarchy != want) throw new StepException(Scenes.PathOf(tr) + " activeInHierarchy 是 " + tr.gameObject.activeInHierarchy + "，要 " + want);
                        return Scenes.PathOf(tr) + " activeInHierarchy " + want;
                    }
                case "assert_renderer":
                    {
                        var tr = Need(TJson.S(TJson.G(st, "path")));
                        var r = tr.GetComponent<Renderer>();
                        bool want = TJson.B(TJson.G(st, "value"), true);
                        bool on = r != null && r.enabled;
                        if (on != want) throw new StepException(Scenes.PathOf(tr) + " 的 Renderer " + (r == null ? "没有" : "enabled = " + r.enabled) + "，要 " + want);
                        return Scenes.PathOf(tr) + " Renderer.enabled " + on;
                    }
                case "assert_no_component":
                    {
                        string cn = TJson.S(TJson.G(st, "component"));
                        var hits = new List<string>();
                        foreach (var g in Scenes.AllRoots())
                            foreach (var c in g.GetComponentsInChildren<Component>(true))
                                if (c != null && (c.GetType().Name == cn || c.GetType().FullName == cn)) hits.Add(Scenes.PathOf(c.transform));
                        if (hits.Count > 0) throw new StepException("场景里有 " + cn + "：" + string.Join("、", hits.ToArray()));
                        return "场景里没有 " + cn;
                    }
                case "assert_light":
                    {
                        var tr = Need(TJson.S(TJson.G(st, "path")));
                        var l = tr.GetComponent<Light>();
                        if (l == null) throw new StepException(Scenes.PathOf(tr) + " 上没有 Light");
                        var bad = new List<string>();
                        if (TJson.Has(st, "culling_mask") && l.cullingMask != TJson.I(TJson.G(st, "culling_mask"))) bad.Add("cullingMask " + l.cullingMask + "，要 " + TJson.I(TJson.G(st, "culling_mask")));
                        if (TJson.Has(st, "render_mode"))
                        {
                            string rm = TJson.S(TJson.G(st, "render_mode"));
                            if (rm == "NotImportant") rm = "ForceVertex";
                            if (rm == "Important") rm = "ForcePixel";
                            if (!string.Equals(l.renderMode.ToString(), rm, StringComparison.OrdinalIgnoreCase)) bad.Add("renderMode " + l.renderMode + "，要 " + rm);
                        }
                        if (TJson.Has(st, "enabled") && l.enabled != TJson.B(TJson.G(st, "enabled"))) bad.Add("enabled " + l.enabled);
                        if (bad.Count > 0) throw new StepException(Scenes.PathOf(tr) + "：" + string.Join("；", bad.ToArray()));
                        return Scenes.PathOf(tr) + "：cullingMask " + l.cullingMask + "，renderMode " + l.renderMode + "，强度 " + l.intensity.ToString("0.###", IC) + "，颜色 #" + ColorUtility.ToHtmlStringRGB(l.color);
                    }
                case "collect":
                    {
                        string f = TJson.S(TJson.G(st, "file"));
                        string sc = TJson.S(TJson.G(st, "script"));
                        if (sc != null)
                        {
                            f = null;
                            foreach (var g in AssetDatabase.FindAssets(sc + " t:MonoScript"))
                            {
                                string ap = AssetDatabase.GUIDToAssetPath(g);
                                if (Path.GetFileNameWithoutExtension(ap) == sc) { f = ap; break; }
                            }
                            if (f == null) throw new StepException("找不到脚本 " + sc);
                        }
                        if (f == null || !File.Exists(f)) throw new StepException("文件不在：" + f);
                        string rel = "collected/" + Path.GetFileName(f);
                        File.Copy(f, ctx.Out(rel), true);
                        ctx.AddFile(rel);
                        return f + " → " + rel;
                    }
                case "save_scene_copy":
                    {
                        string name = Path.GetFileName(TJson.S(TJson.G(st, "name"), "copy.unity"));
                        string dst = Sandbox.DIR + "/" + name;
                        var sc = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
                        if (!EditorSceneManager.SaveScene(sc, dst, true)) throw new StepException("另存到沙盒失败：" + dst);
                        return sc.path + " 另存一份到 " + dst + "（原场景没存）";
                    }
                case "open_scene":
                    {
                        string p = TJson.S(TJson.G(st, "path"));
                        if (p == null || !p.StartsWith(Sandbox.DIR + "/", StringComparison.Ordinal)) throw new StepException("open_scene 只开沙盒里的场景：" + p);
                        var cur = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
                        // 当前场景的改动丢掉（工具不存场景；要留的已经另存进沙盒了）
                        EditorSceneManager.OpenScene(p, OpenSceneMode.Single);
                        ctx.scenePath = p;
                        ctx.lastT = null;
                        return "打开 " + p + "（" + cur.path + " 的改动没存）";
                    }
                case "add_component":
                    {
                        RequireSandboxScene("add_component");
                        string on = TJson.S(TJson.G(st, "object"));
                        var tr = Scenes.Find(on);
                        if (tr == null && TJson.B(TJson.G(st, "create"))) tr = new GameObject(on).transform;
                        if (tr == null) throw new StepException("场景里没有 " + on);
                        var pos = TJson.Fa(TJson.G(st, "position"));
                        if (pos != null && pos.Length == 3) tr.position = new Vector3(pos[0], pos[1], pos[2]);
                        string cn = TJson.S(TJson.G(st, "component"));
                        var ct = Preflight.FindType(cn);
                        if (ct == null || !typeof(Component).IsAssignableFrom(ct)) throw new StepException("找不到组件类型 " + cn);
                        if (tr.GetComponent(ct) != null) return Scenes.PathOf(tr) + " 上已经有 " + ct.Name;
                        tr.gameObject.AddComponent(ct);
                        return Scenes.PathOf(tr) + " 加了 " + ct.FullName;
                    }
                case "save_scene":
                    {
                        RequireSandboxScene("save_scene");
                        var sc = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
                        if (!EditorSceneManager.SaveScene(sc)) throw new StepException("存不了 " + sc.path);
                        return "存了 " + sc.path + "（沙盒里）";
                    }
                case "refresh":
                    AssetDatabase.Refresh();
                    return "AssetDatabase.Refresh";
                case "log":
                    ctx.Info(Fmt(TJson.S(TJson.G(st, "text")), t));
                    return null;
                default:
                    throw new StepException("不认识的步骤类型 " + type);
            }
        }

        static void RequireSandboxScene(string what)
        {
            var sc = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if (!sc.path.StartsWith(Sandbox.DIR + "/", StringComparison.Ordinal))
                throw new StepException(what + " 只能在沙盒里的场景上做，当前场景是 " + (string.IsNullOrEmpty(sc.path) ? "（未命名）" : sc.path));
        }

        static Transform Need(string path)
        {
            var tr = Scenes.Find(path);
            if (tr == null) throw new StepException("场景里没有 " + path);
            return tr;
        }

        // ── 静态方法 / 组件方法 ─────────────────────────────────────
        static string Method(Ctx ctx, Dictionary<string, object> st, float? t)
        {
            string full = TJson.S(TJson.G(st, "name"));
            int k = full.LastIndexOf('.');
            if (k <= 0) throw new StepException("method 要写成 类型全名.方法名：" + full);
            var type = Preflight.FindType(full.Substring(0, k));
            if (type == null) throw new StepException("找不到类型 " + full.Substring(0, k));
            var args = Args(st, t);
            var mi = Pick(type.GetMethods(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic), full.Substring(k + 1), args.Count);
            if (mi == null) throw new StepException(type.FullName + " 上没有接受 " + args.Count + " 个参数的静态方法 " + full.Substring(k + 1));
            object ret = mi.Invoke(null, Convert(mi, args));
            return Ret(st, ret);
        }

        static string Call(Dictionary<string, object> st, float? t)
        {
            var tr = Need(TJson.S(TJson.G(st, "object")));
            string cn = TJson.S(TJson.G(st, "component"));
            Component comp = null;
            foreach (var c in tr.GetComponents<Component>())
                if (c != null && (c.GetType().Name == cn || c.GetType().FullName == cn)) { comp = c; break; }
            if (comp == null) throw new StepException(Scenes.PathOf(tr) + " 上没有组件 " + cn);
            var args = Args(st, t);
            string mn = TJson.S(TJson.G(st, "method"));
            var mi = Pick(comp.GetType().GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic), mn, args.Count);
            if (mi == null) throw new StepException(cn + " 上没有接受 " + args.Count + " 个参数的方法 " + mn);
            object ret = mi.Invoke(comp, Convert(mi, args));
            return Ret(st, ret) ?? (cn + "." + mn + " 跑完");
        }

        static string SetFieldObjectsActive(Ctx ctx, Dictionary<string, object> st, bool restore)
        {
            string cn = TJson.S(TJson.G(st, "component"));
            bool optional = TJson.B(TJson.G(st, "optional")), v = TJson.B(TJson.G(st, "value"));
            Component comp = null;
            foreach (var g in Scenes.AllRoots())
            {
                foreach (var c in g.GetComponentsInChildren<Component>(true))
                    if (c != null && (c.GetType().Name == cn || c.GetType().FullName == cn)) { comp = c; break; }
                if (comp != null) break;
            }
            if (comp == null)
            {
                if (optional) return "场景里没有 " + cn + "（optional，跳过）";
                throw new StepException("场景里没有组件 " + cn);
            }
            var pats = TJson.Sa(TJson.G(st, "fields")).Select(p => new Regex("^" + Regex.Escape(p).Replace("\\*", ".*") + "$")).ToList();
            var said = new List<string>();
            foreach (var f in comp.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (!pats.Any(r => r.IsMatch(f.Name))) continue;
                var objs = new List<GameObject>();
                object val = f.GetValue(comp);
                if (val is GameObject) objs.Add((GameObject)val);
                else if (val is Component) objs.Add(((Component)val).gameObject);
                else if (val is Array)
                    foreach (var o in (Array)val)
                    {
                        if (o is GameObject) objs.Add((GameObject)o);
                        else if (o is Component) objs.Add(((Component)o).gameObject);
                    }
                foreach (var go in objs)
                {
                    if (go == null) continue;
                    bool old = go.activeSelf;
                    go.SetActive(v);
                    var g2 = go;
                    if (restore) ctx.undo.Push("SetActive " + go.name, () => { if (g2 != null) g2.SetActive(old); });
                    said.Add(f.Name + ":" + go.name + " " + old + " → " + v);
                }
            }
            if (said.Count == 0)
            {
                if (optional) return cn + " 上没有对得上 " + string.Join("、", TJson.Sa(TJson.G(st, "fields")).ToArray()) + " 的物体字段（optional，跳过）";
                throw new StepException(cn + " 上没有对得上的物体字段");
            }
            return Scenes.PathOf(comp.transform) + " " + cn + "：" + string.Join("；", said.ToArray());
        }

        static string SetField(Ctx ctx, Dictionary<string, object> st, bool restore)
        {
            var tr = Need(TJson.S(TJson.G(st, "object")));
            string cn = TJson.S(TJson.G(st, "component")), fn = TJson.S(TJson.G(st, "field"));
            Component comp = tr.GetComponents<Component>().FirstOrDefault(c => c != null && (c.GetType().Name == cn || c.GetType().FullName == cn));
            if (comp == null) throw new StepException(Scenes.PathOf(tr) + " 上没有组件 " + cn);
            var fi = comp.GetType().GetField(fn, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            if (fi == null) throw new StepException(cn + " 没有字段 " + fn);
            object old = fi.GetValue(comp), v = TJson.G(st, "value");
            object nv;
            if (fi.FieldType == typeof(bool)) nv = TJson.B(v);
            else if (fi.FieldType == typeof(float)) nv = TJson.F(v);
            else if (fi.FieldType == typeof(int)) nv = TJson.I(v);
            else if (fi.FieldType == typeof(string)) nv = TJson.S(v);
            else throw new StepException(cn + "." + fn + " 是 " + fi.FieldType.Name + "，set_field 只改 bool / float / int / string");
            fi.SetValue(comp, nv);
            if (restore) ctx.undo.Push(cn + "." + fn, () => { if (comp != null) fi.SetValue(comp, old); });
            return Scenes.PathOf(tr) + " " + cn + "." + fn + " " + old + " → " + nv;
        }

        static List<object> Args(Dictionary<string, object> st, float? t)
        {
            var l = new List<object>();
            if (TJson.Has(st, "arg"))
            {
                var a = TJson.G(st, "arg");
                l.Add(a is double ? ((double)a).ToString("R", IC) : Fmt(TJson.S(a), t));
            }
            else foreach (var a in TJson.L(TJson.G(st, "args"))) l.Add(a is string ? (object)Fmt((string)a, t) : a);
            return l;
        }

        static MethodInfo Pick(MethodInfo[] all, string name, int n)
        {
            return all.Where(m => m.Name == name && m.GetParameters().Length == n && !m.IsGenericMethodDefinition)
                      .OrderBy(m => m.GetParameters().Count(p => p.ParameterType != typeof(string))).FirstOrDefault();
        }

        static object[] Convert(MethodInfo mi, List<object> a)
        {
            var ps = mi.GetParameters();
            var r = new object[ps.Length];
            for (int i = 0; i < ps.Length; i++)
            {
                var pt = ps[i].ParameterType;
                object v = a[i];
                if (pt == typeof(string)) r[i] = TJson.S(v);
                else if (pt == typeof(float)) r[i] = TJson.F(v);
                else if (pt == typeof(double)) r[i] = TJson.D(v);
                else if (pt == typeof(int)) r[i] = TJson.I(v);
                else if (pt == typeof(bool)) r[i] = v is string ? ((string)v == "true") : TJson.B(v);
                else throw new StepException(mi.Name + " 的第 " + (i + 1) + " 个参数是 " + pt.Name + "，测试定义传不了");
            }
            return r;
        }

        static string Ret(Dictionary<string, object> st, object ret)
        {
            if (ret == null) return null;
            string s = ret as string ?? ret.ToString();
            string errPrefix = TJson.S(TJson.G(st, "error_prefix"), "ERROR");
            if (s.TrimStart().StartsWith(errPrefix, StringComparison.Ordinal)) throw new StepException(s);
            string expect = TJson.S(TJson.G(st, "expect"));
            if (expect != null && s.IndexOf(expect, StringComparison.Ordinal) < 0) throw new StepException("返回里没有「" + expect + "」：" + s);
            return s;
        }

        // ── 灯 ──────────────────────────────────────────────────────
        static string SetLight(Ctx ctx, Dictionary<string, object> st, bool restore)
        {
            var tr = Need(TJson.S(TJson.G(st, "path")));
            var l = tr.GetComponent<Light>();
            if (l == null) throw new StepException(Scenes.PathOf(tr) + " 上没有 Light");
            var old = new { rm = l.renderMode, cm = l.cullingMask, it = l.intensity, en = l.enabled };
            var said = new List<string>();
            string rm = TJson.S(TJson.G(st, "render_mode"));
            if (rm != null)
            {
                // Inspector 上的 “Not Important” = LightRenderMode.ForceVertex，“Important” = ForcePixel
                if (rm == "NotImportant") rm = "ForceVertex";
                if (rm == "Important") rm = "ForcePixel";
                l.renderMode = (LightRenderMode)Enum.Parse(typeof(LightRenderMode), rm, true);
                said.Add("renderMode " + old.rm + " → " + l.renderMode);
            }
            if (TJson.Has(st, "culling_mask")) { l.cullingMask = TJson.I(TJson.G(st, "culling_mask")); said.Add("cullingMask " + old.cm + " → " + l.cullingMask); }
            if (TJson.Has(st, "intensity")) { l.intensity = TJson.F(TJson.G(st, "intensity")); said.Add("intensity " + old.it + " → " + l.intensity); }
            if (TJson.Has(st, "enabled")) { l.enabled = TJson.B(TJson.G(st, "enabled")); said.Add("enabled " + old.en + " → " + l.enabled); }
            if (restore) ctx.undo.Push("Light " + tr.name, () => { if (l != null) { l.renderMode = old.rm; l.cullingMask = old.cm; l.intensity = old.it; l.enabled = old.en; } });
            return Scenes.PathOf(tr) + "：" + string.Join("，", said.ToArray());
        }

        // ── 材质 ────────────────────────────────────────────────────
        static string SetMaterial(Ctx ctx, Dictionary<string, object> st, float? t, bool restore)
        {
            var mats = SelectMaterials(st);
            var props = TJson.M(TJson.G(st, "props"));
            if (props == null || props.Count == 0) throw new StepException("set_material 没写 props");
            int changed = 0;
            var said = new List<string>();
            foreach (var m in mats)
            {
                string ap = AssetDatabase.GetAssetPath(m);
                if (!string.IsNullOrEmpty(ap) && !ctx.toolTouched.Contains(ap)) ctx.toolTouched.Add(ap);
                foreach (var kv in props)
                {
                    if (!m.HasProperty(kv.Key)) continue;
                    int idx = m.shader.FindPropertyIndex(kv.Key);
                    var pt = idx >= 0 ? m.shader.GetPropertyType(idx) : ShaderPropertyType.Float;
                    var mm = m; string key = kv.Key;
                    if (pt == ShaderPropertyType.Color || pt == ShaderPropertyType.Vector)
                    {
                        var a = TJson.Fa(kv.Value);
                        if (a == null || a.Length < 3) throw new StepException(m.name + "." + key + " 要 3 或 4 个数");
                        var v = new Vector4(a[0], a[1], a[2], a.Length > 3 ? a[3] : (pt == ShaderPropertyType.Color ? 1f : 0f));
                        var old = m.GetVector(key);
                        if (pt == ShaderPropertyType.Color) m.SetColor(key, v); else m.SetVector(key, v);
                        if (restore) ctx.undo.Push(m.name + "." + key, () => { if (mm != null) { if (pt == ShaderPropertyType.Color) mm.SetColor(key, old); else mm.SetVector(key, old); } });
                        said.Add(m.name + "." + key + " " + old + " → " + v);
                    }
                    else if (pt == ShaderPropertyType.Texture) throw new StepException(key + " 是贴图，set_material 不改贴图");
                    else
                    {
                        float v = TJson.F(kv.Value), old = m.GetFloat(key);
                        m.SetFloat(key, v);
                        if (restore) ctx.undo.Push(m.name + "." + key, () => { if (mm != null) mm.SetFloat(key, old); });
                        said.Add(m.name + "." + key + " " + old.ToString("0.####", IC) + " → " + v.ToString("0.####", IC));
                    }
                    changed++;
                }
            }
            int need = TJson.I(TJson.G(st, "min_count"), 1);
            if (changed < need) throw new StepException("选中的 " + mats.Count + " 个材质里，有这些属性的只有 " + changed + " 处（至少要 " + need + "）");
            return "改了 " + changed + " 处（" + mats.Count + " 个材质）：" + string.Join("；", said.Take(40).ToArray()) + (said.Count > 40 ? " …" : "");
        }

        public static List<Material> SelectMaterials(Dictionary<string, object> st)
        {
            var set = new List<Material>();
            Action<Material> add = m => { if (m != null && !set.Contains(m)) set.Add(m); };
            foreach (var a in TJson.Sa(TJson.G(st, "asset")))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(a);
                if (m == null) throw new StepException("材质不在：" + a);
                add(m);
            }
            foreach (var n in TJson.Sa(TJson.G(st, "find")))
            {
                var hits = AssetDatabase.FindAssets(n + " t:Material").Select(AssetDatabase.GUIDToAssetPath)
                    .Where(p => Path.GetFileNameWithoutExtension(p) == n).ToList();
                if (hits.Count == 0) throw new StepException("工程里找不到材质 " + n);
                if (hits.Count > 1 && !TJson.B(TJson.G(st, "allow_many"))) throw new StepException("材质 " + n + " 有 " + hits.Count + " 个同名：" + string.Join("、", hits.ToArray()) + "（写 asset 路径，或 allow_many）");
                foreach (var p in hits) add(AssetDatabase.LoadAssetAtPath<Material>(p));
            }
            foreach (var u in TJson.Sa(TJson.G(st, "under")))
            {
                var tr = Need(u);
                foreach (var r in tr.GetComponentsInChildren<Renderer>(true)) foreach (var m in r.sharedMaterials) add(m);
            }
            foreach (var pat in TJson.Sa(TJson.G(st, "renderer_name")))
            {
                var rx = new Regex("^" + Regex.Escape(pat).Replace("\\*", ".*").Replace("\\?", ".") + "$");
                foreach (var g in Scenes.AllRoots())
                    foreach (var r in g.GetComponentsInChildren<Renderer>(true))
                    {
                        // renderer 自己或它的任何一层父物体名字对上都算（实例的 renderer 常在子物体 / LOD 上）
                        bool hit = false;
                        for (var tr = r.transform; tr != null && !hit; tr = tr.parent) hit = rx.IsMatch(tr.name);
                        if (hit) foreach (var m in r.sharedMaterials) add(m);
                    }
            }
            return set;
        }

        // ── JSON 文件（比如 GateClouds_Layout.json 的画质档）────────
        static string EditJson(Ctx ctx, Dictionary<string, object> st, bool restore)
        {
            string path = TJson.S(TJson.G(st, "asset"));
            if (path == null || !File.Exists(path)) throw new StepException("文件不在：" + path);
            byte[] orig = File.ReadAllBytes(path);
            string bak = ctx.Out("backup/" + Path.GetFileName(path) + "." + ctx.steps.Count + ".orig");
            File.WriteAllBytes(bak, orig);
            var root = TJson.Parse(File.ReadAllText(path));
            var said = new List<string>();
            foreach (var kv in TJson.M(TJson.G(st, "set")) ?? new Dictionary<string, object>())
            {
                var old = TJson.GetPath(root, kv.Key);
                if (old == null && !TJson.B(TJson.G(st, "allow_new"))) throw new StepException(path + " 里没有 " + kv.Key);
                if (!TJson.SetPath(root, kv.Key, kv.Value)) throw new StepException("写不进 " + kv.Key);
                said.Add(kv.Key + " " + TJson.Write(old, false) + " → " + TJson.Write(kv.Value, false));
            }
            File.WriteAllText(path, TJson.Write(root, true) + "\n", new System.Text.UTF8Encoding(false));
            AssetDatabase.ImportAsset(path);
            if (!ctx.toolTouched.Contains(path)) ctx.toolTouched.Add(path);
            if (restore)
                ctx.undo.Push("JSON " + path, () => { File.WriteAllBytes(path, orig); AssetDatabase.ImportAsset(path); });
            ctx.restoredBytes[path] = orig;
            return path + "：" + string.Join("，", said.ToArray()) + (restore ? "（结束时逐字节写回；原文件备份在 backup/）" : "（不写回）");
        }
    }
}
