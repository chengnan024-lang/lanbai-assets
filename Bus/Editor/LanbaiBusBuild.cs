// Lanbai / 蓝白 -- 蓝白/Build/车 : builds the PAZ-672 bus and its cabin into the open scene (re-runnable).
// UNCOMPILED (cloud side): Roslyn type-check only (Common/Tools~/compile_check/check_cs.sh). Never run in Unity.
//
// Inputs (all under Assets/Lanbai/): Bus/Models/Bus.fbx, Bus/Models/BusLayout.json, Bus/Textures/*, Rain/Textures/Glass/*,
// shaders Lanbai/Cabin, Lanbai/ThinCloth (Cabin/), Lanbai/BusGlass (Rain/), scripts LanbaiCabinDriver (Cabin/Scripts),
// LanbaiWipers (Rain/Runtime, optional). UdonSharp, VRCStation and the two U# scripts are reached by REFLECTION, so this
// file compiles without the VRChat / UdonSharp editor assemblies; when one is missing the report says what to add by hand.
// What it does: Bus/Editor/README_Build.md.
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class LanbaiBusBuild
{
    // internal: shared with LanbaiBusSliceBuilder (蓝白/Build/车 切片, same folder / assembly)
    internal const string Root = "Assets/Lanbai/";
    internal const string FbxPath = Root + "Bus/Models/Bus.fbx";
    internal const string LayoutPath = Root + "Bus/Models/BusLayout.json";
    internal const string MatDir = Root + "Bus/Materials";
    const string ProgDir = Root + "Bus/Programs";
    internal const string Tex = Root + "Bus/Textures/";
    const string RainGlass = Root + "Rain/Textures/Glass/";
    const string RootName = "Lanbai_Bus";

    // ------------------------------------------------------------------------------------------------ BusLayout.json
    [Serializable] public class Seat { public string name; public bool hero; public float x; public float cushion_y; public float back_z; public float[] station_pos; public float[] eye_approx; }
    [Serializable] public class Col { public string name; public float[] c; public float[] s; }
    [Serializable] public class Pose { public float[] position; public float yaw_deg; }
    [Serializable] public class DoorPanel { public string name; public Pose open; public Pose closed; }
    [Serializable] public class FillLight { public float[] pos; public string colour; }
    [Serializable] public class BusBox { public float[] bounds_min; public float[] bounds_max; }
    [Serializable] public class PartInfo { public string type; public int res; public float metres_per_uv; public string[] instances; }
    [Serializable] public class Layout
    {
        public float[] eye_hero; public float floor_y;
        public Seat[] seats; public Col[] colliders; public DoorPanel[] door_panels; public FillLight[] head_fill_lights; public BusBox bus;
        public PartInfo[] parts;
    }

    // ------------------------------------------------------------------------------------------------ materials
    // Copied from Bus/Source/build_bus.py MAT_TABLE (= bible §4.2 / §4.9): Blender name M_Bus_<key> -> (sRGB, smoothness, metallic)
    static readonly Dictionary<string, object[]> MatTable = new Dictionary<string, object[]>
    {
        { "Ext_Indigo", new object[] { "#34506E", 0.50f, 0f } }, { "Ext_Cream", new object[] { "#D8D2C2", 0.55f, 0f } },
        { "Ext_Silver", new object[] { "#BFC2C4", 0.70f, 1f } }, { "Ext_Black", new object[] { "#26272A", 0.40f, 0f } },
        { "Tyre", new object[] { "#2A2A2A", 0.55f, 0f } }, { "Rim", new object[] { "#D8D2C2", 0.45f, 0f } },
        { "Chrome", new object[] { "#CFD1D3", 0.85f, 1f } }, { "Lamp_Head", new object[] { "#EBE2CF", 0.90f, 0f } },
        { "Lamp_Tail", new object[] { "#8A1A1E", 0.80f, 0f } }, { "Lamp_Amber", new object[] { "#E3D69B", 0.80f, 0f } },
        { "ButtonRed", new object[] { "#8A1A1E", 0.55f, 0f } },
        { "Int_Enamel", new object[] { "#D9D4C5", 0.45f, 0f } }, { "Int_Ceiling", new object[] { "#E2DDCF", 0.25f, 0f } },
        { "Seal", new object[] { "#2B2B2B", 0.30f, 0f } }, { "Vinyl", new object[] { "#5A2126", 0.45f, 0f } },
        { "SeatFrame", new object[] { "#3C3E3D", 0.35f, 0f } }, { "Floor", new object[] { "#323634", 0.22f, 0f } },
        { "Alu", new object[] { "#B8BBBD", 0.45f, 1f } }, { "SafetyYellow", new object[] { "#C9A227", 0.40f, 0f } },
        { "Steel", new object[] { "#C0C3C4", 0.55f, 1f } }, { "TubeDiffuser", new object[] { "#D8DBD6", 0.60f, 0f } },
        { "Dash", new object[] { "#353637", 0.30f, 0f } }, { "Bakelite", new object[] { "#2E2E2E", 0.45f, 0f } },
        { "RadioLeather", new object[] { "#4A2E1F", 0.45f, 0f } }, { "RadioGrille", new object[] { "#B8BBBD", 0.55f, 1f } },
        { "RadioDial", new object[] { "#E8DFC8", 0.50f, 0f } }, { "Curtain", new object[] { "#A9BCCB", 0.18f, 0f } },
        { "Linen", new object[] { "#262626", 0.10f, 0f } }, { "Glass", new object[] { "#E9EFEA", 0.97f, 0f } },
    };

    internal enum Mode { CabinLM, Cabin, ExteriorAtlas, Exterior }

    static StringBuilder _rep;
    static Dictionary<string, PartInfo> _parts = new Dictionary<string, PartInfo>();
    const string PartTex = Tex + "Parts/";

    // D-41：菜单先建三个 U# 程序资产（ProgDir）、等 SDK 初始化完，再搭（Common/Editor/LanbaiUdonPrograms）
    static readonly string[] UdonScripts = { "LanbaiBusSeat", "LanbaiCabinDriver", "LanbaiWipers" };

    // for LanbaiBusSliceBuilder: the report the material makers write into, and the D-36 part table PartMat reads
    // (Build() sets both itself)
    internal static void BeginShared(StringBuilder rep, Layout L)
    {
        _rep = rep;
        _parts = new Dictionary<string, PartInfo>();
        if (L != null && L.parts != null) foreach (var pi in L.parts) _parts[pi.type] = pi;
    }

    // which Lanbai/Cabin variant an FBX object gets. Window_* / Pole_* are the D-40 #1 slice pieces that finish_bus.py
    // now exports on their own (Window_R1, Pole_R0): they were part of Cabin_Static and stay on its tube light map.
    internal static Mode ModeFor(string n)
    {
        return n == "Cabin_Static" || n.StartsWith("Seat_") || n.StartsWith("Window_") || n.StartsWith("Pole_") ? Mode.CabinLM  // D-36 seats share the LM atlas
             : n.StartsWith("Cabin_") || n.StartsWith("Bus_Door") ? Mode.Cabin
             : n.StartsWith("Bus_Exterior") ? Mode.ExteriorAtlas
             : Mode.Exterior;                                  // wheels, wipers
    }

    [MenuItem("蓝白/Build/车")]
    public static void BuildMenu()
    {
        var types = UdonScripts.Select(Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript).Where(t => t != null).ToArray();
        Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("蓝白/Build/车", types, Build, t => ProgDir + "/" + t.Name + ".asset");
    }

    public static void Build()
    {
        foreach (var sn in UdonScripts)
        {
            var st = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript(sn);
            if (st != null) Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Build/车", st);
        }
        _rep = new StringBuilder();
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath);
        if (fbx == null) { Debug.LogError("[Lanbai Bus] not found: " + FbxPath); return; }
        var layoutText = AssetDatabase.LoadAssetAtPath<TextAsset>(LayoutPath);
        if (layoutText == null) { Debug.LogError("[Lanbai Bus] not found: " + LayoutPath); return; }
        Layout L = JsonUtility.FromJson<Layout>(layoutText.text);
        _parts = new Dictionary<string, PartInfo>();
        if (L.parts != null) foreach (var pi in L.parts) _parts[pi.type] = pi;

        // 1. delete the previous build
        var old = GameObject.Find(RootName);
        while (old != null) { Undo.DestroyObjectImmediate(old); old = GameObject.Find(RootName); }
        EnsureFolder(MatDir); EnsureFolder(ProgDir);

        // 2. the FBX under Lanbai_Bus at the origin (unpacked: we add components and a LOD parent)
        var root = new GameObject(RootName);
        Undo.RegisterCreatedObjectUndo(root, "Build bus");
        var model = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        PrefabUtility.UnpackPrefabInstance(model, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        model.transform.SetParent(root.transform, false);
        model.transform.localPosition = Vector3.zero; model.transform.localRotation = Quaternion.identity; model.transform.localScale = Vector3.one;

        // 2b. door panes ride with their leaves (finish_bus.py exports Glass_DoorK separately: BusGlass, not Lanbai/Cabin)
        for (int k = 0; k < 4; k++)
        {
            var leaf = FindDeep(model.transform, "Bus_Door" + k); var pane = FindDeep(model.transform, "Glass_Door" + k);
            if (leaf != null && pane != null) pane.SetParent(leaf, true);
        }

        // 3. materials
        Shader cabin = Shader.Find("Lanbai/Cabin"), cloth = Shader.Find("Lanbai/ThinCloth"), glass = Shader.Find("Lanbai/BusGlass");
        if (cabin == null || cloth == null || glass == null) _rep.AppendLine("MISSING SHADER: Lanbai/Cabin " + (cabin != null) + ", ThinCloth " + (cloth != null) + ", BusGlass " + (glass != null));
        var glassRenderers = new List<Renderer>();
        var cabinRenderers = new List<Renderer>();
        Renderer curtains = null;
        foreach (var r in model.GetComponentsInChildren<Renderer>(true))
        {
            string n = r.gameObject.name;
            if (n.StartsWith("Glass_"))
            {
                r.sharedMaterial = GlassMat(glass, n);
                r.shadowCastingMode = ShadowCastingMode.Off;
                glassRenderers.Add(r);
                continue;
            }
            if (n == "Cabin_Curtains")
            {
                r.sharedMaterials = r.sharedMaterials.Select(m => ClothMat(cloth)).ToArray();
                curtains = r;
                continue;
            }
            Mode mode = ModeFor(n);
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++) mats[i] = CabinMat(cabin, mats[i] != null ? mats[i].name : "Alu", mode);
            r.sharedMaterials = mats;
            cabinRenderers.Add(r);
            // no Unity lightmapping on the bus (the tube light is _CabinTubeLM, baked in Blender)
            GameObjectUtility.SetStaticEditorFlags(r.gameObject, 0);
            r.reflectionProbeUsage = ReflectionProbeUsage.BlendProbes;
        }
        // render layers (bible §1.6 / §4.3): the cabin, its glass and the curtains on Bus (world key light, sodium sweep,
        // Act07 lights cull to it); the outside skin, wheels and wipers on BusExterior (the stop lamp in acts 1 and 12)
        int layerBus = LayerMask.NameToLayer("Bus"), layerExt = LayerMask.NameToLayer("BusExterior");
        if (layerBus < 0 || layerExt < 0) _rep.AppendLine("WARNING: layer Bus (" + layerBus + ") / BusExterior (" + layerExt + ") missing: add them in Project Settings > Tags and Layers and build again (README §1)");
        int nBus = 0, nExt = 0;
        foreach (var r in model.GetComponentsInChildren<Renderer>(true))
        {
            string n = r.gameObject.name;
            bool ext = n.StartsWith("Bus_Exterior") || n.StartsWith("Wheel_") || n.StartsWith("Wiper");
            int l = ext ? layerExt : layerBus;
            if (l < 0) continue;
            r.gameObject.layer = l;
            if (ext) nExt++; else nBus++;
        }
        _rep.AppendLine("layers: Bus " + nBus + " renderers, BusExterior " + nExt);
        _rep.AppendLine("materials -> " + MatDir + "; glass panes " + glassRenderers.Count + "; Lanbai/Cabin renderers " + cabinRenderers.Count + "; curtains " + (curtains != null));

        // 4. exterior LODGroup (CONTROL §6 pitfall 4: the importer does not group <name>_LOD0/1)
        var lod0 = FindDeep(model.transform, "Bus_Exterior_LOD0");
        var lod1 = FindDeep(model.transform, "Bus_Exterior_LOD1");
        if (lod0 != null && lod1 != null)
        {
            var lodGo = new GameObject("Bus_Exterior");
            lodGo.transform.SetParent(model.transform, false);
            lod0.SetParent(lodGo.transform, true); lod1.SetParent(lodGo.transform, true);
            var lg = lodGo.AddComponent<LODGroup>();
            lg.SetLODs(new LOD[] {
                new LOD(0.12f, lod0.GetComponentsInChildren<Renderer>()),
                new LOD(0.005f, lod1.GetComponentsInChildren<Renderer>()) });
            lg.RecalculateBounds();
            _rep.AppendLine("LODGroup Bus_Exterior: LOD0 > 12 % screen height, LOD1 > 0.5 %");
        }
        else _rep.AppendLine("WARNING: Bus_Exterior_LOD0 / LOD1 not found");

        // 5. seats (VRCStation) and colliders
        var seatRoot = new GameObject("Seats"); seatRoot.transform.SetParent(root.transform, false);
        var seatCentres = new List<Vector3>();
        Type stationType = FindType("VRC.SDK3.Components.VRCStation");
        if (L.seats != null)
            foreach (var s in L.seats)
            {
                Vector3 p = V(s.station_pos);
                seatCentres.Add(new Vector3(s.x, s.cushion_y, s.back_z + 0.25f));
                var go = new GameObject("Station_" + s.name + (s.hero ? "_HERO" : ""));
                go.transform.SetParent(seatRoot.transform, false);
                go.transform.localPosition = p;                               // facing +Z (identity)
                var bc = go.AddComponent<BoxCollider>();                      // the interact target
                bc.isTrigger = true; bc.center = new Vector3(0f, 0.15f, -0.1f); bc.size = new Vector3(0.45f, 0.3f, 0.45f);
                var enter = new GameObject("Enter"); enter.transform.SetParent(go.transform, false);
                if (stationType != null)
                {
                    var st = go.AddComponent(stationType);
                    var so = new SerializedObject(st);
                    SetRef(so, "stationEnterPlayerLocation", enter.transform);
                    SetRef(so, "stationExitPlayerLocation", enter.transform);
                    SetInt(so, "PlayerMobility", 1);                          // Immobilize
                    SetBool(so, "seated", true);
                    so.ApplyModifiedPropertiesWithoutUndo();
                    // the sit interaction (review r1 #6): Bus/Scripts/LanbaiBusSeat.cs, Interact -> UseStation
                    string sr = AddUdonSharp(go, "LanbaiBusSeat");
                    var seatB = go.GetComponent("LanbaiBusSeat");
                    if (seatB != null)
                    {
                        var sso = new SerializedObject(seatB);
                        SetRef(sso, "station", st);
                        sso.ApplyModifiedPropertiesWithoutUndo();
                        InteractText(seatB, "坐下", 2f);
                    }
                    else if (s.hero) _rep.AppendLine("  LanbaiBusSeat: " + sr);
                }
            }
        if (stationType == null) _rep.AppendLine("WARNING: VRCStation type not found (VRChat SDK?): stations not added, only their transforms");
        _rep.AppendLine("seats " + seatCentres.Count + " (hero = the one named *_HERO)");

        var colRoot = new GameObject("Colliders"); colRoot.transform.SetParent(root.transform, false);
        if (L.colliders != null)
            foreach (var c in L.colliders)
            {
                var go = new GameObject(c.name); go.transform.SetParent(colRoot.transform, false);
                var bc = go.AddComponent<BoxCollider>(); bc.center = V(c.c); bc.size = V(c.s);
            }

        // 6. head-fill lights (bible §4.3: Not Important, culling Player + PlayerLocal, #E4F1F3; x _Udon_CabinLightmap via LB_Journey.cabinLights)
        var lightRoot = new GameObject("HeadFill"); lightRoot.transform.SetParent(root.transform, false);
        int playerMask = LayerMask.GetMask("Player", "PlayerLocal");
        if (L.head_fill_lights != null)
            for (int i = 0; i < L.head_fill_lights.Length; i++)
            {
                var hl = L.head_fill_lights[i];
                var go = new GameObject("HeadFill_" + i); go.transform.SetParent(lightRoot.transform, false);
                go.transform.localPosition = V(hl.pos);
                var li = go.AddComponent<Light>();
                li.type = LightType.Point; li.renderMode = LightRenderMode.ForceVertex; li.shadows = LightShadows.None;
                li.color = Hex(string.IsNullOrEmpty(hl.colour) ? "#E4F1F3" : hl.colour);
                li.intensity = 0.5f; li.range = 6.0f; li.lightmapBakeType = LightmapBakeType.Realtime;   // range 6: one lamp per tube row reaches both ends of the 7.1 m cabin (calibrate on the #585F64 grey card)
                li.cullingMask = playerMask;
            }
        if (playerMask == 0) _rep.AppendLine("WARNING: layers Player / PlayerLocal not found: set the head-fill culling by hand");

        // 7. the cabin driver (+ program asset, pitfall 11)
        var drvGo = new GameObject("LanbaiCabinDriver"); drvGo.transform.SetParent(root.transform, false);
        _rep.AppendLine("LanbaiCabinDriver: " + AddUdonSharp(drvGo, "LanbaiCabinDriver"));
        var drv = drvGo.GetComponent("LanbaiCabinDriver");
        if (drv != null)
        {
            var so = new SerializedObject(drv);
            SetRefs(so, "cabinRenderers", cabinRenderers.Cast<UnityEngine.Object>().ToList());
            SetRefs(so, "curtainRenderers", curtains != null ? new List<UnityEngine.Object> { curtains } : new List<UnityEngine.Object>());
            SetRefs(so, "glassRenderers", glassRenderers.Cast<UnityEngine.Object>().ToList());
            SetVec3s(so, "seatCentres", seatCentres);
            if (L.seats != null) { var h = L.seats.FirstOrDefault(x => x.hero); if (h != null) SetVec3(so, "heroSeat", new Vector3(h.x, h.cushion_y, h.back_z + 0.25f)); }
            var doors = new List<UnityEngine.Object>(); var dpos = new List<Vector3>(); var dyaw = new List<float>();
            if (L.door_panels != null)
                foreach (var d in L.door_panels)
                {
                    var t = FindDeep(model.transform, d.name);
                    if (t == null || d.closed == null) continue;
                    doors.Add(t); dpos.Add(V(d.closed.position)); dyaw.Add(d.closed.yaw_deg);
                }
            SetRefs(so, "doorPanels", doors); SetVec3s(so, "doorClosedPos", dpos); SetFloats(so, "doorClosedYaw", dyaw);
            var journey = UnityEngine.Object.FindObjectsOfType<MonoBehaviour>().FirstOrDefault(m => m != null && m.GetType().Name == "LB_Journey");
            if (journey != null) SetRef(so, "journey", journey);
            else _rep.AppendLine("  LB_Journey not in the scene: fill LanbaiCabinDriver.journey by hand (act 4 flicker hook)");
            so.ApplyModifiedPropertiesWithoutUndo();
            _rep.AppendLine("  refs: " + cabinRenderers.Count + " cabin, " + glassRenderers.Count + " glass, " + doors.Count + " doors, " + seatCentres.Count + " seats");
        }

        // 8. wipers (Rain/Runtime/LanbaiWipers.cs, if present)
        var pl = FindDeep(model.transform, "WiperPivot_L"); var pr = FindDeep(model.transform, "WiperPivot_R");
        if (AssetDatabase.LoadAssetAtPath<MonoScript>(Root + "Rain/Runtime/LanbaiWipers.cs") != null && pl != null && pr != null)
        {
            var wGo = new GameObject("LanbaiWipers"); wGo.transform.SetParent(root.transform, false);
            _rep.AppendLine("LanbaiWipers: " + AddUdonSharp(wGo, "LanbaiWipers"));
            var w = wGo.GetComponent("LanbaiWipers");
            if (w != null)
            {
                var so = new SerializedObject(w);
                SetRefs(so, "pivot", new List<UnityEngine.Object> { pl, pr });
                so.ApplyModifiedPropertiesWithoutUndo();
            }
        }
        else _rep.AppendLine("wipers: LanbaiWipers.cs or WiperPivot_L/_R missing -> not hooked (README_Build.md)");

        AssetDatabase.SaveAssets();
        Selection.activeGameObject = root;
        Debug.Log("[Lanbai Bus] built " + RootName + "\n" + _rep);
    }

    // ------------------------------------------------------------------------------------------------ material makers
    // folder: where the .mat goes (null = Bus/Materials, the full build; the slice passes Bus/Generated/Materials)
    internal static Material GetOrCreate(string name, Shader sh, string folder = null)
    {
        string path = (folder ?? MatDir) + "/" + name + ".mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null) { m = new Material(sh != null ? sh : Shader.Find("Standard")); AssetDatabase.CreateAsset(m, path); }
        else if (sh != null && m.shader != sh) m.shader = sh;
        return m;
    }

    internal static Material CabinMat(Shader sh, string importedName, Mode mode, string folder = null)
    {
        string key = importedName.Replace(" (Instance)", "");
        if (key.StartsWith("M_Bus_")) key = key.Substring(6);
        int dot = key.IndexOf('.'); if (dot > 0) key = key.Substring(0, dot);          // Blender duplicates: Vinyl.001
        object[] v;
        bool part = key.StartsWith("Part_");                            // D-36 part atlas (Bus/Textures/Parts)
        if (part) v = MatTable["Vinyl"];
        else if (!MatTable.TryGetValue(key, out v)) { _rep.AppendLine("  unknown material " + importedName + " -> Alu values"); v = MatTable["Alu"]; }
        string suffix = mode == Mode.CabinLM ? "" : mode == Mode.Cabin ? "_NoLM" : mode == Mode.ExteriorAtlas ? "_ExtAtlas" : "_Ext";
        var m = GetOrCreate("M_Bus_" + key + suffix, sh, folder);
        m.SetColor("_Color", Hex((string)v[0]));
        m.SetFloat("_Glossiness", (float)v[1]);
        m.SetFloat("_Metallic", (float)v[2]);
        bool lm = mode == Mode.CabinLM;
        m.SetFloat("_UseTubeLM", lm ? 1f : 0f);
        m.SetTexture("_CabinTubeLM", lm ? T(Tex + "Cabin_TubeLM.exr") : null);
        bool inCabin = mode == Mode.CabinLM || mode == Mode.Cabin;
        m.SetFloat("_CabinLight", inCabin ? 1f : 0f);
        m.SetFloat("_SHAmbientK", inCabin ? 0f : 1f);                  // outside: Unity's Trilight is the ambient
        m.SetVector("_TubeLMConst", new Vector4(0.6f, 0.66f, 0.68f, 1f));   // linear: SetVector, no gamma step
        bool atlas = mode == Mode.ExteriorAtlas;
        m.SetFloat("_UseAtlas", atlas ? 1f : 0f);
        if (atlas)
        {
            m.SetColor("_Color", Color.white);                         // the atlas carries the colour
            m.SetTexture("_AtlasAlbedo", T(Tex + "Bus_Exterior_Albedo_2048.png"));
            m.SetTexture("_AtlasMask", T(Tex + "Bus_Exterior_Mask_2048.png"));
        }
        // defaults, then the bible §4.2 specifics (Cabin/README.md §2)
        m.SetFloat("_EmitMode", 0f); m.SetFloat("_DetailNormalScale", 0f); m.SetTexture("_DetailNormal", null); m.SetTexture("_DetailMask", null);
        m.SetFloat("_WearAmount", 0f); m.SetFloat("_SunFadeAmount", 0f); m.SetFloat("_CrackAmount", 0f);
        m.SetVector("_HeightSmooth", new Vector4(1.62f, 2.42f, 0.80f, 0f)); m.SetFloat("_FadeResist", 0f);
        m.SetVector("_MaskAlbedoMul", new Vector4(1, 1, 1, 0)); m.SetVector("_MaskSmoothAdd", Vector4.zero);
        m.SetFloat("_WetDarken", 1f);
        m.SetFloat("_GrimeAmount", 0f); m.SetFloat("_GrimeAbsolute", 0f);
        switch (key)
        {
            case "Vinyl":
                // CC0 scanned leather (Poly Haven leather_red_03, 30 cm tile): its normal only; colour stays the bible's
                Detail(m, "Cabin_SeatLeather_N_0.30m.jpg", 0.35f, 0.30f, null);
                m.SetColor("_WearColor", Hex("#6A3434")); m.SetFloat("_WearSmooth", 0.66f); m.SetFloat("_WearAmount", 1f);
                m.SetColor("_SunFadeColor", Hex("#7A4A48")); m.SetFloat("_SunFadeSmooth", 0.40f); m.SetFloat("_SunFadeAmount", 1f);
                m.SetColor("_CrackColor", Hex("#8A6A60")); m.SetFloat("_CrackSmooth", 0.20f); m.SetFloat("_CrackAmount", 1f);
                break;
            case "SeatFrame":
                m.SetColor("_WearColor", Hex("#3C3E3D")); m.SetFloat("_WearSmooth", 0.50f); m.SetFloat("_WearAmount", 1f); break;
            case "Floor":
                Detail(m, "Cabin_FloorStud_N_0.20m.png", 1f, 0.20f, "Cabin_FloorStud_M_0.20m.png");
                m.SetColor("_GrimeColor", Hex("#555550")); m.SetFloat("_GrimeAbsolute", 1f); m.SetFloat("_GrimeAmount", 1f);   // corner dust, lighter than the floor (bible §1.6)
                m.SetVector("_MaskAlbedoMul", new Vector4(1f, 1.6f, 0.92f, 0f)); m.SetVector("_MaskSmoothAdd", new Vector4(0.05f, -0.05f, 0f, 0f));
                m.SetColor("_WearColor", Hex("#4A4B47")); m.SetFloat("_WearSmooth", 0.35f); m.SetFloat("_WearAmount", 1f);
                m.SetFloat("_WetDarken", 0.8f); break;
            case "Int_Ceiling":
                Detail(m, "Cabin_CeilingPerf_N_0.12m.png", 1f, 0.12f, "Cabin_CeilingPerf_M_0.12m.png");
                m.SetColor("_GrimeColor", Hex("#D8CBA6")); m.SetFloat("_GrimeAbsolute", 1f); m.SetFloat("_GrimeAmount", 1f);   // yellowed round the tubes (vertex R); absolute so it stays <= sRGB 231 (bible §1.6)
                m.SetVector("_MaskAlbedoMul", new Vector4(0.15f, 1f, 1f, 0f)); break;
            case "Int_Enamel":
                m.SetColor("_GrimeColor", Hex("#8C8370")); m.SetFloat("_GrimeAmount", 1f);
                m.SetColor("_WearColor", Hex("#5B5A55")); m.SetFloat("_WearSmooth", 0.35f); m.SetFloat("_WearAmount", 1f); break;
            case "Steel":
                m.SetVector("_HeightSmooth", new Vector4(1.62f, 2.42f, 0.80f, 1f)); m.SetFloat("_FadeResist", 0.3f); break;
            case "TubeDiffuser":
                m.SetFloat("_EmitMode", 1f); m.SetVector("_EmissionColor", new Vector4(1.632f, 2.024f, 2.042f, 1f)); m.SetFloat("_BugDots", 1f); break;
            case "Dash":       // textured vinyl dash (CC0 leather normal, finer), hands' wear on the edge (vertex G)
                Detail(m, "Cabin_SeatLeather_N_0.30m.jpg", 0.4f, 0.15f, null);
                m.SetColor("_WearColor", Hex("#3E3F40")); m.SetFloat("_WearSmooth", 0.45f); m.SetFloat("_WearAmount", 1f);
                m.SetColor("_GrimeColor", Hex("#6A6355")); m.SetFloat("_GrimeAmount", 1f); break;
            case "Alu":        // window frames: dust / a little corrosion in the corners (vertex R)
                m.SetColor("_GrimeColor", Hex("#6B5A48")); m.SetFloat("_GrimeAmount", 1f); break;
            case "Bakelite":
                m.SetColor("_WearColor", Hex("#2E2E2E")); m.SetFloat("_WearSmooth", 0.72f); m.SetFloat("_WearAmount", 1f); break;
            case "RadioLeather":
                Detail(m, "Cabin_RadioLeather_N_0.40m.jpg", 0.6f, 0.40f, null);   // CC0 Poly Haven brown_leather, 40 cm tile
                m.SetColor("_WearColor", Hex("#4A2E1F")); m.SetFloat("_WearSmooth", 0.60f); m.SetFloat("_WearAmount", 1f); break;
            case "Lamp_Tail":     // bible 4.9: screen #B2252C (fill #CB1500); constant emission (gauge mode, white _EmitTex)
                m.SetFloat("_EmitMode", 3f); m.SetTexture("_EmitTex", Texture2D.whiteTexture);
                m.SetVector("_EmissionColor", Lin(Hex("#CB1500"), 1f)); break;
            case "Lamp_Head":     // bible 4.9: halogen 3200 K #FFC47A, the headlights are on ('this is what is uncanny')
                m.SetFloat("_EmitMode", 3f); m.SetTexture("_EmitTex", Texture2D.whiteTexture);
                m.SetVector("_EmissionColor", Lin(Hex("#FFC47A"), 4f)); break;   // x4 in linear, not in sRGB
            case "RadioDial":
                var dial = T(Tex + "Cabin_RadioDial_512x256.png");
                m.SetColor("_Color", Color.white); m.SetTexture("_MainTex", dial); m.SetTexture("_EmitTex", dial); m.SetFloat("_EmitMode", 2f); break;
            case "Linen":
                var letters = FindTexture("Bus_DestBlind_1024x296");   // the lettered one (not ..._Blank_..., act 11)
                if (letters != null) { m.SetFloat("_EmitMode", 4f); m.SetTexture("_EmitTex", letters); m.SetVector("_EmissionColor", new Vector4(2.22f, 2.283f, 2.178f, 1f)); }
                else _rep.AppendLine("  destination blind: no *DestBlind* letters texture in Bus/Textures -> no backlit letters yet");
                break;
        }
        m.SetFloat("_UsePart", 0f);
        if (part) PartMat(m, key.Substring(5));
        EditorUtility.SetDirty(m);
        return m;
    }

    static Material ClothMat(Shader sh)
    {
        var m = GetOrCreate("M_Bus_Curtain_Cloth", sh);
        m.SetColor("_Color", Hex("#A9BCCB")); m.SetColor("_HemColor", Hex("#8898A8")); m.SetFloat("_Glossiness", 0.18f);
        m.SetTexture("_WeaveNormal", T(Tex + "Cabin_CurtainWeave_N_0.05m.png")); m.SetFloat("_WeaveScale", 0.3f); m.SetFloat("_WeaveTile", 20f);
        m.SetFloat("_Inward", 0f);
        EditorUtility.SetDirty(m);
        return m;
    }

    // Rain/README_Rain.md §5.2: windscreen (face wind + wipers), skylight (horizontal beads, alpha 0.08), everything else
    // (side, roof-slope, rear, brow, destination window, door panes) vertical beads, alpha 0.06.
    internal static Material GlassMat(Shader sh, string pane, string folder = null)
    {
        string kind = pane.StartsWith("Glass_Windscreen") ? "Windscreen" : pane == "Glass_Skylight" ? "Skylight" : "Side";
        var m = GetOrCreate("M_Bus_Glass_" + kind, sh, folder);
        bool horiz = kind == "Skylight";
        string o = horiz ? "Horizontal" : "Vertical";
        m.SetTexture("_BeadNormal", T(RainGlass + "RainBeads_" + o + "_Normal_1024.png"));
        m.SetTexture("_BeadData", T(RainGlass + "RainBeads_" + o + "_Data_1024.png"));
        m.SetTexture("_RunnerFlow", T(RainGlass + "GlassRunners_Flow_512x1024.png"));
        m.SetFloat("_BaseAlpha", horiz ? 0.08f : 0.06f);
        m.SetFloat("_PaneFaceWind", kind == "Windscreen" ? 1f : 0f);
        m.SetFloat("_Wipers", kind == "Windscreen" ? 1f : 0f);
        m.SetFloat("_RainOverride", -1f);
        m.SetColor("_BehindColour", Color.black); m.SetFloat("_BehindLight", 0f);
        m.SetVector("_CabinBoxMin", new Vector4(-1.37f, 0.62f, -3.60f, 0f));     // inner cabin (BusLayout colliders)
        m.SetVector("_CabinBoxMax", new Vector4(1.01f, 2.62f, 3.44f, 0f));
        m.SetVector("_CabinProbePos", new Vector4(0.55f, 1.70f, 2.05f, 0f));     // bake the cabin cube at the hero eye
        if (m.GetTexture("_CabinCube") == null) _rep.AppendLine("  " + m.name + ": _CabinCube empty (bake the cabin cubemap, tubes on, and assign it)");
        EditorUtility.SetDirty(m);
        return m;
    }

    // D-36: the part's baked atlas on uv0 (albedo x _Color, normal, mask R metal G smooth B wear A AO); the thirty years
    // are in the bake, so the vertex-colour wear / fade / crack layers are off; the scanned grain tiles on top.
    internal static void PartMat(Material m, string ptype)
    {
        PartInfo pi;
        if (!_parts.TryGetValue(ptype, out pi)) { _rep.AppendLine("  part " + ptype + ": not in BusLayout.json parts"); return; }
        string b = PartTex + "Part_" + ptype + "_";
        m.SetFloat("_UsePart", 1f);
        m.SetColor("_Color", Color.white);
        m.SetTexture("_PartAlbedo", T(b + "Albedo_" + pi.res + ".png"));
        m.SetTexture("_PartNormal", T(b + "Normal_" + pi.res + ".png"));
        m.SetTexture("_PartMask", T(b + "Mask_" + pi.res + ".png"));
        m.SetFloat("_PartNormalScale", 1f);
        // the atlas is the same for every seat of a type; the per-seat wear is in the vertex colours (finish_bus.seat_wear):
        // G polish where people sit, B window sun-fade, R grime in the crease
        m.SetColor("_WearColor", Hex("#6A3434")); m.SetFloat("_WearSmooth", 0.66f); m.SetFloat("_WearAmount", 0.8f);
        m.SetColor("_SunFadeColor", Hex("#7A4A48")); m.SetFloat("_SunFadeSmooth", 0.40f); m.SetFloat("_SunFadeAmount", 0.8f);
        m.SetColor("_GrimeColor", Hex("#5B524A")); m.SetFloat("_GrimeAbsolute", 1f); m.SetFloat("_GrimeAmount", 0.5f);
        m.SetColor("_CrackColor", Hex("#8A6A60")); m.SetFloat("_CrackSmooth", 0.20f); m.SetFloat("_CrackAmount", 1f);   // bible 4.2 seam cracks: atlas mask B x vertex alpha (2-5 per seat)
        Detail(m, "Cabin_SeatLeather_N_0.30m.jpg", 0.30f, 0.30f / Mathf.Max(pi.metres_per_uv, 0.01f), null);
    }

    static void Detail(Material m, string normal, float strength, float tileM, string mask)
    {
        m.SetTexture("_DetailNormal", T(Tex + normal));
        m.SetFloat("_DetailNormalScale", strength);
        m.SetFloat("_DetailTile", 1f / tileM);
        if (mask != null) m.SetTexture("_DetailMask", T(Tex + mask));
    }

    // ------------------------------------------------------------------------------------------------ UdonSharp by reflection
    static string AddUdonSharp(GameObject go, string className)
    {
        // D-41：共用工具按 Type 查程序资产、要求已初始化完（菜单先等过了）、加组件并检查背后的 UdonBehaviour
        Type behType = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript(className);
        if (behType == null) return "script " + className + " not found or not compiled yet";
        if (!Lanbai.Udon.LanbaiUdonPrograms.Available)
        {
            Undo.AddComponent(go, behType);
            return "UdonSharp editor not found: plain AddComponent, make the program asset by hand";
        }
        Lanbai.Udon.LanbaiUdonPrograms.CreateMissing(className, new[] { behType }, t => ProgDir + "/" + t.Name + ".asset");
        Lanbai.Udon.LanbaiUdonPrograms.AddComponent(go, behType);
        return "added (program asset " + ProgDir + "/" + className + ".asset)";
    }

    // the backing UdonBehaviour's interactText / proximity (as LB_Udon.Commit does), by reflection
    static void InteractText(Component usb, string text, float proximity)
    {
        Type u = FindType("UdonSharpEditor.UdonSharpEditorUtility");
        MethodInfo get = u == null ? null : u.GetMethods(BindingFlags.Public | BindingFlags.Static)
            .FirstOrDefault(m => m.Name == "GetBackingUdonBehaviour" && m.GetParameters().Length == 1);
        object ub = get == null ? null : get.Invoke(null, new object[] { usb });
        if (ub == null) { _rep.AppendLine("  " + usb.name + ": no backing UdonBehaviour yet (interact text left default)"); return; }
        var ft = ub.GetType().GetField("interactText"); if (ft != null) ft.SetValue(ub, text);
        var fp = ub.GetType().GetField("proximity"); if (fp != null) fp.SetValue(ub, proximity);
        EditorUtility.SetDirty((UnityEngine.Object)ub);
    }

    static Type FindType(string fullName)
    {
        foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
        {
            var t = a.GetType(fullName, false);
            if (t != null) return t;
        }
        return null;
    }

    // ------------------------------------------------------------------------------------------------ helpers
    internal static Transform FindDeep(Transform t, string name)
    {
        if (t.name == name) return t;
        for (int i = 0; i < t.childCount; i++) { var r = FindDeep(t.GetChild(i), name); if (r != null) return r; }
        return null;
    }

    static Vector3 V(float[] a) { return a != null && a.Length >= 3 ? new Vector3(a[0], a[1], a[2]) : Vector3.zero; }

    internal static Color Hex(string h)
    {
        Color c; return ColorUtility.TryParseHtmlString(h, out c) ? c : Color.magenta;   // sRGB, as typed in the Inspector
    }

    // sRGB hex -> linear x gain, for Vector properties (SetVector writes the numbers as they are; VRChat projects are linear)
    static Vector4 Lin(Color srgb, float gain)
    {
        Color l = srgb.linear; return new Vector4(l.r * gain, l.g * gain, l.b * gain, 1f);
    }

    internal static Texture T(string path)
    {
        var t = AssetDatabase.LoadAssetAtPath<Texture>(path);
        if (t == null) _rep.AppendLine("  texture missing: " + path);
        return t;
    }

    static Texture FindTexture(string contains)
    {
        foreach (var g in AssetDatabase.FindAssets("t:Texture", new[] { Root + "Bus/Textures" }))
        {
            string p = AssetDatabase.GUIDToAssetPath(g);
            if (Path.GetFileNameWithoutExtension(p).Contains(contains)) return AssetDatabase.LoadAssetAtPath<Texture>(p);
        }
        return null;
    }

    internal static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path)) return;
        string parent = Path.GetDirectoryName(path).Replace('\\', '/');
        EnsureFolder(parent);
        AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
    }

    static void SetRef(SerializedObject so, string prop, UnityEngine.Object v)
    {
        var p = so.FindProperty(prop); if (p == null) { _rep.AppendLine("  no field " + prop); return; }
        p.objectReferenceValue = v;
    }
    static void SetInt(SerializedObject so, string prop, int v) { var p = so.FindProperty(prop); if (p != null) p.intValue = v; else _rep.AppendLine("  no field " + prop); }
    static void SetBool(SerializedObject so, string prop, bool v) { var p = so.FindProperty(prop); if (p != null) p.boolValue = v; else _rep.AppendLine("  no field " + prop); }
    static void SetVec3(SerializedObject so, string prop, Vector3 v) { var p = so.FindProperty(prop); if (p != null) p.vector3Value = v; else _rep.AppendLine("  no field " + prop); }
    static void SetRefs(SerializedObject so, string prop, List<UnityEngine.Object> v)
    {
        var p = so.FindProperty(prop); if (p == null || !p.isArray) { _rep.AppendLine("  no array field " + prop); return; }
        p.arraySize = v.Count;
        for (int i = 0; i < v.Count; i++) p.GetArrayElementAtIndex(i).objectReferenceValue = v[i];
    }
    static void SetVec3s(SerializedObject so, string prop, List<Vector3> v)
    {
        var p = so.FindProperty(prop); if (p == null || !p.isArray) { _rep.AppendLine("  no array field " + prop); return; }
        p.arraySize = v.Count;
        for (int i = 0; i < v.Count; i++) p.GetArrayElementAtIndex(i).vector3Value = v[i];
    }
    static void SetFloats(SerializedObject so, string prop, List<float> v)
    {
        var p = so.FindProperty(prop); if (p == null || !p.isArray) { _rep.AppendLine("  no array field " + prop); return; }
        p.arraySize = v.Count;
        for (int i = 0; i < v.Count; i++) p.GetArrayElementAtIndex(i).floatValue = v[i];
    }
}
#endif
