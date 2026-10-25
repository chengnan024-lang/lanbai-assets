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

        // D-41：菜单先建三个 U# 程序资产（脚本旁边）、等 SDK 初始化完，再搭（Common/Editor/LanbaiUdonPrograms）
        [MenuItem("蓝白/Build/04c 门内")]
        public static void BuildMenu()
        {
            var types = new[] { "LanbaiInsideDriver", "LanbaiInsideTestClock", "LanbaiSkylightSpot" }
                .Select(Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript).Where(t => t != null).ToArray();
            if (types.Length < 3) { Debug.LogError("[Lanbai 4c] Act04c_Inside/Runtime/ 的脚本没编译完（要 LanbaiInsideDriver、LanbaiInsideTestClock、LanbaiSkylightSpot）"); return; }
            Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("蓝白/Build/04c 门内", types, Build, Lanbai.Udon.LanbaiUdonPrograms.NextToScript);
        }

        public static void Build()
        {
            foreach (var sn in new[] { "LanbaiInsideDriver", "LanbaiInsideTestClock", "LanbaiSkylightSpot" })
            {
                var st = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript(sn);
                if (st != null) Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Build/04c 门内", st);
            }
            var old = GameObject.Find("Lanbai_Inside");
            // 总导演终审 #11: a rebuild keeps what was wired / tuned by hand on the old driver (the references and the
            // dial time); the Director's wiring is re-run by hand afterwards (logged below)
            UnityEngine.Object keepOverlay = null, keepExposure = null, keepLight = null;
            float keepDial = float.NaN;
            bool keepRS = false, keepML = false, hadOld = old != null;
            if (old != null)
            {
                var oc = old.GetComponentInChildren(FindDriverType(), true);
                if (oc != null)
                {
                    var os = new SerializedObject(oc);
                    keepOverlay = os.FindProperty("overlay")?.objectReferenceValue;
                    keepExposure = os.FindProperty("exposure")?.objectReferenceValue;
                    keepLight = os.FindProperty("worldMainLight")?.objectReferenceValue;
                    var pd = os.FindProperty("tLichtDial"); if (pd != null) keepDial = pd.floatValue;
                    var p1 = os.FindProperty("writeRenderSettings"); if (p1 != null) keepRS = p1.boolValue;
                    var p2 = os.FindProperty("writeMainLight"); if (p2 != null) keepML = p2.boolValue;
                }
                Undo.DestroyObjectImmediate(old);
            }
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
                var pb = so.FindProperty("busAnchoredObject"); if (pb != null) pb.objectReferenceValue = busAnch;
                // D-24: the one shadowed main light is the gate test scene's Gate_Lights/Moon
                var pl = so.FindProperty("worldMainLight");
                if (pl != null && pl.objectReferenceValue == null && keepLight == null)
                {
                    var moon = GameObject.Find("Gate_Lights/Moon");
                    if (moon != null) pl.objectReferenceValue = moon.GetComponent<Light>();
                }
                if (hadOld)
                {
                    void R(string name, UnityEngine.Object v) { var q = so.FindProperty(name); if (q != null && v != null) q.objectReferenceValue = v; }
                    R("overlay", keepOverlay); R("exposure", keepExposure); R("worldMainLight", keepLight);
                    var pd = so.FindProperty("tLichtDial"); if (pd != null && !float.IsNaN(keepDial)) pd.floatValue = keepDial;
                    var p1 = so.FindProperty("writeRenderSettings"); if (p1 != null) p1.boolValue = keepRS;
                    var p2 = so.FindProperty("writeMainLight"); if (p2 != null) p2.boolValue = keepML;
                }
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            insideRoot.SetActive(false);
            busAnch.SetActive(false);                      // 总导演终审 #1: the dome / dot / loose threads start off
            string sky = BuildSkylight(top.transform);
            sky += " " + BuildTestClock(top.transform, comp);
            AssetDatabase.SaveAssets();
            Debug.Log("[Lanbai 4c] built Lanbai_Inside: " + n + " renderers. " + note + " " + sky +
                      (hadOld ? " Kept from the old build: overlay / exposure / worldMainLight / tLichtDial / write flags."
                              : " Wire the driver's overlay (Lanbai_Overlay), exposure (Lanbai_Grades) and worldMainLight by hand.") +
                      " Then re-run 蓝白/Director/2 Wire Scene (the driver and the skylight are new objects).");
        }

        /// <summary>The act 4 -> 5 test clock for the gate test scene (switched OFF; README §0): it stands in for the Director
        /// from 166 to 252.64 and activates / ticks / deactivates the gate, its clouds, the skylight spot and the inside driver
        /// by their own windows. Use it instead of Gate_TestClock.</summary>
        static string BuildTestClock(Transform top, Component insideDriver)
        {
            var go = new GameObject("Inside_TestClock (test scene only)");
            go.transform.SetParent(top, false);
            string note = Lanbai.Overlay.Editor.LanbaiOverlayBuild.AddUdonSharp(go, Root + "/Runtime/LanbaiInsideTestClock.cs",
                Root + "/Runtime/LanbaiInsideTestClock.asset", "LanbaiInsideTestClock");
            var c = go.GetComponent("LanbaiInsideTestClock");
            if (c != null)
            {
                var so = new SerializedObject(c);
                void Ref(string field, string typeName)
                {
                    var p = so.FindProperty(field); if (p == null) return;
                    foreach (var a in System.AppDomain.CurrentDomain.GetAssemblies())
                    {
                        var t = a.GetType(typeName);
                        if (t == null) continue;
                        var o = UnityEngine.Object.FindObjectOfType(t, true);
                        if (o != null) { p.objectReferenceValue = o; return; }
                    }
                }
                Ref("gate", "LanbaiGateDriver");
                Ref("clouds", "LanbaiGateClouds");
                Ref("skylight", "LanbaiSkylightSpot");
                var pi = so.FindProperty("inside"); if (pi != null && insideDriver != null) pi.objectReferenceValue = insideDriver;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            go.SetActive(false);
            return "Test clock (off): " + note;
        }

        static System.Type FindDriverType()
        {
            foreach (var a in System.AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = a.GetType("LanbaiInsideDriver");
                if (t != null) return t;
            }
            return typeof(MonoBehaviour);
        }

        /// <summary>总导演终审 #8: the skylight spot (act 4, U8 -> U9) built like the rest: FBX under the bus (bus space =
        /// world), three materials (Lanbai/SkylightSpot, Part Spot / Beam / Dust), the LanbaiSkylightSpot U# with its
        /// renderers; the renderers start off (the U# switches them). Bounds: set at import (LanbaiInsideImport).</summary>
        static string BuildSkylight(Transform top)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/FBX/Skylight_Spot.fbx");
            var sh = Shader.Find("Lanbai/SkylightSpot");
            if (asset == null || sh == null) return "(skylight spot NOT built: FBX or shader missing)";
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
            go.name = "Skylight_Spot";
            go.transform.SetParent(top, false);
            var rs = new List<Renderer>();
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                string part = r.name.Contains("Beam") ? "BEAM" : r.name.Contains("Dust") ? "DUST" : "SPOT";
                string path = MatDir + "/M_04c_Skylight_" + part + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
                m.shader = sh;
                foreach (var kw in new[] { "SPOT", "BEAM", "DUST" }) m.DisableKeyword("_PART_" + kw);
                m.EnableKeyword("_PART_" + part);
                m.SetFloat("_Part", Array.IndexOf(new[] { "SPOT", "BEAM", "DUST" }, part));
                EditorUtility.SetDirty(m);
                r.sharedMaterial = m;
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = false;
                r.lightProbeUsage = LightProbeUsage.Off;
                r.reflectionProbeUsage = ReflectionProbeUsage.Off;
                r.enabled = false;
                rs.Add(r);
            }
            var u = new GameObject("LanbaiSkylightSpot");
            u.transform.SetParent(top, false);
            string note = Lanbai.Overlay.Editor.LanbaiOverlayBuild.AddUdonSharp(u, Root + "/Runtime/LanbaiSkylightSpot.cs",
                Root + "/Runtime/LanbaiSkylightSpot.asset", "LanbaiSkylightSpot");
            var c = u.GetComponent("LanbaiSkylightSpot");
            if (c != null)
            {
                var so = new SerializedObject(c);
                var p = so.FindProperty("renderers");
                if (p != null)
                {
                    p.arraySize = rs.Count;
                    for (int i = 0; i < rs.Count; i++) p.GetArrayElementAtIndex(i).objectReferenceValue = rs[i];
                }
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            return "Skylight spot: " + rs.Count + " renderers. " + note;
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

        const float SheetFogCap = 0.25f;               // r09 (art review r08 B2-3)
        const float SleeveInnerClothK = 1.35f;         // r09 (art review r08 B3): the sleeve's inner cut faces

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
            float ck = (objName.StartsWith("Lip8_Ply1") || objName.StartsWith("Lip8_Ply2") || objName.StartsWith("Lip8_Ply3")) ? SleeveInnerClothK : 1f;
            m.SetVector("_ClothColor", new Vector4(cloth.r * ck, cloth.g * ck, cloth.b * ck, 0f));
            m.SetVector("_FibreColor", new Vector4(fib.r, fib.g, fib.b, 0f));
            m.SetFloat("_Gain", 1f);
            m.SetFloat("_FogCap", part == "SHEET" ? SheetFogCap : 1f);     // r06: the cloth stays 12-20 luma darker than the air beyond it
            float H = InsideLayoutData.LipH[ki];
            m.SetFloat("_LipGlow", 3.15f);                                 // r06 / r07 (art reviews r05 #1, r06 S2): fibres to luma 200
            m.SetFloat("_WeaveAmount", 0.02f);                             // r06-r11: the streaks read as rain on glass
            m.SetVector("_Folds", new Vector4(0.08f * H, 0.5f * H, 0f, 0.35f * H));   // r15: the old texture fold off (its u-sampling drew staircase seams); x = 0.08 H still sets the pleat scale
            m.SetFloat("_ThreadCore", objName == "Lip8_Wall" ? 1f : 0f);
            m.SetVector("_DotHalo", new Vector4(dotHaloR, dotHaloR * 0.86f, dotHaloR * 0.70f, 0f));
            m.SetFloat("_FogHeightFalloff", 0f);
            float roll = InsideLayoutData.LipRoll[ki];
            if (objName.StartsWith("Lip8_Ply") && objName.Length > 8 && char.IsDigit(objName[8]))
                roll = InsideLayoutData.PlyRoll[objName[8] - '0'];
            m.SetFloat("_GrainRoll", roll);
            m.SetFloat("_LipGlowWidth", InsideLayoutData.LipGlowWidth[ki]);
            m.SetVector("_LipGlowFar", new Vector4(0.07f, InsideLayoutData.BandWidth[ki], 0f, 0f));   // r12: -30 % (art review r11 S6)
            var weave = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Textures/Inside_Weave_1024.png");
            var fringe = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Textures/Inside_Fringe_2048x256.png");
            if (weave != null) m.SetTexture("_WeaveTex", weave);
            if (fringe != null) m.SetTexture("_FringeTex", fringe);
            m.SetFloat("_FringeGain", objName.EndsWith("_Hang") ? 4.4f : 2.75f);   // r13: the hanging threads x 1.6
            m.SetFloat("_Sway", objName.EndsWith("_Hang") ? 0.6f : 0f);   // r13: the hanging threads sway (D-19)
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
            void Col1(string name, Color v) { var p = so.FindProperty(name); if (p != null) p.colorValue = v; }
            Col1("dialBase", InsideLayoutData.DialBase); Col1("dialBright", InsideLayoutData.DialBright);   // same source as inside_drive.dial
            Cols("zoneFill", InsideLayoutData.ZoneFill); Cols("fibreFill", InsideLayoutData.FibreFill); Cols("bandColour", InsideLayoutData.BandColour);
            var root = so.FindProperty("insideRoot"); if (root != null) root.objectReferenceValue = insideRoot.transform;
            var rootGo = so.FindProperty("insideRootObject"); if (rootGo != null) rootGo.objectReferenceValue = insideRoot;
            var d = so.FindProperty("dotTransform"); if (d != null && dot != null) d.objectReferenceValue = dot;
            so.ApplyModifiedPropertiesWithoutUndo();
        }
    }
}
#endif
