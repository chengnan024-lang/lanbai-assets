// Lanbai / 蓝白 -- 蓝白/Build/车厢（先交）/… : D-44 "外壳 + Lanbai/Cabin 先交". Puts the PAZ-672M (Bus/Models/Bus.fbx, every
// surface on Lanbai/Cabin: bleach + clip erosion on a world-space FBM, bible §4.8 / D-32 #1, no dither) into the local
// FullPreview in place of the v1 placeholder bus (local LB_LitPBR: a screen-door dither driven by LB_Journey.SetBusAlpha),
// without editing LB_Journey.
// UNCOMPILED (cloud side): Roslyn type-check only (Common/Tools~/compile_check/check_cs.sh). Never run in Unity.
// Why and how, step by step for the local integrator: Bus/Docs~/D44_车厢先交.md.
//
// 搭建（车厢 + 车外皮）  Lanbai_Bus under LB_Journey.busRoot (the v1 root: origin, identity; the bus never moves), from Bus.fbx:
//                        cabin, seats, window, pole, curtains, doors, glass, exterior LODs, wheels and wipers (static). Materials
//                        = 蓝白/Build/车's makers (LanbaiBusBuild.CabinMat / GlassMat / ClothMat / PartMat) into
//                        Bus/Generated/Materials. 23 VRCStations (the local LB_Seat with its poem seat when the project has it,
//                        else LanbaiBusSeat), the BusLayout colliders, LanbaiCabinDriver (journey, the inside driver's window,
//                        the dispatcher's LanbaiCabinDriver[] if it already has one), copies of the panes for the sea's
//                        waterline. Then 用新车, but only when the build has 0 ERRORs; otherwise the new bus is built but
//                        left off, the v1 bus stays in use and the report says "built, NOT switched" (the menu's status
//                        is FAILED). No head-fill lights (LB_Journey.cabinLights stay the avatar light), no LanbaiWipers.
// 搭建（只车厢）         the same without Bus_Exterior_LOD0/1, Wheel_*, Wiper* (then the bus has no outside).
// 用新车 / 用旧车（对照）  GameObjects only, one undo step: v1 Model / Seats / Colliders / Label <-> the new model / Seats /
//                        Colliders. 用新车 takes the v1 depart button out of the v1 Model (it would go off with it); when it
//                        is outside BusLayout cabin_bounds (the v1 dash is at about z 3.8, the new cabin ends at z 3.41) or
//                        stuck in a BusLayout collider, it goes on top of Col_Dash beside the steering column (DepartSpot);
//                        its old pose goes into the report and into an EditorOnly marker next to it, 用旧车 puts it back.
//                        LanbaiAct07Driver.waterlines and Act07_TrailsFront follow the bus in use. LanbaiCabinDriver stays
//                        active in both.
// 检查（只读）            writes nothing: what is wired, other writers of the cabin globals, the Director (the driver's
//                        LanbaiTakesOverNothing, the generated dispatcher, windowsFlat in Play), texture import types, the
//                        depart button (ERROR outside cabin_bounds while the new bus is in use), RadioAnchor, layers,
//                        vertex compression.
// Never: the formal scene (Assets/Lanbai/Scenes/Lanbai.unity, D-46 #3; refused before any program asset is made),
// LB_Journey's fields, project settings / layers, import settings (.meta), saving the scene, deleting anything of the v1 bus.
// AssetDatabase.SaveAssets: this file saves its own materials one by one with SaveAssetIfDirty and calls SaveAssets only in
// the pre-2021.2 fallback (the report warns). Creating missing program assets through the shared tool DOES call it
// (LanbaiUdonPrograms.CreateMissing: SaveAssets + Refresh once it has made one), i.e. on the first build.
// Writes: Assets/Lanbai/Bus/Generated/Materials/*.mat; U# program assets for LanbaiCabinDriver / LanbaiBusSeat when missing
// (Assets/Lanbai/Bus/Programs/, the folder 蓝白/Build/车 uses; via Common/Editor/LanbaiUdonPrograms, D-41) and UdonSharp's own
// Assets/SerializedUdonPrograms/; the open scene in memory (marked dirty, not saved).
#if UNITY_EDITOR
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
using UnityEngine.SceneManagement;

public static class LanbaiBusCabinDropIn
{
    const string Menu = "蓝白/Build/车厢（先交）/";
    public const string MenuBuildAll = Menu + "搭建（车厢 + 车外皮）";
    public const string MenuBuildCabin = Menu + "搭建（只车厢）";
    public const string MenuUseNew = Menu + "用新车";
    public const string MenuUseOld = Menu + "用旧车（对照）";
    public const string MenuCheck = Menu + "检查（只读）";

    public const string RootName = "Lanbai_Bus";                  // the name 蓝白/Build/车 uses too: one bus per scene
    const string ModelName = "Model_PAZ672", SeatsName = "Seats", CollidersName = "Colliders", DriverName = "LanbaiCabinDriver";
    const string GenDir = LanbaiBusBuild.Root + "Bus/Generated";
    const string GenMatDir = GenDir + "/Materials";
    const string FormalScene = LanbaiBusBuild.Root + "Scenes/Lanbai.unity";
    const string WaterlineName = "DeliveredWaterline";            // the local binding's name for the glass copies (LB_FullAssemblyBinding)
    const string Tag = "[Lanbai Bus DropIn] ";
    static readonly Vector3 HeroEye = new Vector3(0.55f, 1.70f, 2.05f);   // D-28 / D-40b #1
    // the v1 bus = these children of LB_Journey.busRoot (FromLocal/visual_feedback/20261025-0206/flicker_20261025_0203_read.step1.txt).
    // Everything else under busRoot stays as it is: CabinLight x3 (= LB_Journey.cabinLights, the avatar light), Headlight x2,
    // CabinProbe, RadioAnchor, SpawnInBus, Rain.
    static readonly string[] V1Parts = { "Model", "Seats", "Colliders", "Label" };

    // BusLayout.json 'cabin_bounds' and 'radio' (LanbaiBusBuild.Layout does not read them): public, as JsonUtility fills them
    [Serializable] public class Box { public float[] min; public float[] max; }
    [Serializable] public class Radio { public float[] centre; }
    [Serializable] public class DropInLayout { public Box cabin_bounds; public Radio radio; }

    // The depart button's place in the new cabin (bus frame): the bottom-centre of its colliders (else meshes) goes here,
    // rotation kept. On top of Col_Dash (y 0.62..1.28, z 3.08..3.46; the moulded top under it is 1.24-1.27, build_bus.py
    // driver_area, so the button stands about 3 cm above the plastic but wholly above the collider, where the interact ray
    // reaches it), right of the steering-wheel rim (x <= -0.57) and the binnacle (x -0.99..-0.65), not on the wheel centre
    // (-0.82, 1.30, 3.00), in front of the engine cover (x -0.50..0.12, z to 3.08, top 1.02), behind Col_Front (z 3.41):
    // about 1.2 m from a player standing in the front aisle. From the hero eye it is at az -39, el -15, clear of every bible
    // target (bus_spec.py TARGETS); a button up to about 6 cm tall stays under the windscreen's lower edge.
    static readonly Vector3 DepartSpot = new Vector3(-0.40f, 1.283f, 3.22f);
    const string DepartMarker = "DropIn_DepartButton_v1Pose_";    // + the button's name: an EditorOnly empty beside it (same
                                                                  // parent, same local pose) = where 用旧车 puts it back
    const float FilmEnd = 1729.96f;                               // FromLocal/timeline_v1.md: 13 (end) = wake + 480

    // Import types the new bus's materials need (READ only: fixing them writes .meta files, the integrator does it). Lanbai/
    // Cabin and ThinCloth unpack these normals with UnpackScaleNormal, so a colour (sRGB, Default) import bends every normal
    // (Part_<type>_Normal_<res>.png comes in that way with a LanbaiCabinImport.cs older than the '_Normal_' rule); masks
    // and the tube light map are data (linear). ERROR, the build does not switch.
    static readonly string[] NormalProps = { "_PartNormal", "_DetailNormal", "_WeaveNormal" };
    static readonly string[] LinearProps = { "_PartMask", "_DetailMask", "_AtlasMask", "_CabinTubeLM" };
    // the rain glass (Rain/README_Rain.md §1: every texture is data, Default type, sRGB off; Rain has no import script and
    // the folder is not ours): WARNING
    static readonly string[] RainProps = { "_BeadNormal", "_BeadData", "_RunnerFlow" };

    // ------------------------------------------------------------------------------------------------ report
    sealed class Rep
    {
        public readonly StringBuilder sb = new StringBuilder();
        public int errors, warnings;
        public void Err(string s) { errors++; sb.AppendLine("ERROR " + s); }
        public void Warn(string s) { warnings++; sb.AppendLine("WARNING " + s); }
        public void Line(string s) { sb.AppendLine(s); }
        public string Finish(string what)
        {
            string text = sb.ToString();
            // the shared material makers (LanbaiBusBuild) report missing inputs as plain lines: count them as warnings
            warnings += Count(text, "texture missing") + Count(text, "unknown material") + Count(text, "  no field ") +
                        Count(text, "  no array field ") + Count(text, "not in BusLayout.json parts");
            string head = (errors > 0 ? "ERROR " : "OK ") + what + ": " + errors + " error(s), " + warnings + " warning(s)";
            if (errors > 0) Debug.LogError(Tag + head + "\n" + text);
            else if (warnings > 0) Debug.LogWarning(Tag + head + "\n" + text);
            else Debug.Log(Tag + head + "\n" + text);
            return head;
        }
        static int Count(string s, string sub)
        {
            int n = 0;
            for (int i = s.IndexOf(sub, StringComparison.Ordinal); i >= 0; i = s.IndexOf(sub, i + sub.Length, StringComparison.Ordinal)) n++;
            return n;
        }
    }

    // ------------------------------------------------------------------------------------------------ menus
    [MenuItem(MenuBuildAll, false, 30)]
    static void BuildAllMenu() { RunMenu(MenuBuildAll, true); }

    [MenuItem(MenuBuildCabin, false, 31)]
    static void BuildCabinMenu() { RunMenu(MenuBuildCabin, false); }

    [MenuItem(MenuUseNew, false, 50)]
    static void UseNewMenu() { UseNew(); }

    [MenuItem(MenuUseOld, false, 51)]
    static void UseOldMenu() { UseOld(); }

    [MenuItem(MenuCheck, false, 70)]
    static void CheckMenu() { Check(); }

