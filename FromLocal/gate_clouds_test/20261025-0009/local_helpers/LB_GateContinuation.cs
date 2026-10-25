using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UdonSharp;
using UdonSharpEditor;

namespace Lanbai.Tests
{
    // Local test-only staging: let the installed SDK initialize new program assets
    // on its normal editor update before any builder copies proxy data into them.
    public static class LB_GateContinuation
    {
        static readonly Type[] Types = { typeof(LanbaiGateClouds), typeof(LanbaiGateDriver), typeof(LanbaiGateTestClock) };
        const string Folder = "Assets/Lanbai/UdonPrograms";
        static int batchStage;
        static double batchDeadline, nextBatchTick;
        static long initialC;
        static string batchReport;
        static bool compileOnly, stagingEmpty;

        public static void RunBatchCompile()
        {
            compileOnly = true;
            RunBatchSetup();
        }

        // A bounded editor-only job; no player build, Play or scene-view rendering.
        public static void RunBatchSetup()
        {
            if (!Application.isBatchMode) throw new InvalidOperationException("Batch entry only");
            batchReport = Environment.GetEnvironmentVariable("LANBAI_CONTINUATION_REPORT");
            if (string.IsNullOrEmpty(batchReport) || !Path.GetFullPath(batchReport).StartsWith("E:\\IDMdownload\\VRCC\\Backups\\", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Report must be under the E drive backup workspace");
            initialC = new DriveInfo("C").AvailableFreeSpace;
            CheckSpace();
            // Keep meshes/textures out of memory while Roslyn/Udon initializes.
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            stagingEmpty = true;
            EditorUtility.UnloadUnusedAssetsImmediate();
            GC.Collect();
            batchStage = 0;
            batchDeadline = EditorApplication.timeSinceStartup + 180;
            nextBatchTick = EditorApplication.timeSinceStartup + 1;
            BatchLog("START " + DateTimeOffset.Now.ToString("o") + "; graphics=" + SystemInfo.graphicsDeviceType);
            EditorApplication.update += BatchTick;
        }

        static void CheckSpace()
        {
            long c = new DriveInfo("C").AvailableFreeSpace, e = new DriveInfo("E").AvailableFreeSpace;
            if (c < 128L * 1024 * 1024 || initialC - c > 64L * 1024 * 1024 || e < 8L * 1024 * 1024 * 1024)
                throw new IOException("Space guard: C=" + c + "; E=" + e);
        }

        static void BatchLog(string message)
        {
            Debug.Log("[GateContinuation] " + message);
            File.AppendAllText(batchReport, DateTimeOffset.Now.ToString("o") + " " + message + "\n");
        }

        static void BatchTick()
        {
            if (EditorApplication.timeSinceStartup < nextBatchTick) return;
            nextBatchTick = EditorApplication.timeSinceStartup + 1;
            try
            {
                CheckSpace();
                if (EditorApplication.timeSinceStartup > batchDeadline) throw new TimeoutException("Gate setup exceeded 180 seconds");
                if (EditorApplication.isCompiling || EditorApplication.isUpdating) return;
                Guard();
                switch (batchStage)
                {
                    case 0:
                        BatchLog(PreparePrograms());
                        batchStage = 1;
                        break;
                    case 1:
                        if (Types.Any(t => { var p = UdonSharpEditorUtility.GetUdonSharpProgramAsset(t); return p == null || p.ScriptVersion != UdonSharpProgramVersion.CurrentVersion || p.CompiledVersion != UdonSharpProgramVersion.CurrentVersion; })) return;
                        BatchLog(CheckPrograms());
                        if (compileOnly)
                        {
                            BatchLog("SUCCESS; programs initialized and compiled only; no scene build or rendering");
                            EditorApplication.update -= BatchTick;
                            EditorApplication.Exit(0);
                            return;
                        }
                        EditorUtility.UnloadUnusedAssetsImmediate();
                        GC.Collect();
                        EditorSceneManager.OpenScene(LB_GateTest.SCENE, OpenSceneMode.Single);
                        stagingEmpty = false;
                        batchStage = 2;
                        break;
                    case 2:
                        LanbaiGateCloudsBuilder.BuildMenu();
                        BatchLog("Cloud builder completed");
                        batchStage = 3;
                        break;
                    case 3:
                        BatchLog(LB_GateTest.Apply("155.1"));
                        LanbaiGateDriverBuilder.BuildClockMenu();
                        BatchLog("Gate driver and clock builder completed");
                        batchStage = 4;
                        break;
                    case 4:
                        BatchLog(SaveValidated());
                        CheckSpace();
                        BatchLog("SUCCESS; Play, performance and headset not tested; appearance not yet rendered");
                        EditorApplication.update -= BatchTick;
                        EditorApplication.Exit(0);
                        break;
                }
                CheckSpace();
            }
            catch (Exception error)
            {
                BatchLog("FAILED; stage=" + batchStage + "; " + error);
                EditorApplication.update -= BatchTick;
                // Preserve a failed job's in-memory scene separately, never overwrite GateTest.
                if (SceneManager.GetActiveScene().isDirty)
                    EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), Path.ChangeExtension(batchReport, ".failed.unity"), true);
                EditorApplication.Exit(1);
            }
        }

