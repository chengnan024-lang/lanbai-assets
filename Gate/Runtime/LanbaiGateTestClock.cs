// =====================================================================================================
//  LanbaiGateTestClock.cs   蓝白 · 门的 Play 模式测试时钟（UdonSharp）—— 只用于测试
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn + U# rules). !!!
//
//  Without LB_Journey / the Director in the test scene nothing ticks the gate in Play mode (ClientSim or a VRChat test
//  build), so the deck does not move and the headset checks (README_GateClouds §8) cannot be done. This clock stands in
//  for the Director: it runs t from `startT` at `speed` x real time, activates both drivers once and ticks them every
//  frame (LanbaiGateDriver first: it writes the globals the clouds read). Loops at `endT` when `loop` is on.
//  Made by 蓝白/Gate/Build Driver (option "with test clock"). REMOVE IT from the real world: there the Director ticks.
// =====================================================================================================
using UdonSharp;
using UnityEngine;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiGateTestClock : UdonSharpBehaviour
{
    public LanbaiGateDriver gate;
    public LanbaiGateClouds clouds;
    public float startT = 150.30f;             // U7
    public float endT = 181.55f;               // U9 + 2
    public float speed = 1f;
    public bool loop = true;

    private float _t;
    private bool _on;

    void Start()
    {
        _t = startT;
    }

    void Update()
    {
        if (!_on)
        {
            if (gate != null) gate.LanbaiActivate(true);
            if (clouds != null) clouds.LanbaiActivate(true);
            _on = true;
        }
        _t += Time.deltaTime * speed;
        if (_t > endT) _t = loop ? startT : endT;
        if (gate != null) gate.LanbaiTick(_t);
        if (clouds != null) clouds.LanbaiTick(_t);
    }

    // jump (e.g. from the Inspector's U# event button): t = startT
    public void _Restart()
    {
        _t = startT;
    }
}
