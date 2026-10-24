// Lanbai / 蓝白 -- 蓝白/Build/Overlay: builds the full-field fade sphere (Lanbai_Overlay v2) in the open scene.
// UNCOMPILED (cloud side; Roslyn type-check against UnityEditor 2021.1 only). Re-runnable: deletes the previous build.
//
// Creates  Lanbai_Overlay  (scene root, at the hero eye; LanbaiOverlay moves it to the local head every frame)
//            MeshFilter = Unity's built-in Sphere (radius 0.5) x scale 3 = r 1.5 m, no collider
//            MeshRenderer: M_Overlay_Lanbai (shader Lanbai/Overlay), shadows off, probes off, DISABLED (the script enables it)
//            LanbaiOverlay (UdonSharp) + its program asset Overlay/Runtime/LanbaiOverlay.asset (U# 1.x compiles only
//            scripts that have one; gate test pitfall 11). Both are made by reflection so this file compiles even where
//            the UdonSharp editor assembly is not referenced; if reflection fails it says so and you add them by hand.
#if UNITY_EDITOR
using System;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Overlay.Editor
{
    public static class LanbaiOverlayBuild
    {
        const string Root = "Assets/Lanbai/Overlay";
        const string MatPath = Root + "/Materials/M_Overlay_Lanbai.mat";
        const string ScriptPath = Root + "/Runtime/LanbaiOverlay.cs";
        const string ProgramPath = Root + "/Runtime/LanbaiOverlay.asset";
        static readonly Vector3 HeroEye = new Vector3(0.55f, 1.70f, 2.05f);   // Gate/GateLayout_v2.json cameras.U7

        [MenuItem("蓝白/Build/Overlay")]
        public static void Build()
        {
            var old = GameObject.Find("Lanbai_Overlay");
            if (old != null) Undo.DestroyObjectImmediate(old);

            var shader = Shader.Find("Lanbai/Overlay");
            if (shader == null) { Debug.LogError("[Lanbai Overlay] shader Lanbai/Overlay not found (did it compile?)"); return; }
            if (!AssetDatabase.IsValidFolder(Root + "/Materials")) AssetDatabase.CreateFolder(Root, "Materials");
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
            if (mat == null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, MatPath); }
            mat.shader = shader;
            mat.SetFloat("_DitherLSB", 1.5f);
            mat.renderQueue = -1;          // the shader's Overlay+100
            EditorUtility.SetDirty(mat);

            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = "Lanbai_Overlay";
            UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
            go.transform.position = HeroEye;
            go.transform.rotation = Quaternion.identity;
            go.transform.localScale = Vector3.one * 3f;
            var mr = go.GetComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
            mr.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off;
            mr.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
            mr.allowOcclusionWhenDynamic = false;
            mr.enabled = false;
            GameObjectUtility.SetStaticEditorFlags(go, 0);
            Undo.RegisterCreatedObjectUndo(go, "Build Lanbai Overlay");

            string note = AddUdonSharp(go, ScriptPath, ProgramPath, "LanbaiOverlay");
            var comp = go.GetComponent("LanbaiOverlay");
            if (comp != null)
            {
                var so = new SerializedObject(comp);
                var p = so.FindProperty("sphere");
                if (p != null) { p.objectReferenceValue = mr; so.ApplyModifiedPropertiesWithoutUndo(); }
            }
            AssetDatabase.SaveAssets();
            Debug.Log("[Lanbai Overlay] built Lanbai_Overlay (r 1.5 m, disabled until a driver shows it). " + note);
        }

        /// <summary>Program asset + component for an UdonSharp script, by reflection (UdonSharp 1.x).</summary>
        public static string AddUdonSharp(GameObject go, string scriptPath, string programPath, string className)
        {
            var script = AssetDatabase.LoadAssetAtPath<MonoScript>(scriptPath);
            if (script == null) return "script not found: " + scriptPath;
            Type progType = FindType("UdonSharp.UdonSharpProgramAsset");
            if (progType == null) return "UdonSharp editor not found: add " + className + " and its program asset by hand.";
            var prog = AssetDatabase.LoadAssetAtPath(programPath, progType);
            if (prog == null)
            {
                prog = ScriptableObject.CreateInstance(progType);
                var f = progType.GetField("sourceCsScript", BindingFlags.Public | BindingFlags.Instance);
                if (f != null) f.SetValue(prog, script);
                AssetDatabase.CreateAsset(prog, programPath);
            }
            Type behType = script.GetClass();
            if (behType == null) return "class " + className + " not compiled yet: run again after the scripts compile.";
            Type undo = FindType("UdonSharpEditor.UdonSharpUndo");
            MethodInfo add = undo == null ? null : undo.GetMethods(BindingFlags.Public | BindingFlags.Static)
                .FirstOrDefault(m => m.Name == "AddComponent" && !m.IsGenericMethod && m.GetParameters().Length == 2);
            if (add != null)
            {
                add.Invoke(null, new object[] { go, behType });
                return "UdonSharp component added.";
            }
            Undo.AddComponent(go, behType);
            return "added " + className + " with Undo.AddComponent: open it once in the Inspector so UdonSharp makes its UdonBehaviour.";
        }

        public static Type FindType(string fullName)
        {
            foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = a.GetType(fullName, false);
                if (t != null) return t;
            }
            return null;
        }
    }
}
#endif
