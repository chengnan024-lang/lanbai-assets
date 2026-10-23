// Lanbai / 蓝白 -- LanbaiOverlay: the full-field fade sphere v2 (ART BIBLE v2.1 §1.8, E17; calib_final §D).
//
// UdonSharp 1.x. UNCOMPILED (cloud side): type-checked with Roslyn against UnityEngine 2021.1 + an UdonSharp / VRC stub.
// That proves C# syntax and types only, not the Udon extern whitelist: check VRCPlayerApi.GetTrackingData,
// VRCShader.SetGlobalVector and Renderer.enabled in the Class Exposure Tree once.
//
// ONE per scene, local only (BehaviourSyncMode.None): every client draws its own sphere at its own head.
//   * PostLateUpdate: transform.position = local player's head position (position only, rotation never changes).
//     No player (editor without ClientSim): the sphere stays where it is (put it at the hero eye in the scene).
//   * Act drivers call ONE of the Set* methods per frame while they own the overlay (the Director's time windows decide
//     who owns it; nobody calls it outside a window, so the last call stands). Hide() when done.
//   * Fills are calib §D values (linear). The caller passes the dEV the EXPO helpers APPLY this frame
//     (LanbaiExposure.SetDeltaEV returns it); this script multiplies the fill by 2^(-dEV) (OverlayFillScale).
//
//   SetFlat(fill, alpha, dEV)                                   one alpha for every direction
//   SetCurve(fill, dEV, tau, T, Lfrom, Lto, Lscene, Lover)      EvOverlayAlpha(saturate((tau - lead(dir)) / T), ...)
//   SetLobe(i, worldDir, halfAngleDeg, lead) / SetLeadElse(lead, softDeg) / ClearLobes()
//                                                               per-direction start offsets of the ONE curve
//   SetBreath(amount)                                           act 10's white: 0.02 (+-2 %, 0.1 Hz)
//   PickFill(desktop, vr)                                       IsUserInVR() ? vr : desktop
//   static EvOverlayAlpha(x, Lfrom, Lto, Ls, Lo)                lens_tech.md appendix A (floor 0.004)
//   static float LumOfHex... not needed: callers pass relative luminance (APL luma -> L = (luma / 255)^2.2)
//
// The renderer is disabled whenever nothing is drawn (flat alpha 0, or Hide()), so it costs nothing outside the
// fades. In CURVE mode the renderer stays on (directions can differ); the caller Hide()s when the curve is over.

