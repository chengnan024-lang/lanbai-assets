// 蓝白 · 一组天空预设的运行时写入器（UdonSharp）。
// !!! NOT COMPILED IN UNITY / UdonSharp: Roslyn type-check against UnityEngine 2021.1 + a U# stub only. !!!
//
// One component per preset (蓝白/Sky/Create Preset Objects fills the arrays from Sky/SkyPresets.json).
// The act's driver calls Apply() in Start() and under occlusion (black, white, entering cloud, under water), or
// ApplyBlend(other, t) for the visible transitions (both presets carry every sky global, absent = 0; an index map is
// built once per 'other'; at t >= 1 it calls other.Apply()). It writes:
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
        private int fogIndex = -1;

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
            fogIndex = -1;
            for (int i = 0; i < nv; i++)
            {
                vecIds[i] = VRCShader.PropertyToID(vectorNames[i]);
                if (vectorNames[i] == "_Udon_Fog") fogIndex = i;
            }
            for (int i = 0; i < nf; i++) floatIds[i] = VRCShader.PropertyToID(floatNames[i]);
        }

        public void Apply()
        {
            CacheIds();
            for (int i = 0; i < vecIds.Length; i++)
            {
                VRCShader.SetGlobalVector(vecIds[i], vectorValues[i]);
                if (i == fogIndex)
                    RenderSettings.fogDensity = vectorValues[i].x;
            }
            for (int i = 0; i < floatIds.Length; i++)
                VRCShader.SetGlobalFloat(floatIds[i], floatValues[i]);
            if (setSkybox && skyMaterial != null)
                RenderSettings.skybox = skyMaterial;
        }

        // lerp from THIS preset toward 'other' (t 0..1). Both presets list the same names (the builder writes every sky
        // global into every preset; absent = 0), so the index map is built once per 'other' and the per-frame work is
        // one SetGlobal per name. A name only one side has is lerped against 0. At t >= 1 it is other.Apply().
        private LanbaiSkyPreset mapFor;
        private int[] vecMap;
        private int[] floatMap;

        public void ApplyBlend(LanbaiSkyPreset other, float t)
        {
            CacheIds();
            t = Mathf.Clamp01(t);
            if (t >= 1f)
            {
                other.Apply();
                return;
            }
            if (mapFor != other)
            {
                vecMap = new int[vecIds.Length];
                for (int i = 0; i < vecIds.Length; i++)
                {
                    vecMap[i] = -1;
                    for (int j = 0; j < other.vectorNames.Length; j++)
                        if (other.vectorNames[j] == vectorNames[i]) { vecMap[i] = j; break; }
                }
                floatMap = new int[floatIds.Length];
                for (int i = 0; i < floatIds.Length; i++)
                {
                    floatMap[i] = -1;
                    for (int j = 0; j < other.floatNames.Length; j++)
                        if (other.floatNames[j] == floatNames[i]) { floatMap[i] = j; break; }
                }
                mapFor = other;
            }
            Vector4[] ov = other.vectorValues;
            float[] of = other.floatValues;
            for (int i = 0; i < vecIds.Length; i++)
            {
                Vector4 b = (vecMap[i] >= 0) ? ov[vecMap[i]] : Vector4.zero;
                Vector4 val = Vector4.Lerp(vectorValues[i], b, t);
                VRCShader.SetGlobalVector(vecIds[i], val);
                if (i == fogIndex)
                    RenderSettings.fogDensity = val.x;
            }
            for (int i = 0; i < floatIds.Length; i++)
            {
                float b = (floatMap[i] >= 0) ? of[floatMap[i]] : 0f;
                VRCShader.SetGlobalFloat(floatIds[i], Mathf.Lerp(floatValues[i], b, t));
            }
        }

        public void CacheIdsPublic()
        {
            CacheIds();
        }
    }
}
