// Lanbai / 蓝白 -- 蓝白/Build/车 切片 : the D-40 #1 bus slice for the local Unity test (Engineering/UnityTest/tests/bus_slice.json).
// UNCOMPILED (cloud side): Roslyn type-check only (Common/Tools~/compile_check/check_cs.sh). Never run in Unity.
//
// Builds into the CURRENT scene (the test tool hands it an empty sandbox scene); re-runnable (deletes its previous root):
//   Lanbai_BusSlice        origin, identity = the bus-local frame of the whole bus (bus at the origin, facing +Z)
//     Slice_Seat           <- Seat_SeatR0 (D-36 hero seat: part atlas on uv0, _CabinTubeLM on uv1)
//     Slice_SideWindow     <- Window_R1 (the hero side window's inside parts) + Glass_WinR1 (Lanbai/BusGlass)
//     Slice_Pillar         <- Pole_R0 (the first right stanchion)
//     Slice_Globals        LanbaiBusSliceGlobals (Bus/Scripts): the cabin globals LanbaiCabinDriver writes in the world
//     Slice_Camera         hero eye (0.55, 1.70, 2.05) looking +Z, 90 deg horizontal at 16:9, near 0.02, PPv2 PostProcessLayer
//     Slice_Grade_S2       only if the grading kit's Lanbai_PP_S2 profile exists: a global PPv2 volume (night road)
// The pieces come out of Bus.fbx with their world transforms; the rest of the FBX instance is destroyed. Names: BusLayout.json
// 'slice' (finish_bus.py), the defaults below for an older layout. Materials: exactly the full build's makers
// (LanbaiBusBuild.CabinMat / GlassMat / PartMat, the mode from LanbaiBusBuild.ModeFor) written to Bus/Generated/Materials;
// what those makers report ('texture missing', 'unknown material', 'part X: not in BusLayout.json parts', ...) is counted
// in the summary line as errors / warnings (CountShared).
// Writes ONLY under Assets/Lanbai/Bus/Generated/. bus_slice.json allowed_writes is Assets/Lanbai/Bus/Generated/**,
// Assets/Lanbai/UdonPrograms/** and Assets/SerializedUdonPrograms/**: the last two are for the U# compiler / the SDK,
// which may write there on their own while the test runs; this menu writes neither. It saves its own assets one by one
// (SaveAssetIfDirty), never AssetDatabase.SaveAssets (that would also flush whatever else is dirty, e.g. U# program
// assets). The first build in a project also makes Assets/Lanbai/Bus/Generated.meta, which is outside 'Generated/**':
// reported as a WARNING (the test's no_undeclared_writes fails on that run only).
// No .unity (the scene is never saved), no UdonSharp program assets (D-41), no VRChat components, no import-setting or
// project-setting changes: the vertex compression (bus_slice.json settings.vertex_compression_off, set by the local
// tester) and the texture import types (Part_*_Normal_* must be Normal maps: ERROR if not) are only READ and reported.
// Light: the pre-baked _CabinTubeLM on uv1 (D-32), no Unity light maps (bus_slice.json has_lightmaps only warns). Other
// lights in the scene are switched off (undoable, one undo step with the build): the slice is lit by the tube light map.
// Explained in Bus/README.md §5.
#if UNITY_EDITOR
#pragma warning disable 0618 // PPv2 3.5+ marks its types [Obsolete] (the project has 3.4.0; a warning only)
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.PostProcessing;
using UnityEngine.SceneManagement;

public static class LanbaiBusSliceBuilder
{
    public const string MenuPath = "蓝白/Build/车 切片";
    public const string RootName = "Lanbai_BusSlice";
    public const string GenDir = LanbaiBusBuild.Root + "Bus/Generated";
    const string GenMatDir = GenDir + "/Materials";
    const string GenMeshDir = GenDir + "/Meshes";
    const string PPLayerName = "PostProcessing";                  // Grading/README_Grading.md: the volume layer
    const string GradeProfile = "Lanbai_PP_S2";                    // 夜路 night road: the grade the cabin LM is calibrated under
    const string PPResourcesGuid = "d82512f9c8e5d4a4d938b575d47f88d4"; // PostProcessResources.asset in com.unity.postprocessing
    const string Tag = "[Lanbai Bus Slice] ";
    static readonly Vector3 HeroEye = new Vector3(0.55f, 1.70f, 2.05f);   // D-28 / D-40b #1 (cameras.json 'hero')

    // BusLayout.json 'slice' (finish_bus.SLICE): FBX object names per slice piece
    [Serializable] public class SliceNames { public string[] seat; public string[] window; public string[] pillar; }
    [Serializable] public class SliceLayout { public SliceNames slice; }
    static readonly string[] DefSeat = { "Seat_SeatR0" }, DefWindow = { "Window_R1", "Glass_WinR1" }, DefPillar = { "Pole_R0" };

    [MenuItem(MenuPath)]
    public static void BuildMenu() { Build(); }

