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
        public Texture cubeA;      // Texture, not Cubemap: VRCShader.SetGlobalTexture takes a Texture (U# field type safe)
        public Texture cubeB;

        [Header("Globals (filled by 蓝白/Sky/Build Sky; do not hand-edit)")]
        public string[] vectorNames;
        public Vector4[] vectorValues;
        public string[] floatNames;
        public float[] floatValues;
        [Tooltip("Per vector: 0 lerp, 1 cube-A parameter, 2 cube-B parameter, 3 flags, 4 shared cube-layer parameter, 5 direction")]
        public int[] vecGroups;
        [Tooltip("For a cube-B parameter: the index of its cube-A twin (the crossfade through slot B)")]
        public int[] vecPartner;
        [Tooltip("Names ApplyBlend FROM this preset does not write (another driver owns them in that fade)")]
        public string[] blendSkip;

        private int[] vecIds;
        private int[] floatIds;
        private int[] vecGroup;          // = vecGroups (0 when the builder did not fill it)
        private bool[] vecSkip;
        private bool[] floatSkip;
        private int fogIndex = -1;
        private int flagIndex = -1;
        private int blendIndex = -1;
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
            vecSkip = new bool[nv];
            floatSkip = new bool[nf];
            for (int i = 0; i < nv; i++)
            {
                string n = vectorNames[i];
                vecIds[i] = VRCShader.PropertyToID(n);
                vecGroup[i] = (vecGroups != null && i < vecGroups.Length) ? vecGroups[i] : 0;
                vecSkip[i] = IsSkipped(n);
                if (n == "_Udon_Fog") fogIndex = i;
                if (n == "_Udon_SkyGlobals") flagIndex = i;
                if (n == "_Udon_SkyBlend") blendIndex = i;
            }
            for (int i = 0; i < nf; i++)
            {
                floatIds[i] = VRCShader.PropertyToID(floatNames[i]);
                floatSkip[i] = IsSkipped(floatNames[i]);
            }
            idCubeA = VRCShader.PropertyToID("_Udon_SkyCubeTexA");
            idCubeB = VRCShader.PropertyToID("_Udon_SkyCubeTexB");
        }

        private bool IsSkipped(string n)
        {
            if (blendSkip == null)
                return false;
            for (int j = 0; j < blendSkip.Length; j++)
                if (blendSkip[j] == n) return true;
            return false;
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
            mapFor = null;   // the next ApplyBlend from this preset starts with a full write
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

        // lerp from THIS preset toward 'other' (t 0..1). Every preset lists the same names in the same order (the builder
        // writes them sorted), so the index map is the identity (checked once per 'other'; a name-by-name map otherwise).
        // The groups (vecGroups, exported by make_presets.py, Sky/README_Sky.md §3.1) fix what a plain lerp gets wrong:
        //   1 / 2 cube-A / cube-B parameters and 4 the shared cube-layer parameters: never lerped against a side without
        //     a cube (the side that has one gives them);
        //   both sides have a cube A but not the same one (or not the same rotation): a CROSSFADE through slot B: the
        //     other cube is bound as _Udon_SkyCubeTexB with its A parameters in the B slot and _Udon_SkyBlend.x = t;
        //     at t = 1 other.Apply() puts it back in A with blend 0 (the same picture), so nothing turns or jumps;
        //   3 _Udon_SkyGlobals: the component-wise max (+ z = 1 in a crossfade);
        //   5 directions: a side whose direction is zero does not pull; two directions: normalised lerp;
        //   blendSkip (of THIS preset): not written (another driver owns that name in this fade).
        // At t >= 1 it is other.Apply().
        private LanbaiSkyPreset mapFor;
        private int[] vecMap;
        private int[] floatMap;
        private bool[] vecSame;        // this name has the same value on both sides: written on the fade's first frame only
        private bool[] floatSame;
        private bool firstFrame;

        private int[] BuildMap(string[] mine, string[] theirs)
        {
            int[] m = new int[mine.Length];
            bool same = theirs != null && theirs.Length == mine.Length;
            for (int i = 0; same && i < mine.Length; i++)
                if (theirs[i] != mine[i]) same = false;
            for (int i = 0; i < mine.Length; i++)
            {
                if (same) { m[i] = i; continue; }
                m[i] = -1;
                if (theirs == null) continue;
                for (int j = 0; j < theirs.Length; j++)
                    if (theirs[j] == mine[i]) { m[i] = j; break; }
            }
            return m;
        }

        public float RotationA()
        {
            CacheIds();
            for (int i = 0; i < vecIds.Length; i++)
                if (vectorNames[i] == "_Udon_Sky_RotationA") return vectorValues[i].x;
            return 0f;
        }

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
                vecMap = BuildMap(vectorNames, other.vectorNames);
                floatMap = BuildMap(floatNames, other.floatNames);
                vecSame = new bool[vecIds.Length];
                for (int i = 0; i < vecIds.Length; i++)
                    vecSame[i] = vecMap[i] >= 0 && vectorValues[i] == other.vectorValues[vecMap[i]];
                floatSame = new bool[floatIds.Length];
                for (int i = 0; i < floatIds.Length; i++)
                    floatSame[i] = floatMap[i] >= 0 && floatValues[i] == other.floatValues[floatMap[i]];
                mapFor = other;
                firstFrame = true;
            }
            Vector4 fa = Flags();
            Vector4 fb = other.Flags();
            bool hasA = fa.y >= 0.5f, hasB = fb.y >= 0.5f;
            bool cross = hasA && hasB && (cubeA != other.cubeA || Mathf.Abs(RotationA() - other.RotationA()) > 0.01f);
            Texture ca = (cubeA != null) ? cubeA : other.cubeA;
            if (ca != null) VRCShader.SetGlobalTexture(idCubeA, ca);
            if (cross) { if (other.cubeA != null) VRCShader.SetGlobalTexture(idCubeB, other.cubeA); }
            else
            {
                Texture cb = (cubeB != null) ? cubeB : other.cubeB;
                if (cb != null) VRCShader.SetGlobalTexture(idCubeB, cb);
            }
            bool anyCubeA = fa.y >= 0.5f || fa.z >= 0.5f, anyCubeB = fb.y >= 0.5f || fb.z >= 0.5f;
            Vector4[] ov = other.vectorValues;
            float[] of = other.floatValues;
            float density = 0f;
            for (int i = 0; i < vecIds.Length; i++)
            {
                if (vecSkip[i]) continue;
                // identical on both sides: nothing to fade (final review: ~30 of 67 change in the real fades); the cube-B
                // slot and _Udon_SkyBlend are rewritten in a crossfade, and everything on the fade's first frame
                if (vecSame[i] && !firstFrame && !(cross && (vecGroup[i] == 2 || vecGroup[i] == 3 || i == blendIndex))) continue;
                Vector4 a = vectorValues[i];
                Vector4 b = (vecMap[i] >= 0) ? ov[vecMap[i]] : Vector4.zero;
                Vector4 val;
                int g = vecGroup[i];
                if (g == 3)
                {
                    val = Vector4.Max(a, b);
                    if (cross) val.z = 1f;
                }
                else if (g == 1)
                    val = cross ? a : ((hasA && !hasB) ? a : ((hasB && !hasA) ? b : Vector4.Lerp(a, b, t)));
                else if (g == 2)
                {
                    if (cross)
                    {
                        int pa = (vecPartner != null && i < vecPartner.Length) ? vecPartner[i] : -1;
                        val = (pa >= 0 && vecMap[pa] >= 0) ? ov[vecMap[pa]] : b;   // the other's A parameters in slot B
                    }
                    else
                        val = (fa.z >= 0.5f && fb.z < 0.5f) ? a : ((fb.z >= 0.5f && fa.z < 0.5f) ? b : Vector4.Lerp(a, b, t));
                }
                else if (g == 4)
                    val = (anyCubeA && !anyCubeB) ? a : ((anyCubeB && !anyCubeA) ? b : Vector4.Lerp(a, b, t));
                else if (g == 5)
                {
                    Vector3 da = new Vector3(a.x, a.y, a.z), db = new Vector3(b.x, b.y, b.z);
                    if (db.sqrMagnitude < 1e-8f) val = a;
                    else if (da.sqrMagnitude < 1e-8f) val = b;
                    else
                    {
                        Vector3 d = Vector3.Lerp(da, db, t).normalized;
                        val = new Vector4(d.x, d.y, d.z, Mathf.Lerp(a.w, b.w, t));
                    }
                }
                else
                    val = Vector4.Lerp(a, b, t);
                if (cross && i == blendIndex) val.x = t;   // cube A (this) -> cube B (the other's, in slot B)
                VRCShader.SetGlobalVector(vecIds[i], val);
                if (i == fogIndex) density = val.x;
            }
            for (int i = 0; i < floatIds.Length; i++)
            {
                if (floatSkip[i] || (floatSame[i] && !firstFrame)) continue;
                float b = (floatMap[i] >= 0) ? of[floatMap[i]] : 0f;
                VRCShader.SetGlobalFloat(floatIds[i], Mathf.Lerp(floatValues[i], b, t));
            }
            WriteAtmosphere(density, Color.Lerp(fogColor, other.fogColor, t), Color.Lerp(ambientColor, other.ambientColor, t));
            firstFrame = false;
        }
    }
}
