// 蓝白 · Sea kit (bible §8.1 #7): import settings for Assets/Lanbai/Sea/ only, and the materials of the four sea surfaces.
// !!! WRITTEN WITHOUT UNITY (cloud side). Type-checked with Roslyn against Unity reference assemblies only. !!!
// Menu: 蓝白/Sea/Create Materials  (re-runnable: updates the materials in place)
#if UNITY_EDITOR
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
                var pc = ti.GetPlatformTextureSettings("Standalone");
                pc.overridden = true;
                pc.format = TextureImporterFormat.BC6H;                                 // bible §1.6: BC6H, no crunch
                pc.maxTextureSize = 1536;
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

    public static class LanbaiSeaMaterials
    {
        public const string Root = "Assets/Lanbai/Sea";

        static Color Lin(float r, float g, float b) { return new Color(r, g, b, 0f); }

        static T Load<T>(string rel) where T : Object { return AssetDatabase.LoadAssetAtPath<T>(Root + "/" + rel); }

        /// one material per surface; mode = 0 Above, 1 Below, 2 Ceiling. transparent: null = by mode (Ceiling transparent)
        public static Material Make(string name, int mode) { return Make(name, mode, mode == 2); }

        public static Material Make(string name, int mode, bool transparent)
        {
            var sh = Shader.Find("Lanbai/Sea");
            if (sh == null) { Debug.LogError("[Lanbai Sea] shader Lanbai/Sea not found (did it compile?)"); return null; }
            Directory.CreateDirectory(Root + "/Materials");
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

        [MenuItem("蓝白/Sea/Create Materials")]
        public static void CreateAll()
        {
            // act 6 · sea mirror (the Sky places it; README_Sea接口 §4)
            var a = Make("M_06_Sea", 0);
            if (a != null) { a.SetVector("_WaterColor", Lin(0.0156f, 0.0484f, 0.0954f)); }
            // act 7a · the surface from below: Snell's window
            var b = Make("M_07a_SeaSurface", 1);
            if (b != null)
            {
                b.SetFloat("_AirSide", 1f);
                b.SetTexture("_WindowCube", Load<Cubemap>("Textures/Cube_Dawn_256.exr"));
                b.SetVector("_TIRColor", Lin(0.0222f, 0.0685f, 0.1651f));
            }
            // act 7c · the inverted window under the bus
            var c = Make("M_07c_SeaMirror", 1);
            if (c != null)
            {
                c.SetFloat("_AirSide", -1f);
                c.SetTexture("_WindowCube", Load<Cubemap>("Textures/Cube_DuskLower_256.exr"));
                c.SetFloat("_TIRCubeGain", 1f);
                c.SetFloat("_WindowGain", 0f);       // the driver opens it (F8b -> 897.96)
            }
            // act 8 · the sea ceiling (the Clouds session places it): Sea_Ceiling.fbx = Sea_Ceiling_Inner (r <= 2.4 km) +
            // Sea_Ceiling_Edge (2.4 .. 3.2 km). Inner = M_08_SeaCeiling (OPAQUE) until 956.36, then M_08_SeaCeilingFade;
            // Edge = M_08_SeaCeilingEdge (transparent, the soft 2.7 km edge) throughout. README_Sea接口 §2.4.
            CeilingCommon(Make("M_08_SeaCeiling", 2, false), false);
            CeilingCommon(Make("M_08_SeaCeilingEdge", 2, true), true);
            CeilingCommon(Make("M_08_SeaCeilingFade", 2, true), false);
            // act 11 · the hanging sea 80 m over the road (the Lamps session places it; Lamps/总导演意见.md §2)
            var h = Make("M_11_SeaHanging", 2, false);
            if (h != null)
            {
                h.SetVector("_WaterColor", Lin(0.0116f, 0.0296f, 0.0683f));
                h.SetVector("_DiscCenter", Vector4.zero);
                h.SetVector("_GerstnerAmp", new Vector4(0.6f, 0.35f, 0.15f, 0f));
                h.SetFloat("_LampGlints", 1f);
            }
            AssetDatabase.SaveAssets();
            Debug.Log("[Lanbai Sea] materials written to " + Root + "/Materials");
        }

        static void CeilingCommon(Material d, bool edge)
        {
            if (d == null) return;
            d.SetVector("_WaterColor", Lin(0.0116f, 0.0296f, 0.0683f));                 // #10263F <- fill #1C304B (S8)
            d.SetVector("_DiscCenter", edge ? new Vector4(0f, 0f, 2700f, 800f) : Vector4.zero);   // 2.7 km, 800 m band (>= 500, bible)
            d.SetFloat("_FogHeightFalloff", 120f);                                        // the warm dusk fog must not tint the water overhead violet (D-17)
            d.SetFloat("_NormalStrength", 0.25f);
            d.SetVector("_MirrorTint", new Vector4(1f, 1.2f, 0.85f, 0f));               // D-17: the mirror band to gold (h_ab 62)
            d.SetVector("_PurpleGuard", new Vector4(1f, 0.02f, 0f, 0f));
            d.SetFloat("_ReflClamp", 8f);
            d.SetTexture("_SkyBehindCube", Load<Cubemap>("Textures/Cube_Dusk_256.exr"));
        }
    }
}
#endif
