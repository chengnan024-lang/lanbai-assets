// =====================================================================================================
//  LanbaiOneDrop.cs        蓝白 · "那一滴雨": the whole dream takes as long as one raindrop's slide
//                          (bible §3.3 一滴雨, §4.6, §6·1 坐下, §6·12 0-8 s)
//
//  !!! UNCOMPILED IN UNITY. Type-checked with Roslyn (C# 9) against the Unity 2021.1 UnityEngine reference
//      assembly and a stub of UdonSharp / VRC.SDKBase. Compile with UdonSharp 1.x in Unity 2022.3. !!!
//
//  LOCAL: every player has their own drop on the hero window (no sync).
//    ResetRound()   at the start of a round: at the top of its path, round, visible
//    BeginSlide()   the local player sits down: 20 mm at ~1 cm/s (2 s, stick-slip), then it stops
//    Hide()         after 1 -> 2 (fades out over 1.5 s with the strip it swept; it stays exactly where it stopped)
//    ShowAtRest()   scene 12, the moment the second white has shrunk into the tube: it is still there
//    FinishSlide()  scene 12, 0-8 s: the last 60 mm in 8 s, then it sinks into the rubber seal
//  The head's shape follows its speed (round when it pauses, drawn out when it runs).
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiOneDrop : UdonSharpBehaviour
{
    [Tooltip("The 12 x 96 mm quad with Lanbai/OneDrop on the outer face of the hero window.")]
    public Renderer decal;
    [Tooltip("Where the first slide stops, as a fraction of the 80 mm path (20 mm).")]
    public float pauseAt = 0.25f;
    public float firstSlideSeconds = 2f;
    public float lastSlideSeconds = 8f;
    public float mergeSeconds = 0.6f;
    [Tooltip("Stick-slip depth (0 = smooth glide, 0.9 = pronounced stops).")]
    public float stickSlip = 0.8f;

    [Tooltip("Half-width of the strip its slide sweeps clean of beads on the BusGlass (m).")]
    public float sweptHalfWidth = 0.0022f;
    [Tooltip("Hide() fades the drop and its strip out over this many seconds (no pop).")]
    public float hideSeconds = 1.5f;

    private Material _m;
    private int _idA, _idB;
    private int _mode;          // 0 waiting, 1 first slide, 2 resting, 3 hidden, 4 last slide, 5 merging, 6 gone, 7 hiding
    private float _strip = 1f;  // 0..1 how much of the swept strip is published (v2: 0 while hidden)
    private float _t0;
    private float _progress;
    private float _slide;
    private float _merge;
    private float _visible = 1f;

    private void Start()
    {
        if (decal != null) _m = decal.material;
        _idA = VRCShader.PropertyToID("_Udon_OneDropA");
        _idB = VRCShader.PropertyToID("_Udon_OneDropB");
        ResetRound();
    }

    public void ResetRound()
    {
        _mode = 0; _progress = 0f; _slide = 0f; _merge = 0f; _visible = 1f; _strip = 1f;
        Apply();
    }

    public void BeginSlide()
    {
        if (_mode != 0) return;
        _mode = 1;
        _t0 = Time.timeSinceLevelLoad;
    }

    public void Hide()
    {
        if (_mode == 1) { _progress = pauseAt; _slide = 0f; }
        _mode = 7;
        _t0 = Time.timeSinceLevelLoad;
    }

    public void ShowAtRest()
    {
        _progress = pauseAt; _slide = 0f; _merge = 0f; _visible = 1f; _strip = 1f;
        _mode = 2;
        Apply();
    }

    public void FinishSlide()
    {
        if (_mode >= 4 && _mode != 7) return;
        _progress = pauseAt; _visible = 1f; _strip = 1f;
        _mode = 4;
        _t0 = Time.timeSinceLevelLoad;
    }

    // monotonic stick-slip profile: eased, with k speed pulses (derivative >= 0 while stickSlip < 1)
    private float Profile(float u, float k)
    {
        u = Mathf.Clamp01(u);
        float e = u * u * (3f - 2f * u);
        float w = 2f * Mathf.PI * k;
        return Mathf.Clamp01(e - stickSlip * Mathf.Sin(w * e) / w);
    }

    private float Speed(float u, float k)
    {
        u = Mathf.Clamp01(u);
        float e = u * u * (3f - 2f * u);
        float de = 6f * u * (1f - u);
        return de * (1f - stickSlip * Mathf.Cos(2f * Mathf.PI * k * e));
    }

    private void Update()
    {
        if (_mode == 0 || _mode == 3 || _mode == 6) return;
        float now = Time.timeSinceLevelLoad;
        float dt = Time.deltaTime;
        if (_mode == 1)
        {
            float u = (now - _t0) / Mathf.Max(0.1f, firstSlideSeconds);
            _progress = pauseAt * Profile(u, 3f);
            _slide = Mathf.Clamp01(Speed(u, 3f) / 1.6f);
            if (u >= 1f) { _progress = pauseAt; _mode = 2; }
        }
        else if (_mode == 2)
        {
            _slide = Mathf.MoveTowards(_slide, 0f, dt * 1.5f);
        }
        else if (_mode == 4)
        {
            float u = (now - _t0) / Mathf.Max(0.1f, lastSlideSeconds);
            _progress = pauseAt + (1f - pauseAt) * Profile(u, 5f);
            _slide = Mathf.Clamp01(Speed(u, 5f) / 1.6f);
            if (u >= 1f) { _progress = 1f; _mode = 5; _t0 = now; }
        }
        else if (_mode == 7)
        {
            float u = Mathf.Clamp01((now - _t0) / Mathf.Max(0.05f, hideSeconds));
            _visible = 1f - u; _strip = 1f - u;
            if (u >= 1f) { _visible = 0f; _strip = 0f; _mode = 3; }
        }
        else if (_mode == 5)
        {
            _merge = Mathf.Clamp01((now - _t0) / Mathf.Max(0.05f, mergeSeconds));
            _slide = Mathf.MoveTowards(_slide, 0f, dt * 2f);
            if (_merge >= 1f) { _visible = 0f; _mode = 6; }
        }
        Apply();
    }

    // the swept path for Lanbai/BusGlass: from the start of the path to the head (decal = Unity Quad scaled 12 x 96 mm)
    private void PublishPath()
    {
        if (decal == null) return;
        Transform tr = decal.transform;
        float yStart = 0.5f - 8f / 96f;
        float yHead = 0.5f - (8f + _progress * 80f) / 96f;
        Vector3 a = tr.TransformPoint(new Vector3(0f, yStart, 0f));
        Vector3 b = tr.TransformPoint(new Vector3(0f, yHead + 2.5f / 96f, 0f));
        float on = (_progress > 0.01f && _strip > 0.001f) ? 1f : 0f;      // v2: no bead-free strip while hidden
        VRCShader.SetGlobalVector(_idA, new Vector4(a.x, a.y, a.z, sweptHalfWidth * _strip));
        VRCShader.SetGlobalVector(_idB, new Vector4(b.x, b.y, b.z, on));
    }

    private void Apply()
    {
        PublishPath();
        if (_m == null) return;
        _m.SetFloat("_Progress", _progress);
        _m.SetFloat("_Slide", _slide);
        _m.SetFloat("_Merge", _merge);
        _m.SetFloat("_Visible", _visible);
    }
}
