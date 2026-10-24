// Compile-check stub of the VRChat SDK3 Worlds (3.10.x) types Lanbai scripts touch: VRC.SDKBase (VRCShader, Networking,
// VRCPlayerApi, Utilities) and VRC.Udon (UdonBehaviour, NetworkEventTarget, EventTiming).
// It is NOT the SDK: names and signatures follow the public VRChat docs / SDK; bodies are fake. Passing against it proves
// the C# is well-typed against THESE declarations only - it does not prove Udon exposes the member (check the Class
// Exposure Tree in Unity once for anything new). Anything not declared here fails the check on purpose: add it here
// (with the real signature) only after confirming it in the SDK.
// Merged from Grading/Tools~/compile_check/UdonStub.cs and Rain/Tools~/compile_check/UdonStub.cs (2026-10-22).
using System;
using UnityEngine;

namespace VRC.Udon.Common.Interfaces
{
    public enum NetworkEventTarget { All = 0, Owner = 1, Self = 2, Others = 3 }
}

namespace VRC.Udon.Common.Enums
{
    public enum EventTiming { Update = 0, LateUpdate = 1 }
}

namespace VRC.Udon.Common
{
    public struct SerializationResult
    {
        public bool success;
        public int byteCount;
        public SerializationResult(bool success, int byteCount) { this.success = success; this.byteCount = byteCount; }
    }
}

namespace VRC.Udon
{
    // The component that runs a compiled program (what an UdonSharpBehaviour becomes at runtime).
    public class UdonBehaviour : MonoBehaviour
    {
        public void SendCustomEvent(string eventName) { }
        public void SendCustomNetworkEvent(VRC.Udon.Common.Interfaces.NetworkEventTarget target, string eventName) { }
        public void SendCustomEventDelayedSeconds(string eventName, float delaySeconds, VRC.Udon.Common.Enums.EventTiming eventTiming = VRC.Udon.Common.Enums.EventTiming.Update) { }
        public void SendCustomEventDelayedFrames(string eventName, int delayFrames, VRC.Udon.Common.Enums.EventTiming eventTiming = VRC.Udon.Common.Enums.EventTiming.Update) { }
        public void SetProgramVariable(string symbolName, object value) { }
        public object GetProgramVariable(string symbolName) { return null; }
        public void RequestSerialization() { }
        public bool DisableInteractive { get { return false; } set { } }
        public string InteractionText { get { return null; } set { } }
    }
}

namespace VRC.SDKBase
{
    // Global shader properties from Udon. VRChat only lets Udon write names that start with "_Udon"
    // (Lanbai convention: "_Udon_" + an entry in Common/UdonGlobals.md).
    public static class VRCShader
    {
        public static int PropertyToID(string name) { return 0; }
        public static void SetGlobalFloat(int nameID, float value) { }
        public static void SetGlobalInteger(int nameID, int value) { }
        public static void SetGlobalVector(int nameID, Vector4 value) { }
        public static void SetGlobalColor(int nameID, Color value) { }
        public static void SetGlobalMatrix(int nameID, Matrix4x4 value) { }
        public static void SetGlobalTexture(int nameID, Texture value) { }
        // array setters deliberately not stubbed until checked against the SDK
    }

    public class VRCPlayerApi
    {
        public enum TrackingDataType { Head = 0, LeftHand = 1, RightHand = 2, Origin = 3, AvatarRoot = 4 }
        public struct TrackingData
        {
            public Vector3 position;
            public Quaternion rotation;
            public TrackingData(Vector3 position, Quaternion rotation) { this.position = position; this.rotation = rotation; }
        }
        public string displayName;
        public int playerId;
        public bool isLocal;
        public bool isMaster;
        public bool IsValid() { return true; }
        public static bool IsValid(VRCPlayerApi player) { return player != null; }
        public bool IsUserInVR() { return false; }
        public bool IsOwner(GameObject obj) { return false; }
        public Vector3 GetPosition() { return Vector3.zero; }
        public Quaternion GetRotation() { return Quaternion.identity; }
        public Vector3 GetVelocity() { return Vector3.zero; }
        public Vector3 GetBonePosition(HumanBodyBones tgt) { return Vector3.zero; }
        public Quaternion GetBoneRotation(HumanBodyBones tgt) { return Quaternion.identity; }
        public TrackingData GetTrackingData(TrackingDataType tt) { return new TrackingData(); }
        public void TeleportTo(Vector3 teleportPos, Quaternion teleportRot) { }
        public void Immobilize(bool immobile) { }
        public void SetWalkSpeed(float speed) { }
        public void SetRunSpeed(float speed) { }
        public void SetStrafeSpeed(float speed) { }
        public void SetJumpImpulse(float impulse) { }
        public void SetGravityStrength(float strength) { }
        public float GetAvatarEyeHeightAsMeters() { return 1.6f; }
        public static VRCPlayerApi GetPlayerById(int playerId) { return null; }
        // SDK 3.2.3+ (RFC 5646 codes since client 2024.1.1): creators.vrchat.com/worlds/udon/players/#language
        public static string GetCurrentLanguage() { return "en"; }
        public static string[] GetAvailableLanguages() { return new string[] { "en" }; }
        public static int GetPlayerCount() { return 1; }
        public static VRCPlayerApi[] GetPlayers(VRCPlayerApi[] players) { return players; }
    }

    public static class Networking
    {
        public static VRCPlayerApi LocalPlayer { get { return null; } }
        public static bool IsMaster { get { return true; } }
        public static bool IsClogged { get { return false; } }
        public static bool IsNetworkSettled { get { return true; } }
        public static bool IsOwner(GameObject obj) { return true; }
        public static bool IsOwner(VRCPlayerApi player, GameObject obj) { return true; }
        public static VRCPlayerApi GetOwner(GameObject obj) { return null; }
        public static void SetOwner(VRCPlayerApi player, GameObject obj) { }
        public static double GetServerTimeInSeconds() { return 0.0; }
        public static int GetServerTimeInMilliseconds() { return 0; }
        public static double CalculateServerDeltaTime(double timeInSeconds, double previousTimeInSeconds) { return 0.0; }
    }

    public static class Utilities
    {
        public static bool IsValid(object obj) { return obj != null; }
    }
}
