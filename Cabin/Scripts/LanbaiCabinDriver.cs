// Lanbai / 蓝白 -- LanbaiCabinDriver: the cabin over the whole film (bible v2.1 §4.3 tubes, §4.4 radio dial, §4.5
// curtains, §4.6 glass hooks, §4.8 'the cabin slowly vanishing'; D-02, D-08, D-26, Act04c 181 s glass note).
//
// UdonSharp 1.x. UNCOMPILED (cloud side): Roslyn type-check only (Common/Tools~/compile_check/check_cs.sh, editor +
// player passes, UdonSharp / VRC stubs). Never compiled by the U# compiler, never run in Unity.
// Check in the Class Exposure Tree: VRCShader.SetGlobalFloat / SetGlobalVector / PropertyToID,
// Renderer.GetPropertyBlock / SetPropertyBlock / enabled, MaterialPropertyBlock.SetFloat / SetVector,
// UdonSharpBehaviour.GetProgramVariable, VRCPlayerApi.GetTrackingData.
//
// Every value is a deterministic function of the timeline second t, keyed to the labels below (cues.json + bible
// v2.1 §2.1). Colours are LINEAR (converted from the bible's sRGB hex here) and written with SetGlobalVector, not
// SetGlobalColor (which would gamma-convert a second time in a linear project).
//
// Director interface (CONTROL §5): LanbaiTick(t) every frame inside LanbaiWindow() (= the whole film);
// LanbaiActivate(on) only re-arms the writes (the cabin root is never switched off: it is the frame of every act).
//
// Who else writes what (D-22 'one writer at a time'):
//   _Udon_CabinAmbient, _Udon_RadioDial, _Udon_CabinSlice / Color  : LanbaiInsideDriver owns them in its window
//       [U9 - 2, U12 + 4] = [177.55, 252.64]; this driver does not write them there (yieldToInside). Without the
//       inside package (yieldToInside = false) this driver writes the bible §4.8 / §4.4 fallback values itself.
//   Tube flicker in act 4: LB_Journey.ApplyLamps plays FlickerTable (bible §1.8) on the tube lights and renderers.
//       This driver READS its result (LB_Journey's private _l0 / _l1 / _l2 via GetProgramVariable) from U6 to U9 + 0.45
//       and writes their mean as _Udon_CabinLightmap. It does not keep a second copy of the table.
//   PPv2 / exposure: LB_Journey.ApplyGrades only (Director README §0.5). This driver reports no grade event.
//   Lights: this driver creates and drives no light (D-24: the one shadowed light is RenderSettings.sun =
//       Gate_Lights/Moon; D-00: any Inspector value is E).

