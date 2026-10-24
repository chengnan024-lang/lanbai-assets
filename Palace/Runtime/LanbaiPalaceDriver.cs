// =====================================================================================================
//  LanbaiPalaceDriver.cs   蓝白 · 第 7b 幕河伯宫殿的驱动（UdonSharp）
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn + U# rules). !!!
//
//  CONTROL §5 接口（Director/LanbaiActDispatcher 每帧调用）：
//     LanbaiTick(t)        时间窗里每帧一次（t = 时间轴秒）
//     LanbaiActivate(on)   开关 R_Palace（只在遮挡下切；宫殿从 F5 起就在视野里，所以它在 7a 的黑里就开着，海的驱动管 R_Sea）
//     LanbaiWindow()       {F5 − 1, F8 + 40 + 1} = {643.96, 876.16}（圣经 §1.9：宫殿热点一直到 7c 的前 40 秒）
//  只写这些：
//     _Udon_Lamp0..6：离主座位眼睛最近的 7 盏宫灯；_Udon_Lamp7：开着的殿门（竖直线光源，湿石面上的亮带，第 4 轮）
//       （LanbaiPalace.cginc 的解析 GGX 高光；D-24：宫殿全烘焙，铜灯的高光走这里）。时间窗外写 w = 0（关）——只在
//       离开时间窗的那一帧写一次，之后不再碰（D-22：同一时刻只有一个驱动写同一个全局量；第 1、2、11、12 幕的雨 / 路灯
//       在别的时间窗里用同一套名字）。
//     鱼的材质：_Count（lite 700 / 全 1 500）。
//  不写：R_Palace 的位置（它是 R_Sea 的子物体，局部位置是常数，搭建脚本放好）、_Udon_PalaceVeil（海写）、_Udon_T（海写）、
//  PPv2（LB_Journey）、车厢。
//  所有数来自 Palace/PalaceLayout.json，由 蓝白/Build/7b 宫殿（Palace/Editor/LanbaiPalaceBuilder.cs）写进下面的字段。
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiPalaceDriver : UdonSharpBehaviour
{
    [Header("Scene (filled by the builder)")]
    public GameObject rPalace;
    public Transform rPalaceTf;
    public Renderer fish;
    public bool lite = false;                  // Director 的 auto-lite（圣经 §1.9）：鱼 1 500 → 700

    [Header("Timeline")]
    public float windowStart = 643.96f, windowEnd = 876.16f;

    [Header("Lamps (palace frame, from PalaceLayout.json)")]
    public Vector3[] lampLocal;                // 30 盏灯焰中心（R_Palace 的局部坐标）
    public float lampIntensity = 5.46f;        // 与烘焙暖光同一个 I（E = I / d²）
    public Color lampColorLinear = new Color(1.0f, 0.332f, 0.028f, 1f);   // #FF9C2F 线性
    public float lampRadius = 0.10f;
    public Vector3 eyeBusRelative = new Vector3(0.55f, 1.70f, 2.05f);

    [Header("Door as an analytic line lamp (slot 7)")]
    public Vector3 doorLocal;                  // 门洞中心（R_Palace 局部）
    public float doorHalfHeight = 3.75f;       // 竖直线光源的半长（门高 / 2）
    public float doorIntensity = 60f;          // 线光源的 I（湿石面上的高光亮带；第 4 轮，美术评审 r3 #3）
    public Color doorColorLinear = new Color(1.0f, 0.473f, 0.074f, 1f);  // #FFB74D 线性
    public float doorRadius = 0.6f;

    private int[] _idLamp, _idCol, _idDir, _idAxis;
    private int _idCount;
    private bool _wrote;
    private float[] _d2;
    private int[] _pick;
    private MaterialPropertyBlock _mpb;

    void Start()
    {
        _idLamp = new int[8];
        _idCol = new int[8];
        _idDir = new int[8];
        _idAxis = new int[8];
        for (int i = 0; i < 8; i++)
        {
            _idLamp[i] = VRCShader.PropertyToID("_Udon_Lamp" + i);
            _idCol[i] = VRCShader.PropertyToID("_Udon_LampColor" + i);
            _idDir[i] = VRCShader.PropertyToID("_Udon_LampDir" + i);
            _idAxis[i] = VRCShader.PropertyToID("_Udon_LampAxis" + i);
        }
        _idCount = VRCShader.PropertyToID("_Count");
        int n = lampLocal != null ? lampLocal.Length : 0;
        _d2 = new float[n];
        _pick = new int[7];
        _mpb = new MaterialPropertyBlock();
        ApplyLite();
    }

    public float[] LanbaiWindow()
    {
        return new float[] { windowStart, windowEnd };
    }

    public void LanbaiActivate(bool on)
    {
        if (rPalace != null) rPalace.SetActive(on);
    }

    public void ApplyLite()
    {
        if (fish == null) return;
        fish.GetPropertyBlock(_mpb);
        _mpb.SetFloat(_idCount, lite ? 700f : 1500f);
        fish.SetPropertyBlock(_mpb);
    }

    public void LanbaiTick(float t)
    {
        if (t < windowStart || t > windowEnd)
        {
            if (_wrote) LampsOff();
            return;
        }
        if (rPalaceTf == null || lampLocal == null) return;
        int n = lampLocal.Length;
        Vector3 eye = eyeBusRelative;                      // 车在世界原点（跑步机）
        for (int i = 0; i < n; i++)
        {
            Vector3 w = rPalaceTf.TransformPoint(lampLocal[i]);
            _d2[i] = (w - eye).sqrMagnitude;
        }
        // 选最近的 7 盏（第 8 个位子留给门）
        for (int k = 0; k < 7; k++)
        {
            int best = -1;
            float bd = float.MaxValue;
            for (int i = 0; i < n; i++)
            {
                if (_d2[i] < bd)
                {
                    bool used = false;
                    for (int j = 0; j < k; j++) if (_pick[j] == i) used = true;
                    if (!used) { bd = _d2[i]; best = i; }
                }
            }
            _pick[k] = best;
        }
        Vector4 col = new Vector4(lampColorLinear.r, lampColorLinear.g, lampColorLinear.b, lampRadius);
        for (int k = 0; k < 7; k++)
        {
            int i = _pick[k];
            if (i < 0)
            {
                VRCShader.SetGlobalVector(_idLamp[k], Vector4.zero);
                continue;
            }
            Vector3 w = rPalaceTf.TransformPoint(lampLocal[i]);
            VRCShader.SetGlobalVector(_idLamp[k], new Vector4(w.x, w.y, w.z, lampIntensity));
            VRCShader.SetGlobalVector(_idCol[k], col);
            VRCShader.SetGlobalVector(_idDir[k], new Vector4(0f, -1f, 0f, -1f));    // 全向
            VRCShader.SetGlobalVector(_idAxis[k], Vector4.zero);
        }
        Vector3 dw = rPalaceTf.TransformPoint(doorLocal);
        Vector3 ax = rPalaceTf.TransformVector(new Vector3(0f, doorHalfHeight, 0f));
        VRCShader.SetGlobalVector(_idLamp[7], new Vector4(dw.x, dw.y, dw.z, doorIntensity));
        VRCShader.SetGlobalVector(_idCol[7], new Vector4(doorColorLinear.r, doorColorLinear.g, doorColorLinear.b, doorRadius));
        VRCShader.SetGlobalVector(_idDir[7], new Vector4(0f, 0f, -1f, 0f));          // 朝外的半球（cos 0）
        VRCShader.SetGlobalVector(_idAxis[7], new Vector4(ax.x, ax.y, ax.z, 0f));
        _wrote = true;
    }

    private void LampsOff()
    {
        for (int k = 0; k < 8; k++) VRCShader.SetGlobalVector(_idLamp[k], Vector4.zero);
        _wrote = false;
    }
}
