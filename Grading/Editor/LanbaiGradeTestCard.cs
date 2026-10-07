// Lanbai / 蓝白 -- grade test card + calibration cards + LDR neutral-LUT verification (ART BIBLE v2.1, 1.5 / 1.7 / 9.3).
// Menu: 蓝白/Grades/Test Card   (build or refresh; idempotent)
//       蓝白/Grades/Measure Test Card (all 15 profiles)  -> LanbaiReports/TestCard_Report.md + PNGs
//       蓝白/Grades/Verify Neutral LUT (LDR, contribution 0 vs 1) -> LanbaiReports/NeutralLUT_Report.md
//       蓝白/Grades/Probe Bloom Colour (single or double sRGB decode) -> LanbaiReports/BloomColour_Report.md
//
// UNCOMPILED IN UNITY (Roslyn type-check against Unity 2021.1 reference DLLs + the PPv2 API stub and the real
// PPv2 3.0.2 runtime source).
//
// Measurement passes (verify.md m3): the patch pass renders ONLY the LanbaiDebug layer, so seat backs or pillars on
// other layers can never cover a patch; the grey / white cards are read in a separate close-up pass whose culling
// mask adds the cards' own layer (e.g. Bus, when they were moved there to catch the world main light).
//
// The rig "Lanbai_TestCard" (tag EditorOnly: it is stripped from every build, players never see it):
//   Patches/k-6 .. k+4   11 unlit quads, emission = 0.18 * 2^k scene-linear (shader Lanbai/Debug/TestPatch,
//                        a FLOAT, not a colour: no sRGB conversion, no fog, HDR values above 1 kept)
//   ColourPatches/c1..c8 second row: 8 saturated scene-linear colours (LanbaiGradeData.ColourPatchLinear, set with
//                        SetVector): checks that Unity grades saturated colours the way the art side's model says
//   Backing              unlit 0.0 board behind both rows (shows the grade's black lift; sampled as input 0)
//   CalibCards/Grey      0.5 m, Standard, albedo #767676 (0.18 linear), smoothness 0
//   CalibCards/White     0.5 m, Standard, albedo #E6E6E6 (~0.80), smoothness 0
//   CalibSpheres/*       lookdev calibration balls: 18% grey, 80% white, chrome, sRGB-30 black (bible 1.5 step 5)
//   DebugVolumes/PPV_DEBUG_Measure       priority 1001: bloom, vignette, grain intensity 0 (measurement mode)
//   DebugVolumes/PPV_VERIFY_LDR          priority 1000: LDR mode + Lanbai_Neutral_1024x32 (bible 1.7 check)
// Visual children live on the layer "LanbaiDebug" (created in a free user slot if missing); the two debug
// volumes on "PostProcessing". Both debug volumes start at weight 0.

