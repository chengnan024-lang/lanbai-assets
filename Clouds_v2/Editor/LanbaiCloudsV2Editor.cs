// =====================================================================================================
//  蓝白 · 云卡 v2 · 编辑器（导入设置 + 菜单 蓝白/Clouds v2/Build Materials）
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Roslyn-checked against the Unity 2022.3 reference assemblies only.
//
//  1. LanbaiCloudsV2Import (AssetPostprocessor, ONLY this folder: .../Clouds_v2/Textures/):
//       *_K.png : sRGB on, Alpha Is Transparency on, Clamp, mips on (Preserve Coverage off), Trilinear, aniso 2, BC7
//       *_S.png : sRGB on, no alpha, Clamp, mips on, Trilinear, BC7
//  2. Build Materials: reads Textures/cards_v2.json and for every card writes
//       Generated/Mesh_<card>.asset  : a quad with its pivot on the flat cloud base (x -0.5..0.5, y -base..1-base)
//       Generated/M_CloudV2_<card>.mat: Lanbai/CloudCard, textures, scales, the group's solved colours
//     Re-runnable: assets are updated in place. The act packages (Act06_Dawn, Act08_Dusk) place the cards; their
//     drivers write _Gain / _Alpha / _Mirror per renderer with MaterialPropertyBlocks.
// =====================================================================================================
#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Lanbai.CloudsV2
{
    public class LanbaiCloudsV2Import : AssetPostprocessor
    {
        static bool Mine(string path)
        {
            return path.Replace('\\', '/').Contains("/Clouds_v2/Textures/");
        }

        void OnPreprocessTexture()
        {
            if (!Mine(assetPath))
                return;
            var ti = (TextureImporter)assetImporter;
            string f = Path.GetFileNameWithoutExtension(assetPath);
            bool key = f.EndsWith("_K");
            bool sky = f.EndsWith("_S");
            if (!key && !sky)
                return;
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = true;
            ti.alphaSource = key ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
            ti.alphaIsTransparency = key;
            ti.wrapMode = TextureWrapMode.Clamp;
            ti.mipmapEnabled = true;
            ti.mipMapsPreserveCoverage = false;
            ti.filterMode = FilterMode.Trilinear;
            ti.anisoLevel = 2;
            ti.streamingMipmaps = false;
            ti.maxTextureSize = 2048;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            var pc = ti.GetPlatformTextureSettings("Standalone");
            pc.overridden = true;
            pc.format = TextureImporterFormat.BC7;
            pc.maxTextureSize = 2048;
            ti.SetPlatformTextureSettings(pc);
        }
    }

    [System.Serializable]
    public class CardInfo
    {
        public string name;
        public string set;
        public int[] size;
        public float cloud_base_v;
        public float kscale;
        public float sscale;
    }

    public static class LanbaiCloudsV2Builder
    {
        static string Kit()
        {
            string[] g = AssetDatabase.FindAssets("Lanbai_CloudCard t:Shader");
            foreach (string id in g)
            {
                string p = AssetDatabase.GUIDToAssetPath(id).Replace('\\', '/');
                if (p.EndsWith("/Clouds_v2/Shaders/Lanbai_CloudCard.shader"))
                    return p.Substring(0, p.Length - "/Shaders/Lanbai_CloudCard.shader".Length);
            }
            return "Assets/Lanbai/Clouds_v2";
        }

        // group of a card set: dawn -> "dawn"; duskU / duskD -> "dusk"
        static string Group(string set)
        {
            return set.StartsWith("dusk") ? "dusk" : set;
        }

        static Vector4 Vec(List<object> l)
        {
            return new Vector4(System.Convert.ToSingle(l[0]), System.Convert.ToSingle(l[1]), System.Convert.ToSingle(l[2]), 0f);
        }

        [MenuItem("蓝白/Clouds v2/Build Materials")]
        public static string BuildMaterials()
        {
            string kit = Kit();
            string texDir = kit + "/Textures";
            string genDir = kit + "/Generated";
            if (!AssetDatabase.IsValidFolder(genDir))
                AssetDatabase.CreateFolder(kit, "Generated");
            string jsonPath = Path.Combine(Path.GetDirectoryName(Application.dataPath), texDir, "cards_v2.json");
            if (!File.Exists(jsonPath))
                return "cards_v2.json not found at " + jsonPath;
            var root = MiniJson.Parse(File.ReadAllText(jsonPath)) as Dictionary<string, object>;
            var colours = root["colours"] as Dictionary<string, object>;
            var cards = root["cards"] as Dictionary<string, object>;
            Shader sh = Shader.Find("Lanbai/CloudCard");
            if (sh == null)
                return "shader Lanbai/CloudCard not found";
            var log = new System.Text.StringBuilder();
            foreach (var kv in cards)
            {
                var c = kv.Value as Dictionary<string, object>;
                string name = kv.Key;
                string set = (string)c["set"];
                float baseV = System.Convert.ToSingle(c["cloud_base_v"]);
                var size = c["size"] as List<object>;
                float aspect = System.Convert.ToSingle(size[1]) / System.Convert.ToSingle(size[0]);

                // mesh: unit width, height = aspect; pivot on the cloud base
                string meshPath = genDir + "/Mesh_" + name + ".asset";
                Mesh m = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
                bool newMesh = m == null;
                if (newMesh)
                    m = new Mesh();
                m.Clear();
                float y0 = -baseV * aspect, y1 = (1f - baseV) * aspect;
                m.vertices = new[] { new Vector3(-0.5f, y0, 0), new Vector3(0.5f, y0, 0), new Vector3(0.5f, y1, 0), new Vector3(-0.5f, y1, 0) };
                m.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
                m.triangles = new[] { 0, 2, 1, 0, 3, 2 };
                m.RecalculateNormals();
                m.bounds = new Bounds(new Vector3(0, 0.5f * (y0 + y1), 0), new Vector3(1.5f, 1.5f * (y1 - y0) + 0.5f, 1.5f));
                if (newMesh)
                    AssetDatabase.CreateAsset(m, meshPath);

                string matPath = genDir + "/M_CloudV2_" + name + ".mat";
                Material mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
                if (mat == null)
                {
                    mat = new Material(sh);
                    AssetDatabase.CreateAsset(mat, matPath);
                }
                mat.shader = sh;
                mat.SetTexture("_KeyTex", AssetDatabase.LoadAssetAtPath<Texture2D>(texDir + "/" + name + "_K.png"));
                mat.SetTexture("_SkyTex", AssetDatabase.LoadAssetAtPath<Texture2D>(texDir + "/" + name + "_S.png"));
                mat.SetVector("_KScale", new Vector4(System.Convert.ToSingle(c["kscale"]), System.Convert.ToSingle(c["sscale"]), 0, 0));
                var col = colours[Group(set)] as Dictionary<string, object>;
                mat.SetVector("_SunColor", Vec(col["SunColor"] as List<object>));
                mat.SetVector("_SkyUpColor", Vec(col["SkyUpColor"] as List<object>));
                mat.SetVector("_GroundColor", Vec(col["GroundColor"] as List<object>));
                mat.enableInstancing = true;
                EditorUtility.SetDirty(mat);
                EditorUtility.SetDirty(m);
                log.AppendLine(name + "  base_v " + baseV.ToString("0.000") + "  aspect " + aspect.ToString("0.000"));
            }
            AssetDatabase.SaveAssets();
            string s = "Clouds v2: " + cards.Count + " cards -> " + genDir + "\n" + log;
            Debug.Log(s);
            return s;
        }
    }

    // Minimal JSON reader (objects, arrays, numbers, strings, true/false/null): enough for cards_v2.json.
    public static class MiniJson
    {
        public static object Parse(string s)
        {
            int i = 0;
            return Val(s, ref i);
        }

        static void Ws(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        static object Val(string s, ref int i)
        {
            Ws(s, ref i);
            char ch = s[i];
            if (ch == '{')
            {
                var d = new Dictionary<string, object>();
                i++;
                Ws(s, ref i);
                if (s[i] == '}') { i++; return d; }
                while (true)
                {
                    Ws(s, ref i);
                    string k = (string)Val(s, ref i);
                    Ws(s, ref i);
                    i++; // ':'
                    d[k] = Val(s, ref i);
                    Ws(s, ref i);
                    if (s[i] == ',') { i++; continue; }
                    i++; // '}'
                    return d;
                }
            }
            if (ch == '[')
            {
                var l = new List<object>();
                i++;
                Ws(s, ref i);
                if (s[i] == ']') { i++; return l; }
                while (true)
                {
                    l.Add(Val(s, ref i));
                    Ws(s, ref i);
                    if (s[i] == ',') { i++; continue; }
                    i++; // ']'
                    return l;
                }
            }
            if (ch == '"')
            {
                var sb = new System.Text.StringBuilder();
                i++;
                while (s[i] != '"')
                {
                    if (s[i] == '\\')
                    {
                        i++;
                        char e = s[i];
                        if (e == 'u') { sb.Append((char)System.Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; }
                        else if (e == 'n') sb.Append('\n');
                        else if (e == 't') sb.Append('\t');
                        else sb.Append(e);
                    }
                    else sb.Append(s[i]);
                    i++;
                }
                i++;
                return sb.ToString();
            }
            if (s.Substring(i).StartsWith("true")) { i += 4; return true; }
            if (s.Substring(i).StartsWith("false")) { i += 5; return false; }
            if (s.Substring(i).StartsWith("null")) { i += 4; return null; }
            int st = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            return double.Parse(s.Substring(st, i - st), System.Globalization.CultureInfo.InvariantCulture);
        }
    }
}
#endif
