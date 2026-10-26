// 蓝白 · 座位：点一下坐下（车上的每个座位、站牌下的长椅）
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using VRCStation = VRC.SDK3.Components.VRCStation;

namespace Lanbai
{
    [UdonBehaviourSyncMode(BehaviourSyncMode.Manual)]
    public class LB_Seat : UdonSharpBehaviour
    {
        public VRCStation station;
        public LanbaiPoemDriver poemDriver;
        public int poemSeatIndex;
        public override void OnStationEntered(VRCPlayerApi player) {
            if (player != null && player.isLocal && poemDriver != null) poemDriver.SetSeat(poemSeatIndex);
        }

        public override void OnStationExited(VRCPlayerApi player) {
            if (player != null && player.isLocal && poemDriver != null) poemDriver.SetSeat(-1);
        }

        public override void Interact()
        {
            if (station != null) station.UseStation(Networking.LocalPlayer);
        }
    }
}
