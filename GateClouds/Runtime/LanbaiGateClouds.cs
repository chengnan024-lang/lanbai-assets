// 蓝白 · 触手之门 · 云的运行时（UdonSharp）  gate clouds kit v1, 2026-10-22, cloud art team.
// !!! NOT COMPILED IN UNITY: compile with UdonSharp and check. !!!
//
// Filled by LanbaiGateCloudsBuilder (蓝白/Gate Clouds/Build). The act interface of CONTROL_总控.md §5:
//     LanbaiTick(t)        every frame inside LanbaiWindow() (t = timeline seconds)
//     LanbaiActivate(on)   `root` (GateRoot/GateClouds) on / off, only under an occluder; the driver itself sits on an
//                          always-active object (Director v1 rule: never switch off the object you live on)
//     LanbaiWindow()       {U6 - 20, U9 + 2} = {113.80, 181.55} (GateRoot's own window)
// (Apply() with the public `t` does the same as LanbaiTick, for a caller that sets t itself.)
// Start() / _Init(): every card gets its MaterialPropertyBlock (_Mirror, _Gain, _Alpha = opacity): property blocks are not
// saved with the scene, so they are written at runtime.
// Apply(): the towers SAG (localScale.y x sag, pivot on the base), SINK (localPosition.y + sink) and fade out in their
// last 2 s (alpha); a renderer turns off at alpha 0 (GateLayout_v2.json towers, unchanged).
// Keys are flattened (t0, v0, t1, v1, ...) per card, smoothstep between keys, held outside them.
using UdonSharp;
using VRC.SDKBase;
using UnityEngine;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiGateClouds : UdonSharpBehaviour
{
    [Header("Timeline seconds (set by the Director before Apply)")]
    public float t;

    [Header("The clouds' root (GateRoot/GateClouds), switched by LanbaiActivate")]
    public GameObject root;

    [Header("All cards (builder)")]
    public Renderer[] cardRenderers;
    public float[] cardMirror;
    public float[] cardGain;
    public float[] cardOpacity;

    [Header("Towers (builder)")]
    public Transform[] towers;
    public Renderer[] towerRenderers;
    public float[] towerOpacity;
    public float[] towerMirror;
    public float[] towerGain;
    public float[] towerBaseY;
    public float[] towerBaseScaleY;
    public float[] sagKeys;
    public int[] sagStart;
    public int[] sagCount;
    public float[] sinkKeys;
    public int[] sinkStart;
    public int[] sinkCount;
    public float[] alphaKeys;
    public int[] alphaStart;
    public int[] alphaCount;

    private MaterialPropertyBlock _mpb;
    private int _idAlpha, _idMirror, _idGain;
    // act 4's haze band for every LanbaiFog user (Common/UdonGlobals.md: act 4 = the gate's driver): LANBAI_GATE_NEAR
    private float[] _window;
    private bool _warnedMissing;
    // the fog band (_Udon_FogBand*) is NOT written here any more: D-22 gives the whole fog / moon / star family on
    // [U6, U9) to LanbaiGateDriver (one writer per global)

    public void LanbaiTick(float time)
    {
        if (_mpb == null) _Init();             // activated and ticked in the same frame: Start has not run yet (tech r1 #9)
        t = time;
        Apply();
    }

    public void LanbaiActivate(bool on)
    {
        if (root != null) root.SetActive(on);
    }

    // written by the builder from GateClouds_Layout.json "window" = {U6 - 20, U9 + 2} (FromLocal/cues.json labels)
    public float windowStart = 113.80f;
    public float windowEnd = 181.55f;

    public float[] LanbaiWindow()
    {
        if (_window == null) _window = new float[] { windowStart, windowEnd };   // no garbage per call
        return _window;
    }

    void Start()
    {
        if (_mpb == null) _Init();
    }

    // the set-up, callable before Start (tech r2 #7: an event method is not called as a plain method)
    public void _Init()
    {
        _mpb = new MaterialPropertyBlock();
        _idAlpha = VRCShader.PropertyToID("_Alpha");
        _idMirror = VRCShader.PropertyToID("_Mirror");
        _idGain = VRCShader.PropertyToID("_Gain");
        for (int i = 0; i < cardRenderers.Length; i++)
        {
            if (cardRenderers[i] == null) continue;
            _mpb.Clear();
            _mpb.SetFloat(_idMirror, cardMirror[i]);
            _mpb.SetFloat(_idGain, cardGain[i]);
            _mpb.SetFloat(_idAlpha, cardOpacity[i]);
            cardRenderers[i].SetPropertyBlock(_mpb);
        }
    }

    float Smooth(float x)
    {
        x = Mathf.Clamp01(x);
        return x * x * (3f - 2f * x);
    }

    float Key(float[] keys, int start, int count, float time, float dflt)
    {
        if (count <= 0) return dflt;
        if (time <= keys[start]) return keys[start + 1];
        int last = start + 2 * (count - 1);
        if (time >= keys[last]) return keys[last + 1];
        for (int k = start; k < last; k += 2)
        {
            float t0 = keys[k], t1 = keys[k + 2];
            if (time >= t0 && time <= t1)
                return Mathf.Lerp(keys[k + 1], keys[k + 3], Smooth((time - t0) / Mathf.Max(t1 - t0, 1e-4f)));
        }
        return keys[last + 1];
    }

    public void Apply()
    {
        if (_mpb == null) _Init();
        for (int i = 0; i < towers.Length; i++)
        {
            Transform tr = towers[i];
            if (tr == null) continue;
            float sag = Key(sagKeys, sagStart[i], sagCount[i], t, 1f);
            float sink = Key(sinkKeys, sinkStart[i], sinkCount[i], t, 0f);
            float a = Key(alphaKeys, alphaStart[i], alphaCount[i], t, 1f);
            Vector3 s = tr.localScale;
            s.y = towerBaseScaleY[i] * sag;
            tr.localScale = s;
            Vector3 p = tr.localPosition;
            p.y = towerBaseY[i] + sink;
            tr.localPosition = p;
            Renderer r = towerRenderers[i];
            if (r == null)
            {
                // the gate was rebuilt after the clouds: skip, warn once (v1.5, 总导演 A4)
                if (!_warnedMissing) Debug.LogWarning("[GateClouds] a tower renderer is missing: please re-run 蓝白/Gate Clouds/Build");
                _warnedMissing = true;
                continue;
            }
            bool on = a > 0.001f;
            if (r.enabled != on) r.enabled = on;
            if (!on) continue;
            _mpb.Clear();
            _mpb.SetFloat(_idMirror, towerMirror[i]);
            _mpb.SetFloat(_idGain, towerGain[i]);
            _mpb.SetFloat(_idAlpha, towerOpacity[i] * a);
            r.SetPropertyBlock(_mpb);
        }
    }
}
