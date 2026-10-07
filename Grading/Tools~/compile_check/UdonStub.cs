// Compile-check stub for UdonSharp 1.x + VRC SDK3 (only what LanbaiExposure touches).
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
    public class VRCPlayerApi { public bool IsUserInVR() { return false; } }
    public static class Networking { public static VRCPlayerApi LocalPlayer { get { return null; } } }
    public static class Utilities { public static bool IsValid(object o) { return o != null; } }
}
