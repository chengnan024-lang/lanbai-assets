// 蓝白 · Unity 测试工具 · 预检（只读）、前置条件、沙盒、写入核对、检查项
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Debug = UnityEngine.Debug;

namespace Lanbai.Test
{
    // ─────────────────────────────────────────────────────────────────
    //  预检：版本、编译、场景、git。全部只读；有一条 blocked 就整个 BLOCKED。
    // ─────────────────────────────────────────────────────────────────
    public static class Preflight
    {
        public const string SYNC_RECORD = "Assets/Lanbai/.lanbai_sync.json";
        // 默认要求（D-40a #3）；测试定义的 requires 里写了同名项就以测试定义为准
        static readonly Dictionary<string, string> DEFAULT_PACKAGES = new Dictionary<string, string>
        {
            { "com.vrchat.worlds", "3.10.5" },
            { "com.unity.postprocessing", "3.4.0" },
        };
        const string DEFAULT_UNITY = "2022.3.22f1";

        static void Item(List<Dictionary<string, object>> l, string name, string status, string detail)
        {
            l.Add(new Dictionary<string, object> { { "item", name }, { "status", status }, { "detail", detail } });
        }

        public static void Run(Ctx ctx)
        {
            var P = ctx.preflight;
            var req = TJson.G(ctx.test, "requires");

            // GPU：截图和性能都要真的显卡
            var gdt = SystemInfo.graphicsDeviceType;
            Item(P, "gpu", gdt == GraphicsDeviceType.Null ? "blocked" : "ok",
                SystemInfo.graphicsDeviceName + "（" + gdt + "，" + SystemInfo.graphicsDeviceVersion + "，显存 " + SystemInfo.graphicsMemorySize + " MB）" +
                (gdt == GraphicsDeviceType.Null ? "：没有显卡设备。批处理不要加 -nographics" : ""));

            string wantUnity = TJson.S(TJson.G(req, "unity"), DEFAULT_UNITY);
            Item(P, "unity", Application.unityVersion == wantUnity ? "ok" : "blocked", Application.unityVersion + "（要 " + wantUnity + "）");

            Item(P, "editor_state", EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating ? "blocked" : "ok",
                "Play " + EditorApplication.isPlaying + "，编译中 " + EditorApplication.isCompiling + "，导入中 " + EditorApplication.isUpdating +
                "（要在编辑模式、编译和导入都完成后再跑）");

            Item(P, "color_space", PlayerSettings.colorSpace == ColorSpace.Linear ? "ok" : "blocked", PlayerSettings.colorSpace + "（要 Linear）");

            var pk = new Dictionary<string, string>(DEFAULT_PACKAGES);
            var rp = TJson.M(TJson.G(req, "packages"));
            if (rp != null) foreach (var kv in rp) pk[kv.Key] = TJson.S(kv.Value);
            foreach (var kv in pk)
            {
                string src;
                string v = PackageVersion(kv.Key, out src);
                Item(P, "package:" + kv.Key, v == null ? "blocked" : (v == kv.Value ? "ok" : "blocked"),
                    (v ?? "没装") + "（要 " + kv.Value + "；读自 " + src + "）");
            }

            // UdonSharp：SDK 3.4 起合进 com.vrchat.worlds；单独的包也认
            var usb = FindType("UdonSharp.UdonSharpBehaviour");
            string usrc; string usv = PackageVersion("com.vrchat.udonsharp", out usrc);
            Item(P, "udonsharp", usb != null ? "ok" : "blocked",
                usb != null ? "UdonSharp.UdonSharpBehaviour 在（" + usb.Assembly.GetName().Name + "）" + (usv != null ? "，单独的包 " + usv : "，随 VRChat Worlds SDK") : "找不到 UdonSharp.UdonSharpBehaviour");

            // 编译：开跑前 Console 里的编译错误、scriptCompilationFailed
            int snap = ctx.log.SnapshotConsole();
            // UdonSharp 的编译错误走 Debug.LogError（Console 里是 Error，不是 CompileError），scriptCompilationFailed 也不管它：带 U# 标记的 Error 一并算
            int compileErr = ctx.log.CountWhere(r => LogCapture.Source(r) == "console_snapshot" && (LogCapture.Type(r) == "CompileError" || (LogCapture.Type(r) == "Error" && r.ContainsKey("udonsharp"))));
            ctx.Metric("console.compile_errors_at_start", compileErr);
            bool failed = EditorUtility.scriptCompilationFailed;
            Item(P, "compile", failed || compileErr > 0 ? "blocked" : "ok",
                "scriptCompilationFailed " + failed + "，Console 里的编译错误（含 UdonSharp 的）" + compileErr + " 条" + (snap < 0 ? "（Console 读不到，只看 scriptCompilationFailed）" : "（Console 共 " + snap + " 条，原样在 console.jsonl）"));

            // 打开的场景：有没保存的改动就停，不替人保存也不丢掉
            var dirty = new List<string>();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var s = SceneManager.GetSceneAt(i);
                if (s.isDirty) dirty.Add(string.IsNullOrEmpty(s.path) ? "（未命名场景）" : s.path);
            }
            Item(P, "open_scenes", dirty.Count > 0 ? "blocked" : "ok",
                dirty.Count > 0 ? "这些场景有没保存的改动：" + string.Join("、", dirty.ToArray()) + "。工具不替你保存：自己存或放弃改动（测试场景可以用 蓝白/Test/放弃测试场景的改动）后再跑"
                                : "没有没保存的改动（" + SceneManager.GetActiveScene().path + "）");