    // D-41: the program assets first (created next to 蓝白/Build/车's, Bus/Programs), wait for the SDK, then build. 'who' is
    // the menu path: after a domain reload the shared tool clicks it again. Guard() comes before RunWhenReady, so Play mode
    // and the formal scene get no program assets either. A build that does not return OK throws InvalidOperationException
    // inside the callback, so the shared tool's MenuStatus(who) (read by LB_Remote) says FAILED, not DONE. A refusal before
    // that (Guard, no program types) also records FAILED (Refused), so an older DONE does not stay.
    static void RunMenu(string who, bool exterior)
    {
        var R = new Rep();
        if (!Guard(R))
        {
            string head = R.Finish(who + " - nothing done");
            Refused(who, head + " - " + R.sb.ToString().Split('\n')[0].Trim());
            return;
        }
        string why;
        var types = ProgramTypes(out why);
        if (types == null) { Debug.LogError(Tag + "ERROR " + why); Refused(who, "ERROR " + why); return; }
        try
        {
            Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady(who, types, () =>
            {
                string s = Build(exterior);
                if (!s.StartsWith("OK", StringComparison.Ordinal)) throw new InvalidOperationException(Tag + s);
            }, t => LanbaiBusBuild.ProgDir + "/" + t.Name + ".asset");
        }
        catch (InvalidOperationException e)
        {
            // ours: the report is already in the Console (Rep.Finish) and the shared tool has set FAILED; anything else goes on
            if (!e.Message.StartsWith(Tag, StringComparison.Ordinal)) throw;
        }
    }

    // a menu refused before any program asset is made: record FAILED through the shared tool. With no types it creates and
    // waits for nothing (AllReady of none is true) and runs the throwing callback at once. Without UdonSharp the shared tool
    // keeps no status at all, so there is nothing to record.
    static void Refused(string who, string why)
    {
        if (!Lanbai.Udon.LanbaiUdonPrograms.Available) return;
        try { Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady(who, Type.EmptyTypes, () => { throw new InvalidOperationException(Tag + why); }); }
        catch (InvalidOperationException e) { if (!e.Message.StartsWith(Tag, StringComparison.Ordinal)) throw; }
    }

    // ------------------------------------------------------------------------------------------------ method steps
    // For the test tool ('method' steps) and LB_Remote. Each returns "OK ..." or "ERROR ..." (one line); the report goes to
    // the Console. The two builds need the program assets ready (use the menus, or list the types in 'udon_programs').
    public static string BuildAll() { return Build(true); }
    public static string BuildCabinOnly() { return Build(false); }

    public static string UseNew() { return Switched(true); }
    public static string UseOld() { return Switched(false); }

    static string Switched(bool useNew)
    {
        var R = new Rep();
        string what = useNew ? "用新车" : "用旧车（对照）";
        if (!Guard(R)) return R.Finish(what + " - nothing done");
        Undo.IncrementCurrentGroup();
        Undo.SetCurrentGroupName("Bus drop-in: " + what);
        int group = Undo.GetCurrentGroup();
        Switch(useNew, R);
        Undo.CollapseUndoOperations(group);
        return R.Finish(what);
    }

    // ------------------------------------------------------------------------------------------------ build
    static string Build(bool exterior)
    {
        var R = new Rep();
        string what = "built " + RootName + (exterior ? " (cabin + exterior)" : " (cabin only)");
        if (!Guard(R)) return R.Finish(what + " - nothing done");
        string why;
        var types = ProgramTypes(out why);
        if (types == null) { R.Err(why); return R.Finish(what + " - nothing done"); }
        try { Lanbai.Udon.LanbaiUdonPrograms.RequireReady(exterior ? MenuBuildAll : MenuBuildCabin, types); }
        catch (Exception e) { R.Err(e.Message); return R.Finish(what + " - nothing done"); }

        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(LanbaiBusBuild.FbxPath);
        var layoutText = AssetDatabase.LoadAssetAtPath<TextAsset>(LanbaiBusBuild.LayoutPath);
        if (fbx == null || layoutText == null)
        {
            R.Err("没找到 " + (fbx == null ? LanbaiBusBuild.FbxPath + " " : "") + (layoutText == null ? LanbaiBusBuild.LayoutPath : "") +
                  "（Bus/Models 拷到 Assets/Lanbai/Bus/Models 了吗？）：场景没动");
            return R.Finish(what + " - nothing done");
        }
        var L = JsonUtility.FromJson<LanbaiBusBuild.Layout>(layoutText.text);
        if (L == null || L.seats == null || L.seats.Length == 0)
        {
            R.Err(LanbaiBusBuild.LayoutPath + " 读不出座位：场景没动");
            return R.Finish(what + " - nothing done");
        }
        Shader cabin = Shader.Find("Lanbai/Cabin"), cloth = Shader.Find("Lanbai/ThinCloth"), glass = Shader.Find("Lanbai/BusGlass");
        if (cabin == null || cloth == null)
        {
            R.Err("shader 不在：Lanbai/Cabin " + (cabin != null) + "，Lanbai/ThinCloth " + (cloth != null) +
                  "（Cabin/Shaders 拷到 Assets/Lanbai/Cabin/Shaders、Common/Shaders 是 main 上最新的吗？Console 有没有 shader 报错？）：场景没动");
            return R.Finish(what + " - nothing done");
        }
        LanbaiBusBuild.BeginShared(R.sb, L);                       // the material makers report into R, PartMat reads L.parts
        CheckImport(R);
        CheckVertexCompression(R, false);

        // the v1 bus root: the new bus goes under it at identity, so every reference to busRoot keeps working (poem driver,
        // spawn check, the test tools' cameras busRoot.TransformPoint(0.55, 1.70, 2.05))
        Component journey = One("LB_Journey", R);
        Transform busRoot = Field(journey, "busRoot") as Transform;
        if (journey == null) R.Warn("场景里没有 LB_Journey：搭在场景根上，没有旧车可换（测试场景？）");
        else if (busRoot == null) R.Warn("LB_Journey.busRoot 是空的：搭在场景根上");
        else CheckIdentity(busRoot, R);
        CheckOtherWriters(R);

        Undo.IncrementCurrentGroup();
        Undo.SetCurrentGroupName("Build bus drop-in");
        int group = Undo.GetCurrentGroup();                         // one Ctrl+Z: the build and the switch
        var save = new List<UnityEngine.Object>();

        // 1. the previous build goes (anywhere, active or not; 蓝白/Build/车's full bus has the same name: one bus per scene)
        foreach (var t in Named(RootName))
            if (t != null) { R.Line("removed the previous " + Path(t)); Undo.DestroyObjectImmediate(t.gameObject); }

        // 2. the FBX under Lanbai_Bus at identity (unpacked, as 蓝白/Build/车)
        var root = new GameObject(RootName);
        Undo.RegisterCreatedObjectUndo(root, "Build bus drop-in");
        if (busRoot != null) root.transform.SetParent(busRoot, false);
        Identity(root.transform);
        var model = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        PrefabUtility.UnpackPrefabInstance(model, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        model.name = ModelName;
        model.transform.SetParent(root.transform, false);
        Identity(model.transform);
        if (!exterior)
        {
            int cut = 0;
            foreach (var t in model.GetComponentsInChildren<Transform>(true).Where(x => IsExterior(x.name)).ToList())
                if (t != null) { UnityEngine.Object.DestroyImmediate(t.gameObject); cut++; }
            R.Warn("只车厢：车外皮、轮子、雨刮没搭（" + cut + " 个物体）。从车外看（第 1、12 幕的站台）是车厢的背面；要整车点「搭建（车厢 + 车外皮）」");
        }
        // 2b. door panes ride with their leaves (finish_bus.py exports Glass_DoorK separately)
        for (int k = 0; k < 4; k++)
        {
            var leaf = LanbaiBusBuild.FindDeep(model.transform, "Bus_Door" + k);
            var pane = LanbaiBusBuild.FindDeep(model.transform, "Glass_Door" + k);
            if (leaf != null && pane != null) pane.SetParent(leaf, true);
        }

        // 3. materials: exactly 蓝白/Build/车's makers, written to Bus/Generated/Materials
        LanbaiBusBuild.EnsureFolder(GenMatDir);
        var glassRs = new List<Renderer>();
        var cabinRs = new List<Renderer>();
        Renderer curtains = null;
        int uvOk = 0, uvBad = 0;
        foreach (var r in model.GetComponentsInChildren<Renderer>(true))
        {
            string n = r.gameObject.name;
            if (n.StartsWith("Glass_", StringComparison.Ordinal))
            {
                r.shadowCastingMode = ShadowCastingMode.Off;
                if (glass == null) { r.enabled = false; continue; }  // a Standard fallback would be opaque: no glass is better
                r.sharedMaterial = LanbaiBusBuild.GlassMat(glass, n, GenMatDir);
                save.Add(r.sharedMaterial);
                glassRs.Add(r);
                continue;
            }
            if (n == "Cabin_Curtains")
            {
                r.sharedMaterials = r.sharedMaterials.Select(m => LanbaiBusBuild.ClothMat(cloth, GenMatDir)).ToArray();
                save.AddRange(r.sharedMaterials);
                curtains = r;
                continue;
            }
            var mode = LanbaiBusBuild.ModeFor(n);
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++) mats[i] = LanbaiBusBuild.CabinMat(cabin, mats[i] != null ? mats[i].name : "Alu", mode, GenMatDir);
            r.sharedMaterials = mats;
            save.AddRange(mats);
            cabinRs.Add(r);
            GameObjectUtility.SetStaticEditorFlags(r.gameObject, 0);   // no Unity lightmapping (D-42 ①): the tube light is _CabinTubeLM
            r.reflectionProbeUsage = ReflectionProbeUsage.BlendProbes;
            if (mode == LanbaiBusBuild.Mode.CabinLM || mode == LanbaiBusBuild.Mode.ExteriorAtlas) { if (Uv1Atlas(r)) uvOk++; else uvBad++; }
        }
        if (glass == null)
            R.Err("Lanbai/BusGlass 不在（Rain/Shaders 没同步？）：玻璃没上材质、全部关掉，窗是空的。同步 Rain/Shaders 和 Rain/Textures/Glass 以后再搭一次");
        if (uvBad > 0)
            R.Err(uvBad + " 个用光照图 / 外观图集的物体 uv1 不在 0..1：Bus.fbx 是旧的（uv 顺序不对），或者导入时生成了第二套 UV。管灯光照图会采错");
        R.Line("materials -> " + GenMatDir + ": Lanbai/Cabin renderers " + cabinRs.Count + " (uv1 = atlas: " + uvOk + "), glass " + glassRs.Count +
               ", curtains " + (curtains != null));
        CheckTextureTypes(save.OfType<Material>(), false, R);              // read only: a normal map imported as colour is an ERROR

        // 4. layers (bible §1.6 / §4.3, as 蓝白/Build/车): cabin, glass, curtains, doors on Bus; the outside skin, wheels, wipers on BusExterior
        int layerBus = LayerMask.NameToLayer("Bus"), layerExt = LayerMask.NameToLayer("BusExterior");
        if (layerBus < 0) R.Warn("layer Bus 不在：车厢留在 Default（第 7 幕的光柱、玫瑰灯只照 Bus 层，照不到车厢）。加层是改 ProjectSettings：先备份、经小楠确认");
        if (exterior && layerExt < 0) R.Warn("layer BusExterior 不在：车外皮留在 Default（圣经 §4.3 要它单独一层，给站台灯照；FullPreview 里还没有新站台灯，暂时不影响）");
        foreach (var r in model.GetComponentsInChildren<Renderer>(true))
        {
            int l = IsExterior(r.gameObject.name) ? layerExt : layerBus;
            if (l >= 0) r.gameObject.layer = l;
        }

        // 5. the exterior LODGroup (CONTROL §6 pitfall 4: the importer does not group <name>_LOD0/1)
        if (exterior)
        {
            var lod0 = LanbaiBusBuild.FindDeep(model.transform, "Bus_Exterior_LOD0");
            var lod1 = LanbaiBusBuild.FindDeep(model.transform, "Bus_Exterior_LOD1");
            if (lod0 != null && lod1 != null)
            {
                var lodGo = new GameObject("Bus_Exterior");
                lodGo.transform.SetParent(model.transform, false);
                lod0.SetParent(lodGo.transform, true); lod1.SetParent(lodGo.transform, true);
                var lg = lodGo.AddComponent<LODGroup>();
                lg.SetLODs(new LOD[] {
                    new LOD(0.12f, lod0.GetComponentsInChildren<Renderer>(true)),
                    new LOD(0.005f, lod1.GetComponentsInChildren<Renderer>(true)) });
                lg.RecalculateBounds();
            }
            else R.Warn("Bus_Exterior_LOD0 / LOD1 不在 Bus.fbx 里：车外皮没有 LOD");
        }
        // 5b. D-36 seat LODs (finish_bus.seat_lods: Seat_<inst>_LOD1 / _LOD2), the full builder's own grouping: without it
        //     an FBX with the copies would draw each seat three times, one inside the other
        R.Line(LanbaiBusBuild.GroupSeatLods(model.transform));

        // 6. seats: one VRCStation per BusLayout seat (23), facing +Z; the local LB_Seat when the project has it (its
        //    OnStationEntered tells LanbaiPoemDriver which seat you sit in), else the bus package's LanbaiBusSeat
        var seatCentres = new List<Vector3>();
        BuildSeats(root.transform, L, seatCentres, R);

        // 7. the BusLayout colliders (invisible boxes: floor, walls, roof, dash, engine cover, guard, step)
        var colRoot = new GameObject(CollidersName);
        colRoot.transform.SetParent(root.transform, false);
        if (L.colliders != null)
            foreach (var c in L.colliders)
            {
                var go = new GameObject(c.name);
                go.transform.SetParent(colRoot.transform, false);
                var bc = go.AddComponent<BoxCollider>(); bc.center = V(c.c); bc.size = V(c.s);
            }

        // 8. LanbaiCabinDriver: the cabin's whole-film timeline (writes _Udon_CabinLightmap / Bleach / Fade; ambient and the
        //    dial outside the inside driver's window). On its own object, always active (the Director's rule).
        var drvGo = new GameObject(DriverName);
        drvGo.transform.SetParent(root.transform, false);
        Component drv = null;
        try { drv = Lanbai.Udon.LanbaiUdonPrograms.AddComponent(drvGo, types[0]); }
        catch (Exception e) { R.Err("LanbaiCabinDriver: " + e.Message); }
        if (drv != null) FillDriver(drv, model.transform, L, cabinRs, curtains, glassRs, seatCentres, journey, R);

        // 9. the sea's waterline on the new panes (copies with Lanbai/SeaWaterline, as the local binding makes them on the
        //    v1 glass); 用新车 points LanbaiAct07Driver.waterlines at them
        MakeWaterlines(busRoot, root.transform, glassRs, layerBus, save, R);

        // 10. save what this build wrote (one by one, only under Bus/Generated); the scene is only marked dirty
        SaveEach(save, R);
        EditorSceneManager.MarkSceneDirty(root.scene);

        // 11. switch: the v1 bus off, the new one on (same undo step) - only after a clean build. With ERRORs the new bus is
        //     left built but off (the 用旧车 state, so the two never show at once) and the v1 bus stays in use.
        if (R.errors > 0)
        {
            int before = R.errors;
            Switch(false, R);
            what += ", NOT switched";
            R.Line("built, NOT switched：上面有 " + before + " 个 ERROR。新车搭好了、关着，旧车还在用。先修 ERROR 再搭一次；" +
                   "只想先看一眼新车，点「用新车」");
        }
        else Switch(true, R);
        Undo.CollapseUndoOperations(group);
        Selection.activeGameObject = root;
        R.Line("next: Bus/Docs~/D44_车厢先交.md §5（分发层、Play 里看哪几个时刻、可选的 LB_Journey 字段）；对照旧车点「用旧车（对照）」");
        return R.Finish(what);
    }

