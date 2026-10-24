// 蓝白 · Director · 每幕的反射立方图烘焙器（bible §1.6 “反射”、§8.1 #14）。v1, 2026-10-23, 总工程师。
// !!! NOT COMPILED IN UNITY: Roslyn type-check only (Common/Tools~/compile_check). !!!
//
// 菜单 蓝白/Director/Bake Reflection Cubes：按 Director/ReflectionBakes.json 每一条烘一张立方图：
//   1. 把时间轴拨到 t：场景里每个驱动（LanbaiTick / LanbaiActivate / LanbaiWindow，见 LanbaiDirectorGen）调一次
//      LanbaiActivate(true) + LanbaiTick(t)；窗口不含 t 的驱动 LanbaiActivate(false)。驱动的 Start() 在编辑模式下不会跑，
//      若驱动有 public void EditorApply() 就先调它（写 MPB / 全局量的那部分：建议每个包把 Start() 里的写入挪进一个
//      EditorApply() 并在 Start() 里调它）。
//   2. 临时相机：位置 = 车局部坐标的 eye（车在原点），HDR、无 PostProcessLayer（立方图要场景线性）、远裁剪 45 000 m、
//      cullingMask 去掉 excludeLayers（车、玩家、UI……），可选 hideSunDisc（_Udon_SunDisc 的增益暂时清零：太阳的闪光交给
//      海 / 镜子 shader 的解析项，见 pkg/sea 的意见第 5 条）。Camera.RenderToCubemap 进一张 ARGBHalf 的立方 RenderTexture。
//   3. 6 个面读回 → 一张 6×1 横条的 EXR（RGBAHalf）→ 导入成 Cube（BC6H、sRGB 关、mip 开、Clamp、三线性），存到 output。
//   4. 把所有全局量 / 驱动状态还原（再调一次每个驱动的 LanbaiTick(原来的 t)；没有就只还原 _Udon_SunDisc）。
// 运行时由当前幕的驱动在自己的窗口里设 _Udon_ReflCube（全局纹理）+ _Udon_ReflCube_HDR（DecodeHDR 参数：BC6H 是线性 HDR，
// 填 (1, 1, 0, 0)）+ _Udon_ReflExposure。这些名字已登记（Common/UdonGlobals.md）。
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Director.Editor
{
    public static class LanbaiReflectionBaker
    {
        [Serializable] public class Bake
        {
            public string name;              // e.g. ReflCube_Dawn
            public float t;                  // timeline seconds
            public float[] eye;              // bus-relative position (m), default (0.55, 1.70, 2.05)
            public int size = 256;
            public string[] excludeLayers;   // layer names left out of the cube (the bus, players, ...)
            public bool hideSunDisc;
            public string output;            // asset folder, default Assets/Lanbai/Director/ReflCubes
            public string note;
        }
        [Serializable] class BakeList { public Bake[] bakes; }

        static string ConfigPath()
        {
            foreach (var guid in AssetDatabase.FindAssets("ReflectionBakes"))
            {
                var p = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileName(p) == "ReflectionBakes.json") return p;
            }
            return null;
        }

        [MenuItem("蓝白/Director/Bake Reflection Cubes")]
        public static void BakeAll()
        {
            var cfg = ConfigPath();
            if (cfg == null) { Debug.LogError("[Lanbai Refl] Director/ReflectionBakes.json not found"); return; }
            var list = JsonUtility.FromJson<BakeList>(File.ReadAllText(cfg));
            if (list == null || list.bakes == null || list.bakes.Length == 0) { Debug.LogWarning("[Lanbai Refl] no bakes in " + cfg); return; }
            int sunId = Shader.PropertyToID("_Udon_SunDisc");
            Vector4 sunSaved = Shader.GetGlobalVector(sunId);
            var drivers = SceneDrivers();
            try
            {
                for (int i = 0; i < list.bakes.Length; i++)
                {
                    var b = list.bakes[i];
                    if (EditorUtility.DisplayCancelableProgressBar("Lanbai reflection cubes", b.name, (float)i / list.bakes.Length)) break;
                    SetTime(drivers, b.t);
                    if (b.hideSunDisc) Shader.SetGlobalVector(sunId, new Vector4(0f, sunSaved.y, sunSaved.z, sunSaved.w));
                    BakeOne(b);
                    Shader.SetGlobalVector(sunId, sunSaved);
                }
            }
            finally
            {
                Shader.SetGlobalVector(sunId, sunSaved);
                EditorUtility.ClearProgressBar();
            }
            Debug.Log("[Lanbai Refl] done (" + list.bakes.Length + " cubes). The drivers were left at the last bake's t: scrub the timeline / re-run your act's Apply.");
        }

        // ---- the timeline in edit mode ---------------------------------------------------------------------------
        static List<Component> SceneDrivers()
        {
            var res = new List<Component>();
            foreach (var t in LanbaiDirectorGen.DriverTypes())
                res.AddRange(UnityEngine.Object.FindObjectsOfType(t, true).Cast<Component>());
            return res;
        }

        static void SetTime(List<Component> drivers, float t)
        {
            const BindingFlags F = BindingFlags.Public | BindingFlags.Instance;
            foreach (var d in drivers)
            {
                var ty = d.GetType();
                float[] w = null;
                try { w = (float[])ty.GetMethod("LanbaiWindow", F, null, Type.EmptyTypes, null).Invoke(d, null); } catch (Exception) { }
                bool inside = w != null && w.Length >= 2 && t >= w[0] && t < w[1];
                try
                {
                    var ea = ty.GetMethod("EditorApply", F, null, Type.EmptyTypes, null);
                    if (inside && ea != null) ea.Invoke(d, null);
                    ty.GetMethod("LanbaiActivate", F, null, new[] { typeof(bool) }, null).Invoke(d, new object[] { inside });
                    if (inside) ty.GetMethod("LanbaiTick", F, null, new[] { typeof(float) }, null).Invoke(d, new object[] { t });
                }
                catch (Exception e)
                {
                    Debug.LogWarning("[Lanbai Refl] " + ty.Name + " at t = " + t + ": " + e.GetBaseException().Message);
                }
            }
        }

        // ---- one cube ----------------------------------------------------------------------------------------------
        static void BakeOne(Bake b)
        {
            int size = Mathf.ClosestPowerOfTwo(Mathf.Clamp(b.size <= 0 ? 256 : b.size, 32, 1024));
            var go = new GameObject("__LanbaiReflBakeCam") { hideFlags = HideFlags.HideAndDontSave };
            var rt = new RenderTexture(size, size, 24, RenderTextureFormat.ARGBHalf, RenderTextureReadWrite.Linear)
            { dimension = UnityEngine.Rendering.TextureDimension.Cube, useMipMap = false, autoGenerateMips = false };
            try
            {
                var cam = go.AddComponent<Camera>();
                cam.enabled = false;
                cam.allowHDR = true;
                cam.allowMSAA = false;
                cam.nearClipPlane = 0.05f;
                cam.farClipPlane = 45000f;
                cam.clearFlags = CameraClearFlags.Skybox;
                int mask = ~0;
                if (b.excludeLayers != null)
                    foreach (var ln in b.excludeLayers)
                    {
                        int l = LayerMask.NameToLayer(ln);
                        if (l >= 0) mask &= ~(1 << l);
                        else Debug.LogWarning("[Lanbai Refl] layer '" + ln + "' does not exist (" + b.name + ")");
                    }
                cam.cullingMask = mask;
                var e = (b.eye != null && b.eye.Length >= 3) ? new Vector3(b.eye[0], b.eye[1], b.eye[2]) : new Vector3(0.55f, 1.70f, 2.05f);
                go.transform.position = e;
                go.transform.rotation = Quaternion.identity;
                rt.Create();
                if (!cam.RenderToCubemap(rt, 63)) { Debug.LogError("[Lanbai Refl] RenderToCubemap failed for " + b.name); return; }
                var strip = new Texture2D(size * 6, size, TextureFormat.RGBAHalf, false, true);
                var face = new Texture2D(size, size, TextureFormat.RGBAHalf, false, true);
                var tmp = RenderTexture.GetTemporary(size, size, 0, RenderTextureFormat.ARGBHalf, RenderTextureReadWrite.Linear);
                var prev = RenderTexture.active;
                for (int f = 0; f < 6; f++)
                {
                    Graphics.CopyTexture(rt, f, 0, tmp, 0, 0);
                    RenderTexture.active = tmp;
                    face.ReadPixels(new Rect(0, 0, size, size), 0, 0, false);
                    face.Apply(false);
                    // cubemap faces are stored top-down relative to a 2D texture: flip rows into the strip
                    var px = face.GetPixels();
                    var flipped = new Color[px.Length];
                    for (int y = 0; y < size; y++) Array.Copy(px, y * size, flipped, (size - 1 - y) * size, size);
                    strip.SetPixels(f * size, 0, size, size, flipped);
                }
                RenderTexture.active = prev;
                RenderTexture.ReleaseTemporary(tmp);
                strip.Apply(false);
                string dir = string.IsNullOrEmpty(b.output) ? "Assets/Lanbai/Director/ReflCubes" : b.output.TrimEnd('/');
                Directory.CreateDirectory(dir);
                string path = dir + "/" + b.name + ".exr";
                File.WriteAllBytes(path, strip.EncodeToEXR(Texture2D.EXRFlags.CompressZIP));
                UnityEngine.Object.DestroyImmediate(strip);
                UnityEngine.Object.DestroyImmediate(face);
                AssetDatabase.ImportAsset(path);
                var imp = (TextureImporter)AssetImporter.GetAtPath(path);
                imp.textureShape = TextureImporterShape.TextureCube;
                imp.generateCubemap = TextureImporterGenerateCubemap.FullCubemap;
                imp.sRGBTexture = false;
                imp.mipmapEnabled = true;
                imp.wrapMode = TextureWrapMode.Clamp;
                imp.filterMode = FilterMode.Trilinear;
                imp.maxTextureSize = size;
                imp.textureCompression = TextureImporterCompression.CompressedHQ;
                var ps = imp.GetPlatformTextureSettings("Standalone");
                ps.overridden = true;
                ps.maxTextureSize = size;
                ps.format = TextureImporterFormat.BC6H;
                imp.SetPlatformTextureSettings(ps);
                imp.SaveAndReimport();
                Debug.Log("[Lanbai Refl] " + path + "  t = " + b.t + "  eye = " + e + "  " + size + "/face  BC6H" + (b.hideSunDisc ? "  (no sun disc)" : ""));
            }
            finally
            {
                rt.Release();
                UnityEngine.Object.DestroyImmediate(rt);
                UnityEngine.Object.DestroyImmediate(go);
            }
        }
    }
}
#endif
