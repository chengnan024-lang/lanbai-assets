// =====================================================================================================
//  LanbaiBusSeat   蓝白 · 车 · 座位的“坐下”交互（每个 VRCStation 一个）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (never compiled in Unity). !!!
//  The 23 VRCStations made by 蓝白/Build/车 need an Interact that calls UseStation (review r1 #6). The local v1
//  LB_Seat (FromLocal/code/timeline_v1/LB_Udon.cs) is wired only to the old bus's seats; if you re-point LB_Seat to
//  these stations instead, delete this component (Bus/README.md §1).
//  InteractionText '坐下' and proximity 2 m are set by the build script (same as LB_Seat).
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiBusSeat : UdonSharpBehaviour
{
    public VRCStation station;          // VRC.SDKBase.VRCStation (the SDK3 component derives from it)

    public override void Interact()
    {
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (station == null || lp == null) return;
        station.UseStation(lp);
    }
}
