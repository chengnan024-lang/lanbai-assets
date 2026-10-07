// =====================================================================================================
//  LanbaiLamps.cs        蓝白 · publishes the 8 analytic lamps (bible §1.6 "_Udon_Lamp0..7") to every shader
//
//  !!! UNCOMPILED IN UNITY. Type-checked with Roslyn (C# 9) against the Unity 2021.1 UnityEngine reference
//      assembly and a stub of UdonSharp / VRC.SDKBase (Tools~/compile_check/UdonStub.cs). The implementer
//      compiles it with UdonSharp 1.x in Unity 2022.3 + VRChat SDK Worlds. !!!
//
//  One instance in the world, LOCAL (no sync). Each slot = a Transform (+ numbers). Globals written per slot:
//    _Udon_Lamp{i}       = (world position, intensity * gain)          w <= 0 : off
//    _Udon_LampColor{i}  = (linear colour, source radius)
//    _Udon_LampAxis{i}   = (transform.right * halfLength, 0)            tubes lie along the Transform's local X
//    _Udon_LampDir{i}    = (emission axis, cos of the cone half-angle)  axis = local -Y (emitAxis 0) or +Z (1)
//  Suggested slots at the stop (bible §6·1 "8 个解析 GGX 灯"): 0 stop tube, 1-2 headlights, 3-4 tail lights,
//  5 door light, 6-7 the two lit window strips. On the night road Udon moves slots 0, 5-7 to the nearest
//  sodium lamps (bible §6·2) - just move the Transforms; this script re-publishes every frame.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiLamps : UdonSharpBehaviour
{
    [Tooltip("Up to 8 lamps. Empty slot = off. Tube lamps: the tube runs along the Transform's local X.")]
    public Transform[] lamps = new Transform[8];

    [Tooltip("I: E = I / d^2 (Unity light units, the bible's E). Stop tube: E 1.0 on the road 3.9 m below -> 15.")]
    public float[] intensity = new float[] { 15f, 4f, 4f, 0.6f, 0.6f, 2f, 1.5f, 1.5f };

    [Tooltip("Colour as picked (sRGB). Stop tube / cabin #E4F1F3, headlight #FFC47A, tail light #CB1500.")]
    public Color[] colour = new Color[]
    {
        new Color(0.894f, 0.945f, 0.953f), new Color(1f, 0.769f, 0.478f), new Color(1f, 0.769f, 0.478f),
        new Color(0.796f, 0.082f, 0f), new Color(0.796f, 0.082f, 0f), new Color(0.894f, 0.945f, 0.953f),
        new Color(0.788f, 0.863f, 0.878f), new Color(0.788f, 0.863f, 0.878f)
    };

    [Tooltip("Source radius (m): widens the highlight. Tube 0.013, headlight 0.08, tail light 0.05, window 0.3.")]
    public float[] radius = new float[] { 0.013f, 0.08f, 0.08f, 0.05f, 0.05f, 0.25f, 0.3f, 0.3f };

    [Tooltip("Half-length (m) of a line source along local X. Tube 0.6; points 0.")]
    public float[] halfLength = new float[] { 0.6f, 0f, 0f, 0f, 0f, 0f, 0.9f, 0.9f };

    [Tooltip("Cosine of the cone half-angle; -1 = omni. Trough reflector 0.05, headlight 0.954.")]
    public float[] coneCos = new float[] { 0.05f, 0.954f, 0.954f, 0.2f, 0.2f, 0.0f, 0.0f, 0.0f };

    [Tooltip("Emission axis: 0 = the Transform's local -Y (trough, door light), 1 = local +Z (headlights, tail lights, windows).")]
    public int[] emitAxis = new int[] { 0, 1, 1, 1, 1, 0, 1, 1 };

    [Tooltip("Runtime multipliers (fades, headlights off in some scenes). The Director may write these.")]
    public float[] gain = new float[] { 1f, 1f, 1f, 1f, 1f, 1f, 1f, 1f };

    [Tooltip("Re-publish every frame (needed when lamps move: headlights, the night road). Off = once at Start.")]
    public bool everyFrame = true;

    private int[] _idPos;
    private int[] _idCol;
    private int[] _idAxis;
    private int[] _idDir;
    private bool _ready;

    private void Start()
    {
        Init();
        Push();
    }

    private void Update()
    {
        if (everyFrame) Push();
    }

    private void Init()
    {
        _idPos = new int[8];
        _idCol = new int[8];
        _idAxis = new int[8];
        _idDir = new int[8];
        for (int i = 0; i < 8; i++)
        {
            _idPos[i] = VRCShader.PropertyToID("_Udon_Lamp" + i);
            _idCol[i] = VRCShader.PropertyToID("_Udon_LampColor" + i);
            _idAxis[i] = VRCShader.PropertyToID("_Udon_LampAxis" + i);
            _idDir[i] = VRCShader.PropertyToID("_Udon_LampDir" + i);
        }
        _ready = true;
    }

    private float GetF(float[] a, int i, float def)
    {
        if (a == null || i >= a.Length) return def;
        return a[i];
    }

    private float SrgbToLinear(float c)
    {
        if (c <= 0.04045f) return c / 12.92f;
        return Mathf.Pow((c + 0.055f) / 1.055f, 2.4f);
    }

    /// <summary>Write all 8 slots now (also callable from the Director after moving lamps).</summary>
    public void Push()
    {
        if (!_ready) Init();
        for (int i = 0; i < 8; i++)
        {
            Transform t = null;
            if (lamps != null && i < lamps.Length) t = lamps[i];
            float g = GetF(gain, i, 1f);
            if (t == null || !t.gameObject.activeInHierarchy || g <= 0f)
            {
                VRCShader.SetGlobalVector(_idPos[i], Vector4.zero);
                continue;
            }
            Vector3 p = t.position;
            VRCShader.SetGlobalVector(_idPos[i], new Vector4(p.x, p.y, p.z, GetF(intensity, i, 1f) * g));

            Color c = Color.white;
            if (colour != null && i < colour.Length) c = colour[i];
            VRCShader.SetGlobalVector(_idCol[i], new Vector4(SrgbToLinear(c.r), SrgbToLinear(c.g), SrgbToLinear(c.b), GetF(radius, i, 0.02f)));

            Vector3 ax = t.right * GetF(halfLength, i, 0f);
            VRCShader.SetGlobalVector(_idAxis[i], new Vector4(ax.x, ax.y, ax.z, 0f));

            int mode = 0;
            if (emitAxis != null && i < emitAxis.Length) mode = emitAxis[i];
            Vector3 d = mode == 1 ? t.forward : -t.up;
            VRCShader.SetGlobalVector(_idDir[i], new Vector4(d.x, d.y, d.z, GetF(coneCos, i, -1f)));
        }
    }
}
