// =====================================================================================================
//  LanbaiRainState.cs        蓝白 · the rain / wetness globals and their per-scene values (bible §1.6, §4.6)
//
//  !!! UNCOMPILED IN UNITY. Type-checked with Roslyn (C# 9) against the Unity 2021.1 UnityEngine reference
//      assembly and a stub of UdonSharp / VRC.SDKBase. Compile with UdonSharp 1.x in Unity 2022.3. !!!
//
//  LOCAL. Publishes every frame:
//    _Udon_Wetness     road / stop wetness (Lagarde)            _Udon_RainFall  rain still falling (puddle rings)
//    _Udon_RainAmount  water on the glass (= AREA of beads left) _Udon_RunStretch running drops drawn out
//    _Udon_FlowDir     flow FRAME A: xyz = air-drag direction on the drops (world), w = drag 0..1
//    _Udon_FlowDirB    flow frame B, _Udon_FlowMix 0..1: when the flow changes by > 6 deg or 0.12 drag, B is set to the
//                      new flow and faded in over 1.2 s, then A := B. The runner field therefore CROSS-FADES between
//                      fixed frames instead of turning about each pane's pivot (verification round 2, minor 10).
//    _Udon_RunClock    x = integral of drag dt (the shader's distance clock: speed changes never make heads jump),
//                      y = drag averaged over ~4 s (turns distances into ages)
//    _Udon_StopOffset  xyz = R_Stop world position - its home position (the treadmill moves R_Stop)
//  The Director calls a preset (SendCustomEvent) or SetTargets(); values glide there linearly in 'seconds'.
//  The bus never moves (treadmill): SetBusSpeed() only changes how hard the air pushes the drops.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiRainState : UdonSharpBehaviour
{
    [Tooltip("The bus root: its forward = the direction of travel.")]
    public Transform bus;
    [Tooltip("R_Stop root; its position at Start is 'home'.")]
    public Transform stopRoot;

    [Header("Current values (driven; shown for debugging)")]
    public float wetness = 1f;
    public float rainAmount = 1f;
    public float rainFall = 1f;
    public float drag;
    public float dragUp;
    public float stretch;

    [Header("Flow frames")]
    public float frameAngleStep = 6f;       // degrees
    public float frameDragStep = 0.12f;
    public float frameFadeSeconds = 1.2f;

    private float[] _from = new float[6];
    private float[] _to = new float[6];
    private float _t0;
    private float _dur;
    private Vector3 _stopHome;
    private int _idWet, _idRain, _idFall, _idFlow, _idFlowB, _idMix, _idClock, _idStretch, _idStop;
    private Vector4 _frameA, _frameB;
    private bool _fading;
    private float _fadeT0;
    private float _stableSince;
    private Vector4 _lastLive;
    private float _clock;
    private float _dragAvg;

    private void Start()
    {
        _idWet = VRCShader.PropertyToID("_Udon_Wetness");
        _idRain = VRCShader.PropertyToID("_Udon_RainAmount");
        _idFall = VRCShader.PropertyToID("_Udon_RainFall");
        _idFlow = VRCShader.PropertyToID("_Udon_FlowDir");
        _idFlowB = VRCShader.PropertyToID("_Udon_FlowDirB");
        _idMix = VRCShader.PropertyToID("_Udon_FlowMix");
        _idClock = VRCShader.PropertyToID("_Udon_RunClock");
        _idStretch = VRCShader.PropertyToID("_Udon_RunStretch");
        _idStop = VRCShader.PropertyToID("_Udon_StopOffset");
        if (stopRoot != null) _stopHome = stopRoot.position;
        Preset_Stop();
        _frameA = LiveFlow();
        _frameB = _frameA;
        _lastLive = _frameA;
    }

    /// <summary>Glide to new values over 'seconds' (0 = now).</summary>
    public void SetTargets(float wet, float rain, float fall, float dragAmount, float dragUpAmount, float stretchAmount, float seconds)
    {
        _from[0] = wetness; _from[1] = rainAmount; _from[2] = rainFall; _from[3] = drag; _from[4] = dragUp; _from[5] = stretch;
        _to[0] = wet; _to[1] = rain; _to[2] = fall; _to[3] = dragAmount; _to[4] = dragUpAmount; _to[5] = stretchAmount;
        _t0 = Time.timeSinceLevelLoad;
        _dur = Mathf.Max(0f, seconds);
        if (_dur <= 0f) Snap();
    }

    /// <summary>The Director's world speed (m/s); 10 m/s = full drag on the glass.</summary>
    public void SetBusSpeed(float metresPerSecond)
    {
        float d = Mathf.Clamp01(metresPerSecond / 10f);
        _to[3] = d;
        if (_dur <= 0f) drag = d;
    }

    // ---------------- presets (bible §4.6 雨的状态) ----------------
    // 1 the stop: rain, static beads + occasional slow runners
    public void Preset_Stop() { SetTargets(1f, 1f, 1f, 0f, 0f, 0f, 0f); }
    // 1 -> 2 the bus glides out at U1 (12 s smoothstep to 10 m/s, bible 1->2): drops start to lean back 30-60 deg
    public void Preset_Depart() { SetTargets(1f, 1f, 1f, 1f, 0f, 0f, 12f); }
    // 2 night road (also the 11 false wake's look is DRY - use Preset_Dry there)
    public void Preset_NightRoad() { SetTargets(1f, 1f, 1f, 1f, 0f, 0f, 2f); }
    // 3 lift-off U4: flow slows, stops, then streaks up and back and evaporates within 20 s
    public void Preset_LiftOff() { SetTargets(1f, 0f, 0f, 1f, 0.9f, 1.6f, 20f); }
    // 4-10 clean glass, 11 false wake "dry, slightly too clean"
    public void Preset_Dry() { SetTargets(0f, 0f, 0f, 0f, 0f, 0f, 0f); }
    // 12 wake (set under the second white): wet road 0.85, crown drying, glass 0.4 = 40 % of the beads left (the big
    // ones), no falling rain
    public void Preset_Wake() { SetTargets(0.85f, 0.4f, 0f, 0f, 0f, 0f, 0f); }
    // a NEW ROUND (bible §6·12: the player gets off, back on, sits down): "雨在 20 秒里回来"
    public void Preset_NewRound() { SetTargets(1f, 1f, 1f, 0f, 0f, 0f, 20f); }

    private void Snap()
    {
        wetness = _to[0]; rainAmount = _to[1]; rainFall = _to[2]; drag = _to[3]; dragUp = _to[4]; stretch = _to[5];
    }

    private Vector4 LiveFlow()
    {
        Vector3 back = bus != null ? -bus.forward : Vector3.back;
        Vector3 dir = (back + Vector3.up * dragUp).normalized;
        return new Vector4(dir.x, dir.y, dir.z, Mathf.Clamp01(drag + dragUp * 0.5f));
    }

    private void Update()
    {
        float now = Time.timeSinceLevelLoad;
        float dt = Time.deltaTime;
        if (_dur > 0f)
        {
            float u = Mathf.Clamp01((now - _t0) / _dur);
            wetness = Mathf.Lerp(_from[0], _to[0], u);
            rainAmount = Mathf.Lerp(_from[1], _to[1], u);
            rainFall = Mathf.Lerp(_from[2], _to[2], u);
            drag = Mathf.Lerp(_from[3], _to[3], u);
            dragUp = Mathf.Lerp(_from[4], _to[4], u);
            stretch = Mathf.Lerp(_from[5], _to[5], u);
            if (u >= 1f) _dur = 0f;
        }
        VRCShader.SetGlobalFloat(_idWet, wetness);
        VRCShader.SetGlobalFloat(_idRain, rainAmount);
        VRCShader.SetGlobalFloat(_idFall, rainFall);
        VRCShader.SetGlobalFloat(_idStretch, stretch);

        // ---- flow frames
        Vector4 live = LiveFlow();
        if (Vector4.Distance(live, _lastLive) > 1e-4f) _stableSince = now;
        _lastLive = live;
        float mix = 0f;
        if (_fading)
        {
            float u = Mathf.Clamp01((now - _fadeT0) / Mathf.Max(0.1f, frameFadeSeconds));
            mix = u * u * (3f - 2f * u);
            if (u >= 1f) { _frameA = _frameB; _fading = false; mix = 0f; }
        }
        if (!_fading)
        {
            float ang = Vector3.Angle(new Vector3(_frameA.x, _frameA.y, _frameA.z), new Vector3(live.x, live.y, live.z));
            float dd = Mathf.Abs(_frameA.w - live.w);
            bool far = ang > frameAngleStep || dd > frameDragStep;
            bool settledOff = (ang > 0.05f || dd > 0.002f) && now - _stableSince > 1f;   // land exactly on a steady flow
            if (far || settledOff)
            {
                _frameB = live; _fading = true; _fadeT0 = now; mix = 0f;
            }
        }
        VRCShader.SetGlobalVector(_idFlow, _frameA);
        VRCShader.SetGlobalVector(_idFlowB, _frameB);
        VRCShader.SetGlobalFloat(_idMix, mix);

        // ---- distance clock for the runners
        float dl = Mathf.Clamp01(live.w);
        _clock += dl * dt;
        _dragAvg += (dl - _dragAvg) * (1f - Mathf.Exp(-dt / 4f));
        VRCShader.SetGlobalVector(_idClock, new Vector4(_clock, _dragAvg, 0f, 0f));

        Vector3 off = stopRoot != null ? stopRoot.position - _stopHome : Vector3.zero;
        VRCShader.SetGlobalVector(_idStop, new Vector4(off.x, off.y, off.z, 0f));
    }
}