        static void Guard()
        {
            if (Application.isBatchMode && stagingEmpty && SceneManager.GetActiveScene().path == "" && !EditorApplication.isPlaying) return;
            if (SceneManager.GetActiveScene().path != LB_GateTest.SCENE || EditorApplication.isPlaying)
                throw new InvalidOperationException("Only the GateTest edit-mode scene is allowed.");
        }

        public static string PreparePrograms()
        {
            Guard();
            var report = new List<string>();
            foreach (var type in Types)
            {
                var path = Folder + "/" + type.Name + ".asset";
                var asset = UdonSharpEditorUtility.GetUdonSharpProgramAsset(type);
                if (asset == null)
                {
                    var existing = AssetDatabase.LoadMainAssetAtPath(path);
                    if (existing != null)
                    {
                        asset = existing as UdonSharpProgramAsset;
                        if (asset == null || asset.sourceCsScript == null || asset.sourceCsScript.GetClass() != type)
                            throw new InvalidOperationException("Unrecognized program asset; refusing to overwrite " + path);
                    }
                }
                if (asset != null) { report.Add(type.Name + ": reused " + AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(asset))); continue; }
                MonoScript script = null;
                foreach (var guid in AssetDatabase.FindAssets(type.Name + " t:MonoScript"))
                {
                    var candidate = AssetDatabase.LoadAssetAtPath<MonoScript>(AssetDatabase.GUIDToAssetPath(guid));
                    if (candidate != null && candidate.GetClass() == type) { script = candidate; break; }
                }
                if (script == null) throw new InvalidOperationException("Missing script " + type.Name);
                asset = ScriptableObject.CreateInstance<UdonSharpProgramAsset>();
                asset.sourceCsScript = script;
                AssetDatabase.CreateAsset(asset, path);
                report.Add(type.Name + ": created; await SDK editor update before building");
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            return string.Join("\n", report);
        }

        public static string CheckPrograms()
        {
            Guard();
            var report = new List<string>();
            foreach (var type in Types)
            {
                var asset = UdonSharpEditorUtility.GetUdonSharpProgramAsset(type);
                if (asset == null || asset.ScriptVersion != UdonSharpProgramVersion.CurrentVersion || asset.CompiledVersion != UdonSharpProgramVersion.CurrentVersion)
                    throw new InvalidOperationException("Program not ready: " + type.Name);
                report.Add(type.Name + ": ready; script=" + asset.ScriptVersion + "; compiled=" + asset.CompiledVersion + "; guid=" + AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(asset)));
            }
            AssetDatabase.SaveAssets();
            return string.Join("\n", report);
        }