            // 沙盒：在、但没有标记文件 = 不是工具建的，不删，停
            bool sbx = Directory.Exists(Sandbox.DIR), mk = File.Exists(Sandbox.MarkerPath);
            Item(P, "sandbox", sbx && !mk ? "blocked" : "ok",
                !sbx ? "没有遗留的沙盒" : (mk ? "有上次遗留的沙盒（有标记），开跑时删掉重建" : Sandbox.DIR + " 在，但没有标记文件 " + Sandbox.MARKER + "：不是本工具建的，不删。请人工看过再处理"));

            // 两套调色：旧的 Assets/Lanbai/Grades/（layer 4）和套件的 Assets/Lanbai/Grading/（layer 22）。只报告，不删
            bool oldG = Directory.Exists("Assets/Lanbai/Grades"), newG = Directory.Exists("Assets/Lanbai/Grading");
            string l4 = LayerMask.LayerToName(4), l22 = LayerMask.LayerToName(22);
            Item(P, "grading", oldG && newG ? "warn" : "info",
                (oldG ? "有旧的 Assets/Lanbai/Grades/" : "没有旧的 Grades/") + "，" + (newG ? "有套件的 Assets/Lanbai/Grading/" : "没有套件的 Grading/") +
                "；layer 4 =「" + l4 + "」，layer 22 =「" + l22 + "」" + (oldG && newG ? "。两套调色都在：工具不删，截图用的是参考相机上的那一套（PostProcessLayer 的 volumeLayer 写在 manifest 的截图记录里）" : ""));

            // 同步记录（仓库提交号从这里来）
            ctx.sync = null;
            if (File.Exists(SYNC_RECORD))
            {
                try { ctx.sync = TJson.M(TJson.Parse(File.ReadAllText(SYNC_RECORD))); } catch (Exception e) { ctx.Warn("同步记录读不懂：" + e.Message); }
            }
            Item(P, "sync_record", ctx.sync != null ? "ok" : "warn",
                ctx.sync != null ? "仓库提交 " + TJson.S(TJson.G(ctx.sync, "repo_commit"), "?") + "（" + TJson.S(TJson.G(ctx.sync, "synced_at"), "?") + " 同步，条目：" + TJson.S(TJson.G(ctx.sync, "entry"), "?") + "）"
                                 : "没有 " + SYNC_RECORD + "：manifest 里的仓库提交号会空着（请用同步脚本拷文件）");

            // 工程是 git 仓库的话，记一下 git status（只读）
            if (Directory.Exists(Path.Combine(ctx.projectDir, ".git")))
            {
                string o = Git(ctx.projectDir, "status --porcelain");
                ctx.gitStatus = o;
                Item(P, "git_status", "info", o == null ? "工程是 git 仓库，但 git 跑不起来" : (o.Trim().Length == 0 ? "干净" : o.Split('\n').Length + " 行改动，原文在 manifest.json"));
            }
            else Item(P, "git_status", "info", "工程不是 git 仓库");

            var bad = P.Where(x => (string)x["status"] == "blocked").Select(x => x["item"] + "：" + x["detail"]).ToList();
            if (bad.Count > 0) throw new BlockedException("预检没过：" + string.Join("；", bad.ToArray()));
        }

