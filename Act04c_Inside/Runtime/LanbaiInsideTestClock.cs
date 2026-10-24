// =====================================================================================================
//  LanbaiInsideTestClock.cs   蓝白 · 第 4c、5 幕的 Play 模式测试时钟（UdonSharp）—— 只用于门测试场景
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn + U# rules). !!!
//
//  Gate_TestClock (the gate's) only ticks the gate and its clouds from U7 to U9 + 2. This one stands in for the Director
//  over the whole of acts 4 -> 5: t runs from `startT` at `speed` x real time to `endT`, and every driver is activated
//  when t enters its own LanbaiWindow(), ticked inside it and deactivated when t leaves it (the order of the dispatcher:
//  gate, clouds, skylight spot, inside). Loops at `endT` (everything is deactivated first, so a second departure is
//  tested too). Made (switched off) by 蓝白/Build/04c 门内. Use it INSTEAD of Gate_TestClock (switch that one off).
//  REMOVE IT from the real world: there the Director ticks.
// =====================================================================================================
using UdonSharp;
using UnityEngine;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiInsideTestClock : UdonSharpBehaviour
{
    public LanbaiGateDriver gate;
    public LanbaiGateClouds clouds;
    public LanbaiSkylightSpot skylight;
    public LanbaiInsideDriver inside;
    public float startT = 166.00f;             // just before U8 (the skylight spot)
    public float endT = 252.64f;               // U12 + 4 (act 6 takes the overlay)
    public float speed = 1f;
    public bool loop = true;

    private float _t;
    private float[] _wGate, _wClouds, _wSky, _wInside;
    private bool _onGate, _onClouds, _onSky, _onInside;

    void Start()
    {
        _t = startT;
        if (gate != null) _wGate = gate.LanbaiWindow();
        if (clouds != null) _wClouds = clouds.LanbaiWindow();
        if (skylight != null) _wSky = skylight.LanbaiWindow();
        if (inside != null) _wInside = inside.LanbaiWindow();
    }

    private static bool In(float[] w, float t)
    {
        return w != null && w.Length >= 2 && t >= w[0] && t < w[1];
    }

    void Update()
    {
        _t += Time.deltaTime * speed;
        if (_t > endT)
        {
            if (!loop) { _t = endT; return; }
            AllOff();
            _t = startT;
        }
        bool g = In(_wGate, _t), c = In(_wClouds, _t), k = In(_wSky, _t), i = In(_wInside, _t);
        if (gate != null && g != _onGate) { gate.LanbaiActivate(g); _onGate = g; }
        if (clouds != null && c != _onClouds) { clouds.LanbaiActivate(c); _onClouds = c; }
        if (skylight != null && k != _onSky) { skylight.LanbaiActivate(k); _onSky = k; }
        if (inside != null && i != _onInside) { inside.LanbaiActivate(i); _onInside = i; }
        if (g) gate.LanbaiTick(_t);
        if (c) clouds.LanbaiTick(_t);
        if (k) skylight.LanbaiTick(_t);
        if (i) inside.LanbaiTick(_t);
    }

    private void AllOff()
    {
        if (gate != null && _onGate) gate.LanbaiActivate(false);
        if (clouds != null && _onClouds) clouds.LanbaiActivate(false);
        if (skylight != null && _onSky) skylight.LanbaiActivate(false);
        if (inside != null && _onInside) inside.LanbaiActivate(false);
        _onGate = _onClouds = _onSky = _onInside = false;
    }

    // jump (from the Inspector's U# event button): back to startT, everything off first
    public void _Restart()
    {
        AllOff();
        _t = startT;
    }
}
