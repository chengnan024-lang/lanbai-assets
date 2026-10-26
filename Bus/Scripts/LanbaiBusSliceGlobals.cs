// =====================================================================================================
//  LanbaiBusSliceGlobals   蓝白 · 车 · 切片场景里的车厢全局量（D-40 #1，菜单 蓝白/Build/车 切片 挂上它）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (never compiled or run in Unity). Roslyn type-check only. !!!
//  In the world, LanbaiCabinDriver (U#) writes the cabin globals every frame. The slice is a local test scene with no
//  driver, so Lanbai/Cabin would read 0 for _Udon_CabinLightmap (tubes off: black cabin). This plain MonoBehaviour
//  (NOT UdonSharp; the slice scene is never uploaded) writes the same globals, with the same types as the driver
//  (Common/UdonGlobals.md): the float with SetGlobalFloat, the float4s with SetGlobalVector (linear, no gamma step).
//  Defaults = the night road, t = 30: tubes 1, cabin ambient 0, no bleach, no erosion, no crossing band.
//  Do not put it in the world scene: it would fight LanbaiCabinDriver every frame (and VRChat strips it on upload).
// =====================================================================================================
using UnityEngine;

[ExecuteAlways]
[DisallowMultipleComponent]
public class LanbaiBusSliceGlobals : MonoBehaviour
{
    [Tooltip("_Udon_CabinLightmap: the tube multiplier on _CabinTubeLM (1 = tubes on, acts 1-4 and 11-12)")]
    public float tubes = 1f;

    [Tooltip("_Udon_CabinAmbient.rgb, LINEAR (a is written as 1). 0 = night road; act 6 dawn = #98A4B8 x 0.5 = (0.157, 0.186, 0.239)")]
    public Vector3 ambientLinear = Vector3.zero;

    [Tooltip("_Udon_CabinBleach.x (bible 4.8), keep 0 for the slice")]
    [Range(0f, 1f)] public float bleach = 0f;

    [Tooltip("_Udon_CabinFade.x: erosion (bible 4.8), keep 0 for the slice")]
    [Range(0f, 1f)] public float fade = 0f;

    private static int _idLightmap, _idAmbient, _idBleach, _idFade, _idSlice, _idSliceColor;
    private static bool _ids;

    private void OnEnable() { Apply(); }

    private void Update() { Apply(); }          // six globals: cheap; keeps them if anything else wrote over them

    private void OnValidate() { Apply(); }

    /// <summary>Writes the cabin globals now (the build menu calls it once right after adding the component).</summary>
    public void Apply()
    {
        if (!_ids)
        {
            _idLightmap = Shader.PropertyToID("_Udon_CabinLightmap");
            _idAmbient = Shader.PropertyToID("_Udon_CabinAmbient");
            _idBleach = Shader.PropertyToID("_Udon_CabinBleach");
            _idFade = Shader.PropertyToID("_Udon_CabinFade");
            _idSlice = Shader.PropertyToID("_Udon_CabinSlice");
            _idSliceColor = Shader.PropertyToID("_Udon_CabinSliceColor");
            _ids = true;
        }
        Shader.SetGlobalFloat(_idLightmap, tubes);
        Shader.SetGlobalVector(_idAmbient, new Vector4(ambientLinear.x, ambientLinear.y, ambientLinear.z, 1f));
        Shader.SetGlobalVector(_idBleach, new Vector4(bleach, 0f, 0f, 1f));            // float4: .x read, w = 1 'set'
        Shader.SetGlobalVector(_idFade, new Vector4(fade, 0f, 0f, 1f));
        // the crossing bands off, as LanbaiCabinDriver starts them outside the inside window
        Shader.SetGlobalVector(_idSlice, new Vector4(0f, 1.5f, 3f, 0f));
        Shader.SetGlobalVector(_idSliceColor, Vector4.zero);
    }
}