        /// <summary>测试自己的前置条件：文件夹、文件、类型、脚本里的补丁、版本标记。缺一样就 BLOCKED（不会算“过”）。</summary>
        public static void Preconditions(Ctx ctx)
        {
            var req = TJson.G(ctx.test, "requires");
            var miss = new List<string>();
            Action<string, bool, string> add = (what, ok, detail) =>
            {
                ctx.preconditions.Add(new Dictionary<string, object> { { "item", what }, { "status", ok ? "ok" : "missing" }, { "detail", detail } });
                if (!ok) miss.Add(what + (string.IsNullOrEmpty(detail) ? "" : "（" + detail + "）"));
            };
            foreach (var f in TJson.Sa(TJson.G(req, "folders"))) add("文件夹 " + f, Directory.Exists(f), "");
            foreach (var f in TJson.Sa(TJson.G(req, "files"))) add("文件 " + f, File.Exists(f), "");
            foreach (var t in TJson.Sa(TJson.G(req, "types"))) add("类型 " + t, FindType(t) != null, "脚本没拷进来或没编译");
            foreach (var m in TJson.Sa(TJson.G(req, "menus")))
                add("菜单 " + m, MenuExists(m), "");
            foreach (var o in TJson.L(TJson.G(req, "file_contains")))
            {
                string file = TJson.S(TJson.G(o, "file"));
                string script = TJson.S(TJson.G(o, "script"));
                string why = TJson.S(TJson.G(o, "why"), "");
                if (script != null) file = FindScript(script);
                string label = (script != null ? "脚本 " + script : "文件 " + file);
                if (file == null || !File.Exists(file)) { add(label, false, "没找到。" + why); continue; }
                string text = File.ReadAllText(file);
                foreach (var s in TJson.Sa(TJson.G(o, "text")))
                    add(label + " 含「" + s + "」", text.Contains(s), why + "（" + file + "）");
                foreach (var s in TJson.Sa(TJson.G(o, "absent")))
                    add(label + " 不含「" + s + "」", !text.Contains(s), why + "（" + file + "）");
            }
            if (miss.Count > 0) throw new BlockedException("前置条件不满足：" + string.Join("；", miss.ToArray()));
        }

        public static void ScenePreconditions(Ctx ctx)
        {
            var miss = new List<string>();
            foreach (var p in TJson.Sa(TJson.G(TJson.G(ctx.test, "requires"), "scene_objects")))
            {
                bool ok = Scenes.Find(p) != null;
                ctx.preconditions.Add(new Dictionary<string, object> { { "item", "场景物体 " + p }, { "status", ok ? "ok" : "missing" }, { "detail", ctx.scenePath } });
                if (!ok) miss.Add(p);
            }
            foreach (var cn in TJson.Sa(TJson.G(TJson.G(ctx.test, "requires"), "scene_components")))
            {
                bool ok = false;
                foreach (var g in Scenes.AllRoots())
                {
                    foreach (var c in g.GetComponentsInChildren<Component>(true))
                        if (c != null && (c.GetType().Name == cn || c.GetType().FullName == cn)) { ok = true; break; }
                    if (ok) break;
                }
                ctx.preconditions.Add(new Dictionary<string, object> { { "item", "场景里的组件 " + cn }, { "status", ok ? "ok" : "missing" }, { "detail", ctx.scenePath } });
                if (!ok) miss.Add("组件 " + cn);
            }
            if (miss.Count > 0) throw new BlockedException("场景 " + ctx.scenePath + " 里缺：" + string.Join("、", miss.ToArray()));
        }

