// Compile-check stub for UdonSharp 1.x + VRChat SDK3 Worlds (only what the Rain kit touches).
// It is NOT the SDK: it lets Roslyn type-check the kit against the real UnityEngine API.
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
    }
}