using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiCabinDriver : UdonSharpBehaviour
{
    // ------------------------------------------------------------------------------------------------ cue labels
    // Copied from FromLocal/cues.json ("t" fields) and, for the v2.1 sub-labels cues.json does not have yet
    // (U4h, F8b, F10e, F10l ...), from Art/ART_BIBLE.md v2.1 §2.1 (which reads them from cues.md / the waveform).
    // If cues.json changes, change these (or let the build script fill them from cues.json).
    [Header("Cues  timeline seconds  cues.json and bible 2.1")]
    public float tU1 = 17.50f;      // cues.json U.U1: the bus slides off
    public float tU3 = 50.30f;      // cues.json U.U3: Der Mensch liegt in groesster Not (the sound opens)
    public float tU4h = 99.50f;     // bible 2.1: second Himmel high note, touching the cloud
    public float tU5 = 107.50f;     // cues.json U.U5
    public float tU6k = 129.10f;    // cues.json U_sub.U6k: breaking out of the cloud, the moon
    public float tU6 = 133.80f;     // cues.json U.U6
    public float tU9 = 179.55f;     // cues.json U.U9: in; tubes flash and die
    public float tU12 = 248.64f;    // cues.json U.U12: FLASH_TEAR done -> black (cut 1)
    public float tLicht = 196.10f;  // bible 4.4: 'ein Lichtchen' (inside LIP4 193.90)
    public float tF0 = 251.64f;     // cues.json F.F0
    public float tF1 = 281.86f;     // cues.json F.F1
    public float tF2h = 363.26f;    // cues.json F_sub.F2h: into the water
    public float tF3e = 474.36f;    // bible 2.1: starting to sink, S7a -> S7b
    public float tF3e3 = 556.36f;   // bible 2.1: the last blue goes out
    public float tF5 = 644.96f;     // cues.json F.F5
    public float tF8b = 877.96f;    // bible 2.1: Hoer auf zu beben (D-26 hole opens)
    public float tF8bSettle = 897.96f; // Act07a §9: the window under the floor has settled (APL 30)
    public float tF9s = 921.86f;    // bible 2.1: the swell; out of the sea = F9s + 0.5
    public float tF10 = 942.26f;    // cues.json F.F10: Mit Fluegeln (wings)
    public float tF10e = 956.36f;   // bible 2.1: werd ich entschweben (release)
    public float tF10l = 961.06f;   // bible 2.1: zum Licht (dissolve, 8 s)
    public float tRise = 962.26f;   // bible 6.8: steady rise begins (erosion 0.65 reached)
    public float tF12 = 987.06f;    // cues.json F.F12
    public float tDark9 = 1009.21f; // bible 6.8b: the first 8 s of act 9 (darkening) end
    public float tF16 = 1149.31f;   // cues.json F.F16: the 13th mirror, white (cut 2)
    public float tAct11 = 1178.46f; // bible 6.11: false awakening, the cabin snaps back under the white
    public float tRadioOff = 1238.46f; // bible 4.4: act 11 + 60 s, the radio clicks off
    public float tAct12 = 1251.96f; // bible 6.11 -> 12: the second white is full, act 12
    // cues.json derived.mirror_crossings_snapped_t, mirrors 1..12 (each +0.027 erosion over 1.2 s)
    public float[] mirrorT = new float[] { 1032.41f, 1034.91f, 1037.98f, 1041.74f, 1045.82f, 1052.30f,
                                           1058.95f, 1067.46f, 1077.21f, 1089.91f, 1106.41f, 1125.55f };

    [Header("Ownership")]
    public bool yieldToInside = true;          // LanbaiInsideDriver writes ambient / dial / slice in its window
    public float insideFrom = 177.55f;         // = LanbaiInsideDriver.LanbaiWindow()[0] (U9 - 2)
    public float insideTo = 252.64f;           // = [1] (U12 + 4)
    public UdonSharpBehaviour journey;         // LB_Journey (tube flicker hook); null = no flicker, base curve only

    [Header("Renderers")]
    public Renderer[] cabinRenderers;          // Cabin_Static, Cabin_Tubes, Cabin_Radio, Cabin_DestBlind (Lanbai/Cabin)
    public Renderer[] curtainRenderers;        // Cabin_Curtains (Lanbai/ThinCloth)
    public Renderer[] glassRenderers;          // every Lanbai/BusGlass pane: windows, roof-slope windows, windscreen, skylight, door

    [Header("Seats  local seat sphere 0.9 m")]
    public Vector3 heroSeat = new Vector3(0.55f, 1.05f, 2.05f);   // Bus/Source/bus_spec.py: eye (0.55, 1.70, 2.05)
    public Vector3[] seatCentres;              // every seat cushion centre (world); empty = hero seat for everyone
    public float seatRadius = 0.9f;

    [Header("Door  closed only in act 11  under the white")]
    public Transform[] doorPanels;             // Bus_Door0..3 (FBX = open state; origin = hinge)
    public Vector3[] doorClosedPos;            // BusLayout.json door_panels[k].closed.position (bus frame = world)
    public float[] doorClosedYaw;              // closed.yaw_deg, about the panel's own +Y

    [Header("Glass")]
    public float reflGainNight = 1.0f;         // BusGlass _CabinReflGain (Rain README 5.2: night 1, day 0.25)
    public float reflGainDay = 0.25f;
    // BusGlass does not clip on the erosion field: each pane is switched off when _Udon_CabinFade passes the erosion
    // threshold at its centre (same tau as LanbaiCabinCommon.cginc, _ErodeForm 0 / D-32, default coefficients) plus
    // the median of the noise range, i.e. when about half its frame has gone. Numbers from bus_spec.py.
    public float glassErodeMedian = 0.025f;    // mid of _ErodeNoiseRange (-0.20, 0.25)
    public float glassFadeSeconds = 1.5f;
    [Header("D-33 #7a door group")]
    public float doorGoneFrom = 957.40f;       // the door group starts to go (F10e + 1 s)
    public float doorGoneBy = 965.40f;         // ... and is gone (the zenith gone; Zhuangzi from 971.4)      // D-32 #8: each pane fades out over this, no broken edge

    // ------------------------------------------------------------------------------------------------ state
    private int _idLightmap, _idAmbient, _idBleach, _idFade, _idDial, _idSlice, _idSliceColor;
    private int _idSeat, _idHole, _idClock, _idSway, _idFloat, _idWing, _idRelease, _idDissolve, _idReflGain;
    private MaterialPropertyBlock _mpb;
    private bool _ready;
    private float _lm = -1f, _bleach = -1f, _fade = -1f, _hole = -1f, _refl = -1f, _door = -1f;
    private Vector4 _amb = new Vector4(-1f, 0f, 0f, 0f), _dial = new Vector4(-1f, 0f, 0f, 0f), _seat;
    private int _glassOn = -1;
    private float[] _paneFadeAt;               // per pane: fade at which it goes (computed once from its bounds)
    private float[] _paneZen;                  // per pane: D-46 zenith term at its centre (before the fade ramp)
    private float[] _paneT;                    // per pane: timeline second the fade passes it (1e9 = never)
    private float[] _paneBase;                 // per pane: material _TintStrength, _BaseAlpha, _DropOpacity, (spare)
    private bool _paneFading;
    private int _idTintStrength, _idBaseAlpha, _idDropOpacity, _idDoorBias;
    private int _panesGone = -1;               // how many panes are off for erosion (re-write when it changes)
    private int _clothVisible = -1;
    private float _nextSeatCheck;
    private Vector3[] _doorOpenPos;
    private Quaternion[] _doorOpenRot;
    private int _doorClosed = -1;

    // linear colours (bible sRGB hex -> linear x the bible's factor), filled in Init()
    private Vector4 _ambMoon, _ambInside, _ambDawn, _ambSeaShallow, _ambSeaDeep, _ambDusk, _ambNight9;
    private Vector4 _dialBase, _dialBright;

    // ------------------------------------------------------------------------------------------------ Udon events
    void Start()
    {
        Init();
        WriteAll(0f, true);      // CONTROL §6 pitfall 9: editor-written globals / MPB are gone in Play; write them here
    }

    private void Init()
    {
        if (_ready) return;
        _mpb = new MaterialPropertyBlock();
        _idLightmap = VRCShader.PropertyToID("_Udon_CabinLightmap");
        _idAmbient = VRCShader.PropertyToID("_Udon_CabinAmbient");
        _idBleach = VRCShader.PropertyToID("_Udon_CabinBleach");
        _idFade = VRCShader.PropertyToID("_Udon_CabinFade");
        _idDial = VRCShader.PropertyToID("_Udon_RadioDial");
        _idSlice = VRCShader.PropertyToID("_Udon_CabinSlice");
        _idSliceColor = VRCShader.PropertyToID("_Udon_CabinSliceColor");
        _idSeat = VRCShader.PropertyToID("_SeatSphere");          // material properties (MPB), not globals
        _idHole = VRCShader.PropertyToID("_HoleOpen");
        _idDoorBias = VRCShader.PropertyToID("_DoorBias");
        _idClock = VRCShader.PropertyToID("_ClothClock");
        _idSway = VRCShader.PropertyToID("_Sway");
        _idFloat = VRCShader.PropertyToID("_Float");
        _idWing = VRCShader.PropertyToID("_Wing");
        _idRelease = VRCShader.PropertyToID("_Release");
        _idDissolve = VRCShader.PropertyToID("_Dissolve");
        _idReflGain = VRCShader.PropertyToID("_CabinReflGain");
        _idTintStrength = VRCShader.PropertyToID("_TintStrength");
        _idBaseAlpha = VRCShader.PropertyToID("_BaseAlpha");
        _idDropOpacity = VRCShader.PropertyToID("_DropOpacity");

        _ambMoon = Lin(0x23, 0x2A, 0x3A, 0.30f);       // bible 4.8 act 4: moon #232A3A x 0.3
        _ambInside = Lin(0xB5, 0xC3, 0xDB, 0.30f);     // 4c: #B5C3DB x 0.30 (fallback only; the inside driver owns it)
        _ambDawn = Lin(0x98, 0xA4, 0xB8, 0.50f);       // 6: #98A4B8 x 0.5
        _ambSeaShallow = Lin(0x61, 0x86, 0xA7, 0.60f); // 7a shallow #6186A7 x 0.6
        _ambSeaDeep = Lin(0x0F, 0x1E, 0x30, 0.30f);    // deep #0F1E30 x 0.3 (also 7c)
        _ambDusk = Lin(0x82, 0x8B, 0xAA, 0.45f);       // 8: #828BAA x 0.45
        _ambNight9 = Lin(0x23, 0x2A, 0x3A, 0.30f);     // 9: #232A3A x 0.3
        _dialBase = Lin(0xFF, 0x77, 0x03, Mathf.Pow(2f, 0.71f));   // bible 4.4 act 2: fill #FF7703 @ +0.71
        _dialBright = Lin(0xFF, 0x7B, 0x00, Mathf.Pow(2f, 2.13f)); // 4c after ein Lichtchen: fill #FF7B00 @ +2.13
        _seat = new Vector4(heroSeat.x, heroSeat.y, heroSeat.z, seatRadius);
        int nd = doorPanels == null ? 0 : doorPanels.Length;
        _doorOpenPos = new Vector3[nd];
        _doorOpenRot = new Quaternion[nd];
        for (int i = 0; i < nd; i++)
            if (doorPanels[i] != null) { _doorOpenPos[i] = doorPanels[i].localPosition; _doorOpenRot[i] = doorPanels[i].localRotation; }
        _ready = true;
    }

    // ------------------------------------------------------------------------------------------------ interface
    public float[] LanbaiWindow()
    {
        return new float[] { -600f, 1400f };     // the whole film: the cabin is the frame of every act
    }

    public void LanbaiActivate(bool on)
    {
        Init();
        // the cabin root is never switched; entering the window (or a seek) re-writes everything once
        _lm = -1f; _bleach = -1f; _fade = -1f; _hole = -1f; _refl = -1f; _door = -1f; _glassOn = -1; _clothVisible = -1; _panesGone = -1;
        _amb.x = -1f; _dial.x = -1f; _doorClosed = -1;
    }

    public void LanbaiTick(float t)
    {
        Init();
        WriteAll(t, false);
    }

    // ------------------------------------------------------------------------------------------------ the curves
    private void WriteAll(float t, bool force)
    {
        bool insideOwns = yieldToInside && t >= insideFrom && t < insideTo;

        float lm = Tubes(t);
        if (force || Mathf.Abs(lm - _lm) > 1e-4f) { _lm = lm; VRCShader.SetGlobalFloat(_idLightmap, lm); }

        float b = Bleach(t);
        if (force || Mathf.Abs(b - _bleach) > 1e-4f) { _bleach = b; VRCShader.SetGlobalVector(_idBleach, new Vector4(b, 0f, 0f, 1f)); }

        float f = Fade(t);
        if (force || Mathf.Abs(f - _fade) > 1e-4f) { _fade = f; VRCShader.SetGlobalVector(_idFade, new Vector4(f, 0f, 0f, 1f)); }

        if (!insideOwns)
        {
            Vector4 a = Ambient(t);
            if (force || (a - _amb).sqrMagnitude > 1e-9f) { _amb = a; VRCShader.SetGlobalVector(_idAmbient, a); }
            Vector4 d = Dial(t);
            if (force || (d - _dial).sqrMagnitude > 1e-9f) { _dial = d; VRCShader.SetGlobalVector(_idDial, d); }
            if (force)
            {   // nobody else writes the bands outside the inside window: start clean
                VRCShader.SetGlobalVector(_idSlice, new Vector4(0f, 1.5f, 3f, 0f));
                VRCShader.SetGlobalVector(_idSliceColor, Vector4.zero);
            }
        }
        else
        {
            _amb.x = -1f; _dial.x = -1f;          // re-write when the inside driver hands back
        }

        // per-client seat sphere (1 Hz), D-26 hole -> MPB on the cabin and curtain renderers
        bool seatChanged = UpdateSeat(t, force);
        float h = Hole(t);
        float db = DoorBias(t);
        if (force || seatChanged || Mathf.Abs(h - _hole) > 1e-4f || Mathf.Abs(db - _door) > 1e-4f)
        {
            _hole = h; _door = db;
            WriteCabinMPB(cabinRenderers);
        }
        WriteCloth(t, force || seatChanged);
        WriteGlass(t, force);
        WriteDoor(t, force);
    }

    // bible §3 / D-28d: the door is never closed, except in act 11 (closed under the white at 1178.46, open again
    // under the second white before act 12). Poses from BusLayout.json door_panels.
    private void WriteDoor(float t, bool force)
    {
        if (doorPanels == null || _doorOpenPos == null) return;
        int closed = (t >= tAct11 && t < tAct12) ? 1 : 0;
        if (!force && closed == _doorClosed) return;
        _doorClosed = closed;
        for (int i = 0; i < doorPanels.Length && i < _doorOpenPos.Length; i++)
        {
            Transform d = doorPanels[i];
            if (d == null) continue;
            bool haveClosed = doorClosedPos != null && doorClosedYaw != null && i < doorClosedPos.Length && i < doorClosedYaw.Length;
            if (closed == 1 && haveClosed)
            {
                d.localPosition = doorClosedPos[i];
                d.localRotation = _doorOpenRot[i] * Quaternion.Euler(0f, doorClosedYaw[i], 0f);
            }
            else
            {
                d.localPosition = _doorOpenPos[i];
                d.localRotation = _doorOpenRot[i];
            }
        }
    }

    /// <summary>bible 4.3 / 4.8 'tubes' column, 1 = full (seat cushion E 0.8).</summary>
    private float Tubes(float t)
    {
        if (t < tU4h) return 1f;
        if (t < tU5) return Mathf.Pow(2f, -(t - tU4h) / (tU5 - tU4h));          // U4h -> U5: 1 -> 0.5 (EV linear)
        if (t < tU6) return 0.5f;
        if (t < tU9)
        {
            float j = JourneyTubes();
            if (j >= 0f) return j;                                              // FlickerTable owns the value here
            return Mathf.Lerp(0.5f, 0.3125f, SS((t - tU6) / 30f));              // U6 + 30 s: seat E 0.4 -> 0.25
        }
        if (t < tU9 + 0.2f) return 0.3125f * 1.5f;                              // the 150 % flash, 0.2 s
        if (t < tU9 + 0.45f) return 0.3125f * 1.5f * (1f - (t - tU9 - 0.2f) / 0.25f);   // 0.25 s to 0
        if (t < tAct11) return 0f;
        return 1f;                                                              // acts 11, 12: steady
    }

    // LB_Journey's per-tube levels (front / middle / rear groups) after FlickerTable; mean -> the one LM float.
    private float JourneyTubes()
    {
        if (journey == null) return -1f;
        object o0 = journey.GetProgramVariable("_l0");
        object o1 = journey.GetProgramVariable("_l1");
        object o2 = journey.GetProgramVariable("_l2");
        if (o0 == null || o1 == null || o2 == null) return -1f;
        float l = ((float)o0 + (float)o1 + (float)o2) / 3f;
        return l < 0f ? -1f : l;                                                // LB_Journey starts them at -1 (unset)
    }

    private float MirrorSteps(float t)
    {
        float s = 0f;
        if (mirrorT == null) return s;
        for (int i = 0; i < mirrorT.Length; i++) s += SS((t - mirrorT[i]) / 1.2f);
        return s;
    }

    /// <summary>bible 4.8 'bleach' column.</summary>
    private float Bleach(float t)
    {
        if (t >= tAct11 || t < tF0) return 0f;
        if (t < tF1) return 0.10f * (t - tF0) / (tF1 - tF0);
        if (t < tF2h) return 0.10f;
        if (t < tF5) return 0.10f + 0.15f * (t - tF2h) / (tF5 - tF2h);
        float exitT = tF9s + 0.5f;
        if (t < exitT) return 0.25f;
        if (t < tRise) return 0.25f + 0.25f * SS((t - exitT) / (tRise - exitT));
        float b = 0.5f + 0.3f * MirrorSteps(t) / 12f;                           // act 9: 0.5 -> 0.8 with the mirrors
        return b + (1f - b) * SS((t - tF16) / 1.2f);                            // the 13th: -> 1
    }

    /// <summary>bible 4.8 'erosion' column. F2h -> F5 is front-loaded (sqrt) so the hole at the skylight's edge is
    /// open by ~387 s (Snell's window through the hole, bible 4.8 / Act07a §4).</summary>
    private float Fade(float t)
    {
        if (t >= tAct11 || t < tF2h) return 0f;
        if (t < tF5) return 0.25f * Mathf.Sqrt((t - tF2h) / (tF5 - tF2h));
        float exitT = tF9s + 0.5f;
        if (t < exitT) return 0.25f;
        if (t < tRise) return 0.25f + 0.40f * SS((t - exitT) / (tRise - exitT));
        float f = 0.65f + 0.027f * MirrorSteps(t);                              // mirrors 1-12, 1.2 s each
        return f + (1f - f) * SS((t - tF16) / 1.2f);                            // the 13th takes your seat
    }

    /// <summary>D-33 #7a: the door group erodes away between doorGoneFrom and doorGoneBy (965.4, the zenith gone,
    /// before Zhuangzi at 971.4). 0 again from act 11 (the fade is 0 there anyway: the bus is whole at the stop).</summary>
    private float DoorBias(float t)
    {
        if (t < doorGoneFrom || t >= tAct11) return 0f;
        return SS((t - doorGoneFrom) / Mathf.Max(doorGoneBy - doorGoneFrom, 0.1f));
    }

    /// <summary>D-26 (Act07a §9.1): 0 shut, 0.5 the minimum hole (F8b + 6 s, the waves calm), 1 the full hole
    /// (897.96, the window settles). Held to the false awakening.</summary>
    private float Hole(float t)
    {
        if (t < tF8b || t >= tAct11) return 0f;
        if (t < tF8b + 6f) return 0.5f * SS((t - tF8b) / 6f);
        return 0.5f + 0.5f * SS((t - tF8b - 6f) / Mathf.Max(tF8bSettle - tF8b - 6f, 0.1f));
    }

    /// <summary>bible 4.8 'ambient' column (linear rgb x factor). Acts 1-3, 11, 12: 0 (the tubes light the cabin).</summary>
    private Vector4 Ambient(float t)
    {
        if (t < tU6k || t >= tAct11) return Vector4.zero;
        if (t < insideFrom) return _ambMoon * SS((t - tU6k) / 4f);
        if (t < insideTo)
        {   // fallback without the inside package: the gate's moon -> #B5C3DB x 0.30 over U9 + 3 s, 0 under the black
            if (t >= tU12) return Vector4.zero;
            return LerpEV(_ambMoon, _ambInside, SS((t - tU9) / 3f));
        }
        if (t < tF2h) return _ambDawn;
        if (t < tF3e) return LerpEV(_ambDawn, _ambSeaShallow, SS((t - tF2h) / 1.5f));
        if (t < tF9s) return LerpEV(_ambSeaShallow, _ambSeaDeep, Mathf.Clamp01((t - tF3e) / (tF3e3 - tF3e)));
        if (t < tF12) return LerpEV(_ambSeaDeep, _ambDusk, Mathf.Clamp01((t - tF9s) / 1.5f));   // the water line
        return LerpEV(_ambDusk, _ambNight9, Mathf.Clamp01((t - tF12) / (tDark9 - tF12)));
    }

    /// <summary>bible 4.4 + D-02. Flicker = sums of sines <= 2 Hz (deterministic in t: every client the same).</summary>
    private Vector4 Dial(float t)
    {
        if (t < 0f) return Vector4.zero;                                        // before departure: off (see README)
        if (t >= tAct11)
        {
            if (t >= tRadioOff) return Vector4.zero;                            // clicks off by itself
            return _dialBase * (1f + 0.10f * Noise(t));                         // act 11: noise only
        }
        if (t >= insideTo || (t >= tU12 && !yieldToInside)) return Vector4.zero;   // never again after the flash
        float g;
        if (t < 3f) g = 1f + 0.10f * Noise(t);                                  // tuning noise
        else g = 1f + 0.09f * Signal(t);                                        // the signal breathing
        float x = t - tU3;                                                      // U3: 1.5 -> 3 'HDR' and back
        if (x > 0f && x < 12f) g *= 1f + (x < 6f ? SS(x / 6f) : 1f - SS((x - 6f) / 6f));
        Vector4 c = _dialBase * g;
        if (t >= insideFrom)
        {   // fallback without the inside package: ein Lichtchen +1 stop in 3 s, D-02: down with the black mask
            c = Vector4.Lerp(c, _dialBright, Mathf.Clamp01((t - tLicht) / 3f));
            float tb = tU12 - 0.25f;
            if (t >= tb) c *= Mathf.Max(0f, 1f - (t - tb) / 0.25f);
        }
        return c;
    }

    private static float Noise(float t)
    {
        return 0.6f * Mathf.Sin(6.2832f * 1.7f * t) + 0.4f * Mathf.Sin(6.2832f * 0.9f * t + 1.3f);
    }

    private static float Signal(float t)
    {
        return 0.5f * Mathf.Sin(6.2832f * 0.37f * t + 0.4f) + 0.3f * Mathf.Sin(6.2832f * 0.91f * t + 2.1f)
             + 0.2f * Mathf.Sin(6.2832f * 1.6f * t + 0.7f);
    }

    // ------------------------------------------------------------------------------------------------ curtains
    private void WriteCloth(float t, bool force)
    {
        if (curtainRenderers == null || curtainRenderers.Length == 0) return;
        float sway = 0f, swayHz = 0.8f, fl = 0f, wing = 0f, wingHz = 0.3f, rel = 0f, dis = 0f;
        float exitT = tF9s + 0.5f;
        if (t >= tAct11)
        {
            if (t < tAct12) { sway = 0.015f; swayHz = 0.8f; }                  // act 11: the same road as act 2
        }
        else if (t >= tF10)
        {
            float k = SS((t - tF10) / (tF10e - tF10));
            wing = Mathf.Lerp(0.30f, 0.60f, k); wingHz = Mathf.Lerp(0.3f, 0.5f, k);
            sway = 0.04f * (1f - SS((t - tF10) / 3f)); swayHz = 0.5f;
            if (t >= tF10e) rel = t - tF10e;                                    // let go: straight up past the roof line, then a turn toward the sun (ThinCloth, D-32 #9)
            dis = Mathf.Clamp01((t - tF10l) / 8f);                              // into the light by F10l + 8 s
        }
        else if (t >= exitT)
        {
            float k = SS((t - exitT) / 3f);
            fl = 0.15f * (1f - k); sway = Mathf.Lerp(0.01f, 0.04f, k); swayHz = Mathf.Lerp(0.2f, 0.5f, k);
        }
        else if (t >= tF2h)
        {
            float k = SS((t - tF2h) / 4f);
            fl = 0.15f * k; sway = Mathf.Lerp(0.04f, 0.01f, k); swayHz = Mathf.Lerp(0.6f, 0.2f, k);   // 10-20 cm / 0.2 Hz
        }
        else if (t >= tU3)
        {
            float k = SS((t - tU3) / 4f);
            sway = Mathf.Lerp(0.015f, 0.04f, k); swayHz = Mathf.Lerp(0.8f, 0.6f, k);                  // lift-off 4 cm
        }
        else if (t >= tU1)
        {
            sway = 0.015f * SS((t - tU1) / 12f); swayHz = 0.8f;                // night road 1-2 cm / 0.8 Hz
        }

        int visible = dis < 1f ? 1 : 0;
        if (visible != _clothVisible)
        {
            _clothVisible = visible;
            for (int i = 0; i < curtainRenderers.Length; i++)
                if (curtainRenderers[i] != null) curtainRenderers[i].enabled = visible == 1;
        }
        bool moving = sway > 0f || fl > 0f || wing > 0f || rel > 0f || dis > 0f;
        if (!moving && !force) return;                                          // still: nothing changes per frame
        for (int i = 0; i < curtainRenderers.Length; i++)
        {
            Renderer r = curtainRenderers[i];
            if (r == null) continue;
            r.GetPropertyBlock(_mpb);
            _mpb.SetFloat(_idClock, t);
            _mpb.SetVector(_idSway, new Vector4(sway, swayHz, 0f, 0f));
            _mpb.SetVector(_idFloat, new Vector4(fl, 0.2f, 0f, 0f));
            _mpb.SetVector(_idWing, new Vector4(wing, wingHz, 0f, 0f));
            _mpb.SetVector(_idRelease, new Vector4(rel, 1.2f, 6f, 0f));
            _mpb.SetFloat(_idDissolve, dis);
            _mpb.SetVector(_idSeat, _seat);
            _mpb.SetFloat(_idHole, _hole);
            _mpb.SetFloat(_idDoorBias, _door);
            r.SetPropertyBlock(_mpb);
        }
    }

    // ------------------------------------------------------------------------------------------------ glass
    private void WriteGlass(float t, bool force)
    {
        if (glassRenderers == null) return;
        // bible 6.5 / 6.10: under the full black (U12 -> F0) and the full white (F16 -> act 11) the glass is off
        int on = ((t >= tU12 && t < tF0) || (t >= tF16 && t < tAct11)) ? 0 : 1;
        // Act04c 给总控 (181 s): no glass may show the lip behind the bus -> the cabin reflection gain is 0 over the
        // inside window. (BusGlass's inside reflection is cube x _Udon_CabinLightmap x gain and the tubes are 0 from
        // U9 anyway; this is the belt to that brace, and it also covers the roof-slope windows, D-28 #5.)
        float g = (t >= insideFrom && t < tU12) ? 0f : ((t >= tF0 && t < tDark9) ? reflGainDay : reflGainNight);
        if (_paneFadeAt == null || _paneFadeAt.Length != glassRenderers.Length) PaneThresholds();
        // D-32 #8: a pane fades out over glassFadeSeconds (tint, base alpha, drops and reflection together) from the
        // moment the fade passes its threshold. The moment is a function of t (bisection on the monotonic Fade curve,
        // done once), so a seek / late join rebuilds the same state (D-33 #6).
        int gone = 0;
        for (int i = 0; i < _paneT.Length; i++) if (PaneK(i, t) <= 0f) gone++;
        if (force || on != _glassOn || gone != _panesGone)
        {
            _glassOn = on; _panesGone = gone;
            for (int i = 0; i < glassRenderers.Length; i++)
                if (glassRenderers[i] != null) glassRenderers[i].enabled = on == 1 && PaneK(i, t) > 0f;
        }
        bool fading = false;
        for (int i = 0; i < _paneT.Length; i++) { float k = PaneK(i, t); if (k > 0f && k < 1f) fading = true; }
        if (force || fading || _paneFading || Mathf.Abs(g - _refl) > 1e-4f)
        {
            _refl = g; _paneFading = fading;
            for (int i = 0; i < glassRenderers.Length; i++)
            {
                Renderer r = glassRenderers[i];
                if (r == null) continue;
                float k = PaneK(i, t);
                r.GetPropertyBlock(_mpb);
                _mpb.SetFloat(_idReflGain, g * k);
                _mpb.SetFloat(_idTintStrength, _paneBase[4 * i] * k);
                _mpb.SetFloat(_idBaseAlpha, _paneBase[4 * i + 1] * k);
                _mpb.SetFloat(_idDropOpacity, _paneBase[4 * i + 2] * k);
                r.SetPropertyBlock(_mpb);
            }
        }
    }

    // 1 = the pane is whole, 0 = gone; linear over glassFadeSeconds after its crossing time
    private float PaneK(int i, float t)
    {
        float t0 = _paneT[i];
        if (t < t0 || t >= tAct11) return 1f;
        return 1f - Mathf.Clamp01((t - t0) / Mathf.Max(glassFadeSeconds, 0.01f));
    }

    // D-46 zenith term (= LanbaiZenithTerm with the Lanbai/Cabin defaults _ErodeZenith (0.55, 1.95, 2.50, 0.50),
    // _ErodeZenithShape (0.15, 2.0, 2.40, 2.50)), without the fade ramp
    private float PaneZen(Vector3 p)
    {
        float dx = (p.x - 0.55f) / 2.0f;
        float dz = Mathf.Max(Mathf.Max(1.95f - p.z, p.z - 2.50f), 0f);
        float u = Mathf.Clamp01((p.y - 2.40f) / 0.10f);
        return 0.50f * Mathf.Exp(-Mathf.Sqrt(dx * dx + dz * dz) / 0.15f) * u * u * (3f - 2f * u);
    }

    // the pane's tau at fade f, plus its threshold: fade + zenith x ramp (_ErodeZenithRamp 0.050 -> 0.075)
    private float PaneTau(int i, float f)
    {
        return f + _paneZen[i] * Mathf.Clamp01((f - 0.050f) / 0.025f);
    }

    // tau(P) = fade - 0.45 (1 - hN) - 0.25 (1 - fN) - 0.35 (1 - exp(-d_sky / 0.8)) (+ D-46 zenith term); the pane goes
    // when tau > median
    private void PaneThresholds()
    {
        _paneFadeAt = new float[glassRenderers.Length];
        _paneZen = new float[glassRenderers.Length];
        for (int i = 0; i < glassRenderers.Length; i++)
        {
            Renderer r = glassRenderers[i];
            if (r == null) { _paneFadeAt[i] = 9f; continue; }
            Vector3 p = r.bounds.center;
            float hN = Mathf.Clamp01((p.y - 0.62f) / 2.00f);              // _CabinBox x 0.62, y 2.62
            float fN = Mathf.Clamp01((p.z + 3.65f) / 7.15f);              // z -3.65 .. 3.50
            float qx = Mathf.Max(Mathf.Abs(p.x - 0.55f) - 0.30f, 0f), qz = Mathf.Max(Mathf.Abs(p.z - 2.80f) - 0.30f, 0f);
            float dSky = Mathf.Sqrt(qx * qx + qz * qz + (p.y - 2.62f) * (p.y - 2.62f));
            float e = Mathf.Exp(-dSky / 0.8f);
            _paneFadeAt[i] = glassErodeMedian + 0.45f * (1f - hN) + 0.25f * (1f - fN) + 0.35f * (1f - e);
            _paneZen[i] = PaneZen(p);
        }
        // the time each threshold is crossed: Fade is 0 before F2h, non-decreasing to act 11 (then 0 again)
        _paneT = new float[glassRenderers.Length];
        _paneBase = new float[4 * glassRenderers.Length];
        for (int i = 0; i < glassRenderers.Length; i++)
        {
            float thr = _paneFadeAt[i];
            float lo = tF2h, hi = tAct11 - 0.001f;
            if (PaneTau(i, Fade(hi)) < thr) { _paneT[i] = 1e9f; }
            else
            {
                for (int it = 0; it < 30; it++) { float m = 0.5f * (lo + hi); if (PaneTau(i, Fade(m)) >= thr) hi = m; else lo = m; }
                _paneT[i] = hi;
            }
            // D-33 #7a: a pane in the door box (the folding leaves' glass) goes with the door group, at half its bias
            Renderer rb = glassRenderers[i];
            if (rb != null)
            {
                Vector3 c = rb.bounds.center;
                if (c.x > 0.80f && c.x < 1.60f && c.y > 0.45f && c.y < 3.00f && c.z > 2.38f && c.z < 3.45f)
                    _paneT[i] = Mathf.Min(_paneT[i], doorGoneFrom + 0.5f * (doorGoneBy - doorGoneFrom));
            }
            Renderer r = glassRenderers[i];
            Material m0 = r != null ? r.sharedMaterial : null;
            _paneBase[4 * i] = m0 != null ? m0.GetFloat(_idTintStrength) : 1f;
            _paneBase[4 * i + 1] = m0 != null ? m0.GetFloat(_idBaseAlpha) : 0.06f;
            _paneBase[4 * i + 2] = m0 != null ? m0.GetFloat(_idDropOpacity) : 0.92f;
        }
    }

    // ------------------------------------------------------------------------------------------------ seat / MPB
    private bool UpdateSeat(float t, bool force)
    {
        if (!force && Time.time < _nextSeatCheck) return false;
        _nextSeatCheck = Time.time + 1f;
        Vector3 c = heroSeat;
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (seatCentres != null && seatCentres.Length > 0 && lp != null)
        {
            Vector3 head = lp.GetTrackingData(VRCPlayerApi.TrackingDataType.Head).position;
            float best = 1e9f;
            for (int i = 0; i < seatCentres.Length; i++)
            {
                Vector3 s = seatCentres[i];
                float dx = s.x - head.x, dz = s.z - head.z;
                float d = dx * dx + dz * dz;
                if (d < best) { best = d; c = s; }
            }
        }
        Vector4 v = new Vector4(c.x, c.y, c.z, seatRadius);
        if (!force && (v - _seat).sqrMagnitude < 1e-6f) return false;
        _seat = v;
        return true;
    }

    private void WriteCabinMPB(Renderer[] rs)
    {
        if (rs == null) return;
        for (int i = 0; i < rs.Length; i++)
        {
            Renderer r = rs[i];
            if (r == null) continue;
            r.GetPropertyBlock(_mpb);
            _mpb.SetVector(_idSeat, _seat);
            _mpb.SetFloat(_idHole, _hole);
            _mpb.SetFloat(_idDoorBias, _door);
            r.SetPropertyBlock(_mpb);
        }
    }

    // ------------------------------------------------------------------------------------------------ helpers
    private static float SS(float x)
    {
        x = Mathf.Clamp01(x);
        return x * x * (3f - 2f * x);
    }

    private static float SrgbToLin(int c)
    {
        float v = c / 255f;
        return v <= 0.04045f ? v / 12.92f : Mathf.Pow((v + 0.055f) / 1.055f, 2.4f);
    }

    private static Vector4 Lin(int r, int g, int b, float k)
    {
        return new Vector4(SrgbToLin(r) * k, SrgbToLin(g) * k, SrgbToLin(b) * k, 1f);
    }

    // per-channel lerp in log space (EV-linear), alpha 1
    private static Vector4 LerpEV(Vector4 a, Vector4 b, float x)
    {
        x = Mathf.Clamp01(x);
        return new Vector4(
            Mathf.Exp(Mathf.Lerp(Mathf.Log(Mathf.Max(a.x, 1e-5f)), Mathf.Log(Mathf.Max(b.x, 1e-5f)), x)),
            Mathf.Exp(Mathf.Lerp(Mathf.Log(Mathf.Max(a.y, 1e-5f)), Mathf.Log(Mathf.Max(b.y, 1e-5f)), x)),
            Mathf.Exp(Mathf.Lerp(Mathf.Log(Mathf.Max(a.z, 1e-5f)), Mathf.Log(Mathf.Max(b.z, 1e-5f)), x)),
            1f);
    }
}
