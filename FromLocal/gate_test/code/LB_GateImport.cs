// ═══════════════════════════════════════════════════════════════════
//  蓝白 · 触手之门导入测试（只给测试场景用）
//  导入设置：按 Gate/README_GateLayout.md §9、Tentacles/README_Tentacles.md §4、Tear/README_Tear.md §2 / §4
//  只管 Assets/Lanbai/Gate、Assets/Lanbai/Tentacles、Assets/Lanbai/Tear 下面的文件，别的一概不碰。
// ═══════════════════════════════════════════════════════════════════
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Tests
{
    public class LB_GateImport : AssetPostprocessor
    {
        static bool InKits(string p)
        {
            return p.StartsWith("Assets/Lanbai/Gate/") || p.StartsWith("Assets/Lanbai/Tentacles/") || p.StartsWith("Assets/Lanbai/Tear/");
        }

        void OnPreprocessModel()
        {
            if (!InKits(assetPath)) return;
            var mi = (ModelImporter)assetImporter;
            mi.globalScale = 1f;
            mi.useFileUnits = true;              // Convert Units 开
            mi.bakeAxisConversion = false;       // 导出时已经烘好了
            mi.importBlendShapes = false;
            mi.importVisibility = false;
            mi.importCameras = false;
            mi.importLights = false;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.isReadable = false;               // Read/Write 关
            mi.optimizeMeshPolygons = true;
            mi.optimizeMeshVertices = true;
            mi.addCollider = false;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.CalculateMikk;
            mi.generateSecondaryUV = false;      // 必须关：会覆盖 UV1 / UV2
            mi.animationType = ModelImporterAnimationType.None;
            mi.importAnimation = false;
            // 远潮要知道每个子网格对应哪张图集，所以留着 FBX 里的材质名（嵌在模型里，不往外抽文件）；其余手动指定材质
            if (Path.GetFileName(assetPath) == "TentacleTide_v2.fbx")
            {
                mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
                mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
            }
            else mi.materialImportMode = ModelImporterMaterialImportMode.None;
        }

        void OnPreprocessTexture()
        {
            if (!InKits(assetPath)) return;
            var ti = (TextureImporter)assetImporter;
            string n = Path.GetFileNameWithoutExtension(assetPath);
            ti.mipmapEnabled = true;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            int max = 2048;
            var fmt = TextureImporterFormat.BC7;

            if (n == "T_Tentacle_Albedo")
            {
                Set(ti, TextureImporterType.Default, true, TextureWrapMode.Repeat, 8); max = 2048;
            }
            else if (n == "T_Tentacle_Normal")
            {
                Set(ti, TextureImporterType.NormalMap, false, TextureWrapMode.Repeat, 8); max = 2048; fmt = TextureImporterFormat.BC5;
            }
            else if (n == "T_Tentacle_MetallicSmoothness")
            {
                Set(ti, TextureImporterType.Default, false, TextureWrapMode.Repeat, 1);
                ti.alphaSource = TextureImporterAlphaSource.FromInput; ti.alphaIsTransparency = false; max = 2048;
            }
            else if (n == "T_Tentacle_DetailNormal")
            {
                Set(ti, TextureImporterType.NormalMap, false, TextureWrapMode.Repeat, 8); max = 1024; fmt = TextureImporterFormat.BC5;
            }
            else if (n.EndsWith("_Occlusion"))   // T_Tentacle_X_Occlusion、T_Gate_X_Occlusion：按 (U, t) 采样，U 平铺、V 夹住
            {
                Set(ti, TextureImporterType.Default, false, TextureWrapMode.Repeat, 1);
                ti.wrapModeU = TextureWrapMode.Repeat; ti.wrapModeV = TextureWrapMode.Clamp; max = 1024;
            }
            else if (n.StartsWith("TentacleTide_") && n.Contains("Atlas"))
            {
                Set(ti, TextureImporterType.Default, true, TextureWrapMode.Clamp, 1);
                ti.alphaIsTransparency = true; max = 2048;
            }
            else if (n == "Tear_CloudLanes_1024")      // 光池的阴影道：shader 里当线性数据读
            {
                Set(ti, TextureImporterType.Default, false, TextureWrapMode.Clamp, 1); max = 1024;
            }
            else if (n.StartsWith("Tear_Emission") || n.StartsWith("Tear_Rip") || n.StartsWith("Tear_SkyFolds") || n.StartsWith("Halo_"))
            {
                Set(ti, TextureImporterType.Default, true, TextureWrapMode.Clamp, n.StartsWith("Tear_Emission") ? 4 : 1);
                ti.alphaIsTransparency = false;          // 重要：A = 0 的地方仍有颜色
                max = 2048;
            }
            else if (n.StartsWith("Tear_Flaps"))
            {
                Set(ti, TextureImporterType.Default, false, TextureWrapMode.Clamp, 4);
                ti.alphaIsTransparency = false; ti.mipMapsPreserveCoverage = true; ti.alphaTestReferenceValue = 0.5f; max = 1024;
            }
            else if (n.StartsWith("Shaft_Gradient") || n.StartsWith("Tear_FootSkyline"))
            {
                Set(ti, TextureImporterType.Default, false, TextureWrapMode.Clamp, 1);
                ti.alphaIsTransparency = false; max = 1024;
            }
            else return;                                  // 其余（没用到的）保持 Unity 默认

            var ps = ti.GetPlatformTextureSettings("Standalone");
            ps.overridden = true;
            ps.maxTextureSize = max;
            ps.format = fmt;
            ps.textureCompression = TextureImporterCompression.CompressedHQ;
            ti.SetPlatformTextureSettings(ps);
            ti.maxTextureSize = max;
        }

        // 触手的贴图：README_Tentacles §4 写的是 Trilinear；裂口的贴图 README 没写过滤方式，保持 Unity 默认（Bilinear）
        static void Set(TextureImporter ti, TextureImporterType type, bool srgb, TextureWrapMode wrap, int aniso)
        {
            ti.textureType = type;
            ti.sRGBTexture = srgb;
            ti.wrapMode = wrap;
            ti.filterMode = ti.assetPath.StartsWith("Assets/Lanbai/Tear/") ? FilterMode.Bilinear : FilterMode.Trilinear;
            ti.anisoLevel = aniso;
        }
    }
}