    static void BuildSeats(Transform root, LanbaiBusBuild.Layout L, List<Vector3> seatCentres, Rep R)
    {
        var seatRoot = new GameObject(SeatsName);
        seatRoot.transform.SetParent(root, false);
        Type stationType = Lanbai.Udon.LanbaiUdonPrograms.FindType("VRC.SDK3.Components.VRCStation");
        Type lbSeat = LocalSeatType();
        Type seatType = lbSeat ?? Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript("LanbaiBusSeat");
        Component poems = One("LanbaiPoemDriver", R);
        var eyes = Field(poems, "seatEye") as Vector3[];
        bool poemSeat = lbSeat != null && lbSeat.GetField("poemDriver") != null && lbSeat.GetField("poemSeatIndex") != null && poems != null;
        if (poemSeat && (eyes == null || eyes.Length == 0)) R.Warn("LanbaiPoemDriver.seatEye 是空的：每个座位的诗都按主座位摆（Fonts/seat_positions.json 烘了吗？）");
        float worst = 0f;
        int made = 0;
        foreach (var s in L.seats)
        {
            var go = new GameObject("Station_" + s.name + (s.hero ? "_HERO" : ""));
            go.transform.SetParent(seatRoot.transform, false);
            go.transform.localPosition = V(s.station_pos);                // facing +Z (identity)
            seatCentres.Add(new Vector3(s.x, s.cushion_y, s.back_z + 0.25f));
            var bc = go.AddComponent<BoxCollider>();                      // the interact target
            bc.isTrigger = true; bc.center = new Vector3(0f, 0.15f, -0.1f); bc.size = new Vector3(0.45f, 0.3f, 0.45f);
            var enter = new GameObject("Enter");
            enter.transform.SetParent(go.transform, false);
            if (stationType == null) continue;
            var st = go.AddComponent(stationType);
            var so = new SerializedObject(st);
            LanbaiBusBuild.SetRef(so, "stationEnterPlayerLocation", enter.transform);
            LanbaiBusBuild.SetRef(so, "stationExitPlayerLocation", enter.transform);
            LanbaiBusBuild.SetInt(so, "PlayerMobility", 1);               // Immobilize
            LanbaiBusBuild.SetBool(so, "seated", true);
            so.ApplyModifiedPropertiesWithoutUndo();
            made++;
            if (seatType == null) continue;
            try
            {
                var seat = Lanbai.Udon.LanbaiUdonPrograms.AddComponent(go, seatType);
                var sso = new SerializedObject(seat);
                LanbaiBusBuild.SetRef(sso, "station", st);
                if (poemSeat)
                {
                    float d;
                    int k = NearestEye(eyes, s, out d);
                    worst = Mathf.Max(worst, d);
                    LanbaiBusBuild.SetRef(sso, "poemDriver", poems);
                    LanbaiBusBuild.SetInt(sso, "poemSeatIndex", k);
                }
                sso.ApplyModifiedPropertiesWithoutUndo();
                Lanbai.Udon.LanbaiUdonPrograms.CopyProxyToUdon(seat);
                LanbaiBusBuild.InteractText(seat, "坐下", 2f);
            }
            catch (Exception e) { R.Err("seat " + s.name + ": " + e.Message); }
        }
        if (stationType == null) R.Warn("VRCStation 类型找不到（VRChat SDK？）：只建了座位的位置，没有 station");
        if (seatType == null) R.Warn("LB_Seat 和 LanbaiBusSeat 都找不到：station 没有“坐下”的交互");
        R.Line("seats: " + made + " VRCStation(s), sit script " + (seatType != null ? seatType.Name : "none") +
               (poemSeat ? ", poem seat = nearest LanbaiPoemDriver.seatEye (worst " + worst.ToString("0.00") + " m)" : ""));
        if (poemSeat && worst > 0.15f) R.Warn("有座位离最近的 seatEye 超过 0.15 m：Fonts/seat_positions.json 和 BusLayout.json 的座位对不上，诗的位置按别的座位算");
    }

    static void FillDriver(Component drv, Transform model, LanbaiBusBuild.Layout L, List<Renderer> cabinRs, Renderer curtains,
                           List<Renderer> glassRs, List<Vector3> seatCentres, Component journey, Rep R)
    {
        var so = new SerializedObject(drv);
        LanbaiBusBuild.SetRefs(so, "cabinRenderers", cabinRs.Cast<UnityEngine.Object>().ToList());   // incl. the exterior (D-26 hole)
        LanbaiBusBuild.SetRefs(so, "curtainRenderers", curtains != null ? new List<UnityEngine.Object> { curtains } : new List<UnityEngine.Object>());
        LanbaiBusBuild.SetRefs(so, "glassRenderers", glassRs.Cast<UnityEngine.Object>().ToList());
        LanbaiBusBuild.SetVec3s(so, "seatCentres", seatCentres);
        var h = L.seats.FirstOrDefault(x => x.hero);
        if (h != null) LanbaiBusBuild.SetVec3(so, "heroSeat", new Vector3(h.x, h.cushion_y, h.back_z + 0.25f));
        var doors = new List<UnityEngine.Object>(); var dpos = new List<Vector3>(); var dyaw = new List<float>();
        if (L.door_panels != null)
            foreach (var d in L.door_panels)
            {
                var t = LanbaiBusBuild.FindDeep(model, d.name);
                if (t == null || d.closed == null) continue;
                doors.Add(t); dpos.Add(V(d.closed.position)); dyaw.Add(d.closed.yaw_deg);
            }
        LanbaiBusBuild.SetRefs(so, "doorPanels", doors); LanbaiBusBuild.SetVec3s(so, "doorClosedPos", dpos); LanbaiBusBuild.SetFloats(so, "doorClosedYaw", dyaw);
        if (journey != null) LanbaiBusBuild.SetRef(so, "journey", journey);      // act 4 tube flicker: reads LB_Journey._l0/_l1/_l2
        else R.Warn("没有 LB_Journey：LanbaiCabinDriver.journey 空着（第 4 幕管灯闪烁只走基础曲线）");
        // D-22 one writer at a time: the inside driver owns _Udon_CabinAmbient / _Udon_RadioDial / _Udon_CabinSlice in its window
        Component inside = One("LanbaiInsideDriver", R);
        LanbaiBusBuild.SetBool(so, "yieldToInside", inside != null);
        float[] w = Window(inside);
        if (w != null) { SetFloat(so, "insideFrom", w[0], R); SetFloat(so, "insideTo", w[1], R); }
        so.ApplyModifiedPropertiesWithoutUndo();
        try { Lanbai.Udon.LanbaiUdonPrograms.CopyProxyToUdon(drv); }
        catch (Exception e) { R.Err("LanbaiCabinDriver CopyProxyToUdon: " + e.Message); }
        R.Line("LanbaiCabinDriver: " + cabinRs.Count + " cabin, " + glassRs.Count + " glass, " + doors.Count + " door leaves, " + seatCentres.Count +
               " seats, journey " + (journey != null) + ", yieldToInside " + (inside != null) +
               (w != null ? " [" + w[0].ToString("0.00") + ", " + w[1].ToString("0.00") + "]" : ""));
        if (inside != null && w == null) R.Warn("LanbaiInsideDriver.LanbaiWindow() 读不出来：LanbaiCabinDriver 用默认的门内窗口 [177.55, 252.64]");
        CheckDriverInterface(drv, R);
        WireDispatcher(drv, R);
    }