        public static string CheckScene()
        {
            Guard();
            var roots = SceneManager.GetActiveScene().GetRootGameObjects();
            var all = roots.SelectMany(r => r.GetComponentsInChildren<Transform>(true)).ToArray();
            var clouds = all.Select(t => t.GetComponent<LanbaiGateClouds>()).FirstOrDefault(x => x != null);
            var driver = all.Select(t => t.GetComponent<LanbaiGateDriver>()).FirstOrDefault(x => x != null);
            var clock = all.Select(t => t.GetComponent<LanbaiGateTestClock>()).FirstOrDefault(x => x != null);
            if (clouds == null || driver == null || clock == null) throw new InvalidOperationException("Missing cloud, gate driver or clock");
            if (clouds.cardRenderers.Length != 38 || clouds.cardRenderers.Any(x => x == null) || clouds.towers.Length != 10 || clouds.towers.Any(x => x == null))
                throw new InvalidOperationException("Cloud binding count mismatch");
            if (driver.instTf.Length != 64 || driver.instTf.Any(x => x == null)) throw new InvalidOperationException("Gate binding count mismatch");
            foreach (var b in new UdonSharpBehaviour[] { clouds, driver, clock })
                if (UdonSharpEditorUtility.GetBackingUdonBehaviour(b) == null) throw new InvalidOperationException("Missing backing Udon: " + b.GetType().Name);
            string[] legacy = { "Tear_CloudGlow", "Tear_CloudGlow_Additive", "Tear_LightLane", "Tear_FootSkyline", "Tear_FootSkylineIn", "Shaft_00", "Shaft_01" };
            foreach (var t in all.Where(t => legacy.Contains(t.name)))
            {
                var renderer = t.GetComponent<Renderer>();
                if (renderer != null && renderer.enabled) throw new InvalidOperationException("Legacy renderer unexpectedly enabled: " + t.name);
            }
            var camera = all.Select(t => t.GetComponent<Camera>()).FirstOrDefault(x => x != null);
            if (camera == null || !camera.allowHDR) throw new InvalidOperationException("Missing HDR reference camera");
            return "Scene bindings valid: 64 gate instances, 38 cards, 10 tower layers, all 3 backing Udon behaviours, legacy renderers disabled; HDR reference camera. skyFromSky=" + driver.skyFromSky + "; sceneDirty=" + SceneManager.GetActiveScene().isDirty;
        }

        public static string SaveValidated()
        {
            string result = CheckScene();
            AssetDatabase.SaveAssets();
            if (!EditorSceneManager.SaveScene(SceneManager.GetActiveScene())) throw new InvalidOperationException("Scene save failed");
            return result + "\nSaved GateTest only.";
        }

        public static string ShootRear(string file)
        {
            CheckScene();
            string output = Path.GetFullPath(file);
            if (!output.StartsWith("E:\\IDMdownload\\VRCC\\lanbai-assets-gate-main-20261024\\FromLocal\\gate_clouds_test\\", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Rear output must be in this test's E-drive report directory");
            var all = SceneManager.GetActiveScene().GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true)).ToArray();
            var rear = all.Where(t => t.name.StartsWith("Rear_") && !HasRearAncestor(t)).ToArray();
            if (rear.Length != 8) throw new InvalidOperationException("Expected 8 rear arm roots; got " + rear.Length);
            var clouds = all.Select(t => t.GetComponent<LanbaiGateClouds>()).First(x => x != null);
            var materials = new HashSet<Material>();
            materials.Add(RenderSettings.skybox);
            foreach (var r in clouds.root.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.sharedMaterials)
                    if (m != null && (m.shader.name == "Lanbai/GateCloudDeck" || m.shader.name == "Lanbai/GateCloudCard")) materials.Add(m);
            foreach (var t in rear)
                foreach (var r in t.GetComponentsInChildren<Renderer>(true))
                    foreach (var m in r.sharedMaterials) materials.Add(m);
            foreach (var m in materials)
                if (m == null || !m.HasProperty("_BackBand") || Mathf.Abs(m.GetFloat("_BackBand") - 0.55f) > 0.0001f)
                    throw new InvalidOperationException("Unexpected rear baseline material: " + (m != null ? m.name : "null"));
            try
            {
                foreach (var m in materials) m.SetFloat("_BackBand", 1.25f);
                return LB_GateTest.Shoot("cam=rear;w=1920;h=1080;ss=2;file=" + output.Replace('\\', '/')) + "\nRear override: 8 arms, " + materials.Count + " materials; restored to 0.55 in finally.";
            }
            finally
            {
                foreach (var m in materials) m.SetFloat("_BackBand", 0.55f);
                LB_GateTest.Apply("155.1");
            }
        }

        static bool HasRearAncestor(Transform t)
        {
            for (var p = t.parent; p != null; p = p.parent) if (p.name.StartsWith("Rear_")) return true;
            return false;
        }