        // ── 只查不改的项目设置（顶点压缩、雾的变体剔除、光强）────────
        public static void ProjectSettingsChecks(Ctx ctx)
        {
            var st = TJson.G(ctx.test, "settings");
            if (st == null) return;
            bool gate = TJson.B(TJson.G(st, "gate"), true);

            var off = TJson.Sa(TJson.G(st, "vertex_compression_off"));
            if (off.Count > 0)
            {
                string how; int mask = VertexCompressionMask(out how);
                var still = new List<string>();
                foreach (var n in off)
                {
                    VertexAttribute va;
                    if (!TryEnum(n, out va)) { still.Add(n + "（名字不认识）"); continue; }
                    if (mask < 0 || (mask & (1 << (int)va)) != 0) still.Add(n);
                }
                Setting(ctx, "vertex_compression_off", still.Count == 0, gate,
                    "Player → Other Settings → Vertex Compression：要关掉 " + string.Join("、", off.ToArray()) + "；" +
                    (mask < 0 ? "读不到（" + how + "）" : "现在的掩码 " + mask + "（" + how + "）" + (still.Count > 0 ? "，还开着：" + string.Join("、", still.ToArray()) : "，都关了")));
            }

            var keep = TJson.Sa(TJson.G(st, "fog_modes_kept"));
            if (keep.Count > 0)
            {
                var g = ReadYaml("ProjectSettings/GraphicsSettings.asset");
                string strip; g.TryGetValue("m_FogStripping", out strip);
                var lost = new List<string>();
                foreach (var m in keep)
                {
                    string v; g.TryGetValue("m_FogKeep" + m, out v);
                    if (strip != "1" || v != "1") lost.Add(m);
                }
                Setting(ctx, "fog_modes_kept", strip == "1" && lost.Count == 0, gate,
                    "Graphics → Shader Stripping → Fog Modes：要 Custom 并保留 " + string.Join("、", keep.ToArray()) + "；现在 m_FogStripping=" + (strip ?? "?") +
                    (strip == "1" ? "（Custom）" : "（Automatic：只留构建场景里用到的模式，测试场景以外的雾可能被剔掉）") +
                    (lost.Count > 0 ? "，缺：" + string.Join("、", lost.ToArray()) : ""));
            }

            if (TJson.Has(st, "lights_linear_intensity"))
            {
                bool want = TJson.B(TJson.G(st, "lights_linear_intensity"));
                Setting(ctx, "lights_linear_intensity", GraphicsSettings.lightsUseLinearIntensity == want, gate,
                    "GraphicsSettings.lightsUseLinearIntensity = " + GraphicsSettings.lightsUseLinearIntensity + "（要 " + want + "）");
            }
        }

        static void Setting(Ctx ctx, string name, bool ok, bool gate, string detail)
        {
            ctx.settings.Add(new Dictionary<string, object> { { "item", name }, { "status", ok ? "ok" : (gate ? "fail" : "warn") }, { "detail", detail }, { "changed_by_tool", false } });
            ctx.Metric("settings." + name, ok ? 1 : 0, detail);
        }

        static bool TryEnum<T>(string s, out T v) where T : struct
        {
            try { v = (T)Enum.Parse(typeof(T), s, true); return true; }
            catch { v = default(T); return false; }
        }