    /// <summary>Builds the slice. Returns "OK ..." or "ERROR ..." (one line) for a method step; the full report goes to
    /// the Console ([Lanbai Bus Slice]).</summary>
    public static string Build()
    {
        var rep = new StringBuilder();
        int errors = 0, warnings = 0;
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(LanbaiBusBuild.FbxPath);
        if (fbx == null)
        {
            string e = "ERROR not found: " + LanbaiBusBuild.FbxPath + " (copy Bus/ to Assets/Lanbai/Bus/)";
            Debug.LogError(Tag + e);
            return e;
        }
        LanbaiBusBuild.Layout L = null;
        SliceNames sn = null;
        var layoutText = AssetDatabase.LoadAssetAtPath<TextAsset>(LanbaiBusBuild.LayoutPath);
        if (layoutText != null)
        {
            L = JsonUtility.FromJson<LanbaiBusBuild.Layout>(layoutText.text);
            var sl = JsonUtility.FromJson<SliceLayout>(layoutText.text);
            if (sl != null) sn = sl.slice;
        }
        else
        {
            errors++;
            rep.AppendLine("ERROR: not found: " + LanbaiBusBuild.LayoutPath + " (the seat's part atlas needs its 'parts' table): building with the default names");
            Debug.LogError(Tag + "not found: " + LanbaiBusBuild.LayoutPath + " (the seat's part atlas needs its 'parts' table): building with the default names");
        }
        bool fromLayout = sn != null && Has(sn.seat) && Has(sn.window) && Has(sn.pillar);
        string[] seatN = fromLayout ? sn.seat : DefSeat, windowN = fromLayout ? sn.window : DefWindow, pillarN = fromLayout ? sn.pillar : DefPillar;
        rep.AppendLine("names from " + (fromLayout ? "BusLayout.json 'slice'" : "the builder's defaults (BusLayout.json has no 'slice': exported before D-40 #1)"));
        if (L != null && L.eye_hero != null && L.eye_hero.Length >= 3 && (new Vector3(L.eye_hero[0], L.eye_hero[1], L.eye_hero[2]) - HeroEye).sqrMagnitude > 1e-6f)
        {
            warnings++;
            rep.AppendLine("WARNING: BusLayout.json eye_hero " + Fmt(new Vector3(L.eye_hero[0], L.eye_hero[1], L.eye_hero[2])) + " is not the contract eye " + Fmt(HeroEye) + " (D-40b #1): the camera uses the contract eye");
        }
        var shared = new StringBuilder();                           // the material makers report here; counted after step 3
        LanbaiBusBuild.BeginShared(shared, L);                      // PartMat reads L.parts
        // Unity's own lightmap unwrap would overwrite uv1 = the _CabinTubeLM atlas (and the uv1 check below cannot see it:
        // that unwrap is inside 0..1 too). Only reported: changing it would write Bus.fbx.meta, outside allowed_writes.
        var mi = AssetImporter.GetAtPath(LanbaiBusBuild.FbxPath) as ModelImporter;
        if (mi != null && mi.generateSecondaryUV)
        {
            errors++;
            rep.AppendLine("ERROR: " + LanbaiBusBuild.FbxPath + ": Generate Lightmap UVs is ON (Unity replaces uv1 = the _CabinTubeLM atlas)");
            Debug.LogError(Tag + LanbaiBusBuild.FbxPath + ": Generate Lightmap UVs is ON, Unity replaces uv1 (the _CabinTubeLM atlas): turn it off in the import settings and build again");
        }
        // bus_slice.json settings.vertex_compression_off (a gate of the test): a PROJECT setting, read here and reported,
        // never changed (the test's project_settings_untouched / writes.project_settings_changed would catch it)
        string vcHow;
        int vcMask = VertexCompressionMask(out vcHow);
        string vcStill = string.Join(", ", VcNeedOff.Where(a => vcMask < 0 || (vcMask & (1 << (int)a)) != 0).Select(a => a.ToString()).ToArray());
        if (vcStill.Length > 0)
        {
            warnings++;
            rep.AppendLine("WARNING: Project Settings > Player > Other Settings > Vertex Compression: " + (vcMask < 0 ? "could not read it (" + vcHow + ")" : "still compresses " + vcStill) +
                           ". bus_slice.json settings.vertex_compression_off (a gate) wants TexCoord0-3 and Color off (uv1 = the _CabinTubeLM atlas, Col = the wear masks). " +
                           "This menu does not change project settings: untick them by hand (Bus/README.md §5)");
        }
        else rep.AppendLine("vertex compression: TexCoord0-3 and Color off (mask " + vcMask + ", " + vcHow + "; bus_slice.json settings.vertex_compression_off)");

        Undo.IncrementCurrentGroup();
        Undo.SetCurrentGroupName("Build bus slice");
        int undoGroup = Undo.GetCurrentGroup();                     // one Ctrl+Z: the old slice back, the lights back on, the new one gone
        var save = new List<UnityEngine.Object>();                  // the assets this build wrote (saved one by one at the end)

        // 1. the previous slice goes (also an inactive one: GameObject.Find sees only active objects)
        for (int i = 0; i < SceneManager.sceneCount; i++)
        {
            var sc = SceneManager.GetSceneAt(i);
            if (!sc.isLoaded) continue;
            foreach (var g in sc.GetRootGameObjects()) if (g.name == RootName) Undo.DestroyObjectImmediate(g);
        }
        var old = GameObject.Find(RootName);
        while (old != null) { Undo.DestroyObjectImmediate(old); old = GameObject.Find(RootName); }
        if (GameObject.Find("Lanbai_Bus") != null)
        {
            warnings++;
            rep.AppendLine("WARNING: this scene also has the full bus (Lanbai_Bus): the slice sits inside it (same bus-local frame)");
        }
        bool firstRun = !AssetDatabase.IsValidFolder(GenDir);
        LanbaiBusBuild.EnsureFolder(GenMatDir);
        if (firstRun)
        {
            // the folder's own .meta (Assets/Lanbai/Bus/Generated.meta) is not inside 'Generated/**'
            warnings++;
            rep.AppendLine("WARNING: first build in this project: made " + GenDir + " and with it " + GenDir + ".meta, which is outside bus_slice.json " +
                           "allowed_writes (" + GenDir + "/**): the test's no_undeclared_writes fails on this run only, run it again (Bus/README.md §5)");
        }

        // 2. the FBX at the origin (unpacked, as the full build does), the three pieces out of it with their world transforms
        var root = new GameObject(RootName);
        var model = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        PrefabUtility.UnpackPrefabInstance(model, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        model.transform.SetParent(root.transform, false);
        model.transform.localPosition = Vector3.zero; model.transform.localRotation = Quaternion.identity; model.transform.localScale = Vector3.one;
        var pieces = new[] { new KeyValuePair<string, string[]>("Slice_Seat", seatN), new KeyValuePair<string, string[]>("Slice_SideWindow", windowN),
                             new KeyValuePair<string, string[]>("Slice_Pillar", pillarN) };
        var missing = new List<string>();
        var groups = new List<GameObject>();
        foreach (var p in pieces)
        {
            var g = new GameObject(p.Key);
            g.transform.SetParent(root.transform, false);
            groups.Add(g);
            foreach (string n in p.Value)
            {
                var t = LanbaiBusBuild.FindDeep(model.transform, n);
                if (t == null)
                {
                    errors++; missing.Add(n);
                    rep.AppendLine("ERROR: " + p.Key + ": " + n + " is not in Bus.fbx");
                    Debug.LogError(Tag + p.Key + ": object " + n + " is not in " + LanbaiBusBuild.FbxPath +
                                   " (an FBX exported before D-40 #1? re-export with Bus/Source/finish_bus.py, Bus/README.md §5). The rest is built.");
                    continue;
                }
                t.SetParent(g.transform, true);
            }
        }
        UnityEngine.Object.DestroyImmediate(model);

        // 3. materials, exactly as 蓝白/Build/车 makes them (Lanbai/Cabin with the tube light map on uv1; Lanbai/BusGlass for the pane)
        Shader cabin = Shader.Find("Lanbai/Cabin"), glass = Shader.Find("Lanbai/BusGlass");
        if (cabin == null || glass == null)
        {
            errors++;
            rep.AppendLine("ERROR: shader missing: Lanbai/Cabin " + (cabin != null) + ", Lanbai/BusGlass " + (glass != null));
            Debug.LogError(Tag + "shader missing: Lanbai/Cabin " + (cabin != null) + ", Lanbai/BusGlass " + (glass != null) + " (Cabin/Shaders, Rain/): materials fall back to Standard");
        }
        int layerBus = LayerMask.NameToLayer("Bus");
        if (layerBus < 0)
        {
            warnings++;
            rep.AppendLine("WARNING: layer Bus missing: add it in Project Settings > Tags and Layers (Bus/README.md §0 step 3) and build again; the slice stays on Default");
        }
        foreach (var g in groups)
        {
            var rs = g.GetComponentsInChildren<Renderer>(true);
            rep.AppendLine(g.name + ": " + rs.Length + " renderer(s)" + (rs.Length == 0 ? "  <- EMPTY" : ""));
            foreach (var r in rs)
            {
                string n = r.gameObject.name;
                string uvNote = "";
                if (n.StartsWith("Glass_"))
                {
                    r.sharedMaterial = LanbaiBusBuild.GlassMat(glass, n, GenMatDir);
                    r.shadowCastingMode = ShadowCastingMode.Off;
                }
                else
                {
                    var mode = LanbaiBusBuild.ModeFor(n);
                    var mats = r.sharedMaterials;
                    for (int i = 0; i < mats.Length; i++) mats[i] = LanbaiBusBuild.CabinMat(cabin, mats[i] != null ? mats[i].name : "Alu", mode, GenMatDir);
                    r.sharedMaterials = mats;
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject, 0);      // no Unity lightmapping (D-42 ①): the tube light is _CabinTubeLM
                    r.reflectionProbeUsage = ReflectionProbeUsage.BlendProbes;
                    if (mode == LanbaiBusBuild.Mode.CabinLM) uvNote = LightmapUV(r, save, ref errors, ref warnings);
                    else { warnings++; uvNote = "WARNING: mode " + mode + ", not on the tube light map"; }
                }
                save.AddRange(r.sharedMaterials.Where(m => m != null));
                if (layerBus >= 0) r.gameObject.layer = layerBus;
                var b = r.bounds;
                rep.AppendLine("  " + n + "  " + Tris(r) + " tris  bounds " + Fmt(b.min) + " .. " + Fmt(b.max) + "  layer " + LayerMask.LayerToName(r.gameObject.layer));
                rep.AppendLine("    materials: " + string.Join(", ", r.sharedMaterials.Select(m => m != null ? m.name + " (" + (m.shader != null ? m.shader.name : "?") + ")" : "null").ToArray()));
                if (uvNote.Length > 0) rep.AppendLine("    " + uvNote);
            }
        }
        CountShared(shared, rep, ref errors, ref warnings);
        CheckImports(groups, rep, ref errors, ref warnings);
        int nLightmaps = LightmapSettings.lightmaps != null ? LightmapSettings.lightmaps.Length : 0;
        rep.AppendLine("light: the pre-baked _CabinTubeLM (" + LanbaiBusBuild.Tex + "Cabin_TubeLM.exr) on uv1 (D-32); the slice uses no Unity light map " +
                       "(static flags off; this scene has " + nLightmaps + "), so bus_slice.json has_lightmaps (scene.lightmaps >= 1) only warns");

        // 4. tube light only: the sandbox's default Directional Light (and any other light) would light the slice like day
        foreach (var li in UnityEngine.Object.FindObjectsOfType<Light>())
        {
            if (li == null || !li.enabled || li.gameObject.scene != root.scene || li.transform.IsChildOf(root.transform)) continue;
            Undo.RecordObject(li, "Bus slice: tube light only");
            li.enabled = false;
            rep.AppendLine("switched off light " + li.name + " (" + li.type + "): the slice is lit by _CabinTubeLM x _Udon_CabinLightmap; Undo or re-enable by hand");
        }

        // 5. the cabin globals (no LanbaiCabinDriver here): tubes 1, ambient 0, bleach 0, fade 0
        var gGo = new GameObject("Slice_Globals");
        gGo.transform.SetParent(root.transform, false);
        var globals = gGo.AddComponent<LanbaiBusSliceGlobals>();
        globals.Apply();
        rep.AppendLine("Slice_Globals: LanbaiBusSliceGlobals _Udon_CabinLightmap " + globals.tubes + ", _Udon_CabinAmbient " + Fmt(globals.ambientLinear) +
                       ", _Udon_CabinBleach.x " + globals.bleach + ", _Udon_CabinFade.x " + globals.fade + " (edit them on the component)");

        // 6. the camera at the hero eye, looking forward, with a PPv2 layer the test tool copies (camera_template)
        var camGo = new GameObject("Slice_Camera");
        camGo.transform.SetParent(root.transform, false);
        camGo.transform.localPosition = HeroEye;
        camGo.transform.localRotation = Quaternion.identity;
        var cam = camGo.AddComponent<Camera>();
        cam.fieldOfView = 2f * Mathf.Rad2Deg * Mathf.Atan(Mathf.Tan(0.5f * 90f * Mathf.Deg2Rad) / (16f / 9f));   // 90 deg horizontal at 16:9 = 58.7 vertical
        cam.nearClipPlane = 0.02f;
        cam.farClipPlane = 1000f;
        cam.allowHDR = true;
        cam.clearFlags = CameraClearFlags.SolidColor;               // no world outside the slice: the night road is black
        cam.backgroundColor = Color.black;
        cam.depth = 10f;                                            // over the sandbox's Main Camera in the Game view
        var ppl = camGo.AddComponent<PostProcessLayer>();
        ppl.volumeTrigger = camGo.transform;
        ppl.antialiasingMode = PostProcessLayer.Antialiasing.None;   // as the grading kit's reference camera (Grading/README_Grading.md)
        ppl.stopNaNPropagation = true;
        ppl.finalBlitToCameraTarget = false;
        int ppLayer = LayerMask.NameToLayer(PPLayerName);
        if (ppLayer >= 0) ppl.volumeLayer = 1 << ppLayer;
        else
        {
            warnings++;
            ppl.volumeLayer = 0;
            Debug.LogWarning(Tag + "layer " + PPLayerName + " missing: the PostProcessLayer's volume layer is Nothing (run 蓝白/Grades/Build Profiles & Volumes once, it adds the layer, then build again)");
            rep.AppendLine("WARNING: layer " + PPLayerName + " missing: volume layer = Nothing");
        }
        var res = FindPPResources();
        if (res != null)
        {
            var so = new SerializedObject(ppl);
            var sp = so.FindProperty("m_Resources");
            if (sp != null) { sp.objectReferenceValue = res; so.ApplyModifiedPropertiesWithoutUndo(); }
            ppl.Init(res);
        }
        else
        {
            errors++;
            rep.AppendLine("ERROR: PostProcessResources not found: the camera's PostProcessLayer has no resources");
            Debug.LogError(Tag + "PostProcessResources not found (is com.unity.postprocessing installed?): the camera's PostProcessLayer has no resources");
        }
        rep.AppendLine("Slice_Camera: " + Fmt(HeroEye) + " looking +Z, vertical FOV " + cam.fieldOfView.ToString("0.0") + " (90 horizontal at 16:9), near 0.02, HDR, PostProcessLayer volume layer " +
                       (ppLayer >= 0 ? PPLayerName : "Nothing") + ", resources " + (res != null));

        // 7. the night-road grade if the grading kit is in the project (otherwise PPv2 has nothing to do)
        var prof = FindProfile(GradeProfile);
        if (prof != null && ppLayer >= 0)
        {
            var vGo = new GameObject("Slice_Grade_S2");
            vGo.transform.SetParent(root.transform, false);
            vGo.layer = ppLayer;
            var vol = vGo.AddComponent<PostProcessVolume>();
            vol.isGlobal = true; vol.priority = 2f; vol.weight = 1f;
            vol.sharedProfile = prof;
            rep.AppendLine("Slice_Grade_S2: global volume, " + AssetDatabase.GetAssetPath(prof) + " (S2 night road), weight 1");
        }
        else
        {
            warnings++;
            rep.AppendLine("WARNING: no grade volume (" + GradeProfile + " " + (prof != null ? "found" : "not found") + ", layer " + PPLayerName + " " + (ppLayer >= 0) +
                           "): PPv2 has nothing to do, so the test's ppv2_effective (a gate when there are shots) fails; " +
                           "run 蓝白/Grades/Build Profiles & Volumes once and build again");
        }

        // the test tool copies the FIRST camera with a PostProcessLayer it meets (bus_slice.json has no camera_template):
        // the slice's root goes to the top of its scene, and anything that would still come first is reported
        root.transform.SetSiblingIndex(0);
        var firstPP = FirstPPCamera();
        if (firstPP != null && firstPP != cam)
        {
            warnings++;
            rep.AppendLine("WARNING: the test tool would copy the camera settings of " + firstPP.name + " (the first camera with a PostProcessLayer), not Slice_Camera");
        }

        Undo.RegisterCreatedObjectUndo(root, "Build bus slice");
        Undo.CollapseUndoOperations(undoGroup);
        EditorSceneManager.MarkSceneDirty(root.scene);              // the scene is not saved (the test tool's sandbox scene)
        // save only what this build wrote, and only under Generated/ (allowed_writes)
        var saved = new List<string>();
        foreach (var a in save.Distinct())
        {
            string p = AssetDatabase.GetAssetPath(a);
            if (string.IsNullOrEmpty(p)) continue;
            if (!p.StartsWith(GenDir + "/", StringComparison.Ordinal))
            {
                warnings++;
                rep.AppendLine("WARNING: not saved (outside " + GenDir + "): " + p);
                continue;
            }
            if (SaveIfDirty != null) SaveIfDirty.Invoke(null, new object[] { a });
            saved.Add(p);
        }
        if (SaveIfDirty == null && saved.Count > 0)
        {
            warnings++;
            AssetDatabase.SaveAssets();
            rep.AppendLine("WARNING: AssetDatabase.SaveAssetIfDirty not found (Unity older than 2021.2?): saved with AssetDatabase.SaveAssets, which also writes any other dirty asset");
        }
        Selection.activeGameObject = root;
        rep.AppendLine("writes: " + saved.Count + " asset(s) under " + GenDir + " (" + string.Join(", ", saved.Select(Path.GetFileName).ToArray()) +
                       "); nothing else" + (SaveIfDirty != null ? " (saved one by one, no AssetDatabase.SaveAssets)" : "") +
                       ": no UdonSharp program assets (Assets/Lanbai/UdonPrograms/, Assets/SerializedUdonPrograms/ are in bus_slice.json " +
                       "allowed_writes for the U# compiler, not for this menu), no import or project settings, the scene is not saved (no .unity)");
        string head = (errors > 0 ? "ERROR " : "OK ") + "built " + RootName + ": " + errors + " error(s), " + warnings + " warning(s)" +
                      (missing.Count > 0 ? ", missing in Bus.fbx: " + string.Join(", ", missing.ToArray()) : "");
        if (errors > 0) Debug.LogError(Tag + head + "\n" + rep);
        else if (warnings > 0) Debug.LogWarning(Tag + head + "\n" + rep);
        else Debug.Log(Tag + head + "\n" + rep);
        return head;
    }

