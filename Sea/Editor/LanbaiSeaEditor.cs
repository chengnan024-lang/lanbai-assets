// 蓝白 · Sea kit (bible §8.1 #7): import settings for Assets/Lanbai/Sea/ only, and the materials of the sea surfaces.
// !!! WRITTEN WITHOUT UNITY (cloud side). Type-checked with Roslyn against Unity reference assemblies only. !!!
// Menu: 蓝白/Sea/Create Materials  (re-runnable: updates the materials in place). Every number comes from
// Assets/Lanbai/Sea/SeaMaterials.json (the same file the reference frames read; README_Sea接口 §2.3 explains each).
#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Lanbai.Sea.Editor
{
    /// Import settings for this folder only (CONTROL §2.3). Other folders are never touched.
    public class LanbaiSeaImport : AssetPostprocessor
    {
        const string Root = "Assets/Lanbai/Sea/";

        static bool Mine(string path) { return path.Replace('\\', '/').StartsWith(Root); }

        void OnPreprocessTexture()
        {
            if (!Mine(assetPath)) return;
            var ti = (TextureImporter)assetImporter;
            string n = Path.GetFileNameWithoutExtension(assetPath);
            ti.mipmapEnabled = true;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.filterMode = FilterMode.Trilinear;
            ti.anisoLevel = 1;                      // the shader folds what the mip chain averages into roughness (it assumes isotropic mips)
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            if (n.StartsWith("SeaN_"))
            {
                ti.textureType = TextureImporterType.NormalMap;            // BC5 on PC with CompressedHQ
                ti.sRGBTexture = false;
                ti.maxTextureSize = 1024;
            }
            else if (n.StartsWith("Caustics_"))
            {
                ti.textureType = TextureImporterType.SingleChannel;
                var s = new TextureImporterSettings();
                ti.ReadTextureSettings(s);
                s.singleChannelComponent = TextureImporterSingleChannelComponent.Red;
                ti.SetTextureSettings(s);
                ti.sRGBTexture = false;
                ti.maxTextureSize = 2048;
                ti.textureCompression = TextureImporterCompression.Uncompressed;   // R8: the bright net is 1-2 texels wide
                ti.anisoLevel = 2;
            }
            else if (n.StartsWith("CausticsCookie_"))
            {
                // the static fallback cookie of the 7a sun: a built-in directional cookie reads ALPHA (the PNG carries it)
                ti.textureType = TextureImporterType.Cookie;
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
                ti.sRGBTexture = false;
                ti.maxTextureSize = 256;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
            }
            else if (n.StartsWith("Sea_PurpleCeiling"))
            {
                // the purple guard's lookup (LanbaiSea.cginc): exact values, bilinear, no mips, hue wraps, lightness clamps
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = false;
                ti.mipmapEnabled = false;
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
                ti.filterMode = FilterMode.Bilinear;
                ti.anisoLevel = 0;
                ti.wrapModeU = TextureWrapMode.Repeat;
                ti.wrapModeV = TextureWrapMode.Clamp;
                ti.npotScale = TextureImporterNPOTScale.None;
                ti.maxTextureSize = 512;
                ti.textureCompression = TextureImporterCompression.Uncompressed;   // RGBA32: a compressed ceiling would let violet through
            }
            else if (n.StartsWith("SeaMacro_") || n.StartsWith("ShaftStreaks_"))
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = false;
                ti.maxTextureSize = 512;
            }
            else if (n.StartsWith("Cube_"))
            {
                ti.textureType = TextureImporterType.Default;
                ti.textureShape = TextureImporterShape.TextureCube;
                var s = new TextureImporterSettings();
                ti.ReadTextureSettings(s);
                s.generateCubemap = TextureImporterGenerateCubemap.AutoCubemap;         // 6-frame horizontal strip
                s.cubemapConvolution = TextureImporterCubemapConvolution.Specular;    // rough lookups read blurred mips
                ti.SetTextureSettings(s);
                ti.sRGBTexture = false;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.anisoLevel = 0;
                int face = n.EndsWith("_256") ? 256 : 2048;                            // the fallbacks are 256 per face
                ti.maxTextureSize = face;
                var pc = ti.GetPlatformTextureSettings("Standalone");
                pc.overridden = true;
                pc.format = TextureImporterFormat.BC6H;                                 // bible §1.6: BC6H, no crunch
                pc.maxTextureSize = face;
                ti.SetPlatformTextureSettings(pc);
            }
        }

        void OnPreprocessModel()
        {
            if (!Mine(assetPath)) return;
            var mi = (ModelImporter)assetImporter;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.isReadable = false;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.None;            // the sea builds its normal itself
            mi.generateSecondaryUV = false;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importAnimation = false;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
        }
    }

    // ---- SeaMaterials.json (JsonUtility: arrays of small records, no dictionaries) ----
    [Serializable] public class SeaSet { public string k; public float[] v; }
    [Serializable] public class SeaTex { public string k; public string path; }
    [Serializable] public class SeaMat
    {
        public string name; public int mode; public bool transparent; public string ceiling;
        public SeaSet[] set; public SeaTex[] tex;
    }
    [Serializable] public class SeaCeilingCommon { public SeaSet[] set; public SeaSet[] inner; public SeaSet[] edge; public SeaTex[] tex; }
    [Serializable] public class SeaMaterialsFile { public int version; public SeaMat[] materials; public SeaCeilingCommon ceiling_common; }

    public static class LanbaiSeaMaterials
    {
        public const string Root = "Assets/Lanbai/Sea";

        static T Load<T>(string rel) where T : UnityEngine.Object { return AssetDatabase.LoadAssetAtPath<T>(Root + "/" + rel); }

        static void EnsureFolder()
        {
            if (!AssetDatabase.IsValidFolder(Root + "/Materials")) AssetDatabase.CreateFolder(Root, "Materials");
        }

        /// one material per surface; mode = 0 Above, 1 Below, 2 Ceiling
        public static Material Make(string name, int mode, bool transparent)
        {
            var sh = Shader.Find("Lanbai/Sea");
            if (sh == null) { Debug.LogError("[Lanbai Sea] shader Lanbai/Sea not found (did it compile?)"); return null; }
            EnsureFolder();
            string path = Root + "/Materials/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
            m.shader = sh;
            m.SetTexture("_NormalLarge", Load<Texture2D>("Textures/SeaN_Large_1024.png"));
            m.SetTexture("_NormalSmall", Load<Texture2D>("Textures/SeaN_Small_1024.png"));
            m.SetTexture("_Macro", Load<Texture2D>("Textures/SeaMacro_512.png"));
            m.SetFloat("_SEA", mode);
            m.DisableKeyword("_SEA_ABOVE"); m.DisableKeyword("_SEA_BELOW"); m.DisableKeyword("_SEA_CEILING");
            m.EnableKeyword(mode == 0 ? "_SEA_ABOVE" : mode == 1 ? "_SEA_BELOW" : "_SEA_CEILING");
            m.SetFloat("_SrcBlend", (float)(transparent ? BlendMode.SrcAlpha : BlendMode.One));
            m.SetFloat("_DstBlend", (float)(transparent ? BlendMode.OneMinusSrcAlpha : BlendMode.Zero));
            m.SetFloat("_ZWrite", transparent ? 0f : 1f);
            m.SetFloat("_Cull", (float)CullMode.Off);
            m.renderQueue = transparent ? 2990 : 2000;
            m.SetOverrideTag("RenderType", transparent ? "Transparent" : "Opaque");
            EditorUtility.SetDirty(m);
            return m;
        }

        static void Apply(Material m, SeaSet[] sets)
        {
            if (sets == null) return;
            foreach (var s in sets)
            {
                if (s.v == null || s.v.Length == 0) continue;
                if (!m.HasProperty(s.k)) { Debug.LogWarning("[Lanbai Sea] " + m.name + ": no property " + s.k); continue; }
                if (s.v.Length == 1) m.SetFloat(s.k, s.v[0]);
                else m.SetVector(s.k, new Vector4(s.v[0], s.v.Length > 1 ? s.v[1] : 0f, s.v.Length > 2 ? s.v[2] : 0f, s.v.Length > 3 ? s.v[3] : 0f));
            }
        }

        static void ApplyTex(Material m, SeaTex[] texs)
        {
            if (texs == null) return;
            foreach (var t in texs)
            {
                var tex = Load<Texture>(t.path);
                if (tex == null) Debug.LogError("[Lanbai Sea] " + m.name + ": texture not found " + Root + "/" + t.path);
                m.SetTexture(t.k, tex);
            }
        }

        // ---- editor-only previews of the _Udon_ globals the drivers will write (README_Sea §0). Shader.SetGlobal* in edit
        // mode lasts until the next domain reload / Play (CONTROL §6.9): click again after a recompile.
        [MenuItem("蓝白/Sea/Preview Globals/A · 7a Snell window (underwater)")]
        public static void PreviewA()
        {
            Shader.SetGlobalFloat("_Udon_Underwater", 1f);
            Shader.SetGlobalVector("_Udon_WaterFogUp", new Vector4(0.0084f, 0.0267f, 0.0639f, 1f));      // #294B72 x 0.38
            Shader.SetGlobalVector("_Udon_WaterFogMid", new Vector4(0.184f, 0.352f, 0.644f, 1f));       // #77A0D2 (bible 0-15 m)
            Shader.SetGlobalVector("_Udon_WaterFogDown", new Vector4(0.0159f, 0.0733f, 0.1275f, 1f));
            Shader.SetGlobalVector("_Udon_Fog", new Vector4(0.040f, 0f, 0f, 1f));                        // F2h..: 0.040 /m
            Shader.SetGlobalVector("_Udon_FogBase", Vector4.zero);
            Fog(0.040f, new Color(0.184f, 0.352f, 0.644f));
            Debug.Log("[Lanbai Sea] preview A: underwater globals set (eye ~6.3 m under the plane, look up 60 deg; compare Docs~/iterations/29_K2_r06)");
        }

        [MenuItem("蓝白/Sea/Preview Globals/B · 6 sea mirror")]
        public static void PreviewB()
        {
            Shader.SetGlobalFloat("_Udon_Underwater", 0f);
            Shader.SetGlobalTexture("_Udon_ReflCube", Load<Cubemap>("Textures/Cube_Dawn_256.exr"));
            Shader.SetGlobalVector("_Udon_ReflCube_HDR", new Vector4(1f, 1f, 0f, 0f));
            Shader.SetGlobalFloat("_Udon_ReflExposure", 1f);
            Shader.SetGlobalVector("_Udon_SunDir", new Vector4(0.4973f, 0.1045f, 0.8613f, 1f));          // D-12: az +30, el +6
            Shader.SetGlobalVector("_Udon_SunDisc", new Vector4(1f, 0.265f, 0f, 1f));                    // D-18: 0.53 deg
            Shader.SetGlobalVector("_Udon_Fog", new Vector4(0.00012f, 0f, 0f, 1f));                      // bible §6·6
            Shader.SetGlobalVector("_Udon_FogBase", Vector4.zero);
            Fog(0.00012f, new Color(1.0f, 0.776f, 0.871f) * 1.24f);                                     // #FFE4F0 @ +0.31
            var cam = Camera.main;
            if (cam != null) cam.farClipPlane = 45000f;                                                   // bible: 45 km
            Debug.Log("[Lanbai Sea] preview B: dawn cube, sun, fog, far clip 45 km (eye 70 m over the plane, pitch -10; compare 33_K1_r05fwd)");
        }

        [MenuItem("蓝白/Sea/Preview Globals/Clear")]
        public static void PreviewClear()
        {
            Shader.SetGlobalFloat("_Udon_Underwater", 0f);
            Shader.SetGlobalVector("_Udon_Fog", Vector4.zero);
            Shader.SetGlobalVector("_Udon_SunDir", Vector4.zero);
            Shader.SetGlobalVector("_Udon_SunDisc", Vector4.zero);
            Shader.SetGlobalVector("_Udon_ReflCube_HDR", Vector4.zero);
        }

        static void Fog(float density, Color c)
        {
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;
            RenderSettings.fogDensity = density;
            RenderSettings.fogColor = c;
        }

        [MenuItem("蓝白/Sea/Create Materials")]
        public static void CreateAll()
        {
            var ta = Load<TextAsset>("SeaMaterials.json");
            if (ta == null) { Debug.LogError("[Lanbai Sea] " + Root + "/SeaMaterials.json not found"); return; }
            var f = JsonUtility.FromJson<SeaMaterialsFile>(ta.text);
            foreach (var e in f.materials)
            {
                var m = Make(e.name, e.mode, e.transparent);
                if (m == null) return;
                if (!string.IsNullOrEmpty(e.ceiling) && f.ceiling_common != null)
                {
                    // act 8: Sea_Ceiling.fbx = Sea_Ceiling_Inner (r <= 2.3 km) + Sea_Ceiling_Edge (2.3 .. 3.2 km). Inner =
                    // M_08_SeaCeiling (OPAQUE) until 956.36, then M_08_SeaCeilingFade; Edge = M_08_SeaCeilingEdge. §2.4
                    Apply(m, f.ceiling_common.set);
                    Apply(m, e.ceiling == "edge" ? f.ceiling_common.edge : f.ceiling_common.inner);
                    ApplyTex(m, f.ceiling_common.tex);
                }
                Apply(m, e.set);
                ApplyTex(m, e.tex);
                EditorUtility.SetDirty(m);
            }
            AssetDatabase.SaveAssets();
            Debug.Log("[Lanbai Sea] " + f.materials.Length + " materials written to " + Root + "/Materials (from SeaMaterials.json v" + f.version + ")");
        }
    }
}
#endif
