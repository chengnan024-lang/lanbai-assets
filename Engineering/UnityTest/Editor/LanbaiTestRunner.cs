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
        public readonly List<Dictionary<string, object>> play = new List<Dictionary<string, object>>();   // 1.2.0：Play 阶段的每一段（交接扫描 / 闪烁探测）
        public readonly List<string> warnings = new List<string>();
        public readonly List<string> files = new List<string>();
        public readonly UndoStack undo = new UndoStack();
        public readonly LogCapture log = new LogCapture();
        public Dictionary<string, object> sync;             // Assets/Lanbai/.lanbai_sync.json（同步脚本写的）
        public Dictionary<string, object> consent;          // LanbaiReports/tests/CONSENT.json（小楠的同意，阿白写）
        public string gitStatus;                             // 工程是 git 仓库时，git status --porcelain 的原文
        public WriteGuard.Snapshot before;
        public Dictionary<string, object> writes;
        public string blockedReason, error, errorStack, scenePath;
        public readonly List<string> toolErrors = new List<string>();            // 工具自己代码里的异常（不是被调的脚本、不是步骤判的失败）→ 退出码 3
        public readonly List<string> toolTouched = new List<string>();           // 工具临时改过、又改回去的资产（材质、JSON）
        public readonly Dictionary<string, byte[]> restoredBytes = new Dictionary<string, byte[]>();
        public bool sandboxReady, preflightOnly;
        public float? lastT;
        public DateTime started = DateTime.UtcNow;   // Play 阶段读回来时要恢复（1.2.0），所以不是 readonly

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
        public void ToolError(string where, Exception e)
        {
            toolErrors.Add(where + "：" + e.GetType().Name + ": " + e.Message + "\n" + e.StackTrace);
            Debug.LogError(LogCapture.TAG + " 工具自己的异常（" + where + "）：" + e);
        }
        public void Warn(string w) { warnings.Add(w); Debug.LogWarning(LogCapture.TAG + " " + w); }
        public void Info(string s) { Debug.Log(LogCapture.TAG + " " + s); }
        public object T(string key) { return TJson.G(test, key); }
    }

    /// <summary>测试里临时改的东西（GameObject 开关、材质值、JSON 文件），按相反顺序改回去。</summary>
    public sealed class UndoStack
    {
        readonly List<KeyValuePair<string, Action>> _a = new List<KeyValuePair<string, Action>>();
        // 复核的次要项：改回失败的不丢，留在这里，之后每次 RollbackTo 再试；收尾时还有的 → 报告里列出来（JSON 的 → 退出码 3）
        readonly List<KeyValuePair<string, Action>> _failed = new List<KeyValuePair<string, Action>>();
        public int Mark() { return _a.Count; }
        public void Push(string what, Action a) { _a.Add(new KeyValuePair<string, Action>(what, a)); }
        public List<string> Failed { get { return _failed.Select(x => x.Key).ToList(); } }
        public List<string> RollbackTo(int mark)
        {
            var errs = new List<string>();
            int fresh = 0;
            for (int i = _a.Count - 1; i >= mark; i--)
            {
                try { _a[i].Value(); }
                catch (Exception)
                {
                    // 再试一次（比如导入刚好在忙）；还不行就留下来，下次 RollbackTo 和收尾时再试
                    try { _a[i].Value(); }
                    catch (Exception e2) { errs.Add("改回 " + _a[i].Key + " 失败（试了两次，留着之后再试）：" + e2.Message); _failed.Add(_a[i]); fresh++; }
                }
                _a.RemoveAt(i);
            }
            for (int i = _failed.Count - 1; i >= 0; i--)
            {
                if (i >= _failed.Count - fresh) continue;   // 这一轮刚失败的，下次再试
                try { _failed[i].Value(); errs.Add("改回 " + _failed[i].Key + "：之前失败，这次重试成功了"); _failed.RemoveAt(i); }
                catch (Exception) { }
            }
            return errs;
        }
    }

    [InitializeOnLoad]
    public static class Runner
    {
        public const string VERSION = "1.3.0";   // 1.3.0（2026-10-31，D-50 #9）：参考图逐级方框缩小、序列里着色器时间每帧走、记 LOD、阿白的 Play / Capture 补丁、全局保存的归因、重复的场景描述符、收尾后的 Console；1.2.2（2026-10-25）：机位 msaa、序列 isolate / ROI、WriteGuard 小文件按内容哈希；1.2.1（2026-10-25）：Play 阶段按复核 E1–E12 改；1.2.0：Play 阶段（transitions_sweep、flicker_probe，D-44 #4）；1.1.0：D-43 #6 copied、复核的次要项
        public const string TESTS_DIR = "Assets/Lanbai/Engineering/UnityTest/tests";
        public const string REPORTS = "LanbaiReports/tests";
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        // ─────────────────────────────────────────────────────────────
        //  批处理入口
        // ─────────────────────────────────────────────────────────────
        // ── domain reload 时（等 U# 程序资产的时候编辑器 reload 了）：排着的“接着跑”丢了。记在 SessionState 里，
        //    reload 以后从头再跑一次（新的输出文件夹，D-40a“重跑安全”）；再 reload 一次就算 BLOCKED（批处理照样退出）
        const string PendingKey = "Lanbai.Test.Pending", ResumeKey = "Lanbai.Test.Resumed";

        static Runner()
        {
            string p = SessionState.GetString(PendingKey, "");
            if (string.IsNullOrEmpty(p)) return;
            SessionState.EraseString(PendingKey);
            var a = p.Split('\t');
            if (a.Length < 4) return;
            string id = a[0].Length > 0 ? a[0] : null, file = a[1].Length > 0 ? a[1] : null, mode = a[3];
            bool pre = a[2] == "1";
            Action<int, string> done = mode == "batch" ? (Action<int, string>)((code, o) => EditorApplication.Exit(code)) : null;
            EditorApplication.delayCall += () =>
            {
                if (SessionState.GetBool(ResumeKey, false))
                {
                    SessionState.EraseBool(ResumeKey);
                    Debug.LogError(LogCapture.TAG + " 等 U# 程序资产时编辑器 reload 了两次，测试 " + id + " 没跑完：BLOCKED。看 Console 里 [Lanbai U#] 和 UdonSharp 的报错，好了以后再跑");
                    Final(new Dictionary<string, object> { { "test", id }, { "exit", 2.0 }, { "status", "blocked" }, { "blocked_reason", "domain reload twice while waiting for U# program assets" }, { "vr_headset", "not_tested" }, { "tool_version", VERSION } });
                    if (done != null) done(2, null);
                    return;
                }
                SessionState.SetBool(ResumeKey, true);
                Debug.LogWarning(LogCapture.TAG + " 等 U# 程序资产时编辑器 reload 了：测试 " + id + " 从头再跑一次（新的输出文件夹；上一次的文件夹没有报告）");
                Start(id, file, pre, mode, done ?? MenuDone(id, pre));
            };
        }

        static Action<int, string> MenuDone(string id, bool pre)
        {
            return (code, outDir) => Debug.Log(LogCapture.TAG + " 测试 " + id + " 跑完（reload 以后续跑的），退出码 " + code + "，看 " + outDir + "/summary.md");
        }

        public static void RunCli()
        {
            try
            {
                var args = Environment.GetCommandLineArgs();
                string id = Arg(args, "-lanbaiTest"), file = Arg(args, "-lanbaiTestFile");
                bool pre = args.Contains("-lanbaiPreflightOnly");
                if (string.IsNullOrEmpty(id) && string.IsNullOrEmpty(file))
                {
                    Final(new Dictionary<string, object> { { "exit", 3.0 }, { "status", "error" }, { "error", "缺 -lanbaiTest <id>" } });
                    EditorApplication.Exit(3);
                    return;
                }
                // 可能要等 U# 程序资产初始化（D-41）：这时 RunCli 先返回，批处理的编辑器循环接着转，跑完由回调退出
                Start(id, file, pre, "batch", (code, outDir) => EditorApplication.Exit(code));
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                Final(new Dictionary<string, object> { { "exit", 3.0 }, { "status", "error" }, { "error", e.GetType().Name + ": " + e.Message } });
                EditorApplication.Exit(3);
            }
        }

        static string Arg(string[] a, string k)
        {
            for (int i = 0; i < a.Length - 1; i++) if (a[i] == k) return a[i + 1];
            return null;
        }

        // ─────────────────────────────────────────────────────────────
        //  一次运行（菜单和批处理共用）。done(退出码, 输出文件夹) 在跑完时调一次：
        //  不用等 U# 程序资产时就在 Start 里面同步调；要等时（测试定义的 udon_programs 有没初始化完的）在之后的编辑器循环里调。
        // ─────────────────────────────────────────────────────────────
        public static void Start(string testId, string testFile, bool preflightOnly, string mode, Action<int, string> done)
        {
            var ctx = new Ctx { mode = mode, projectDir = Path.GetFullPath(Path.Combine(Application.dataPath, "..")) };
            ctx.log.Start();
            int exit = 3;
            bool deferred = false;
            try
            {
                // 0) 测试定义和输出文件夹（输出文件夹在 Assets 外面，写它不算碰工程）
                ctx.testFile = FindTest(testId, testFile);
                ctx.testId = testId ?? Path.GetFileNameWithoutExtension(ctx.testFile ?? "unknown");
                ctx.runId = DateTime.Now.ToString("yyyyMMdd-HHmmss", IC);
                ctx.outDir = NewOutDir(ctx);
                ctx.preflightOnly = preflightOnly;
                // 一开始就写一个 running 标记：Unity 中途崩了，这个文件夹里留下的是 running，不会被误读成上一次的结果
                File.WriteAllText(Path.Combine(ctx.outDir, "result.json"), TJson.Write(new Dictionary<string, object>
                {
                    { "test", ctx.testId }, { "run", ctx.runId }, { "status", "running" }, { "started_utc", ctx.started.ToString("o", IC) },
                    { "note", "跑完会被这次的结果盖掉；还是 running，就是没跑完（Unity 崩了或被关了）。以这个文件夹的 result.json / 日志里这次的 LANBAI_TEST_RESULT 为准，不看 Unity.exe 自己的退出码" }
                }), new UTF8Encoding(false));
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
                else
                {
                    Prepare(ctx);
                    // 2b) U# 程序资产（D-41）：测试要用到的先建好、等 SDK 初始化完（2/2），再搭。搭建菜单自己也会等，
                    //     但工具是一口气跑完的，所以在这里统一等，不让菜单在半路排队
                    var types = UdonTypes(ctx);
                    string rep;
                    if (types.Count > 0 && !Lanbai.Udon.LanbaiUdonPrograms.AllReady(types, out rep))
                    {
                        deferred = true;
                        SessionState.SetString(PendingKey, (testId ?? "") + "\t" + (testFile ?? "") + "\t" + (preflightOnly ? "1" : "0") + "\t" + mode);
                        ctx.Info("等 U# 程序资产初始化完再搭（最多 " + Lanbai.Udon.LanbaiUdonPrograms.TimeoutSeconds.ToString("0", IC) + " 秒）：\n" + rep);
                        Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("测试 " + ctx.testId, types,
                            () => { int e = Guarded(ctx, () => Body(ctx)); if (e != PlayPhase.Deferred) Finish(ctx, e, done); },
                            null,
                            msg => { ctx.blockedReason = "U# 程序资产没准备好：" + msg; Finish(ctx, 2, done); });
                    }
                    else exit = Body(ctx);
                }
            }
            catch (BlockedException b) { exit = Blocked(ctx, b); }
            catch (Exception e) { exit = ToolFailure(ctx, e); }
            if (!deferred && exit != PlayPhase.Deferred) Finish(ctx, exit, done);
        }

        /// <summary>Play 阶段（1.2.0）跑完、退出 Play、reload 以后由 PlayPhase 调：查检查项和写入，再照常收尾。</summary>
        public static void FinishFromPlay(Ctx ctx, int exit, Action<int, string> done)
        {
            if (exit == 0)
            {
                try
                {
                    if (ctx.before != null) ctx.writes = WriteGuard.Diff(ctx);
                    Checks.Evaluate(ctx);
                    exit = ctx.checks.Count(c => (string)c["status"] == "fail") > 0 ? 1 : 0;
                    if (ctx.toolErrors.Count > 0)
                    {
                        ctx.error = "工具自己的代码出了 " + ctx.toolErrors.Count + " 次异常（详情在 manifest 的 tool_errors）：" + ctx.toolErrors[0].Split('\n')[0];
                        exit = 3;
                    }
                }
                catch (Exception e) { exit = ToolFailure(ctx, e); }
            }
            Finish(ctx, exit, done);
        }

        /// <summary>1.2.1（E6）：Play 阶段收尾自己出错时也要有结果：result.json + LANBAI_TEST_RESULT（退出码 3），再回调</summary>
        public static void Emergency(string outDir, string test, string error, Action<int, string> done)
        {
            var r = new Dictionary<string, object> { { "test", test }, { "exit", 3.0 }, { "status", "error" }, { "out", outDir }, { "error", error }, { "vr_headset", "not_tested" }, { "tool_version", VERSION } };
            try { File.WriteAllText(Path.Combine(outDir, "result.json"), TJson.Write(r), new UTF8Encoding(false)); } catch { }
            Final(r);
            if (done != null) done(3, outDir);
        }

        /// <summary>进 Play 之前调：等 U# 时记下的“reload 以后从头再跑”不能留着，不然进 Play 的那次 reload 会把测试又从头跑一遍</summary>
        public static void ClearPending()
        {
            SessionState.EraseString(PendingKey);
            SessionState.EraseBool(ResumeKey);
        }

        /// <summary>reload 以后重建“跑完以后做什么”：批处理退出，菜单打一行日志。</summary>
        public static Action<int, string> DoneFor(string mode, string id, bool pre)
        {
            return mode == "batch" ? (Action<int, string>)((code, o) => EditorApplication.Exit(code)) : MenuDone(id, pre);
        }

        static int Guarded(Ctx ctx, Func<int> f)
        {
            try { return f(); }
            catch (BlockedException b) { return Blocked(ctx, b); }
            catch (Exception e) { return ToolFailure(ctx, e); }
        }

        static int Blocked(Ctx ctx, BlockedException b)
        {
            ctx.blockedReason = b.Message;
            Debug.LogWarning(LogCapture.TAG + " BLOCKED：" + b.Message);
            return 2;
        }

        static int ToolFailure(Ctx ctx, Exception e)
        {
            ctx.error = e.GetType().Name + ": " + e.Message;
            ctx.errorStack = e.StackTrace;
            Debug.LogError(LogCapture.TAG + " 工具异常：" + ctx.error + "\n" + e.StackTrace);
            return 3;
        }

        /// <summary>测试定义的 udon_programs（脚本名 / 类型名）→ 类型；找不到的算前置条件不满足。</summary>
        static List<Type> UdonTypes(Ctx ctx)
        {
            var l = new List<Type>();
            var miss = new List<string>();
            foreach (var n in TJson.Sa(ctx.T("udon_programs")))
            {
                var t = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript(n) ?? Preflight.FindType(n);
                if (t == null) miss.Add(n); else l.Add(t);
            }
            if (miss.Count > 0) throw new BlockedException("udon_programs 里的脚本不在或没编译：" + string.Join("、", miss.ToArray()));
            return l;
        }

        /// <summary>收尾（只调一次）：改回、报告、结果行、回调。</summary>
        static void Finish(Ctx ctx, int exit, Action<int, string> done)
        {
            SessionState.EraseString(PendingKey);
            SessionState.EraseBool(ResumeKey);
            try { foreach (var e in ctx.undo.RollbackTo(0)) ctx.warnings.Add(e); } catch { }
            try { foreach (var e in ctx.undo.RollbackTo(0)) ctx.warnings.Add(e); } catch { }   // 失败过的再试一次
            if (ctx.undo.Failed.Any(f => f.StartsWith("JSON ", StringComparison.Ordinal)))
            {
                // edit_json 改过的文件写不回去：工程里留着测试改过的值，不能当没事（退出码 3），原文件在输出的 backup/
                ctx.error = (ctx.error != null ? ctx.error + "；" : "") + "改回失败、留在工程里：" + string.Join("、", ctx.undo.Failed.ToArray()) + "。原文件在输出文件夹的 backup/，停，告诉小楠";
                exit = 3;
            }
            try { EditorUtility.ClearProgressBar(); } catch { }
            // 报告（报告写不出来也算工具异常）
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
            finally { ctx.log.Stop(); }
            Final(ResultLine(ctx, exit));
            // 1.3.0（D-50 #9）：报告写完以后再听 3 秒 Console：SDK 的 RunBehaviourSetup 这类延迟回调会在测试结束后才抛异常
            // （本地 gate_clouds_test-06），以前没算进去。来了就记进 late_console.jsonl、改 result.json（pass 降成 fail）
            if (ctx.outDir != null && !ctx.preflightOnly) LateConsole.Watch(ctx.outDir, 3.0, () => { if (done != null) done(exit, ctx.outDir); });
            else if (done != null) done(exit, ctx.outDir);
        }

        static void Prepare(Ctx ctx)
        {
            // 2) 沙盒、写入快照、场景
            Sandbox.Prepare(ctx);
            ctx.before = WriteGuard.Take(ctx.projectDir);
            WriteGuard.BackupBefore(ctx);       // backup_before：会被搭建脚本改的文件，开搭之前原样拷一份进输出文件夹
            Scenes.Open(ctx);
            Preflight.ScenePreconditions(ctx);
        }

        static int Body(Ctx ctx)
        {
            // 1.2.0：测试定义有 play 的（transitions_sweep、flicker_probe），搭建以后进 Play 模式去拍，收尾在退出 Play 以后
            if (PlayPhase.Wants(ctx))
            {
                bool okBuild = Steps.RunList(ctx, TJson.L(ctx.T("build")), "build", null, true);
                if (!okBuild) { ctx.Warn("搭建有一步失败，不进 Play"); return 1; }
                Preflight.ProjectSettingsChecks(ctx);
                return PlayPhase.Begin(ctx);
            }
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
            if (ctx.toolErrors.Count > 0)
            {
                ctx.error = "工具自己的代码出了 " + ctx.toolErrors.Count + " 次异常（详情在 manifest 的 tool_errors）：" + ctx.toolErrors[0].Split('\n')[0];
                return 3;
            }
            return failed > 0 ? 1 : 0;
        }

        /// <summary>只做预检时不报 pass（没跑测试）：通过 = preflight_ok。</summary>
        public static string StatusOf(Ctx ctx, int exit)
        {
            if (ctx != null && ctx.preflightOnly) return exit == 0 ? "preflight_ok" : StatusOf(exit);
            return StatusOf(exit);
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
            r["status"] = StatusOf(ctx, exit);
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
            // 一律从磁盘上的版本开始（in_place 时也重开一次：预检已经保证没有没保存的改动，重开不丢东西）
            EditorSceneManager.OpenScene(open, OpenSceneMode.Single);
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