    // The Director ticks LanbaiCabinDriver once 蓝白/Director/1 Generate Dispatcher has given the dispatcher a typed array for
    // it. A rebuild makes a new driver object, so if that array exists it is pointed at the new driver here (what
    // 蓝白/Director/2 Wire Scene does, for this one array). No array yet: nobody ticks the driver and the cabin keeps its
    // Start() state (t = 0: whole, tubes on, no bleach, no erosion) until Generate + Wire.
    static void WireDispatcher(Component drv, Rep R)
    {
        Component disp = One("LanbaiActDispatcher", R);
        if (disp == null) { R.Warn("场景里没有 LanbaiActDispatcher：没人调 LanbaiCabinDriver.LanbaiTick，车厢一直是 t = 0 的样子（完整、管灯亮）"); return; }
        FieldInfo f = CabinArray(disp.GetType(), drv.GetType());
        if (f == null)
        {
            R.Warn("分发层还没有 LanbaiCabinDriver 的数组：先备份 Assets/Lanbai/Director/Runtime/LanbaiActDispatcher.cs（本地改过），点 蓝白/Director/1 Generate Dispatcher，" +
                   "等编译完，再点 蓝白/Director/2 Wire Scene。在那之前车厢一直是 t = 0 的样子（完整、管灯亮），不漂白、不侵蚀");
            return;
        }
        var so = new SerializedObject(disp);
        var p = so.FindProperty(f.Name);
        if (p == null || !p.isArray) { R.Warn("分发层的 " + f.Name + " 读不到：点 蓝白/Director/2 Wire Scene"); return; }
        p.arraySize = 1;
        p.GetArrayElementAtIndex(0).objectReferenceValue = drv;
        so.ApplyModifiedProperties();
        try { Lanbai.Udon.LanbaiUdonPrograms.CopyProxyToUdon(disp); R.Line("Director: " + Path(disp.transform) + "." + f.Name + " = [" + DriverName + "]"); }
        catch (Exception e) { R.Err("Director CopyProxyToUdon: " + e.Message + "：点 蓝白/Director/2 Wire Scene"); }
        CheckDispatcherSource(disp, f, drv.GetType(), R);
    }

    // Director README §3 #7 / D-33 review #2: LanbaiCabinDriver's window is the whole film. Without LanbaiTakesOverNothing()
    // the generated dispatcher puts it into windowsFlat, LanbaiCovered(t) is true everywhere and LB_Journey (README_集成)
    // switches the placeholder groups off in acts 6 / 7b / 8 / 10 / 11. Read only: the driver type, by reflection.
    static void CheckDriverInterface(Component drv, Rep R)
    {
        if (drv == null) return;
        var m = drv.GetType().GetMethod("LanbaiTakesOverNothing", BindingFlags.Public | BindingFlags.Instance, null, Type.EmptyTypes, null);
        float[] w = Window(drv);
        string win = w != null ? " [" + w[0].ToString("0.##") + ", " + w[1].ToString("0.##") + "]" : "";
        if (m == null || m.ReturnType != typeof(bool))
            R.Warn("LanbaiCabinDriver 没有 public bool LanbaiTakesOverNothing()（Cabin/Scripts 是旧的？）：它的全片窗口" + win + "会进分发层的 windowsFlat，" +
                   "LanbaiCovered(t) 处处为真，LB_Journey 会在第 6、7b、8、10、11 幕把占位组全关掉。同步新的 Cabin/Scripts/LanbaiCabinDriver.cs 再点 蓝白/Director/1 Generate");
        else R.Line("LanbaiCabinDriver window" + win + ", LanbaiTakesOverNothing() = true (not in windowsFlat once the dispatcher is generated with it)");
        if (w != null && w[1] < FilmEnd)
            R.Warn("LanbaiCabinDriver.LanbaiWindow() 到 " + w[1].ToString("0.##") + " 就结束了，片尾是 " + FilmEnd.ToString("0.##") +
                   "：之后进来的人、跳到之后的，车厢停在 Start() 的 t = 0（收音机表盘亮着）。同步新的 Cabin/Scripts/LanbaiCabinDriver.cs");
    }

    // The generated dispatcher leaves a driver's window out of windowsFlat only if 1 Generate ran while the driver had
    // LanbaiTakesOverNothing() (LanbaiDirectorGen writes 'if (!dK[i].LanbaiTakesOverNothing())'). Read from its source text;
    // in Play also windowsFlat itself (its Start() fills it; read from the UdonBehaviour, the U# proxy is not updated in Play).
    static void CheckDispatcherSource(Component disp, FieldInfo f, Type drvType, Rep R)
    {
        bool has = drvType.GetMethod("LanbaiTakesOverNothing", BindingFlags.Public | BindingFlags.Instance, null, Type.EmptyTypes, null) != null;
        var mb = disp as MonoBehaviour;
        var ms = mb != null ? MonoScript.FromMonoBehaviour(mb) : null;
        string src = ms != null ? ms.text : null;
        if (src == null) R.Warn("分发层的源码读不到：在生成的 LanbaiActDispatcher.cs 里找 “if (!" + f.Name + "[i].LanbaiTakesOverNothing())” 这一行");
        else if (src.Contains("if (!" + f.Name + "[i].LanbaiTakesOverNothing())")) R.Line("Director: the generated dispatcher keeps " + f.Name + " (LanbaiCabinDriver) out of windowsFlat");
        else if (has)
            R.Warn("分发层是在车厢驱动还没有 LanbaiTakesOverNothing() 时生成的：" + f.Name + " 的全片窗口在 windowsFlat 里，LanbaiCovered(t) 处处为真。" +
                   "先备份 LanbaiActDispatcher.cs，再点 蓝白/Director/1 Generate Dispatcher → 等编译完 → 2 Wire Scene");
        if (!Application.isPlaying) return;
        var flat = UdonVar(disp, "windowsFlat") as float[];
        if (flat == null) { R.Warn("Play 里读不到分发层的 windowsFlat：在 Lanbai/Director 的 Inspector 里看，里面不该有 [−600, 100000] 这样的全片窗口"); return; }
        R.Line("Director windowsFlat (Play): " + flat.Length / 2 + " window(s)");
        for (int i = 0; i + 1 < flat.Length; i += 2)
                if (flat[i] <= 0f && flat[i + 1] >= FilmEnd)
                    R.Err("分发层的 windowsFlat 里有一个全片窗口 [" + flat[i].ToString("0.##") + ", " + flat[i + 1].ToString("0.##") + "]：LanbaiCovered(t) 处处为真，" +
                          "LB_Journey 会把第 6、7b、8、10、11 幕的占位组全关掉。哪个驱动报的，看 蓝白/Director/3 Report；它要有 LanbaiTakesOverNothing()，然后重新 1 Generate");
    }

    static FieldInfo CabinArray(Type disp, Type drv)
    {
        foreach (var f in disp.GetFields(BindingFlags.Public | BindingFlags.Instance))
            if (f.FieldType.IsArray && f.FieldType.GetElementType() == drv) return f;
        return null;
    }

    static void MakeWaterlines(Transform busRoot, Transform ours, List<Renderer> glassRs, int layerBus, List<UnityEngine.Object> save, Rep R)
    {
        if (One("LanbaiAct07Driver", null) == null) { R.Line("waterlines: no LanbaiAct07Driver in the scene, none made"); return; }
        Material mat = null;
        if (busRoot != null)
            foreach (var r in busRoot.GetComponentsInChildren<Renderer>(true))
                if (r.name == WaterlineName && !r.transform.IsChildOf(ours) && r.sharedMaterial != null) { mat = r.sharedMaterial; break; }
        if (mat == null)
        {
            var sh = Shader.Find("Lanbai/SeaWaterline");
            if (sh == null) { R.Warn("Lanbai/SeaWaterline 不在：新车窗上没有第 7 幕入水 / 出水的水线"); return; }
            mat = LanbaiBusBuild.GetOrCreate("M_Bus_SeaWaterline", sh, GenMatDir);
            save.Add(mat);
        }
        int n = 0;
        foreach (var pane in glassRs)
        {
            var mf0 = pane.GetComponent<MeshFilter>();
            if (mf0 == null || mf0.sharedMesh == null) continue;
            var g = new GameObject(WaterlineName);
            g.transform.SetParent(pane.transform, false);
            g.layer = layerBus >= 0 ? layerBus : pane.gameObject.layer;
            var mf = g.AddComponent<MeshFilter>(); mf.sharedMesh = mf0.sharedMesh;
            var mr = g.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat; mr.enabled = false;   // LanbaiAct07Driver switches them
            mr.shadowCastingMode = ShadowCastingMode.Off; mr.receiveShadows = false;
            n++;
        }
        R.Line("waterlines: " + n + " pane copies (" + mat.name + ")");
    }

    // ------------------------------------------------------------------------------------------------ switch
    static void Switch(bool useNew, Rep R)
    {
        Component journey = One("LB_Journey", R);
        Transform busRoot = Field(journey, "busRoot") as Transform;
        Transform ours = OurRoot(busRoot);
        if (ours == null) { R.Err("没有 " + RootName + "：先点「搭建」"); return; }
        var newParts = new List<GameObject>();
        foreach (string n in new[] { ModelName, SeatsName, CollidersName })
        {
            var t = ours.Find(n);
            if (t != null) newParts.Add(t.gameObject); else R.Warn(Path(ours) + "/" + n + " 不在");
        }
        var oldParts = new List<GameObject>();
        if (busRoot != null)
            foreach (Transform c in busRoot)
                if (c != ours && Array.IndexOf(V1Parts, c.name) >= 0) oldParts.Add(c.gameObject);
        if (journey != null && oldParts.Count == 0) R.Warn("LB_Journey.busRoot 下没有旧车的 Model / Seats / Colliders / Label：只开关了新车");
        // the v1 depart button (LB_DepartButton) lives in the v1 Model: out of it first, or nobody can depart; into the new
        // cabin when it is outside it. 用旧车 puts it back where it was (the marker).
        if (busRoot != null)
        {
            if (useNew) MoveDepartButtons(busRoot, oldParts, R);
            else RestoreDepartButtons(busRoot, R);
        }
        foreach (var g in oldParts) SetActive(g, !useNew, R);
        foreach (var g in newParts) SetActive(g, useNew, R);
        var drvT = ours.Find(DriverName);
        if (drvT != null) SetActive(drvT.gameObject, true, R);      // the driver stays on in both (Director: always-active objects)
        PointWaterlines(useNew, busRoot, ours, R);
        // act 7a's front trails sit just outside the new bus's front (z 3.70): off while the v1 bus is in use (its dash is at
        // about z 3.8, they would be inside it), on with the new one (HANDOFF_LOG 10-25 22:30 #1, Act07_Sea/README_Act07a.md)
        foreach (var t in Named("Act07_TrailsFront")) SetActive(t.gameObject, useNew, R);
        if (busRoot != null) KeptChildren(busRoot, ours, R);
        EditorSceneManager.MarkSceneDirty(ours.gameObject.scene);
        R.Line("in use: " + (useNew ? "the new bus (" + Path(ours) + ")" : "the v1 bus (comparison; LanbaiCabinDriver keeps writing the cabin globals, the v1 shader does not read them)"));
    }

