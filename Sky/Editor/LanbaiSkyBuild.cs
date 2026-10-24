// 蓝白 · Sky 的编辑器菜单：星点网格、每一幕的天空材质（Sky/SkyPresets.json）、预览、雾色立方图。
// !!! NOT COMPILED IN UNITY: Roslyn type-check against UnityEditor 2021.1 only (Sky/Tools~/compile_check/check_cs.sh). !!!
//
//   蓝白/Sky/Build Star Mesh          Sky/Data/StarPoints_BSC5.csv -> Sky/Generated/StarPoints_BSC5.asset (4 verts / star)
//   蓝白/Sky/Build Sky                ONE material Sky/Generated/M_Sky.mat (= RenderSettings.skybox) + one GameObject per
//                                     preset (LanbaiSkyPreset, U#, + program assets) from Sky/SkyPresets.json; re-measures
//                                     each HDRI's sun on its source .hdr and writes the rotation into _Udon_Sky_RotationA
//   蓝白/Sky/Create Preset Objects    = Build Sky (old name)
//   蓝白/Sky/Preview Window           apply a preset in the editor (globals + global cube + fog density), clear the globals
//   蓝白/Sky/Bake Fog Cube From Skybox  the current skybox -> a 64 px HDR cubemap for _Udon_FogCube (optional)
// Re-runnable: everything is rewritten in place. Report: Sky/Generated/SkyBuild_Report.txt
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Sky.EditorTools
{
    [Serializable] public class SkyKV { public string k; public float v; }
    [Serializable] public class SkyKV4 { public string k; public float[] v; }
    [Serializable] public class SkyPreset
    {
        public string name; public string acts; public string profile; public string cubeA; public bool glow; public bool moon;
        public float sunAz; public string notes;
        public SkyKV[] floats; public SkyKV4[] vectors; public SkyKV[] globalFloats; public SkyKV4[] globalVectors;
        public int[] vecGroups; public int[] vecPartner; public string[] blendSkip;
    }
    [Serializable] public class SkyDriverEntry { public string preset; public float t0; public float t1; public float fade; public string label; }
    [Serializable] public class SkyDriverDef { public string name; public SkyDriverEntry[] entries; }
    [Serializable] public class SkyRot { public string preset; public float rotation; }
    [Serializable] public class SkyRotFile { public SkyRot[] rotations; }
    [Serializable] public class SkyPresetFile { public string about; public SkyPreset[] presets; public SkyDriverDef[] drivers; }

    public static class LanbaiSkyBuild
    {
        static string SkyRoot()
        {
            string[] g = AssetDatabase.FindAssets("SkyPresets");
            foreach (string id in g)
            {
                string p = AssetDatabase.GUIDToAssetPath(id);
                if (p.EndsWith("/Sky/SkyPresets.json"))
                    return p.Substring(0, p.Length - "/SkyPresets.json".Length);
            }
            return "Assets/Lanbai/Sky";
        }

        static string Gen()
        {
            string d = SkyRoot() + "/Generated";
            if (!AssetDatabase.IsValidFolder(d))
                AssetDatabase.CreateFolder(SkyRoot(), "Generated");
            return d;
        }

        public static SkyPresetFile LoadPresets()
        {
            string path = SkyRoot() + "/SkyPresets.json";
            return JsonUtility.FromJson<SkyPresetFile>(File.ReadAllText(path));
        }

        // ---------------------------------------------------------------------------------------------------------
        [MenuItem("蓝白/Sky/Build Star Mesh")]
        public static void BuildStarMesh()
        {
            string csv = SkyRoot() + "/Data/StarPoints_BSC5.csv";
            string[] lines = File.ReadAllLines(csv);
            List<Vector3> v = new List<Vector3>(); List<Vector2> uv0 = new List<Vector2>(); List<Vector4> uv1 = new List<Vector4>();
            List<Color> col = new List<Color>(); List<int> idx = new List<int>();
            Vector2[] corners = { new Vector2(-1, -1), new Vector2(1, -1), new Vector2(1, 1), new Vector2(-1, 1) };
            int n = 0;
            List<string[]> rows = new List<string[]>();
            foreach (string l in lines)
            {
                if (l.StartsWith("#") || l.StartsWith("hr,") || l.Trim().Length == 0)
                    continue;
                rows.Add(l.Split(','));
            }
            float count = rows.Count;
            foreach (string[] c in rows)
            {
                Vector3 d = new Vector3(F(c[1]), F(c[2]), F(c[3]));
                float mag = F(c[4]); Color cc = new Color(F(c[6]), F(c[7]), F(c[8]), 1f); float rank = F(c[9]);
                for (int k = 0; k < 4; k++)
                {
                    v.Add(d); uv0.Add(corners[k]); uv1.Add(new Vector4(mag, rank, rank / Mathf.Max(count - 1f, 1f), 0f)); col.Add(cc);
                }
                int b = n * 4;
                idx.Add(b); idx.Add(b + 2); idx.Add(b + 1); idx.Add(b); idx.Add(b + 3); idx.Add(b + 2);
                n++;
            }
            Mesh m = new Mesh();
            m.name = "StarPoints_BSC5";
            m.indexFormat = (v.Count > 65000) ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16;
            m.SetVertices(v); m.SetUVs(0, uv0); m.SetUVs(1, uv1); m.SetColors(col); m.SetTriangles(idx, 0);
            m.bounds = new Bounds(Vector3.zero, Vector3.one * 200000f);   // never frustum-culled: the shader places the stars
            string path = Gen() + "/StarPoints_BSC5.asset";
            Mesh old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (old != null) { EditorUtility.CopySerialized(m, old); EditorUtility.SetDirty(old); }
            else AssetDatabase.CreateAsset(m, path);
            AssetDatabase.SaveAssets();
            Debug.Log("[Lanbai/Sky] star mesh: " + n + " stars -> " + path);
        }

        static float F(string s) { return float.Parse(s, CultureInfo.InvariantCulture); }

        // a star-point mesh in the Lanbai/StarPoints vertex format (README_Sky.md §4), saved / updated at assetPath
        public static Mesh SaveStarMesh(string assetPath, string meshName, Vector3[] dirs, float[] mags, float[] ranks, float[] orders, Color[] cols)
        {
            int n = dirs.Length;
            Vector3[] v = new Vector3[n * 4]; Vector2[] uv0 = new Vector2[n * 4]; Vector4[] uv1 = new Vector4[n * 4];
            Color[] col = new Color[n * 4]; int[] idx = new int[n * 6];
            Vector2[] corners = { new Vector2(-1, -1), new Vector2(1, -1), new Vector2(1, 1), new Vector2(-1, 1) };
            for (int s = 0; s < n; s++)
            {
                for (int k = 0; k < 4; k++)
                {
                    v[s * 4 + k] = dirs[s].normalized; uv0[s * 4 + k] = corners[k];
                    uv1[s * 4 + k] = new Vector4(mags[s], ranks[s], orders[s], 0f); col[s * 4 + k] = cols[s];
                }
                int b = s * 4;
                idx[s * 6 + 0] = b; idx[s * 6 + 1] = b + 2; idx[s * 6 + 2] = b + 1;
                idx[s * 6 + 3] = b; idx[s * 6 + 4] = b + 3; idx[s * 6 + 5] = b + 2;
            }
            Mesh m = new Mesh();
            m.name = meshName;
            m.indexFormat = (v.Length > 65000) ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16;
            m.vertices = v; m.SetUVs(0, new List<Vector2>(uv0)); m.SetUVs(1, new List<Vector4>(uv1)); m.colors = col; m.triangles = idx;
            m.bounds = new Bounds(Vector3.zero, Vector3.one * 200000f);   // never frustum-culled: the shader places the stars
            Mesh old = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
            if (old != null) { EditorUtility.CopySerialized(m, old); EditorUtility.SetDirty(old); AssetDatabase.SaveAssets(); return old; }
            AssetDatabase.CreateAsset(m, assetPath);
            AssetDatabase.SaveAssets();
            return m;
        }

        public static string GeneratedFolder() { return Gen(); }
        public static string RootFolder() { return SkyRoot(); }

        // ---------------------------------------------------------------------------------------------------------
        // ONE skybox material for the whole film (chief engineer r2 #0): Sky/Generated/M_Sky.mat with the textures that
        // never change (galaxy glow, moon); every preset difference is a global (LanbaiSkyPreset). The HDRI sun is
        // re-measured on each source .hdr and the corrected rotation goes into that preset's _Udon_Sky_RotationA.
        [MenuItem("蓝白/Sky/Build Sky (one material + preset objects)")]
        public static void BuildSky()
        {
            // D-41：先等两个 U# 程序资产（脚本旁边）初始化完，再搭（Common/Editor/LanbaiUdonPrograms）
            Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("蓝白/Sky/Build Sky", new[] { typeof(Lanbai.Sky.LanbaiSkyPreset), typeof(Lanbai.Sky.LanbaiSkyDriver) },
                BuildSkyNow, Lanbai.Udon.LanbaiUdonPrograms.NextToScript);
        }

        public static void BuildSkyNow()
        {
            Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Sky/Build Sky", typeof(Lanbai.Sky.LanbaiSkyPreset), typeof(Lanbai.Sky.LanbaiSkyDriver));
            StringBuilder rep = new StringBuilder();
            rep.AppendLine("蓝白 · Sky build report " + DateTime.Now.ToString("yyyy-MM-dd HH:mm"));
            Material mat = BuildSkyMaterial(rep);
            if (mat == null) return;
            RenderSettings.skybox = mat;
            rep.AppendLine("RenderSettings.skybox = " + AssetDatabase.GetAssetPath(mat) + " (save the scene)");
            SkyPresetFile pf = LoadPresets();
            Dictionary<string, float> rot = new Dictionary<string, float>();
            foreach (SkyPreset p in pf.presets)
            {
                if (string.IsNullOrEmpty(p.cubeA)) continue;
                Cubemap cube = FindCube(p.cubeA, out string cubePath);
                if (cube == null)
                {
                    rep.AppendLine("  " + p.name + ": cube '" + p.cubeA + "' NOT FOUND (import the HDRI as Texture Shape = Cube, Lat-Long): this preset has no HDRI");
                    continue;
                }
                rep.AppendLine("  " + p.name + ": cube A = " + cubePath);
                if (p.sunAz > -900f && cubePath.ToLowerInvariant().EndsWith(".hdr") && HdrSunDirection(cubePath, out Vector3 sun))
                {
                    float az = Mathf.Atan2(sun.x, sun.z) * Mathf.Rad2Deg;
                    float el = Mathf.Asin(Mathf.Clamp(sun.y, -1f, 1f)) * Mathf.Rad2Deg;
                    float r = Mathf.DeltaAngle(0f, p.sunAz - az);
                    rot[p.name] = r;
                    rep.AppendLine(string.Format(CultureInfo.InvariantCulture,
                        "    HDRI sun measured on the source file: az {0:F2} el {1:F2} -> _Udon_Sky_RotationA {2:F2} (cloud value from the 1K file {3:F2}); align the real-time sun to az {4:F1} el {1:F2}",
                        az, el, r, GetGlobal4(p, "_Udon_Sky_RotationA").x, p.sunAz));
                }
            }
            SaveRotations(rot);
            GameObject presetRoot = CreatePresetObjectsWith(pf, mat, rot, rep);
            CreateDrivers(pf, presetRoot, rep);
            CreateStarObject(rep);
            AssetDatabase.SaveAssets();
            File.WriteAllText(Gen() + "/SkyBuild_Report.txt", rep.ToString());
            AssetDatabase.Refresh();
            Debug.Log("[Lanbai/Sky] sky built\n" + rep);
        }

        public static Material BuildSkyMaterial(StringBuilder rep)
        {
            Shader sky = Shader.Find("Lanbai/Sky");
            if (sky == null) { Debug.LogError("[Lanbai/Sky] shader Lanbai/Sky not found (compile errors?)"); return null; }
            string path = Gen() + "/M_Sky.mat";
            Material mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(sky); AssetDatabase.CreateAsset(mat, path); }
            mat.shader = sky;
            Texture glow = AssetDatabase.LoadAssetAtPath<Texture>(SkyRoot() + "/Textures/StarSky_Glow_8192x4096.png");
            Texture moon = AssetDatabase.LoadAssetAtPath<Texture>(SkyRoot() + "/Textures/Moon_Disc_1024.png");
            if (glow != null) mat.SetTexture("_GlowTex", glow); else rep.AppendLine("  StarSky_Glow_8192x4096.png NOT FOUND");
            if (moon != null) mat.SetTexture("_MoonTex", moon); else rep.AppendLine("  Moon_Disc_1024.png NOT FOUND");
            mat.SetFloat("_Dither", 1f);
            EditorUtility.SetDirty(mat);
            rep.AppendLine("one material: " + path + " (all preset values arrive as _Udon_Sky_* globals, _Udon_SkyGlobals.x = 1)");
            return mat;
        }

        static Vector4 GetGlobal4(SkyPreset p, string k)
        {
            foreach (SkyKV4 kv in p.globalVectors) if (kv.k == k) return V4(kv.v);
            return Vector4.zero;
        }

        static Color Gamma(Vector4 lin)
        {
            return new Color(Mathf.LinearToGammaSpace(Mathf.Max(lin.x, 0f)), Mathf.LinearToGammaSpace(Mathf.Max(lin.y, 0f)),
                             Mathf.LinearToGammaSpace(Mathf.Max(lin.z, 0f)), 1f);
        }

        static Vector4 V4(float[] a)
        {
            return new Vector4(a.Length > 0 ? a[0] : 0f, a.Length > 1 ? a[1] : 0f, a.Length > 2 ? a[2] : 0f, a.Length > 3 ? a[3] : 0f);
        }

        static Cubemap FindCube(string name, out string path)
        {
            path = null;
            foreach (string id in AssetDatabase.FindAssets(name))
            {
                string p = AssetDatabase.GUIDToAssetPath(id);
                Cubemap c = AssetDatabase.LoadAssetAtPath<Cubemap>(p);
                if (c != null) { path = p; return c; }
            }
            return null;
        }

        // brightest pixel of a Radiance .hdr (after a 3x3 box) -> Unity direction with Unity's lat-long convention
        // (u = 0.5 - atan2(z, x) / 2pi, v = 1 - acos(y) / pi): the same mapping the cubemap importer uses.
        public static bool HdrSunDirection(string assetPath, out Vector3 dir)
        {
            dir = Vector3.forward;
            int w, h; float[] lum;
            if (!ReadHdrLuminance(assetPath, out w, out h, out lum)) return false;
            float best = -1f; int bx = 0, by = 0;
            for (int y = 1; y < h / 2; y++)
                for (int x = 0; x < w; x++)
                {
                    float s = 0f;
                    for (int dy = -1; dy <= 1; dy++)
                        for (int dx = -1; dx <= 1; dx++)
                            s += lum[(y + dy) * w + ((x + dx + w) % w)];
                    if (s > best) { best = s; bx = x; by = y; }
                }
            float u = (bx + 0.5f) / w, v = 1f - (by + 0.5f) / h;
            float phi = (0.5f - u) * 2f * Mathf.PI, theta = (1f - v) * Mathf.PI;
            dir = new Vector3(Mathf.Sin(theta) * Mathf.Cos(phi), Mathf.Cos(theta), Mathf.Sin(theta) * Mathf.Sin(phi));
            return true;
        }

        static bool ReadHdrLuminance(string assetPath, out int w, out int h, out float[] lum)
        {
            w = h = 0; lum = null;
            byte[] b = File.ReadAllBytes(assetPath);
            int pos = 0; string line;
            do
            {
                int e = Array.IndexOf(b, (byte)'\n', pos);
                if (e < 0) return false;
                line = Encoding.ASCII.GetString(b, pos, e - pos); pos = e + 1;
            } while (!(line.StartsWith("-Y") || line.StartsWith("+Y")));
            string[] t = line.Split(' ');
            h = int.Parse(t[1]); w = int.Parse(t[3]);
            bool flip = line.StartsWith("+Y");
            lum = new float[w * h];
            byte[] sc = new byte[w * 4];
            for (int y = 0; y < h; y++)
            {
                if (b[pos] == 2 && b[pos + 1] == 2 && w >= 8 && w < 32768)
                {
                    pos += 4;
                    for (int c = 0; c < 4; c++)
                    {
                        int x = 0;
                        while (x < w)
                        {
                            int n = b[pos++];
                            if (n > 128) { n -= 128; byte val = b[pos++]; for (int i = 0; i < n; i++) sc[(x + i) * 4 + c] = val; }
                            else { for (int i = 0; i < n; i++) sc[(x + i) * 4 + c] = b[pos++]; }
                            x += n;
                        }
                    }
                }
                else { Array.Copy(b, pos, sc, 0, w * 4); pos += w * 4; }
                int row = flip ? (h - 1 - y) : y;
                for (int x = 0; x < w; x++)
                {
                    int ex = sc[x * 4 + 3];
                    float f = ex > 0 ? (float)Math.Pow(2.0, ex - 136) : 0f;
                    lum[row * w + x] = f * (0.2126f * sc[x * 4] + 0.7152f * sc[x * 4 + 1] + 0.0722f * sc[x * 4 + 2]);
                }
            }
            return true;
        }


        // ---------------------------------------------------------------------------------------------------------
        // U# 1.x compiles only scripts that have a program asset (gate test pitfall 11): create it next to the script
        // (reflection, so this file does not need the UdonSharp editor assembly to compile), then one GameObject per
        // preset with a LanbaiSkyPreset filled from SkyPresets.json.
        [MenuItem("蓝白/Sky/Create Preset Objects")]
        public static void CreatePresetObjects()
        {
            BuildSky();
        }

        // a scene root by name, inactive ones included (GameObject.Find misses those and the builder made duplicates)
        public static GameObject FindRoot(string n, bool create)
        {
            foreach (GameObject g in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
                if (g.name == n) return g;
            if (!create) return null;
            GameObject r = new GameObject(n);
            Undo.RegisterCreatedObjectUndo(r, "蓝白 Sky build");
            return r;
        }

        static GameObject Child(GameObject root, string n)
        {
            Transform tr = root.transform.Find(n);
            if (tr != null) return tr.gameObject;
            GameObject go = new GameObject(n);
            Undo.RegisterCreatedObjectUndo(go, "蓝白 Sky build");
            go.transform.SetParent(root.transform, false);
            return go;
        }

        static string RotPath() { return Gen() + "/SkyBuild_Rotations.json"; }

        static void SaveRotations(Dictionary<string, float> rot)
        {
            List<SkyRot> l = new List<SkyRot>();
            foreach (KeyValuePair<string, float> kv in rot) l.Add(new SkyRot { preset = kv.Key, rotation = kv.Value });
            File.WriteAllText(RotPath(), JsonUtility.ToJson(new SkyRotFile { rotations = l.ToArray() }, true));
        }

        static Dictionary<string, float> LoadRotations()
        {
            Dictionary<string, float> d = new Dictionary<string, float>();
            if (!File.Exists(RotPath())) return d;
            SkyRotFile f = JsonUtility.FromJson<SkyRotFile>(File.ReadAllText(RotPath()));
            if (f != null && f.rotations != null) foreach (SkyRot r in f.rotations) d[r.preset] = r.rotation;
            return d;
        }

        static Vector4 PresetVector(SkyPreset p, int i, Dictionary<string, float> rot, bool hasCube)
        {
            Vector4 v = V4(p.globalVectors[i].v);
            if (p.globalVectors[i].k == "_Udon_Sky_RotationA" && rot.ContainsKey(p.name)) v.x = rot[p.name];
            if (p.globalVectors[i].k == "_Udon_SkyGlobals" && !hasCube) v.y = 0f;   // no HDRI here: procedural only
            return v;
        }

        static GameObject CreatePresetObjectsWith(SkyPresetFile pf, Material mat, Dictionary<string, float> rot, StringBuilder rep)
        {
            // updated in place (references from drivers to these objects survive a re-run); new presets are added,
            // objects of presets no longer in the JSON are removed (with Undo)
            GameObject root = FindRoot("Lanbai_SkyPresets", true);
            HashSet<string> keep = new HashSet<string>();
            foreach (SkyPreset p in pf.presets) keep.Add("SkyPreset_" + p.name);
            List<GameObject> stale = new List<GameObject>();
            foreach (Transform ch in root.transform) if (ch.name.StartsWith("SkyPreset_") && !keep.Contains(ch.name)) stale.Add(ch.gameObject);
            foreach (GameObject g in stale) { rep.AppendLine("  removed " + g.name + " (no longer in SkyPresets.json)"); Undo.DestroyObjectImmediate(g); }
            bool add = Lanbai.Udon.LanbaiUdonPrograms.Available;
            foreach (SkyPreset p in pf.presets)
            {
                GameObject go = Child(root, "SkyPreset_" + p.name);
                Lanbai.Sky.LanbaiSkyPreset c = go.GetComponent<Lanbai.Sky.LanbaiSkyPreset>();
                if (c == null)
                    c = (Lanbai.Sky.LanbaiSkyPreset)Lanbai.Udon.LanbaiUdonPrograms.AddComponent(go, typeof(Lanbai.Sky.LanbaiSkyPreset));
                c.presetName = p.name;
                c.skyMaterial = mat;
                c.cubeA = string.IsNullOrEmpty(p.cubeA) ? null : FindCube(p.cubeA, out string _);
                c.cubeB = null;
                Undo.RecordObject(c, "蓝白 Sky build");
                c.vectorNames = new string[p.globalVectors.Length]; c.vectorValues = new Vector4[p.globalVectors.Length];
                for (int i = 0; i < p.globalVectors.Length; i++)
                {
                    c.vectorNames[i] = p.globalVectors[i].k;
                    c.vectorValues[i] = PresetVector(p, i, rot, c.cubeA != null);
                }
                c.vecGroups = p.vecGroups; c.vecPartner = p.vecPartner; c.blendSkip = p.blendSkip;
                c.floatNames = new string[p.globalFloats.Length]; c.floatValues = new float[p.globalFloats.Length];
                for (int i = 0; i < p.globalFloats.Length; i++) { c.floatNames[i] = p.globalFloats[i].k; c.floatValues[i] = p.globalFloats[i].v; }
                // Built-in fog / ambient (only written when the act turns ownsAtmosphere on): the far horizon and the zenith
                c.fogColor = Gamma(GetGlobal4(p, "_Udon_HorizonColor"));
                c.ambientColor = Gamma(GetGlobal4(p, "_Udon_ZenithColor"));
                EditorUtility.SetDirty(c);
            }
            rep.AppendLine("preset objects under Lanbai_SkyPresets (" + pf.presets.Length + ")" + (!add ? "  (UdonSharp editor not found: plain AddComponent used)" : ""));
            return root;
        }

        // README_Sky §3.1: one LanbaiSkyDriver per continuous window, arrays from SkyPresets.json 'drivers' (cues.json t)
        static void CreateDrivers(SkyPresetFile pf, GameObject presetRoot, StringBuilder rep)
        {
            if (pf.drivers == null) return;
            foreach (SkyDriverDef d in pf.drivers)
            {
                GameObject go = FindRoot(d.name, true);
                Lanbai.Sky.LanbaiSkyDriver c = go.GetComponent<Lanbai.Sky.LanbaiSkyDriver>();
                if (c == null)
                    c = (Lanbai.Sky.LanbaiSkyDriver)Lanbai.Udon.LanbaiUdonPrograms.AddComponent(go, typeof(Lanbai.Sky.LanbaiSkyDriver));
                Undo.RecordObject(c, "蓝白 Sky build");
                int n = d.entries.Length;
                c.presets = new Lanbai.Sky.LanbaiSkyPreset[n]; c.presetT0 = new float[n]; c.presetT1 = new float[n]; c.fadeSec = new float[n];
                for (int i = 0; i < n; i++)
                {
                    Transform tr = presetRoot.transform.Find("SkyPreset_" + d.entries[i].preset);
                    c.presets[i] = (tr != null) ? tr.GetComponent<Lanbai.Sky.LanbaiSkyPreset>() : null;
                    if (c.presets[i] == null) rep.AppendLine("  " + d.name + ": preset " + d.entries[i].preset + " NOT FOUND");
                    c.presetT0[i] = d.entries[i].t0; c.presetT1[i] = d.entries[i].t1; c.fadeSec[i] = d.entries[i].fade;
                }
                c.root = null;   // the preset objects are shared by both drivers (and the clouds' driver): LanbaiActivate must not switch them (final review 4)
                EditorUtility.SetDirty(c);
                rep.AppendLine(string.Format(CultureInfo.InvariantCulture, "driver {0}: {1} entries, window {2:F2} .. {3:F2}", d.name, n, d.entries[0].t0, d.entries[n - 1].t1));
            }
        }

        // the ONE main star object of the film (acts 3, 4, 9 ...; tech r2 #4: act 9 used to make a second one)
        public static Renderer CreateStarObject(StringBuilder rep)
        {
            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(Gen() + "/StarPoints_BSC5.asset");
            Shader stars = Shader.Find("Lanbai/StarPoints");
            if (mesh == null || stars == null) { rep.AppendLine("stars: run 蓝白/Sky/Build Star Mesh first (or Lanbai/StarPoints does not compile)"); return null; }
            string sp = Gen() + "/M_Sky_StarPoints.mat";
            Material m = AssetDatabase.LoadAssetAtPath<Material>(sp);
            if (m == null) { m = new Material(stars); AssetDatabase.CreateAsset(m, sp); }
            m.shader = stars;
            m.SetFloat("_Gain", 0f);           // every preset writes _Udon_StarGain; the material alone draws nothing
            m.SetFloat("_UseGlobalGain", 1f);
            EditorUtility.SetDirty(m);
            GameObject go = FindRoot("Lanbai_Stars_BSC5", true);
            MeshFilter mf = go.GetComponent<MeshFilter>(); if (mf == null) mf = Undo.AddComponent<MeshFilter>(go);
            MeshRenderer mr = go.GetComponent<MeshRenderer>(); if (mr == null) mr = Undo.AddComponent<MeshRenderer>(go);
            mf.sharedMesh = mesh; mr.sharedMaterial = m;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;
            mr.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off; mr.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
            rep.AppendLine("stars: Lanbai_Stars_BSC5 (" + sp + ", _Gain 0)");
            return mr;
        }

        // D-41：建程序资产交给共用工具（不等初始化；要等就用 LanbaiUdonPrograms.RunWhenReady）。留着这个名字给别的包调
        public static void EnsureProgramAsset(string scriptName)
        {
            Type t = Lanbai.Udon.LanbaiUdonPrograms.TypeOfScript(scriptName);
            if (t == null) { Debug.LogWarning("[Lanbai/Sky] " + scriptName + ".cs 不在工程里或还没编译：没建程序资产"); return; }
            Lanbai.Udon.LanbaiUdonPrograms.CreateMissing("[Lanbai/Sky] " + scriptName, new[] { t }, Lanbai.Udon.LanbaiUdonPrograms.NextToScript);
        }

        // ---------------------------------------------------------------------------------------------------------
        public static string LastPreviewPreset;

        public static void ApplyPresetInEditor(SkyPreset p)
        {
            LastPreviewPreset = p.name;
            Material mat = AssetDatabase.LoadAssetAtPath<Material>(Gen() + "/M_Sky.mat");
            if (mat != null) RenderSettings.skybox = mat;
            ClearGlobals();
            Cubemap cube = string.IsNullOrEmpty(p.cubeA) ? null : FindCube(p.cubeA, out string _);
            if (cube != null) Shader.SetGlobalTexture("_Udon_SkyCubeTexA", cube);
            Dictionary<string, float> rot = LoadRotations();   // the same measured rotation the runtime objects carry
            foreach (SkyKV kv in p.globalFloats)
                Shader.SetGlobalFloat(kv.k, kv.v);
            for (int i = 0; i < p.globalVectors.Length; i++)
            {
                Vector4 v = PresetVector(p, i, rot, cube != null);
                if (p.globalVectors[i].k == "_Udon_Fog") RenderSettings.fogDensity = v.x;
                Shader.SetGlobalVector(p.globalVectors[i].k, v);
            }
            SceneView.RepaintAll();
        }

        // every global any preset writes (the union is in every preset) + the ones the sky reads but presets do not own
        public static void ClearGlobals()
        {
            SkyPresetFile pf = LoadPresets();
            foreach (SkyPreset p in pf.presets)
            {
                foreach (SkyKV4 kv in p.globalVectors) Shader.SetGlobalVector(kv.k, Vector4.zero);
                foreach (SkyKV kv in p.globalFloats) Shader.SetGlobalFloat(kv.k, 0f);
            }
            // (the presets write _Udon_FogCubeParams / _Udon_FogBase / _Udon_StarShape themselves; the gate's and the sea's
            // own names are theirs to reset when their windows end)
        }

        // ---------------------------------------------------------------------------------------------------------
        [MenuItem("蓝白/Sky/Bake Fog Cube From Skybox")]
        public static void BakeFogCube()
        {
            GameObject go = new GameObject("_LanbaiFogCubeBaker");
            go.hideFlags = HideFlags.HideAndDontSave;
            Camera cam = go.AddComponent<Camera>();
            cam.cullingMask = 0; cam.clearFlags = CameraClearFlags.Skybox; cam.allowHDR = true;
            cam.transform.position = Vector3.zero;
            Cubemap cube = new Cubemap(64, TextureFormat.RGBAHalf, true);
            bool ok = cam.RenderToCubemap(cube);
            UnityEngine.Object.DestroyImmediate(go);
            if (!ok) { Debug.LogError("[Lanbai/Sky] RenderToCubemap failed"); return; }
            cube.Apply(true);
            // one material for the film: name the cube after the preset last applied in the preview window (final review)
            string name = string.IsNullOrEmpty(LastPreviewPreset) ? (RenderSettings.skybox != null ? RenderSettings.skybox.name : "Sky") : LastPreviewPreset;
            string path = Gen() + "/FogCube_" + name + ".asset";
            AssetDatabase.CreateAsset(cube, path);
            AssetDatabase.SaveAssets();
            Debug.Log("[Lanbai/Sky] fog cube -> " + path + "  (driver: VRCShader.SetGlobalTexture(_Udon_FogCube); _Udon_FogCubeParams = (weight, mip 3, max el 20, 1))");
        }
    }

    public class LanbaiSkyPreviewWindow : EditorWindow
    {
        Vector2 scroll;
        SkyPresetFile pf;

        [MenuItem("蓝白/Sky/Preview Window")]
        static void Open() { GetWindow<LanbaiSkyPreviewWindow>("蓝白 Sky"); }

        void OnGUI()
        {
            if (pf == null || GUILayout.Button("Reload SkyPresets.json")) pf = LanbaiSkyBuild.LoadPresets();
            if (GUILayout.Button("Clear all sky / fog globals")) LanbaiSkyBuild.ClearGlobals();
            scroll = EditorGUILayout.BeginScrollView(scroll);
            foreach (SkyPreset p in pf.presets)
            {
                EditorGUILayout.BeginHorizontal();
                if (GUILayout.Button(p.name, GUILayout.Width(180))) LanbaiSkyBuild.ApplyPresetInEditor(p);
                EditorGUILayout.LabelField(p.acts + "  ·  " + p.profile);
                EditorGUILayout.EndHorizontal();
            }
            EditorGUILayout.EndScrollView();
            EditorGUILayout.HelpBox("Editor preview only: entering Play mode drops the globals (gate test pitfall 9). In the world the act driver (or LanbaiSkyPreset) writes them in Start / under occlusion.", MessageType.Info);
        }
    }
}
