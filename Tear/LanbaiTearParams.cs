// =====================================================================================================
//  LanbaiTearParams.cs   蓝白 · 裂口套件的 Udon 参数（UdonSharp）
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). UNCOMPILED. !!!
//
//  The four globals Lanbai_Tear.shader reads. The Director (LanbaiDirector.cs) owns the timeline and should
//  simply write these fields (or call SetTear) every frame during scene 4; this component only pushes them to
//  the GPU. Globals must carry the _Udon_ prefix in VRChat.
//
//    tearOpen     0..1  lens width 18 % -> 30 % of H     U6 = 0, U7 = 0.333, U8 and later = 1  (smoothstep between)
//    ripProgress  0..1  the two branch rips              0 before U7, then 0 -> 1 in ~16 s (rip A opens over 0..0.75,
//                                                        rip B over 0.25..1: ~12 s each, staggered; <= 0.5 deg/s)
//    tearHide     0..1  0 = visible, 1 = gone            fade 1 -> 0 at U6 (an unset global reads 0 = visible)
//    breathPhase -1..1  optional                         leave 0: the halo breathes by itself (+-0.25 EV, 8 s)
//
//  The kit's SIZE and PLACE are transforms, not shader globals: Tear_Root uniform scale = H(t) / 1000 with H(t) the
//  monotone PCHIP through gate/GateLayout_v2.json timeline.tear_H_knots (U6 565, U7 616, U7b 640, 160.5 s 715,
//  U8 799, U9 1000 m; the gate is the authority, not the bible's 875 at U8), and its position = the tear foot on the
//  cloud top, a child of GateRoot (gate/README_GateLayout.md §2.2).
//  v5 (gate round 4): the gate ALSO writes _Udon_GateOrigin (GateRoot.position: the foot fade's noise lives in the
//  cloud-sea frame) and the fades in GateLayout_v2.json tear.fades; neither is this component's job.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiTearParams : UdonSharpBehaviour
{
    [Range(0f, 1f)] public float tearOpen = 0f;
    [Range(0f, 1f)] public float ripProgress = 0f;
    [Range(0f, 1f)] public float tearHide = 1f;
    [Range(-1f, 1f)] public float breathPhase = 0f;

    private int _idOpen, _idRip, _idHide, _idBreath;

    private void Start()
    {
        _idOpen = VRCShader.PropertyToID("_Udon_TearOpen");
        _idRip = VRCShader.PropertyToID("_Udon_RipProgress");
        _idHide = VRCShader.PropertyToID("_Udon_TearHide");
        _idBreath = VRCShader.PropertyToID("_Udon_TearBreath");
        Push();
    }

    public void SetTear(float open01, float rip01, float hide01)
    {
        tearOpen = open01; ripProgress = rip01; tearHide = hide01;
    }

    private void Update()
    {
        Push();
    }

    private void Push()
    {
        VRCShader.SetGlobalFloat(_idOpen, Mathf.Clamp01(tearOpen));
        VRCShader.SetGlobalFloat(_idRip, Mathf.Clamp01(ripProgress));
        VRCShader.SetGlobalFloat(_idHide, Mathf.Clamp01(tearHide));
        VRCShader.SetGlobalFloat(_idBreath, Mathf.Clamp(breathPhase, -1f, 1f));
    }
}
