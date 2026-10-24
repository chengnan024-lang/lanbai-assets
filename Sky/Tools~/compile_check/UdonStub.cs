// Compile-check stub for UdonSharp 1.x + VRChat SDK3 Worlds (only what the Sky package touches). NOT the SDK.
using System;
using UnityEngine;
namespace UdonSharp
{
    public abstract class UdonSharpBehaviour : MonoBehaviour { }
    public enum BehaviourSyncMode { Any, None, Continuous, Manual, NoVariableSync }
    [AttributeUsage(AttributeTargets.Class)]
    public sealed class UdonBehaviourSyncModeAttribute : Attribute { public UdonBehaviourSyncModeAttribute(BehaviourSyncMode m) { } }
}
namespace VRC.SDKBase
{
    public static class VRCShader
    {
        public static int PropertyToID(string name) { return 0; }
        public static void SetGlobalFloat(int id, float v) { }
        public static void SetGlobalVector(int id, Vector4 v) { }
        public static void SetGlobalColor(int id, Color v) { }
        public static void SetGlobalTexture(int id, Texture v) { }
    }
    public class VRCPlayerApi { public bool IsUserInVR() { return false; } }
    public static class Networking { public static VRCPlayerApi LocalPlayer { get { return null; } } }
    public static class Utilities { public static bool IsValid(object o) { return o != null; } }
}
