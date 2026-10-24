// =====================================================================================================
//  LanbaiAct06Driver.cs   蓝白 · 第 6 幕「晨」的驱动（UdonSharp）   cloud session "云", 2026-10-24
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn + U# rules). !!!
//
//  CONTROL §5 interface (called by Director/LanbaiActDispatcher):
//     LanbaiTick(t)       every frame inside LanbaiWindow()
//     LanbaiActivate(on)  switches `roots` (R_Dawn); on 'off' hands back ONLY this act's own channels (D-22)
//     LanbaiWindow()      {248.64, 363.62}
//  Writers (Engineering/README_集成.md §8, D-22, D-24):
//     248.64 (cut 1, under the black)  the sky / fog / moon / stars: skyPreset.Apply() (Sky/SkyPresets 'dawn' lists EVERY
//                                       sky / fog / moon / star global any preset uses, so the moon left by the gate is
//                                       overwritten here); re-applied on a backward jump into the window
//     252.64 -> 363.615                THE main light (RenderSettings.sun, D-24): the dawn sun az +30 / el 5.8 (D-12; the
//                                       sky preset's own elevation), #FFC47A, E 3 x the cover's occlusion (table), from the
//                                       0.001 that act 4c leaves; handed to the sea at the eye-under moment (363.615)
//     252.64 -> 362.26                 RenderSettings (writeRenderSettings, LB_Journey.extAtmosphere): Trilight, fog
//     252.64 -> 266.4                  the overlay (Lanbai_Overlay v2): pre-roll, then the per-direction dawn curve
//     300.0 -> 363.26                  the sea (ABOVE, M_06_Sea): _Udon_SeaLevel / SeaMode 1 / SeaClock; off at F2h (the sea's
//                                       driver switches its own plane on, same y: Act07_Layout handover)
//  Every number comes from Act06_Dawn/Act06_Layout.json, baked into the fields by 蓝白/Build/Act06.
//  NOT written here: PPv2 (LB_Journey.ApplyGrades: S6 is set under the cut-1 black), the cabin (_Udon_Cabin*: the
//  cabin bleach 0 -> 0.10 F0 -> F1 is the cabin's writer; Act06_Dawn/给总控.md).
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using Lanbai.Sky;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiAct06Driver : UdonSharpBehaviour
{
    [Header("Scene (filled by the builder)")]
    public GameObject[] roots;
    public Transform rDawn;                    // R_Dawn: vertical translation only, y = d(t)
    public Renderer plain;                     // Lanbai/CloudPlain proxy
    public Renderer plainMist;                 // Lanbai/CloudPlainMist (r2: the slot's mist; same proxy, same _SlotOpen)
    public Renderer seaRenderer;               // Sea_Disc with M_06_Sea (ABOVE)
    public Renderer[] cards;                   // Lanbai/CloudCard renderers (placed cards, then the ring)
    public float[] cardGain;
    public float[] cardMirror;
    public bool[] cardIsRing;
    public Light worldSun;                     // THE main light (D-24); the builder wires RenderSettings.sun if empty
    public LanbaiSkyPreset skyPreset;          // 'dawn' (Lanbai_SkyPresets/dawn, 蓝白/Sky/Build Sky)
    public LanbaiOverlay overlay;              // Overlay/Runtime/LanbaiOverlay.cs (one in the scene)
    public bool writeRenderSettings = false;   // tick only with LB_Journey.extAtmosphere (README_集成 §8.3)
    public bool writeMainLight = false;        // tick only with LB_Journey.extSun
    public bool driveOverlay = true;
    public Texture reflCube;                   // _Udon_ReflCube for the sea (the dawn cube, when Control bakes it)

    [Header("Timeline (Act06_Layout.json)")]
    public float windowStart = 248.64f, windowEnd = 363.62f;
    public float tApplySky = 248.64f, tLight0 = 252.64f, tLight1 = 363.615f, tRS1 = 362.26f;
    public float tF0 = 251.64f, tSeaOn = 300f, tEntry = 363.26f;
    public float tPreroll0 = 252.64f, tDawn0 = 254.14f, dawnT = 8.65f, tOverlayOff = 266.4f;
    public float slotOpen0 = 281.86f, slotOpen1 = 287.86f;
    public float ringOff0 = 285.86f, ringOff1 = 289.86f;
    public float[] answerT0;                   // the towers' crowns answer F0s (+0.7 EV each, 4 s, staggered 1.5 s)
    public int[] answerCard;
    public float answerDur = 4f, answerEV = 0.7f;
    public float calmPatchT0 = 328.36f, calmPatchDur = 6f, calmPatchR = 300f;
    public float calmAllT0 = 337f, calmAllDur = 8f, calmAllV = 0.85f;

    [Header("Motion (closed form, Act06_Layout motion)")]
    public float vStart = 4f;
    public float[] segT0, segDur, segV0, segV1;
    public float seaLevelLocal = -2604.6f;

    [Header("Sun")]
    public Vector3 sunDir = new Vector3(0.4983f, 0.1011f, 0.8611f);
    public Color sunColor = new Color(1f, 0.7686f, 0.4784f, 1f);     // #FFC47A (sRGB; Unity linearises light colours)
    public float sunE = 3f, sunFloorOccluded = 0.1f, sunFloorStart = 0.001f;
    public float sunTabT0 = 248.64f, sunTabDt = 0.25f;
    public float[] sunTab;                     // 1 = clear, 0 = behind the cover / lip (Act06_Layout sun_table)
    public float sunSmooth = 2.2f;             // the disc takes ~2.2 s to clear
    public Vector4 seaSunColor = new Vector4(5.8563f, 3.6146f, 2.0024f, 0f);   // M_06_Sea _SunColor (the disc's radiance)

    [Header("RenderSettings (sRGB colours)")]
    public Color triSky = new Color(0.3529f, 0.4706f, 0.7216f, 1f);       // #5A78B8
    public Color triEquator = new Color(0.7843f, 0.7059f, 0.7216f, 1f);   // #C8B4B8
    public Color triGround = new Color(0.5608f, 0.6275f, 0.7451f, 1f);    // #8FA0BE
    public Color fogColorGamma = new Color(0.7686f, 0.7216f, 0.7529f, 1f); // #C4B8C0 (bible §6·6 雾)
    public float fogDensity = 0.00012f;        // the dawn preset's _Udon_Fog.x
    // D-35 #3: act 6 writes its own far horizon / nadir / band width over the dawn preset (pulled to #8593AA's hue)
    public Vector4 fogFarAct = new Vector4(0.5319f, 0.6314f, 0.9037f, 1f);
    public Vector4 fogNadirAct = new Vector4(0.2183f, 0.2591f, 0.3709f, 1f);
    public float fogWidthAct = 40f;
    public Vector4 fogNearAct = new Vector4(3.0907f, 0.8444f, 0.2586f, 1f);     // the preset's near / zenith (re-written x k)
    public Vector4 fogZenithAct = new Vector4(0.3088f, 0.4944f, 1.0348f, 1f);
    public float fogColourK = 0.7f;            // D-35 #2: under the cover the haze is in shadow (same timing as the density)
    public float mistClockScale = 1f;          // _MistClock = t (the mist's undulation and wisps drift with the timeline)
    public float fogUnder = 0.00003f, fogDownT0 = 305.4f, fogUpT0 = 318.36f, fogDur = 4f;   // thinner haze under the cover

    [Header("Overlay (Overlay/README §3: 5 -> 6)")]
    public Color overlayFill = new Color(0.0027f, 0.0006f, 0f, 1f);       // S6 row #090200, linear
    public float lBlack = 0.0013f, lDawn = 0.652f;                         // #030409; L210
    public Vector3 lobeZenith = new Vector3(0f, 1f, 0f);
    public float lobeZenithDeg = 40f, leadZenith = 0f;
    public float lobeBelowDeg = 60f, leadBelow = 2.2f;
    public float lobeSunDeg = 30f, leadSun = 3.3f;
    public float leadElse = 2.0f, leadSoft = 30f;

    private MaterialPropertyBlock _mpb;
    private int _idSeaLevel, _idSeaMode, _idSeaClock, _idSlotOpen, _idGain, _idAlpha, _idMirror;
    private int _idFog, _idHorizonC, _idNadirC, _idBandW, _idNearC, _idZenithC, _idMistClock;
    private int _idCalmAll, _idCalmPatch, _idSunColor, _idRefl, _idReflHdr, _idReflExp;
    private bool _ready, _skyApplied, _sunTaken, _overlayHidden, _lobesSet;
    private float _lastT = -1f;
    private float[] _window;

    // ---- CONTROL §5 ------------------------------------------------------------------------------------------------
    public void LanbaiTick(float t)
    {
        if (!_ready) _Init();
        if (t < windowStart || t > windowEnd) return;          // D-27 #4: nothing per frame outside the window
        // a backward jump (scrubbing) re-applies the sky; a jump back before the overlay's end re-arms it
        if (t < _lastT - 0.5f) { _skyApplied = false; _overlayHidden = false; _lobesSet = false; }
        else if (t < _lastT && t < tOverlayOff) { _overlayHidden = false; _lobesSet = false; }   // r2 (S6): small drags too
        _lastT = t;
        Evaluate(t);
    }

    public void LanbaiActivate(bool on)
    {
        if (roots != null)
            for (int i = 0; i < roots.Length; i++) if (roots[i] != null) roots[i].SetActive(on);
        if (!on && _ready) HandBack();
        // D-33 #6: on activation everything is rebuilt from t alone (late joiners, timeline drags): the next tick
        // re-applies the dawn preset (sky / fog / moon / stars), re-arms the overlay and writes the main light,
        // RenderSettings, the plain, the cards and the sea from t; nothing is taken from the door or left-over values
        if (on) { _skyApplied = false; _overlayHidden = false; _lobesSet = false; _lastT = -1f; }
    }

    public float[] LanbaiWindow()
    {
        if (_window == null) _window = new float[] { windowStart, windowEnd };
        return _window;
    }

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
        _idRefl = VRCShader.PropertyToID("_Udon_ReflCube");
        _idReflHdr = VRCShader.PropertyToID("_Udon_ReflCube_HDR");
        _idReflExp = VRCShader.PropertyToID("_Udon_ReflExposure");
        _idSlotOpen = VRCShader.PropertyToID("_SlotOpen");
        _idGain = VRCShader.PropertyToID("_Gain");
        _idAlpha = VRCShader.PropertyToID("_Alpha");
        _idMirror = VRCShader.PropertyToID("_Mirror");
        _idCalmAll = VRCShader.PropertyToID("_CalmAll");
        _idFog = VRCShader.PropertyToID("_Udon_Fog");
        _idHorizonC = VRCShader.PropertyToID("_Udon_HorizonColor");
        _idNadirC = VRCShader.PropertyToID("_Udon_NadirColor");
        _idBandW = VRCShader.PropertyToID("_Udon_FogBandWidth");
        _idNearC = VRCShader.PropertyToID("_Udon_FogBandColor");
        _idZenithC = VRCShader.PropertyToID("_Udon_ZenithColor");
        _idMistClock = VRCShader.PropertyToID("_MistClock");
        _idCalmPatch = VRCShader.PropertyToID("_CalmPatch");
        _idSunColor = VRCShader.PropertyToID("_SunColor");
        // the cards' per-renderer values (edit-mode MPBs are lost on Play: gate test pitfall 9)
        if (cards != null)
            for (int i = 0; i < cards.Length; i++) CardMPB(i, cardGain[i], 1f);
        _ready = true;
    }

    // ---- helpers ------------------------------------------------------------------------------------------------------
    private float Smooth(float x)
    {
        x = Mathf.Clamp01(x);
        return x * x * (3f - 2f * x);
    }

    private float SmoothInt(float x)                           // integral of smoothstep, 0..x (linear beyond 1)
    {
        if (x <= 0f) return 0f;
        if (x >= 1f) return 0.5f + (x - 1f);
        return x * x * x - 0.5f * x * x * x * x;
    }

    public float Descent(float t)                              // metres descended since F0 (Act06_Layout motion)
    {
        float d = vStart * (t - tF0);
        for (int i = 0; i < segT0.Length; i++)
            d += (segV1[i] - segV0[i]) * segDur[i] * SmoothInt((t - segT0[i]) / segDur[i]);
        return d;
    }

    private float SunVisible(float t)                          // the table, smoothed over sunSmooth seconds
    {
        if (sunTab == null || sunTab.Length == 0) return 1f;
        int n = 5;
        float acc = 0f;
        for (int k = 0; k < n; k++)
        {
            float tt = t + sunSmooth * ((k + 0.5f) / n - 0.5f);
            int i = Mathf.Clamp(Mathf.RoundToInt((tt - sunTabT0) / sunTabDt), 0, sunTab.Length - 1);
            acc += sunTab[i];
        }
        return Smooth(acc / n);
    }

    private void CardMPB(int i, float gain, float alpha)
    {
        Renderer r = cards[i];
        if (r == null) return;
        r.GetPropertyBlock(_mpb);
        _mpb.SetFloat(_idGain, gain);
        _mpb.SetFloat(_idAlpha, alpha);
        _mpb.SetFloat(_idMirror, cardMirror[i]);
        r.SetPropertyBlock(_mpb);
    }

    // ---- per frame ----------------------------------------------------------------------------------------------------
    public void Evaluate(float t)
    {
        float d = Descent(t);
        if (rDawn != null) rDawn.localPosition = new Vector3(0f, d, 0f);

        // the sky / fog / moon / stars: once, under the cut-1 black (and again after a backward jump)
        if (!_skyApplied && t >= tApplySky && skyPreset != null)
        {
            skyPreset.Apply();
            _skyApplied = true;
        }

        float sunVis = SunVisible(t);

        // the fog density (the sky / fog group is this act's from 248.64 to F2h: the preset's 0.00012, thinner under the
        // cover). Written after Apply(); the colour stays the preset's (LanbaiHorizon model B)
        float under = Smooth((t - fogDownT0) / fogDur) * (1f - Smooth((t - fogUpT0) / fogDur));
        float fogD = Mathf.Lerp(fogDensity, fogUnder, under);
        if (_skyApplied && t < tEntry)
        {
            VRCShader.SetGlobalVector(_idFog, new Vector4(fogD, 0f, 0f, 1f));
            // D-35 #3: the fog's cool side (README §3); D-35 #2: x k under the cover. The other fog globals stay the preset's
            float k = Mathf.Lerp(1f, fogColourK, under);
            VRCShader.SetGlobalVector(_idHorizonC, new Vector4(fogFarAct.x * k, fogFarAct.y * k, fogFarAct.z * k, 1f));
            VRCShader.SetGlobalVector(_idNadirC, new Vector4(fogNadirAct.x * k, fogNadirAct.y * k, fogNadirAct.z * k, 1f));
            VRCShader.SetGlobalVector(_idNearC, new Vector4(fogNearAct.x * k, fogNearAct.y * k, fogNearAct.z * k, 1f));
            VRCShader.SetGlobalVector(_idZenithC, new Vector4(fogZenithAct.x * k, fogZenithAct.y * k, fogZenithAct.z * k, 1f));
            VRCShader.SetGlobalFloat(_idBandW, fogWidthAct);
        }

        // the main light (D-24)
        if (writeMainLight && t >= tLight0 && t < tLight1)
        {
            if (worldSun == null) worldSun = RenderSettings.sun;
            if (worldSun != null)
            {
                _sunTaken = true;
                worldSun.transform.rotation = Quaternion.LookRotation(-sunDir);
                worldSun.color = sunColor;
                float k = Mathf.Lerp(sunFloorOccluded, 1f, sunVis);
                worldSun.intensity = Mathf.Max(sunE * k, sunFloorStart);
            }
        }

        // RenderSettings (Trilight, fog) while this act owns them
        if (writeRenderSettings && t >= tLight0 && t < tRS1)
        {
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = triSky;
            RenderSettings.ambientEquatorColor = triEquator;
            RenderSettings.ambientGroundColor = triGround;
            RenderSettings.fogColor = fogColorGamma;
            RenderSettings.fogDensity = fogD;
        }

        // the plain: the slot opens at F1 (6 s)
        if (plain != null)
        {
            plain.GetPropertyBlock(_mpb);
            _mpb.SetFloat(_idSlotOpen, Smooth((t - slotOpen0) / Mathf.Max(slotOpen1 - slotOpen0, 1e-3f)));
            plain.SetPropertyBlock(_mpb);
        }
        if (plainMist != null)
        {
            plainMist.GetPropertyBlock(_mpb);
            _mpb.SetFloat(_idMistClock, t * mistClockScale);
            _mpb.SetFloat(_idSlotOpen, Smooth((t - slotOpen0) / Mathf.Max(slotOpen1 - slotOpen0, 1e-3f)));
            plainMist.SetPropertyBlock(_mpb);
        }

        // the cards: the towers answer F0s, the ring fades as the slot walls rise past the windows
        if (cards != null)
        {
            float ringA = 1f - Smooth((t - ringOff0) / Mathf.Max(ringOff1 - ringOff0, 1e-3f));
            for (int i = 0; i < cards.Length; i++)
            {
                if (cards[i] == null) continue;
                float g = cardGain[i];
                if (answerCard != null)
                    for (int j = 0; j < answerCard.Length; j++)
                        if (answerCard[j] == i) g *= Mathf.Pow(2f, answerEV * Smooth((t - answerT0[j]) / answerDur));
                bool ring = cardIsRing[i];
                cards[i].enabled = !ring || ringA > 0f;
                CardMPB(i, g, ring ? ringA : 1f);
            }
        }

        // the sea (ABOVE): on from inside the canyon (occluded) to F2h
        bool seaOn = t >= tSeaOn && t < tEntry;
        if (seaRenderer != null)
        {
            seaRenderer.enabled = seaOn;
            if (seaOn)
            {
                float level = seaLevelLocal + d;
                VRCShader.SetGlobalFloat(_idSeaLevel, level);
                VRCShader.SetGlobalFloat(_idSeaMode, 1f);
                VRCShader.SetGlobalVector(_idSeaClock, new Vector4(t, 0f, 0f, 1f));
                if (reflCube != null)
                {
                    VRCShader.SetGlobalTexture(_idRefl, reflCube);
                    VRCShader.SetGlobalVector(_idReflHdr, new Vector4(1f, 1f, 0f, 0f));
                    VRCShader.SetGlobalFloat(_idReflExp, 1f);
                }
                seaRenderer.GetPropertyBlock(_mpb);
                _mpb.SetFloat(_idCalmAll, calmAllV * Smooth((t - calmAllT0) / calmAllDur));
                _mpb.SetVector(_idCalmPatch, new Vector4(0f, 0f, calmPatchR, Smooth((t - calmPatchT0) / calmPatchDur)));
                _mpb.SetVector(_idSunColor, seaSunColor * sunVis);
                seaRenderer.SetPropertyBlock(_mpb);
            }
        }

        // the overlay: black -> dawn (one curve built for the brightest view, per-direction starts; Overlay/README §3)
        if (driveOverlay && overlay != null && !_overlayHidden && t >= tPreroll0)
        {
            if (t < tDawn0)
            {
                float a0 = EvAlpha(0f);
                float x = (t - tPreroll0) / Mathf.Max(tDawn0 - tPreroll0, 1e-3f);
                // EV-linear from the black to the curve's floor
                float aCur = Mathf.Lerp(1f, a0, x);
                overlay.SetFlat(overlayFill, aCur, 0f);
            }
            else if (t < tOverlayOff)
            {
                if (!_lobesSet)
                {
                    // zenith / skylight first, below +2.2, the sun's sector (az +30, D-12) +3.3, everything else +2.0
                    overlay.SetLobe(0, lobeZenith, lobeZenithDeg, leadZenith);
                    overlay.SetLobe(1, Vector3.down, lobeBelowDeg, leadBelow);
                    overlay.SetLobe(2, new Vector3(sunDir.x, 0f, sunDir.z).normalized, lobeSunDeg, leadSun);
                    overlay.SetLeadElse(leadElse, leadSoft);
                    _lobesSet = true;
                }
                overlay.SetCurve(overlayFill, 0f, t - tDawn0, dawnT, lBlack, lDawn, lDawn, lBlack);
            }
            else
            {
                overlay.Hide();
                _overlayHidden = true;
            }
        }

        if (t >= tLight1) HandBackLight();
    }

    private float EvAlpha(float x)                             // LanbaiOverlay.EvOverlayAlpha with this act's luminances
    {
        float floorL = 0.004f;
        float a = Mathf.Max(lBlack, floorL), b = Mathf.Max(lDawn, floorL);
        float L = a * Mathf.Pow(b / a, Mathf.Clamp01(x));
        float den = lDawn - lBlack;
        return Mathf.Clamp01((lDawn - L) / den);
    }

    private void HandBackLight()
    {
        // the main light stays ON (bible 1.6): the sea takes it at the eye-under moment; nothing of ours to clear
        _sunTaken = false;
    }

    private void HandBack()
    {
        // only this act's own channels (D-22): the sea plane / mode while ours; never w = 0 on shared sky / fog
        if (seaRenderer != null) seaRenderer.enabled = false;
        if (_lastT < tEntry) VRCShader.SetGlobalFloat(_idSeaMode, 0f);
        // r2 (review r1 S6): the overlay is ours from the preroll to its end: leaving mid-curve (a seek, a scrub back
        // before 252.64) must not leave it half black over another act
        if (driveOverlay && overlay != null && !_overlayHidden && _lastT >= tPreroll0)
        {
            overlay.Hide();
            _overlayHidden = true;
        }
        _sunTaken = false;
    }
}
