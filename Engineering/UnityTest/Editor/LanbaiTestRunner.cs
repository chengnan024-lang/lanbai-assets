// ═══════════════════════════════════════════════════════════════════
//  蓝白 · Unity 测试工具（D-40 #1 / D-40a）· 总工程师
//  数据驱动：Engineering/UnityTest/tests/<test-id>.json（工程里：Assets/Lanbai/Engineering/UnityTest/tests/）
//  两个入口，同一套代码：
//    菜单  蓝白/Test/...
//    批处理 Unity.exe -batchmode -projectPath <工程> -executeMethod Lanbai.Test.Runner.RunCli -lanbaiTest <id> -logFile <路径>
//  退出码：0 全部跑完、检查全过；1 跑完了、有检查没过；2 预检 / 前置条件不满足（BLOCKED）；3 工具自己出了异常。
//  日志的最后一条：LANBAI_TEST_RESULT {json}。每次跑都新建一个输出文件夹，重跑是安全的。
//  没在 Unity 里编译过、没在 Unity 里跑过：只过了 Common/Tools~/compile_check（Roslyn + 桩）。
// ═══════════════════════════════════════════════════════════════════
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Lanbai.Test
{
    public sealed class BlockedException : Exception { public BlockedException(string m) : base(m) { } }
    public sealed class StepException : Exception { public StepException(string m) : base(m) { } }

    /// <summary>一次运行的全部状态。</summary>
    public sealed class Ctx
    {
        public string testId, testFile, testSha, runId, outDir, projectDir, mode;
        public Dictionary<string, object> test;
        public readonly Dictionary<string, double> metrics = new Dictionary<string, double>();
        public readonly Dictionary<string, string> metricNotes = new Dictionary<string, string>();
        public readonly List<Dictionary<string, object>> preflight = new List<Dictionary<string, object>>();
        public readonly List<Dictionary<string, object>> preconditions = new List<Dictionary<string, object>>();
        public readonly List<Dictionary<string, object>> steps = new List<Dictionary<string, object>>();
        public readonly List<Dictionary<string, object>> checks = new List<Dictionary<string, object>>();
        public readonly List<Dictionary<string, object>> shots = new List<Dictionary<string, object>>();
        public readonly List<Dictionary<string, object>> sequences = new List<Dictionary<string, object>>();
        public readonly List<Dictionary<string, object>> perf = new List<Dictionary<string, object>>();
        public readonly List<Dictionary<string, object>> textures = new List<Dictionary<string, object>>();
        public readonly List<Dictionary<string, object>> settings = new List<Dictionary<string, object>>();
        public readonly List<string> warnings = new List<string>();
        public readonly List<string> files = new List<string>();
        public readonly UndoStack undo = new UndoStack();
        public readonly LogCapture log = new LogCapture();
        public Dictionary<string, object> sync;             // Assets/Lanbai/.lanbai_sync.json（同步脚本写的）
        public string gitStatus;                             // 工程是 git 仓库时，git status --porcelain 的原文
        public WriteGuard.Snapshot before;
        public Dictionary<string, object> writes;
        public string blockedReason, error, errorStack, scenePath;
        public bool sandboxReady;
        public float? lastT;
        public readonly DateTime started = DateTime.UtcNow;

        public void Metric(string name, double v, string note = null)
        {
            metrics[name] = v;
            if (note != null) metricNotes[name] = note;
        }
        public string Out(string rel)
        {
            string p = Path.Combine(outDir, rel.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(p));
            return p;
        }
        public void AddFile(string rel) { if (!files.Contains(rel)) files.Add(rel); }
        public void Warn(string w) { warnings.Add(w); Debug.LogWarning(LogCapture.TAG + " " + w); }
        public void Info(string s) { Debug.Log(LogCapture.TAG + " " + s); }
        public object T(string key) { return TJson.G(test, key); }
    }

    /// <summary>测试里临时改的东西（GameObject 开关、材质值、JSON 文件），按相反顺序改回去。</summary>
    public sealed class UndoStack
    {
        readonly List<KeyValuePair<string, Action>> _a = new List<KeyValuePair<string, Action>>();
        public int Mark() { return _a.Count; }
        public void Push(string what, Action a) { _a.Add(new KeyValuePair<string, Action>(what, a)); }
        public List<string> RollbackTo(int mark)
        {
            var errs = new List<string>();
            for (int i = _a.Count - 1; i >= mark; i--)
            {
                try { _a[i].Value(); }
                catch (Exception e) { errs.Add("改回 " + _a[i].Key + " 失败：" + e.Message); }
                _a.RemoveAt(i);
            }
            return errs;
        }
    }

    public static class Runner
    {
        public const string VERSION = "1.0.0";
        public const string TESTS_DIR = "Assets/Lanbai/Engineering/UnityTest/tests";
        public const string REPORTS = "LanbaiReports/tests";
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        // ─────────────────────────────────────────────────────────────
        //  批处理入口
        // ─────────────────────────────────────────────────────────────
        public static void RunCli()
        {
            int code = 3;
            try
            {
                var args = Environment.GetCommandLineArgs();
                string id = Arg(args, "-lanbaiTest"), file = Arg(args, "-lanbaiTestFile");
                bool pre = args.Contains("-lanbaiPreflightOnly");
                if (string.IsNullOrEmpty(id) && string.IsNullOrEmpty(file))
                {
                    Final(new Dictionary<string, object> { { "exit", 3.0 }, { "status", "error" }, { "error", "缺 -lanbaiTest <id>" } });
                    code = 3;
                }
                else
                {
                    string outDir;
                    code = Run(id, file, pre, "batch", out outDir);
                }
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                Final(new Dictionary<string, object> { { "exit", 3.0 }, { "status", "error" }, { "error", e.GetType().Name + ": " + e.Message } });
                code = 3;
            }
            EditorApplication.Exit(code);
        }

        static string Arg(string[] a, string k)
        {
            for (int i = 0; i < a.Length - 1; i++) if (a[i] == k) return a[i + 1];
            return null;
        }

        // ─────────────────────────────────────────────────────────────
        //  一次运行（菜单和批处理共用）
        // ─────────────────────────────────────────────────────────────
        public static int Run(string testId, string testFile, bool preflightOnly, string mode, out string outDir)
        {
            var ctx = new Ctx { mode = mode, projectDir = Path.GetFullPath(Path.Combine(Application.dataPath, "..")) };
            ctx.log.Start();
            int exit = 3;
            outDir = null;
            try
            {
                // 0) 测试定义和输出文件夹（输出文件夹在 Assets 外面，写它不算碰工程）
                ctx.testFile = FindTest(testId, testFile);
                ctx.testId = testId ?? Path.GetFileNameWithoutExtension(ctx.testFile ?? "unknown");
                ctx.runId = DateTime.Now.ToString("yyyyMMdd-HHmmss", IC);
                ctx.outDir = NewOutDir(ctx);
                outDir = ctx.outDir;
                ctx.Info("测试 " + ctx.testId + "，输出 " + ctx.outDir);
                if (ctx.testFile == null) throw new BlockedException("找不到测试定义 " + testId + ".json（应该在 " + TESTS_DIR + "/ 里；先跑同步脚本）");
                string text = File.ReadAllText(ctx.testFile);
                ctx.testSha = WriteGuard.Sha256(Encoding.UTF8.GetBytes(text));
                try { ctx.test = TJson.M(TJson.Parse(text)); }
                catch (Exception e) { throw new BlockedException("测试定义 " + ctx.testFile + " 读不懂：" + e.Message); }
                if (ctx.test == null) throw new BlockedException("测试定义不是一个 JSON 对象");
                File.Copy(ctx.testFile, ctx.Out("test_definition.json"), true);
                ctx.AddFile("test_definition.json");

                // 1) 只读的预检（这之前不碰工程里任何东西）
                Preflight.Run(ctx);
                Preflight.Preconditions(ctx);
                string placeholder = TJson.S(ctx.T("blocked"));
                if (!string.IsNullOrEmpty(placeholder)) throw new BlockedException(placeholder);
                if (preflightOnly) { ctx.Info("只做预检：通过"); exit = 0; }
                else exit = Body(ctx);
            }
            catch (BlockedException b)
            {
                ctx.blockedReason = b.Message;
                Debug.LogWarning(LogCapture.TAG + " BLOCKED：" + b.Message);
                exit = 2;
            }
            catch (Exception e)
            {
                ctx.error = e.GetType().Name + ": " + e.Message;
                ctx.errorStack = e.StackTrace;
                Debug.LogError(LogCapture.TAG + " 工具异常：" + ctx.error + "\n" + e.StackTrace);
                exit = 3;
            }
            finally
            {
                try { foreach (var e in ctx.undo.RollbackTo(0)) ctx.warnings.Add(e); } catch { }
                try { EditorUtility.ClearProgressBar(); } catch { }
            }

            // 7) 报告（报告写不出来也算工具异常）
            try
            {
                if (ctx.writes == null && ctx.before != null) ctx.writes = WriteGuard.Diff(ctx);
                ctx.log.Stop();
                if (ctx.outDir != null) Report.WriteAll(ctx, exit);
            }
            catch (Exception e)
            {
                Debug.LogError(LogCapture.TAG + " 报告写不出来：" + e);
                exit = 3;
            }
            Final(ResultLine(ctx, exit));
            return exit;
        }

        static int Body(Ctx ctx)
        {
            // 2) 沙盒、写入快照、场景
            Sandbox.Prepare(ctx);
            ctx.before = WriteGuard.Take(ctx.projectDir);
            Scenes.Open(ctx);
            Preflight.ScenePreconditions(ctx);

            // 3) 搭建
            bool built = Steps.RunList(ctx, TJson.L(ctx.T("build")), "build", null, true);
            if (built) Steps.RunList(ctx, TJson.L(ctx.T("after_build")), "after_build", null, false);

            // 4) 只查不改的项目设置；场景里的光照图张数（光照图接缝那一项要先有光照图）
            Preflight.ProjectSettingsChecks(ctx);
            ctx.Metric("scene.lightmaps", LightmapSettings.lightmaps != null ? LightmapSettings.lightmaps.Length : 0, "打开的场景里的光照图张数");

            // 5) 截图、双眼近似、动态序列、贴图压缩对照、性能（搭建失败就不拍：拍出来也没有意义）
            if (built)
            {
                Capture.All(ctx);
                Perf.All(ctx);
                // 最后（比如把搭好的场景另存进沙盒、加 VRC 场景描述符，给 Play / ClientSim 用）
                Steps.RunList(ctx, TJson.L(ctx.T("post")), "post", null, true);
            }
            else ctx.Warn("搭建有一步失败，后面的截图、序列、性能都没做");

            // 6) 收尾：改回临时改的东西，查写入，判检查项
            foreach (var e in ctx.undo.RollbackTo(0)) ctx.Warn(e);
            ctx.writes = WriteGuard.Diff(ctx);
            Checks.Evaluate(ctx);
            int failed = ctx.checks.Count(c => (string)c["status"] == "fail");
            return failed > 0 ? 1 : 0;
        }

        public static string StatusOf(int exit)
        {
            switch (exit) { case 0: return "pass"; case 1: return "fail"; case 2: return "blocked"; default: return "error"; }
        }

        static Dictionary<string, object> ResultLine(Ctx ctx, int exit)
        {
            var r = new Dictionary<string, object>();
            r["test"] = ctx.testId;
            r["run"] = ctx.runId;
            r["exit"] = (double)exit;
            r["status"] = StatusOf(exit);
            r["out"] = ctx.outDir;
            r["checks_failed"] = (double)ctx.checks.Count(c => (string)c["status"] == "fail");
            r["checks_total"] = (double)ctx.checks.Count;
            if (ctx.blockedReason != null) r["blocked_reason"] = ctx.blockedReason;
            if (ctx.error != null) r["error"] = ctx.error;
            r["vr_headset"] = "not_tested";
            r["tool_version"] = VERSION;
            return r;
        }

        /// <summary>日志里最后一条（批处理时也写到标准输出）。</summary>
        static void Final(Dictionary<string, object> r)
        {
            string line = "LANBAI_TEST_RESULT " + TJson.Write(r, false);
            var prev = Application.GetStackTraceLogType(LogType.Log);
            Application.SetStackTraceLogType(LogType.Log, StackTraceLogType.None);
            Debug.Log(line);
            Application.SetStackTraceLogType(LogType.Log, prev);
            try { Console.Out.WriteLine(line); Console.Out.Flush(); } catch { }
        }

        public static string FindTest(string id, string file)
        {
            if (!string.IsNullOrEmpty(file)) return File.Exists(file) ? Path.GetFullPath(file) : null;
            string p = Path.Combine(TESTS_DIR, id + ".json");
            if (File.Exists(p)) return Path.GetFullPath(p);
            foreach (var g in AssetDatabase.FindAssets(id))
            {
                string ap = AssetDatabase.GUIDToAssetPath(g);
                if (ap.EndsWith("/UnityTest/tests/" + id + ".json", StringComparison.Ordinal)) return Path.GetFullPath(ap);
            }
            return null;
        }

        public static List<string> ListTests()
        {
            var l = new List<string>();
            if (Directory.Exists(TESTS_DIR))
                foreach (var f in Directory.GetFiles(TESTS_DIR, "*.json"))
                {
                    string n = Path.GetFileNameWithoutExtension(f);
                    if (!n.StartsWith("_")) l.Add(n);
                }
            l.Sort(StringComparer.Ordinal);
            return l;
        }

        static string NewOutDir(Ctx ctx)
        {
            string baseDir = Path.Combine(ctx.projectDir, REPORTS, ctx.testId);
            string d = Path.Combine(baseDir, ctx.runId);
            for (int k = 2; Directory.Exists(d); k++) d = Path.Combine(baseDir, ctx.runId + "-" + k);
            ctx.runId = Path.GetFileName(d);
            Directory.CreateDirectory(d);
            return d;
        }
    }

    // ─────────────────────────────────────────────────────────────────
    //  场景：in_place（就在原场景里，比如门测试场景）/ copy（拷进沙盒再开）/ new（沙盒里的空场景）
    //  工具从不保存场景。拷贝在沙盒里，下次跑会被删掉。
    // ─────────────────────────────────────────────────────────────────
    public static class Scenes
    {
        public static void Open(Ctx ctx)
        {
            var sc = TJson.G(ctx.test, "scene");
            string path = TJson.S(TJson.G(sc, "path"));
            string mode = TJson.S(TJson.G(sc, "mode"), "copy");
            if (mode == "new")
            {
                var s = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
                string p = Sandbox.DIR + "/" + ctx.testId + "_new.unity";
                EditorSceneManager.SaveScene(s, p);           // 沙盒里，允许
                ctx.scenePath = p;
                return;
            }
            if (string.IsNullOrEmpty(path)) throw new BlockedException("测试定义没写 scene.path");
            if (!File.Exists(path)) throw new BlockedException("场景不在：" + path);
            string open = path;
            if (mode == "copy")
            {
                open = Sandbox.DIR + "/" + Path.GetFileNameWithoutExtension(path) + "_copy.unity";
                if (!AssetDatabase.CopyAsset(path, open)) throw new Exception("拷贝场景到沙盒失败：" + path + " → " + open);
            }
            else if (mode != "in_place") throw new BlockedException("scene.mode 只能是 in_place / copy / new，现在是 " + mode);
            var cur = SceneManager.GetActiveScene();
            if (cur.path != open || !cur.isLoaded) EditorSceneManager.OpenScene(open, OpenSceneMode.Single);
            ctx.scenePath = open;
            ctx.Info("场景：" + open + "（" + mode + (mode == "copy" ? "，原件 " + path : "") + "）");
        }

        /// <summary>按 "Root/Child/Grandchild" 找（含没激活的）；"**/Name" 在所有根下深找，"**/Name/Child" 深找到 Name 再往下。</summary>
        public static Transform Find(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var roots = new List<GameObject>();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var s = SceneManager.GetSceneAt(i);
                if (s.isLoaded) roots.AddRange(s.GetRootGameObjects());
            }
            if (path.StartsWith("**/", StringComparison.Ordinal))
            {
                // "**/A" 在所有根下深找 A；"**/A/B/C" 深找 A，再从 A 往下按 B/C 找
                string rest = path.Substring(3);
                int j = rest.IndexOf('/');
                string n = j < 0 ? rest : rest.Substring(0, j);
                foreach (var r in roots)
                {
                    var t = Deep(r.transform, n);
                    if (t == null) continue;
                    if (j < 0) return t;
                    var u = t.Find(rest.Substring(j + 1));
                    if (u != null) return u;
                }
                return null;
            }
            int k = path.IndexOf('/');
            string head = k < 0 ? path : path.Substring(0, k);
            foreach (var r in roots)
            {
                if (r.name != head) continue;
                if (k < 0) return r.transform;
                var t = r.transform.Find(path.Substring(k + 1));
                if (t != null) return t;
            }
            return null;
        }

        public static Transform Deep(Transform t, string name)
        {
            if (t.name == name) return t;
            for (int i = 0; i < t.childCount; i++) { var r = Deep(t.GetChild(i), name); if (r != null) return r; }
            return null;
        }

        public static IEnumerable<GameObject> AllRoots()
        {
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var s = SceneManager.GetSceneAt(i);
                if (!s.isLoaded) continue;
                foreach (var g in s.GetRootGameObjects()) yield return g;
            }
        }

        public static string PathOf(Transform t)
        {
            var s = t.name;
            while (t.parent != null) { t = t.parent; s = t.name + "/" + s; }
            return s;
        }
    }
}
