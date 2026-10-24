// ═══════════════════════════════════════════════════════════════════
//  蓝白 · U# 程序资产的共用工具（D-41，总工程师）
//  所有搭建脚本都用它：查已有的程序资产、缺了就建、等 SDK 把版本初始化完、加组件、CopyProxyToUdon。
//
//  为什么要它（本地 gate_clouds_test-03，S0）：
//    * SDK 3.10.5 的 UdonSharpEditorUtility.GetUdonSharpProgramAsset 公开的重载接 Type；接 MonoScript 的那个是 private。
//      以前按 MonoScript 反射去查，永远查不到，每次都新建一个程序资产。
//    * 新建的程序资产，SDK 要在之后的 EditorApplication.update 里才把 ScriptVersion / CompiledVersion 升到 CurrentVersion。
//      没升完就 CopyProxyToUdon，会抛 “outdated script version”。
//  规矩：
//    * 按 Type 查（SDK 的公开重载），再扫一遍所有程序资产核对 sourceCsScript；查到就复用，不另建。
//    * 新建以后，等两项版本都到 CurrentVersion（“2/2”）才算 Ready；搭建菜单用 RunWhenReady 排队等，等到了再搭。
//    * 绝不手写版本号，不调 Force Upgrade。只在“脚本版本到了、编译版本没到”时请一次编辑器模式的编译（CompileSync）。
//    * 失败报清楚（哪个类型、哪个资产、两个版本各是多少），不静默重建；目标路径上有一个不认识的资产时不覆盖。
//  全部走反射：没有 UdonSharp 的工程也编得过（这时 Available = false，搭建脚本照原样退回普通 AddComponent 并报警告）。
//  没在 Unity 里编译过、跑过（只过了 Common/Tools~/compile_check）。
// ═══════════════════════════════════════════════════════════════════
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Lanbai.Udon
{
    public enum ProgramState { NoUdonSharp, NoScript, Missing, Initializing, Ready, Conflict }

    [InitializeOnLoad]
    public static class LanbaiUdonPrograms
    {
        public const string DefaultFolder = "Assets/Lanbai/UdonPrograms";
        public const double TimeoutSeconds = 180.0;
        const string TAG = "[Lanbai U#] ";

        // ── SDK 的类型（反射）────────────────────────────────────────
        static Type _pa, _util, _undo, _ver, _compiler;
        static bool _looked;
        static void Look()
        {
            if (_looked) return;
            _looked = true;
            _pa = FindType("UdonSharp.UdonSharpProgramAsset");
            _util = FindType("UdonSharpEditor.UdonSharpEditorUtility");
            _undo = FindType("UdonSharpEditor.UdonSharpUndo");
            _ver = FindType("UdonSharp.UdonSharpProgramVersion");
            _compiler = FindType("UdonSharp.Compiler.UdonSharpCompilerV1");
        }

        /// <summary>工程里有没有 UdonSharp（SDK 3.4 起随 VRChat Worlds SDK）。</summary>
        public static bool Available { get { Look(); return _pa != null && _util != null; } }

        public static Type FindType(string fullName)
        {
            foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = a.GetType(fullName, false);
                if (t != null) return t;
            }
            return null;
        }

        /// <summary>按脚本名（不带 .cs）找它编出来的类型；找不到返回 null。</summary>
        public static Type TypeOfScript(string scriptName)
        {
            foreach (string g in AssetDatabase.FindAssets(scriptName + " t:MonoScript"))
            {
                string p = AssetDatabase.GUIDToAssetPath(g);
                if (Path.GetFileNameWithoutExtension(p) != scriptName) continue;
                var ms = AssetDatabase.LoadAssetAtPath<MonoScript>(p);
                if (ms != null && ms.GetClass() != null) return ms.GetClass();
            }
            return null;
        }

        public static MonoScript ScriptOf(Type t)
        {
            foreach (string g in AssetDatabase.FindAssets(t.Name + " t:MonoScript"))
            {
                var ms = AssetDatabase.LoadAssetAtPath<MonoScript>(AssetDatabase.GUIDToAssetPath(g));
                if (ms != null && ms.GetClass() == t) return ms;
            }
            return null;
        }

        /// <summary>新程序资产默认放哪：Assets/Lanbai/UdonPrograms/&lt;类型名&gt;.asset。</summary>
        public static string DefaultPath(Type t) { return DefaultFolder + "/" + t.Name + ".asset"; }

        /// <summary>放在脚本旁边：Foo.cs → Foo.asset（天空、诗、Director 以前的习惯）。</summary>
        public static string NextToScript(Type t)
        {
            var ms = ScriptOf(t);
            string sp = ms != null ? AssetDatabase.GetAssetPath(ms) : null;
            return string.IsNullOrEmpty(sp) ? DefaultPath(t) : sp.Substring(0, sp.Length - 3) + ".asset";
        }

        // ── 查 ──────────────────────────────────────────────────────
        /// <summary>这个类型已有的程序资产（SDK 的公开 Type 重载；再扫一遍全部程序资产核对 sourceCsScript）。没有返回 null；有两个以上时报警告、用 SDK 给的那个。</summary>
        public static Object Find(Type t)
        {
            if (!Available) return null;
            Object viaSdk = null;
            var m = _util.GetMethod("GetUdonSharpProgramAsset", BindingFlags.Public | BindingFlags.Static, null, new[] { typeof(Type) }, null);
            if (m != null)
            {
                try { viaSdk = m.Invoke(null, new object[] { t }) as Object; }
                catch (TargetInvocationException e) { Debug.LogWarning(TAG + "GetUdonSharpProgramAsset(" + t.Name + ") threw: " + e.InnerException); }
            }
            var all = Scan(t);
            if (all.Count > 1)
                Debug.LogWarning(TAG + t.Name + " has " + all.Count + " program assets: " + string.Join(", ", all.Select(AssetDatabase.GetAssetPath).ToArray()) +
                                 ". Keep one (the SDK uses " + (viaSdk != null ? AssetDatabase.GetAssetPath(viaSdk) : all[0].name) + "), delete the others in the Project window.");
            return viaSdk != null ? viaSdk : (all.Count > 0 ? all[0] : null);
        }

        static List<Object> Scan(Type t)
        {
            var r = new List<Object>();
            var src = _pa.GetField("sourceCsScript", BindingFlags.Public | BindingFlags.Instance);
            foreach (string g in AssetDatabase.FindAssets("t:" + _pa.Name))
            {
                var a = AssetDatabase.LoadAssetAtPath(AssetDatabase.GUIDToAssetPath(g), _pa);
                var ms = a != null && src != null ? src.GetValue(a) as MonoScript : null;
                if (ms != null && ms.GetClass() == t) r.Add(a);
            }
            return r;
        }

        // ── 状态 ────────────────────────────────────────────────────
        /// <summary>两个版本：ScriptVersion、CompiledVersion，和 SDK 的 CurrentVersion。读不到时返回 false。</summary>
        public static bool Versions(Object asset, out int script, out int compiled, out int current)
        {
            script = compiled = current = -1;
            if (asset == null || _pa == null || _ver == null) return false;
            const BindingFlags F = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
            var ps = _pa.GetProperty("ScriptVersion", F); var pc = _pa.GetProperty("CompiledVersion", F);
            var cur = _ver.GetField("CurrentVersion", BindingFlags.Public | BindingFlags.Static);
            if (ps == null || pc == null || cur == null) return false;
            script = Convert.ToInt32(ps.GetValue(asset, null));
            compiled = Convert.ToInt32(pc.GetValue(asset, null));
            current = Convert.ToInt32(cur.GetValue(null));
            return true;
        }

        public static ProgramState StateOf(Type t, out Object asset, out string detail)
        {
            asset = null;
            if (!Available) { detail = "UdonSharp 不在这个工程里"; return ProgramState.NoUdonSharp; }
            if (ScriptOf(t) == null) { detail = t.Name + ".cs 不在工程里，或者还没编译"; return ProgramState.NoScript; }
            asset = Find(t);
            if (asset == null) { detail = t.Name + " 还没有程序资产"; return ProgramState.Missing; }
            int s, c, cur;
            if (!Versions(asset, out s, out c, out cur))
            {
                detail = AssetDatabase.GetAssetPath(asset) + "：这个 SDK 版本读不到 ScriptVersion / CompiledVersion，当作已初始化";
                return ProgramState.Ready;
            }
            detail = AssetDatabase.GetAssetPath(asset) + "：ScriptVersion " + s + " / CompiledVersion " + c + "（SDK 当前 " + cur + "）";
            return s == cur && c == cur ? ProgramState.Ready : ProgramState.Initializing;
        }

        public static bool AllReady(IEnumerable<Type> types, out string report)
        {
            var sb = new StringBuilder();
            bool ok = true;
            foreach (var t in types)
            {
                Object a; string d;
                var st = StateOf(t, out a, out d);
                sb.Append("  ").Append(t.Name).Append("：").Append(st).Append("，").Append(d).Append('\n');
                if (st != ProgramState.Ready) ok = false;
            }
            report = sb.ToString();
            return ok;
        }

        // ── 建 ──────────────────────────────────────────────────────
        /// <summary>缺程序资产的就建（pathFor 决定放哪，默认 Assets/Lanbai/UdonPrograms/）。不覆盖目标路径上已有的任何资产。返回新建了几个。</summary>
        public static int CreateMissing(string who, IEnumerable<Type> types, Func<Type, string> pathFor = null)
        {
            if (!Available) return 0;
            int made = 0;
            foreach (var t in types)
            {
                Object a; string d;
                var st = StateOf(t, out a, out d);
                if (st == ProgramState.NoScript) throw new InvalidOperationException(TAG + who + "：" + d);
                if (st != ProgramState.Missing) continue;
                string path = (pathFor ?? DefaultPath)(t);
                if (AssetDatabase.LoadMainAssetAtPath(path) != null || File.Exists(path))
                    throw new InvalidOperationException(TAG + who + "：" + path + " 已经有一个资产，但 SDK 认不出它是 " + t.Name +
                                                        " 的程序资产。工具不覆盖它：在 Inspector 里看一眼（Source Script 对不对），删掉或修好以后再点一次");
                string dir = Path.GetDirectoryName(path).Replace('\\', '/');
                EnsureFolder(dir);
                var asset = ScriptableObject.CreateInstance(_pa);
                var src = _pa.GetField("sourceCsScript", BindingFlags.Public | BindingFlags.Instance);
                if (src == null) throw new InvalidOperationException(TAG + "UdonSharpProgramAsset.sourceCsScript 不在：SDK 版本不对");
                src.SetValue(asset, ScriptOf(t));
                AssetDatabase.CreateAsset(asset, path);
                made++;
                Debug.Log(TAG + who + "：建了 " + path + "（等 SDK 初始化版本，之后自动继续）");
            }
            if (made > 0) { AssetDatabase.SaveAssets(); AssetDatabase.Refresh(); }
            return made;
        }

        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }

        // ── 排队等 ──────────────────────────────────────────────────
        sealed class Job
        {
            public string who; public Type[] types; public Action build; public Action<string> fail;
            public double deadline, created, nextTick; public bool compileAsked;
        }
        static readonly List<Job> _jobs = new List<Job>();

        // ── domain reload：排着队的搭建会丢（静态表和委托都不活过 reload）──────────
        // 所以排队时把菜单路径记进 SessionState（编辑器开着就一直在，reload 也在），reload 以后自动再点一次那个菜单；
        // 菜单本身是幂等的：程序资产已经建了就复用，没初始化完就再排队。每个菜单最多自动续 3 次，免得来回转。
        // 不是菜单的排队（测试工具自己的）由测试工具自己续（Engineering/UnityTest/Editor/LanbaiTestRunner.cs）。
        const string PendingKey = "Lanbai.Udon.PendingMenus", ResumeKey = "Lanbai.Udon.ResumeCount.";

        static LanbaiUdonPrograms()
        {
            string pending = SessionState.GetString(PendingKey, "");
            if (string.IsNullOrEmpty(pending)) return;
            SessionState.EraseString(PendingKey);
            EditorApplication.delayCall += () =>
            {
                foreach (var menu in pending.Split('\n'))
                {
                    if (string.IsNullOrEmpty(menu)) continue;
                    int n = SessionState.GetInt(ResumeKey + menu, 0) + 1;
                    SessionState.SetInt(ResumeKey + menu, n);
                    if (n > 3) { Debug.LogError(TAG + "domain reload 以后已经自动续了 3 次 “" + menu + "”，不再续：看 Console 里 UdonSharp 的报错，好了以后手动再点一次"); continue; }
                    Debug.Log(TAG + "编辑器 reload 过（编译 / 导入），排着队的 “" + menu + "” 丢了：自动再点一次（第 " + n + " 次）");
                    if (!EditorApplication.ExecuteMenuItem(menu)) Debug.LogError(TAG + "自动再点 “" + menu + "” 失败（菜单不在？）：请手动点一次");
                }
            };
        }

        static void RememberMenu(string who)
        {
            if (!who.StartsWith("蓝白/", StringComparison.Ordinal)) return;
            var l = SessionState.GetString(PendingKey, "").Split('\n').Where(x => x.Length > 0).ToList();
            if (!l.Contains(who)) l.Add(who);
            SessionState.SetString(PendingKey, string.Join("\n", l.ToArray()));
        }

        static void ForgetMenu(string who, bool success)
        {
            var l = SessionState.GetString(PendingKey, "").Split('\n').Where(x => x.Length > 0 && x != who).ToList();
            if (l.Count == 0) SessionState.EraseString(PendingKey); else SessionState.SetString(PendingKey, string.Join("\n", l.ToArray()));
            if (success) SessionState.EraseInt(ResumeKey + who);
        }

        /// <summary>有没有搭建在排队等程序资产。</summary>
        public static bool Busy { get { return _jobs.Count > 0; } }

        /// <summary>
        /// 搭建菜单用：程序资产都 Ready 就马上 build() 并返回 true；不然缺的先建好，排进 EditorApplication.update，
        /// 等 SDK 初始化完（2/2）再 build()，返回 false。超时或出错调 fail（默认 Debug.LogError），不重建、不改版本号。
        /// </summary>
        public static bool RunWhenReady(string who, IEnumerable<Type> types, Action build, Func<Type, string> pathFor = null, Action<string> fail = null)
        {
            var ts = types.Where(t => t != null).Distinct().ToArray();
            if (fail == null) fail = msg => Debug.LogError(msg);
            if (!Available)
            {
                Debug.LogWarning(TAG + who + "：UdonSharp 不在这个工程里，照原样搭（U# 组件不会有 UdonBehaviour，在 VRChat 里不会跑）");
                build();
                return true;
            }
            string rep;
            if (AllReady(ts, out rep)) { ForgetMenu(who, true); build(); return true; }
            try { CreateMissing(who, ts, pathFor); }
            catch (Exception e) { fail(e.Message); return false; }
            double now = EditorApplication.timeSinceStartup;
            _jobs.Add(new Job { who = who, types = ts, build = build, fail = fail, deadline = now + TimeoutSeconds, created = now, nextTick = now + 0.5 });
            RememberMenu(who);
            if (_jobs.Count == 1) EditorApplication.update += Tick;
            AllReady(ts, out rep);
            Debug.Log(TAG + who + "：程序资产还没初始化完，等 SDK（最多 " + TimeoutSeconds.ToString("0") + " 秒），初始化完自动接着搭：\n" + rep);
            return false;
        }

        static void Tick()
        {
            double now = EditorApplication.timeSinceStartup;
            if (EditorApplication.isCompiling || EditorApplication.isUpdating) return;
            for (int i = _jobs.Count - 1; i >= 0; i--)
            {
                var j = _jobs[i];
                if (now < j.nextTick) continue;
                j.nextTick = now + 0.5;
                string rep;
                bool ready;
                try { ready = AllReady(j.types, out rep); }
                catch (Exception e) { Finish(i); ForgetMenu(j.who, false); j.fail(TAG + j.who + "：查程序资产时出错：" + e); continue; }
                if (ready)
                {
                    Finish(i);
                    ForgetMenu(j.who, true);
                    Debug.Log(TAG + j.who + "：程序资产都初始化完了，接着搭");
                    try { j.build(); }
                    catch (Exception e) { j.fail(TAG + j.who + " 搭建失败：" + e); }
                    continue;
                }
                if (now > j.deadline)
                {
                    Finish(i);
                    ForgetMenu(j.who, false);
                    j.fail(TAG + j.who + "：等了 " + TimeoutSeconds.ToString("0") + " 秒，程序资产还没初始化完，没搭。工具不手写版本号、不 Force Upgrade：" +
                           "把 Console 里 UdonSharp 的报错原样推回来（可能是 U# 编译不过）。现在的状态：\n" + rep);
                    continue;
                }
                // 脚本版本到了、编译版本没到、也没在编译：请一次编辑器模式的编译（不是 Force Upgrade，不是 build 模式）
                if (!j.compileAsked && now - j.created > 2.0 && NeedsCompile(j.types)) { j.compileAsked = true; CompileOnce(j.who); }
            }
        }

        static void Finish(int i)
        {
            _jobs.RemoveAt(i);
            if (_jobs.Count == 0) EditorApplication.update -= Tick;
        }

        static bool NeedsCompile(Type[] types)
        {
            foreach (var t in types)
            {
                Object a; string d;
                if (StateOf(t, out a, out d) != ProgramState.Initializing) continue;
                int s, c, cur;
                if (Versions(a, out s, out c, out cur) && s == cur && c != cur) return true;
            }
            return false;
        }

        static void CompileOnce(string who)
        {
            if (_compiler == null) return;
            var m = _compiler.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(x => x.Name == "CompileSync");
            if (m == null) return;
            var ps = m.GetParameters();
            var args = new object[ps.Length];
            for (int k = 0; k < ps.Length; k++) args[k] = ps[k].HasDefaultValue ? ps[k].DefaultValue : null;   // 默认选项 = 编辑器模式
            Debug.Log(TAG + who + "：程序资产的编译版本没到，请一次编辑器模式的 U# 编译（CompileSync，默认选项）");
            try { m.Invoke(null, args); }
            catch (TargetInvocationException e) { Debug.LogError(TAG + who + "：U# 编译抛了异常：" + e.InnerException); }
        }

        // ── 用 ──────────────────────────────────────────────────────
        /// <summary>搭建脚本被直接调（不经过菜单）时，在动场景之前先调它：没 Ready 就抛异常，说清楚怎么办。</summary>
        public static void RequireReady(string who, params Type[] types)
        {
            if (!Available) return;
            string rep;
            if (AllReady(types, out rep)) return;
            throw new InvalidOperationException(TAG + who + "：U# 程序资产还没初始化完，没搭（场景没动）。用搭建菜单（它会先建程序资产、等 SDK 初始化完再搭），或者等 Console 里 “接着搭” 那一条：\n" + rep);
        }

        /// <summary>加一个 U# 组件（带它的 UdonBehaviour）：UdonSharpUndo.AddComponent；程序资产要已经 Ready。</summary>
        public static Component AddComponent(GameObject go, Type t)
        {
            if (!Available)
            {
                Debug.LogWarning(TAG + t.Name + "：UdonSharp 不在，普通 AddComponent（没有 UdonBehaviour）");
                return go.AddComponent(t);
            }
            RequireReady("AddComponent " + t.Name, t);
            Component c = null;
            if (_undo != null)
            {
                var m = _undo.GetMethod("AddComponent", BindingFlags.Public | BindingFlags.Static, null, new[] { typeof(GameObject), typeof(Type) }, null);
                if (m != null) c = m.Invoke(null, new object[] { go, t }) as Component;
                else
                {
                    var g = _undo.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(x => x.Name == "AddComponent" && x.IsGenericMethodDefinition && x.GetParameters().Length == 1);
                    if (g != null) c = g.MakeGenericMethod(t).Invoke(null, new object[] { go }) as Component;
                }
            }
            if (c == null)
            {
                c = go.AddComponent(t);
                var rbs = _util.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(x => x.Name == "RunBehaviourSetup" && x.GetParameters().Length >= 1);
                if (rbs != null) rbs.Invoke(null, FillArgs(rbs, c));
            }
            if (Backing(c) == null) throw new InvalidOperationException(TAG + t.Name + "：加上了组件，但没有背后的 UdonBehaviour（程序资产 " + PathOf(t) + "）。看 Console 里 UdonSharp 的报错");
            return c;
        }

        /// <summary>字段填好以后，把代理上的值拷进 UdonBehaviour。程序资产要已经 Ready；SDK 抛的异常原样往上抛（不吞）。</summary>
        public static void CopyProxyToUdon(Component proxy)
        {
            if (!Available || proxy == null) return;
            RequireReady("CopyProxyToUdon " + proxy.GetType().Name, proxy.GetType());
            var m = _util.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(x => x.Name == "CopyProxyToUdon" && x.GetParameters().Length == 1);
            if (m == null) throw new InvalidOperationException(TAG + "UdonSharpEditorUtility.CopyProxyToUdon 不在：SDK 版本不对");
            try { m.Invoke(null, new object[] { proxy }); }
            catch (TargetInvocationException e)
            {
                throw new InvalidOperationException(TAG + proxy.GetType().Name + " 的 CopyProxyToUdon 失败（程序资产 " + PathOf(proxy.GetType()) + "）：" + e.InnerException.Message, e.InnerException);
            }
            if (Backing(proxy) == null) throw new InvalidOperationException(TAG + proxy.GetType().Name + " 没有背后的 UdonBehaviour：看程序资产 " + PathOf(proxy.GetType()) + " 和 Console");
        }

        static object Backing(Component c)
        {
            var m = _util.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(x => x.Name == "GetBackingUdonBehaviour" && x.GetParameters().Length == 1);
            if (m == null) return c;   // 读不到就不判
            try { return m.Invoke(null, new object[] { c }); } catch { return null; }
        }

        static object[] FillArgs(MethodInfo m, object first)
        {
            var ps = m.GetParameters();
            var a = new object[ps.Length];
            a[0] = first;
            for (int k = 1; k < ps.Length; k++) a[k] = ps[k].HasDefaultValue ? ps[k].DefaultValue : null;
            return a;
        }

        static string PathOf(Type t) { var a = Find(t); return a != null ? AssetDatabase.GetAssetPath(a) : "（没有）"; }

        // ── 菜单：看状态（只读）─────────────────────────────────────
        [MenuItem("蓝白/U#/Program Asset Status (read only)")]
        static void StatusMenu()
        {
            if (!Available) { Debug.LogWarning(TAG + "UdonSharp 不在这个工程里"); return; }
            var types = new List<Type>();
            var src = _pa.GetField("sourceCsScript", BindingFlags.Public | BindingFlags.Instance);
            foreach (string g in AssetDatabase.FindAssets("t:" + _pa.Name))
            {
                var a = AssetDatabase.LoadAssetAtPath(AssetDatabase.GUIDToAssetPath(g), _pa);
                var ms = a != null && src != null ? src.GetValue(a) as MonoScript : null;
                if (ms != null && ms.GetClass() != null && !types.Contains(ms.GetClass())) types.Add(ms.GetClass());
            }
            string rep;
            AllReady(types, out rep);
            Debug.Log(TAG + "工程里的 U# 程序资产（" + types.Count + " 个类型）：\n" + rep + (Busy ? "有 " + _jobs.Count + " 个搭建在排队等。" : ""));
        }
    }
}
#endif
