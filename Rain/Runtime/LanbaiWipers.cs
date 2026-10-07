// =====================================================================================================
//  LanbaiWipers.cs        蓝白 · the driverless wipers (bible 1->2 U1 "雨刮开始每 5 秒扫一次，无人驾驶", §4.6, §6·2)
//
//  !!! UNCOMPILED IN UNITY. Type-checked with Roslyn (C# 9) against the Unity 2021.1 UnityEngine reference
//      assembly and a stub of UdonSharp / VRC.SDKBase. Compile with UdonSharp 1.x in Unity 2022.3. !!!
//
//  LOCAL (everyone's wipers run on their own clock; nobody can compare). Two tandem blades. Each blade pivot is a
//  Transform at the spindle: its local +Y = the arm direction AT REST (parked along the bottom of the windscreen), its
//  local +Z = the spindle axis; the sweep turns the pivot about local +Z by 0 -> sweepDegrees -> 0. The arm + blade
//  mesh is a CHILD of the pivot. If your blades sweep the wrong way, use a negative sweepDegrees.
//  One cycle = out (stroke s) + back (stroke s), smooth (1 - cos), then parked until the next cycle (period s).
//  Globals for Lanbai/BusGlass (windscreen material: _Wipers = 1): the glass under a blade loses its beads and
//  runners, refills in _WipeRefill s (bible 2-5 s), and a thin water line rides ahead of the moving blade.
//    _Udon_WiperPivot{0,1} (pivot world, r_max)   _Udon_WiperRest{0,1} (rest dir world, sweep rad)
//    _Udon_WiperAxis{0,1} (axis world, r_min)     _Udon_WiperTime (cycle start, stroke, period, previous cycle ran)
//  Director: StartWipers at U1 (17.50), StopWipers at U4 + 20 (95.8, the windscreen is clean - bible §4.6): the blades
//  finish their cycle and park. Scene 11 (dry) and 12 (parked at the stop): never started.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiWipers : UdonSharpBehaviour
{
    [Tooltip("Blade pivots (spindles): local +Y = arm at rest, local +Z = spindle axis. 1 or 2.")]
    public Transform[] pivot = new Transform[2];
    [Tooltip("Sweep angle (deg); negative = the other way.")]
    public float sweepDegrees = 95f;
    [Tooltip("The rubber wipes from rMin to rMax along the arm (m from the spindle).")]
    public float rMin = 0.14f;
    public float rMax = 0.66f;
    [Tooltip("One stroke (s): out, then the same back.")]
    public float strokeSeconds = 0.65f;
    [Tooltip("A cycle every ... s (bible: 5).")]
    public float periodSeconds = 5f;

    private Quaternion[] _rest;
    private int[] _idPiv, _idRest, _idAxis;
    private int _idTime;
    private bool _running;
    private bool _stopping;
    private bool _prev;
    private float _t0 = -1000f;

    private void Start()
    {
        int n = pivot == null ? 0 : pivot.Length;
        _rest = new Quaternion[n];
        for (int i = 0; i < n; i++) if (pivot[i] != null) _rest[i] = pivot[i].localRotation;
        _idPiv = new int[2]; _idRest = new int[2]; _idAxis = new int[2];
        for (int k = 0; k < 2; k++)
        {
            _idPiv[k] = VRCShader.PropertyToID("_Udon_WiperPivot" + k);
            _idRest[k] = VRCShader.PropertyToID("_Udon_WiperRest" + k);
            _idAxis[k] = VRCShader.PropertyToID("_Udon_WiperAxis" + k);
        }
        _idTime = VRCShader.PropertyToID("_Udon_WiperTime");
        Publish();
    }

    public void StartWipers()
    {
        if (_running && !_stopping) return;
        float now = Time.timeSinceLevelLoad;
        if (!_running) { _t0 = now; _prev = false; }
        _running = true; _stopping = false;
    }

    public void StopWipers() { if (_running) _stopping = true; }

    // angle (deg) of the blade tau seconds into its cycle
    private float Angle(float tau)
    {
        float th = Mathf.Max(0.05f, strokeSeconds);
        if (tau <= 0f || tau >= 2f * th) return 0f;
        if (tau < th) return sweepDegrees * (0.5f - 0.5f * Mathf.Cos(Mathf.PI * tau / th));
        return sweepDegrees * (0.5f + 0.5f * Mathf.Cos(Mathf.PI * (tau - th) / th));
    }

    private void Update()
    {
        float now = Time.timeSinceLevelLoad;
        if (_running)
        {
            float per = Mathf.Max(periodSeconds, 2f * strokeSeconds + 0.1f);
            if (now - _t0 >= 2f * strokeSeconds && _stopping) { _running = false; _stopping = false; }
            else if (now - _t0 >= per) { _t0 += per; _prev = true; if (now - _t0 >= per) _t0 = now; }
        }
        float a = _running ? Angle(now - _t0) : 0f;
        for (int i = 0; i < _rest.Length; i++)
        {
            if (pivot[i] == null) continue;
            pivot[i].localRotation = _rest[i] * Quaternion.AngleAxis(a, Vector3.forward);
        }
        Publish();
    }

    private void Publish()
    {
        float sweepRad = Mathf.Abs(sweepDegrees) * Mathf.Deg2Rad;
        for (int k = 0; k < 2; k++)
        {
            Transform p = (pivot != null && k < pivot.Length) ? pivot[k] : null;
            if (p == null || _rest == null || k >= _rest.Length)
            {
                VRCShader.SetGlobalVector(_idPiv[k], Vector4.zero);
                continue;
            }
            // the REST frame in world space (the pivot's parent x its rest rotation), whatever the blade is doing now
            Quaternion restW = (p.parent != null ? p.parent.rotation : Quaternion.identity) * _rest[k];
            Vector3 e1 = restW * Vector3.up;
            Vector3 ax = restW * Vector3.forward;
            if (sweepDegrees < 0f) ax = -ax;                 // the shader measures the sweep as positive angles
            Vector3 pos = p.position;
            VRCShader.SetGlobalVector(_idPiv[k], new Vector4(pos.x, pos.y, pos.z, rMax));
            VRCShader.SetGlobalVector(_idRest[k], new Vector4(e1.x, e1.y, e1.z, sweepRad));
            VRCShader.SetGlobalVector(_idAxis[k], new Vector4(ax.x, ax.y, ax.z, rMin));
        }
        VRCShader.SetGlobalVector(_idTime, new Vector4(_t0, Mathf.Max(0.05f, strokeSeconds), Mathf.Max(periodSeconds, 2f * strokeSeconds + 0.1f), _prev ? 1f : 0f));
    }
}