    // 用新车, every LB_DepartButton under busRoot. In the v1 Model it would go off with it: out to busRoot, world pose kept.
    // Outside BusLayout cabin_bounds (the v1 dash is at about z 3.8, the new cabin ends at Col_Front z 3.41) or stuck in a
    // BusLayout collider: onto DepartSpot (the bottom-centre of its bounds, rotation kept). Before it moves the first time,
    // an EditorOnly marker with its old parent and local pose goes beside it, and the report prints that pose.
    static void MoveDepartButtons(Transform busRoot, List<GameObject> oldParts, Rep R)
    {
        LanbaiBusBuild.Layout L;
        DropInLayout box;
        ReadLayout(out L, out box);
        bool haveBox = box != null && box.cabin_bounds != null && box.cabin_bounds.min != null && box.cabin_bounds.max != null;
        if (!haveBox) R.Warn(LanbaiBusBuild.LayoutPath + " 的 cabin_bounds 读不到：出发按钮只从旧 Model 里挪出来，没检查、没挪进新车厢");
        var busRenderers = Field(One("LB_Journey", null), "busRenderers") as Renderer[];
        var buttons = DepartButtons(busRoot);
        foreach (var c in buttons)
        {
            Transform t = c.transform;
            string oldPose = PoseText(t);
            Vector3 p = busRoot.InverseTransformPoint(BoundsOf(t).center);
            bool inV1 = oldParts.Any(g => t.IsChildOf(g.transform));
            bool outside = haveBox && !InBox(p, box.cabin_bounds);
            string stuck = StuckIn(p, L);
            bool move = outside || stuck.Length > 0;
            if ((inV1 || move) && FindMarker(busRoot, t.name) == null)
            {
                MakeMarker(t);
                R.Line("depart button " + Path(t) + ": old pose " + oldPose + " (centre in the bus frame " + Fmt(p) + ") -> kept in the EditorOnly marker " +
                       DepartMarker + t.name + "; 「用旧车（对照）」 puts it back");
            }
            if (inV1)
            {
                string from = Path(t);
                Undo.SetTransformParent(t, busRoot, "Bus drop-in: depart button out of the v1 Model");
                R.Line("moved the depart button " + from + " -> " + Path(t) + " (world pose kept)");
            }
            if (move)
            {
                Bounds b = BoundsOf(t);
                Vector3 bottom = busRoot.InverseTransformPoint(new Vector3(b.center.x, b.min.y, b.center.z));
                Undo.RecordObject(t, "Bus drop-in: depart button onto the new dash");
                t.position += busRoot.TransformVector(DepartSpot - bottom);
                R.Line("depart button " + (outside ? "was outside the new cabin" : "was in " + stuck.Trim()) + " at " + Fmt(p) + " -> on top of Col_Dash: bottom-centre " +
                       Fmt(DepartSpot) + " (right of the steering wheel, x -0.40), size " + Fmt(b.size) + ", rotation kept, now " + PoseText(t) +
                       "。进 Play 看一眼点不点得到（它的网格还是旧材质，比仪表台面高约 3 cm）");
                if (b.size.y > 0.06f) R.Warn("出发按钮高 " + b.size.y.ToString("0.00") + " m（> 0.06）：从主座位看可能挡到挡风玻璃的下沿。进 Play 看一眼");
            }
            Vector3 q = busRoot.InverseTransformPoint(BoundsOf(t).center);
            if (haveBox && !InBox(q, box.cabin_bounds))
                R.Err("出发按钮 " + Path(t) + " 在新车厢外（中心 " + Fmt(q) + "，cabin_bounds " + Fmt(V(box.cabin_bounds.min)) + " – " + Fmt(V(box.cabin_bounds.max)) +
                      "）：用着新车就没人点得到。挪到车厢里，比如 Col_Dash 顶上 " + Fmt(DepartSpot));
            else if (!move) R.Line("depart button " + Path(t) + " at " + Fmt(q) + ": inside the new cabin, left where it is");
            if (busRenderers != null)
                foreach (var r in t.GetComponentsInChildren<Renderer>(true))
                    if (Array.IndexOf(busRenderers, r) >= 0) { R.Warn("出发按钮的 renderer 在 LB_Journey.busRenderers 里：第 7–9 幕它自己还会棋盘溶解（小东西，旅程中也用不到）"); break; }
        }
        if (buttons.Count == 0) R.Warn("没找到 LB_DepartButton（出发按钮）：查一下它在哪；它要是在旧车的 Model 里，关掉旧车以后就没人能出发");
    }

    // 用旧车: each depart button with a marker goes back to the marker's parent and local pose; the marker goes
    static void RestoreDepartButtons(Transform busRoot, Rep R)
    {
        foreach (var c in DepartButtons(busRoot))
        {
            Transform t = c.transform, m = FindMarker(busRoot, t.name);
            if (m == null) continue;
            string from = Path(t);
            if (t.parent != m.parent) Undo.SetTransformParent(t, m.parent, "Bus drop-in: depart button back to its v1 pose");
            Undo.RecordObject(t, "Bus drop-in: depart button back to its v1 pose");
            t.localPosition = m.localPosition; t.localRotation = m.localRotation; t.localScale = m.localScale;
            Undo.DestroyObjectImmediate(m.gameObject);
            R.Line("depart button " + from + " -> back to its v1 pose " + PoseText(t));
        }
    }

    static List<Component> DepartButtons(Transform busRoot)
    {
        return busRoot.GetComponentsInChildren<Component>(true).Where(c => c != null && c.GetType().Name == "LB_DepartButton").ToList();
    }

    static Transform FindMarker(Transform busRoot, string button)
    {
        foreach (var x in busRoot.GetComponentsInChildren<Transform>(true)) if (x.name == DepartMarker + button) return x;
        return null;
    }

    // an empty beside the button (same parent, same local pose), tagged EditorOnly (not in the build)
    static void MakeMarker(Transform t)
    {
        var m = new GameObject(DepartMarker + t.name);
        Undo.RegisterCreatedObjectUndo(m, "Bus drop-in: depart button v1 pose");
        m.tag = "EditorOnly";
        m.transform.SetParent(t.parent, false);
        m.transform.localPosition = t.localPosition; m.transform.localRotation = t.localRotation; m.transform.localScale = t.localScale;
    }

    static string PoseText(Transform t)
    {
        return (t.parent != null ? Path(t.parent) : "(scene root)") + " local " + Fmt(t.localPosition) + " euler " + Fmt(t.localEulerAngles);
    }

    // the BusLayout colliders that hold p (bus frame), as " Col_A Col_B"
    static string StuckIn(Vector3 p, LanbaiBusBuild.Layout L)
    {
        string where = "";
        if (L == null || L.colliders == null) return where;
        foreach (var col in L.colliders)
        {
            Vector3 cc = V(col.c), hs = V(col.s) * 0.5f;
            if (Mathf.Abs(p.x - cc.x) < hs.x && Mathf.Abs(p.y - cc.y) < hs.y && Mathf.Abs(p.z - cc.z) < hs.z) where += " " + col.name;
        }
        return where;
    }

    static bool InBox(Vector3 p, Box b)
    {
        Vector3 mn = V(b.min), mx = V(b.max);
        return p.x >= mn.x && p.x <= mx.x && p.y >= mn.y && p.y <= mx.y && p.z >= mn.z && p.z <= mx.z;
    }

    // world bounds of a transform's box colliders (else its meshes, else its position), also when it is inactive (the
    // renderer / collider bounds are empty then)
    static Bounds BoundsOf(Transform t)
    {
        bool any = false;
        var b = new Bounds(t.position, Vector3.zero);
        foreach (var bc in t.GetComponentsInChildren<BoxCollider>(true))
            Encapsulate(ref b, ref any, bc.transform.localToWorldMatrix, new Bounds(bc.center, bc.size));
        if (!any)
            foreach (var mf in t.GetComponentsInChildren<MeshFilter>(true))
                if (mf.sharedMesh != null) Encapsulate(ref b, ref any, mf.transform.localToWorldMatrix, mf.sharedMesh.bounds);
        return b;
    }

    static void Encapsulate(ref Bounds b, ref bool any, Matrix4x4 m, Bounds local)
    {
        for (int i = 0; i < 8; i++)
        {
            var corner = local.center + Vector3.Scale(local.extents, new Vector3((i & 1) == 0 ? -1f : 1f, (i & 2) == 0 ? -1f : 1f, (i & 4) == 0 ? -1f : 1f));
            var w = m.MultiplyPoint3x4(corner);
            if (!any) { b = new Bounds(w, Vector3.zero); any = true; }
            else b.Encapsulate(w);
        }
    }

    static void ReadLayout(out LanbaiBusBuild.Layout L, out DropInLayout box)
    {
        L = null; box = null;
        var text = AssetDatabase.LoadAssetAtPath<TextAsset>(LanbaiBusBuild.LayoutPath);
        if (text == null) return;
        try { L = JsonUtility.FromJson<LanbaiBusBuild.Layout>(text.text); box = JsonUtility.FromJson<DropInLayout>(text.text); }
        catch (Exception) { }
    }

    static void PointWaterlines(bool useNew, Transform busRoot, Transform ours, Rep R)
    {
        Component sea = One("LanbaiAct07Driver", null);
        if (sea == null) return;
        var list = new List<UnityEngine.Object>();
        Transform scope = useNew ? ours : busRoot;
        if (scope != null)
            foreach (var r in scope.GetComponentsInChildren<Renderer>(true))
                if (r.name == WaterlineName && (useNew || !r.transform.IsChildOf(ours))) list.Add(r);
        if (list.Count == 0) { R.Warn("LanbaiAct07Driver.waterlines 没改：" + (useNew ? "新车" : "旧车") + "上没有 " + WaterlineName); return; }
        var so = new SerializedObject(sea);
        var p = so.FindProperty("waterlines");
        if (p == null || !p.isArray) { R.Warn("LanbaiAct07Driver 没有 waterlines 数组：没改"); return; }
        p.arraySize = list.Count;
        for (int i = 0; i < list.Count; i++) p.GetArrayElementAtIndex(i).objectReferenceValue = list[i];
        so.ApplyModifiedProperties();
        try { Lanbai.Udon.LanbaiUdonPrograms.CopyProxyToUdon(sea); }
        catch (Exception e) { R.Err("LanbaiAct07Driver CopyProxyToUdon: " + e.Message); }
        R.Line("LanbaiAct07Driver.waterlines = " + list.Count + " copies on the " + (useNew ? "new" : "v1") + " glass");
    }

