// 蓝白 · Director · editor side. v1, 2026-10-23, 总工程师.
// !!! NOT COMPILED IN UNITY: Roslyn type-check only. !!!
//
// 蓝白/Director/1 Generate Dispatcher : finds every UdonSharpBehaviour class with the act interface (CONTROL_总控.md §5:
//     public void LanbaiTick(float), public void LanbaiActivate(bool), public float[] LanbaiWindow())
//   and rewrites the generated regions of Director/Runtime/LanbaiActDispatcher.cs (one typed array per class). Unity then
//   recompiles; UdonSharp recompiles the dispatcher's program asset.
// 蓝白/Director/2 Wire Scene        : (after the recompile) makes sure the scene has Lanbai/Director with the dispatcher
//   (creates its UdonSharpProgramAsset next to the script if none exists, CONTROL §6 item 11), and fills every typed array
//   with all instances of that class in the open scene (inactive ones too), in hierarchy order.
// 蓝白/Director/3 Report            : prints every driver, its window, and the overlaps between windows (two drivers active
//   at the same t must not write the same global / RenderSettings / renderer: Engineering/README_集成.md §2).
// UdonSharp editor APIs are reached by reflection so this file type-checks without the UdonSharp editor assembly; if a
// call is not found, the menu says what to do by hand.
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Director.Editor
{
    public static class LanbaiDirectorGen
    {
        const string DispatcherClass = "LanbaiActDispatcher";

        public static List<Type> DriverTypes()
        {
            var baseType = FindType("UdonSharp.UdonSharpBehaviour");
            var list = new List<Type>();
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] types;
                try { types = asm.GetTypes(); } catch (ReflectionTypeLoadException e) { types = e.Types.Where(x => x != null).ToArray(); }
                foreach (var t in types)
                {
                    if (t == null || t.IsAbstract || t.Name == DispatcherClass) continue;
                    if (baseType != null && !baseType.IsAssignableFrom(t)) continue;
                    if (IsDriver(t)) list.Add(t);
                }
            }
            return list.OrderBy(t => t.FullName, StringComparer.Ordinal).ToList();
        }

        public static bool IsDriver(Type t)
        {
            const BindingFlags F = BindingFlags.Public | BindingFlags.Instance;
            var tick = t.GetMethod("LanbaiTick", F, null, new[] { typeof(float) }, null);
            var act = t.GetMethod("LanbaiActivate", F, null, new[] { typeof(bool) }, null);
            var win = t.GetMethod("LanbaiWindow", F, null, Type.EmptyTypes, null);
            return tick != null && act != null && win != null && win.ReturnType == typeof(float[]);
        }

        static Type FindType(string fullName)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType(fullName, false);
                if (t != null) return t;
            }
            return null;
        }

        static string DispatcherPath()
        {
            foreach (var guid in AssetDatabase.FindAssets(DispatcherClass + " t:MonoScript"))
            {
                var p = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(p) == DispatcherClass) return p;
            }
            return null;
        }

        static string Replace(string src, string tag, string body)
        {
            string a = "// <" + tag + ">", b = "// </" + tag + ">";
            int i = src.IndexOf(a, StringComparison.Ordinal), j = src.IndexOf(b, StringComparison.Ordinal);
            if (i < 0 || j < i) throw new Exception("region " + tag + " not found in " + DispatcherClass + ".cs");
            int lineStart = src.LastIndexOf('\n', i) + 1;
            string indent = src.Substring(lineStart, i - lineStart);
            return src.Substring(0, i + a.Length) + "\n" + body + indent + src.Substring(j);
        }

        public static string Generate(string src, List<Type> types)
        {
            var fields = new StringBuilder();
            var start = new StringBuilder();
            var wins = new StringBuilder();
            var disp = new StringBuilder();
            const BindingFlags PF = BindingFlags.Public | BindingFlags.Instance;
            for (int k = 0; k < types.Count; k++)
            {
                string c = types[k].FullName.Replace('+', '.'), d = "d" + k;
                fields.AppendFormat("    public {0}[] {1};          // {2}\n    private bool[] {1}_on;\n    private float[] {1}_w;\n", c, d, types[k].Name);
                start.AppendFormat(
                    "        if ({0} == null) {0} = new {1}[0];\n" +
                    "        {0}_on = new bool[{0}.Length];\n" +
                    "        {0}_w = new float[2 * {0}.Length];\n" +
                    "        for (int i = 0; i < {0}.Length; i++)\n" +
                    "        {{\n" +
                    "            {0}_w[2 * i] = 1e9f; {0}_w[2 * i + 1] = -1e9f;\n" +
                    "            if ({0}[i] == null) continue;\n" +
                    "            float[] w = {0}[i].LanbaiWindow();\n" +
                    "            if (w != null && w.Length >= 2) {{ {0}_w[2 * i] = w[0]; {0}_w[2 * i + 1] = w[1]; n++; }}\n" +
                    "        }}\n", d, c);
                wins.AppendFormat(
                    "        for (int i = 0; i < {0}.Length; i++)\n" +
                    "            if ({0}_w[2 * i] <= {0}_w[2 * i + 1]) {{ windowsFlat[2 * n] = {0}_w[2 * i]; windowsFlat[2 * n + 1] = {0}_w[2 * i + 1]; n++; }}\n", d);
                var gm = types[k].GetMethod("LanbaiGrade", PF, null, new[] { typeof(float) }, null);
                bool hasGrade = gm != null && gm.ReturnType == typeof(float[]);
                string grade = hasGrade
                    ? "                float[] g = d.LanbaiGrade(t);\n" +
                      "                if (g != null && g.Length >= 4)\n" +
                      "                {\n" +
                      "                    gradeOwned = true; gradeDEV += g[0];\n" +
                      "                    gradeWhiteSat = Mathf.Max(gradeWhiteSat, g[1]); gradeWhiteBloom = Mathf.Max(gradeWhiteBloom, g[2]);\n" +
                      "                    gradeLensClean = Mathf.Min(gradeLensClean, g[3]);\n" +
                      "                }\n"
                    : "";
                disp.AppendFormat(
                    "        for (int i = 0; i < {0}.Length; i++)\n" +
                    "        {{\n" +
                    "            {1} d = {0}[i];\n" +
                    "            if (d == null) continue;\n" +
                    "            bool inside = hold || (t >= {0}_w[2 * i] && t < {0}_w[2 * i + 1]);\n" +
                    "            if (inside != {0}_on[i]) {{ d.LanbaiActivate(inside); {0}_on[i] = inside; }}\n" +
                    "            if (inside && !hold)\n" +
                    "            {{\n" +
                    "                d.LanbaiTick(t); act++;\n" +
                    "{2}" +
                    "            }}\n" +
                    "        }}\n", d, c, grade);
            }
            src = Replace(src, "LANBAI-GENERATED-FIELDS", fields.ToString());
            src = Replace(src, "LANBAI-GENERATED-START", start.ToString());
            src = Replace(src, "LANBAI-GENERATED-WINDOWS", wins.ToString());
            src = Replace(src, "LANBAI-GENERATED-DISPATCH", disp.ToString());
            return src;
        }

        [MenuItem("蓝白/Director/1 Generate Dispatcher")]
        public static void GenerateMenu()
        {
            var path = DispatcherPath();
            if (path == null) { Debug.LogError("[Lanbai Director] " + DispatcherClass + ".cs not found (copy Director/ to Assets/Lanbai/Director/)"); return; }
            var types = DriverTypes();
            var src = File.ReadAllText(path);
            var gen = Generate(src, types);
            var sb = new StringBuilder("[Lanbai Director] drivers found: " + types.Count + "\n");
            foreach (var t in types) sb.AppendLine("  " + t.FullName);
            if (gen == src) { Debug.Log(sb + "dispatcher unchanged."); return; }
            File.WriteAllText(path, gen);
            AssetDatabase.ImportAsset(path);
            Debug.Log(sb + "dispatcher regenerated: wait for the recompile, then run 蓝白/Director/2 Wire Scene.");
        }

        [MenuItem("蓝白/Director/2 Wire Scene")]
        public static void WireMenu()
        {
            var dispType = FindType(DispatcherClass);
            if (dispType == null) { Debug.LogError("[Lanbai Director] " + DispatcherClass + " is not compiled yet"); return; }
            EnsureProgramAsset(dispType);
            var comp = UnityEngine.Object.FindObjectsOfType(dispType, true).FirstOrDefault() as Component;
            if (comp == null)
            {
                var root = GameObject.Find("Lanbai") ?? new GameObject("Lanbai");
                var go = new GameObject("Director");
                go.transform.SetParent(root.transform, false);
                Undo.RegisterCreatedObjectUndo(go, "Lanbai Director");
                comp = AddUdonSharpComponent(go, dispType);
                if (comp == null) { Debug.LogError("[Lanbai Director] could not add " + DispatcherClass + ": add it by hand to Lanbai/Director, then run this menu again"); return; }
            }
            var report = new StringBuilder("[Lanbai Director] wired:\n");
            foreach (var f in dispType.GetFields(BindingFlags.Public | BindingFlags.Instance))
            {
                if (!f.FieldType.IsArray || !f.Name.StartsWith("d", StringComparison.Ordinal)) continue;
                var et = f.FieldType.GetElementType();
                if (et == null || !IsDriver(et)) continue;
                var found = UnityEngine.Object.FindObjectsOfType(et, true).Cast<Component>()
                    .OrderBy(c => HierarchyPath(c.transform), StringComparer.Ordinal).ToArray();
                var arr = Array.CreateInstance(et, found.Length);
                for (int i = 0; i < found.Length; i++) arr.SetValue(found[i], i);
                Undo.RecordObject(comp, "Lanbai Director wire");
                f.SetValue(comp, arr);
                report.AppendFormat("  {0} <- {1} x {2}\n", f.Name, et.Name, found.Length);
                foreach (var c in found)
                    if (!c.gameObject.activeInHierarchy)
                        report.AppendFormat("    ! {0} is on an INACTIVE object: put the driver on an always-active object and let LanbaiActivate switch a separate root\n", HierarchyPath(c.transform));
            }
            CopyProxyToUdon(comp);
            EditorUtility.SetDirty(comp);
            Debug.Log(report.ToString() + "LB_Journey: call dispatcher.LanbaiDispatch(t) every frame and dispatcher.LanbaiPrewarm() at spawn.");
        }

        [MenuItem("蓝白/Director/3 Report")]
        public static void ReportMenu()
        {
            var sb = new StringBuilder("[Lanbai Director] driver windows (from LanbaiWindow() on the scene instances):\n");
            var wins = new List<KeyValuePair<string, float[]>>();
            foreach (var t in DriverTypes())
                foreach (var c in UnityEngine.Object.FindObjectsOfType(t, true).Cast<Component>())
                {
                    float[] w = null;
                    try { w = (float[])t.GetMethod("LanbaiWindow").Invoke(c, null); } catch (Exception e) { sb.AppendLine("  " + t.Name + ": LanbaiWindow threw " + e.GetBaseException().Message); }
                    if (w == null || w.Length < 2) continue;
                    wins.Add(new KeyValuePair<string, float[]>(t.Name + " (" + HierarchyPath(c.transform) + ")", w));
                    sb.AppendFormat("  {0,8:F2} .. {1,8:F2}  {2}\n", w[0], w[1], t.Name + " @ " + HierarchyPath(c.transform));
                }
            for (int i = 0; i < wins.Count; i++)
                for (int j = i + 1; j < wins.Count; j++)
                {
                    float a = Mathf.Max(wins[i].Value[0], wins[j].Value[0]), b = Mathf.Min(wins[i].Value[1], wins[j].Value[1]);
                    if (a < b) sb.AppendFormat("  overlap {0:F2} .. {1:F2}: {2} / {3} (must not write the same things)\n", a, b, wins[i].Key, wins[j].Key);
                }
            Debug.Log(sb.ToString());
        }

        static string HierarchyPath(Transform t)
        {
            var s = t.name;
            while (t.parent != null) { t = t.parent; s = t.name + "/" + s; }
            return s;
        }

        // ---- UdonSharp editor calls by reflection ----------------------------------------------------------------
        static Component AddUdonSharpComponent(GameObject go, Type t)
        {
            var undo = FindType("UdonSharpEditor.UdonSharpUndo");
            var m = undo != null ? undo.GetMethod("AddComponent", BindingFlags.Public | BindingFlags.Static, null, new[] { typeof(GameObject), typeof(Type) }, null) : null;
            if (m != null) return m.Invoke(null, new object[] { go, t }) as Component;
            return null;
        }

        static void CopyProxyToUdon(Component proxy)
        {
            var util = FindType("UdonSharpEditor.UdonSharpEditorUtility");
            var m = util != null ? util.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(x => x.Name == "CopyProxyToUdon" && x.GetParameters().Length == 1) : null;
            if (m != null) { try { m.Invoke(null, new object[] { proxy }); } catch (Exception) { } }
        }

        static void EnsureProgramAsset(Type dispType)
        {
            var pa = FindType("UdonSharp.UdonSharpProgramAsset");
            if (pa == null) return;
            var script = AssetDatabase.LoadAssetAtPath<MonoScript>(DispatcherPath());
            var srcField = pa.GetField("sourceCsScript", BindingFlags.Public | BindingFlags.Instance);
            foreach (var guid in AssetDatabase.FindAssets("t:" + pa.Name))
            {
                var a = AssetDatabase.LoadAssetAtPath(AssetDatabase.GUIDToAssetPath(guid), pa);
                if (a != null && srcField != null && (UnityEngine.Object)srcField.GetValue(a) == script) return;
            }
            var asset = ScriptableObject.CreateInstance(pa);
            if (srcField != null) srcField.SetValue(asset, script);
            var p = Path.ChangeExtension(DispatcherPath(), ".asset");
            AssetDatabase.CreateAsset(asset, p);
            AssetDatabase.SaveAssets();
            Debug.Log("[Lanbai Director] created the UdonSharp program asset " + p);
        }
    }
}
#endif