using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiOverlay : UdonSharpBehaviour
{
    public const float Floor = 0.004f;
    public const float MinSoftDeg = 30f;

    [Tooltip("The sphere's MeshRenderer (Unity built-in Sphere, scale 3 = r 1.5 m, material M_Overlay_Lanbai).")]
    public Renderer sphere;
    [Tooltip("Follow the local player's head every frame (off only for editor tests).")]
    public bool followHead = true;

    private int _idColor, _idCurve, _idLum, _idLobe0, _idLobe1, _idLobe2, _idLobe3, _idLead, _idLeadElse;
    private Vector4[] _lobes = new Vector4[4];
    private float[] _leads = new float[4];
    private float _leadElse = 0f, _softDeg = MinSoftDeg, _breath = 0f;
    private bool _ready;
    private VRCPlayerApi _local;

    private bool _written;                       // somebody has set the overlay since load

    void Start()
    {
        Init();
        // 总导演终审 #9: no unconditional Hide() (an act that set the overlay before this Start, e.g. the spawn black,
        // must keep it); only switch the sphere off if nobody has written yet
        if (!_written && sphere != null) sphere.enabled = false;
    }

    private void Init()
    {
        if (_ready) return;
        _idColor = VRCShader.PropertyToID("_Udon_OverlayColor");
        _idCurve = VRCShader.PropertyToID("_Udon_OverlayCurve");
        _idLum = VRCShader.PropertyToID("_Udon_OverlayLum");
        _idLobe0 = VRCShader.PropertyToID("_Udon_OverlayLobe0");
        _idLobe1 = VRCShader.PropertyToID("_Udon_OverlayLobe1");
        _idLobe2 = VRCShader.PropertyToID("_Udon_OverlayLobe2");
        _idLobe3 = VRCShader.PropertyToID("_Udon_OverlayLobe3");
        _idLead = VRCShader.PropertyToID("_Udon_OverlayLead");
        _idLeadElse = VRCShader.PropertyToID("_Udon_OverlayLeadElse");
        _local = Networking.LocalPlayer;
        if (sphere == null) sphere = GetComponent<Renderer>();
        _ready = true;
        WriteLobes();
    }

    public override void PostLateUpdate()
    {
        if (!followHead) return;
        if (_local == null) _local = Networking.LocalPlayer;
        if (_local == null || !Utilities.IsValid(_local)) return;
        transform.position = _local.GetTrackingData(VRCPlayerApi.TrackingDataType.Head).position;
        transform.rotation = Quaternion.identity;
    }

    // ------------------------------------------------------------------------------------------------ maths
    public static float EvOverlayAlpha(float x, float Lfrom, float Lto, float Ls, float Lo)
    {
        float a = Mathf.Max(Lfrom, Floor);
        float b = Mathf.Max(Lto, Floor);
        float L = a * Mathf.Pow(b / a, Mathf.Clamp01(x));
        float den = Ls - Lo;
        if (Mathf.Abs(den) < 1e-6f) return 1f;
        return Mathf.Clamp01((Ls - L) / den);
    }

    /// <summary>2^(-dEV): the overlay is graded after it is drawn, so its fill must undo the EXPO helpers.</summary>
    public static float FillScale(float appliedDeltaEV)
    {
        return Mathf.Pow(2f, -appliedDeltaEV);
    }

    /// <summary>Time a per-direction curve needs so its fastest view direction stays at 0.85 EV/s (bible E17):
    /// T = log2(L_extreme / 0.004) / 0.85.</summary>
    public static float DurationForExtreme(float Lextreme)
    {
        return Mathf.Log(Mathf.Max(Lextreme, Floor) / Floor, 2f) / 0.85f;
    }

    public Color PickFill(Color desktop, Color vr)
    {
        if (_local == null) _local = Networking.LocalPlayer;
        bool isVR = _local != null && Utilities.IsValid(_local) && _local.IsUserInVR();
        return isVR ? vr : desktop;
    }

    // ------------------------------------------------------------------------------------------------ drawing
    public void SetFlat(Color fillLinear, float alpha, float appliedDeltaEV)
    {
        Init();
        _written = true;
        float k = FillScale(appliedDeltaEV);
        float a = Mathf.Clamp01(alpha);
        VRCShader.SetGlobalVector(_idColor, new Vector4(fillLinear.r * k, fillLinear.g * k, fillLinear.b * k, a));
        VRCShader.SetGlobalVector(_idCurve, new Vector4(0f, 1f, 0f, _breath));
        if (sphere != null) sphere.enabled = a > 0f;
    }

    public void SetCurve(Color fillLinear, float appliedDeltaEV, float tau, float T, float Lfrom, float Lto, float Lscene, float Lover)
    {
        Init();
        _written = true;
        float k = FillScale(appliedDeltaEV);
        VRCShader.SetGlobalVector(_idColor, new Vector4(fillLinear.r * k, fillLinear.g * k, fillLinear.b * k, 1f));
        VRCShader.SetGlobalVector(_idCurve, new Vector4(tau, Mathf.Max(T, 1e-3f), 1f, _breath));
        VRCShader.SetGlobalVector(_idLum, new Vector4(Lfrom, Lto, Lscene, Lover));
        if (sphere != null) sphere.enabled = true;
    }

    public void SetLobe(int i, Vector3 worldDir, float halfAngleDeg, float leadSeconds)
    {
        Init();
        if (i < 0 || i > 3) return;
        Vector3 d = worldDir.sqrMagnitude > 1e-8f ? worldDir.normalized : Vector3.up;
        _lobes[i] = new Vector4(d.x, d.y, d.z, halfAngleDeg);
        _leads[i] = leadSeconds;
        WriteLobes();
    }

    public void SetLeadElse(float leadSeconds, float softDeg)
    {
        Init();
        _leadElse = leadSeconds;
        _softDeg = Mathf.Max(softDeg, MinSoftDeg);
        WriteLobes();
    }

    public void ClearLobes()
    {
        Init();
        for (int i = 0; i < 4; i++) { _lobes[i] = new Vector4(0f, 1f, 0f, 0f); _leads[i] = 0f; }
        _leadElse = 0f;
        _softDeg = MinSoftDeg;
        WriteLobes();
    }

    public void SetBreath(float amount)
    {
        _breath = Mathf.Clamp(amount, 0f, 0.05f);
    }

    public void Hide()
    {
        Init();
        ClearLobes();                            // 总导演终审 #9: the next owner starts without this one's lobes / leads
        VRCShader.SetGlobalVector(_idColor, new Vector4(0f, 0f, 0f, 0f));
        VRCShader.SetGlobalVector(_idCurve, new Vector4(0f, 1f, 0f, 0f));
        _breath = 0f;
        if (sphere != null) sphere.enabled = false;
    }

    private void WriteLobes()
    {
        VRCShader.SetGlobalVector(_idLobe0, _lobes[0]);
        VRCShader.SetGlobalVector(_idLobe1, _lobes[1]);
        VRCShader.SetGlobalVector(_idLobe2, _lobes[2]);
        VRCShader.SetGlobalVector(_idLobe3, _lobes[3]);
        VRCShader.SetGlobalVector(_idLead, new Vector4(_leads[0], _leads[1], _leads[2], _leads[3]));
        VRCShader.SetGlobalVector(_idLeadElse, new Vector4(_leadElse, _softDeg, 0f, 0f));
    }
}
