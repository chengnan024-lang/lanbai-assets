// 蓝白 · Unity 测试工具 · 菜单（和批处理走同一个 Runner.Run）
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Lanbai.Test
{
    public static class TestMenu
    {
        const string M = "蓝白/Test/";

        [MenuItem(M + "Run gate_clouds_test", false, 1)] static void RunGate() { RunMenu("gate_clouds_test"); }
        [MenuItem(M + "Run act06_dawn", false, 2)] static void RunAct06() { RunMenu("act06_dawn"); }
        [MenuItem(M + "Run bus_slice", false, 3)] static void RunBus() { RunMenu("bus_slice"); }
        [MenuItem(M + "Run act01_spawn", false, 4)] static void RunAct01() { RunMenu("act01_spawn"); }
        [MenuItem(M + "Run palace_hotspot", false, 5)] static void RunPalace() { RunMenu("palace_hotspot"); }
        [MenuItem(M + "Run Other Test…", false, 20)] static void RunOther() { TestPicker.Open(false); }
        [MenuItem(M + "Preflight Only…", false, 21)] static void PreflightOnly() { TestPicker.Open(true); }
        [MenuItem(M + "Delete Sandbox (Assets/_LanbaiTest)", false, 40)] static void DeleteSandbox()
        {
            if (!Directory.Exists(Sandbox.DIR)) { EditorUtility.DisplayDialog("蓝白测试", "没有沙盒。", "好"); return; }
            if (!File.Exists(Sandbox.MarkerPath)) { EditorUtility.DisplayDialog("蓝白测试", Sandbox.DIR + " 没有标记文件，不是测试工具建的，不删。", "好"); return; }
            if (EditorUtility.DisplayDialog("蓝白测试", "删掉 " + Sandbox.DIR + "？（测试工具的沙盒，里面只有拷贝）", "删", "取消")) Sandbox.Delete(null);
        }
        [MenuItem(M + "Discard Test Scene Changes", false, 41)] static void Discard()
        {
            var s = SceneManager.GetActiveScene();
            bool ours = s.path.StartsWith(Sandbox.DIR + "/") || s.path.StartsWith("Assets/Lanbai/Tests/");
            if (!ours) { EditorUtility.DisplayDialog("蓝白测试", "当前场景 " + s.path + " 不是测试场景（沙盒里的拷贝或 Assets/Lanbai/Tests/ 下的），这个菜单不碰它。", "好"); return; }
            if (!s.isDirty) { EditorUtility.DisplayDialog("蓝白测试", "没有没保存的改动。", "好"); return; }
            if (EditorUtility.DisplayDialog("蓝白测试", "不保存，从磁盘重新打开 " + s.path + "？", "放弃改动", "取消"))
                EditorSceneManager.OpenScene(s.path, OpenSceneMode.Single);
        }
        [MenuItem(M + "Open Reports Folder", false, 42)] static void OpenReports()
        {
            string p = Path.GetFullPath(Path.Combine(Application.dataPath, "..", Runner.REPORTS));
            Directory.CreateDirectory(p);
            EditorUtility.RevealInFinder(p);
        }

        public static void RunMenu(string id, bool preflightOnly = false)
        {
            if (!preflightOnly && !EditorUtility.DisplayDialog("蓝白测试 " + id,
                    "开始跑 " + id + "？\n会在 " + Sandbox.DIR + "/ 里建沙盒、按测试定义搭场景、截图、量性能，可能要几分钟，期间编辑器不响应。\n工具不保存场景。", "开始", "取消")) return;
            // 要等 U# 程序资产初始化时（D-41），这里先返回，跑完再弹框
            Runner.Start(id, null, preflightOnly, "menu", (code, outDir) =>
            {
                string msg;
                switch (code)
                {
                    case 0: msg = preflightOnly ? "预检通过。" : "跑完了，检查全过。"; break;
                    case 1: msg = "跑完了，有检查没过。"; break;
                    case 2: msg = "BLOCKED：预检或前置条件不满足，没跑。"; break;
                    default: msg = "工具自己出了异常。"; break;
                }
                if (outDir != null && EditorUtility.DisplayDialog("蓝白测试 " + id, msg + "（退出码 " + code + "）\n\n" + outDir + "\n\n看 summary.md。", "打开文件夹", "关闭"))
                    EditorUtility.RevealInFinder(Path.Combine(outDir, "summary.md"));
            });
        }
    }

    public sealed class TestPicker : EditorWindow
    {
        bool _pre;
        Vector2 _scroll;
        public static void Open(bool preflightOnly)
        {
            var w = GetWindow<TestPicker>(true, preflightOnly ? "蓝白测试 · 只做预检" : "蓝白测试 · 选一个测试");
            w._pre = preflightOnly;
            w.minSize = new Vector2(360, 240);
        }
        void OnGUI()
        {
            var tests = Runner.ListTests();
            EditorGUILayout.LabelField("测试定义在 " + Runner.TESTS_DIR + "/", EditorStyles.miniLabel);
            if (tests.Count == 0) { EditorGUILayout.HelpBox("一个测试定义都没有：先用同步脚本把 Engineering/UnityTest/ 拷进来。", MessageType.Warning); return; }
            _scroll = EditorGUILayout.BeginScrollView(_scroll);
            foreach (var t in tests.ToList())
                if (GUILayout.Button(t)) { Close(); TestMenu.RunMenu(t, _pre); GUIUtility.ExitGUI(); }
            EditorGUILayout.EndScrollView();
        }
    }
}
