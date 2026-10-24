// Compile-check stub for UdonSharp 1.x + VRChat SDK3 Worlds (only what the 门内 packages touch).
// NOT the SDK: it lets Roslyn type-check our scripts against the real UnityEngine API. Signatures follow SDK 3.x.
using System;
using UnityEngine;
namespace UdonSharp
{
    public abstract class UdonSharpBehaviour : MonoBehaviour
    {
        public virtual void PostLateUpdate() { }
        public virtual void OnPlayerJoined(VRC.SDKBase.VRCPlayerApi p) { }
        public void SendCustomEventDelayedSeconds(string e, float s) { }
    }
    public enum BehaviourSyncMode { Any, None, Continuous, Manual, NoVariableSync }
    [AttributeUsage(AttributeTargets.Class)]
    public sealed class UdonBehaviourSyncModeAttribute : Attribute { public UdonBehaviourSyncModeAttribute(BehaviourSyncMode m) { } }
}
namespace VRC.SDKBase
{
    public class VRCPlayerApi
    {
        public enum TrackingDataType { Head, LeftHand, RightHand, Origin, AvatarRoot }
        public struct TrackingData { public Vector3 position; public Quaternion rotation; }
        public bool isLocal;
        public bool IsUserInVR() { return false; }
        public TrackingData GetTrackingData(TrackingDataType t) { return new TrackingData(); }
        public Vector3 GetPosition() { return Vector3.zero; }
    }
    public static class Networking { public static VRCPlayerApi LocalPlayer { get { return null; } } }
    public static class Utilities { public static bool IsValid(object o) { return o != null; } }
    public static class VRCShader
    {
        public static int PropertyToID(string name) { return 0; }
        public static void SetGlobalFloat(int id, float v) { }
        public static void SetGlobalVector(int id, Vector4 v) { }
        public static void SetGlobalColor(int id, Color v) { }
        public static void SetGlobalTexture(int id, Texture t) { }
    }
}
