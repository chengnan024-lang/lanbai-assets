// =====================================================================================================
//  LanbaiAct07Driver.cs   蓝白 · 第 7 幕「海」的驱动（UdonSharp）。v1 = 第 7a 幕（F2h → F5）；7b / 7c 以后接在同一个驱动里
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn + U# rules). !!!
//
//  CONTROL §5 interface (called by Director/LanbaiActDispatcher):
//     LanbaiTick(t)        every frame inside LanbaiWindow() (t = timeline seconds)
//     LanbaiActivate(on)   switches `roots` (R_Sea, R_Act07Bus), never this object
//     LanbaiWindow()       {F2h - 1, exit + 1} = {362.26, 923.36}; after F5 the 7a end state is held until 7b / 7c arrive.
//                          Gates: nothing of the sea before tEntry (F2h 363.26); from tExit (922.36, out of the water) only
//                          the sea's own channels are handed back and nothing shared is written (终审 7a 一 #2)
//  Every number comes from Act07_Sea/Act07_Layout.json, baked into the fields below by 蓝白/Build/Act07a
//  (Act07_Sea/Editor/LanbaiAct07Builder.cs). Udon cannot read JSON at runtime (Engineering/README_集成.md §4).
//
//  Per frame (README_Act07a §3):
//    motion   depth(t), fwd(t) (closed-form integrals of the smoothstep velocity profiles) -> R_Sea = (0, depth, -fwd)
//    sea      the plane on from F2h with the ABOVE material (M_06_Sea, the Clouds' look), M_07a_SeaSurface from the
//             eye-under moment; _WindowGain x the F3e1 'dark coin' curve; _WindowCore desktop / VR (D-23 #2)
//    globals  _Udon_SeaLevel, SeaMode, SeaClock, Underwater, SeaBus, SeaBusVel, T, Fog (+ FogBase = (sea y, 0, 0, 1)),
//             WaterFogUp / Mid / Down, Caustics (+ Color, Tex)
//    takeover (README_集成 §2-3; both switches default OFF, like 4c):
//             writeRenderSettings (LB_Journey.extAtmosphere): RenderSettings.fogDensity / fogColor / Trilight ambient;
//             writeMainLight (LB_Journey.extSun): the world's ONE shadowed main light (D-24, bible §1.6) is never switched
//             off: at the eye-under moment (the waterline covers it) it turns to the sun through the water (el 70, az +30,
//             #B0D9F2, E 1.6 -> 0.001 by 15 m, never 0, shadows untouched) and carries the caustic cookie
//    beats    shafts (depth fade, F4p gather into the skylight, gone by 467.6), F3e1's last sweeping shaft, trails from
//             F4, seeds from F3i, the ridge wall's rim, the warm point at F5
//  NOT written here: PPv2 weights (LB_Journey.ApplyGrades: S7a -> S7b F3e -> F5), the cabin (_Udon_Cabin*), the
//  Clouds' sea before F2h.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiAct07Driver : UdonSharpBehaviour
{
    [Header("Scene (filled by the builder)")]
    public GameObject[] roots;
    public Transform rSea;                     // everything fixed in the water: the plane, the shafts, the ridge, the warm point
    public Renderer seaRenderer;
    public Material seaAbove, seaBelow;
    public Renderer shafts, lastShaft, ridge, warmPoint;
    public Transform lastShaftTf;
    public Renderer snow, seeds, trails, bubblesGlass, bubblesSeats;
    public Renderer dome;                      // Lanbai/SeaDome: the 'sky' under water (on while the eye is under)
    public Light beam;                         // R_Act07Bus/Act07_Beam (spot): F4p gather and F3e1's last shaft on the seats / hands
    public Light worldSun;                     // THE main light (D-24 = RenderSettings.sun; the builder wires it if empty)
    public Texture sunCookie;                  // the caustic cookie (CRT Lanbai/SeaCausticsCookie), put on worldSun under water
    public float sunCookieSize = 1.5f;
    public Texture causticsTex;
    public bool writeRenderSettings = false;   // README_集成 §3: tick only with LB_Journey.extAtmosphere
    public bool writeMainLight = false;        // README_集成 §3: tick only with LB_Journey.extSun

    [Header("Timeline (Act07_Layout.json)")]
    public float windowStart = 362.26f, windowEnd = 923.36f;
    public float tEntry = 363.26f, tEyeUnder = 363.615f, tExit = 922.36f, tF3i = 558.86f, tF4 = 446.01f, tF5 = 644.96f;

    [Header("Motion (smoothstep velocity profiles)")]
    public float D0 = 1f;
    public float sinkT0, sinkV0;
    public float[] sinkSegT0, sinkSegDur, sinkSegDv;
    public float fwdT0, fwdV0;
    public float[] fwdSegT0, fwdSegDur, fwdSegDv;

    [Header("Water by depth")]
    public float[] wDepth, wDensity;
    public Vector4[] wUp, wMid, wDown;
    public Color[] wFogGamma;                  // RenderSettings.fogColor per key: the mid colour in sRGB (gamma) space
    public Vector4 causticsColor;
    public float causticsDepth0 = 0f, causticsDepth1 = 15f;

    [Header("Light")]
    // colours of lights and RenderSettings are sRGB values (Unity linearises them); intensity = linear E (D-00: VRChat forces
    // lightsUseLinearIntensity = true -> Inspector = E; the bible's §1.5 trap 1 is void)
    public Color sunColor = new Color(0.69f, 0.85f, 0.95f, 1f);
    public float sunE0 = 1.6f, sunDepth1 = 15f, sunFloor = 0.001f;   // below 15 m: 0.001, never off (bible §1.6)
    public Quaternion sunRotation = Quaternion.identity;               // el 70, az +30 (builder)
    public Color ambSky, ambEquator, ambGround;

    [Header("Snell window")]
    public float[] winGainT, winGainV;         // x the material's _WindowGain
    public float baseWindowGain = 18f;
    public Vector4 coreDesktop = new Vector4(4.45f, 3f, 2f, 1f), coreVR = new Vector4(3.2f, 4f, 2f, 1f);
    public float erosionT0 = 363.26f, erosionT1 = 644.96f, erosionMax = 0.25f;

    [Header("Shafts")]
    public float shaftDepthFull = 18f, shaftDepthGone = 25f;
    public float gatherT0 = 453f, gatherT1 = 462.36f, shaftsGoneT = 467.6f;
    public Vector3 gatherPointBus = new Vector3(0.55f, 2.74f, 1.2f);
    public float lastT0 = 506.36f, lastIn = 2f, lastSweep = 4f, lastOut = 2f;
    public Vector3 lastFromBus = new Vector3(3f, 14f, -2f), lastToBus = new Vector3(-1.5f, 14f, 4.5f), lastTargetBus = new Vector3(1f, 0.95f, -2f), lastTargetToBus = new Vector3(0f, 0.95f, 3.5f);
    public Vector3 beamGatherPos = new Vector3(0.87f, 5.16f, 1.76f), beamGatherAim = new Vector3(0.55f, 1.1f, 1.75f);
    public float beamGatherE = 9f, beamLastE = 7.5f;

    [Header("Warm point (F5)")]
    public float warmFadeIn = 3f;

    private MaterialPropertyBlock _mpb;
    private int _idSeaLevel, _idSeaMode, _idSeaClock, _idUnder, _idSeaBus, _idSeaBusVel, _idT, _idFog, _idFogBase;
    private int _idWUp, _idWMid, _idWDown, _idCaus, _idCausCol, _idCausTex;
    private int _idWindowGain, _idWindowCore, _idGain, _idGather, _idGatherPoint;
    // _below starts true: the plane is BUILT with the BELOW material so the prewarm frames draw that variant too; the
    // first Tick at / after F2h swaps it to ABOVE (until the eye is under)
    private bool _ready, _vr, _below = true, _sunTaken;
    private float[] _window;

    // ---- CONTROL §5 ----------------------------------------------------------------------------------------------
    public void LanbaiTick(float t)
    {
        if (!_ready) _Init();
        Evaluate(t);
    }

    public void LanbaiActivate(bool on)
    {
        if (roots == null) return;
        for (int i = 0; i < roots.Length; i++) if (roots[i] != null) roots[i].SetActive(on);
        if (!on && _ready) HandBack();
    }

    // hand back only what is the sea's alone (裁决 20:40: shared channels -- fog, RenderSettings, sea level / mode, the
    // main light's direction / colour / intensity -- are never cleared here; the next writer writes them in full)
    private void HandBack()
    {
        VRCShader.SetGlobalFloat(_idUnder, 0f);
        VRCShader.SetGlobalVector(_idCaus, new Vector4(0f, 1f, 0f, 1f));
        if (_sunTaken && worldSun != null) worldSun.cookie = null;    // the cookie is ours
        _sunTaken = false;
    }

    public float[] LanbaiWindow()
    {
        if (_window == null) _window = new float[] { windowStart, windowEnd };
        return _window;
    }

    // Start only initialises: the renderers stay as built, so the dispatcher's 2 prewarm frames really draw every
    // shader and mesh once (终审 7a 二: no hitch in the silence of 363.26-363.615); the first Tick applies the gates
    void Start()
    {
        if (!_ready) _Init();
    }

    public void _Init()
    {
        _mpb = new MaterialPropertyBlock();
        _idSeaLevel = VRCShader.PropertyToID("_Udon_SeaLevel");
        _idSeaMode = VRCShader.PropertyToID("_Udon_SeaMode");
        _idSeaClock = VRCShader.PropertyToID("_Udon_SeaClock");
        _idUnder = VRCShader.PropertyToID("_Udon_Underwater");
        _idSeaBus = VRCShader.PropertyToID("_Udon_SeaBus");
        _idSeaBusVel = VRCShader.PropertyToID("_Udon_SeaBusVel");
        _idT = VRCShader.PropertyToID("_Udon_T");
        _idFog = VRCShader.PropertyToID("_Udon_Fog");
        _idFogBase = VRCShader.PropertyToID("_Udon_FogBase");
        _idWUp = VRCShader.PropertyToID("_Udon_WaterFogUp");
        _idWMid = VRCShader.PropertyToID("_Udon_WaterFogMid");
        _idWDown = VRCShader.PropertyToID("_Udon_WaterFogDown");
        _idCaus = VRCShader.PropertyToID("_Udon_Caustics");
        _idCausCol = VRCShader.PropertyToID("_Udon_CausticsColor");
        _idCausTex = VRCShader.PropertyToID("_Udon_CausticsTex");
        _idWindowGain = VRCShader.PropertyToID("_WindowGain");
        _idWindowCore = VRCShader.PropertyToID("_WindowCore");
        _idGain = VRCShader.PropertyToID("_Gain");
        _idGather = VRCShader.PropertyToID("_Gather");
        _idGatherPoint = VRCShader.PropertyToID("_GatherPoint");
        VRCPlayerApi lp = Networking.LocalPlayer;
        _vr = lp != null && lp.IsUserInVR();
        if (causticsTex != null) VRCShader.SetGlobalTexture(_idCausTex, causticsTex);
        _ready = true;
    }

    // ---- maths -----------------------------------------------------------------------------------------------------
    private float Smooth(float x)
    {
        x = Mathf.Clamp01(x);
        return x * x * (3f - 2f * x);
    }

    private float SmoothInt(float x)          // integral of smoothstep from 0 to x
    {
        if (x <= 0f) return 0f;
        if (x >= 1f) return 0.5f + (x - 1f);
        return x * x * x - 0.5f * x * x * x * x;
    }

    private float ProfileX(float t, float T0, float v0, float[] s0, float[] dur, float[] dv)
    {
        if (t <= T0) return v0 * (t - T0);
        float x = v0 * (t - T0);
        for (int i = 0; i < s0.Length; i++) x += dv[i] * dur[i] * SmoothInt((t - s0[i]) / dur[i]);
        return x;
    }

    private float ProfileV(float t, float v0, float[] s0, float[] dur, float[] dv)
    {
        float v = v0;
        for (int i = 0; i < s0.Length; i++) v += dv[i] * Smooth((t - s0[i]) / dur[i]);
        return v;
    }

    private float Keys(float t, float[] kt, float[] kv)       // smoothstep between keys, held outside
    {
        if (kt == null || kt.Length == 0) return 1f;
        if (t <= kt[0]) return kv[0];
        for (int i = 1; i < kt.Length; i++)
            if (t < kt[i]) return Mathf.Lerp(kv[i - 1], kv[i], Smooth((t - kt[i - 1]) / Mathf.Max(kt[i] - kt[i - 1], 1e-4f)));
        return kv[kv.Length - 1];
    }

    private int _wi;
    private float _wf;
    private void WaterIndex(float depth)                        // linear between the depth keys
    {
        int n = wDepth.Length;
        if (depth <= wDepth[0]) { _wi = 0; _wf = 0f; return; }
        for (int i = 1; i < n; i++)
            if (depth < wDepth[i]) { _wi = i - 1; _wf = (depth - wDepth[i - 1]) / Mathf.Max(wDepth[i] - wDepth[i - 1], 1e-4f); return; }
        _wi = n - 2; _wf = 1f;
    }

    // ---- per frame ---------------------------------------------------------------------------------------------------
    public void Evaluate(float t)
    {
        float depth = D0 + ProfileX(t, sinkT0, sinkV0, sinkSegT0, sinkSegDur, sinkSegDv);
        float fwd = ProfileX(t, fwdT0, fwdV0, fwdSegT0, fwdSegDur, fwdSegDv);
        float vSink = ProfileV(t, sinkV0, sinkSegT0, sinkSegDur, sinkSegDv);
        float vFwd = t < fwdT0 ? 0f : ProfileV(t, fwdV0, fwdSegT0, fwdSegDur, fwdSegDv);
        if (rSea != null) rSea.localPosition = new Vector3(0f, depth, -fwd);
        bool under = t >= tEyeUnder;

        // out of the water (922.36): hand back the sea's own channels, switch our things off, write nothing shared
        if (t >= tExit)
        {
            HandBack();
            AllOff();
            return;
        }

        // before F2h (the window opens 1 s early, under the dispatcher's cover) nothing of the sea exists yet: the act-6 sea
        // plane and globals are still the Clouds' (README_Sea接口 §5: the two planes never coexist; the sea's globals from F2h)
        if (t < tEntry)
        {
            AllOff();
            return;
        }
        if (seaRenderer != null) seaRenderer.enabled = true;

        // ---- the plane: ABOVE until the eye is under (the Clouds' look, under the waterline), then BELOW
        if (seaRenderer != null)
        {
            if (under != _below)
            {
                seaRenderer.sharedMaterial = under ? seaBelow : seaAbove;
                _below = under;
            }
            if (under)
            {
                seaRenderer.GetPropertyBlock(_mpb);
                _mpb.SetFloat(_idWindowGain, baseWindowGain * Keys(t, winGainT, winGainV));
                Vector4 core = coreDesktop;
                if (_vr)
                {
                    float er = erosionMax * Mathf.Clamp01((t - erosionT0) / Mathf.Max(erosionT1 - erosionT0, 1e-3f));
                    core = Vector4.Lerp(coreDesktop, coreVR, Smooth(er / Mathf.Max(erosionMax, 1e-4f)));
                }
                _mpb.SetVector(_idWindowCore, core);
                seaRenderer.SetPropertyBlock(_mpb);
            }
            else
            {
                _mpb.Clear();
                seaRenderer.SetPropertyBlock(_mpb);
            }
        }

        if (dome != null) dome.enabled = under;

        // ---- globals
        VRCShader.SetGlobalFloat(_idT, t);
        VRCShader.SetGlobalFloat(_idSeaLevel, depth);
        VRCShader.SetGlobalFloat(_idSeaMode, under ? 2f : 1f);
        VRCShader.SetGlobalVector(_idSeaClock, new Vector4(t, 0f, fwd, 1f));
        VRCShader.SetGlobalFloat(_idUnder, under ? 1f : 0f);
        VRCShader.SetGlobalVector(_idSeaBus, new Vector4(0f, -depth, fwd, 1f));
        VRCShader.SetGlobalVector(_idSeaBusVel, new Vector4(0f, -vSink, vFwd, 1f));

        float dens = 0f;
        if (under && wDepth != null && wDepth.Length > 1)
        {
            WaterIndex(depth);
            dens = Mathf.Lerp(wDensity[_wi], wDensity[_wi + 1], _wf);
            Vector4 up = Vector4.Lerp(wUp[_wi], wUp[_wi + 1], _wf);
            Vector4 mid = Vector4.Lerp(wMid[_wi], wMid[_wi + 1], _wf);
            Vector4 down = Vector4.Lerp(wDown[_wi], wDown[_wi + 1], _wf);
            VRCShader.SetGlobalVector(_idWUp, up);
            VRCShader.SetGlobalVector(_idWMid, mid);
            VRCShader.SetGlobalVector(_idWDown, down);
            // _Udon_Fog wins over the legacy _Udon_FogDensity (LanbaiFog.cginc); act 6 left its own _Udon_Fog (w = 1)
            VRCShader.SetGlobalVector(_idFog, new Vector4(dens, 0f, 0f, 1f));
            VRCShader.SetGlobalVector(_idFogBase, new Vector4(depth, 0f, 0f, 1f));   // set (w 1); unused under water
            if (writeRenderSettings)
            {
                RenderSettings.fogDensity = dens;
                RenderSettings.fogColor = Color.Lerp(wFogGamma[_wi], wFogGamma[_wi + 1], _wf);
                RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
                RenderSettings.ambientSkyColor = ambSky;
                RenderSettings.ambientEquatorColor = ambEquator;
                RenderSettings.ambientGroundColor = ambGround;
            }
        }

        // ---- caustics and the sun through the water (both fade to 0 by 15 m)
        float cs = 1f - Mathf.Clamp01((depth - causticsDepth0) / Mathf.Max(causticsDepth1 - causticsDepth0, 1e-3f));
        VRCShader.SetGlobalVector(_idCaus, new Vector4(under ? cs : 0f, 1f, t, 1f));
        VRCShader.SetGlobalVector(_idCausCol, causticsColor);
        // the main light: taken over at the eye-under moment (the waterline covers the turn), never switched off
        // scrubbed back above the water (debug clock): the cookie is ours, take it off; the act-6 writer turns the light back
        if (!under && _sunTaken) { if (worldSun != null) worldSun.cookie = null; _sunTaken = false; }
        if (writeMainLight && worldSun != null && under)
        {
            float e = Mathf.Max(sunE0 * (1f - Mathf.Clamp01(depth / Mathf.Max(sunDepth1, 1e-3f))), sunFloor);
            worldSun.transform.rotation = sunRotation;
            worldSun.color = sunColor;
            worldSun.intensity = e;            // VRChat forces lightsUseLinearIntensity = true -> Inspector = E (D-00)
            if (!_sunTaken)
            {
                worldSun.cookie = sunCookie;
                worldSun.cookieSize = sunCookieSize;
                _sunTaken = true;
            }
        }

        // ---- shafts: depth fade, F4p gather into the skylight, gone by 467.6
        if (shafts != null)
        {
            // F4p is their brightest (bible §6·7a): from 453 they gather AND come back up from the depth fade (lerp to 1),
            // then fade out by 467.6; the depth fade alone would have them gone at 25 m, i.e. at F4p
            float g = 1f - Mathf.Clamp01((depth - shaftDepthFull) / Mathf.Max(shaftDepthGone - shaftDepthFull, 1e-3f));
            float gather = Smooth((t - gatherT0) / Mathf.Max(gatherT1 - gatherT0, 1e-3f));
            if (t > gatherT0) g = Mathf.Lerp(g, 1f, gather);
            if (t > gatherT1) g *= 1f - Smooth((t - gatherT1) / Mathf.Max(shaftsGoneT - gatherT1, 1e-3f));
            if (!under) g = 0f;
            shafts.enabled = g > 0.001f;
            if (shafts.enabled)
            {
                shafts.GetPropertyBlock(_mpb);
                _mpb.SetFloat(_idGain, g);
                _mpb.SetFloat(_idGather, gather);
                // the gather point (the skylight, bus frame = world) in R_Sea's object space
                Vector3 gp = gatherPointBus - new Vector3(0f, depth, -fwd);
                _mpb.SetVector(_idGatherPoint, new Vector4(gp.x, gp.y, gp.z, 0f));
                shafts.SetPropertyBlock(_mpb);
            }
        }
        // the beam light: F4p (the gathered shafts land on the seats and your hands), else the last shaft below
        float beamE = 0f;
        Vector3 beamPos = beamGatherPos, beamAim = beamGatherAim;
        if (under && t > gatherT0 && t < shaftsGoneT)
        {
            float up = Smooth((t - gatherT0) / Mathf.Max(gatherT1 - gatherT0, 1e-3f));
            float down = 1f - Smooth((t - gatherT1) / Mathf.Max(shaftsGoneT - gatherT1, 1e-3f));
            beamE = beamGatherE * (t < gatherT1 ? up : down);
        }
        // F3e1: the last wide shaft (2 s in, 4 s sweep across the seats, 2 s out); its quad lives in the BUS frame,
        // its foot moves across the seats (target from -> to), the beam rides with it
        if (lastShaft != null)
        {
            float u = t - lastT0;
            float tot = lastIn + lastSweep + lastOut;
            bool on = u > 0f && u < tot;
            lastShaft.enabled = on;
            if (on)
            {
                float a = Smooth(u / lastIn) * (1f - Smooth((u - lastIn - lastSweep) / lastOut));
                float s = Smooth((u - lastIn * 0.5f) / (lastSweep + lastIn));
                Vector3 c = Vector3.Lerp(lastFromBus, lastToBus, s);
                Vector3 foot = Vector3.Lerp(lastTargetBus, lastTargetToBus, s);
                if (lastShaftTf != null)
                {
                    lastShaftTf.localPosition = c;
                    lastShaftTf.localRotation = Quaternion.FromToRotation(Vector3.down, (foot - c).normalized);
                }
                beamE = beamLastE * a;
                beamPos = foot + (c - foot).normalized * 4f;
                beamAim = foot;
                lastShaft.GetPropertyBlock(_mpb);
                _mpb.SetFloat(_idGain, a);
                lastShaft.SetPropertyBlock(_mpb);
            }
        }

        if (beam != null)
        {
            beam.enabled = beamE > 0.001f;
            if (beam.enabled)
            {
                beam.intensity = beamE;              // Inspector = E (D-00)
                beam.transform.localPosition = beamPos;
                beam.transform.localRotation = Quaternion.LookRotation((beamAim - beamPos).normalized, Vector3.forward);
            }
        }

        // ---- particles: snow while under, seeds from F3i (the shader times each birth), trails from F4
        SetGain(snow, under ? 1f : 0f);
        SetGain(seeds, t >= tF3i - 0.1f ? 1f : 0f);
        SetGain(trails, t >= tF4 ? 1f : 0f);
        SetGain(bubblesGlass, t >= tEntry && t < tEntry + 4f ? 1f : 0f);
        SetGain(bubblesSeats, under ? 1f : 0f);
        SetGain(ridge, t >= tF4 ? 1f : 0f);                        // its rim is the trails' light
        SetGain(warmPoint, Smooth((t - tF5) / Mathf.Max(warmFadeIn, 1e-3f)));
    }

    private void AllOff()
    {
        if (seaRenderer != null) seaRenderer.enabled = false;
        if (dome != null) dome.enabled = false;
        if (beam != null) beam.enabled = false;
        if (shafts != null) shafts.enabled = false;
        if (lastShaft != null) lastShaft.enabled = false;
        SetGain(snow, 0f); SetGain(seeds, 0f); SetGain(trails, 0f); SetGain(bubblesGlass, 0f); SetGain(bubblesSeats, 0f);
        SetGain(ridge, 0f); SetGain(warmPoint, 0f);
    }

    private void SetGain(Renderer r, float g)
    {
        if (r == null) return;
        bool on = g > 0.0001f;
        r.enabled = on;
        if (!on) return;
        r.GetPropertyBlock(_mpb);
        _mpb.SetFloat(_idGain, g);
        r.SetPropertyBlock(_mpb);
    }
}