    // what stays under the v1 root, and the two things there that can fight the new cabin
    static void KeptChildren(Transform busRoot, Transform ours, Rep R)
    {
        int layerBus = LayerMask.NameToLayer("Bus");
        foreach (Transform c in busRoot)
        {
            if (c == ours || Array.IndexOf(V1Parts, c.name) >= 0) continue;
            var comps = c.GetComponents<Component>().Where(x => x != null && !(x is Transform)).Select(x => x.GetType().Name).Distinct().ToArray();
            R.Line("  kept " + c.name + (c.gameObject.activeSelf ? "" : " (off)") + (comps.Length > 0 ? " [" + string.Join(", ", comps) + "]" : "") +
                   " at " + Fmt(busRoot.InverseTransformPoint(c.position)));
            var rp = c.GetComponent<ReflectionProbe>();
            if (rp != null && rp.mode != ReflectionProbeMode.Realtime)
                R.Warn(c.name + " 是烘好的反射探针（" + rp.mode + "），里面是旧车厢：新车的金属和漆会反射出旧车。用新车只开管灯重烘这一个，或者先关掉");
            var li = c.GetComponent<Light>();
            if (li != null && layerBus >= 0 && (li.cullingMask & (1 << layerBus)) != 0 && li.type == LightType.Point)
                R.Warn(c.name + " 的 culling 含 Bus 层：它会再照一遍新车厢（管灯光已经烘在 _CabinTubeLM 里）。只留 Player / PlayerLocal");
        }
    }

    // ------------------------------------------------------------------------------------------------ check (read only)
    public static string Check()
    {
        var R = new Rep();
        var sc = SceneManager.GetActiveScene();
        R.Line("scene " + sc.path + (sc.path == FormalScene ? "  <- 正式场景：两个搭建菜单都拒绝在这里搭（D-46 #3）" : ""));
        // inputs
        foreach (var sn in new[] { "Lanbai/Cabin", "Lanbai/ThinCloth", "Lanbai/BusGlass", "Lanbai/SeaWaterline" })
        {
            var sh = Shader.Find(sn);
            if (sh != null) R.Line("shader " + sn + ": " + AssetDatabase.GetAssetPath(sh));
            else if (sn == "Lanbai/SeaWaterline") R.Warn("shader " + sn + " 不在：新车窗上没有水线");
            else R.Err("shader " + sn + " 不在");
        }
        var layoutText = AssetDatabase.LoadAssetAtPath<TextAsset>(LanbaiBusBuild.LayoutPath);
        if (AssetDatabase.LoadAssetAtPath<GameObject>(LanbaiBusBuild.FbxPath) == null) R.Err("没有 " + LanbaiBusBuild.FbxPath);
        if (layoutText == null) R.Err("没有 " + LanbaiBusBuild.LayoutPath);
        CheckImport(R);
        var genMats = new List<Material>();
        if (AssetDatabase.IsValidFolder(GenMatDir))
            foreach (var g in AssetDatabase.FindAssets("t:Material", new[] { GenMatDir }))
                genMats.Add(AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(g)));
        CheckTextureTypes(genMats, true, R);
        CheckVertexCompression(R, true);
        int layerBus = LayerMask.NameToLayer("Bus");
        R.Line("layers: Bus " + layerBus + ", BusExterior " + LayerMask.NameToLayer("BusExterior"));
        if (layerBus < 0) R.Warn("layer Bus 不在");
        else
        {
            // what lights the cabin besides its baked tube map (bible §4.3: the moon = RenderSettings.sun, the rift light, act 7's lights)
            var lit = All(c => c is Light).Cast<Light>().Where(l => (l.cullingMask & (1 << layerBus)) != 0).ToList();
            R.Line("lights reaching layer Bus: " + lit.Count);
            foreach (var l in lit)
                R.Line("  " + Path(l.transform) + " " + l.type + " " + l.renderMode + (l.isActiveAndEnabled ? "" : " (off now)") +
                       (RenderSettings.sun == l ? " = RenderSettings.sun" : ""));
        }
        string why;
        var types = ProgramTypes(out why);
        if (types == null) R.Err(why);
        else
        {
            string rep;
            if (!Lanbai.Udon.LanbaiUdonPrograms.AllReady(types, out rep)) R.Warn("U# 程序资产没全好（搭建菜单会建、会等）：\n" + rep);
            else R.Line("U# programs ready: " + string.Join(", ", types.Select(t => t.Name).ToArray()));
        }

