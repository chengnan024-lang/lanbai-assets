// Lanbai / 蓝白 -- 蓝白/Build/04c 门内: builds act 4c (inside the tear) + act 5's wiring in the open scene.
// UNCOMPILED (cloud side; Roslyn type-check against UnityEditor 2021.1 only). Re-runnable: deletes the previous build.
//
// Lanbai_Inside                      (scene root, world origin, never moves: the bus is at the origin)
//   InsideRoot                       R_Inside: the driver moves it to (0, 0, -s(t)); INACTIVE until the driver's window
//     Inside_Lips (FBX instance)     Lip1..7 Sheet / Fringe / Threads, Lip8_Ply0..4 Sheet (+ Fringe), Lip8_Wall
//   Inside_BusAnchored               things that travel with the bus: the dome (r 2.4 km), the loose threads, the Lichtchen
//   LanbaiInsideDriver               UdonSharp; fields filled from InsideLayoutData (generated from InsideLayout.json)
// Materials: Assets/Lanbai/Act04c_Inside/Materials/M_04c_*.mat (shader Lanbai/InsideLip, one per part per lip).
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Lanbai.Inside.Editor
{
    public static class LanbaiInsideBuild
    {
        const string Root = "Assets/Lanbai/Act04c_Inside";
        const string MatDir = Root + "/Materials";

        [MenuItem("蓝白/Build/04c 门内")]
        public static void Build()
        {
            var old = GameObject.Find("Lanbai_Inside");
            if (old != null) Undo.DestroyObjectImmediate(old);
            var shader = Shader.Find("Lanbai/InsideLip");
            if (shader == null) { Debug.LogError("[Lanbai 4c] shader Lanbai/InsideLip not found (did it compile? it needs Common/Shaders/LanbaiFog.cginc)"); return; }
            if (!AssetDatabase.IsValidFolder(MatDir)) AssetDatabase.CreateFolder(Root, "Materials");

            var top = new GameObject("Lanbai_Inside");
            Undo.RegisterCreatedObjectUndo(top, "Build 04c");
            var insideRoot = new GameObject("InsideRoot");
            insideRoot.transform.SetParent(top.transform, false);
            var busAnch = new GameObject("Inside_BusAnchored");
            busAnch.transform.SetParent(top.transform, false);

            var lipsAsset = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/FBX/Inside_Lips.fbx");
            var extrasAsset = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/FBX/Inside_Extras.fbx");
            if (lipsAsset == null || extrasAsset == null) { Debug.LogError("[Lanbai 4c] FBX not found under " + Root + "/FBX"); return; }
            var lips = (GameObject)PrefabUtility.InstantiatePrefab(lipsAsset);
            lips.name = "Inside_Lips";
            lips.transform.SetParent(insideRoot.transform, false);
            var extras = (GameObject)PrefabUtility.InstantiatePrefab(extrasAsset);
            extras.name = "Inside_Extras";
            extras.transform.SetParent(busAnch.transform, false);

            int n = 0;
            var lipMats = new List<Material>();
            var lipMatLip = new List<float>();
            foreach (var r in lips.GetComponentsInChildren<MeshRenderer>(true))
            {
                var m = MaterialFor(r.name, shader);
                Setup(r, m); n++;
                // r06: the driver's "<= 3 lips visible" rule writes _Gain (= visibility) on every lip material
                lipMats.Add(m); lipMatLip.Add(LipIndex(r.name));
            }
            foreach (var r in extras.GetComponentsInChildren<MeshRenderer>(true)) { Setup(r, MaterialFor(r.name, shader)); n++; }

            // the Lichtchen: 2.3 km from the hero eye along the bus-fixed direction
            var dot = extras.transform.Find("Inside_Dot");
            if (dot != null)
            {
                float az = InsideLayoutData.DotAz * Mathf.Deg2Rad, el = InsideLayoutData.DotEl * Mathf.Deg2Rad;
                var dir = new Vector3(Mathf.Sin(az) * Mathf.Cos(el), Mathf.Sin(el), Mathf.Cos(az) * Mathf.Cos(el));
                dot.position = InsideLayoutData.HeroEye + dir * InsideLayoutData.DotDist;
                dot.rotation = Quaternion.identity;
                dot.gameObject.SetActive(false);
            }

            // the driver
            var drvGo = new GameObject("LanbaiInsideDriver");
            drvGo.transform.SetParent(top.transform, false);
            string note = Lanbai.Overlay.Editor.LanbaiOverlayBuild.AddUdonSharp(drvGo, Root + "/Runtime/LanbaiInsideDriver.cs",
                Root + "/Runtime/LanbaiInsideDriver.asset", "LanbaiInsideDriver");
            var comp = drvGo.GetComponent("LanbaiInsideDriver");
            if (comp != null)
            {
                var so = new SerializedObject(comp);
                var pm = so.FindProperty("lipMats");
                if (pm != null)
                {
                    pm.arraySize = lipMats.Count;
                    for (int i = 0; i < lipMats.Count; i++) pm.GetArrayElementAtIndex(i).objectReferenceValue = lipMats[i];
                }
                Fill(so, insideRoot, dot, lipMatLip.ToArray());
            }
            insideRoot.SetActive(false);
            AssetDatabase.SaveAssets();
            Debug.Log("[Lanbai 4c] built Lanbai_Inside: " + n + " renderers. " + note +
                      " Wire the driver's overlay (Lanbai_Overlay), exposure (Lanbai_Grades) and worldMainLight by hand, then add it to the Director.");
        }

        static void Setup(MeshRenderer r, Material m)
        {
            r.sharedMaterial = m;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.lightProbeUsage = LightProbeUsage.Off;
            r.reflectionProbeUsage = ReflectionProbeUsage.Off;
            r.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
            r.allowOcclusionWhenDynamic = false;
            GameObjectUtility.SetStaticEditorFlags(r.gameObject, 0);   // moving roots: no static batching / occlusion
        }

        static int LipIndex(string name)
        {
            // Lip1_Sheet .. Lip7_Threads, Lip8_Ply3_Sheet, Lip8_Wall
            if (name.StartsWith("Lip") && name.Length > 3 && char.IsDigit(name[3])) return name[3] - '0';
            return 0;
        }

        const float SheetFogCap = 0.30f;

        static Material MaterialFor(string objName, Shader shader)
        {
            string path = MatDir + "/M_04c_" + objName + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(shader); AssetDatabase.CreateAsset(m, path); }
            m.shader = shader;
            int k = LipIndex(objName);
            int ki = Mathf.Clamp(k, 1, 8) - 1;
            string part = objName.EndsWith("_Sheet") ? "SHEET" : (objName.EndsWith("_Fringe") || objName.EndsWith("_Hang")) ? "FRINGE" :
                (objName.EndsWith("_Threads") || objName == "Lip8_Wall") ? "THREAD" :
                objName == "Inside_Dome" ? "DOME" : objName == "Inside_Dot" ? "DOT" : objName == "Inside_Loose" ? "LOOSE" : "SHEET";
            foreach (var kw in new[] { "SHEET", "FRINGE", "THREAD", "DOME", "DOT", "LOOSE" }) m.DisableKeyword("_PART_" + kw);
            m.EnableKeyword("_PART_" + part);
            m.SetFloat("_Part", Array.IndexOf(new[] { "SHEET", "FRINGE", "THREAD", "DOME", "DOT", "LOOSE" }, part));
            Color fib = InsideLayoutData.FibreFill[ki];
            float dotHaloR = InsideLayoutData.DotFill.r;
            Color cloth = InsideLayoutData.ClothFill;
            m.SetVector("_ClothColor", new Vector4(cloth.r, cloth.g, cloth.b, 0f));
            m.SetVector("_FibreColor", new Vector4(fib.r, fib.g, fib.b, 0f));
            m.SetFloat("_Gain", 1f);
            m.SetFloat("_FogCap", part == "SHEET" ? SheetFogCap : 1f);     // r06: the cloth stays 12-20 luma darker than the air beyond it
            float H = InsideLayoutData.LipH[ki];
            m.SetFloat("_LipGlow", 3.15f);                                 // r06 / r07 (art reviews r05 #1, r06 S2): fibres to luma 200
            m.SetFloat("_WeaveAmount", 0.06f);                             // r06 / r07: the streaks read as rain on glass
            m.SetVector("_Folds", new Vector4(0.08f * H, 0.5f * H, 0.25f, 0.35f * H));   // r07: visible at 100-400 m
            m.SetFloat("_ThreadCore", objName == "Lip8_Wall" ? 1f : 0f);
            m.SetVector("_DotHalo", new Vector4(dotHaloR, dotHaloR * 0.86f, dotHaloR * 0.70f, 0f));
            m.SetFloat("_FogHeightFalloff", 0f);
            float roll = InsideLayoutData.LipRoll[ki];
            if (objName.StartsWith("Lip8_Ply") && objName.Length > 8 && char.IsDigit(objName[8]))
                roll = InsideLayoutData.PlyRoll[objName[8] - '0'];
            m.SetFloat("_GrainRoll", roll);
            m.SetFloat("_LipGlowWidth", InsideLayoutData.LipGlowWidth[ki]);
            m.SetVector("_LipGlowFar", new Vector4(0.10f, InsideLayoutData.BandWidth[ki], 0f, 0f));
            var weave = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Textures/Inside_Weave_1024.png");
            var fringe = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Textures/Inside_Fringe_2048x256.png");
            if (weave != null) m.SetTexture("_WeaveTex", weave);
            if (fringe != null) m.SetTexture("_FringeTex", fringe);
            m.SetFloat("_FringeGain", 2.75f);
            Color dot = InsideLayoutData.DotFill;
            m.SetVector("_DotCore", new Vector4(dot.r, dot.g, dot.b, 0f));
            m.SetFloat("_DotGlow", 0.32f);
            m.SetFloat("_DotDist", InsideLayoutData.DotDist);
            switch (part)
            {
                case "SHEET": Blend(m, BlendMode.One, BlendMode.Zero, 1, (int)RenderQueue.Geometry, CullMode.Off, "Opaque"); break;
                case "DOME": Blend(m, BlendMode.One, BlendMode.Zero, 1, (int)RenderQueue.AlphaTest + 1, CullMode.Off, "Opaque"); break;
                case "THREAD": Blend(m, BlendMode.One, BlendMode.OneMinusSrcAlpha, 0, 2990, CullMode.Off, "Transparent"); break;
                case "FRINGE": Blend(m, BlendMode.One, BlendMode.One, 0, 2995, CullMode.Off, "Transparent"); break;
                case "DOT": Blend(m, BlendMode.One, BlendMode.One, 0, 3000, CullMode.Off, "Transparent"); break;
                default: Blend(m, BlendMode.One, BlendMode.One, 0, 3005, CullMode.Off, "Transparent"); break;
            }
            EditorUtility.SetDirty(m);
            return m;
        }

        static void Blend(Material m, BlendMode src, BlendMode dst, int zwrite, int queue, CullMode cull, string type)
        {
            m.SetFloat("_SrcBlend", (float)src);
            m.SetFloat("_DstBlend", (float)dst);
            m.SetFloat("_ZWrite", zwrite);
            m.SetFloat("_Cull", (float)cull);
            m.renderQueue = queue;
            m.SetOverrideTag("RenderType", type);
        }

        static void Fill(SerializedObject so, GameObject insideRoot, Transform dot, float[] lipMatLip)
        {
            void F(string name, float v) { var p = so.FindProperty(name); if (p != null) p.floatValue = v; }
            void Arr(string name, float[] v)
            {
                var p = so.FindProperty(name); if (p == null) return;
                p.arraySize = v.Length; for (int i = 0; i < v.Length; i++) p.GetArrayElementAtIndex(i).floatValue = v[i];
            }
            void Cols(string name, Color[] v)
            {
                var p = so.FindProperty(name); if (p == null) return;
                p.arraySize = v.Length; for (int i = 0; i < v.Length; i++) p.GetArrayElementAtIndex(i).colorValue = v[i];
            }
            F("tU6", InsideLayoutData.U6); F("tU9", InsideLayoutData.U9); F("tVoiceEnd", InsideLayoutData.VoiceEnd);
            F("tU12", InsideLayoutData.U12); F("tLichtDial", InsideLayoutData.LichtDial); F("tSleeveExit", InsideLayoutData.SleeveExit);
            Arr("lipT", InsideLayoutData.LipT); Arr("lipS", InsideLayoutData.LipS);
            Arr("lipMatLip", lipMatLip);
            Arr("bandStart", InsideLayoutData.BandStart); Arr("bandSweep", InsideLayoutData.BandSweep);
            Cols("zoneFill", InsideLayoutData.ZoneFill); Cols("fibreFill", InsideLayoutData.FibreFill); Cols("bandColour", InsideLayoutData.BandColour);
            var root = so.FindProperty("insideRoot"); if (root != null) root.objectReferenceValue = insideRoot.transform;
            var rootGo = so.FindProperty("insideRootObject"); if (rootGo != null) rootGo.objectReferenceValue = insideRoot;
            var d = so.FindProperty("dotTransform"); if (d != null && dot != null) d.objectReferenceValue = dot;
            so.ApplyModifiedPropertiesWithoutUndo();
        }
    }
}
#endif