#pragma warning disable 0618 // PPv2 3.5+ marks its types [Obsolete] (a warning only)
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;
using UnityEngine.Rendering.PostProcessing;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace Lanbai.Grading
{
    public static class LanbaiGradeTestCard
    {
        public const string RigName = "Lanbai_TestCard";
        public const string DebugLayerName = "LanbaiDebug";
        public const string PatchShaderName = "Lanbai/Debug/TestPatch";
        public const string NeutralLutName = "Lanbai_Neutral_1024x32";
        public const string MeasureId = "DEBUG_Measure";
        public const string VerifyId = "VERIFY_LDR";
        const string UndoName = "蓝白 Test Card";

        public const float PatchSize = 0.10f;       // m
        public const float PatchPitch = 0.115f;     // m
        public const int KMin = -6, KMax = 4;       // 11 patches
        public const float MeasureDistance = 1.5f;  // m, measurement camera to the patch row
        public const float ColourRowY = -0.135f;    // m, centre of the colour row below the grey row
        const int CapW = 1280, CapH = 720;

        [MenuItem(LanbaiGradeBuilder.Menu + "Test Card", false, 20)]
        static void MenuBuild() { Debug.Log("[蓝白 Grades] " + Build()); }

        [MenuItem(LanbaiGradeBuilder.Menu + "Test Card: Show or Hide", false, 21)]
        static void MenuToggle() { Debug.Log("[蓝白 Grades] " + ToggleVisible()); }

        [MenuItem(LanbaiGradeBuilder.Menu + "Measure Test Card (all 15 profiles)", false, 22)]
        static void MenuMeasure() { Debug.Log("[蓝白 Grades] " + MeasureAll()); }

        [MenuItem(LanbaiGradeBuilder.Menu + "Verify Neutral LUT (LDR, contribution 0 vs 1)", false, 23)]
        static void MenuVerify() { Debug.Log("[蓝白 Grades] " + VerifyNeutralLut()); }

        [MenuItem(LanbaiGradeBuilder.Menu + "Fix LUT Strip Import Settings", false, 24)]
        static void MenuFixLuts() { Debug.Log("[蓝白 Grades] " + FixAllLutImportSettings()); }

        [MenuItem(LanbaiGradeBuilder.Menu + "Probe Bloom Colour (single or double sRGB decode)", false, 25)]
        static void MenuProbeBloom() { Debug.Log("[蓝白 Grades] " + ProbeBloomColour()); }

        public static float PatchEmission(int k) { return 0.18f * Mathf.Pow(2f, k); }

        // =========================================================================================
        // Build
        // =========================================================================================
        public static string Build()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) return "ERROR: leave Play mode first.";
            var log = new StringBuilder();
            int dbgLayer = LanbaiGradeUtil.EnsureLayer(DebugLayerName, log);
            int ppLayer = LanbaiGradeUtil.EnsureLayer(LanbaiGradeBuilder.VolumeLayerName, log);
            if (dbgLayer < 0 || ppLayer < 0) return "ERROR: no free user layer for " + DebugLayerName + " / " + LanbaiGradeBuilder.VolumeLayerName;

            Shader patchShader = Shader.Find(PatchShaderName);
            if (patchShader == null) return "ERROR: shader '" + PatchShaderName + "' not found (Shaders/Lanbai_TestPatch.shader missing or failed to compile).";
            Shader standard = Shader.Find("Standard");

            Undo.IncrementCurrentGroup();
            Undo.SetCurrentGroupName(UndoName);
            int undoGroup = Undo.GetCurrentGroup();

            string kit = LanbaiGradeUtil.KitFolder();
            string matDir = kit + "/TestCard/Materials";
            LanbaiGradeUtil.EnsureFolder(matDir);

            // ---- materials
            var patchMats = new Material[KMax - KMin + 1];
            for (int k = KMin; k <= KMax; k++)
            {
                var m = GetOrCreateMaterial(matDir + "/TC_Patch_k" + (k >= 0 ? "+" : "") + k + ".mat", patchShader);
                m.SetFloat("_Emission", PatchEmission(k));
                EditorUtility.SetDirty(m);
                patchMats[k - KMin] = m;
            }
            var backing = GetOrCreateMaterial(matDir + "/TC_Backing.mat", patchShader);
            backing.SetFloat("_Emission", 0f);
            EditorUtility.SetDirty(backing);
            int nCol = LanbaiGradeData.ColourPatchNames.Length;
            var colourMats = new Material[nCol];
            for (int i = 0; i < nCol; i++)
            {
                var m = GetOrCreateMaterial(matDir + "/TC_Colour_c" + (i + 1) + ".mat", patchShader);
                m.SetFloat("_Emission", 1f);
                m.SetVector("_Tint", new Vector4(LanbaiGradeData.ColourPatchLinear[3 * i], LanbaiGradeData.ColourPatchLinear[3 * i + 1],
                                                 LanbaiGradeData.ColourPatchLinear[3 * i + 2], 1f));   // SetVector: never colour-converted
                EditorUtility.SetDirty(m);
                colourMats[i] = m;
            }
            for (int i = 0; i < patchMats.Length; i++) { patchMats[i].SetVector("_Tint", Vector4.one); EditorUtility.SetDirty(patchMats[i]); }
            backing.SetVector("_Tint", Vector4.one);
            var grey = StandardMat(matDir + "/TC_GreyCard_18.mat", standard, "#767676", 0f, 0f, true);
            var white = StandardMat(matDir + "/TC_WhiteCard_80.mat", standard, "#E6E6E6", 0f, 0f, true);
            var sGrey = StandardMat(matDir + "/TC_Sphere_Grey18.mat", standard, "#767676", 0.2f, 0f, false);
            var sWhite = StandardMat(matDir + "/TC_Sphere_White80.mat", standard, "#E7E7E7", 0.2f, 0f, false);
            var sChrome = StandardMat(matDir + "/TC_Sphere_Chrome.mat", standard, "#CFD1D3", 1f, 1f, false);
            var sBlack = StandardMat(matDir + "/TC_Sphere_Black30.mat", standard, "#1E1E1E", 0.2f, 0f, false);

            // ---- rig
            Scene scene = SceneManager.GetActiveScene();
            GameObject rig = LanbaiGradeUtil.FindRoot(scene, RigName);
            if (rig == null)
            {
                rig = LanbaiGradeUtil.FindOrCreateRoot(scene, RigName, UndoName);
                PlaceInFrontOfSceneView(rig.transform);
                log.AppendLine("- new rig placed 1.6 m in front of the Scene view camera: move it (keep the patches facing the seat)");
            }
            else Undo.RecordObject(rig, UndoName);
            rig.tag = "EditorOnly";
            rig.layer = dbgLayer;

            Transform patches = LanbaiGradeUtil.FindOrCreateChild(rig.transform, "Patches", UndoName);
            patches.gameObject.layer = dbgLayer;
            patches.gameObject.tag = "EditorOnly";
            for (int k = KMin; k <= KMax; k++)
            {
                int i = k - KMin;
                string n = "k" + (k >= 0 ? "+" : "") + k;
                var q = Primitive(patches, n, PrimitiveType.Quad, dbgLayer, patchMats[i], false);
                q.localPosition = new Vector3((i - 5) * PatchPitch, 0f, 0f);
                q.localRotation = Quaternion.identity;
                q.localScale = new Vector3(PatchSize, PatchSize, 1f);
            }
            Transform colours = LanbaiGradeUtil.FindOrCreateChild(rig.transform, "ColourPatches", UndoName);
            colours.gameObject.layer = dbgLayer;
            colours.gameObject.tag = "EditorOnly";
            for (int i = 0; i < nCol; i++)
            {
                var q = Primitive(colours, "c" + (i + 1), PrimitiveType.Quad, dbgLayer, colourMats[i], false);
                q.localPosition = new Vector3((i - (nCol - 1) * 0.5f) * PatchPitch, ColourRowY, 0f);
                q.localRotation = Quaternion.identity;
                q.localScale = new Vector3(PatchSize, PatchSize, 1f);
            }
            var back = Primitive(rig.transform, "Backing", PrimitiveType.Quad, dbgLayer, backing, false);
            back.localPosition = new Vector3(0f, -0.06f, 0.003f);                // behind both rows (viewer is on -Z)
            back.localRotation = Quaternion.identity;
            back.localScale = new Vector3(10 * PatchPitch + PatchSize + 0.06f, 0.28f, 1f);   // +0.08 .. -0.20

            Transform cards = LanbaiGradeUtil.FindOrCreateChild(rig.transform, "CalibCards", UndoName);
            bool newCards = cards.childCount == 0;
            cards.gameObject.tag = "EditorOnly";
            if (newCards) cards.gameObject.layer = dbgLayer;
            var gc = Primitive(cards, "Grey_767676", PrimitiveType.Quad, cards.gameObject.layer, grey, true);
            var wc = Primitive(cards, "White_E6E6E6", PrimitiveType.Quad, cards.gameObject.layer, white, true);
            if (newCards)
            {
                gc.localPosition = new Vector3(-0.30f, -0.45f, 0f); gc.localScale = new Vector3(0.5f, 0.5f, 1f);
                wc.localPosition = new Vector3(0.30f, -0.45f, 0f); wc.localScale = new Vector3(0.5f, 0.5f, 1f);
            }

            Transform spheres = LanbaiGradeUtil.FindOrCreateChild(rig.transform, "CalibSpheres", UndoName);
            bool newSpheres = spheres.childCount == 0;
            spheres.gameObject.tag = "EditorOnly";
            if (newSpheres) spheres.gameObject.layer = dbgLayer;
            var sphereMats = new[] { sGrey, sWhite, sChrome, sBlack };
            var sphereNames = new[] { "Grey18", "White80", "Chrome", "Black30" };
            for (int i = 0; i < 4; i++)
            {
                var s = Primitive(spheres, sphereNames[i], PrimitiveType.Sphere, spheres.gameObject.layer, sphereMats[i], true);
                if (newSpheres) { s.localPosition = new Vector3(-0.3f + 0.2f * i, 0.25f, 0f); s.localScale = Vector3.one * 0.15f; }
            }

            // ---- debug profiles + volumes
            string profDir = kit + "/Profiles";
            LanbaiGradeUtil.EnsureFolder(profDir);
            Texture2D lut = FindNeutralLut(log);
            var measure = BuildMeasureProfile(profDir + "/" + LanbaiGradeBuilder.ProfilePrefix + MeasureId + ".asset");
            var verify = BuildVerifyProfile(profDir + "/" + LanbaiGradeBuilder.ProfilePrefix + VerifyId + "_NeutralLUT.asset", lut, 1f);
            AssetDatabase.SaveAssets();
            Transform dv = LanbaiGradeUtil.FindOrCreateChild(rig.transform, "DebugVolumes", UndoName);
            dv.gameObject.layer = ppLayer;
            dv.gameObject.tag = "EditorOnly";
            DebugVolume(dv, "PPV_" + MeasureId, measure, 1001f, ppLayer);
            DebugVolume(dv, "PPV_" + VerifyId, verify, 1000f, ppLayer);

            EditorSceneManager.MarkSceneDirty(scene);
            Undo.CollapseUndoOperations(undoGroup);
            Selection.activeGameObject = rig;
            LanbaiGradeBuilder.InternalRepaint();
            return "test card ready: " + LanbaiGradeUtil.PathOf(rig.transform) + " (layer " + DebugLayerName + " = " + dbgLayer
                   + ", tag EditorOnly). Patches left->right k = -6..+4. " + log.ToString().Replace("\n", " ");
        }

        static Material GetOrCreateMaterial(string path, Shader shader)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(shader);
                AssetDatabase.CreateAsset(m, path);
            }
            else if (m.shader != shader) m.shader = shader;
            return m;
        }

        static Material StandardMat(string path, Shader standard, string hex, float smoothness, float metallic, bool matte)
        {
            var m = GetOrCreateMaterial(path, standard);
            m.SetColor("_Color", LanbaiGradeUtil.Hex(hex));                 // inspector (sRGB) value, like typing the hex
            m.SetFloat("_Glossiness", smoothness);
            m.SetFloat("_Metallic", metallic);
            // calibration cards read as pure Lambert (calib §A = albedo × E): no specular lobe, no glossy reflection
            m.SetFloat("_SpecularHighlights", matte ? 0f : 1f);
            m.SetFloat("_GlossyReflections", matte ? 0f : 1f);
            if (matte) { m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF"); m.EnableKeyword("_GLOSSYREFLECTIONS_OFF"); }
            else { m.DisableKeyword("_SPECULARHIGHLIGHTS_OFF"); m.DisableKeyword("_GLOSSYREFLECTIONS_OFF"); }
            EditorUtility.SetDirty(m);
            return m;
        }

        static Transform Primitive(Transform parent, string name, PrimitiveType type, int layer, Material mat, bool lit)
        {
            Transform t = parent.Find(name);
            GameObject go;
            if (t == null)
            {
                go = GameObject.CreatePrimitive(type);
                go.name = name;
                var col = go.GetComponent<Collider>();
                if (col != null) Object.DestroyImmediate(col);
                Undo.RegisterCreatedObjectUndo(go, UndoName);
                Undo.SetTransformParent(go.transform, parent, UndoName);
                go.transform.localPosition = Vector3.zero;
                go.transform.localRotation = Quaternion.identity;
                go.transform.localScale = Vector3.one;
            }
            else
            {
                go = t.gameObject;
                Undo.RecordObject(go, UndoName);
            }
            go.layer = layer;
            go.tag = "EditorOnly";
            GameObjectUtility.SetStaticEditorFlags(go, 0);               // never baked, never batched
            var r = go.GetComponent<MeshRenderer>();
            if (r != null)
            {
                Undo.RecordObject(r, UndoName);
                r.sharedMaterial = mat;
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = lit;
                r.lightProbeUsage = LightProbeUsage.Off;
                r.reflectionProbeUsage = lit ? ReflectionProbeUsage.BlendProbes : ReflectionProbeUsage.Off;
                r.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
            }
            return go.transform;
        }

        static void PlaceInFrontOfSceneView(Transform rig)
        {
            SceneView sv = SceneView.lastActiveSceneView;
            Vector3 pos = Vector3.zero, fwd = Vector3.forward;
            if (sv != null && sv.camera != null)
            {
                Transform ct = sv.camera.transform;
                fwd = Vector3.ProjectOnPlane(ct.forward, Vector3.up);
                if (fwd.sqrMagnitude < 1e-4f) fwd = Vector3.forward;
                fwd.Normalize();
                pos = ct.position + fwd * 1.6f;
            }
            rig.position = pos;
            rig.rotation = Quaternion.LookRotation(fwd, Vector3.up);          // +Z away from the viewer: quads face the viewer
        }

        static void DebugVolume(Transform parent, string name, PostProcessProfile profile, float priority, int layer)
        {
            Transform t = parent.Find(name);
            GameObject go;
            if (t == null)
            {
                go = new GameObject(name);
                go.layer = layer;
                Undo.RegisterCreatedObjectUndo(go, UndoName);
                Undo.SetTransformParent(go.transform, parent, UndoName);
            }
            else go = t.gameObject;
            go.layer = layer;
            go.tag = "EditorOnly";
            var v = go.GetComponent<PostProcessVolume>();
            if (v == null) v = Undo.AddComponent<PostProcessVolume>(go);
            else Undo.RecordObject(v, UndoName);
            v.isGlobal = true;
            v.blendDistance = 0f;
            v.priority = priority;
            v.weight = 0f;
            v.sharedProfile = profile;
            EditorUtility.SetDirty(v);
        }

        static PostProcessProfile LoadOrCreateProfile(string path)
        {
            var p = AssetDatabase.LoadAssetAtPath<PostProcessProfile>(path);
            if (p != null) return p;
            p = ScriptableObject.CreateInstance<PostProcessProfile>();
            AssetDatabase.CreateAsset(p, path);
            return p;
        }

        static PostProcessProfile BuildMeasureProfile(string path)
        {
            var p = LoadOrCreateProfile(path);
            LanbaiGradeBuilder.PruneSettings(p, new List<Type> { typeof(Bloom), typeof(Vignette), typeof(Grain) });
            var b = LanbaiGradeBuilder.GetOrAdd<Bloom>(p); b.intensity.Override(0f); EditorUtility.SetDirty(b);
            var v = LanbaiGradeBuilder.GetOrAdd<Vignette>(p); v.intensity.Override(0f); EditorUtility.SetDirty(v);
            var g = LanbaiGradeBuilder.GetOrAdd<Grain>(p); g.intensity.Override(0f); EditorUtility.SetDirty(g);
            p.isDirty = true;
            EditorUtility.SetDirty(p);
            return p;
        }

        static PostProcessProfile BuildVerifyProfile(string path, Texture2D lut, float contribution)
        {
            var p = LoadOrCreateProfile(path);
            LanbaiGradeBuilder.PruneSettings(p, new List<Type> { typeof(ColorGrading), typeof(Bloom), typeof(Vignette), typeof(Grain) });
            var cg = LanbaiGradeBuilder.GetOrAdd<ColorGrading>(p);
            cg.gradingMode.Override(GradingMode.LowDefinitionRange);   // bible 1.7: LDR test profile
            cg.ldrLut.Override(lut);
            cg.ldrLutContribution.Override(contribution);
            cg.temperature.Override(0f);
            cg.tint.Override(0f);
            cg.colorFilter.Override(Color.white);
            cg.hueShift.Override(0f);
            cg.saturation.Override(0f);
            cg.brightness.Override(0f);
            cg.contrast.Override(0f);
            cg.lift.Override(new Vector4(1f, 1f, 1f, 0f));
            cg.gamma.Override(new Vector4(1f, 1f, 1f, 0f));
            cg.gain.Override(new Vector4(1f, 1f, 1f, 0f));
            EditorUtility.SetDirty(cg);
            var b = LanbaiGradeBuilder.GetOrAdd<Bloom>(p); b.intensity.Override(0f); EditorUtility.SetDirty(b);
            var v = LanbaiGradeBuilder.GetOrAdd<Vignette>(p); v.intensity.Override(0f); EditorUtility.SetDirty(v);
            var g = LanbaiGradeBuilder.GetOrAdd<Grain>(p); g.intensity.Override(0f); EditorUtility.SetDirty(g);
            p.isDirty = true;
            EditorUtility.SetDirty(p);
            return p;
        }

        // =========================================================================================
        // LUT import settings (bible 1.7): Default, sRGB off, no mips, Clamp, Bilinear, Aniso 0, uncompressed
        // =========================================================================================
        static Texture2D FindNeutralLut(StringBuilder log)
        {
            string best = null;
            string kit = LanbaiGradeUtil.KitFolder();
            foreach (string guid in AssetDatabase.FindAssets(NeutralLutName + " t:Texture2D"))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(p) != NeutralLutName) continue;
                if (best == null || p.StartsWith(kit, StringComparison.Ordinal)) best = p;
            }
            if (best == null) { log.AppendLine("- WARNING " + NeutralLutName + ".png not found: the LDR verify profile has no LUT"); return null; }
            string fix = FixLutImport(best);
            if (fix.Length > 0) log.AppendLine("- " + fix);
            return AssetDatabase.LoadAssetAtPath<Texture2D>(best);
        }

        public static string FixAllLutImportSettings()
        {
            var sb = new StringBuilder();
            int n = 0;
            foreach (string guid in AssetDatabase.FindAssets("_1024x32 t:Texture2D"))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                string name = Path.GetFileNameWithoutExtension(p);
                if (!name.StartsWith("Lanbai_", StringComparison.Ordinal) || !name.EndsWith("_1024x32", StringComparison.Ordinal)) continue;
                n++;
                string r = FixLutImport(p);
                if (r.Length > 0) sb.Append(r).Append(" ");
            }
            return n + " Lanbai LUT strips checked. " + (sb.Length > 0 ? sb.ToString() : "all already correct.");
        }

        static string FixLutImport(string path)
        {
            var imp = AssetImporter.GetAtPath(path) as TextureImporter;
            if (imp == null) return "";
            bool ch = false;
            if (imp.textureType != TextureImporterType.Default) { imp.textureType = TextureImporterType.Default; ch = true; }
            if (imp.sRGBTexture) { imp.sRGBTexture = false; ch = true; }
            if (imp.mipmapEnabled) { imp.mipmapEnabled = false; ch = true; }
            if (imp.wrapMode != TextureWrapMode.Clamp) { imp.wrapMode = TextureWrapMode.Clamp; ch = true; }
            if (imp.filterMode != FilterMode.Bilinear) { imp.filterMode = FilterMode.Bilinear; ch = true; }
            if (imp.anisoLevel != 0) { imp.anisoLevel = 0; ch = true; }
            if (imp.textureCompression != TextureImporterCompression.Uncompressed) { imp.textureCompression = TextureImporterCompression.Uncompressed; ch = true; }
            if (imp.crunchedCompression) { imp.crunchedCompression = false; ch = true; }
            if (imp.maxTextureSize < 1024) { imp.maxTextureSize = 2048; ch = true; }
            if (imp.npotScale != TextureImporterNPOTScale.None) { imp.npotScale = TextureImporterNPOTScale.None; ch = true; }
            if (imp.isReadable) { imp.isReadable = false; ch = true; }
            foreach (string plat in new[] { "Standalone", "Android" })
            {
                var ps = imp.GetPlatformTextureSettings(plat);
                if (ps != null && ps.overridden) { ps.overridden = false; imp.SetPlatformTextureSettings(ps); ch = true; }
            }
            if (!ch) return "";
            imp.SaveAndReimport();
            return "fixed LUT import settings of " + path;
        }

        // =========================================================================================
        // Visibility / weights helpers
        // =========================================================================================
        public static string ToggleVisible()
        {
            GameObject rig = LanbaiGradeUtil.FindRoot(SceneManager.GetActiveScene(), RigName);
            if (rig == null) return "no test card: run 蓝白/Grades/Test Card";
            Undo.RecordObject(rig, UndoName);
            rig.SetActive(!rig.activeSelf);
            EditorSceneManager.MarkSceneDirty(rig.scene);
            return "test card " + (rig.activeSelf ? "shown" : "hidden (its debug volumes are off too)");
        }

        public static PostProcessVolume DebugVolume(string id)
        {
            GameObject rig = LanbaiGradeUtil.FindRoot(SceneManager.GetActiveScene(), RigName);
            if (rig == null) return null;
            Transform t = rig.transform.Find("DebugVolumes/PPV_" + id);
            return t == null ? null : t.GetComponent<PostProcessVolume>();
        }

        public static string SetMeasurementMode(bool on)
        {
            var v = DebugVolume(MeasureId);
            if (v == null) return "no test card";
            LanbaiGradeBuilder.SetWeight(v, on ? 1f : 0f);
            LanbaiGradeBuilder.InternalRepaint();
            return "measurement mode (bloom / vignette / grain off) " + (on ? "ON" : "off");
        }

        /// <summary>contribution &lt; 0: verify volume off; 0 or 1: LDR verify volume on with that contribution.</summary>
        public static string SetLutVerify(float contribution)
        {
            var v = DebugVolume(VerifyId);
            if (v == null || v.sharedProfile == null) return "no test card";
            ColorGrading cg;
            if (contribution >= 0f && v.sharedProfile.TryGetSettings(out cg))
            {
                Undo.RecordObject(cg, "蓝白 LUT verify");
                cg.ldrLutContribution.Override(Mathf.Clamp01(contribution));
                EditorUtility.SetDirty(cg);
            }
            LanbaiGradeBuilder.SetWeight(v, contribution >= 0f ? 1f : 0f);
            LanbaiGradeBuilder.InternalRepaint();
            return contribution < 0f ? "LDR verify off" : "LDR verify ON, contribution " + contribution;
        }

        // =========================================================================================
        // Automatic measurement
        // =========================================================================================
        sealed class Session
        {
            public GameObject rig, gradesRoot, camGo;
            public Camera cam;
            public RenderTexture rt;
            public Texture2D read;
            public bool rigActive, rootActive;
            public readonly List<KeyValuePair<PostProcessVolume, float>> weights = new List<KeyValuePair<PostProcessVolume, float>>();
            public Dictionary<string, PostProcessVolume> volumes;
            public Transform[] patches;
            public Transform[] colourPatches;           // null on a rig built by an older kit (re-run Test Card)
            public Transform greyCard, whiteCard;
            public int patchMask, cardMask;
        }

        static string Begin(out Session s)
        {
            s = null;
            if (EditorApplication.isPlayingOrWillChangePlaymode) return "leave Play mode first (the Director would fight the weights)";
            Scene scene = SceneManager.GetActiveScene();
            GameObject rig = LanbaiGradeUtil.FindRoot(scene, RigName);
            if (rig == null) { string b = Build(); rig = LanbaiGradeUtil.FindRoot(scene, RigName); if (rig == null) return b; }
            var vols = LanbaiGradeBuilder.FindVolumes();
            if (vols.Count == 0) return "no grade volumes: run 蓝白/Grades/Build Profiles & Volumes first";
            int dbg = LayerMask.NameToLayer(DebugLayerName), pp = LayerMask.NameToLayer(LanbaiGradeBuilder.VolumeLayerName);
            if (dbg < 0 || pp < 0) return "layers missing: run Test Card first";
            PostProcessResources res = LanbaiGradeUtil.FindResources();
            if (res == null) return "PPv2 PostProcessResources asset not found (is com.unity.postprocessing installed?)";

            s = new Session { rig = rig, volumes = vols };
            s.gradesRoot = LanbaiGradeUtil.FindRoot(scene, LanbaiGradeBuilder.RootName);
            s.rigActive = rig.activeSelf;
            s.rootActive = s.gradesRoot != null && s.gradesRoot.activeSelf;
            foreach (var v in vols.Values) s.weights.Add(new KeyValuePair<PostProcessVolume, float>(v, v.weight));
            foreach (string id in new[] { MeasureId, VerifyId })
            {
                var dv = DebugVolume(id);
                if (dv != null) s.weights.Add(new KeyValuePair<PostProcessVolume, float>(dv, dv.weight));
            }
            rig.SetActive(true);
            if (s.gradesRoot != null) s.gradesRoot.SetActive(true);
            var all = new List<PostProcessVolume>(vols.Values);
            foreach (string id in new[] { MeasureId, VerifyId }) { var dv = DebugVolume(id); if (dv != null) all.Add(dv); }
            LanbaiGradeUtil.ResortVolumes(all);

            s.patches = new Transform[KMax - KMin + 1];
            for (int k = KMin; k <= KMax; k++)
            {
                s.patches[k - KMin] = rig.transform.Find("Patches/k" + (k >= 0 ? "+" : "") + k);
                if (s.patches[k - KMin] == null) { End(s); s = null; return "patch k" + k + " missing: re-run Test Card"; }
            }
            int nCol = LanbaiGradeData.ColourPatchNames.Length;
            s.colourPatches = new Transform[nCol];
            for (int i = 0; i < nCol; i++)
            {
                s.colourPatches[i] = rig.transform.Find("ColourPatches/c" + (i + 1));
                if (s.colourPatches[i] == null) { s.colourPatches = null; break; }
            }
            s.greyCard = rig.transform.Find("CalibCards/Grey_767676");
            s.whiteCard = rig.transform.Find("CalibCards/White_E6E6E6");

            s.camGo = new GameObject("Lanbai_MeasureCam") { hideFlags = HideFlags.HideAndDontSave };
            s.cam = s.camGo.AddComponent<Camera>();
            s.cam.enabled = false;                                             // rendered by hand
            s.cam.clearFlags = CameraClearFlags.SolidColor;
            s.cam.backgroundColor = Color.black;
            // patch pass: the debug layer ONLY (m3); card pass: + the cards' own layers (they may sit on Bus)
            s.patchMask = 1 << dbg;
            s.cardMask = s.patchMask;
            if (s.greyCard != null) s.cardMask |= 1 << s.greyCard.gameObject.layer;
            if (s.whiteCard != null) s.cardMask |= 1 << s.whiteCard.gameObject.layer;
            s.cam.allowHDR = true;                                             // bible 1.4
            s.cam.allowMSAA = false;
            s.cam.useOcclusionCulling = false;
            s.cam.renderingPath = RenderingPath.Forward;
            s.cam.nearClipPlane = 0.05f;
            s.cam.farClipPlane = 100f;
            AimAtPatches(s);
            var ppl = s.camGo.AddComponent<PostProcessLayer>();
            ppl.Init(res);
            ppl.volumeTrigger = s.camGo.transform;
            ppl.volumeLayer = 1 << pp;
            ppl.antialiasingMode = PostProcessLayer.Antialiasing.None;
            ppl.stopNaNPropagation = true;
            ppl.finalBlitToCameraTarget = false;

            s.rt = new RenderTexture(CapW, CapH, 24, RenderTextureFormat.ARGBHalf, RenderTextureReadWrite.Linear);
            s.rt.antiAliasing = 1;
            s.rt.Create();
            s.cam.targetTexture = s.rt;
            // float read-back when the GPU supports it (exact); otherwise Capture() goes through an 8-bit sRGB target
            if (SystemInfo.IsFormatSupported(GraphicsFormat.R16G16B16A16_SFloat, FormatUsage.ReadPixels))
                s.read = new Texture2D(CapW, CapH, TextureFormat.RGBAHalf, false, true);
            return null;
        }

        /// <summary>Patch pass: 1.5 m in front of the patch row, FOV 40, LanbaiDebug layer only.</summary>
        static void AimAtPatches(Session s)
        {
            Transform row = s.rig.transform.Find("Patches");
            s.cam.cullingMask = s.patchMask;
            s.cam.fieldOfView = 40f;
            s.camGo.transform.rotation = row.rotation;                         // look along +Z at the quads' front faces
            s.camGo.transform.position = row.position - row.forward * MeasureDistance;
        }

        /// <summary>Card pass: 0.7 m in front of the two cards' midpoint (close, so nothing on the Bus layer gets between).</summary>
        static bool AimAtCards(Session s)
        {
            if (s.greyCard == null && s.whiteCard == null) return false;
            Transform a = s.greyCard != null ? s.greyCard : s.whiteCard, b = s.whiteCard != null ? s.whiteCard : s.greyCard;
            Vector3 mid = (a.position + b.position) * 0.5f;
            s.cam.cullingMask = s.cardMask;
            s.cam.fieldOfView = 60f;
            s.camGo.transform.rotation = a.rotation;                           // quads face -Z: look along their +Z
            s.camGo.transform.position = mid - a.forward * 0.7f;
            return true;
        }

        static void End(Session s)
        {
            if (s == null) return;
            foreach (var kv in s.weights) if (kv.Key != null) kv.Key.weight = kv.Value;
            if (s.rig != null) s.rig.SetActive(s.rigActive);
            if (s.gradesRoot != null) s.gradesRoot.SetActive(s.rootActive);
            if (s.cam != null) s.cam.targetTexture = null;
            if (s.rt != null) { s.rt.Release(); Object.DestroyImmediate(s.rt); }
            if (s.read != null) Object.DestroyImmediate(s.read);
            if (s.camGo != null) Object.DestroyImmediate(s.camGo);
            LanbaiGradeBuilder.InternalRepaint();
        }

        /// <summary>Scene 'id' alone at weight 1, helpers + lens 0, debug volumes as given.</summary>
        static void SoloForMeasure(Session s, string sceneId, bool measure, bool verify)
        {
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (!s.volumes.TryGetValue(e.id, out v)) continue;
                v.weight = (e.kind == LanbaiGradeKind.Scene && e.id == sceneId) ? 1f : 0f;
            }
            var mv = DebugVolume(MeasureId); if (mv != null) mv.weight = measure ? 1f : 0f;
            var vv = DebugVolume(VerifyId); if (vv != null) vv.weight = verify ? 1f : 0f;
        }

        static Color[] Capture(Session s)
        {
            for (int i = 0; i < 3; i++) s.cam.Render();                        // first frames bake the PPv2 LUT
            RenderTexture prev = RenderTexture.active;
            try
            {
                if (s.read != null)
                {
                    RenderTexture.active = s.rt;
                    s.read.ReadPixels(new Rect(0, 0, CapW, CapH), 0, 0, false);
                    s.read.Apply(false, false);
                    return s.read.GetPixels();                                  // linear display values, row 0 = bottom
                }
                // no float ReadPixels on this GPU: let the hardware sRGB-encode into an 8-bit target, then decode back
                RenderTexture tmp = RenderTexture.GetTemporary(CapW, CapH, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
                Graphics.Blit(s.rt, tmp);
                RenderTexture.active = tmp;
                var t8 = new Texture2D(CapW, CapH, TextureFormat.RGBA32, false, false);
                t8.ReadPixels(new Rect(0, 0, CapW, CapH), 0, 0, false);
                t8.Apply(false, false);
                Color32[] b = t8.GetPixels32();
                Object.DestroyImmediate(t8);
                RenderTexture.ReleaseTemporary(tmp);
                var o = new Color[b.Length];
                for (int i = 0; i < b.Length; i++)
                    o[i] = new Color(Mathf.GammaToLinearSpace(b[i].r / 255f), Mathf.GammaToLinearSpace(b[i].g / 255f), Mathf.GammaToLinearSpace(b[i].b / 255f), 1f);
                return o;
            }
            finally { RenderTexture.active = prev; }
        }

        /// <summary>Average sRGB 0-255 of a box around a world point (per-pixel encode, then mean: like a colour picker average).</summary>
        static bool Sample(Session s, Color[] px, Transform t, float halfWorld, out Vector3 srgb255)
        {
            srgb255 = Vector3.zero;
            if (t == null) return false;
            Vector3 c = s.cam.WorldToScreenPoint(t.position);
            Vector3 e = s.cam.WorldToScreenPoint(t.position + t.right * halfWorld * t.lossyScale.x);
            if (c.z <= 0f) return false;
            float halfPx = Mathf.Max(2f, Mathf.Abs(e.x - c.x) * 0.6f);
            int x0 = Mathf.RoundToInt(c.x - halfPx), x1 = Mathf.RoundToInt(c.x + halfPx);
            int y0 = Mathf.RoundToInt(c.y - halfPx), y1 = Mathf.RoundToInt(c.y + halfPx);
            if (x0 < 0 || y0 < 0 || x1 >= CapW || y1 >= CapH) return false;
            double r = 0, g = 0, b = 0; int n = 0;
            for (int y = y0; y <= y1; y++)
                for (int x = x0; x <= x1; x++)
                {
                    Color p = px[y * CapW + x];
                    r += Mathf.LinearToGammaSpace(Mathf.Clamp01(p.r));
                    g += Mathf.LinearToGammaSpace(Mathf.Clamp01(p.g));
                    b += Mathf.LinearToGammaSpace(Mathf.Clamp01(p.b));
                    n++;
                }
            srgb255 = new Vector3((float)(r / n * 255.0), (float)(g / n * 255.0), (float)(b / n * 255.0));
            return true;
        }

        /// <summary>Average sRGB 0-255 of a square of half size halfWorld (m) around a world point.</summary>
        static bool SamplePoint(Session s, Color[] px, Vector3 world, Vector3 right, float halfWorld, out Vector3 srgb255)
        {
            srgb255 = Vector3.zero;
            Vector3 c = s.cam.WorldToScreenPoint(world);
            Vector3 e = s.cam.WorldToScreenPoint(world + right * halfWorld);
            if (c.z <= 0f) return false;
            float halfPx = Mathf.Max(2f, Mathf.Abs(e.x - c.x));
            int x0 = Mathf.RoundToInt(c.x - halfPx), x1 = Mathf.RoundToInt(c.x + halfPx);
            int y0 = Mathf.RoundToInt(c.y - halfPx), y1 = Mathf.RoundToInt(c.y + halfPx);
            if (x0 < 0 || y0 < 0 || x1 >= CapW || y1 >= CapH) return false;
            double r = 0, g = 0, b = 0; int n = 0;
            for (int y = y0; y <= y1; y++)
                for (int x = x0; x <= x1; x++)
                {
                    Color p = px[y * CapW + x];
                    r += Mathf.LinearToGammaSpace(Mathf.Clamp01(p.r));
                    g += Mathf.LinearToGammaSpace(Mathf.Clamp01(p.g));
                    b += Mathf.LinearToGammaSpace(Mathf.Clamp01(p.b));
                    n++;
                }
            srgb255 = new Vector3((float)(r / n * 255.0), (float)(g / n * 255.0), (float)(b / n * 255.0));
            return true;
        }

        static string Hex(Vector3 v)
        {
            return "#" + Mathf.Clamp(Mathf.RoundToInt(v.x), 0, 255).ToString("X2") + Mathf.Clamp(Mathf.RoundToInt(v.y), 0, 255).ToString("X2")
                   + Mathf.Clamp(Mathf.RoundToInt(v.z), 0, 255).ToString("X2");
        }

        static float MaxDiff(Vector3 got, string wantHex)
        {
            Color w = LanbaiGradeUtil.Hex(wantHex);
            return Mathf.Max(Mathf.Abs(got.x - w.r * 255f), Mathf.Max(Mathf.Abs(got.y - w.g * 255f), Mathf.Abs(got.z - w.b * 255f)));
        }

        static Color32[] ToSRGB32(Color[] px)
        {
            var o = new Color32[px.Length];
            for (int i = 0; i < px.Length; i++)
                o[i] = new Color32((byte)Mathf.RoundToInt(Mathf.LinearToGammaSpace(Mathf.Clamp01(px[i].r)) * 255f),
                                   (byte)Mathf.RoundToInt(Mathf.LinearToGammaSpace(Mathf.Clamp01(px[i].g)) * 255f),
                                   (byte)Mathf.RoundToInt(Mathf.LinearToGammaSpace(Mathf.Clamp01(px[i].b)) * 255f), 255);
            return o;
        }

        static void SavePng(Color32[] px, int w, int h, string path)
        {
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false, false);
            t.SetPixels32(px);
            t.Apply(false, false);
            File.WriteAllBytes(path, t.EncodeToPNG());
            Object.DestroyImmediate(t);
        }

        /// <summary>
        /// Bible 1.5 step 1 / 9.3, automated: every scene profile alone at weight 1, bloom / vignette / grain off,
        /// the 11 patches and the black backing sampled and compared with calib_final.md section C (+-3 codes) and with
        /// the black the bible asks for at input 0. Each reading is also compared with the art side's model of PPv2,
        /// which tells a wrong solve (Unity = model, model != target) from a wrong model (Unity != model).
        /// Writes LanbaiReports/TestCard_Report.md, TestCard/&lt;id&gt;.png and TestCard_AllProfiles.png.
        /// </summary>
        public static string MeasureAll()
        {
            Session s;
            string err = Begin(out s);
            if (err != null) return "ERROR: " + err;
            var md = new StringBuilder();
            var diag = new StringBuilder();
            var colourMd = new StringBuilder();
            int fails = 0, profilesDone = 0, modelOff = 0, solveOff = 0, colourModelOff = 0;
            float selfCheck = -1f;
            string pngDir = Path.Combine(LanbaiGradeUtil.ReportFolder(), "TestCard");
            Directory.CreateDirectory(pngDir);
            var stripRows = new List<Color32[]>();
            int stripW = 0, stripH = 0, stripX0 = 0, stripY0 = 0;
            bool routeC = LanbaiGradeBuilder.CurrentRouteIsC();
            try
            {
                md.AppendLine("# 蓝白 · grade test card (bible 1.5 / calib_final.md §C)");
                md.AppendLine();
                md.AppendLine("- " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture) + ", Unity " + Application.unityVersion
                              + ", " + SystemInfo.graphicsDeviceType + ", colour space " + PlayerSettings.colorSpace
                              + ", route " + (routeC ? "C (External LUT)" : "A (parametric)") + ", data sha256 " + LanbaiGradeData.GradesSha256.Substring(0, 12) + "…");
                md.AppendLine("- each scene profile alone at weight 1; measurement volume on (bloom, vignette, grain = 0); patches 0.18 × 2^k, k = −6..+4; "
                              + "black = the 0.0 backing above the row (input 0)");
                md.AppendLine("- cell = measured screen hex (max channel error vs §C in codes). PASS = every patch and the black within ±3.");
                md.AppendLine();
                md.AppendLine("| profile | k−6 | k−5 | k−4 | k−3 | k−2 | k−1 | k0 | k+1 | k+2 | k+3 | k+4 | black (input 0) | max Δ | result | grey card | white card |");
                md.AppendLine("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|");
                diag.AppendLine("| profile | max Δ measured vs model (codes) | max Δ model vs §C target (codes) | reading |");
                diag.AppendLine("|---|---|---|---|");
                colourMd.Append("| profile ");
                foreach (string n in LanbaiGradeData.ColourPatchNames) colourMd.Append("| " + n + " ");
                colourMd.AppendLine("| max Δ vs look | max Δ vs model |");
                colourMd.Append("|---");
                for (int i = 0; i <= LanbaiGradeData.ColourPatchNames.Length + 1; i++) colourMd.Append("|---");
                colourMd.AppendLine("|");
                foreach (var e in LanbaiGradeData.Entries)
                {
                    if (e.kind != LanbaiGradeKind.Scene) continue;
                    EditorUtility.DisplayProgressBar("蓝白 test card", e.id, (float)profilesDone / 15f);
                    SoloForMeasure(s, e.id, true, false);
                    AimAtPatches(s);
                    Color[] px = Capture(s);
                    var row = new StringBuilder("| " + e.id + " ");
                    float worst = 0f, vsModel = 0f, modelVsTarget = 0f;
                    for (int i = 0; i < s.patches.Length; i++)
                    {
                        Vector3 v;
                        if (!Sample(s, px, s.patches[i], PatchSize * 0.5f / Mathf.Max(1e-4f, s.patches[i].lossyScale.x), out v))
                        { row.Append("| off-frame "); worst = 999f; continue; }
                        float d = e.expectedTestCard != null ? MaxDiff(v, e.expectedTestCard[i]) : 0f;
                        worst = Mathf.Max(worst, d);
                        if (e.predictedTestCard != null)
                        {
                            vsModel = Mathf.Max(vsModel, MaxDiff(v, e.predictedTestCard[i]));
                            if (e.expectedTestCard != null) modelVsTarget = Mathf.Max(modelVsTarget, HexDiff(e.predictedTestCard[i], e.expectedTestCard[i]));
                        }
                        row.Append("| `" + Hex(v) + "` (" + d.ToString("0.0", CultureInfo.InvariantCulture) + ") ");
                        if (e.id == "S10" && i == 6) selfCheck = d;
                    }
                    // black point: the 0.0 backing strip between the patch row and the backing's top edge
                    Vector3 bk;
                    Transform row0 = s.rig.transform.Find("Patches");
                    Vector3 blackPos = row0.position + row0.up * (PatchSize * 0.5f + 0.015f) + row0.forward * 0.003f;
                    if (SamplePoint(s, px, blackPos, row0.right, 0.008f, out bk) && e.expectedBlack != null)
                    {
                        float d = MaxDiff(bk, e.expectedBlack);
                        worst = Mathf.Max(worst, d);
                        if (e.predictedBlack != null) vsModel = Mathf.Max(vsModel, MaxDiff(bk, e.predictedBlack));
                        row.Append("| `" + Hex(bk) + "` (" + d.ToString("0.0", CultureInfo.InvariantCulture) + "; bible `" + e.expectedBlack + "`) ");
                    }
                    else row.Append("| — ");
                    // colour row (not a bible target): measured vs the look and vs the engine model
                    if (s.colourPatches != null && e.expectedColourPatches != null && e.predictedColourPatches != null)
                    {
                        float cLook = 0f, cModel = 0f;
                        colourMd.Append("| " + e.id + " ");
                        for (int i = 0; i < s.colourPatches.Length; i++)
                        {
                            Vector3 cv;
                            if (!Sample(s, px, s.colourPatches[i], PatchSize * 0.5f / Mathf.Max(1e-4f, s.colourPatches[i].lossyScale.x), out cv))
                            { colourMd.Append("| off-frame "); cModel = 999f; continue; }
                            float dl = MaxDiff(cv, e.expectedColourPatches[i]), dm = MaxDiff(cv, e.predictedColourPatches[i]);
                            cLook = Mathf.Max(cLook, dl);
                            cModel = Mathf.Max(cModel, dm);
                            colourMd.Append("| `" + Hex(cv) + "` (" + dl.ToString("0", CultureInfo.InvariantCulture) + "/" + dm.ToString("0", CultureInfo.InvariantCulture) + ") ");
                        }
                        if (cModel > 3f && !routeC) colourModelOff++;
                        colourMd.AppendLine("| " + cLook.ToString("0.0", CultureInfo.InvariantCulture) + " | " + cModel.ToString("0.0", CultureInfo.InvariantCulture) + " |");
                    }
                    bool pass = worst <= 3f;
                    if (!pass) fails++;
                    string reading;
                    if (routeC) reading = "Route C: the LUT is the look itself (model column = Route A prediction, for information)";
                    else if (pass) reading = "OK";
                    else if (vsModel <= 2f) { solveOff++; reading = "**Unity = our model, model misses the target: the solve is off here. Send the report; do NOT hand-tune.**"; }
                    else { modelOff++; reading = "**Unity differs from our model of PPv2: send the report (TestCard/" + e.id + ".png too). Route C is the fallback.**"; }
                    diag.AppendLine("| " + e.id + " | " + vsModel.ToString("0.0", CultureInfo.InvariantCulture) + " | "
                                    + modelVsTarget.ToString("0.0", CultureInfo.InvariantCulture) + " | " + reading + " |");

                    Color32[] srgb = ToSRGB32(px);
                    SavePng(srgb, CapW, CapH, Path.Combine(pngDir, e.id + ".png"));
                    // crop around the patch row for the composite: measured strip, then the §C target strip
                    if (stripW == 0)
                    {
                        Vector3 a = s.cam.WorldToScreenPoint(s.patches[0].position), z = s.cam.WorldToScreenPoint(s.patches[s.patches.Length - 1].position);
                        Vector3 up = s.cam.WorldToScreenPoint(s.patches[0].position + s.patches[0].up * PatchSize);
                        float ph = Mathf.Abs(up.y - a.y);
                        stripX0 = Mathf.Clamp(Mathf.RoundToInt(a.x - ph * 0.8f), 0, CapW - 1);
                        int x1 = Mathf.Clamp(Mathf.RoundToInt(z.x + ph * 0.8f), 0, CapW - 1);
                        stripY0 = Mathf.Clamp(Mathf.RoundToInt(a.y - ph * 0.7f), 0, CapH - 1);
                        int y1 = Mathf.Clamp(Mathf.RoundToInt(a.y + ph * 0.7f), 0, CapH - 1);
                        stripW = x1 - stripX0 + 1; stripH = y1 - stripY0 + 1;
                    }
                    var crop = new Color32[stripW * stripH];
                    for (int y = 0; y < stripH; y++)
                        for (int x = 0; x < stripW; x++) crop[y * stripW + x] = srgb[(stripY0 + y) * CapW + stripX0 + x];
                    var target = new Color32[stripW * stripH];
                    for (int y = 0; y < stripH; y++)
                        for (int x = 0; x < stripW; x++)
                        {
                            int i = Mathf.Clamp(Mathf.FloorToInt((float)x / stripW * 11f), 0, 10);
                            target[y * stripW + x] = e.expectedTestCard != null ? (Color32)LanbaiGradeUtil.Hex(e.expectedTestCard[i]) : new Color32(0, 0, 0, 255);
                        }
                    stripRows.Add(target);                                      // PNG rows go bottom-up: target first = below
                    stripRows.Add(crop);

                    // card pass (separate camera aim and culling mask, m3)
                    string gs = "—", ws = "—";
                    if (AimAtCards(s))
                    {
                        Color[] pc = Capture(s);
                        Vector3 gv, wv;
                        if (Sample(s, pc, s.greyCard, 0.25f, out gv)) gs = "`" + Hex(gv) + "`";
                        if (Sample(s, pc, s.whiteCard, 0.25f, out wv)) ws = "`" + Hex(wv) + "`";
                        AimAtPatches(s);
                    }
                    row.Append("| " + worst.ToString("0.0", CultureInfo.InvariantCulture) + " | " + (pass ? "PASS" : "**FAIL**") + " | " + gs + " | " + ws + " |");
                    md.AppendLine(row.ToString());
                    profilesDone++;
                }
                // composite (top = first profile)
                if (stripRows.Count > 0)
                {
                    int gap = 4, rowsN = stripRows.Count, H = rowsN * stripH + (rowsN / 2) * gap;
                    var all = new Color32[stripW * H];
                    for (int i = 0; i < all.Length; i++) all[i] = new Color32(24, 24, 24, 255);
                    int yCursor = 0;
                    for (int r = rowsN - 1; r >= 0; r -= 2)                      // last profile at the bottom of the image
                    {
                        for (int part = -1; part <= 0; part++)                  // target row, then measured row above it
                        {
                            Color32[] src = stripRows[r + part];
                            for (int y = 0; y < stripH; y++)
                                for (int x = 0; x < stripW; x++) all[(yCursor + y) * stripW + x] = src[y * stripW + x];
                            yCursor += stripH;
                        }
                        yCursor += gap;
                        if (yCursor >= H) break;
                    }
                    SavePng(all, stripW, H, Path.Combine(LanbaiGradeUtil.ReportFolder(), "TestCard_AllProfiles.png"));
                }
            }
            finally
            {
                EditorUtility.ClearProgressBar();
                End(s);
            }
            md.AppendLine();
            if (selfCheck < 0f || selfCheck > 3f)
                md.AppendLine("**SELF-CHECK FAILED**: S10 (neutral) patch k = 0 must read `#767676` (0.18 through Neutral). The measurement chain itself is wrong: "
                              + "check Linear colour space, camera HDR / Tier HDR FP16, that PPv2 is installed, and that Lanbai/Debug/TestPatch compiled.");
            else md.AppendLine("Self-check OK: S10 (neutral) patch k = 0 reads within ±3 of `#767676`.");
            md.AppendLine();
            md.AppendLine("## Unity vs the art side's model of PPv2");
            md.AppendLine();
            md.AppendLine("The model (Tools~/engine/ppv2_engine.py, written from the PPv2 source) predicted every patch for these exact numbers "
                          + "(LanbaiGradeData.predictedTestCard / predictedBlack). It reads the same way as the table above:");
            md.AppendLine();
            md.Append(diag);
            md.AppendLine();
            if (modelOff > 0) md.AppendLine("**" + modelOff + " profile(s) differ from the model** → the model of PPv2 is off on this Unity / PPv2 version. "
                                            + "Do not hand-tune: push LanbaiReports/ to FromLocal/. If the build cannot wait, 蓝白/Grades/Route C/... (External LUTs, bible 1.7) "
                                            + "does not depend on the model.");
            if (solveOff > 0) md.AppendLine("**" + solveOff + " profile(s) match the model but miss the target** → the art side re-solves. Do not hand-tune.");
            md.AppendLine();
            md.AppendLine("## Colour row (not a bible target: how Unity grades 8 saturated colours)");
            md.AppendLine();
            if (colourMd.Length > 0 && profilesDone > 0)
            {
                md.AppendLine("cell = measured hex (Δ vs the look / Δ vs the model, codes). The look is the art simulator; the model is what we expect PPv2 to show. "
                              + "Δ vs model > 3 means the model of PPv2 is off for saturated colours on this Unity: send the report.");
                md.AppendLine();
                md.Append(colourMd);
                md.AppendLine();
                if (colourModelOff > 0) md.AppendLine("**" + colourModelOff + " profile(s): the colour row differs from the model by more than 3 codes.**");
            }
            else md.AppendLine("(no colour row on this rig: re-run 蓝白/Grades/Test Card)");
            md.AppendLine();
            md.AppendLine("Grey / white cards are read in a separate close-up pass (0.7 m, culling = LanbaiDebug + the cards' own layer). "
                          + "Compare with calib_final.md §A only when the card sits under the named light, on a layer that light's culling mask includes.");
            md.AppendLine();
            md.AppendLine("Images: `TestCard/<id>.png` (full frame), `TestCard_AllProfiles.png` (per profile: measured strip above, §C target below). "
                          + "Please push the whole LanbaiReports folder to FromLocal/.");
            string path = LanbaiGradeUtil.WriteReport("TestCard_Report.md", md.ToString());
            bool ok = fails == 0 && selfCheck >= 0f && selfCheck <= 3f;
            return (ok ? "PASS" : "FAIL (" + fails + " profiles" + (modelOff > 0 ? ", " + modelOff + " differ from the model" : "")
                    + (solveOff > 0 ? ", " + solveOff + " match the model but miss the target" : "") + ")") + ": " + profilesDone + " profiles measured. Report: " + path;
        }

        static float HexDiff(string a, string b)
        {
            Color x = LanbaiGradeUtil.Hex(a), y = LanbaiGradeUtil.Hex(b);
            return 255f * Mathf.Max(Mathf.Abs(x.r - y.r), Mathf.Max(Mathf.Abs(x.g - y.g), Mathf.Abs(x.b - y.b)));
        }

        /// <summary>
        /// Bible 1.7 "先验证方向": the LDR test profile with Lanbai_Neutral_1024x32 at contribution 0 and at 1 must give
        /// the same picture. A wrong import (sRGB on, compression) or a flipped / R-B swapped strip shows up as a large difference.
        /// </summary>
        public static string VerifyNeutralLut()
        {
            Session s;
            string err = Begin(out s);
            if (err != null) return "ERROR: " + err;
            var md = new StringBuilder();
            float worst = 0f;
            ColorGrading cg = null;
            float oldContribution = 1f;
            try
            {
                var vv = DebugVolume(VerifyId);
                if (vv == null || vv.sharedProfile == null || !vv.sharedProfile.TryGetSettings(out cg)) return "ERROR: verify volume missing: run Test Card";
                if (cg.ldrLut.value == null) return "ERROR: the verify profile has no LUT (" + NeutralLutName + ".png not in the project)";
                string lutPath = AssetDatabase.GetAssetPath(cg.ldrLut.value);
                var imp = AssetImporter.GetAtPath(lutPath) as TextureImporter;
                oldContribution = cg.ldrLutContribution.value;
                var reads = new Vector3[2, s.patches.Length];
                for (int pass = 0; pass < 2; pass++)
                {
                    cg.ldrLutContribution.value = pass;
                    SoloForMeasure(s, "S10", true, true);
                    Color[] px = Capture(s);
                    for (int i = 0; i < s.patches.Length; i++)
                    {
                        Vector3 v;
                        Sample(s, px, s.patches[i], PatchSize * 0.5f / Mathf.Max(1e-4f, s.patches[i].lossyScale.x), out v);
                        reads[pass, i] = v;
                    }
                    SavePng(ToSRGB32(px), CapW, CapH, Path.Combine(LanbaiGradeUtil.ReportFolder(), "NeutralLUT_contribution" + pass + ".png"));
                }
                md.AppendLine("# 蓝白 · neutral LUT verification (bible 1.7)");
                md.AppendLine();
                md.AppendLine("- LUT `" + lutPath + "`" + (imp == null ? "" : ": type " + imp.textureType + ", sRGB " + imp.sRGBTexture + ", mips " + imp.mipmapEnabled
                              + ", wrap " + imp.wrapMode + ", filter " + imp.filterMode + ", aniso " + imp.anisoLevel + ", compression " + imp.textureCompression));
                md.AppendLine("- profile: LDR mode, everything else neutral, bloom / vignette / grain off; patches as in the test card");
                md.AppendLine();
                md.AppendLine("| patch | contribution 0 | contribution 1 | max Δ |");
                md.AppendLine("|---|---|---|---|");
                for (int i = 0; i < s.patches.Length; i++)
                {
                    Vector3 a = reads[0, i], b = reads[1, i];
                    float d = Mathf.Max(Mathf.Abs(a.x - b.x), Mathf.Max(Mathf.Abs(a.y - b.y), Mathf.Abs(a.z - b.z)));
                    worst = Mathf.Max(worst, d);
                    md.AppendLine("| k" + (i + KMin) + " | `" + Hex(a) + "` | `" + Hex(b) + "` | " + d.ToString("0.00", CultureInfo.InvariantCulture) + " |");
                }
                md.AppendLine();
                md.AppendLine(worst <= 1f ? "**PASS**: identical within 1 code (dither noise)." :
                              "**FAIL** (" + worst.ToString("0.0", CultureInfo.InvariantCulture) + " codes): check sRGB off, no compression, Aniso 0, "
                              + "and that nobody flipped the strip (we wrote it already flipped; ~255-code errors = flipped rows or R/B swapped).");
            }
            finally
            {
                if (cg != null) cg.ldrLutContribution.value = oldContribution;
                End(s);
            }
            string path = LanbaiGradeUtil.WriteReport("NeutralLUT_Report.md", md.ToString());
            return (worst <= 1f ? "PASS" : "FAIL") + " (max " + worst.ToString("0.00", CultureInfo.InvariantCulture) + " codes). Report: " + path;
        }

        /// <summary>
        /// verify.md m1, measured instead of argued: PPv2's Bloom passes settings.color.value.linear to
        /// MaterialPropertyBlock.SetColor, and SetColor decodes sRGB again in a Linear project. One bright emitter is
        /// rendered twice through a temporary bloom-only volume (no colour grading, so the output is linear), with tint
        /// white and with tint #808080, and the halo ratio is read: single decode = 0.216, double decode = 0.038.
        /// Sets the builder's bloom-colour compensation to match (project-scoped) and rebuilds the profiles if it changed.
        /// </summary>
        public static string ProbeBloomColour()
        {
            Session s;
            string err = Begin(out s);
            if (err != null) return "ERROR: " + err;
            Shader patchShader = Shader.Find(PatchShaderName);
            int dbg = LayerMask.NameToLayer(DebugLayerName), pp = LayerMask.NameToLayer(LanbaiGradeBuilder.VolumeLayerName);
            var hidden = new List<KeyValuePair<GameObject, bool>>();
            GameObject emitter = null, volGo = null;
            Material mat = null;
            PostProcessProfile prof = null;
            float ratio = -1f, halo = 0f;
            int ringPx = 0;
            bool? doubled = null;
            try
            {
                if (patchShader == null) return "ERROR: shader " + PatchShaderName + " not found";
                foreach (string child in new[] { "Patches", "ColourPatches", "Backing", "CalibCards", "CalibSpheres" })
                {
                    Transform t = s.rig.transform.Find(child);
                    if (t == null) continue;
                    hidden.Add(new KeyValuePair<GameObject, bool>(t.gameObject, t.gameObject.activeSelf));
                    t.gameObject.SetActive(false);
                }
                Transform row = s.rig.transform.Find("Patches");
                emitter = GameObject.CreatePrimitive(PrimitiveType.Quad);
                emitter.hideFlags = HideFlags.HideAndDontSave;
                var col = emitter.GetComponent<Collider>();
                if (col != null) Object.DestroyImmediate(col);
                emitter.layer = dbg;
                emitter.transform.position = row.position;
                emitter.transform.rotation = row.rotation;
                emitter.transform.localScale = new Vector3(0.04f, 0.04f, 1f);
                mat = new Material(patchShader) { hideFlags = HideFlags.HideAndDontSave };
                mat.SetFloat("_Emission", 40f);
                emitter.GetComponent<MeshRenderer>().sharedMaterial = mat;

                prof = ScriptableObject.CreateInstance<PostProcessProfile>();
                prof.hideFlags = HideFlags.HideAndDontSave;
                var bloom = prof.AddSettings<Bloom>();
                bloom.enabled.Override(true);
                bloom.intensity.Override(10f);                  // exp2(10 / 10) - 1 = 1
                bloom.threshold.Override(1.8f);                 // gamma: linear 3.6, knee from 1.8 -> only the emitter (40) blooms
                bloom.softKnee.Override(0.5f);
                bloom.diffusion.Override(7f);
                bloom.anamorphicRatio.Override(0f);
                bloom.fastMode.Override(true);
                bloom.color.Override(Color.white);
                volGo = new GameObject("Lanbai_BloomProbe") { hideFlags = HideFlags.HideAndDontSave };
                volGo.layer = pp;                               // before the volume registers itself
                var vol = volGo.AddComponent<PostProcessVolume>();
                vol.isGlobal = true;
                vol.priority = 5000f;
                vol.weight = 1f;
                vol.sharedProfile = prof;

                SoloForMeasure(s, "", false, false);            // every Lanbai volume at 0: no grading, no tonemapper -> linear output
                AimAtPatches(s);
                Color[] pw = Capture(s);
                bloom.color.Override(new Color(128f / 255f, 128f / 255f, 128f / 255f, 1f));
                Color[] pg = Capture(s);
                SavePng(ToSRGB32(pw), CapW, CapH, Path.Combine(LanbaiGradeUtil.ReportFolder(), "BloomColour_probe_white.png"));
                SavePng(ToSRGB32(pg), CapW, CapH, Path.Combine(LanbaiGradeUtil.ReportFolder(), "BloomColour_probe_grey.png"));

                // halo ring 2.5 .. 5 emitter half-sizes from the centre: pure bloom, no emitter pixels
                Vector3 c = s.cam.WorldToScreenPoint(emitter.transform.position);
                Vector3 ed = s.cam.WorldToScreenPoint(emitter.transform.position + emitter.transform.right * 0.02f);
                float h = Mathf.Max(2f, Mathf.Abs(ed.x - c.x));
                double sw = 0, sg = 0;
                int n = 0, r1 = Mathf.CeilToInt(5f * h);
                for (int y = Mathf.Max(0, (int)c.y - r1); y <= Mathf.Min(CapH - 1, (int)c.y + r1); y++)
                    for (int x = Mathf.Max(0, (int)c.x - r1); x <= Mathf.Min(CapW - 1, (int)c.x + r1); x++)
                    {
                        float d = Mathf.Sqrt((x - c.x) * (x - c.x) + (y - c.y) * (y - c.y));
                        if (d < 2.5f * h || d > 5f * h) continue;
                        Color a = pw[y * CapW + x], b = pg[y * CapW + x];
                        sw += a.r + a.g + a.b;
                        sg += b.r + b.g + b.b;
                        n++;
                    }
                ringPx = n;
                if (n > 0 && sw > 0) { halo = (float)(sw / (3.0 * n)); ratio = (float)(sg / sw); }
                if (halo > 1e-3f)
                {
                    if (ratio > 0.15f && ratio < 0.30f) doubled = false;
                    else if (ratio > 0.02f && ratio < 0.07f) doubled = true;
                }
            }
            finally
            {
                if (emitter != null) Object.DestroyImmediate(emitter);
                if (mat != null) Object.DestroyImmediate(mat);
                if (volGo != null) Object.DestroyImmediate(volGo);
                if (prof != null)
                {
                    foreach (var st in prof.settings) if (st != null) Object.DestroyImmediate(st);
                    Object.DestroyImmediate(prof);
                }
                foreach (var kv in hidden) if (kv.Key != null) kv.Key.SetActive(kv.Value);
                End(s);
            }
            bool before = LanbaiGradeUtil.BloomColourCompensation;
            string rebuild = "";
            if (doubled.HasValue && doubled.Value != before)
            {
                LanbaiGradeUtil.BloomColourCompensation = doubled.Value;
                rebuild = " Setting changed -> rebuilt: " + LanbaiGradeBuilder.BuildAll();
            }
            var md = new StringBuilder();
            md.AppendLine("# 蓝白 · bloom colour probe (verify.md m1)");
            md.AppendLine();
            md.AppendLine("- " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture) + ", Unity " + Application.unityVersion
                          + ", " + SystemInfo.graphicsDeviceType + ", colour space " + PlayerSettings.colorSpace);
            md.AppendLine("- one emitter (0.04 m, emission 40) through a bloom-only volume, tint white vs tint #808080; halo ring 2.5–5 emitter half-sizes, " + ringPx + " px");
            md.AppendLine("- halo (white tint, linear) = " + halo.ToString("0.0000", CultureInfo.InvariantCulture)
                          + "; ratio grey / white = **" + ratio.ToString("0.0000", CultureInfo.InvariantCulture) + "** (single sRGB decode 0.2159, double 0.0382)");
            md.AppendLine("- verdict: " + (doubled.HasValue ? (doubled.Value ? "**double decode** (PPv2 Color.linear + SetColor): the builder writes bloomColorCompensated"
                                                                       : "**single decode**: the builder writes the bible hex unchanged")
                                                         : "**inconclusive** (no halo, or a ratio between the two cases): setting left as it was ("
                                                           + (before ? "compensated" : "bible hex") + "). Send this report."));
            md.AppendLine("- images: BloomColour_probe_white.png, BloomColour_probe_grey.png");
            if (rebuild.Length > 0) md.AppendLine("- " + rebuild.Trim());
            string path = LanbaiGradeUtil.WriteReport("BloomColour_Report.md", md.ToString());
            return (doubled.HasValue ? (doubled.Value ? "double sRGB decode" : "single sRGB decode") : "INCONCLUSIVE")
                   + " (ratio " + ratio.ToString("0.000", CultureInfo.InvariantCulture) + "; single 0.216, double 0.038). Bloom colour compensation "
                   + (LanbaiGradeUtil.BloomColourCompensation ? "ON" : "OFF") + "." + rebuild + " Report: " + path;
        }
    }

    // =============================================================================================
    // Debug window: weights by hand, solo a profile, the §C target row, measurement / LUT switches.
    // =============================================================================================
    public sealed class LanbaiGradeDebugWindow : EditorWindow
    {
        Vector2 _scroll;
        string _last = "";

        [MenuItem(LanbaiGradeBuilder.Menu + "Debug Window", false, 40)]
        static void Open() { GetWindow<LanbaiGradeDebugWindow>("蓝白 Grades"); }

        void OnGUI()
        {
            var map = LanbaiGradeBuilder.FindVolumes();
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Build Profiles & Volumes")) _last = LanbaiGradeBuilder.BuildAll();
            if (GUILayout.Button("Test Card")) _last = LanbaiGradeTestCard.Build();
            if (GUILayout.Button("Restore weights")) _last = LanbaiGradeBuilder.RestoreInitialWeights();
            EditorGUILayout.EndHorizontal();
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Measure all → report")) _last = LanbaiGradeTestCard.MeasureAll();
            if (GUILayout.Button("Verify neutral LUT")) _last = LanbaiGradeTestCard.VerifyNeutralLut();
            if (GUILayout.Button("Show / hide card")) _last = LanbaiGradeTestCard.ToggleVisible();
            EditorGUILayout.EndHorizontal();
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Measurement mode ON")) _last = LanbaiGradeTestCard.SetMeasurementMode(true);
            if (GUILayout.Button("off")) _last = LanbaiGradeTestCard.SetMeasurementMode(false);
            if (GUILayout.Button("LDR LUT 0")) _last = LanbaiGradeTestCard.SetLutVerify(0f);
            if (GUILayout.Button("LDR LUT 1")) _last = LanbaiGradeTestCard.SetLutVerify(1f);
            if (GUILayout.Button("LDR off")) _last = LanbaiGradeTestCard.SetLutVerify(-1f);
            EditorGUILayout.EndHorizontal();
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Probe bloom colour")) _last = LanbaiGradeTestCard.ProbeBloomColour();
            if (GUILayout.Button("Route A (default)")) _last = LanbaiGradeBuilder.UseRouteA();
            if (GUILayout.Button("Route C (fallback)")) _last = LanbaiGradeBuilder.UseRouteC();
            EditorGUILayout.EndHorizontal();
            EditorGUILayout.LabelField("route " + (LanbaiGradeBuilder.CurrentRouteIsC() ? "C (External LUT)" : "A (parametric)")
                                       + " · bloom colour " + (LanbaiGradeUtil.BloomColourCompensation ? "compensated" : "bible hex"), EditorStyles.miniLabel);
            if (!string.IsNullOrEmpty(_last)) EditorGUILayout.HelpBox(_last, MessageType.None);
            if (EditorApplication.isPlaying) EditorGUILayout.HelpBox("Play 模式：Director / LanbaiExposure 会覆盖这里的 weight。", MessageType.Info);
            if (map.Count == 0) { EditorGUILayout.HelpBox("场景里还没有 Lanbai_Grades：先点 Build Profiles & Volumes。", MessageType.Warning); return; }

            string solo = null; int ones = 0, nonzero = 0;
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (e.kind != LanbaiGradeKind.Scene || !map.TryGetValue(e.id, out v)) continue;
                if (v.weight > 0f) nonzero++;
                if (v.weight >= 0.999f) { ones++; solo = e.id; }
            }
            if (ones != 1 || nonzero != 1) solo = null;

            _scroll = EditorGUILayout.BeginScrollView(_scroll);
            LanbaiGradeKind? lastKind = null;
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (!map.TryGetValue(e.id, out v)) continue;
                if (lastKind != e.kind) { EditorGUILayout.Space(); EditorGUILayout.LabelField(e.group, EditorStyles.boldLabel); lastKind = e.kind; }
                EditorGUILayout.BeginHorizontal();
                string lab = e.kind == LanbaiGradeKind.Scene ? e.id + "  " + e.shortName : e.id;
                EditorGUILayout.LabelField(new GUIContent(lab, "priority " + e.priority + "\n" + e.displayName + "\n" + e.weightRule), GUILayout.Width(170));
                float w = EditorGUILayout.Slider(v.weight, 0f, 1f);
                if (!Mathf.Approximately(w, v.weight)) { LanbaiGradeBuilder.SetWeight(v, w); LanbaiGradeBuilder.InternalRepaint(); }
                if (e.kind == LanbaiGradeKind.Scene && GUILayout.Button("Solo", GUILayout.Width(44))) _last = LanbaiGradeBuilder.Solo(e.id);
                EditorGUILayout.EndHorizontal();
                if (e.kind == LanbaiGradeKind.Scene && e.id == solo && e.expectedTestCard != null)
                {
                    EditorGUILayout.LabelField("§C target, patches k = −6..+4 (measurement mode on, ±3):", EditorStyles.miniLabel);
                    Rect r = GUILayoutUtility.GetRect(10f, 34f, GUILayout.ExpandWidth(true));
                    float cw = r.width / 11f;
                    for (int i = 0; i < 11; i++)
                    {
                        Rect c = new Rect(r.x + i * cw + 1f, r.y, cw - 2f, 20f);
                        EditorGUI.DrawRect(c, LanbaiGradeUtil.Hex(e.expectedTestCard[i]));
                        GUI.Label(new Rect(c.x, r.y + 20f, cw, 14f), e.expectedTestCard[i], EditorStyles.miniLabel);
                    }
                    EditorGUILayout.LabelField("T0 (bloom knee start, scene-linear) = " + (e.bloomT0.HasValue ? e.bloomT0.Value.ToString("0.000", CultureInfo.InvariantCulture) : "—")
                                               + "   postExposure " + (e.postExposure ?? 0f).ToString("+0.00;-0.00", CultureInfo.InvariantCulture)
                                               + "   black at input 0: bible " + (e.expectedBlack ?? "—") + ", model " + (e.predictedBlack ?? "—"), EditorStyles.miniLabel);
                    if (e.lookDefinition != null) EditorGUILayout.LabelField(new GUIContent("B1 look definition (not for Unity) ⓘ", e.lookDefinition), EditorStyles.miniLabel);
                }
            }
            EditorGUILayout.EndScrollView();
        }

        void OnInspectorUpdate() { Repaint(); }
    }
}
