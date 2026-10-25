using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Lanbai.Tests
{
    // Local adapter for the already-authorized gate test. The upstream Runner
    // remains unmodified; its complete preflight and write guard still run.
    public static class LB_FormalTestEntry
    {
        [Serializable] class Completion { public int exit; public string output, finished; }
        public static string FinalizeGate()
        {
            var scene = SceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || scene.path != "Assets/_LanbaiTest/GateTest_play.unity" || scene.isDirty)
                throw new InvalidOperationException("Requires the saved official test output scene in edit mode");
            var descriptors = UnityEngine.Object.FindObjectsOfType<VRC.SDK3.Components.VRCSceneDescriptor>();
            var keep = GameObject.Find("GateTest_ClientSim");
            var extra = GameObject.Find("VRCWorld");
            if (descriptors.Length != 2 || keep == null || extra == null || extra.transform.childCount != 0 ||
                !descriptors.All(d => d.gameObject == keep || d.gameObject == extra))
                throw new InvalidOperationException("Unexpected descriptor arrangement; no scene mutation");
            var names = extra.GetComponents<Component>().Select(c => c.GetType().FullName).ToArray();
            if (names.Any(n => n != "UnityEngine.Transform" && n != "VRC.SDK3.Components.VRCSceneDescriptor"))
                throw new InvalidOperationException("Unexpected VRCWorld components: " + string.Join(", ", names));
            // The unmodified tool output was backed up and its sandbox scene is
            // retained on disk. Only remove the tool-created duplicate in memory.
            UnityEngine.Object.DestroyImmediate(extra);
            if (!EditorSceneManager.SaveScene(scene, "Assets/Lanbai/Tests/GateTest.unity"))
                throw new InvalidOperationException("Could not save the finalized gate test");
            return "Removed tool-created duplicate VRCWorld; retained the configured GateTest_ClientSim descriptor. " + LB_GateContinuation.FixTestReference();
        }
        public static string Run(string mode)
        {
            if (mode != "preflight" && mode != "run") throw new ArgumentException("Expected preflight or run");
            if (EditorApplication.isPlayingOrWillChangePlaymode || SceneManager.GetActiveScene().path != "Assets/Lanbai/Tests/GateTest.unity" || SceneManager.GetActiveScene().isDirty)
                throw new InvalidOperationException("Requires saved GateTest in edit mode");
            Lanbai.Test.Runner.Start("gate_clouds_test", null, mode == "preflight", "menu", (code, dir) => {
                var result = new Completion { exit = code, output = dir, finished = DateTimeOffset.Now.ToString("o") };
                Directory.CreateDirectory("LanbaiRemote/results");
                File.WriteAllText("LanbaiRemote/results/formal_tool_" + mode + "_completion.json", JsonUtility.ToJson(result, true));
                Debug.Log("[GateContinuation] Official test " + mode + " completed with exit " + code + ": " + dir);
            });
            return "Official Runner invoked; use this run's result.json and completion record, not this adapter return value.";
        }
    }
}
