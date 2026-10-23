// 蓝白 · 一组天空预设的运行时写入器（UdonSharp）。
// !!! NOT COMPILED IN UNITY / UdonSharp: Roslyn type-check against UnityEngine 2021.1 + a U# stub only. !!!
//
// One component per preset (蓝白/Sky/Create Preset Objects fills the arrays from Sky/SkyPresets.json).
// The act's driver calls Apply() in Start() and under occlusion (black, white, entering cloud, under water), or
// ApplyBlend(other, t) for the visible transitions (dusk -> blue hour: same names in the same order, so the vectors
// are lerped index by index; names that differ snap at t = 0.5). It writes:
//   * every _Udon_ global of the preset (VRCShader.SetGlobalVector / SetGlobalFloat; all names carry _Udon_),
//   * RenderSettings.fogDensity from _Udon_Fog.x (Built-in shaders use it; LanbaiFog reads the global),
//   * RenderSettings.skybox = skyMaterial when 'setSkybox' (verify that this setter is exposed to Udon in the SDK;
//     if not, put every act's material on one skybox at build time and keep 'setSkybox' off).
// Edit-mode values are lost on entering Play (gate test pitfall 9): that is why Apply() runs in Start().
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

namespace Lanbai.Sky
{
    [UdonBehaviourSyncMode(BehaviourSyncMode.None)]
    public class LanbaiSkyPreset : UdonSharpBehaviour
    {
        public string presetName;
        public Material skyMaterial;
        public bool setSkybox = true;
        public bool applyOnStart = false;
        public string[] vectorNames;
        public Vector4[] vectorValues;
        public string[] floatNames;
        public float[] floatValues;

        private int[] vecIds;
        private int[] floatIds;

        void Start()
        {
            CacheIds();
            if (applyOnStart)
                Apply();
        }

        private void CacheIds()
        {
            if (vecIds != null)
                return;
            int nv = (vectorNames != null) ? vectorNames.Length : 0;
            int nf = (floatNames != null) ? floatNames.Length : 0;
            vecIds = new int[nv];
            floatIds = new int[nf];
            for (int i = 0; i < nv; i++) vecIds[i] = VRCShader.PropertyToID(vectorNames[i]);
            for (int i = 0; i < nf; i++) floatIds[i] = VRCShader.PropertyToID(floatNames[i]);
        }

        public void Apply()
        {
            CacheIds();
            for (int i = 0; i < vecIds.Length; i++)
            {
                VRCShader.SetGlobalVector(vecIds[i], vectorValues[i]);
                if (vectorNames[i] == "_Udon_Fog")
                    RenderSettings.fogDensity = vectorValues[i].x;
            }
            for (int i = 0; i < floatIds.Length; i++)
            {
                VRCShader.SetGlobalFloat(floatIds[i], floatValues[i]);
                if (floatNames[i] == "_Udon_FogDensity")
                    RenderSettings.fogDensity = floatValues[i];
            }
            if (setSkybox && skyMaterial != null)
                RenderSettings.skybox = skyMaterial;
        }

        // lerp from THIS preset toward 'other' (t 0..1). The skybox material switches at t = 1 only (its material
        // values are not blended: blend skies with _Udon_SkyBlend inside one material instead).
        public void ApplyBlend(LanbaiSkyPreset other, float t)
        {
            CacheIds();
            other.CacheIdsPublic();
            t = Mathf.Clamp01(t);
            for (int i = 0; i < vecIds.Length; i++)
            {
                Vector4 a = vectorValues[i];
                Vector4 b = a;
                bool found = false;
                for (int j = 0; j < other.vectorNames.Length; j++)
                {
                    if (other.vectorNames[j] == vectorNames[i]) { b = other.vectorValues[j]; found = true; break; }
                }
                Vector4 val = found ? Vector4.Lerp(a, b, t) : (t < 0.5f ? a : b);
                VRCShader.SetGlobalVector(vecIds[i], val);
                if (vectorNames[i] == "_Udon_Fog")
                    RenderSettings.fogDensity = val.x;
            }
            for (int i = 0; i < floatIds.Length; i++)
            {
                float a = floatValues[i];
                float b = a;
                for (int j = 0; j < other.floatNames.Length; j++)
                {
                    if (other.floatNames[j] == floatNames[i]) { b = other.floatValues[j]; break; }
                }
                float v = Mathf.Lerp(a, b, t);
                VRCShader.SetGlobalFloat(floatIds[i], v);
                if (floatNames[i] == "_Udon_FogDensity")
                    RenderSettings.fogDensity = v;
            }
            if (t >= 1f && other.setSkybox && other.skyMaterial != null)
                RenderSettings.skybox = other.skyMaterial;
        }

        public void CacheIdsPublic()
        {
            CacheIds();
        }
    }
}