    // ------------------------------------------------------------------------------------------------ uv1 = the light-map atlas
    // Lanbai/Cabin reads _CabinTubeLM with TEXCOORD1, and the FBX uv sets arrive in Unity in the order of the Blender
    // layers. finish_bus.lm_uv_order exports every Seat_* / Window_* / Pole_* as UVMap, UVLightmap, UVMetric: uv1 is
    // the atlas, inside 0..1, and this check only reports it (no copy, nothing written). GUARD for a Bus.fbx exported
    // before that fix (the D-36 seats were UVMap, UVMetric, UVLightmap: the metric chart in metres on uv1, the atlas on
    // uv2): then the slice uses a copy of the mesh with uv1 and uv2 swapped (Generated/Meshes) and warns; the full build
    // samples that FBX's light map wrong, so the fix is to re-export.
    static string LightmapUV(Renderer r, List<UnityEngine.Object> save, ref int errors, ref int warnings)
    {
        var mf = r.GetComponent<MeshFilter>();
        var mesh = mf != null ? mf.sharedMesh : null;
        if (mesh == null) { errors++; return "ERROR: no mesh"; }
        var uv1 = new List<Vector2>();
        var uv2 = new List<Vector2>();
        try { mesh.GetUVs(1, uv1); mesh.GetUVs(2, uv2); }
        catch (Exception ex) { warnings++; return "WARNING: could not read the uvs (" + ex.Message + "): uv1 not checked"; }
        if (uv1.Count == 0) { errors++; return "ERROR: no uv1: _CabinTubeLM would sample one texel"; }
        if (Inside01(uv1)) return "uv1 = the _CabinTubeLM atlas (inside 0..1)";
        if (uv2.Count != uv1.Count || !Inside01(uv2)) { errors++; return "ERROR: uv1 leaves 0..1 and uv2 is no atlas either: _CabinTubeLM is sampled wrong"; }
        string path = GenMeshDir + "/" + Safe(mesh.name) + "_uv1LM.asset";
        try
        {
            LanbaiBusBuild.EnsureFolder(GenMeshDir);
            var copy = UnityEngine.Object.Instantiate(mesh);
            copy.name = Path.GetFileNameWithoutExtension(path);
            copy.SetUVs(1, uv2);
            copy.SetUVs(2, uv1);
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing != null)
            {
                // re-run: the same asset (and GUID) gets the new data
                EditorUtility.CopySerialized(copy, existing); UnityEngine.Object.DestroyImmediate(copy); copy = existing;
                EditorUtility.SetDirty(copy);
            }
            else AssetDatabase.CreateAsset(copy, path);
            mf.sharedMesh = copy;
            save.Add(copy);
        }
        catch (Exception ex)
        {
            errors++;
            return "ERROR: uv1 is the metric chart (atlas on uv2) and the swapped copy failed (" + ex.Message + "): _CabinTubeLM is sampled wrong";
        }
        warnings++;
        string w = "WARNING: uv1 of " + mesh.name + " is the metric chart, the atlas is on uv2: this Bus.fbx was exported before finish_bus.lm_uv_order " +
                   "(uv order UVMap, UVMetric, UVLightmap). The slice uses " + path + " (uv1 <-> uv2); the full build 蓝白/Build/车 samples this FBX's " +
                   "light map wrong. Re-export Bus.fbx (Bus/README.md §5)";
        Debug.LogWarning(Tag + w);
        return w;
    }

    static bool Inside01(List<Vector2> uv)
    {
        const float e = 1e-3f;
        foreach (var v in uv) if (v.x < -e || v.x > 1f + e || v.y < -e || v.y > 1f + e) return false;
        return true;
    }

    // ------------------------------------------------------------------------------------------------ what gets counted
    // bus_slice.json settings.vertex_compression_off: TexCoord0..3 and Color. Read as the test tool reads it (bit = 1 <<
    // VertexAttribute): PlayerSettings.vertexChannelCompressionMask by reflection (not in the 2021.1 reference UnityEditor the
    // compile check uses), else the line 'VertexChannelCompressionMask: <n>' of ProjectSettings/ProjectSettings.asset.
    static readonly VertexAttribute[] VcNeedOff = { VertexAttribute.TexCoord0, VertexAttribute.TexCoord1, VertexAttribute.TexCoord2,
                                                    VertexAttribute.TexCoord3, VertexAttribute.Color };

    static int VertexCompressionMask(out string how)
    {
        try
        {
            var p = typeof(PlayerSettings).GetProperty("vertexChannelCompressionMask", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
            if (p != null) { how = "PlayerSettings.vertexChannelCompressionMask"; return Convert.ToInt32(p.GetValue(null, null)); }
        }
        catch (Exception) { }
        try
        {
            foreach (string line in File.ReadAllLines("ProjectSettings/ProjectSettings.asset"))
            {
                string s = line.Trim();
                int v;
                if (s.StartsWith("VertexChannelCompressionMask:", StringComparison.Ordinal) &&
                    int.TryParse(s.Substring("VertexChannelCompressionMask:".Length).Trim(), out v)) { how = "ProjectSettings.asset"; return v; }
            }
        }
        catch (Exception) { }
        how = "neither PlayerSettings nor ProjectSettings.asset";
        return -1;
    }

    // The shared makers (LanbaiBusBuild.CabinMat / GlassMat / PartMat / T) write one line per problem, once per renderer and
    // material. Each distinct line is counted once: a missing texture or a part type missing from BusLayout.json is an
    // ERROR (the slice would test a material without it), and so is 'unknown material X -> Alu values' (CabinMat then
    // gives the part Alu's values, metallic 1: a vinyl or enamel part would render as metal and spoil the look test);
    // everything else they report ('_CabinCube empty', ...) is a WARNING.
    static void CountShared(StringBuilder shared, StringBuilder rep, ref int errors, ref int warnings)
    {
        var seen = new HashSet<string>();
        foreach (string raw in shared.ToString().Split('\n'))
        {
            string s = raw.Trim();
            if (s.Length == 0 || !seen.Add(s)) continue;
            bool err = s.StartsWith("texture missing", StringComparison.Ordinal) || s.Contains("not in BusLayout.json parts") ||
                       s.StartsWith("unknown material", StringComparison.Ordinal) || s.StartsWith("MISSING SHADER", StringComparison.Ordinal);
            if (err) errors++; else warnings++;
            rep.AppendLine((err ? "ERROR (material): " : "WARNING (material): ") + s);
        }
    }

    // Import settings of the textures on the slice's materials: READ only (changing them writes .meta files outside
    // allowed_writes). Lanbai/Cabin unpacks _PartNormal / _DetailNormal with UnpackScaleNormal, so they must be Normal
    // maps (an sRGB colour import bends every normal; texture_compare's bc5 / ncrunch also key on the Normal map type);
    // masks, the tube light map and the rain-glass data are linear data; _CabinTubeLM is HDR (RGBAHalf, Cabin/README.md §5).
    static readonly string[] NormalProps = { "_PartNormal", "_DetailNormal" };
    static readonly string[] LinearProps = { "_PartMask", "_DetailMask", "_CabinTubeLM", "_BeadNormal", "_BeadData", "_RunnerFlow" };

    const string NormalFix = "Lanbai/Cabin unpacks it as a normal map (UnpackScaleNormal), so the normals come out bent, and texture_compare's bc5 / " +
                             "ncrunch only touch Normal-map textures. Set Texture Type = Normal map (Cabin/Editor/LanbaiCabinImport.cs does it on " +
                             "import for names with '_Normal'; with an older copy of that script, reimport after updating it, or set it by hand). " +
                             "This menu only reads import settings (writing them would change .meta files outside allowed_writes)";

    static void CheckImports(List<GameObject> groups, StringBuilder rep, ref int errors, ref int warnings)
    {
        var done = new HashSet<string>();
        var normalsSeen = new HashSet<string>();
        int n = 0;
        foreach (var g in groups)
            foreach (var r in g.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.sharedMaterials)
                {
                    if (m == null) continue;
                    foreach (string prop in NormalProps.Concat(LinearProps))
                    {
                        if (!m.HasProperty(prop)) continue;
                        var t = m.GetTexture(prop);
                        string p = t != null ? AssetDatabase.GetAssetPath(t) : null;
                        if (string.IsNullOrEmpty(p) || !done.Add(prop + "|" + p)) continue;
                        var ti = AssetImporter.GetAtPath(p) as TextureImporter;
                        if (ti == null) continue;
                        n++;
                        if (Array.IndexOf(NormalProps, prop) >= 0)
                        {
                            if (ti.textureType != TextureImporterType.NormalMap)
                            {
                                errors++;
                                rep.AppendLine("ERROR (import): " + p + " (" + prop + ", on the slice) is imported as " + ti.textureType + (ti.sRGBTexture ? ", sRGB" : "") +
                                               ", not as a Normal map: " + NormalFix);
                            }
                            normalsSeen.Add(p);
                        }
                        else if (ti.textureType != TextureImporterType.NormalMap && ti.sRGBTexture)
                        {
                            warnings++;
                            rep.AppendLine("WARNING (import): " + p + " (" + prop + ") is imported as sRGB; the shader reads linear data: untick sRGB (Color Texture)");
                        }
                        var t2 = t as Texture2D;
                        if (prop == "_CabinTubeLM" && t2 != null && t2.format != TextureFormat.RGBAHalf && t2.format != TextureFormat.RGBAFloat)
                        {
                            warnings++;
                            rep.AppendLine("WARNING (import): " + p + " is " + t2.format + ", not RGBAHalf: the tube light map is HDR (E above 1 near the tubes) " +
                                           "and its seams show every quantisation step (Cabin/README.md §5, LanbaiCabinImport)");
                        }
                    }
                }
        rep.AppendLine("import types: " + n + " texture(s) on the slice's materials checked (read only)");
        CheckPartNormals(normalsSeen, rep, ref errors);
    }

    // Every D-36 part normal map (Bus/Textures/Parts/Part_<type>_Normal_<res>.png), not only the slice's: the full bus uses
    // them all and they go through the same import rule. READ only; one ERROR per texture that is not a Normal map.
    static void CheckPartNormals(HashSet<string> alreadyReported, StringBuilder rep, ref int errors)
    {
        string dir = LanbaiBusBuild.Tex + "Parts";
        if (!AssetDatabase.IsValidFolder(dir))
        {
            rep.AppendLine("part normal maps: " + dir + " not found (the material makers report the missing textures)");
            return;
        }
        int n = 0, bad = 0;
        foreach (string g in AssetDatabase.FindAssets("t:Texture2D", new[] { dir }))
        {
            string p = AssetDatabase.GUIDToAssetPath(g);
            string f = Path.GetFileNameWithoutExtension(p);
            if (!f.StartsWith("Part_", StringComparison.Ordinal) || f.IndexOf("_Normal_", StringComparison.Ordinal) < 0) continue;
            var ti = AssetImporter.GetAtPath(p) as TextureImporter;
            if (ti == null) continue;
            n++;
            if (ti.textureType == TextureImporterType.NormalMap) continue;
            bad++;
            if (alreadyReported.Contains(p)) continue;                  // counted above (on the slice)
            errors++;
            rep.AppendLine("ERROR (import): " + p + " is imported as " + ti.textureType + (ti.sRGBTexture ? ", sRGB" : "") + ", not as a Normal map: " + NormalFix);
        }
        rep.AppendLine("part normal maps: " + n + " Part_*_Normal_* in " + dir + ", " + bad + " not imported as Normal map (read only)");
    }

    // as the test tool's camera template: the first camera (no target texture) with a PostProcessLayer, scenes and roots in order
    static Camera FirstPPCamera()
    {
        for (int i = 0; i < SceneManager.sceneCount; i++)
        {
            var sc = SceneManager.GetSceneAt(i);
            if (!sc.isLoaded) continue;
            foreach (var g in sc.GetRootGameObjects())
                foreach (var c in g.GetComponentsInChildren<Camera>(true))
                    if (c.targetTexture == null && c.GetComponent<PostProcessLayer>() != null) return c;
        }
        return null;
    }

    // ------------------------------------------------------------------------------------------------ PPv2 assets
    static PostProcessResources FindPPResources()
    {
        string p = AssetDatabase.GUIDToAssetPath(PPResourcesGuid);
        var r = string.IsNullOrEmpty(p) ? null : AssetDatabase.LoadAssetAtPath<PostProcessResources>(p);
        if (r != null) return r;
        foreach (string g in AssetDatabase.FindAssets("t:PostProcessResources"))
        {
            r = AssetDatabase.LoadAssetAtPath<PostProcessResources>(AssetDatabase.GUIDToAssetPath(g));
            if (r != null) return r;
        }
        return null;
    }

    static PostProcessProfile FindProfile(string name)
    {
        foreach (string g in AssetDatabase.FindAssets(name + " t:PostProcessProfile"))
        {
            string p = AssetDatabase.GUIDToAssetPath(g);
            if (Path.GetFileNameWithoutExtension(p) == name) return AssetDatabase.LoadAssetAtPath<PostProcessProfile>(p);
        }
        return null;
    }

    // ------------------------------------------------------------------------------------------------ helpers
    // AssetDatabase.SaveAssetIfDirty(Object) is in Unity 2022.3 (since 2021.2 / 2020.3.16) but not in the 2021.1
    // reference UnityEditor the compile check uses: found by reflection.
    static readonly MethodInfo SaveIfDirty = typeof(AssetDatabase).GetMethod("SaveAssetIfDirty", BindingFlags.Public | BindingFlags.Static,
                                                                             null, new[] { typeof(UnityEngine.Object) }, null);

    static bool Has(string[] a) { return a != null && a.Length > 0; }

    static string Fmt(Vector3 v) { return "(" + v.x.ToString("0.000") + ", " + v.y.ToString("0.000") + ", " + v.z.ToString("0.000") + ")"; }

    static string Safe(string s)
    {
        foreach (char c in Path.GetInvalidFileNameChars()) s = s.Replace(c, '_');
        return s;
    }

    static long Tris(Renderer r)
    {
        var mf = r.GetComponent<MeshFilter>();
        if (mf == null || mf.sharedMesh == null) return 0;
        long n = 0;
        for (int i = 0; i < mf.sharedMesh.subMeshCount; i++) n += (long)mf.sharedMesh.GetIndexCount(i) / 3;
        return n;
    }
}
#endif