        public static string PreparePlayTest()
        {
            Guard();
            CheckScene();
            if (!VRC.SDK3.ClientSim.ClientSimSettings.Instance.enableClientSim)
                throw new InvalidOperationException("ClientSim is disabled; preferences were not changed");
            var descriptors = UnityEngine.Object.FindObjectsOfType<VRC.SDK3.Components.VRCSceneDescriptor>();
            if (descriptors.Length != 0) throw new InvalidOperationException("Scene already has a descriptor; refusing duplicate setup");
            if (GameObject.Find("GateTest_ClientSim") != null) throw new InvalidOperationException("Test setup name already exists");
            var camera = SceneManager.GetActiveScene().GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Camera>(true)).First();
            var go = new GameObject("GateTest_ClientSim");
            var descriptor = go.AddComponent<VRC.SDK3.Components.VRCSceneDescriptor>();
            descriptor.ReferenceCamera = camera.gameObject;
            var spawn = new GameObject("Spawn");
            spawn.transform.SetParent(go.transform);
            float height = VRC.SDK3.ClientSim.ClientSimSettings.Instance.playerStartHeight;
            spawn.transform.position = camera.transform.position - Vector3.up * height;
            spawn.transform.rotation = Quaternion.Euler(0, camera.transform.eulerAngles.y, 0);
            descriptor.spawns = new[] { spawn.transform };
            descriptor.RespawnHeightY = spawn.transform.position.y - 10;
            var floor = new GameObject("Invisible_TestFloor");
            floor.transform.SetParent(go.transform);
            floor.transform.position = spawn.transform.position - Vector3.up * 0.1f;
            floor.AddComponent<BoxCollider>().size = new Vector3(6, 0.2f, 6);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return "Added GateTest-only ClientSim descriptor, one spawn and an invisible 6m test floor. No world ID or upload action. " + SaveValidated();
        }

        public static string FixTestReference()
        {
            Guard();
            var descriptor = GameObject.Find("GateTest_ClientSim").GetComponent<VRC.SDK3.Components.VRCSceneDescriptor>();
            var camera = SceneManager.GetActiveScene().GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Camera>(true)).First();
            descriptor.ReferenceCamera = camera.gameObject;
            EditorUtility.SetDirty(descriptor);
            const string meshPath = "Assets/Lanbai/GateClouds/Generated/GateClouds_Card_Congestus_crop45.asset";
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
            if (mesh != null) { mesh.name = Path.GetFileNameWithoutExtension(meshPath); EditorUtility.SetDirty(mesh); }
            LB_GateTest.Apply("155.1");
            return "Bound the HDR reference camera; normalized generated crop45 mesh name without changing geometry or GUID. " + SaveValidated();
        }

        [Serializable]
        class RuntimeSample
        {
            public float realtime, clockT, cloudT, shaderT, gateZ, tearHide;
            public bool localPlayer, skyFromSky;
            public int enabledArmRenderers;
        }

        static VRC.Udon.UdonBehaviour RuntimeBehaviour(Type type)
        {
            return UnityEngine.Object.FindObjectsOfType<VRC.Udon.UdonBehaviour>(true).Single(b =>
                b.gameObject.scene == SceneManager.GetActiveScene() && b.programSource is UdonSharpProgramAsset p && p.sourceCsScript != null && p.sourceCsScript.GetClass() == type);
        }

        public static string ReadPlayState()
        {
            if (!EditorApplication.isPlaying || SceneManager.GetActiveScene().path != LB_GateTest.SCENE)
                throw new InvalidOperationException("GateTest Play required");
            var clock = RuntimeBehaviour(typeof(LanbaiGateTestClock));
            var cloud = RuntimeBehaviour(typeof(LanbaiGateClouds));
            var gate = RuntimeBehaviour(typeof(LanbaiGateDriver));
            var root = (Transform)gate.GetProgramVariable("gateRoot");
            var renderers = (Renderer[])gate.GetProgramVariable("rend");
            return JsonUtility.ToJson(new RuntimeSample {
                realtime = Time.realtimeSinceStartup,
                clockT = Convert.ToSingle(clock.GetProgramVariable("_t")), cloudT = Convert.ToSingle(cloud.GetProgramVariable("t")),
                shaderT = Shader.GetGlobalFloat("_Udon_GateTime"), gateZ = root.position.z,
                tearHide = Shader.GetGlobalFloat("_Udon_TearHide"), localPlayer = VRC.SDKBase.Networking.LocalPlayer != null,
                skyFromSky = Convert.ToBoolean(gate.GetProgramVariable("skyFromSky")),
                enabledArmRenderers = renderers.Count(r => r != null && r.enabled && r.gameObject.activeInHierarchy)
            }, true);
        }
    }
}
