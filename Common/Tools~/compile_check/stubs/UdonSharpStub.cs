// Compile-check stub of UdonSharp 1.x (the copy bundled with VRChat SDK Worlds 3.10.x): assembly UdonSharp.Runtime.
// It is NOT UdonSharp: it lets Roslyn type-check a script as plain C#. U# compiles a SUBSET of C# to Udon assembly,
// and only members on the Udon exposure whitelist can be called; neither is checked by a C# compile (see the U# lint in
// lib/cs_check.py for the few rules that are checked, and README_compile_check.md for what is not).
// Merged from Grading/ and Rain/ Tools~/compile_check/UdonStub.cs (2026-10-22); event list after UdonSharpBehaviour.cs.
using System;
using UnityEngine;
using VRC.SDKBase;
using VRC.Udon.Common;
using VRC.Udon.Common.Enums;
using VRC.Udon.Common.Interfaces;

namespace UdonSharp
{
    public enum BehaviourSyncMode { Any, None, Continuous, Manual, NoVariableSync }
    public enum UdonSyncMode { NotSynced, None, Linear, Smooth }

    [AttributeUsage(AttributeTargets.Class)]
    public sealed class UdonBehaviourSyncModeAttribute : Attribute
    {
        public BehaviourSyncMode behaviourSyncMode;
        public UdonBehaviourSyncModeAttribute(BehaviourSyncMode behaviourSyncMode) { this.behaviourSyncMode = behaviourSyncMode; }
    }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class UdonSyncedAttribute : Attribute
    {
        public UdonSyncedAttribute(UdonSyncMode networkSyncTypeIn = UdonSyncMode.None) { }
    }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class FieldChangeCallbackAttribute : Attribute
    {
        public string CallbackPropertyName { get; }
        public FieldChangeCallbackAttribute(string targetPropertyName) { CallbackPropertyName = targetPropertyName; }
    }

    [AttributeUsage(AttributeTargets.Method)]
    public sealed class RecursiveMethodAttribute : Attribute { }

    public abstract class UdonSharpBehaviour : MonoBehaviour
    {
        // ---- talking to other behaviours / the network
        public void SetProgramVariable(string name, object value) { }
        public object GetProgramVariable(string name) { return null; }
        public void SendCustomEvent(string eventName) { }
        public void SendCustomNetworkEvent(NetworkEventTarget target, string eventName) { }
        public void SendCustomEventDelayedSeconds(string eventName, float delaySeconds, EventTiming eventTiming = EventTiming.Update) { }
        public void SendCustomEventDelayedFrames(string eventName, int delayFrames, EventTiming eventTiming = EventTiming.Update) { }
        public void RequestSerialization() { }
        public bool DisableInteractive { get { return false; } set { } }
        public string InteractionText { get { return null; } set { } }

        // ---- Udon events (override in the behaviour)
        public virtual void Interact() { }
        public virtual void PostLateUpdate() { }
        public virtual void OnPreSerialization() { }
        public virtual void OnDeserialization() { }
        public virtual void OnPostSerialization(SerializationResult result) { }
        public virtual void OnPlayerJoined(VRCPlayerApi player) { }
        public virtual void OnPlayerLeft(VRCPlayerApi player) { }
        public virtual void OnPlayerRespawn(VRCPlayerApi player) { }
        public virtual void OnOwnershipTransferred(VRCPlayerApi player) { }
        public virtual bool OnOwnershipRequest(VRCPlayerApi requestingPlayer, VRCPlayerApi requestedOwner) { return true; }
        public virtual void OnPlayerTriggerEnter(VRCPlayerApi player) { }
        public virtual void OnPlayerTriggerStay(VRCPlayerApi player) { }
        public virtual void OnPlayerTriggerExit(VRCPlayerApi player) { }
        public virtual void OnPlayerCollisionEnter(VRCPlayerApi player) { }
        public virtual void OnPlayerCollisionStay(VRCPlayerApi player) { }
        public virtual void OnPlayerCollisionExit(VRCPlayerApi player) { }
        public virtual void OnStationEntered(VRCPlayerApi player) { }
        public virtual void OnStationExited(VRCPlayerApi player) { }
        public virtual void OnPickup() { }
        public virtual void OnDrop() { }
        public virtual void OnPickupUseDown() { }
        public virtual void OnPickupUseUp() { }
        public virtual void OnVideoStart() { }
        public virtual void OnVideoEnd() { }
        public virtual void OnVideoReady() { }
        // SDK 3.7+ localisation event (local's LB_Journey overrides it and compiles with SDK Worlds 3.10.5)
        public virtual void OnLanguageChanged(string language) { }
    }
}
