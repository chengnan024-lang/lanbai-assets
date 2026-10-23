// =====================================================================================================
//  LanbaiGateDriverBuilder.cs   蓝白 · 门的总驱动搭建（编辑器）
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn). !!!
//
//  菜单 蓝白/Gate/Build Driver（以及 …/Build Driver + Test Clock）：
//    1. 读 Gate/GateDriver_Bake.json（Gate/Source/gate_driver_bake.py 从 GateLayout_v2.json 生成）；
//    2. 在场景里找 GateRoot、NearRoot_bus、Tear_Root（Tear_SkyFolds、Tear_Halo）、GateRoot/TideRoot、
//       Gate_Lights/Tear_CabinOnly、每个实例（GateRoot/<id> 或 NearRoot_bus/<id>）和它所有 LOD 的 renderer；
//    3. 从 renderer 现有的 property block 里抄群臂的 _VariantDims / _OcclusionMap（LB_GateTest.Apply 写的：
//       **先跑一次 LB_GateTest.Apply**，否则群臂少这两项，会报警告）；
//    4. 在常开的物体 Gate_Driver 上（场景里有 Director 就挂在它下面）加 LanbaiGateDriver（U#），填好所有数组；
//    5. 选了 Test Clock：再建 Gate_TestClock（LanbaiGateTestClock），连上门的驱动和 GateClouds_Driver。
//  可以重复运行（先删上一次的）。顺序：LB_GateTest.Build → 蓝白/Gate Clouds/Build → LB_GateTest.Apply → 这个。
//  U# 的程序资产 / 编译 / CopyProxyToUdon 用 LanbaiGateCloudsBuilder 的同一套（GateClouds/Editor）。
// =====================================================================================================
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class LanbaiGateDriverBuilder
{
    [Serializable] public class EaseDef { public float t0; public float t1; public int profile; public float e; public float b; }
    [Serializable] public class InstDef
    {
        public string id; public int bus; public float[] pos; public float[] rot;
        public int reveal_kind; public int group; public float[] rev_t; public float[] rev_v;
        public int rise; public EaseDef rise_ease; public float[] rise_start;
        public int lean; public EaseDef lean_ease; public float[] lean_start;
        public float[] track_t; public float[] track_q;
        public int close; public EaseDef close_ease; public float[] close_end;
        public float drift_v; public float drift_tref;
        public float phase; public float fog_cap; public float pose_t0; public float pose_t1;
    }
    [Serializable] public class Bake
    {
        public float U6, U7, U7b, U8, U9, vg;
        public float[] h_t, h_H, h_d, moon_dir, disc_t, disc_g, g0_t, g0_v, g1_t, g1_v, tide_t, tide_v, folds_t, folds_v;
        public float folds_gain, halo_gain;
        public float[] tear_foot_os, tear_top_os, eye_fallback;
        public float v_end, decel_T;
        public InstDef[] inst;
    }

    [MenuItem("蓝白/Gate/Build Driver")]
    public static void BuildMenu() { Build(false); }

    [MenuItem("蓝白/Gate/Build Driver + Test Clock (Play mode only)")]
    public static void BuildClockMenu() { Build(true); }

    static Vector3 V3(float[] a) { return a != null && a.Length >= 3 ? new Vector3(a[0], a[1], a[2]) : Vector3.zero; }
    static Quaternion Q(float[] a, int o) { return new Quaternion(a[o], a[o + 1], a[o + 2], a[o + 3]); }

    public static LanbaiGateDriver Build(bool withClock)
    {
        string[] g = AssetDatabase.FindAssets("GateDriver_Bake");
        string path = null;
        foreach (string id in g) { string p = AssetDatabase.GUIDToAssetPath(id); if (p.EndsWith("GateDriver_Bake.json")) { path = p; break; } }
        if (path == null) throw new Exception("[GateDriver] Gate/GateDriver_Bake.json not found (run Gate/Source/gate_driver_bake.py)");
        Bake B = JsonUtility.FromJson<Bake>(File.ReadAllText(path));

        Transform gateRoot = LanbaiGateCloudsBuilder.FindInScenePublic("GateRoot");
        if (gateRoot == null) throw new Exception("[GateDriver] no GateRoot in the open scene (run the gate's Build first)");
        Transform nearRoot = LanbaiGateCloudsBuilder.FindInScenePublic("NearRoot_bus");
        Transform tearRoot = LanbaiGateCloudsBuilder.FindDeepPublic(gateRoot, "Tear_Root") ?? LanbaiGateCloudsBuilder.FindDeepPublic(gateRoot, "Tear_Kit");
        Transform lights = LanbaiGateCloudsBuilder.FindInScenePublic("Gate_Lights");
        Transform tide = gateRoot.Find("TideRoot");

        Transform old = LanbaiGateCloudsBuilder.FindInScenePublic("Gate_Driver");
        if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
        Transform oldClock = LanbaiGateCloudsBuilder.FindInScenePublic("Gate_TestClock");
        if (oldClock != null) UnityEngine.Object.DestroyImmediate(oldClock.gameObject);
        var go = new GameObject("Gate_Driver");
        Transform director = LanbaiGateCloudsBuilder.FindInScenePublic("Director");
        if (director != null) go.transform.SetParent(director, false);
        var d = (LanbaiGateDriver)LanbaiGateCloudsBuilder.AddUdonSharp(go, typeof(LanbaiGateDriver));

        // scene
        var roots = new List<GameObject> { gateRoot.gameObject };
        if (nearRoot != null) roots.Add(nearRoot.gameObject);
        d.roots = roots.ToArray();
        d.gateRoot = gateRoot;
        d.tearRoot = tearRoot;
        d.cabinLight = lights != null ? lights.Find("Tear_CabinOnly") : null;
        Transform folds = tearRoot != null ? LanbaiGateCloudsBuilder.FindDeepPublic(tearRoot, "Tear_SkyFolds") : null;
        Transform halo = tearRoot != null ? LanbaiGateCloudsBuilder.FindDeepPublic(tearRoot, "Tear_Halo") : null;
        d.foldsRenderer = folds != null ? folds.GetComponent<Renderer>() : null;
        d.haloRenderer = halo != null ? halo.GetComponent<Renderer>() : null;
        d.tideRenderers = tide != null ? tide.GetComponentsInChildren<Renderer>(true) : new Renderer[0];

        // timeline
        d.windowStart = B.U6 - 20f; d.windowEnd = B.U9 + 2f;
        d.U6 = B.U6; d.U7 = B.U7; d.U7b = B.U7b; d.U8 = B.U8; d.U9 = B.U9; d.vg = B.vg;
        d.hT = B.h_t; d.hH = B.h_H; d.hD = B.h_d;
        d.moonDir = V3(B.moon_dir);
        d.discT = B.disc_t; d.discG = B.disc_g; d.g0T = B.g0_t; d.g0V = B.g0_v; d.g1T = B.g1_t; d.g1V = B.g1_v;
        d.tideT = B.tide_t; d.tideV = B.tide_v; d.foldsT = B.folds_t; d.foldsV = B.folds_v;
        d.foldsGain = B.folds_gain; d.haloGain = B.halo_gain;
        d.vEnd = B.v_end; d.decelT = B.decel_T;
        d.tearFootOS = V3(B.tear_foot_os); d.tearTopOS = V3(B.tear_top_os); d.eyeFallback = V3(B.eye_fallback);

        // instances
        int n = B.inst.Length;
        d.instTf = new Transform[n]; d.instBus = new bool[n]; d.instPos = new Vector3[n]; d.instRot = new Quaternion[n];
        d.revKind = new int[n]; d.revStart = new int[n]; d.revCount = new int[n]; d.instGroup = new int[n];
        d.riseOn = new bool[n]; d.leanOn = new bool[n]; d.closeOn = new bool[n];
        d.riseProf = new int[n]; d.leanProf = new int[n]; d.closeProf = new int[n];
        d.riseT0 = new float[n]; d.riseT1 = new float[n]; d.riseE = new float[n]; d.riseB = new float[n];
        d.leanT0 = new float[n]; d.leanT1 = new float[n]; d.leanE = new float[n]; d.leanB = new float[n];
        d.closeT0 = new float[n]; d.closeT1 = new float[n]; d.closeE = new float[n]; d.closeB = new float[n];
        d.riseStart = new Vector3[n]; d.leanStart = new Quaternion[n]; d.closeEnd = new Quaternion[n];
        d.trackStart = new int[n]; d.trackCount = new int[n]; d.driftV = new float[n]; d.driftTref = new float[n];
        d.poseT0 = new float[n]; d.poseT1 = new float[n];
        d.instRendStart = new int[n]; d.instRendCount = new int[n];
        var revT = new List<float>(); var revV = new List<float>(); var trT = new List<float>(); var trQ = new List<Quaternion>();
        var rend = new List<Renderer>(); var rPhase = new List<float>(); var rFog = new List<float>(); var rHasFog = new List<bool>();
        var rGroup = new List<float>(); var rDims = new List<Vector4>(); var rHasDims = new List<bool>(); var rOcc = new List<Texture>();
        var mpb = new MaterialPropertyBlock();
        int missing = 0, surgeNoDims = 0;
        for (int i = 0; i < n; i++)
        {
            InstDef it = B.inst[i];
            Transform parent = it.bus == 1 ? nearRoot : gateRoot;
            Transform tr = parent != null ? parent.Find(it.id) : null;
            if (tr == null) missing++;
            d.instTf[i] = tr; d.instBus[i] = it.bus == 1;
            d.instPos[i] = V3(it.pos); d.instRot[i] = Q(it.rot, 0);
            d.revKind[i] = it.reveal_kind; d.instGroup[i] = it.group;
            d.revStart[i] = revT.Count; d.revCount[i] = it.rev_t != null ? it.rev_t.Length : 0;
            if (it.rev_t != null) { revT.AddRange(it.rev_t); revV.AddRange(it.rev_v); }
            d.riseOn[i] = it.rise == 1; d.riseProf[i] = it.rise_ease.profile; d.riseT0[i] = it.rise_ease.t0; d.riseT1[i] = it.rise_ease.t1;
            d.riseE[i] = it.rise_ease.e; d.riseB[i] = it.rise_ease.b; d.riseStart[i] = V3(it.rise_start);
            d.leanOn[i] = it.lean == 1; d.leanProf[i] = it.lean_ease.profile; d.leanT0[i] = it.lean_ease.t0; d.leanT1[i] = it.lean_ease.t1;
            d.leanE[i] = it.lean_ease.e; d.leanB[i] = it.lean_ease.b; d.leanStart[i] = Q(it.lean_start, 0);
            d.closeOn[i] = it.close == 1; d.closeProf[i] = it.close_ease.profile; d.closeT0[i] = it.close_ease.t0; d.closeT1[i] = it.close_ease.t1;
            d.closeE[i] = it.close_ease.e; d.closeB[i] = it.close_ease.b; d.closeEnd[i] = Q(it.close_end, 0);
            d.trackStart[i] = trT.Count; d.trackCount[i] = it.track_t != null ? it.track_t.Length : 0;
            if (it.track_t != null) { trT.AddRange(it.track_t); for (int k = 0; k < it.track_t.Length; k++) trQ.Add(Q(it.track_q, 4 * k)); }
            d.driftV[i] = it.drift_v; d.driftTref[i] = it.drift_tref;
            d.poseT0[i] = it.pose_t0; d.poseT1[i] = it.pose_t1;
            d.instRendStart[i] = rend.Count;
            if (tr != null)
                foreach (Renderer r in tr.GetComponentsInChildren<Renderer>(true))
                {
                    rend.Add(r);
                    rPhase.Add(it.phase); rFog.Add(it.fog_cap); rHasFog.Add(it.fog_cap >= 0f);
                    rGroup.Add(it.reveal_kind == 2 ? it.group : 0);
                    r.GetPropertyBlock(mpb);              // what LB_GateTest.Apply left: the multitude's dims / occlusion
                    bool hasDims = mpb.HasVector("_VariantDims");
                    rDims.Add(hasDims ? mpb.GetVector("_VariantDims") : Vector4.zero); rHasDims.Add(hasDims);
                    rOcc.Add(mpb.HasTexture("_OcclusionMap") ? mpb.GetTexture("_OcclusionMap") : null);
                    if (it.reveal_kind == 2 && !hasDims) surgeNoDims++;
                }
            d.instRendCount[i] = rend.Count - d.instRendStart[i];
        }
        d.revT = revT.ToArray(); d.revV = revV.ToArray(); d.trackT = trT.ToArray(); d.trackQ = trQ.ToArray();
        d.rend = rend.ToArray(); d.rPhase = rPhase.ToArray(); d.rFogCap = rFog.ToArray(); d.rHasFogCap = rHasFog.ToArray();
        d.rGroup = rGroup.ToArray(); d.rDims = rDims.ToArray(); d.rHasDims = rHasDims.ToArray(); d.rOcc = rOcc.ToArray();
        LanbaiGateCloudsBuilder.SetupUdonSharp(d);
        if (missing > 0) Debug.LogWarning("[GateDriver] " + missing + " instances not found under GateRoot / NearRoot_bus");
        if (surgeNoDims > 0) Debug.LogWarning("[GateDriver] " + surgeNoDims + " multitude renderers have no _VariantDims: run LB_GateTest.Apply once, then Build Driver again");

        // double writers (tech review driver #9): LanbaiTearParams writes the tear globals every frame, unwindowed
        foreach (MonoBehaviour mb in UnityEngine.Object.FindObjectsOfType<MonoBehaviour>(true))
            if (mb != null && mb.GetType().Name == "LanbaiTearParams")
                Debug.LogWarning("[GateDriver] " + mb.name + " has LanbaiTearParams: remove it, LanbaiGateDriver writes the tear globals now");
        if (withClock)
        {
            if (director != null)
                Debug.LogWarning("[GateDriver] the scene has a Director: the test clock and the dispatcher would both tick the gate. Use the clock only in the test scene");
            var cg = new GameObject("Gate_TestClock");
            var clock = (LanbaiGateTestClock)LanbaiGateCloudsBuilder.AddUdonSharp(cg, typeof(LanbaiGateTestClock));
            clock.gate = d;
            Transform cd = LanbaiGateCloudsBuilder.FindInScenePublic("GateClouds_Driver");
            clock.clouds = cd != null ? cd.GetComponent<LanbaiGateClouds>() : null;
            LanbaiGateCloudsBuilder.SetupUdonSharp(clock);
            Debug.Log("[GateDriver] Gate_TestClock: Play mode only, delete it from the real world");
        }
        EditorUtility.SetDirty(d);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(go.scene);
        Debug.Log(string.Format("[GateDriver] built: {0} instances ({1} missing), {2} renderers, {3} tide renderers, {4} track keys",
                                n, missing, rend.Count, d.tideRenderers.Length, trT.Count));
        return d;
    }
}
#endif