        /// <summary>顶点压缩掩码：先试 PlayerSettings 的属性（反射，2022.3 有），读不到就读 ProjectSettings.asset 原文。位 = 1 &lt;&lt; VertexAttribute。</summary>
        static int VertexCompressionMask(out string how)
        {
            try
            {
                var p = typeof(PlayerSettings).GetProperty("vertexChannelCompressionMask", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
                if (p != null) { how = "PlayerSettings.vertexChannelCompressionMask"; return Convert.ToInt32(p.GetValue(null, null)); }
            }
            catch { }
            var y = ReadYaml("ProjectSettings/ProjectSettings.asset");
            string v; int m;
            if (y.TryGetValue("VertexChannelCompressionMask", out v) && int.TryParse(v, out m)) { how = "ProjectSettings.asset 原文"; return m; }
            how = "两种读法都读不到";
            return -1;
        }

        /// <summary>只认 "key: value" 一行一项的简单读法（ProjectSettings 是 Force Text 时）。</summary>
        public static Dictionary<string, string> ReadYaml(string path)
        {
            var d = new Dictionary<string, string>();
            try
            {
                foreach (var line in File.ReadAllLines(path))
                {
                    string t = line.Trim();
                    int k = t.IndexOf(':');
                    if (k <= 0) continue;
                    string key = t.Substring(0, k).Trim(), val = t.Substring(k + 1).Trim();
                    if (!d.ContainsKey(key)) d[key] = val;
                }
            }
            catch { }
            return d;
        }

        // ── 小工具 ──────────────────────────────────────────────────
        public static string PackageVersion(string name, out string source)
        {
            try
            {
                var pi = UnityEditor.PackageManager.PackageInfo.FindForAssetPath("Packages/" + name);
                if (pi != null && !string.IsNullOrEmpty(pi.version)) { source = "PackageManager"; return pi.version; }
            }
            catch { }
            foreach (var f in new[] { "Packages/vpm-manifest.json", "Packages/manifest.json" })
            {
                if (!File.Exists(f)) continue;
                try
                {
                    var j = TJson.Parse(File.ReadAllText(f));
                    foreach (var sec in new[] { "locked", "dependencies" })
                    {
                        var e = TJson.G(TJson.G(j, sec), name);
                        string v = e is string ? (string)e : TJson.S(TJson.G(e, "version"));
                        if (!string.IsNullOrEmpty(v)) { source = f + " " + sec; return v; }
                    }
                }
                catch { }
            }
            string pj = "Packages/" + name + "/package.json";
            if (File.Exists(pj))
            {
                try { source = pj; return TJson.S(TJson.G(TJson.Parse(File.ReadAllText(pj)), "version")); } catch { }
            }
            source = "PackageManager、vpm-manifest、manifest、package.json 都没有";
            return null;
        }

        public static Type FindType(string name)
        {
            foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = a.GetType(name, false);
                if (t != null) return t;
            }
            if (name.Contains(".")) return null;
            Type hit = null;
            foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] ts;
                try { ts = a.GetTypes(); } catch (System.Reflection.ReflectionTypeLoadException e) { ts = e.Types.Where(x => x != null).ToArray(); }
                foreach (var t in ts) if (t.Name == name) { if (hit != null && hit != t) return hit; hit = t; }
            }
            return hit;
        }

        static string FindScript(string name)
        {
            foreach (var g in AssetDatabase.FindAssets(name + " t:MonoScript"))
            {
                string p = AssetDatabase.GUIDToAssetPath(g);
                if (Path.GetFileNameWithoutExtension(p) == name) return p;
            }
            return null;
        }

        static bool MenuExists(string path)
        {
            // Unity 没有公开的“菜单在不在”：读内部的 Menu.GetMenuItems（读不到就当在，执行时再报错）
            try
            {
                var m = typeof(UnityEditor.Menu).GetMethod("GetMenuItems", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public);
                if (m == null) return true;
                int k = path.LastIndexOf('/');
                var items = m.Invoke(null, new object[] { path.Substring(0, k), false, false }) as Array;
                if (items == null || items.Length == 0) return true;      // 读法不对时宁可当“在”，执行时再报错，不误判 BLOCKED
                string leaf = path.Substring(k + 1);
                int known = 0;
                foreach (var it in items)
                {
                    var f = it.GetType().GetField("path") ?? it.GetType().GetField("m_Path", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
                    var pr = f == null ? it.GetType().GetProperty("path") : null;
                    string p = f != null ? f.GetValue(it) as string : (pr != null ? pr.GetValue(it, null) as string : null);
                    if (p == null) continue;
                    known++;
                    if (p == path || p == leaf || p.EndsWith("/" + leaf, StringComparison.Ordinal)) return true;
                }
                return known == 0;
            }
            catch { return true; }
        }

        public static string Git(string dir, string args)
        {
            try
            {
                var psi = new ProcessStartInfo("git", "-C \"" + dir + "\" " + args)
                { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true, StandardOutputEncoding = Encoding.UTF8 };
                using (var p = Process.Start(psi))
                {
                    string o = p.StandardOutput.ReadToEnd();
                    if (!p.WaitForExit(20000)) { try { p.Kill(); } catch { } return null; }
                    return p.ExitCode == 0 ? o : null;
                }
            }
            catch { return null; }
        }
    }

    // ─────────────────────────────────────────────────────────────────
    //  沙盒：Assets/_LanbaiTest/（带标记文件）。工具只往这里和输出文件夹写；贴图对照用的拷贝、场景拷贝都在这里。
    // ─────────────────────────────────────────────────────────────────
    public static class Sandbox
    {
        public const string DIR = "Assets/_LanbaiTest";
        public const string MARKER = ".lanbai_test_sandbox";       // 点开头：Unity 不导入它
        public static string MarkerPath { get { return DIR + "/" + MARKER; } }

        public static void Prepare(Ctx ctx)
        {
            if (Directory.Exists(DIR)) Delete(ctx);
            AssetDatabase.CreateFolder("Assets", "_LanbaiTest");
            File.WriteAllText(MarkerPath, TJson.Write(new Dictionary<string, object>
            {
                { "created_by", "Lanbai.Test.Runner " + Runner.VERSION }, { "test", ctx.testId }, { "run", ctx.runId },
                { "note", "测试工具的沙盒。下次跑会整个删掉重建；可以随时手动删。" }
            }), new UTF8Encoding(false));
            ctx.sandboxReady = true;
        }

        /// <summary>只删带标记的沙盒。</summary>
        public static bool Delete(Ctx ctx)
        {
            if (!Directory.Exists(DIR)) return true;
            if (!File.Exists(MarkerPath)) throw new BlockedException(DIR + " 没有标记文件，不删");
            bool sandboxOpen = false;
            for (int i = 0; i < SceneManager.sceneCount; i++)
                if (SceneManager.GetSceneAt(i).path.StartsWith(DIR + "/", StringComparison.Ordinal)) sandboxOpen = true;
            if (sandboxOpen)   // 沙盒里的场景开着（哪怕不是当前场景）：先换成空场景，再删
                UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene, UnityEditor.SceneManagement.NewSceneMode.Single);
            AssetDatabase.DeleteAsset(DIR);
            if (Directory.Exists(DIR)) Directory.Delete(DIR, true);
            if (File.Exists(DIR + ".meta")) File.Delete(DIR + ".meta");
            AssetDatabase.Refresh();
            if (ctx != null) ctx.Info("删掉了上次的沙盒 " + DIR);
            return true;
        }
    }

    // ─────────────────────────────────────────────────────────────────
    //  写入核对：跑之前、跑之后各记一次 Assets/（大小 + 修改时间）和 ProjectSettings/（内容哈希），
    //  比出来的每一处改动都要在沙盒里，或在测试定义的 allowed_writes 里（这些是现有搭建脚本自己要写的地方）。
    // ─────────────────────────────────────────────────────────────────
    public static class WriteGuard
    {
        public sealed class Snapshot
        {
            public readonly Dictionary<string, KeyValuePair<long, long>> assets = new Dictionary<string, KeyValuePair<long, long>>();
            public readonly Dictionary<string, string> settings = new Dictionary<string, string>();
        }

        public static Snapshot Take(string projectDir)
        {
            var s = new Snapshot();
            string root = Path.Combine(projectDir, "Assets");
            foreach (var f in Directory.GetFiles(root, "*", SearchOption.AllDirectories))
            {
                string rel = "Assets" + f.Substring(root.Length).Replace('\\', '/');
                if (rel.StartsWith(Sandbox.DIR + "/", StringComparison.Ordinal) || rel == Sandbox.DIR + ".meta") continue;
                var fi = new FileInfo(f);
                s.assets[rel] = new KeyValuePair<long, long>(fi.Length, fi.LastWriteTimeUtc.Ticks);
            }
            string ps = Path.Combine(projectDir, "ProjectSettings");
            if (Directory.Exists(ps))
                foreach (var f in Directory.GetFiles(ps, "*.asset"))
                    s.settings["ProjectSettings/" + Path.GetFileName(f)] = Sha256(File.ReadAllBytes(f));
            return s;
        }

        public static Dictionary<string, object> Diff(Ctx ctx)
        {
            // 工具自己不 SaveAssets：只比搭建脚本自己存下来的。工具在内存里改的材质值不落盘（改回去以后也不落盘）
            var after = Take(ctx.projectDir);
            var allowed = TJson.Sa(TJson.G(ctx.test, "allowed_writes")).Select(Glob).ToList();
            var declared = new List<object>(); var undeclared = new List<object>(); var ps = new List<object>(); var touched = new List<object>();
            Action<string, string> classify = (path, what) =>
            {
                string p = path.EndsWith(".meta", StringComparison.Ordinal) ? path.Substring(0, path.Length - 5) : path;
                // 工具逐字节写回去的文件（edit_json），内容和原来一样就不算改动
                byte[] orig;
                if (what == "改了" && ctx.restoredBytes.TryGetValue(path, out orig))
                {
                    try { if (File.ReadAllBytes(path).SequenceEqual(orig)) { touched.Add("写回了、内容和原来一样 " + path); return; } } catch { }
                }
                bool ok = allowed.Any(r => r.IsMatch(path) || r.IsMatch(p));
                // 工具临时改过又改回的材质：之后别的搭建脚本 SaveAssets 时会把它（改回后的值）落盘，单独列出来，不算没声明的写入
                if (!ok && what == "改了" && ctx.toolTouched.Contains(p)) { touched.Add("工具临时改过、已改回，被搭建脚本的 SaveAssets 落了盘 " + path); return; }
                (ok ? declared : undeclared).Add(what + " " + path);
            };
            foreach (var kv in after.assets)
            {
                KeyValuePair<long, long> b;
                if (!ctx.before.assets.TryGetValue(kv.Key, out b)) classify(kv.Key, "新建");
                else if (b.Key != kv.Value.Key || b.Value != kv.Value.Value) classify(kv.Key, "改了");
            }
            foreach (var kv in ctx.before.assets) if (!after.assets.ContainsKey(kv.Key)) classify(kv.Key, "删了");
            foreach (var kv in after.settings)
            {
                string b;
                if (!ctx.before.settings.TryGetValue(kv.Key, out b) || b != kv.Value) ps.Add(kv.Key);
            }
            ctx.Metric("writes.undeclared", undeclared.Count, "沙盒和 allowed_writes 以外被改动的文件");
            ctx.Metric("writes.declared", declared.Count);
            ctx.Metric("writes.project_settings_changed", ps.Count, "ProjectSettings/*.asset 内容变了的个数（工具只查不改）");
            return new Dictionary<string, object>
            {
                { "sandbox", Sandbox.DIR }, { "allowed_writes", TJson.Sa(TJson.G(ctx.test, "allowed_writes")).Cast<object>().ToList() },
                { "declared", declared }, { "undeclared", undeclared }, { "project_settings_changed", ps }, { "tool_touched_restored", touched },
                { "note", "按文件大小和修改时间比的：搭建脚本存了但内容没变的文件也算“改了”；只在内存里改、没存盘的不算" }
            };
        }

        static Regex Glob(string g)
        {
            var sb = new StringBuilder("^");
            for (int i = 0; i < g.Length; i++)
            {
                char c = g[i];
                if (c == '*' && i + 1 < g.Length && g[i + 1] == '*') { sb.Append(".*"); i++; }
                else if (c == '*') sb.Append("[^/]*");
                else if (c == '?') sb.Append("[^/]");
                else sb.Append(Regex.Escape(c.ToString()));
            }
            sb.Append('$');
            return new Regex(sb.ToString());
        }

        public static string Sha256(byte[] b)
        {
            using (var h = SHA256.Create())
            {
                var d = h.ComputeHash(b);
                var sb = new StringBuilder();
                foreach (var x in d) sb.Append(x.ToString("x2"));
                return sb.ToString();
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────
    //  检查项：默认几条 + 测试定义里的（同 id 以测试定义为准）
    // ─────────────────────────────────────────────────────────────────
    public static class Checks
    {
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        public static void Evaluate(Ctx ctx)
        {
            // 跑的过程中的 Console（开跑前的那些算预检）
            ctx.Metric("console.compile_errors", ctx.log.CountWhere(r => LogCapture.Source(r) != "console_snapshot" && (LogCapture.Type(r) == "CompileError" || (LogCapture.Type(r) == "Error" && r.ContainsKey("udonsharp")))));
            ctx.Metric("console.exceptions", ctx.log.CountWhere(r => LogCapture.Type(r) == "Exception" && LogCapture.Source(r) == "live" && !LogCapture.IsTool(r)));
            ctx.Metric("console.errors", ctx.log.CountWhere(r => (LogCapture.Type(r) == "Error" || LogCapture.Type(r) == "Assert") && LogCapture.Source(r) == "live" && !LogCapture.IsTool(r)));
            ctx.Metric("console.warnings", ctx.log.CountWhere(r => LogCapture.Type(r) == "Warning" && LogCapture.Source(r) == "live" && !LogCapture.IsTool(r)));
            ctx.Metric("steps.errors", ctx.steps.Count(s => (string)s["status"] == "error"));

            var defs = new List<Dictionary<string, object>>
            {
                Def("steps_ok", "steps.errors", "==", 0, true, "每一步都跑成功了"),
                Def("no_compile_errors", "console.compile_errors", "==", 0, true, "跑的过程中没有新的编译错误"),
                Def("no_exceptions", "console.exceptions", "==", 0, true, "跑的过程中 Console 没有异常（工具自己的不算）"),
                Def("no_console_errors", "console.errors", "==", 0, false, "跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须）"),
                Def("no_undeclared_writes", "writes.undeclared", "==", 0, true, "沙盒和 allowed_writes 以外没有文件被改"),
                Def("project_settings_untouched", "writes.project_settings_changed", "==", 0, true, "ProjectSettings 没被改"),
            };
            if (ctx.shots.Count > 0 && TJson.B(TJson.G(ctx.test, "require_ppv2"), true))
                defs.Add(Def("ppv2_effective", "capture.ppv2_effective", "==", 1, true, "截图经过了 PPv2（开 / 关 PPv2 各渲一张小图，要不一样）"));
            foreach (var s in ctx.settings)
                defs.Add(Def("setting_" + s["item"], "settings." + s["item"], "==", 1, (string)s["status"] != "warn", (string)s["detail"]));

            var byId = new Dictionary<string, Dictionary<string, object>>();
            var order = new List<string>();
            foreach (var d in defs) { string id = (string)d["id"]; byId[id] = d; order.Add(id); }
            foreach (var o in TJson.L(TJson.G(ctx.test, "checks")))
            {
                var d = TJson.M(o);
                if (d == null) continue;
                string id = TJson.S(TJson.G(d, "id"), "check_" + order.Count);
                if (!byId.ContainsKey(id)) order.Add(id);
                byId[id] = d;
            }
            foreach (var id in order) ctx.checks.Add(One(ctx, id, byId[id]));
        }

        static Dictionary<string, object> Def(string id, string metric, string op, double v, bool gate, string why)
        {
            return new Dictionary<string, object> { { "id", id }, { "metric", metric }, { "op", op }, { "value", v }, { "gate", gate }, { "why", why } };
        }

        static Dictionary<string, object> One(Ctx ctx, string id, Dictionary<string, object> d)
        {
            string metric = TJson.S(TJson.G(d, "metric"));
            string op = TJson.S(TJson.G(d, "op"), "==");
            bool gate = TJson.B(TJson.G(d, "gate"), true);
            var r = new Dictionary<string, object> { { "id", id }, { "metric", metric }, { "op", op }, { "value", TJson.G(d, "value") }, { "gate", gate } };
            if (TJson.Has(d, "why")) r["why"] = TJson.G(d, "why");
            double m;
            if (metric == null || !ctx.metrics.TryGetValue(metric, out m) || double.IsNaN(m))
            {
                r["status"] = gate ? "fail" : "warn";
                r["detail"] = "没量到（这一项的截图 / 序列 / 性能没跑成，或名字写错）";
                return r;
            }
            r["measured"] = m;
            bool ok; string expect;
            var v = TJson.G(d, "value");
            switch (op)
            {
                case "==": ok = Math.Abs(m - TJson.D(v)) < 1e-9; expect = "= " + TJson.S(v); break;
                case "!=": ok = Math.Abs(m - TJson.D(v)) >= 1e-9; expect = "≠ " + TJson.S(v); break;
                case "<": ok = m < TJson.D(v); expect = "< " + TJson.S(v); break;
                case "<=": ok = m <= TJson.D(v); expect = "≤ " + TJson.S(v); break;
                case ">": ok = m > TJson.D(v); expect = "> " + TJson.S(v); break;
                case ">=": ok = m >= TJson.D(v); expect = "≥ " + TJson.S(v); break;
                case "between":
                    {
                        var a = TJson.L(v);
                        double lo = a.Count == 2 ? TJson.D(a[0]) : double.NaN, hi = a.Count == 2 ? TJson.D(a[1]) : double.NaN;
                        ok = a.Count == 2 && m >= lo && m <= hi;
                        expect = a.Count == 2 ? lo.ToString(IC) + " … " + hi.ToString(IC) : "?";
                        break;
                    }
                case "within_pct":
                    {
                        double target = TJson.D(v), pct = TJson.D(TJson.G(d, "pct"), 15);
                        ok = Math.Abs(m - target) <= Math.Abs(target) * pct / 100.0;
                        expect = target.ToString("0.###", IC) + " ± " + pct.ToString("0.#", IC) + "%";
                        break;
                    }
                default: ok = false; expect = "不认识的 op " + op; break;
            }
            r["expect"] = expect;
            r["status"] = ok ? "pass" : (gate ? "fail" : "warn");
            return r;
        }
    }
}