        // the scene
        Component journey = One("LB_Journey", R);
        Transform busRoot = Field(journey, "busRoot") as Transform;
        if (journey == null) R.Warn("没有 LB_Journey");
        else if (busRoot == null) R.Warn("LB_Journey.busRoot 是空的");
        else CheckIdentity(busRoot, R);
        Transform ours = OurRoot(busRoot);
        bool newInUse = false;
        if (ours == null) R.Warn("没有 " + RootName + "：还没搭");
        else
        {
            var m = ours.Find(ModelName);
            bool newOn = m != null && m.gameObject.activeInHierarchy;
            bool oldOn = busRoot != null && busRoot.Find("Model") != null && busRoot.Find("Model").gameObject.activeInHierarchy;
            R.Line("bus in use: " + (newOn && !oldOn ? "new" : !newOn && oldOn ? "v1 (comparison)" : newOn ? "BOTH" : "NONE"));
            if (newOn && oldOn) R.Err("两辆车都开着：点「用新车」或「用旧车（对照）」");
            if (!newOn && !oldOn) R.Err("两辆车都关着");
            newInUse = newOn && !oldOn;
            var ns = ours.Find(SeatsName);
            int stations = ns != null ? ns.childCount : 0;
            R.Line("new stations: " + stations + (ns != null && !ns.gameObject.activeInHierarchy ? " (off)" : ""));
        }
        // the writers of the cabin globals (D-22: one at a time)
        var drvs = All(c => c.GetType().Name == "LanbaiCabinDriver");
        if (drvs.Count == 0) R.Warn("没有 LanbaiCabinDriver：Lanbai/Cabin 读到的 _Udon_CabinLightmap 是 0（车厢全黑）");
        if (drvs.Count > 1) R.Err(drvs.Count + " 个 LanbaiCabinDriver：同一组全局量有两个写的人，留一个");
        foreach (var d in drvs)
        {
            if (!d.gameObject.activeInHierarchy) R.Err(Path(d.transform) + " 在关着的物体上：分发层调不动它");
            var cr = Field(d, "cabinRenderers") as Array; var gr = Field(d, "glassRenderers") as Array;
            R.Line("LanbaiCabinDriver " + Path(d.transform) + ": cabin " + (cr != null ? cr.Length : 0) + ", glass " + (gr != null ? gr.Length : 0) +
                   ", journey " + (Field(d, "journey") as Component != null) + ", yieldToInside " + Field(d, "yieldToInside") +
                   " [" + Field(d, "insideFrom") + ", " + Field(d, "insideTo") + "]");
        }
        Component inside = One("LanbaiInsideDriver", R);
        float[] w = Window(inside);
        if (inside != null && w != null) R.Line("LanbaiInsideDriver window [" + w[0].ToString("0.00") + ", " + w[1].ToString("0.00") + "] (it writes ambient / dial / slice there)");
        foreach (var d in drvs)
            if (inside != null && !(Field(d, "yieldToInside") is bool b && b)) R.Err("有门内驱动，但 LanbaiCabinDriver.yieldToInside 关着：门内窗口里两个人写环境色和表盘");
        if (drvs.Count > 0) CheckDriverInterface(drvs[0], R);
        CheckOtherWriters(R);
        // the Director
        Component disp = One("LanbaiActDispatcher", R);
        if (disp == null) R.Warn("没有 LanbaiActDispatcher");
        else if (drvs.Count > 0)
        {
            FieldInfo f = CabinArray(disp.GetType(), drvs[0].GetType());
            if (f == null) R.Warn("分发层没有 LanbaiCabinDriver 的数组：备份 LanbaiActDispatcher.cs，蓝白/Director/1 Generate Dispatcher → 编译完 → 2 Wire Scene");
            else
            {
                var arr = f.GetValue(disp) as Array;
                bool has = arr != null && arr.Cast<object>().Any(o => o as Component == drvs[0]);
                if (has) R.Line("Director: " + f.Name + " -> " + Path(drvs[0].transform));
                else R.Err("分发层的 " + f.Name + " 没指着 " + Path(drvs[0].transform) + "：点 蓝白/Director/2 Wire Scene");
                CheckDispatcherSource(disp, f, drvs[0].GetType(), R);
            }
        }
        // the sea's waterlines, the depart button, LB_Journey (read only: suggestions)
        Component sea = One("LanbaiAct07Driver", null);
        var wl = Field(sea, "waterlines") as Renderer[];
        if (sea != null)
        {
            int onNew = wl == null ? 0 : wl.Count(r => r != null && ours != null && r.transform.IsChildOf(ours));
            R.Line("LanbaiAct07Driver.waterlines: " + (wl != null ? wl.Length : 0) + " (" + onNew + " on the new glass)");
        }
        if (busRoot != null)
        {
            LanbaiBusBuild.Layout L;
            DropInLayout box;
            ReadLayout(out L, out box);
            bool haveBox = box != null && box.cabin_bounds != null && box.cabin_bounds.min != null && box.cabin_bounds.max != null;
            var buttons = DepartButtons(busRoot);
            foreach (var c in buttons)
            {
                Vector3 q = busRoot.InverseTransformPoint(BoundsOf(c.transform).center);
                var marker = FindMarker(busRoot, c.transform.name);
                R.Line("depart button " + Path(c.transform) + (c.gameObject.activeInHierarchy ? "" : "  <- OFF: nobody can depart") + " centre " + Fmt(q) +
                       (marker != null ? ", v1 pose kept in " + Path(marker) : ""));
                if (!c.gameObject.activeInHierarchy) R.Err("出发按钮关着");
                if (!newInUse || !haveBox) continue;
                if (!InBox(q, box.cabin_bounds))
                    R.Err("用着新车，出发按钮却在新车厢外（中心 " + Fmt(q) + "，cabin_bounds " + Fmt(V(box.cabin_bounds.min)) + " – " + Fmt(V(box.cabin_bounds.max)) +
                          "）：没人点得到。点一次「用新车」（它会把按钮放到 Col_Dash 顶上 " + Fmt(DepartSpot) + "），或者手挪进车厢");
                else
                {
                    string stuck = StuckIn(q, L);
                    if (stuck.Length > 0) R.Warn("出发按钮的中心在新车的碰撞体里（" + stuck.Trim() + "）：交互的射线可能先打到碰撞体。挪到碰撞体外面");
                }
            }
            if (buttons.Count == 0) R.Warn("busRoot 下没有 LB_DepartButton");
            if (ours != null) KeptChildren(busRoot, ours, R);
        }
        if (journey != null) JourneyNotes(journey, busRoot, ours, layoutText, R);
        return R.Finish("check (read only, nothing written)");
    }

    // LB_Journey is the local integrator's script (Cabin/给总控_shader.md §3): read only here, these are suggestions
    static void JourneyNotes(Component journey, Transform busRoot, Transform ours, TextAsset layoutText, Rep R)
    {
        DropInLayout cb = null;
        try { cb = layoutText != null ? JsonUtility.FromJson<DropInLayout>(layoutText.text) : null; }
        catch (Exception) { }
        object bmin = Field(journey, "busMin"), bmax = Field(journey, "busMax"), eye = Field(journey, "heroEye");
        if (cb != null && cb.cabin_bounds != null && bmin is Vector3 a && bmax is Vector3 b)
        {
            Vector3 cmin = V(cb.cabin_bounds.min), cmax = V(cb.cabin_bounds.max);
            if ((a - cmin).sqrMagnitude > 1e-4f || (b - cmax).sqrMagnitude > 1e-4f)
                R.Line("suggest LB_Journey.busMin / busMax " + Fmt(a) + " / " + Fmt(b) + " -> cabin_bounds " + Fmt(cmin) + " / " + Fmt(cmax) +
                       "（出发时把车外的人接进来用；旧的盒子比新车厢大）");
        }
        if (eye is Vector3 e && (e - HeroEye).sqrMagnitude > 1e-4f)
            R.Line("suggest LB_Journey.heroEye " + Fmt(e) + " -> " + Fmt(HeroEye) + "（D-28；只有旧诗句用它，接了 LanbaiPoemDriver 以后不影响画面）");
        if (ours != null)
            foreach (var fld in new[] { "busRenderers", "glassRenderers", "cabinTubes" })
            {
                var arr = Field(journey, fld) as Renderer[];
                if (arr == null) continue;
                int mine = arr.Count(r => r != null && r.transform.IsChildOf(ours));
                if (mine > 0) R.Err("LB_Journey." + fld + " 里有 " + mine + " 个新车的 renderer：它们会被 SetBusAlpha / 管灯 MPB 改，和 LanbaiCabinDriver 打架（Cabin/给总控_shader.md §3）。拿掉");
                else R.Line("LB_Journey." + fld + ": " + arr.Length + " (all v1: harmless while the v1 bus is off)");
            }
        var spawn = Field(journey, "spawnInBus") as Transform;
        if (spawn != null && busRoot != null && cb != null && cb.cabin_bounds != null)
        {
            Vector3 p = busRoot.InverseTransformPoint(spawn.position), cmin = V(cb.cabin_bounds.min), cmax = V(cb.cabin_bounds.max);
            bool inside = p.x > cmin.x && p.x < cmax.x && p.z > cmin.z && p.z < cmax.z && p.y >= cmin.y && p.y < cmax.y;
            if (inside) R.Line("spawnInBus " + Fmt(p) + ": inside the new cabin");
            else R.Warn("spawnInBus " + Fmt(p) + " 不在新车厢里：挪到过道，比如 (-0.05, 0.64, -1.40)");
        }
        // the radio's sound: the v1 RadioAnchor (0.15, 1.36, 2.88) stays under busRoot; the new radio sits at BusLayout
        // radio.centre (0.165, 1.461, 3.107), 25 cm further forward and 10 cm higher (bus_spec.py RADIO_C, D-14)
        if (busRoot != null && cb != null && cb.radio != null && cb.radio.centre != null && cb.radio.centre.Length >= 3)
        {
            Vector3 rc = V(cb.radio.centre);
            var anchors = new List<Transform>();
            var ra = busRoot.Find("RadioAnchor");
            if (ra != null) anchors.Add(ra);
            foreach (var fld in new[] { "radio", "radioNoise" })
            {
                var src = Field(journey, fld) as Component;
                if (src != null && !anchors.Contains(src.transform)) anchors.Add(src.transform);
            }
            foreach (var anc in anchors)
            {
                Vector3 p = busRoot.InverseTransformPoint(anc.position);
                if ((p - rc).magnitude > 0.03f)
                    R.Line("suggest " + Path(anc) + " " + Fmt(p) + " -> " + Fmt(rc) + "（新车收音机的中心，BusLayout radio.centre；差 " + (p - rc).magnitude.ToString("0.00") +
                           " m。声音和看到的收音机对上。只列不改）");
                else R.Line(Path(anc) + " " + Fmt(p) + ": at the new radio");
            }
        }
    }

    // ------------------------------------------------------------------------------------------------ checks shared by build / check
    static bool Guard(Rep R)
    {
        if (EditorApplication.isPlayingOrWillChangePlaymode) { R.Err("Play 模式里不改场景：回到编辑模式再点"); return false; }
        if (SceneManager.GetActiveScene().path == FormalScene)
        {
            R.Err("这是正式场景 " + FormalScene + "：进正式场景要本地技术验收和小楠的美术确认（D-46 #3）。这几个菜单只在 FullPreview 或测试场景里用");
            return false;
        }
        return true;
    }

    static void CheckIdentity(Transform busRoot, Rep R)
    {
        bool ok = busRoot.position.sqrMagnitude < 1e-6f && Quaternion.Angle(busRoot.rotation, Quaternion.identity) < 0.01f &&
                  (busRoot.lossyScale - Vector3.one).sqrMagnitude < 1e-6f;
        if (ok) R.Line("busRoot " + Path(busRoot) + ": origin, identity (bus frame = world frame, as Lanbai/Cabin needs)");
        else R.Err("LB_Journey.busRoot " + Path(busRoot) + " 不在原点或者有旋转 / 缩放（" + Fmt(busRoot.position) + "）：Lanbai/Cabin 的侵蚀、座位球、地板洞都按“车坐标 = 世界坐标”算" +
                   "（LanbaiCabinCommon.cginc 头注：跑步机，车不动）");
    }

    // D-22: nobody else may write _Udon_CabinLightmap / Bleach / Fade while LanbaiCabinDriver does
    static void CheckOtherWriters(Rep R)
    {
        foreach (var c in All(x => x.GetType().Name == "LanbaiBusSliceGlobals"))
        {
            var b = c as Behaviour;
            if (b != null && b.isActiveAndEnabled) R.Err(Path(c.transform) + "（LanbaiBusSliceGlobals，切片用）开着：它每帧写同一组车厢全局量，和 LanbaiCabinDriver 打架。删掉切片（Lanbai_BusSlice）");
            else R.Warn(Path(c.transform) + "：LanbaiBusSliceGlobals 在场景里（关着）。切片不该在 FullPreview 里，删掉");
        }
        foreach (var c in All(x => x.GetType().Name.EndsWith("TestClock", StringComparison.Ordinal)))
        {
            var b = c as Behaviour;
            if (b != null && b.isActiveAndEnabled)
                R.Warn(Path(c.transform) + "（" + c.GetType().Name + "）开着：测试时钟绕过分发层，按自己的 t 去推门内 / 门的驱动（门内驱动写环境色和表盘）。FullPreview 里要关着");
        }
    }

    static void CheckImport(Rep R)
    {
        var mi = AssetImporter.GetAtPath(LanbaiBusBuild.FbxPath) as ModelImporter;
        if (mi == null) return;
        if (mi.generateSecondaryUV)
            R.Err("Bus.fbx 的 Generate Lightmap UVs 开着：Unity 换掉了 uv1（_CabinTubeLM 图集）。关掉（Cabin/Editor/LanbaiCabinImport.cs 本来会关：Cabin/Editor 拷了吗？）");
        if (mi.meshCompression != ModelImporterMeshCompression.Off) R.Warn("Bus.fbx 的 Mesh Compression 是 " + mi.meshCompression + "（要 Off，Cabin/README.md §5）");
    }

    // Texture import types (read only; fixing one is an import setting = a .meta write, the integrator's): the textures the
    // given materials use, and with byName also the part maps (Bus/Textures/Parts/*_Normal_* / *_Mask_*) and the tube light
    // map by name, so the check works before the first build. ERROR: a normal map not imported as Normal map, a mask / the
    // light map not Default + linear. WARNING: the rain glass's data maps (Rain/README_Rain.md §1).
    static void CheckTextureTypes(IEnumerable<Material> mats, bool byName, Rep R)
    {
        var seen = new HashSet<string>();
        int n = 0, bad = 0;
        foreach (var m in mats)
        {
            if (m == null) continue;
            foreach (var prop in NormalProps.Concat(LinearProps).Concat(RainProps))
            {
                if (!m.HasProperty(prop)) continue;
                var tex = m.GetTexture(prop);
                string path = tex != null ? AssetDatabase.GetAssetPath(tex) : null;
                if (string.IsNullOrEmpty(path) || !seen.Add(path)) continue;
                n++;
                if (!TextureTypeOk(path, prop, R)) bad++;
            }
        }
        if (byName)
        {
            var named = new List<KeyValuePair<string, string>>();
            string parts = LanbaiBusBuild.Tex + "Parts";
            if (AssetDatabase.IsValidFolder(parts))
                foreach (var g in AssetDatabase.FindAssets("t:Texture2D", new[] { parts }))
                {
                    string path = AssetDatabase.GUIDToAssetPath(g), name = System.IO.Path.GetFileNameWithoutExtension(path);
                    if (name.Contains("_Normal_")) named.Add(new KeyValuePair<string, string>(path, "_PartNormal"));
                    else if (name.Contains("_Mask_")) named.Add(new KeyValuePair<string, string>(path, "_PartMask"));
                }
            named.Add(new KeyValuePair<string, string>(LanbaiBusBuild.Tex + "Cabin_TubeLM.exr", "_CabinTubeLM"));
            foreach (var kv in named)
            {
                if (AssetImporter.GetAtPath(kv.Key) == null || !seen.Add(kv.Key)) continue;
                n++;
                if (!TextureTypeOk(kv.Key, kv.Value, R)) bad++;
            }
        }
        R.Line("texture import types: " + n + " texture(s) checked, " + bad + " wrong");
    }

    static bool TextureTypeOk(string path, string prop, Rep R)
    {
        var ti = AssetImporter.GetAtPath(path) as TextureImporter;
        if (ti == null) return true;
        string now = ti.textureType + (ti.sRGBTexture ? ", sRGB" : ", linear");
        if (Array.IndexOf(NormalProps, prop) >= 0)
        {
            if (ti.textureType == TextureImporterType.NormalMap) return true;
            R.Err(path + "（" + prop + "）导入成了 " + now + "，要 Normal map：shader 用 UnpackScaleNormal 解，按颜色导入会把每个法线都掰歪。" +
                  "同步新的 Cabin/Editor/LanbaiCabinImport.cs 以后对它右键 Reimport；还不对就在 Inspector 里把 Texture Type 改成 Normal map");
            return false;
        }
        if (ti.textureType == TextureImporterType.Default && !ti.sRGBTexture) return true;
        if (Array.IndexOf(RainProps, prop) >= 0)
        {
            R.Warn(path + "（" + prop + "，雨玻璃）导入成了 " + now + "：Rain/README_Rain.md §1 要 Default、sRGB 关（法线也一样，shader 自己解包）");
            return false;
        }
        R.Err(path + "（" + prop + "）导入成了 " + now + "：它是数据（遮罩 / 管灯光照图），要 Default、sRGB (Color Texture) 关。" +
              "同步新的 Cabin/Editor/LanbaiCabinImport.cs 以后对它右键 Reimport；还不对就在 Inspector 里取消 sRGB");
        return false;
    }

    // Color and TexCoord0-3 uncompressed (D-40b #3; the cabin light map and the exterior atlas are on uv1, the wear in the
    // vertex colour). Read only, the way the test tool reads it (LanbaiTestPreflight): the property by reflection, else the file.
    static void CheckVertexCompression(Rep R, bool strict)
    {
        string how;
        int m = VertexCompressionMask(out how);
        if (m < 0) { R.Warn("Vertex Compression 读不到（" + how + "）：Project Settings → Player 里看：Color、TexCoord0–3 都不能压缩（D-40b #3）"); return; }
        var bad = new List<string>();
        string[] names = { "Color", "TexCoord0", "TexCoord1", "TexCoord2", "TexCoord3" };
        int[] bits = { 3, 4, 5, 6, 7 };                             // 1 << VertexAttribute
        for (int i = 0; i < names.Length; i++) if ((m & (1 << bits[i])) != 0) bad.Add(names[i]);
        if (bad.Count == 0) { R.Line("Vertex Compression: Color, TexCoord0-3 uncompressed (" + how + ")"); return; }
        string s = "Vertex Compression 压缩着 " + string.Join("、", bad.ToArray()) + "（" + how + "）：车厢光照图和外观图集在 uv1、做旧在顶点色，压缩了会糊、会错位。" +
                   "改 ProjectSettings 先备份、经小楠确认（D-40b #3）";
        if (strict) R.Err(s); else R.Warn(s);
    }

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
            foreach (var line in File.ReadAllLines("ProjectSettings/ProjectSettings.asset"))
            {
                string t = line.Trim();
                const string key = "VertexChannelCompressionMask:";
                int m;
                if (t.StartsWith(key, StringComparison.Ordinal) && int.TryParse(t.Substring(key.Length).Trim(), out m)) { how = "ProjectSettings.asset"; return m; }
            }
        }
        catch (Exception) { }
        how = "两种读法都读不到";
        return -1;
    }

    // ------------------------------------------------------------------------------------------------ helpers
    // U# types the build needs ready (D-41): the driver; LanbaiBusSeat (the bus package's seat script: its program asset is
    // made even when LB_Seat is used, so every U# script under Assets/Lanbai has one, which the local Validate checks); the
    // local LB_Seat when the project has it
    static Type[] ProgramTypes(out string why)
    {
        why = null;
        var drv = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript("LanbaiCabinDriver");
        if (drv == null)
        {
            why = "LanbaiCabinDriver 找不到或者还没编完（Cabin/Scripts 拷到 Assets/Lanbai/Cabin/Scripts 了吗？Console 有没有红字？）";
            return null;
        }
        var list = new List<Type> { drv };
        var busSeat = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript("LanbaiBusSeat");
        if (busSeat != null) list.Add(busSeat);
        var lb = LocalSeatType();
        if (lb != null) list.Add(lb);
        return list.ToArray();
    }

    // the local v1 seat script (Assets/Lanbai/Scripts/LB_Seat.cs; FromLocal/full_preview/20261025-0103/review_sources/Scripts/
    // LB_Seat.cs.txt): Interact -> UseStation, OnStationEntered -> LanbaiPoemDriver.SetSeat(poemSeatIndex)
    static Type LocalSeatType()
    {
        var t = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript("LB_Seat");
        return t != null && t.GetField("station") != null ? t : null;
    }

    static bool IsExterior(string n)
    {
        return n.StartsWith("Bus_Exterior", StringComparison.Ordinal) || n.StartsWith("Wheel_", StringComparison.Ordinal) ||
               n.StartsWith("Wiper", StringComparison.Ordinal);
    }

    static Transform OurRoot(Transform busRoot)
    {
        if (busRoot != null) { var t = busRoot.Find(RootName); if (t != null) return t; }
        var all = Named(RootName);
        return all.Count > 0 ? all[0] : null;
    }

    static List<Transform> Named(string name)
    {
        var r = new List<Transform>();
        for (int i = 0; i < SceneManager.sceneCount; i++)
        {
            var sc = SceneManager.GetSceneAt(i);
            if (!sc.isLoaded) continue;
            foreach (var g in sc.GetRootGameObjects())
                foreach (var t in g.GetComponentsInChildren<Transform>(true))
                    if (t.name == name) r.Add(t);
        }
        return r;
    }

    static List<Component> All(Func<Component, bool> match)
    {
        var r = new List<Component>();
        for (int i = 0; i < SceneManager.sceneCount; i++)
        {
            var sc = SceneManager.GetSceneAt(i);
            if (!sc.isLoaded) continue;
            foreach (var g in sc.GetRootGameObjects())
                foreach (var c in g.GetComponentsInChildren<Component>(true))
                    if (c != null && match(c)) r.Add(c);
        }
        return r;
    }

    static Component One(string typeName, Rep R)
    {
        var l = All(c => c.GetType().Name == typeName);
        if (l.Count > 1 && R != null) R.Warn(l.Count + " 个 " + typeName + "：用第一个（" + Path(l[0].transform) + "）");
        return l.Count > 0 ? l[0] : null;
    }

    // a field of a U# proxy (or any component), by reflection: the local scripts are not in this repository
    static object Field(Component c, string name)
    {
        if (c == null) return null;
        var f = c.GetType().GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
        return f != null ? f.GetValue(c) : null;
    }

    // a variable of the UdonBehaviour behind a U# proxy (Play mode: the proxy's own fields are not updated), by reflection.
    // UdonBehaviour has GetProgramVariable(string) and GetProgramVariable<T>(string): GetMethod(name, types) can throw
    // AmbiguousMatchException, so the non-generic one is picked by hand. Any failure gives null (the caller warns).
    static object UdonVar(Component proxy, string name)
    {
        if (proxy == null) return null;
        foreach (var c in proxy.GetComponents<Component>())
        {
            if (c == null || c.GetType().Name != "UdonBehaviour") continue;
            try
            {
                MethodInfo m = null;
                foreach (var x in c.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance))
                {
                    if (x.Name != "GetProgramVariable" || x.IsGenericMethodDefinition) continue;
                    var ps = x.GetParameters();
                    if (ps.Length == 1 && ps[0].ParameterType == typeof(string)) { m = x; break; }
                }
                if (m == null) continue;
                var v = m.Invoke(c, new object[] { name });
                if (v != null) return v;
            }
            catch (Exception) { }
        }
        return null;
    }

    // a driver's LanbaiWindow() on its editor proxy (as 蓝白/Director/3 Report reads it)
    static float[] Window(Component c)
    {
        if (c == null) return null;
        try
        {
            var m = c.GetType().GetMethod("LanbaiWindow", BindingFlags.Public | BindingFlags.Instance, null, Type.EmptyTypes, null);
            var w = m != null ? m.Invoke(c, null) as float[] : null;
            return w != null && w.Length >= 2 ? w : null;
        }
        catch (Exception) { return null; }
    }

    static int NearestEye(Vector3[] eyes, LanbaiBusBuild.Seat s, out float dist)
    {
        dist = 0f;
        if (eyes == null || eyes.Length == 0) return 0;
        Vector3 e = s.eye_approx != null && s.eye_approx.Length >= 3 ? V(s.eye_approx) : V(s.station_pos);
        int best = 0;
        float bd = float.MaxValue;
        for (int k = 0; k < eyes.Length; k++)
        {
            float dx = eyes[k].x - e.x, dz = eyes[k].z - e.z, d = dx * dx + dz * dz;
            if (d < bd) { bd = d; best = k; }
        }
        dist = Mathf.Sqrt(bd);
        return best;
    }

    static bool Uv1Atlas(Renderer r)
    {
        var mf = r.GetComponent<MeshFilter>();
        var mesh = mf != null ? mf.sharedMesh : null;
        if (mesh == null) return false;
        var uv = new List<Vector2>();
        try { mesh.GetUVs(1, uv); }
        catch (Exception) { return false; }
        if (uv.Count == 0) return false;
        const float e = 1e-3f;
        foreach (var v in uv) if (v.x < -e || v.x > 1f + e || v.y < -e || v.y > 1f + e) return false;
        return true;
    }

    static void SetActive(GameObject g, bool on, Rep R)
    {
        if (g.activeSelf == on) return;
        Undo.RecordObject(g, "Bus drop-in switch");
        g.SetActive(on);
        R.Line("  " + Path(g.transform) + (on ? " on" : " off"));
    }

    static void SetFloat(SerializedObject so, string prop, float v, Rep R)
    {
        var p = so.FindProperty(prop);
        if (p != null) p.floatValue = v; else R.Warn("field missing: " + prop);
    }

    // AssetDatabase.SaveAssetIfDirty(Object) (Unity 2021.2+; the compile check's reference UnityEditor is 2021.1): by reflection.
    // Only what this build wrote, only under Bus/Generated/ - never AssetDatabase.SaveAssets (it would flush every dirty asset).
    static readonly MethodInfo SaveIfDirty = typeof(AssetDatabase).GetMethod("SaveAssetIfDirty", BindingFlags.Public | BindingFlags.Static,
                                                                             null, new[] { typeof(UnityEngine.Object) }, null);

    static void SaveEach(List<UnityEngine.Object> save, Rep R)
    {
        int n = 0;
        foreach (var a in save.Where(x => x != null).Distinct())
        {
            string p = AssetDatabase.GetAssetPath(a);
            if (string.IsNullOrEmpty(p) || !p.StartsWith(GenDir + "/", StringComparison.Ordinal)) continue;
            if (SaveIfDirty != null) SaveIfDirty.Invoke(null, new object[] { a });
            n++;
        }
        if (SaveIfDirty == null && n > 0)
        {
            AssetDatabase.SaveAssets();
            R.Warn("AssetDatabase.SaveAssetIfDirty 不在（Unity 早于 2021.2？）：用了 AssetDatabase.SaveAssets，别的脏资产也一起存了");
        }
        R.Line("saved " + n + " material(s) under " + GenDir + "; the scene is not saved (save it yourself after looking)");
    }

    static void Identity(Transform t)
    {
        t.localPosition = Vector3.zero; t.localRotation = Quaternion.identity; t.localScale = Vector3.one;
    }

    static Vector3 V(float[] a) { return a != null && a.Length >= 3 ? new Vector3(a[0], a[1], a[2]) : Vector3.zero; }

    static string Fmt(Vector3 v) { return "(" + v.x.ToString("0.00") + ", " + v.y.ToString("0.00") + ", " + v.z.ToString("0.00") + ")"; }

    static string Path(Transform t)
    {
        string s = t.name;
        while (t.parent != null) { t = t.parent; s = t.name + "/" + s; }
        return s;
    }
}
#endif
