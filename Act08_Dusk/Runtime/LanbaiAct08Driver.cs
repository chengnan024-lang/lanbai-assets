// =====================================================================================================
//  LanbaiAct08Driver  v1 (2026-10-24; cloud session "云", branch pkg/clouds)  — act 8: dusk 8-i -> 8-ii -> 8b blue hour
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Checked with Common/Tools~/compile_check (Roslyn + U# lint), never in Unity.
//
//  Window 922.36 (the exit: the bus falls out of the sea's underside) -> 1149.31 (the main light stays this act's until F16:
//  act 9 writes no main light / ambient, Engineering/README_集成.md §8.2). Every number comes from Act08_Dusk/Act08_Layout.json,
//  baked into the fields by 蓝白/Build/Act08.
//  Writers (README_集成 §8, D-22, D-24, D-25, D-33 #6):
//    sky / fog / moon / stars  922.36 -> 1001.21: the sky presets by t — dusk_8i.Apply(); F10e dusk_8i.ApplyBlend(dusk_8ii)
//                              8 s; dusk_8ii.Apply(); F12 dusk_8ii.ApplyBlend(blue_hour) 6 s; blue_hour.Apply(). NOTHING through
//                              Apply / ApplyBlend at t >= 1001.21 (act 9 is the writer from there). Over the presets: _Udon_Fog
//                              (water -> air 8 s, 8-ii, F12 -> 0 linear by 1001.21) and _Udon_SunDisc (the sun line: grows to
//                              +-10 deg with the other sky, F12 collapses to a point and goes out in 6 s).
//    main light                922.36 -> 1149.31: the dusk sun (az 0, el +0.5, #FFA642, E 2.2: D-00) x the visible part of the
//                              disc under the ceiling's soft edge (layout reveal table) x the F12 collapse; floor 0.001.
//    RenderSettings            922.36 -> 1149.31: Trilight 8-i -> 8-ii -> 8b -> 9a near zero; fog density / colour.
//    the sea ceiling           922.36 -> 965.36: Sea_Ceiling (Lanbai/Sea CEILING, the sea kit's M_08_* materials) under R_Dusk at
//                              the exit plane; _Udon_SeaLevel / SeaMode 3 / SeaClock / ReflCube; _DissolveTime = t - 956.36 on
//                              the ceiling, its edge and the palace points; renderers off at 965.36 (SeaMode 0: ours).
//    the cards                 Lanbai/CloudCard (Clouds_v2): upper group, lower group (the other sky, 8-ii, x 0.82), wisps;
//                              colours by MPB (D-25: dusk -> blue hour), alpha / gain by t; 9a: EV-linear to dark by 1009.21.
//    exposure                  LanbaiGrade(t) = {dEV, 0, 0, 1}: the exit pin (APL 34) -> +0.5 EV at F9 -> 0 at 933.11; the blue
//                              hour 0 -> -1.09 EV (993.06 -> 1001.21, D-39 #1; Act08_Grade.json) -> 0 at 1009.21 (the
//                              dispatcher sums it; this driver never touches PPv2).
//  D-33 #6: LanbaiActivate(true) clears the 'applied' flags: the next tick rebuilds sky, fog, sun line, light, RenderSettings,
//  ceiling, cards from t alone (an Apply before any blend). Hand-back: only our own channels (ceiling off, SeaMode 0).
//  NOT written here: PPv2 (LB_Journey), the cabin (erosion, the wings, the door group's erosion for the Zhuangzi text: D-33 #7a),
//  the poem (LanbaiPoemDriver), act 9's first stars.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using Lanbai.Sky;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiAct08Driver : UdonSharpBehaviour
{
    [Header("Scene (filled by the builder)")]
    public GameObject[] roots;
    public Transform rDusk;                    // R_Dusk: vertical translation only, y = h(t)
    public Renderer ceilingInner, ceilingEdge, specks;
    public Material matCeiling, matCeilingFade; // M_08_SeaCeiling (opaque, until F10e), M_08_SeaCeilingFade
    public Renderer[] cards;                   // Lanbai/CloudCard renderers: upper, lower, wisps
    public int[] cardGroup;                    // 0 upper from 8-i, 1 upper from 8-ii, 2 lower (other sky, 8-ii), 3 wisp
    public float[] cardGain;
    public float[] cardFogCap;                 // r2: near 0 (D-42), mid 0.12, high 0.2, far 1
    public Vector4[] cardAmb;                  // D-42 #1: the near layer's dusk sky / ground light x amb (deep indigo body)
    public Vector4[] cardMelt;                 // r2: softer bases on the front cards (_Melt)
    public float[] cardTopY, cardDist;         // r2: 8-i cards show only while their top is under the gap's lower edge
    public float ceilingOuterR = 3100f;
    public Vector3[] wispBase, wispTangent;    // wisps only (index = wisp order among cards with group 3)
    public float[] wispDrift;
    public Light worldSun;                     // THE main light (D-24)
    public LanbaiSkyPreset dusk8i, dusk8ii, blueHour;
    public bool writeRenderSettings = false;   // tick with LB_Journey.extAtmosphere 922.36 -> 1149.31 (README_集成 §8.3)
    public bool writeMainLight = false;        // tick with LB_Journey.extSun 922.36 -> 1149.31
    public Texture reflCube;                   // _Udon_ReflCube: ReflCube_DuskLower (stand-in: Sea/Textures/Cube_DuskLower_256)

    [Header("Timeline (Act08_Layout.json)")]
    public float windowStart = 922.36f, windowEnd = 1149.31f;
    public float tExit = 922.36f, tF10e = 956.36f, tF12 = 987.06f, tEnd8 = 1001.21f, tCeilingOff = 965.36f;
    public float blend8iiDur = 8f, blendBlueDur = 9.5f;      // F12: >= 8 s per sky direction (the sky's 1.5 s lead + 8)
    public float wispOut0 = 950.36f, wispOut1 = 956.36f;
    public Vector2 blueFade = new Vector2(0.4f, 0.55f);       // final review A5: F12 gain x lerp(1, x, smoothstep(0, y, wb)): down, no rebound
    public float cardsIn0 = 956.36f, cardsIn1 = 964.36f, darkDur = 8f, darkEV = 6f;

    [Header("Motion (closed form, Act08_Layout motion)")]
    public float v0 = -1.5f;
    public float[] segT0, segDur, segV0, segV1;
    public float ceilingLocalY = 1.7f;

    [Header("Sun / light")]
    public Vector3 sunDir = new Vector3(0f, 0.008727f, 0.999962f);
    public Color sunColor = new Color(1f, 0.651f, 0.2588f, 1f);    // #FFA642 (sRGB; Unity linearises light colours)
    public float sunE = 2.2f, sunFloor = 0.001f;
    public float revealT0 = 922.36f, revealDt = 0.1f;
    public float[] reveal;                     // the visible fraction of the disc under the ceiling edge (layout reveal)
    public float discRadius = 0.265f, lineDeg = 10f, lineGrow0 = 959.36f, lineGrow = 5f, lineCollapse = 6f;
    public float sunEl0 = 0.5f, sunSinkDur = 3f;  // D-39 #2: the sun sinks +0.5 -> 0 deg first (3 s), then the line grows: ONE line

    [Header("Fog (_Udon_Fog.x)")]
    public float fogWater = 0.006f, fogAir = 0.00015f, fogII = 0.00025f, fogAirDur = 8f;

    [Header("RenderSettings (sRGB)")]
    public Color triSkyI = new Color(0.1098f, 0.2f, 0.3137f, 1f);      // #1C3350
    public Color triSkyII = new Color(0.2745f, 0.3333f, 0.5098f, 1f);  // #465582
    public Color triEquator = new Color(0.8157f, 0.5412f, 0.4392f, 1f); // #D08A70
    public Color triGround = new Color(0.298f, 0.3333f, 0.4667f, 1f);  // #4C5577
    public Color triSkyB = new Color(0.149f, 0.251f, 0.4314f, 1f);     // #26406E
    public Color triEquatorB = new Color(0.2902f, 0.3686f, 0.5569f, 1f); // #4A5E8E
    public Color triGroundB = new Color(0.1647f, 0.1882f, 0.3137f, 1f); // #2A3050
    public float triBlueDur = 8f, triDarkK = 0.03f;
    public Color fogColorI = new Color(0.871f, 0.588f, 0.573f, 1f);    // #DE9692 (bible fill)
    public Color fogColorII = new Color(0.878f, 0.643f, 0.639f, 1f);   // #E0A4A3
    public Color fogColorB = new Color(0.4353f, 0.5255f, 0.6902f, 1f); // #6F86B0

    [Header("Card colours (linear, D-25: Clouds_v2 cards_v2.json colours)")]
    public Vector4 upSun, upSky, upGround;     // duskU
    public Vector4 loSun, loSky, loGround;     // duskD (x the other sky's tint, baked by the builder)
    public Vector4 blueSky, blueGround;        // blue hour (no sun)

    [Header("Exposure (LanbaiGrade)")]
    public float[] gradeT, gradeDev;

    private MaterialPropertyBlock _mpb;
    private int _idSeaLevel, _idSeaMode, _idSeaClock, _idRefl, _idDissolve, _idFog, _idSunDisc, _idSunDir;
    private int _idGain, _idAlpha, _idSunColor, _idSkyUp, _idGround, _idFogCap, _idMelt, _idRimFade;
    private bool _ready, _seaModeOurs;
    private int _ceilingMat = -1, _ceilingOn = -1;   // -1 unknown (activation / backward jump: set from t), 0 / 1
    private int _skyStage = -1;                // 0 8-i applied, 1 blending to 8-ii, 2 8-ii applied, 3 blending to blue, 4 blue applied
    private float _lastT = -1f;
    // final review F4 (D-27 #4): what was written last; a state that does not change is not written again
    private bool _cardsValid, _cardsOff, _lightValid, _rsValid, _skyGlobalsValid;
    private float _cW2, _cWb, _cInII, _cWisp, _cDark, _cFade;
    private float _lRsWb;
    private float _lH = float.NaN, _lLightI, _lLightEl, _lRsW2, _lRsWB, _lRsDark, _lRsFog, _lFog, _lK, _lLine, _lSunEl;
    private float[] _window;
    private float[] _grade;

    // ---- CONTROL §5 ------------------------------------------------------------------------------------------------
    public void LanbaiTick(float t)
    {
        if (!_ready) _Init();
        if (t < windowStart || t > windowEnd) return;
        if (t < _lastT - 0.25f) { _skyStage = -1; _ceilingMat = -1; _ceilingOn = -1; Invalidate(); }   // a backward jump: rebuild from t
        _lastT = t;
        Evaluate(t);
    }

    public void LanbaiActivate(bool on)
    {
        if (roots != null)
            for (int i = 0; i < roots.Length; i++) if (roots[i] != null) roots[i].SetActive(on);
        if (!on && _ready) HandBack();
        // D-33 #6: everything is rebuilt from t on the next tick (late joiners, timeline drags)
        if (on) { _skyStage = -1; _ceilingMat = -1; _ceilingOn = -1; _lastT = -1f; Invalidate(); }
    }

    private void Invalidate()
    {
        _cardsValid = false; _cardsOff = false; _lightValid = false; _rsValid = false; _skyGlobalsValid = false; _lH = float.NaN;
    }

    public float[] LanbaiWindow()
    {
        if (_window == null) _window = new float[] { windowStart, windowEnd };
        return _window;
    }

    /// <summary>The exposure events (README_集成 §8.4): {dEV, 0, 0, 1} on 922.36 .. 1009.21 where non-zero, else null.</summary>
    public float[] LanbaiGrade(float t)
    {
        if (gradeT == null || gradeT.Length < 2 || t < gradeT[0] || t > gradeT[gradeT.Length - 1]) return null;
        float d = Table(gradeT, gradeDev, t);
        if (d == 0f) return null;
        if (_grade == null) _grade = new float[4];
        _grade[0] = d; _grade[1] = 0f; _grade[2] = 0f; _grade[3] = 1f;
        return _grade;
    }

    void Start()
    {
        _Init();
    }

    public void _Init()
    {
        if (_ready) return;
        _mpb = new MaterialPropertyBlock();
        _idSeaLevel = VRCShader.PropertyToID("_Udon_SeaLevel");
        _idSeaMode = VRCShader.PropertyToID("_Udon_SeaMode");
        _idSeaClock = VRCShader.PropertyToID("_Udon_SeaClock");
        _idRefl = VRCShader.PropertyToID("_Udon_ReflCube");
        _idFog = VRCShader.PropertyToID("_Udon_Fog");
        _idSunDisc = VRCShader.PropertyToID("_Udon_SunDisc");
        _idSunDir = VRCShader.PropertyToID("_Udon_SunDir");
        _idDissolve = VRCShader.PropertyToID("_DissolveTime");
        _idGain = VRCShader.PropertyToID("_Gain");
        _idAlpha = VRCShader.PropertyToID("_Alpha");
        _idSunColor = VRCShader.PropertyToID("_SunColor");
        _idSkyUp = VRCShader.PropertyToID("_SkyUpColor");
        _idGround = VRCShader.PropertyToID("_GroundColor");
        _idFogCap = VRCShader.PropertyToID("_FogCap");
        _idMelt = VRCShader.PropertyToID("_Melt");
        _idRimFade = VRCShader.PropertyToID("_RimFade");
        _ready = true;
    }

    // ---- helpers ---------------------------------------------------------------------------------------------------
    private float Smooth(float x)
    {
        x = Mathf.Clamp01(x);
        return x * x * (3f - 2f * x);
    }

    private float Depth(float t)                               // h(t): the bus under the exit plane (m)
    {
        if (t <= tExit) return 0f;
        float y = v0 * (t - tExit);
        for (int i = 0; i < segT0.Length; i++)
        {
            if (t <= segT0[i]) break;
            float x = Mathf.Min((t - segT0[i]) / segDur[i], 1f);
            float s = x * x * x - 0.5f * x * x * x * x;
            y += (segV1[i] - segV0[i]) * (segDur[i] * s + Mathf.Max(t - segT0[i] - segDur[i], 0f));
        }
        return -y;
    }

    private float Table(float[] ts, float[] vs, float t)      // piecewise linear over (ts, vs)
    {
        int n = ts.Length;
        if (t <= ts[0]) return vs[0];
        if (t >= ts[n - 1]) return vs[n - 1];
        for (int i = 1; i < n; i++)
            if (t < ts[i]) return Mathf.Lerp(vs[i - 1], vs[i], (t - ts[i - 1]) / Mathf.Max(ts[i] - ts[i - 1], 1e-5f));
        return vs[n - 1];
    }

    private float Reveal(float t)
    {
        if (reveal == null || reveal.Length == 0) return 1f;
        if (t >= tF10e) return 1f;
        float x = (t - revealT0) / revealDt;
        int i = Mathf.Clamp(Mathf.FloorToInt(x), 0, reveal.Length - 1);
        int j = Mathf.Min(i + 1, reveal.Length - 1);
        return Mathf.Lerp(reveal[i], reveal[j], Mathf.Clamp01(x - i));
    }

    private Vector3 SunNow(float t)                            // az 0; el +0.5 -> 0 over the transform (956.36 -> 964.36)
    {
        float el = Mathf.Deg2Rad * sunEl0 * (1f - Smooth((t - tF10e) / sunSinkDur));
        return new Vector3(sunDir.x * Mathf.Cos(el), Mathf.Sin(el), sunDir.z * Mathf.Cos(el)).normalized;
    }

    private float FogDensity(float t)
    {
        if (t < tExit + fogAirDur) return Mathf.Lerp(fogWater, fogAir, Smooth((t - tExit) / fogAirDur));
        if (t < tF10e) return fogAir;
        if (t < tF12) return Mathf.Lerp(fogAir, fogII, Smooth((t - tF10e) / blend8iiDur));
        return fogII * Mathf.Max(0f, 1f - (t - tF12) / (tEnd8 - tF12));   // 0 at 1001.21 (act 9 writes 0 from there)
    }

    // ---- per frame ---------------------------------------------------------------------------------------------------
    public void Evaluate(float t)
    {
        float h = Depth(t);
        if (rDusk != null && h != _lH) { rDusk.localPosition = new Vector3(0f, h, 0f); _lH = h; }   // constant after 995.06
        float w2 = Smooth((t - tF10e) / blend8iiDur);
        float wb = Smooth((t - tF12) / blendBlueDur);
        float collapse = Smooth((t - tF12) / lineCollapse);

        // ---- the sky / fog / moon / stars (the presets), only before 1001.21
        if (t < tEnd8) Sky(t);

        // ---- the main light (D-24): the sun x the disc under the ceiling edge x the F12 collapse
        if (writeMainLight && t < windowEnd)
        {
            if (worldSun == null) worldSun = RenderSettings.sun;
            if (worldSun != null)
            {
                float li = Mathf.Max(sunE * Reveal(t) * (1f - collapse), sunFloor);
                float le = Smooth((t - tF10e) / sunSinkDur);
                if (!_lightValid || li != _lLightI || le != _lLightEl)  // from 993.06 on: the floor, written once
                {
                    worldSun.transform.rotation = Quaternion.LookRotation(-SunNow(t));
                    worldSun.color = sunColor;
                    worldSun.intensity = li;
                    _lLightI = li; _lLightEl = le; _lightValid = true;
                }
            }
        }

        // ---- RenderSettings (Trilight; fog)
        if (writeRenderSettings && t < windowEnd)
        {
            float wB = Smooth((t - tF12) / triBlueDur);
            float dark = Mathf.Pow(triDarkK, Mathf.Clamp01((t - tEnd8) / darkDur));     // 9a: EV-linear to near zero
            float fd = t < tEnd8 ? FogDensity(t) : 0f;
            if (!_rsValid || w2 != _lRsW2 || wB != _lRsWB || dark != _lRsDark || wb != _lRsWb || fd != _lRsFog)   // F4: on a change only
            {
                Color sky = Color.Lerp(Color.Lerp(triSkyI.linear, triSkyII.linear, w2), triSkyB.linear, wB) * dark;
                Color eq = Color.Lerp(triEquator.linear, triEquatorB.linear, wB) * dark;
                Color gr = Color.Lerp(triGround.linear, triGroundB.linear, wB) * dark;
                RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
                RenderSettings.ambientSkyColor = sky.gamma;
                RenderSettings.ambientEquatorColor = eq.gamma;
                RenderSettings.ambientGroundColor = gr.gamma;
                RenderSettings.fogColor = Color.Lerp(Color.Lerp(fogColorI, fogColorII, w2), fogColorB, wb);
                RenderSettings.fogDensity = fd;
                _lRsW2 = w2; _lRsWB = wB; _lRsDark = dark; _lRsFog = fd; _lRsWb = wb; _rsValid = true;
            }
        }

        // ---- the sea ceiling (8-i; dissolves F10e -> 965.36)
        Ceiling(t, h);

        // ---- the cards
        Cards(t, w2, wb, h);
    }

    private void Sky(float t)
    {
        if (dusk8i == null || dusk8ii == null || blueHour == null) return;
        if (t < tF10e)
        {
            if (_skyStage != 0) { dusk8i.Apply(); _skyStage = 0; _skyGlobalsValid = false; }
        }
        else if (t < tF10e + blend8iiDur)
        {
            if (_skyStage != 1) { dusk8i.Apply(); _skyStage = 1; _skyGlobalsValid = false; }          // D-33 #6: a full write before the blend
            dusk8i.ApplyBlend(dusk8ii, Smooth((t - tF10e) / blend8iiDur));
        }
        else if (t < tF12)
        {
            if (_skyStage != 2) { dusk8ii.Apply(); _skyStage = 2; _skyGlobalsValid = false; }
        }
        else if (t < tF12 + blendBlueDur)
        {
            if (_skyStage != 3) { dusk8ii.Apply(); _skyStage = 3; _skyGlobalsValid = false; }
            dusk8ii.ApplyBlend(blueHour, Smooth((t - tF12) / blendBlueDur));
        }
        else
        {
            if (_skyStage != 4) { blueHour.Apply(); _skyStage = 4; _skyGlobalsValid = false; }
        }
        // over the presets: the fog density and the sun line (dusk_8ii lists _Udon_SunDisc in its blendSkip: ours).
        // A preset Apply() rewrites them, so they are always written in a stage that just applied or is blending.
        float fog = FogDensity(t);
        float k = 1f - Smooth((t - tF12) / lineCollapse);
        float line = lineDeg * Smooth((t - lineGrow0) / lineGrow) * k;   // review r1 B1: only once the discs touch
        float se = Smooth((t - tF10e) / sunSinkDur);
        bool blending = _skyStage == 1 || _skyStage == 3;
        if (blending || !_skyGlobalsValid || fog != _lFog || k != _lK || line != _lLine || se != _lSunEl)
        {
            VRCShader.SetGlobalVector(_idFog, new Vector4(fog, 0f, 0f, 1f));
            VRCShader.SetGlobalVector(_idSunDisc, new Vector4(k, discRadius, line, 1f));
            if (t >= tF10e)                                    // D-39 #2: the sun and its other self touch: one line
            {
                Vector3 sd = SunNow(t);
                VRCShader.SetGlobalVector(_idSunDir, new Vector4(sd.x, sd.y, sd.z, 1f));
            }
            _lFog = fog; _lK = k; _lLine = line; _lSunEl = se; _skyGlobalsValid = true;
        }
    }

    private void Ceiling(float t, float h)
    {
        bool on = t >= tExit && t < tCeilingOff;
        int onI = on ? 1 : 0;
        if (onI != _ceilingOn)                                 // only on a change (review r1: not every frame after 965.36)
        {
            if (ceilingInner != null) ceilingInner.enabled = on;
            if (ceilingEdge != null) ceilingEdge.enabled = on;
            if (specks != null) specks.enabled = on;
            _ceilingOn = onI;
        }
        if (!on)
        {
            if (_seaModeOurs) { VRCShader.SetGlobalFloat(_idSeaMode, 0f); _seaModeOurs = false; }
            return;
        }
        bool fade = t >= tF10e;
        int matI = fade ? 1 : 0;
        if (ceilingInner != null && matI != _ceilingMat)       // review r1: unknown after a scrub -> always set from t
        {
            ceilingInner.sharedMaterial = fade ? matCeilingFade : matCeiling;
            _ceilingMat = matI;
        }
        float tau = fade ? t - tF10e : -1f;
        SetDissolve(ceilingInner, tau);
        SetDissolve(ceilingEdge, tau);
        SetDissolve(specks, tau);
        VRCShader.SetGlobalFloat(_idSeaLevel, ceilingLocalY + h);
        VRCShader.SetGlobalFloat(_idSeaMode, 3f);
        VRCShader.SetGlobalVector(_idSeaClock, new Vector4(t, 0f, 0f, 1f));
        if (reflCube != null) VRCShader.SetGlobalTexture(_idRefl, reflCube);
        _seaModeOurs = true;
    }

    private void SetDissolve(Renderer r, float tau)
    {
        if (r == null) return;
        r.GetPropertyBlock(_mpb);
        _mpb.SetFloat(_idDissolve, tau);
        r.SetPropertyBlock(_mpb);
    }

    private float Gap8i(int i, float t, float h)
    {
        if (cardTopY == null || cardDist == null || i >= cardTopY.Length || i >= cardDist.Length) return 1f;
        float lo = Mathf.Atan(Mathf.Max(h, 0.05f) / ceilingOuterR);
        float top = Mathf.Atan((cardTopY[i] + h - ceilingLocalY) / Mathf.Max(cardDist[i], 1f));
        return Mathf.Max(Smooth((lo - top) / (0.5f * Mathf.Deg2Rad)), Smooth((t - tF10e) / 5f));
    }

    private void Cards(float t, float w2, float wb, float h)
    {
        if (cards == null || cardGroup == null || cardGain == null) return;
        int nW = wispBase == null ? 0 : Mathf.Min(wispBase.Length, Mathf.Min(wispTangent == null ? 0 : wispTangent.Length, wispDrift == null ? 0 : wispDrift.Length));
        int nC = Mathf.Min(cards.Length, Mathf.Min(cardGroup.Length, cardGain.Length));   // review r1: no unchecked indexing
        if (t >= tEnd8 + darkDur)                              // the end state: all off, written once
        {
            if (_cardsOff) return;
            for (int i = 0; i < nC; i++) if (cards[i] != null && cards[i].enabled) cards[i].enabled = false;
            _cardsOff = true; _cardsValid = false;
            return;
        }
        _cardsOff = false;
        float dark = Mathf.Pow(2f, -darkEV * Mathf.Clamp01((t - tEnd8) / darkDur));
        float inII = Smooth((t - cardsIn0) / Mathf.Max(cardsIn1 - cardsIn0, 1e-3f));
        float wisp = 1f - Smooth((t - wispOut0) / Mathf.Max(wispOut1 - wispOut0, 1e-3f));
        float fade = 1f + (blueFade.x - 1f) * Smooth(wb / Mathf.Max(blueFade.y, 1e-3f));   // final review A5: no rebound
        // final review F4: from F10e + 5 s the 8-i cards' gap term is 1, so the cards depend only on these six numbers;
        // while none of them moves (8-ii 965.4 -> 987.06, the blue hour 993.06 -> 1001.21) the loop is skipped
        bool gapDone = t >= tF10e + 5f;
        if (_cardsValid && gapDone && w2 == _cW2 && wb == _cWb && inII == _cInII && wisp == _cWisp && dark == _cDark && fade == _cFade) return;
        _cW2 = w2; _cWb = wb; _cInII = inII; _cWisp = wisp; _cDark = dark; _cFade = fade; _cardsValid = gapDone;
        Vector4 uS = upSun * (1f - wb), uK = Vector4.Lerp(upSky, blueSky, wb), uG = Vector4.Lerp(upGround, blueGround, wb);
        Vector4 lS = loSun * (1f - wb), lK = Vector4.Lerp(loSky, blueSky, wb), lG = Vector4.Lerp(loGround, blueGround, wb);
        int wi = 0;
        for (int i = 0; i < nC; i++)
        {
            Renderer r = cards[i];
            if (r == null) continue;
            int g = cardGroup[i];
            float a = g == 0 ? Gap8i(i, t, h) : (g == 3 ? wisp : inII);
            bool vis = a > 0.001f;
            if (g == 3)
            {
                if (vis && wi < nW)                            // final review F4: a wisp moves only while it is seen
                    r.transform.localPosition = wispBase[wi] + wispTangent[wi] * (wispDrift[wi] * (t - tExit));
                wi++;
            }
            if (r.enabled != vis) r.enabled = vis;
            if (!vis) continue;
            bool lower = g == 2;
            r.GetPropertyBlock(_mpb);
            _mpb.SetFloat(_idGain, cardGain[i] * dark * fade);
            _mpb.SetFloat(_idRimFade, 1f);                   // final review A4: the rim fades with _Alpha and the melt
            _mpb.SetFloat(_idAlpha, a);
            _mpb.SetVector(_idSunColor, lower ? lS : uS);
            if (cardAmb != null && i < cardAmb.Length)   // (1,1,1,1) everywhere but the near layer
            {
                // the dusk part only; the blue hour lerps to the same blue colours as every other card
                Vector4 am = cardAmb[i];
                _mpb.SetVector(_idSkyUp, Vector4.Lerp(Vector4.Scale(lower ? loSky : upSky, am), blueSky, wb));
                _mpb.SetVector(_idGround, Vector4.Lerp(Vector4.Scale(lower ? loGround : upGround, am), blueGround, wb));
            }
            else
            {
                _mpb.SetVector(_idSkyUp, lower ? lK : uK);
                _mpb.SetVector(_idGround, lower ? lG : uG);
            }
            if (cardFogCap != null && i < cardFogCap.Length) _mpb.SetFloat(_idFogCap, cardFogCap[i]);
            if (cardMelt != null && i < cardMelt.Length) _mpb.SetVector(_idMelt, cardMelt[i]);
            r.SetPropertyBlock(_mpb);
        }
    }

    private void HandBack()
    {
        // only our own channels (D-22): the ceiling and its SeaMode; the shared sky / fog / light are left for the next writer
        if (ceilingInner != null) ceilingInner.enabled = false;
        if (ceilingEdge != null) ceilingEdge.enabled = false;
        if (specks != null) specks.enabled = false;
        _ceilingOn = 0;
        if (_seaModeOurs) { VRCShader.SetGlobalFloat(_idSeaMode, 0f); _seaModeOurs = false; }
    }
}
