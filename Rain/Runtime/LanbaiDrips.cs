// =====================================================================================================
//  LanbaiDrips.cs        蓝白 · every drip at the stop and on the bus (bible §4.6 天窗, §5.4 滴水, §5.5, §6·12)
//
//  !!! UNCOMPILED IN UNITY. Type-checked with Roslyn (C# 9) against the Unity 2021.1 UnityEngine reference
//      assembly and a stub of UdonSharp / VRC.SDKBase. Compile with UdonSharp 1.x in Unity 2022.3. !!!
//
//  LOCAL (no sync: each client drips on its own; nobody can compare). Per drip point i:
//    grow   the hanging drop (Lanbai/DripDrop, frames 0-11) swells over the interval
//    pinch  frames 12-14 (0.12 s): one falling drop is emitted, frame 15 recoils
//    land   after t = sqrt(2 h / g): a splash, a ring in the water below (a _Udon_Drip slot written AT DETACH with the
//           future impact time, in R_STOP-LOCAL space so the ring rides with the puddle when R_Stop moves), and the
//           door step gets wetter (skylight drip).
//  v2 (verification round 2): ONE shared falling-drop system and ONE shared splash system for every stop drip
//  (the emitter is moved to the point, then Emit(1): Simulation Space = Custom -> R_Stop keeps each drop where it was
//  born, riding with the stop), and one for the bus drip (World: the bus never moves). Bible §1.9: <= 8 systems.
//  Intervals (bible): scene 1 lamp arm & sign rim 1.5-4 s, skylight 4-7 s, notice case 3.5-6 s;
//  scene 12 lamp & sign 4 s -> 10 s over 8 min, case 3.5-6 s, skylight 4-7 s. First drip of scene 12 ~8 s in.
//  Director calls (SendCustomEvent): BeginStop (scene 1, also at Start), StopBusDrips (U1: the bus moves),
//  StopDrips (U5, cloud entry, under the white of the cloud), BeginWake (12).
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiDrips : UdonSharpBehaviour
{
    [Header("Per drip point (all arrays the same length)")]
    [Tooltip("The lip. The Lanbai/DripDrop quad hangs from this point (child at local 0,0,0, scale 0.01).")]
    public Transform[] dripPoint;
    [Tooltip("Renderer of the hanging drop quad (material Lanbai/DripDrop; an instance is made per drip).")]
    public Renderer[] pendant;
    [Tooltip("Height of the lip above the surface it hits (m), to +-1 cm (the ring is drawn only on that surface).")]
    public float[] fallHeight;
    [Tooltip("Scene 1 interval range (s).")]
    public float[] intervalMin;
    public float[] intervalMax;
    [Tooltip("Scene 12 interval at the start and after wakeStretchSeconds (s).")]
    public float[] wakeIntervalStart;
    public float[] wakeIntervalEnd;
    [Tooltip("Lands in water or on a wet film: draws a ring (uses one of the 4 _Udon_Drip slots).")]
    public bool[] ringsWater;
    [Tooltip("Belongs to the BUS (the skylight corner): world-space drop, wets the door step, stops at U1.")]
    public bool[] onBus;

    [Header("Shared particle systems (Play On Awake on, Emission rate 0, Shape off)")]
    [Tooltip("Falling drops of the STOP points: M_DripFall, Simulation Space = Custom -> R_Stop, gravity 1, speed 0.")]
    public ParticleSystem stopFall;
    [Tooltip("Splashes of the STOP points: M_RainSplash, Simulation Space = Custom -> R_Stop.")]
    public ParticleSystem stopSplash;
    [Tooltip("Falling drop of the bus point(s): M_DripFall, Simulation Space = World.")]
    public ParticleSystem busFall;
    [Tooltip("R_Stop root (its position at Start = home). Rings are stored relative to it.")]
    public Transform stopRoot;

    [Header("Door step")]
    public Renderer stepWet;
    public float stepDryPerSecond = 0.004f;
    public float stepWetPerDrip = 0.12f;

    [Header("Scene 12")]
    public float wakeStretchSeconds = 480f;
    public float wakeFirstDripDelay = 8f;

    private float[] _next;
    private float[] _start;
    private float[] _pinch;
    private float[] _landAt;
    private Vector3[] _landLocal;      // impact point, R_Stop-local world space
    private bool[] _active;
    private Material[] _mats;
    private Material _stepMat;
    private float _stepWetness = 0.35f;
    private bool _wake;
    private float _wakeT0;
    private int _slot;
    private int[] _dripIds;
    private int _n;
    private Vector3 _stopHome;

    private void Start()
    {
        _n = dripPoint == null ? 0 : dripPoint.Length;
        _next = new float[_n];
        _start = new float[_n];
        _pinch = new float[_n];
        _landAt = new float[_n];
        _landLocal = new Vector3[_n];
        _active = new bool[_n];
        _mats = new Material[_n];
        for (int i = 0; i < _n; i++)
        {
            _pinch[i] = -1f;
            _landAt[i] = -1f;
            if (pendant != null && i < pendant.Length && pendant[i] != null) _mats[i] = pendant[i].material;
        }
        if (stepWet != null) _stepMat = stepWet.material;
        if (stopRoot != null) _stopHome = stopRoot.position;
        _dripIds = new int[4];
        for (int k = 0; k < 4; k++) _dripIds[k] = VRCShader.PropertyToID("_Udon_Drip" + k);
        BeginStop();
    }

    private Vector3 StopOffset()
    {
        return stopRoot != null ? stopRoot.position - _stopHome : Vector3.zero;
    }

    private bool IsBus(int i) { return onBus != null && i < onBus.Length && onBus[i]; }

    // ------------------------------------------------------------------ Director events
    public void BeginStop()
    {
        _wake = false;
        float now = Time.timeSinceLevelLoad;
        for (int i = 0; i < _n; i++)
        {
            _active[i] = true;
            _start[i] = now;
            _next[i] = now + Random.Range(0.2f, 1f) * Interval(i, now);    // de-synchronise the first drips
            _pinch[i] = -1f;
            SetPendantVisible(i, true);
        }
    }

    public void BeginWake()
    {
        _wake = true;
        float now = Time.timeSinceLevelLoad;
        _wakeT0 = now;
        for (int i = 0; i < _n; i++)
        {
            _active[i] = true;
            _start[i] = now;
            _next[i] = now + wakeFirstDripDelay + Random.Range(0f, 3f) * i;
            _pinch[i] = -1f;
            SetPendantVisible(i, true);
        }
    }

    /// <summary>U1: the bus starts to move - its own drip (skylight corner) stops; the stop's drips go on.</summary>
    public void StopBusDrips()
    {
        for (int i = 0; i < _n; i++) if (IsBus(i)) { _active[i] = false; SetPendantVisible(i, false); }
    }

    /// <summary>U5 (cloud entry, hidden in the white): every drip stops, rings cleared.</summary>
    public void StopDrips()
    {
        for (int i = 0; i < _n; i++) { _active[i] = false; SetPendantVisible(i, false); }
        for (int k = 0; k < 4; k++) VRCShader.SetGlobalVector(_dripIds[k], Vector4.zero);
    }

    // ------------------------------------------------------------------
    private void SetPendantVisible(int i, bool on)
    {
        if (pendant != null && i < pendant.Length && pendant[i] != null) pendant[i].enabled = on;
    }

    private void SetFrame(int i, float f)
    {
        if (_mats[i] != null) _mats[i].SetFloat("_Frame", f);
    }

    private float GetF(float[] a, int i, float def)
    {
        if (a == null || i >= a.Length) return def;
        return a[i];
    }

    private float Interval(int i, float now)
    {
        if (!_wake) return Random.Range(GetF(intervalMin, i, 1.5f), GetF(intervalMax, i, 4f));
        float u = Mathf.Clamp01((now - _wakeT0) / Mathf.Max(1f, wakeStretchSeconds));
        float c = Mathf.Lerp(GetF(wakeIntervalStart, i, 4f), GetF(wakeIntervalEnd, i, 10f), u);
        return c * Random.Range(0.85f, 1.15f);
    }

    private void EmitAt(ParticleSystem ps, Vector3 worldPos)
    {
        if (ps == null) return;
        ps.transform.position = worldPos;            // particles keep their simulation-space position after this
        ps.Emit(1);
    }

    private void Detach(int i, float now)
    {
        _pinch[i] = now;
        Vector3 lip = dripPoint[i].position;
        bool bus = IsBus(i);
        EmitAt(bus ? busFall : stopFall, lip);
        float h = Mathf.Max(0.05f, GetF(fallHeight, i, 2f));
        float tf = Mathf.Sqrt(2f * h / 9.81f);
        Vector3 hit = lip - Vector3.up * h;
        Vector3 off = bus ? Vector3.zero : StopOffset();
        _landLocal[i] = hit - off;
        bool rings = ringsWater != null && i < ringsWater.Length && ringsWater[i];
        if (rings && !bus)
        {
            VRCShader.SetGlobalVector(_dripIds[_slot], new Vector4(_landLocal[i].x, _landLocal[i].y, _landLocal[i].z, now + tf));
            _slot = (_slot + 1) % 4;
        }
        _landAt[i] = now + tf;
        _next[i] = now + 0.4f + Interval(i, now);
    }

    private void Land(int i)
    {
        if (IsBus(i))
        {
            _stepWetness = Mathf.Min(1f, _stepWetness + stepWetPerDrip);
        }
        else
        {
            EmitAt(stopSplash, _landLocal[i] + StopOffset());
        }
        _landAt[i] = -1f;
    }

    private void Update()
    {
        float now = Time.timeSinceLevelLoad;
        for (int i = 0; i < _n; i++)
        {
            if (_landAt[i] >= 0f && now >= _landAt[i]) Land(i);
        }
        if (_stepMat != null)
        {
            _stepWetness = Mathf.Max(0.15f, _stepWetness - Time.deltaTime * stepDryPerSecond);
            _stepMat.SetFloat("_Wet", _stepWetness);
        }

        for (int i = 0; i < _n; i++)
        {
            if (!_active[i] || dripPoint[i] == null) continue;
            if (_pinch[i] >= 0f)
            {
                float a = now - _pinch[i];
                float f = 15f;
                if (a < 0.04f) f = 12f;
                else if (a < 0.08f) f = 13f;
                else if (a < 0.12f) f = 14f;
                if (a > 0.40f)
                {
                    _pinch[i] = -1f;
                    _start[i] = now;
                    f = 0f;
                }
                SetFrame(i, f);
                continue;
            }
            float span = _next[i] - _start[i];
            float g = span > 0.01f ? Mathf.Clamp01((now - _start[i]) / span) : 1f;
            SetFrame(i, Mathf.Floor(11.99f * Mathf.Pow(g, 0.7f)));
            if (now >= _next[i]) Detach(i, now);
        }
    }
}
