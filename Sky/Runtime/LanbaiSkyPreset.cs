// 蓝白 · 一组天空预设的运行时写入器（UdonSharp）。
// !!! NOT COMPILED IN UNITY / UdonSharp: Roslyn type-check (Common/Tools~/compile_check/check_cs.sh) only. !!!
//
// ONE skybox material for the whole film (Sky/Generated/M_Sky.mat, Lanbai/Sky; chief engineer r2 #0): a preset is only
// globals. 蓝白/Sky/Build Sky fills the arrays from Sky/SkyPresets.json; every preset lists EVERY sky / fog global any
// preset uses (absent = 0 = 'not set'), so Apply() never leaves a previous act's value behind. The act's driver (one
// writer per act: LanbaiSkyDriver, or the act's own driver) calls Apply() in Start() and under occlusion, or
// ApplyBlend(other, t) for the visible transitions. It writes:
//   * every _Udon_ global of the preset (VRCShader.SetGlobalVector / SetGlobalFloat),
//   * the preset's HDRIs as the global cubes _Udon_SkyCubeTexA / B (VRCShader.SetGlobalTexture; flags in
//     _Udon_SkyGlobals.y / z),
//   * ownsAtmosphere (default OFF): RenderSettings.fogDensity from _Udon_Fog.x, fogColor, ambientLight,
//   * ownsSkybox (default OFF): RenderSettings.skybox = skyMaterial (the builder already set the one material; turn it
//     on only if something else in the scene swaps the skybox).
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
        [Tooltip("The one Lanbai/Sky material (only used when Owns Skybox)")]
        public Material skyMaterial;
        public bool ownsSkybox = false;
        [Tooltip("Also write RenderSettings fog density / fog colour / ambient (Built-in shaders); off = only the _Udon_ globals")]
        public bool ownsAtmosphere = false;
        public Color fogColor = Color.gray;
        public Color ambientColor = Color.gray;
        public bool applyOnStart = false;

        [Header("HDRIs (global cubes; null = the procedural sky)")]
        public Cubemap cubeA;
        public Cubemap cubeB;

        [Header("Globals (filled by 蓝白/Sky/Build Sky; do not hand-edit)")]
        public string[] vectorNames;
        public Vector4[] vectorValues;
        public string[] floatNames;
        public float[] floatValues;

        private int[] vecIds;
        private int[] floatIds;
        private int[] vecGroup;          // 0 lerp, 1 cube-A parameter, 2 cube-B parameter, 3 _Udon_SkyGlobals (flags)
        private int fogIndex = -1;
        private int flagIndex = -1;
        private int idCubeA, idCubeB;

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
            vecGroup = new int[nv];
            floatIds = new int[nf];
            fogIndex = -1;
            flagIndex = -1;
            for (int i = 0; i < nv; i++)
            {
                string n = vectorNames[i];
                vecIds[i] = VRCShader.PropertyToID(n);
                if (n == "_Udon_Fog") fogIndex = i;
                if (n == "_Udon_SkyGlobals") { flagIndex = i; vecGroup[i] = 3; }
                else if (n.StartsWith("_Udon_Sky_") && n.EndsWith("A")) vecGroup[i] = 1;   // ZenithTintA .. ClampA
                else if (n.StartsWith("_Udon_Sky_") && n.EndsWith("B") && n != "_Udon_Sky_OtherFromB") vecGroup[i] = 2;
            }
            for (int i = 0; i < nf; i++) floatIds[i] = VRCShader.PropertyToID(floatNames[i]);
            idCubeA = VRCShader.PropertyToID("_Udon_SkyCubeTexA");
            idCubeB = VRCShader.PropertyToID("_Udon_SkyCubeTexB");
        }

        public Vector4 Flags()
        {
            CacheIds();
            return (flagIndex >= 0) ? vectorValues[flagIndex] : Vector4.zero;
        }

        private void WriteAtmosphere(float density, Color fog, Color amb)
        {
            if (!ownsAtmosphere)
                return;
            RenderSettings.fogDensity = density;
            RenderSettings.fogColor = fog;
            RenderSettings.ambientLight = amb;
        }

        public void Apply()
        {
            CacheIds();
            if (cubeA != null) VRCShader.SetGlobalTexture(idCubeA, cubeA);
            if (cubeB != null) VRCShader.SetGlobalTexture(idCubeB, cubeB);
            for (int i = 0; i < vecIds.Length; i++)
                VRCShader.SetGlobalVector(vecIds[i], vectorValues[i]);
            for (int i = 0; i < floatIds.Length; i++)
                VRCShader.SetGlobalFloat(floatIds[i], floatValues[i]);
            WriteAtmosphere((fogIndex >= 0) ? vectorValues[fogIndex].x : 0f, fogColor, ambientColor);
            if (ownsSkybox && skyMaterial != null)
                RenderSettings.skybox = skyMaterial;
        }

        // lerp from THIS preset toward 'other' (t 0..1). Both presets list the same names (absent = 0), so the index map
        // is built once per 'other' and the per-frame work is one SetGlobal per name. Rules that a plain lerp gets wrong:
        //   * cube A / B parameters (tints, rotation, exposure, clamp) are NOT lerped against a side without that cube
        //     (the cube would spin / change colour while it fades): the side that has the cube gives them;
        //   * _Udon_SkyGlobals (flags) = the component-wise max (a cube stays bound while either side uses it);
        //   * the cube textures: this side's, else the other's.
        // At t >= 1 it is other.Apply().
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
            Vector4 fa = Flags();
            Vector4 fb = other.Flags();
            Cubemap ca = (cubeA != null) ? cubeA : other.cubeA;
            Cubemap cb = (cubeB != null) ? cubeB : other.cubeB;
            if (ca != null) VRCShader.SetGlobalTexture(idCubeA, ca);
            if (cb != null) VRCShader.SetGlobalTexture(idCubeB, cb);
            Vector4[] ov = other.vectorValues;
            float[] of = other.floatValues;
            float density = 0f;
            for (int i = 0; i < vecIds.Length; i++)
            {
                Vector4 a = vectorValues[i];
                Vector4 b = (vecMap[i] >= 0) ? ov[vecMap[i]] : Vector4.zero;
                Vector4 val;
                int g = vecGroup[i];
                if (g == 3) val = Vector4.Max(a, b);
                else if (g == 1 && fb.y < 0.5f && fa.y >= 0.5f) val = a;
                else if (g == 1 && fa.y < 0.5f && fb.y >= 0.5f) val = b;
                else if (g == 2 && fb.z < 0.5f && fa.z >= 0.5f) val = a;
                else if (g == 2 && fa.z < 0.5f && fb.z >= 0.5f) val = b;
                else val = Vector4.Lerp(a, b, t);
                VRCShader.SetGlobalVector(vecIds[i], val);
                if (i == fogIndex) density = val.x;
            }
            for (int i = 0; i < floatIds.Length; i++)
            {
                float b = (floatMap[i] >= 0) ? of[floatMap[i]] : 0f;
                VRCShader.SetGlobalFloat(floatIds[i], Mathf.Lerp(floatValues[i], b, t));
            }
            WriteAtmosphere(density, Color.Lerp(fogColor, other.fogColor, t), Color.Lerp(ambientColor, other.ambientColor, t));
        }
    }
}
