// Lanbai / 蓝白 -- LanbaiInsideDriver: act 4c (inside the tear, U9 -> U12) and act 5 (the plunge, U12 -> F0).
//
// UdonSharp 1.x. UNCOMPILED (cloud side): Roslyn type-check only (UnityEngine 2021.1 + UdonSharp / VRC / PPv2 stubs).
// Check in the Class Exposure Tree: VRCShader.SetGlobalVector / SetGlobalFloat, RenderSettings.fogColor / fogDensity /
// ambientSkyColor / ambientEquatorColor / ambientGroundColor (if not exposed: untick writeRenderSettings, the
// LanbaiFog shaders do not need them), Light.intensity, Transform.localPosition, GameObject.SetActive.
//
// Every number is a function of the timeline second t (bible v2.1 §6·4c, §6·5, §6.x rows 12-17). The editor build
// (蓝白/Build/04c 门内) fills the arrays from InsideLayout.json; the Tools~ Python (inside_drive.py) computes the same.
//
// Director interface (CONTROL §5):   LanbaiTick(t) every frame inside LanbaiWindow(); LanbaiActivate(on) under cover;
//                                    LanbaiGrade(t) = this act's grade event (FLASH_TEAR) for the dispatcher to sum.

using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiInsideDriver : UdonSharpBehaviour
{
    [Header("Cues (timeline seconds, from FromLocal/cues.json)")]
    public float tU6 = 133.80f;
    public float tU9 = 179.55f;
    public float tVoiceEnd = 233.80f;
    public float tU12 = 248.64f;
    public float tLichtDial = 196.10f;            // 'ein Lichtchen' (bible; cues.json's note says 193.1)
    public float tSleeveExit = 231.0f;
    public float[] lipT = new float[8];           // LIP1..LIP8
    public float[] bandStart = new float[8];      // light band starts (lip 1 delayed to U9 + 0.6)
    public float[] bandSweep = new float[8];      // 1.2 .. 2.4 s

    [Header("Motion")]
    public float vEnd = 12f;                      // m/s after the deceleration
    public Transform insideRoot;                  // R_Inside: localPosition = (0, 0, -s(t))
    public GameObject insideRootObject;           // activated / deactivated under cover (and preheated at spawn)
    public float[] lipS = new float[8];           // s of every lip plane (m)

    [Header("Fog (LanbaiFog model B 'gradient'; fills are linear)")]
    public Color[] zoneFill = new Color[8];       // zone k = the air between lip k and k+1 (zone 8 = the coda)
    public float fogAheadM = 250f;
    public float fogDensityGate = 0.0006f;
    public float fogDensityInside = 0.0035f;
    public float nadirK = 0.80f;
    public float aheadK = 1.0f, behindK = 0.72f, zenithK = 0.85f;
    public float bandWidthDeg = 100f;           // the fog falls off sideways: the frame's edges are darker than ahead
    // r06 (art review r05 #6): after the sleeve the gradient turns toward the dot and narrows into a radial falloff
    public float codaBandWidthDeg = 40f, codaSideK = 0.45f, codaTopK = 0.38f;
    public float dotAzDeg = -6.5f;
    public float sleeveFogK = 0.75f, sleeveDepth = 85.51f;     // r07: darker air inside lip 8's sleeve
    // chief engineer r1 #2: off by default. Tick only after the local timeline has handed act 4c / 5's window
    // (177.55 -> 252.64) to the dispatcher (extWindows, extAtmosphere / extSun); otherwise LB_Journey writes these.
    public bool writeRenderSettings = false;
    public bool writeMainLight = false;

    [Header("Lips visible (bible: <= 3 at once; r06)")]
    public Material[] lipMats;                    // every lip material (sheet, fringe, hang, threads, plies, wall)
    public float[] lipMatLip;                     // which lip (1..8) each material belongs to
    public float lip8HoldM = 70f, lip8RampM = 60f;

    [Header("Lichtchen ahead (sky object)")]
    public Transform dotTransform;                // bus-anchored, 2.3 km along the dot direction from the hero eye
    public float dotAppear = 193.90f;             // LIP4
    public float dotAppearDur = 2.5f;
    public float dotGrowFrom = 202.40f;           // U11
    public float dotStop = 246.39f;               // U12 - 2.25: nothing changes after this
    public Vector2 dotCoreDeg = new Vector2(0.3f, 0.9f);
    public Vector2 dotGlowDeg = new Vector2(4f, 12f);

    [Header("Fibres (current lip colour for the loose threads)")]
    public Color[] fibreFill = new Color[8];
    public float looseGain = 1f;

    [Header("Cabin")]
    public Color cabinAmbientGate = new Color(0.0164f, 0.0232f, 0.0409f, 1f) * 0.3f;   // #232A3A x 0.3 (linear)
    public Color cabinAmbientInside = new Color(0.4621f, 0.5457f, 0.7084f, 1f) * 0.3f; // #B5C3DB x 0.30
    public Color triSkyGate = new Color(0.0060f, 0.0052f, 0.0144f);     // act 4 Trilight #0C1020 (bible §6·4)
    public Color triEquatorGate = new Color(0.0129f, 0.0159f, 0.0343f); // #1E2234
    public Color triGroundGate = new Color(0.0185f, 0.0232f, 0.0513f);  // #262A40
    public Color triSky = new Color(0.0467f, 0.0648f, 0.1248f);    // #3D4863
    public Color triEquator = new Color(0.0723f, 0.1003f, 0.1946f); // #4C5979
    public Color triGround = new Color(0.0137f, 0.0217f, 0.0437f);  // #1F283B
    public Light worldMainLight;
    public float mainLightGate = 1.0f;
    public float mainLightInside = 0.001f;
    public float gradeFadeFrom = 180.05f;         // S4 -> S4c window: the cabin / ambient changes ride on it
    public float gradeFadeDur = 8f;
    public Color[] bandColour = new Color[8];     // linear E x colour of each crossing band (solved: seat top <= luma 120)
    public float bandSoft = 1.5f, bandTail = 3.5f;
    public Color dialBase = new Color(0.4f, 0.10f, 0.0f);          // act 2's dial fill (#FF7703 @ +0.71)
    public Color dialBright = new Color(4.38f, 0.83f, 0.0f);       // #FF7B00 @ +2.13

    [Header("Act 5")]
    public LanbaiOverlay overlay;
    public LanbaiExposure exposure;               // only used when writeExposure is ticked (single-act tests)
    public bool writeExposure = false;
    public Color blackFillS4c = new Color(0.00091f, 0.00121f, 0f); // #030400
    public Color blackFillS6 = new Color(0.00273f, 0.00061f, 0f);  // #090200
    public float flashEV = 1.5f;

    // ------------------------------------------------------------------------------------------------ ids
    private int _idPortal, _idDot, _idFibre, _idClock, _idFogInside, _idDensity, _idBandDir, _idBandColor, _idBandWidth,
        _idHorizon, _idZenith, _idNadir, _idShape, _idBelow, _idAmbient, _idSlice, _idSliceColor, _idDial;
    private bool _ready;
    private float _lastT = -1f;

    void Start()
    {
        Init();
    }

    private void Init()
    {
        if (_ready) return;
        _idPortal = VRCShader.PropertyToID("_Udon_InsidePortal");
        _idDot = VRCShader.PropertyToID("_Udon_InsideDot");
        _idFibre = VRCShader.PropertyToID("_Udon_InsideFibre");
        _idClock = VRCShader.PropertyToID("_Udon_InsideClock");
        _idFogInside = VRCShader.PropertyToID("_Udon_InsideFog");
        _idDensity = VRCShader.PropertyToID("_Udon_FogDensity");
        _idBandDir = VRCShader.PropertyToID("_Udon_FogBandDir");
        _idBandColor = VRCShader.PropertyToID("_Udon_FogBandColor");
        _idBandWidth = VRCShader.PropertyToID("_Udon_FogBandWidth");
        _idHorizon = VRCShader.PropertyToID("_Udon_HorizonColor");
        _idZenith = VRCShader.PropertyToID("_Udon_ZenithColor");
        _idNadir = VRCShader.PropertyToID("_Udon_NadirColor");
        _idShape = VRCShader.PropertyToID("_Udon_FogShape");
        _idBelow = VRCShader.PropertyToID("_Udon_FogBelow");
        _idAmbient = VRCShader.PropertyToID("_Udon_CabinAmbient");
        _idSlice = VRCShader.PropertyToID("_Udon_CabinSlice");
        _idSliceColor = VRCShader.PropertyToID("_Udon_CabinSliceColor");
        _idDial = VRCShader.PropertyToID("_Udon_RadioDial");
        _ready = true;
    }

    // ------------------------------------------------------------------------------------------------ interface
    public float[] LanbaiWindow()
    {
        return new float[] { tU9 - 2.0f, tU12 + 4.0f };      // to F0 + 1: then act 6 takes the overlay (the dawn pre-roll)
    }

    public void LanbaiActivate(bool on)
    {
        if (insideRootObject != null) insideRootObject.SetActive(on);
    }

    /// <summary>A copy of LanbaiOverlay.EvOverlayAlpha (bible §1.8 E17): UdonSharp 1.x may not call another U# class's
    /// static method (chief engineer r1).</summary>
    private static float EvOverlayAlpha(float x, float Lfrom, float Lto, float Ls, float Lo)
    {
        float a = Mathf.Max(Lfrom, 0.004f);
        float b = Mathf.Max(Lto, 0.004f);
        float L = a * Mathf.Pow(b / a, Mathf.Clamp01(x));
        float den = Ls - Lo;
        if (Mathf.Abs(den) < 1e-6f) return 1f;
        return Mathf.Clamp01((Ls - L) / den);
    }

    /// <summary>Director v1 grade hook (README_Director §0.5): {dEV, WHITE_SAT, WHITE_BLOOM, desktop lens multiplier}, or
    /// null when this act has no grade event at t. The dispatcher sums every act's events and writes EXPO once.</summary>
    public float[] LanbaiGrade(float t)
    {
        float d = LanbaiDeltaEV(t);
        return d != 0f ? new float[] { d, 0f, 0f, 1f } : null;
    }

    /// <summary>FLASH_TEAR (U12 - 0.75 .. U12): kept for the overlay's fill compensation (WriteBlack) and LanbaiGrade.</summary>
    public float LanbaiDeltaEV(float t)
    {
        float t0 = tU12 - 0.75f;
        if (t < t0) return 0f;
        if (t < t0 + 0.4f) return flashEV * (t - t0) / 0.4f;
        if (t < t0 + 0.5f) return flashEV;
        if (t < tU12) return flashEV * (1f - (t - t0 - 0.5f) / 0.25f);
        return 0f;
    }

    public void LanbaiTick(float t)
    {
        Init();
        float s = Dist(t);
        if (insideRoot != null) insideRoot.localPosition = new Vector3(0f, 0f, -s);
        // the portal: armed from the window's start; the tear plane is lip 1's plane = InsideRoot's origin
        VRCShader.SetGlobalVector(_idPortal, new Vector4(-s, 1f, 0f, 0f));
        if (t < tU9) { _lastT = t; return; }                       // before U9 the gate owns fog, ambient, light

        WriteFog(t, s);
        WriteLipsVisible(s);
        WriteDot(t);
        WriteCabin(t);
        VRCShader.SetGlobalVector(_idClock, new Vector4(Clock(t), 0f, 0f, 0f));
        Color fib = FibreAt(s);
        VRCShader.SetGlobalVector(_idFibre, new Vector4(fib.r, fib.g, fib.b, looseGain));
        if (writeExposure && exposure != null) exposure.SetDeltaEV(LanbaiDeltaEV(t));
        WriteBlack(t);
        _lastT = t;
    }

    // ------------------------------------------------------------------------------------------------ motion
    /// <summary>s(t): metres since U9. One smoothstep v_g -> 12 m/s over U9 .. voice end, closed form
    /// (integral of smoothstep over 0..x = x^3 - x^4 / 2).</summary>
    public float Dist(float t)
    {
        float vg = 2700f / (tU9 - tU6);
        float T = tVoiceEnd - tU9;
        float tau = t - tU9;
        if (tau < 0f) return vg * tau;
        if (tau <= T)
        {
            float x = tau / T;
            return vg * tau + (vEnd - vg) * T * (x * x * x - 0.5f * x * x * x * x);
        }
        return vg * T + (vEnd - vg) * T * 0.5f + vEnd * (tau - T);
    }

    private static float SS(float x)
    {
        x = Mathf.Clamp01(x);
        return x * x * (3f - 2f * x);
    }

    /// <summary>the loose threads' clock: real time, eased to a stop over the 4 s before U12 - 2.25.</summary>
    public float Clock(float t)
    {
        float t0 = dotStop - 4f;
        if (t <= t0) return t;
        float x = Mathf.Clamp01((t - t0) / 4f);
        return t0 + 4f * (x - x * x * x + 0.5f * x * x * x * x);
    }

    // ------------------------------------------------------------------------------------------------ fog
    private Color ZoneAtS(float s)
    {
        if (s <= lipS[0]) return zoneFill[0];
        if (s >= lipS[7]) return zoneFill[7];
        for (int k = 1; k < 8; k++)
        {
            if (s < lipS[k])
            {
                float f = SS((s - lipS[k - 1]) / Mathf.Max(lipS[k] - lipS[k - 1], 1e-3f));
                return Color.Lerp(zoneFill[k - 1], zoneFill[k], f);
            }
        }
        return zoneFill[7];
    }

    private Color FibreAt(float s)
    {
        for (int k = 7; k >= 0; k--)
            if (s >= lipS[k]) return fibreFill[k];
        return fibreFill[0];
    }

    private void WriteFog(float t, float s)
    {
        float dens = fogDensityGate + (fogDensityInside - fogDensityGate) * SS((t - tU9) / 2f);
        Color mid = ZoneAtS(s);
        Color ahead = ZoneAtS(s + fogAheadM);
        Color behind = ZoneAtS(s - fogAheadM);
        float c = SS((t - tSleeveExit) / 4f);                 // the coda: toward the dot, narrower, darker round the edges
        float az = dotAzDeg * Mathf.Deg2Rad;
        Vector3 bd = Vector3.Normalize(new Vector3(Mathf.Sin(az) * c, 0f, Mathf.Cos(az) * c + (1f - c)));
        // r07 (art pre-review r0 #2): the air inside the sleeve is darker (a tunnel in thick cloth), lifting at the exit
        float ks = SS((s - lipS[7]) / 15f) * (1f - SS((s - lipS[7] - sleeveDepth) / 30f));
        float sk = Mathf.Lerp(1f, sleeveFogK, ks);
        float sideK = Mathf.Lerp(behindK, codaSideK, c) * sk;
        float topK = Mathf.Lerp(zenithK, codaTopK, c) * sk, botK = Mathf.Lerp(nadirK, codaTopK, c) * sk;
        float aheadKs = aheadK * sk;
        VRCShader.SetGlobalFloat(_idDensity, dens);
        VRCShader.SetGlobalVector(_idBandDir, new Vector4(bd.x, 0f, bd.z, 1f));
        VRCShader.SetGlobalVector(_idBandColor, new Vector4(ahead.r * aheadKs, ahead.g * aheadKs, ahead.b * aheadKs, 1f));
        VRCShader.SetGlobalFloat(_idBandWidth, Mathf.Lerp(bandWidthDeg, codaBandWidthDeg, c));
        VRCShader.SetGlobalVector(_idHorizon, new Vector4(behind.r * sideK, behind.g * sideK, behind.b * sideK, 2f));      // a = 2: model B
        VRCShader.SetGlobalVector(_idZenith, new Vector4(mid.r * topK, mid.g * topK, mid.b * topK, 1f));
        VRCShader.SetGlobalVector(_idNadir, new Vector4(mid.r * botK, mid.g * botK, mid.b * botK, 1f));
        VRCShader.SetGlobalVector(_idShape, new Vector4(Mathf.Lerp(25f, 8f, c), 90f, 1f, 0f));
        VRCShader.SetGlobalVector(_idBelow, new Vector4(-90f, Mathf.Lerp(-15f, -6f, c), 1f, 0f));
        VRCShader.SetGlobalVector(_idFogInside, new Vector4(mid.r, mid.g, mid.b, dens));
        if (writeRenderSettings)
        {
            RenderSettings.fogColor = mid;          // the average, for built-in shaders (bible §1.6)
            RenderSettings.fogDensity = dens;
        }
    }

    // ------------------------------------------------------------------------------------------------ lips visible
    /// <summary>Bible "<= 3 lips visible at once" (art review r05 #3): the two nearest lips ahead are fully there, the
    /// third fades in (smoothstep) over the run from the last crossing to the next, the rest are fogged out (glow x 0,
    /// the sheet = the dome's fog colour). Crossed lips: 1. Continuous at every crossing. Same as Tools~/inside_drive.lip_visibility.</summary>
    public float LipVisible(int k, float s)
    {
        if (s >= lipS[k - 1]) return 1f;
        int rank = 0;
        int first = -1;
        float prev = 0f;
        for (int i = 0; i < 8; i++)
        {
            if (lipS[i] > s)
            {
                if (first < 0) first = i;
                if (i < k - 1) rank++;
            }
            else prev = Mathf.Max(prev, lipS[i]);
        }
        float v;
        if (rank <= 1) v = 1f;
        else if (rank >= 3) v = 0f;
        else v = SS((s - prev) / Mathf.Max(lipS[first] - prev, 1e-3f));
        // r07 (art review r06 B1): lip 8's ring would sit inside lip 7's hole round the dot (a target): it waits until
        // lip 7 is lip8HoldM away and fades in over lip8RampM
        if (k == 8) v *= SS((s - (lipS[6] - lip8HoldM)) / lip8RampM);
        return v;
    }

    private float[] _lastVis;

    private void WriteLipsVisible(float s)
    {
        if (lipMats == null || lipMatLip == null) return;
        if (_lastVis == null || _lastVis.Length != lipMats.Length)
        {
            _lastVis = new float[lipMats.Length];
            for (int i = 0; i < _lastVis.Length; i++) _lastVis[i] = -1f;
        }
        for (int i = 0; i < lipMats.Length; i++)
        {
            Material m = lipMats[i];
            if (m == null) continue;
            int k = Mathf.Clamp((int)lipMatLip[i], 1, 8);
            float v = LipVisible(k, s);
            if (Mathf.Abs(v - _lastVis[i]) < 0.002f) continue;   // Udon: only the few materials that change this frame
            _lastVis[i] = v;
            m.SetFloat("_Gain", v);          // glow x v; the sheet blends into the dome's fog colour by v (shader)
        }
    }

    // ------------------------------------------------------------------------------------------------ the Lichtchen
    private void WriteDot(float t)
    {
        float tt = Mathf.Min(t, dotStop);
        float g = SmootherStep((tt - dotGrowFrom) / Mathf.Max(dotStop - dotGrowFrom, 1e-3f));
        float core = Mathf.Lerp(dotCoreDeg.x, dotCoreDeg.y, g);
        float glow = Mathf.Lerp(dotGlowDeg.x, dotGlowDeg.y, g);
        float gain = 0f;
        if (t >= dotAppear) gain = Mathf.Pow(2f, -6f * (1f - Mathf.Clamp01((t - dotAppear) / dotAppearDur)));
        VRCShader.SetGlobalVector(_idDot, new Vector4(core, glow, gain, 0f));
        if (dotTransform != null) dotTransform.gameObject.SetActive(gain > 0f && t < tU12);
    }

    private static float SmootherStep(float x)
    {
        x = Mathf.Clamp01(x);
        return x * x * x * (x * (x * 6f - 15f) + 10f);
    }

    // ------------------------------------------------------------------------------------------------ cabin
    private void WriteCabin(float t)
    {
        float w = SS((t - gradeFadeFrom) / gradeFadeDur);
        Color amb = Color.Lerp(cabinAmbientGate, cabinAmbientInside, w);
        if (t >= tU12) amb = cabinAmbientInside * 0f;                // act 5: the afterglow is under the full black
        VRCShader.SetGlobalVector(_idAmbient, new Vector4(amb.r, amb.g, amb.b, 1f));
        if (writeRenderSettings)
        {
            RenderSettings.ambientSkyColor = Color.Lerp(triSkyGate, triSky, w);
            RenderSettings.ambientEquatorColor = Color.Lerp(triEquatorGate, triEquator, w);
            RenderSettings.ambientGroundColor = Color.Lerp(triGroundGate, triGround, w);
        }
        if (writeMainLight && worldMainLight != null) worldMainLight.intensity = Mathf.Lerp(mainLightGate, mainLightInside, w);
        // crossing bands: soft front + exponential tail, front -> back; lip 8 stays, then retreats from the rear
        Vector4 slice = new Vector4(0f, bandSoft, bandTail, 0f);
        Color sc = Color.black;
        for (int k = 0; k < 8; k++)
        {
            float t0 = bandStart[k];
            float dur = bandSweep[k];
            if (k < 7)
            {
                if (t >= t0 && t < t0 + dur + 1.2f)
                {
                    float x = (t - t0) / dur;
                    slice = new Vector4(3.6f - 7.6f * x, bandSoft, bandTail, 0f);
                    sc = bandColour[k];
                }
            }
            else
            {
                float out0 = tSleeveExit - 2.4f;
                if (t >= t0 && t < out0)
                {
                    float x = Mathf.Min((t - t0) / 2.4f, 1f);
                    slice = new Vector4(3.6f - 7.6f * x, bandSoft, bandTail, 1f);
                    sc = bandColour[k];
                }
                else if (t >= out0 && t < tSleeveExit)
                {
                    float x = (t - out0) / 2.4f;
                    slice = new Vector4(-4.0f + 7.6f * x, bandSoft, 0f, -1f);
                    sc = bandColour[k];
                }
            }
        }
        VRCShader.SetGlobalVector(_idSlice, slice);
        VRCShader.SetGlobalVector(_idSliceColor, new Vector4(sc.r, sc.g, sc.b, 1f));
        // the radio dial: 'ein Lichtchen' 3 s brighter, then out with the black mask (act 5, never again)
        float d = Mathf.Clamp01((t - tLichtDial) / 3f);
        Color dial = Color.Lerp(dialBase, dialBright, d);
        float tb = tU12 - 0.25f;
        if (t >= tb) dial *= Mathf.Max(0f, 1f - (t - tb) / 0.25f);
        VRCShader.SetGlobalVector(_idDial, new Vector4(dial.r, dial.g, dial.b, 1f));
    }

    // ------------------------------------------------------------------------------------------------ act 5
    private void WriteBlack(float t)
    {
        if (overlay == null) return;
        float tb = tU12 - 0.25f;
        if (t < tb) return;
        if (t < tU12)
        {
            // EV-linear from the frame (APL ~90 at the flash's end) to #030409; darkening is free (bible §1.8)
            float Ls = 0.2f, Lb = 0.00129f;
            float x = (t - tb) / 0.25f;
            float a = EvOverlayAlpha(x, Ls, Lb, Ls, Lb);
            overlay.SetFlat(blackFillS4c, a, LanbaiDeltaEV(t));
        }
        else if (t < tU12 + 4.0f)
        {
            overlay.SetFlat(blackFillS6, 1f, 0f);       // cut 1: LB_Journey.ApplyGrades hard-cuts S4c -> S6 in the same frame
        }
    }
}
