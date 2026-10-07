// 蓝白 · 触手之门 · 导入测试：两个套件里的 UdonSharp 脚本过一遍 U# 编译器
//   U# 1.x 只编译有程序资产（UdonSharpProgramAsset）的脚本；套件的 LanbaiExposure.cs、LanbaiTearParams.cs 还没有，
//   所以 C# 编译通过不代表 U# 能编译。这里给它们在 Assets/Lanbai/Tests/UdonPrograms/ 建程序资产，再让 U# 全部编译一次。
using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Tests
{
    public static partial class LB_GateTest
    {
        const string UDON_DIR = "Assets/Lanbai/Tests/UdonPrograms";
        static readonly string[] KIT_US = { "Assets/Lanbai/Grading/Runtime/LanbaiExposure.cs", "Assets/Lanbai/Tear/LanbaiTearParams.cs" };

        static Type FindTypeAny(string full)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType(full, false);
                if (t != null) return t;
            }
            return null;
        }

        public static string UdonCheck(string arg)
        {
            var sb = new StringBuilder();
            var paType = FindTypeAny("UdonSharp.UdonSharpProgramAsset");
            if (paType == null) return "没找到 UdonSharp.UdonSharpProgramAsset";
            EnsureFolder(UDON_DIR);
            foreach (var path in KIT_US)
            {
                var ms = AssetDatabase.LoadAssetAtPath<MonoScript>(path);
                if (ms == null) { sb.AppendLine(path + "：没找到脚本"); continue; }
                string ap = UDON_DIR + "/" + Path.GetFileNameWithoutExtension(path) + ".asset";
                var pa = AssetDatabase.LoadAssetAtPath(ap, paType);
                if (pa == null)
                {
                    pa = ScriptableObject.CreateInstance(paType);
                    var f = paType.GetField("sourceCsScript", BindingFlags.Public | BindingFlags.Instance);
                    if (f == null) { sb.AppendLine("UdonSharpProgramAsset 没有 sourceCsScript 字段"); continue; }
                    f.SetValue(pa, ms);
                    AssetDatabase.CreateAsset(pa, ap);
                    sb.AppendLine("建了程序资产 " + ap + " → " + path);
                }
                else sb.AppendLine("程序资产已有 " + ap);
            }
            AssetDatabase.SaveAssets();
            // 让 U# 全部编译一次（同步）
            var m = paType.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(x => x.Name == "CompileAllCsPrograms");
            if (m != null)
            {
                var ps = m.GetParameters();
                // forceCompile = true；其余参数用默认值（editorBuild 默认 true：编辑器里的正常编译。传 false 是打包时的模式，编辑器里没有打包的引用，会报一堆假错）
                var args = ps.Select(p => p.ParameterType == typeof(bool) && p.Name.ToLower().Contains("force") ? (object)true : (p.HasDefaultValue ? p.DefaultValue : (p.ParameterType == typeof(bool) ? (object)true : null))).ToArray();
                try { m.Invoke(null, args); sb.AppendLine("调用了 UdonSharpProgramAsset.CompileAllCsPrograms(" + string.Join(", ", ps.Select((p, i) => p.Name + "=" + args[i])) + ")"); }
                catch (TargetInvocationException e) { sb.AppendLine("U# 编译抛异常：" + (e.InnerException ?? e).Message); }
            }
            else sb.AppendLine("没找到 CompileAllCsPrograms");
            // 读结果
            var any = paType.GetMethod("AnyUdonSharpScriptHasError", BindingFlags.Public | BindingFlags.Static);
            if (any != null) sb.AppendLine("AnyUdonSharpScriptHasError = " + any.Invoke(null, null));
            foreach (var path in KIT_US)
            {
                string ap = UDON_DIR + "/" + Path.GetFileNameWithoutExtension(path) + ".asset";
                var pa = AssetDatabase.LoadAssetAtPath(ap, paType);
                if (pa == null) continue;
                var ce = paType.GetField("compileErrors", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                var list = ce != null ? ce.GetValue(pa) as IList : null;
                var hasErr = paType.GetMethod("HasErrors", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance, null, Type.EmptyTypes, null);
                sb.AppendLine(Path.GetFileName(path) + "：" + (list != null ? "compileErrors " + list.Count + (list.Count > 0 ? "：" + string.Join(" | ", list.Cast<object>()) : "") : "（读不到 compileErrors）") +
                              (hasErr != null ? "，HasErrors " + hasErr.Invoke(pa, null) : ""));
            }
            return sb.ToString();
        }
    }
}
