// =====================================================================================================
//  LanbaiGateDriver.cs   蓝白 · 第 4 幕「触手之门」的总驱动（UdonSharp）
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn + U# rules). !!!
//
//  CONTROL §5 interface (called by Director/LanbaiActDispatcher):
//     LanbaiTick(t)        every frame inside LanbaiWindow() (t = timeline seconds)
//     LanbaiActivate(on)   switches `roots` (GateRoot, NearRoot_bus), never this object (it stays active)
//     LanbaiWindow()       {U6 - 20, U9 + 2} = {113.80, 181.55}; round 10: to 185.0 (the 6 hands kept for the curl, 184.5 + 0.5)
//
//  Per frame (Gate/README_GateLayout.md §2, §2.1, §2.2, §4.1; the same evaluation as the local editor test
//  FromLocal/gate_test LB_GateTest_Run.Apply):
//     GateRoot position (h_bus(t), v_g), Tear_Root scale H(t) / 1000 (monotone PCHIP), every instance's pose
//     (rise / lean / track / close / drift) and reveal, the multitude's two groups (renderers toggled only when a group
//     crosses 0), the tide's reveal, the tear's sky folds and halo distance fade, the cabin-only tear light, and the
//     globals _Udon_CloudTop / TearPos / TearH / MoonDir / GateTime / GateOrigin / TearFoot / TearTop / MultReveal /
//     MoonDisc / TearOpen / RipProgress / TearHide.
//  U9 (the bus crosses the tear plane): every arm renderer (instances, the multitude, the tide) is switched off on the
//  frame before the eye crosses the plane (the far side's renderers, 总导演 10-23 01:10; the arms behind the bus are
//  retired, so they never meet act 4c's fog; round 10, 总导演 10-26 A: EXCEPT the 6 hands at the lips, kept to 184.5 for the
//  fingertip curl seen looking back, faded 184.0 -> 184.5), and from U9 + 0.15 s _Udon_TearHide = 1. After U9 GateRoot.z = -s(t),
//  the inside's decelerating closed form (GateRoot stays this driver's).
//  NOT written here: _Udon_InsidePortal (the inside driver), _Udon_FogBand* (LanbaiGateClouds), the Tear kit's
//  CloudGlow / LightLane / FootSkyline / old shafts (switched off for good by 蓝白/Gate Clouds/Build).
//  All arrays are filled by 蓝白/Gate/Build Driver (Gate/Editor/LanbaiGateDriverBuilder.cs) from Gate/GateDriver_Bake.json
//  and from the property blocks LB_GateTest left on the arms (phase, fog cap, group, variant dims, occlusion map).
//  Cost per frame (README_GateDriver §2): only the instances inside their pose span are posed (each: <= 2 Ease, <= 2
//  Slerp, 2 transform writes), the 3 near arms always; single arms write their blocks only while their reveal changes;
//  2 tear parts while visible, 12 gate globals + the D-22 family; the multitude's renderers only at the two crossings of 0.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiGateDriver : UdonSharpBehaviour
{
    [Header("Scene (filled by the builder)")]
    public GameObject[] roots;                 // GateRoot, NearRoot_bus: LanbaiActivate switches these
    public Transform gateRoot;
    public Transform tearRoot;
    public Transform cabinLight;               // Gate_Lights/Tear_CabinOnly (may be null)
    public Renderer foldsRenderer, haloRenderer;
    public Renderer[] tideRenderers;
    public Light cabinLightL, fillLight;       // Gate_Lights: Tear_CabinOnly, Fill_from_below (the Moon is not touched)
    public float cabinE = 0.8f, fillE = 0.24f; // Inspector = E (D-07)

    [Header("Sky / fog / moon / stars, U6 -> U9 (D-22): Sky/SkyPresets.json moon_night -> Sky/FogPresets.json act4_gate")]
    public bool skyFromSky;                    // false = the sky's JSONs were not in the project: only fallbackBand is written
    public string[] skyVecNames;
    public Vector4[] skyVecA, skyVecB;
    public int skyBandDirIndex = -1;           // act4_gate's band direction = toward the tear, every frame
    public string[] skyFloatNames;
    public float[] skyFloatA, skyFloatB;
    public float skyFadeT0 = 133.80f, skyFadeT1 = 163.80f;
    public Vector4 fallbackBand = new Vector4(0.1085f, 0.1130f, 0.1641f, 1f);

    [Header("Timeline (GateDriver_Bake.json)")]
    public float windowStart = 113.80f, windowEnd = 181.55f;
    public float U6k = 129.10f;
    public float U6 = 133.80f, U7 = 150.30f, U7b = 155.10f, U8 = 166.15f, U9 = 179.55f, vg = 59.0164f;
    public float[] hT, hH, hD;                 // tear_H_knots and their PCHIP slopes
    public Vector3 moonDir = new Vector3(-0.2059f, 0.1392f, 0.9686f);
    public float[] discT, discG, g0T, g0V, g1T, g1V, tideT, tideV, foldsT, foldsV;
    public float foldsGain = 1f, haloGain = 1f;
    public Vector3 tearFootOS = new Vector3(0.5f, 0f, -30f), tearTopOS = new Vector3(-59.14f, 920.36f, -30f);
    public Vector3 eyeFallback = new Vector3(0.55f, 1.7f, 2.05f);
    public float vEnd = 12f, decelT = 54.25f;    // after U9: GateRoot.z = -s(t), the inside's closed form

    [Header("Instances (one entry per JSON instance)")]
    public Transform[] instTf;
    public bool[] instBus;
    public Vector3[] instPos;
    public Quaternion[] instRot;
    public int[] revKind;                      // 0 = always on, 1 = own keys, 2 = multitude group
    public int[] revStart, revCount, instGroup;
    public float[] revT, revV;
    public bool[] riseOn, leanOn, closeOn;
    public int[] riseProf, leanProf, closeProf;          // 0 ss, 1 trap, 2 beta
    public float[] riseT0, riseT1, riseE, riseB, leanT0, leanT1, leanE, leanB, closeT0, closeT1, closeE, closeB;
    public Vector3[] riseStart;
    public Quaternion[] leanStart, closeEnd;
    public int[] trackStart, trackCount;
    public float[] trackT;
    public Quaternion[] trackQ;
    public float[] driftV, driftTref;
    public float[] poseT0, poseT1;            // the span in which the pose changes

    [Header("Renderers (every LOD of every instance)")]
    public Renderer[] rend;
    public int[] instRendStart, instRendCount;
    [Header("Round 10: the instance's own girth (D-05) and the fingertip curl (圣经 §I 喉), per instance (bake)")]
    public Vector4[] instGirth;                // x _Girth, y _GirthFalloff, z _VariantDims.x, w 1 = write them
    public bool[] curlOn;
    public Vector4[] curlPivot, curlAxis;      // object space: pivot + t0, axis + angle (rad)
    public float[] curlStart, curlDur, curlKeep;   // keep > 0: not retired at U9 until then (the curl is seen looking back)
    public float[] rPhase, rFogCap, rGroup;
    public bool[] rHasFogCap, rHasDims;
    public Vector4[] rDims;
    public Texture[] rOcc;

    private MaterialPropertyBlock _mpb;
    private int _idPhase, _idFogCap, _idGroup, _idReveal, _idDims, _idOcc, _idIntensity;
    private int _idCloudTop, _idTearPos, _idTearH, _idMoonDir, _idGateTime, _idGateOrigin, _idTearFoot, _idTearTop;
    private int _idMult, _idDisc, _idOpen, _idRip, _idHide;
    private float[] _lastRv, _lastCurl;
    private int _idCurl, _idCurlPivot, _idCurlAxis, _idGirth, _idGirthFalloff;
    private int[] _poseState;                 // 0 = must pose, 1 = posed before the span, 2 = after it
    private bool _mult0, _mult1, _retired, _ready;
    private float[] _window;
    private bool _warned, _active;
    private int[] _skyVecIds, _skyFloatIds;
    private int _idFogBand;
    private bool _skyFull;                     // the blend reached act4_gate: only the band direction changes now
    private Vector4 _bandDirFrozen;

    // ---- CONTROL §5 ----------------------------------------------------------------------------------------------
    public void LanbaiTick(float t)
    {
        if (!_ready) _Init();
        Evaluate(t);
    }

    public void LanbaiActivate(bool on)
    {
        _active = on;
        if (roots != null)
            for (int i = 0; i < roots.Length; i++) if (roots[i] != null) roots[i].SetActive(on);
        if (!on)
        {
            // the gate's lights are this driver's (v1.1): off outside the window, not lit through acts 5-12
            if (cabinLightL != null) cabinLightL.enabled = false;
            if (fillLight != null) fillLight.enabled = false;
        }
    }

    public float[] LanbaiWindow()
    {
        if (_window == null) _window = new float[] { windowStart, windowEnd };
        return _window;
    }

    // CONTROL §5 / Director §3: blocks AND globals are written in Start (the warm-up frames run before the first tick)
    void Start()
    {
        if (!_ready) _Init();
        Evaluate(windowStart);
        // not ticked yet: the tear position is not "set" (readers fall back to their materials) and the lights stay off
        VRCShader.SetGlobalVector(_idTearPos, new Vector4(0f, 0f, 0f, 0f));
        if (!skyFromSky) Debug.LogWarning("[LanbaiGateDriver] built without the sky kit: only _Udon_FogBandColor is written on [U6, U9). Re-run 蓝白/Gate/Build Driver after the sky kit is in the project (D-22)");
        if (!_active)
        {
            if (cabinLightL != null) cabinLightL.enabled = false;
            if (fillLight != null) fillLight.enabled = false;
        }
    }

    // the property blocks are lost on entering Play / VRChat (CONTROL §5): every renderer's block is written here once
    public void _Init()
    {
        _mpb = new MaterialPropertyBlock();
        _idPhase = VRCShader.PropertyToID("_Phase");
        _idFogCap = VRCShader.PropertyToID("_FogCapI");
        _idGroup = VRCShader.PropertyToID("_RevealGroup");
        _idReveal = VRCShader.PropertyToID("_Reveal");
        _idDims = VRCShader.PropertyToID("_VariantDims");
        _idOcc = VRCShader.PropertyToID("_OcclusionMap");
        _idIntensity = VRCShader.PropertyToID("_Intensity");
        _idCurl = VRCShader.PropertyToID("_Curl");
        _idCurlPivot = VRCShader.PropertyToID("_CurlPivot");
        _idCurlAxis = VRCShader.PropertyToID("_CurlAxis");
        _idGirth = VRCShader.PropertyToID("_Girth");
        _idGirthFalloff = VRCShader.PropertyToID("_GirthFalloff");
        _idCloudTop = VRCShader.PropertyToID("_Udon_CloudTop");
        _idTearPos = VRCShader.PropertyToID("_Udon_TearPos");
        _idTearH = VRCShader.PropertyToID("_Udon_TearH");
        _idMoonDir = VRCShader.PropertyToID("_Udon_MoonDir");
        _idGateTime = VRCShader.PropertyToID("_Udon_GateTime");
        _idGateOrigin = VRCShader.PropertyToID("_Udon_GateOrigin");
        _idTearFoot = VRCShader.PropertyToID("_Udon_TearFoot");
        _idTearTop = VRCShader.PropertyToID("_Udon_TearTop");
        _idMult = VRCShader.PropertyToID("_Udon_MultReveal");
        _idDisc = VRCShader.PropertyToID("_Udon_MoonDisc");
        _idOpen = VRCShader.PropertyToID("_Udon_TearOpen");
        _idRip = VRCShader.PropertyToID("_Udon_RipProgress");
        _idHide = VRCShader.PropertyToID("_Udon_TearHide");
        _idFogBand = VRCShader.PropertyToID("_Udon_FogBandColor");
        int nv = skyVecNames != null ? skyVecNames.Length : 0;
        _skyVecIds = new int[nv];
        for (int i = 0; i < nv; i++) _skyVecIds[i] = VRCShader.PropertyToID(skyVecNames[i]);
        int nf = skyFloatNames != null ? skyFloatNames.Length : 0;
        _skyFloatIds = new int[nf];
        for (int i = 0; i < nf; i++) _skyFloatIds[i] = VRCShader.PropertyToID(skyFloatNames[i]);
        int n = instTf != null ? instTf.Length : 0;
        _lastRv = new float[n];
        _lastCurl = new float[n];
        _poseState = new int[n];
        for (int i = 0; i < n; i++)
        {
            _lastRv[i] = -1f;
            WriteBlocks(i, 1f, 0f);            // the reveal itself follows on the first tick
        }
        // the multitude's renderers: whatever the editor left, bring them to a known state (tech review driver #1)
        _mult0 = true; _mult1 = true; _retired = false;
        SetGroup(0, true); SetGroup(1, true);
        _ready = true;
    }

    // ---- per frame ---------------------------------------------------------------------------------------------------
    void Evaluate(float t)
    {
        float hb = HBus(t);
        Vector3 gate = new Vector3(0f, 150f - hb, -TravelS(t));
        if (gateRoot != null) gateRoot.position = gate;
        float H = TearH(t), S = H / 1000f;
        float open = TearOpen(t), rip = SS((t - U7) / 16f);
        if (tearRoot != null) tearRoot.localScale = new Vector3(S, S, S);
        Vector3 eye = eyeFallback;
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (Utilities.IsValid(lp)) eye = lp.GetTrackingData(VRCPlayerApi.TrackingDataType.Head).position;
        // the arms go on the frame before this eye crosses the tear plane (z = gate.z); the tear itself 0.15 s after U9
        bool retired = t >= U9 - 0.05f || gate.z <= eye.z + 0.5f;
        bool hidden = t >= U9 + 0.15f;
        if (retired != _retired) for (int k = 0; k < _poseState.Length; k++) _poseState[k] = 0;

        // the multitude's groups first (a jump in t must not show one frame of the old poses)
        float g0 = KeyAt(g0T, g0V, 0, g0T != null ? g0T.Length : 0, t);
        float g1 = KeyAt(g1T, g1V, 0, g1T != null ? g1T.Length : 0, t);
        bool on0 = g0 > 0f && !retired, on1 = g1 > 0f && !retired;
        if (on0 != _mult0) { _mult0 = on0; SetGroup(0, on0); }
        if (on1 != _mult1) { _mult1 = on1; SetGroup(1, on1); }

        // instances: pose, then reveal
        int n = instTf != null ? instTf.Length : 0;
        for (int i = 0; i < n; i++)
        {
            Transform tr = instTf[i];
            if (tr == null) { Warn(); continue; }
            bool groupOff = revKind[i] == 2 && !((instGroup[i] == 0) ? _mult0 : _mult1);
            float rv = revKind[i] == 1 ? KeyAt(revT, revV, revStart[i], revCount[i], t) : 1f;
            // round 10: an arm with a curl kept past U9 (curlKeep > 0) is not retired until then
            bool kept = curlOn != null && i < curlOn.Length && curlOn[i] && curlKeep[i] > 0f && t < curlKeep[i];
            bool ret = retired && !kept;
            if (ret) rv = 0f;
            if (!ret && !groupOff && rv > 0f)                    // hidden arms are not posed
            {
                if (instBus[i] || (t >= poseT0[i] && t <= poseT1[i])) { Pose(i, t, hb, tr); _poseState[i] = 0; }
                else if (t < poseT0[i]) { if (_poseState[i] != 1) { Pose(i, t, hb, tr); _poseState[i] = 1; } }
                else if (_poseState[i] != 2) { Pose(i, t, hb, tr); _poseState[i] = 2; }
            }
            if (revKind[i] == 2) continue;                       // the multitude: above, per group
            // the fingertip curl: smoothstep over its own duration (slow, staggered; no light changes with it)
            float cu = 0f;
            if (curlOn != null && i < curlOn.Length && curlOn[i]) cu = SS((t - curlStart[i]) / Mathf.Max(curlDur[i], 0.1f));
            if (rv == _lastRv[i] && cu == _lastCurl[i]) continue; // nothing changed: no MPB writes
            _lastRv[i] = rv;
            _lastCurl[i] = cu;
            WriteBlocks(i, rv, cu);
        }
        // the tide
        float tide = retired ? 0f : KeyAt(tideT, tideV, 0, tideT != null ? tideT.Length : 0, t);
        if (tideRenderers != null)
            for (int k = 0; k < tideRenderers.Length; k++)
            {
                Renderer r = tideRenderers[k];
                if (r == null) continue;
                bool on = tide > 0f;
                if (r.enabled != on) r.enabled = on;
                if (!on) continue;
                _mpb.Clear();
                _mpb.SetFloat(_idReveal, tide);
                r.SetPropertyBlock(_mpb);
            }

        // the tear: folds, halo distance fade (README_GateLayout §2.2)
        if (foldsRenderer != null)
        {
            float fold = KeyAt(foldsT, foldsV, 0, foldsT != null ? foldsT.Length : 0, t) * foldsGain;
            bool on = fold > 0f && !hidden;
            if (foldsRenderer.enabled != on) foldsRenderer.enabled = on;
            if (on) { _mpb.Clear(); _mpb.SetFloat(_idIntensity, fold); foldsRenderer.SetPropertyBlock(_mpb); }
        }
        if (haloRenderer != null)
        {
            float D = Mathf.Abs(gate.z - eye.z);
            float halo = Mathf.Clamp01((SS((D - 250f) / 950f) - 0.25f) / 0.75f) * haloGain;
            bool on = halo >= 0.05f && !hidden;
            if (haloRenderer.enabled != on) haloRenderer.enabled = on;
            if (on) { _mpb.Clear(); _mpb.SetFloat(_idIntensity, halo); haloRenderer.SetPropertyBlock(_mpb); }
        }

        // globals (§2.1)
        Vector3 tearPos = gate + new Vector3(0f, -150f + 0.4f * H, 0f);
        VRCShader.SetGlobalVector(_idCloudTop, new Vector4(-hb, 0f, 0f, 1f));
        VRCShader.SetGlobalVector(_idTearPos, new Vector4(tearPos.x, tearPos.y, tearPos.z, 1f));
        VRCShader.SetGlobalVector(_idTearH, new Vector4(H, 0f, 0f, 1f));
        VRCShader.SetGlobalFloat(_idGateTime, t);
        VRCShader.SetGlobalVector(_idGateOrigin, new Vector4(gate.x, gate.y, gate.z, 1f));
        VRCShader.SetGlobalVector(_idMult, new Vector4(g0, g1, 0f, 0f));
        // the sky's fog / moon / stars are this driver's only on [U6, U9) (D-22): before U6 the sky, from U9 the inside
        if (t >= U6 && t < U9)
        {
            VRCShader.SetGlobalVector(_idMoonDir, new Vector4(moonDir.x, moonDir.y, moonDir.z, 1f));
            float disc = KeyAt(discT, discG, 0, discT != null ? discT.Length : 0, t);
            float f0 = U7b + 1.5f;
            if (t > f0) disc *= 1f - SS((t - f0) / 2f);
            VRCShader.SetGlobalVector(_idDisc, new Vector4(disc, 0.6f, 0f, 1f));
            WriteSky(t, tearPos, eye, retired);
        }
        else _skyFull = false;                                    // re-entering the span rewrites everything
        VRCShader.SetGlobalFloat(_idOpen, open);
        VRCShader.SetGlobalFloat(_idRip, rip);
        VRCShader.SetGlobalFloat(_idHide, hidden ? 1f : 0f);
        if (tearRoot != null)
        {
            Vector3 foot = tearRoot.TransformPoint(tearFootOS);
            Vector3 top = tearRoot.TransformPoint(tearTopOS);
            VRCShader.SetGlobalVector(_idTearFoot, new Vector4(foot.x, foot.y, foot.z, 0.5f * (0.18f + 0.12f * open) * H));
            VRCShader.SetGlobalVector(_idTearTop, new Vector4(top.x, top.y, top.z, 1f));
        }
        // the lights (v1.1): the cabin-only tear light points from the tear core to the bus and fades out over U9 -> U9 +
        // 0.25 (with the skylight spot); the fill from below lives with the arms. Both only while the gate is active
        if (cabinLight != null && tearPos.sqrMagnitude > 1f)
            cabinLight.rotation = Quaternion.LookRotation(-tearPos.normalized, Vector3.up);
        // the wound's light comes with the wound: from U6k (the cloud break) to 0.6 at U6, then with the opening to 1 at U8;
        // both lights fade together over U9 -> U9 + 0.25 (no one-frame cut)
        float fadeOut = 1f - Mathf.Clamp01((t - U9) / 0.25f);
        if (cabinLightL != null)
        {
            float k = cabinE * SS((t - U6k) / Mathf.Max(0.1f, U6 - U6k)) * (0.6f + 0.4f * open) * fadeOut;
            bool on = _active && k > 0f;
            if (cabinLightL.enabled != on) cabinLightL.enabled = on;
            if (on) cabinLightL.intensity = k;
        }
        if (fillLight != null)
        {
            float kf = fillE * fadeOut;
            bool on = _active && kf > 0f;
            if (fillLight.enabled != on) fillLight.enabled = on;
            if (on) fillLight.intensity = kf;
        }
        _retired = retired;
    }

    // moon_night -> act4_gate, smoothstep over the sky's U6 transition; act4_gate's band points at the tear (D-22)
    void WriteSky(float t, Vector3 tearPos, Vector3 eye, bool retired)
    {
        if (!skyFromSky)
        {
            VRCShader.SetGlobalVector(_idFogBand, fallbackBand);
            return;
        }
        float x = SS((t - skyFadeT0) / Mathf.Max(1e-3f, skyFadeT1 - skyFadeT0));
        bool full = x >= 1f;
        for (int i = 0; i < _skyVecIds.Length; i++)
        {
            if (full && _skyFull && i != skyBandDirIndex) continue;          // constants: written once at the end of the blend
            Vector4 b = skyVecB[i];
            if (i == skyBandDirIndex && retired) { VRCShader.SetGlobalVector(_skyVecIds[i], _bandDirFrozen); continue; }   // the bus is at the plane: hold
            if (i == skyBandDirIndex)
            {
                Vector3 d = tearPos - eye;
                d.y = 0f;
                if (d.sqrMagnitude > 1f) { d.Normalize(); b = new Vector4(d.x, 0f, d.z, b.w); }
            }
            Vector4 v = Vector4.Lerp(skyVecA[i], b, x);
            if (i == skyBandDirIndex)
            {
                Vector3 h = new Vector3(v.x, 0f, v.z);
                if (h.sqrMagnitude > 1e-6f) { h.Normalize(); v = new Vector4(h.x, 0f, h.z, v.w); }
            }
            if (i == skyBandDirIndex) _bandDirFrozen = v;
            VRCShader.SetGlobalVector(_skyVecIds[i], v);
        }
        if (!(full && _skyFull))
            for (int i = 0; i < _skyFloatIds.Length; i++)
                VRCShader.SetGlobalFloat(_skyFloatIds[i], Mathf.Lerp(skyFloatA[i], skyFloatB[i], x));
        _skyFull = full;
    }

    // every LOD renderer of instance i: its whole block (no GetPropertyBlock needed), the reveal, on / off
    void WriteBlocks(int i, float rv, float cu)
    {
        if (rend == null || instRendStart == null) return;
        int s = instRendStart[i], c = instRendCount[i];
        bool on = rv > 0f;
        bool surge = revKind[i] == 2;
        for (int k = s; k < s + c; k++)
        {
            Renderer r = rend[k];
            if (r == null) { Warn(); continue; }
            if (!surge) r.enabled = on;
            if (!on && !surge) continue;
            _mpb.Clear();
            _mpb.SetFloat(_idPhase, rPhase[k]);
            if (rHasFogCap[k]) _mpb.SetFloat(_idFogCap, rFogCap[k]);
            _mpb.SetFloat(_idGroup, rGroup[k]);
            _mpb.SetFloat(_idReveal, surge ? 1f : rv);
            if (rHasDims[k]) _mpb.SetVector(_idDims, rDims[k]);
            if (rOcc[k] != null) _mpb.SetTexture(_idOcc, rOcc[k]);
            if (instGirth != null && i < instGirth.Length && instGirth[i].w > 0f)
            {
                _mpb.SetFloat(_idGirth, instGirth[i].x);
                _mpb.SetFloat(_idGirthFalloff, instGirth[i].y);
                _mpb.SetVector(_idDims, new Vector4(instGirth[i].z, 0f, 0f, 0f));
            }
            if (curlOn != null && i < curlOn.Length && curlOn[i])
            {
                _mpb.SetFloat(_idCurl, cu);
                _mpb.SetVector(_idCurlPivot, curlPivot[i]);
                _mpb.SetVector(_idCurlAxis, curlAxis[i]);
            }
            r.SetPropertyBlock(_mpb);
        }
    }

    void SetGroup(int g, bool on)
    {
        int n = instTf != null ? instTf.Length : 0;
        for (int i = 0; i < n; i++)
        {
            if (revKind[i] != 2 || instGroup[i] != g) continue;
            int s = instRendStart[i], c = instRendCount[i];
            for (int k = s; k < s + c; k++) if (rend[k] != null) rend[k].enabled = on;
        }
    }

    void Warn()
    {
        if (!_warned) Debug.LogWarning("[LanbaiGateDriver] a transform / renderer is missing: re-run 蓝白/Gate/Build Driver after the gate's Build");
        _warned = true;
    }

    // ---- the timeline ------------------------------------------------------------------------------------------------
    float SS(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }

    // the distance the bus has travelled past the tear plane (negative before U9): v_g tau, then the inside's deceleration
    float TravelS(float t)
    {
        float tau = t - U9;
        if (tau <= 0f) return vg * tau;
        float T = Mathf.Max(decelT, 1e-3f);
        if (tau < T)
        {
            float x = tau / T;
            return vg * tau + (vEnd - vg) * T * (x * x * x - 0.5f * x * x * x * x);
        }
        return vg * T + (vEnd - vg) * T * 0.5f + vEnd * (tau - T);
    }

    float HBus(float t)
    {
        if (t <= U6) return 40f;
        if (t < 160.50f) return 40f + 20f * SS((t - U6) / (160.50f - U6));
        return 60f + 90f * SS((t - 160.50f) / (U9 - 160.50f));
    }

    float TearOpen(float t)
    {
        if (t <= U6) return 0f;
        if (t < U7) return 0.333f * SS((t - U6) / (U7 - U6));
        return 0.333f + 0.667f * SS((t - U7) / (U8 - U7));
    }

    // monotone PCHIP through the knots (slopes baked by gate_driver_bake.py = scipy PchipInterpolator)
    float TearH(float t)
    {
        if (hT == null || hT.Length < 2) return 640f;
        int n = hT.Length;
        if (t <= hT[0]) return hH[0];
        if (t >= hT[n - 1]) return hH[n - 1];
        int i = 0;
        while (i < n - 2 && t > hT[i + 1]) i++;
        float h = hT[i + 1] - hT[i];
        float s = (t - hT[i]) / h;
        float s2 = s * s, s3 = s2 * s;
        return (2f * s3 - 3f * s2 + 1f) * hH[i] + (s3 - 2f * s2 + s) * h * hD[i] + (-2f * s3 + 3f * s2) * hH[i + 1] + (s3 - s2) * h * hD[i + 1];
    }

    // keys: smoothstep between keys (the JSON convention); no keys = 1
    float KeyAt(float[] kt, float[] kv, int start, int count, float t)
    {
        if (kt == null || count <= 0) return 1f;
        if (t <= kt[start]) return kv[start];
        int last = start + count - 1;
        if (t >= kt[last]) return kv[last];
        for (int k = start; k < last; k++)
            if (t >= kt[k] && t <= kt[k + 1])
                return kv[k] + (kv[k + 1] - kv[k]) * SS((t - kt[k]) / Mathf.Max(1e-4f, kt[k + 1] - kt[k]));
        return kv[last];
    }

    float Ease(int prof, float t0, float t1, float e, float b, float t)
    {
        float s = Mathf.Clamp01((t - t0) / Mathf.Max(1e-4f, t1 - t0));
        if (prof == 1)
        {
            float vm = 1f / (1f - e);
            if (s < e) return vm * s * s / (2f * e);
            if (s <= 1f - e) return vm * (s - e / 2f);
            return 1f - vm * (1f - s) * (1f - s) / (2f * e);
        }
        if (prof == 2) return 1f - Mathf.Pow(1f - s, b) * (1f + b * s);
        return s * s * (3f - 2f * s);
    }

    // rise -> lean -> track -> close, then the bus frame (README_GateLayout §4; LB_GateTest.Pose)
    void Pose(int i, float t, float hb, Transform tr)
    {
        Vector3 p = instPos[i];
        Quaternion q = instRot[i];
        if (riseOn[i]) p = Vector3.LerpUnclamped(riseStart[i], instPos[i], Ease(riseProf[i], riseT0[i], riseT1[i], riseE[i], riseB[i], t));
        if (leanOn[i]) q = Quaternion.Slerp(leanStart[i], instRot[i], Ease(leanProf[i], leanT0[i], leanT1[i], leanE[i], leanB[i], t));
        int ts = trackStart[i], tc = trackCount[i];
        if (tc > 0 && t >= trackT[ts])
        {
            int last = ts + tc - 1;
            if (t >= trackT[last]) q = trackQ[last];
            else
                for (int k = ts; k < last; k++)
                    if (t >= trackT[k] && t <= trackT[k + 1])
                    {
                        q = Quaternion.Slerp(trackQ[k], trackQ[k + 1], SS((t - trackT[k]) / Mathf.Max(1e-4f, trackT[k + 1] - trackT[k])));
                        break;
                    }
        }
        if (closeOn[i] && t > closeT0[i]) q = Quaternion.Slerp(q, closeEnd[i], Ease(closeProf[i], closeT0[i], closeT1[i], closeE[i], closeB[i], t));
        if (instBus[i]) p = new Vector3(p.x, -hb + p.y, p.z + driftV[i] * (t - driftTref[i]));
        tr.localPosition = p;
        tr.localRotation = q;
    }
}
