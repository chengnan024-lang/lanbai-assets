// 蓝白 · Sky 导入设置（只管 Assets/Lanbai/Sky/Textures/ 里的文件）。
// !!! NOT COMPILED IN UNITY: Roslyn type-check against UnityEditor 2021.1 only (Sky/Tools~/compile_check/check_cs.sh). !!!
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Sky.EditorTools
{
    public class LanbaiSkyImport : AssetPostprocessor
    {
        public override uint GetVersion() { return 3; }   // bump when the settings change: Unity re-imports

        static bool Mine(string path)
        {
            return path.Replace('\\', '/').Contains("/Lanbai/Sky/Textures/");
        }

        static void Platform(TextureImporter ti, TextureImporterFormat fmt, int maxSize)
        {
            ti.maxTextureSize = maxSize;
            TextureImporterPlatformSettings ps = ti.GetPlatformTextureSettings("Standalone");
            ps.overridden = true;
            ps.format = fmt;
            ps.maxTextureSize = maxSize;
            ps.crunchedCompression = false;
            ti.SetPlatformTextureSettings(ps);
        }

        void OnPreprocessTexture()
        {
            if (!Mine(assetPath))
                return;
            TextureImporter ti = (TextureImporter)assetImporter;
            string f = Path.GetFileName(assetPath);
            if (f.StartsWith("Sky_Overcast_Night"))
            {
                // lat-long HDR -> cubemap (Unity's lat-long convention; the file was written for it)
                ti.textureType = TextureImporterType.Default;
                ti.textureShape = TextureImporterShape.TextureCube;
                ti.generateCubemap = TextureImporterGenerateCubemap.Cylindrical;
                ti.mipmapEnabled = true;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.filterMode = FilterMode.Trilinear;
                ti.anisoLevel = 0;
                Platform(ti, TextureImporterFormat.BC6H, 2048);
            }
            else if (f.StartsWith("StarSky_Glow"))
            {
                // world-frame lat-long sampled by Lanbai/Sky with its own mapping (LanbaiGalaxyUV), always mip 0:
                // no mips (no blur, bible §6·9), U repeats across the seam, V clamps at the poles.
                // 8-bit sRGB PNG normalised to 1 (the material's _GlowScale = Sky/Data/StarSky.json glow_scale)
                ti.textureType = TextureImporterType.Default;
                ti.textureShape = TextureImporterShape.Texture2D;
                ti.sRGBTexture = true;
                ti.mipmapEnabled = false;
                ti.wrapModeU = TextureWrapMode.Repeat;
                ti.wrapModeV = TextureWrapMode.Clamp;
                ti.filterMode = FilterMode.Bilinear;
                ti.anisoLevel = 0;
                ti.npotScale = TextureImporterNPOTScale.None;
                Platform(ti, TextureImporterFormat.BC7, 8192);
            }
            else if (f.StartsWith("Moon_Disc"))
            {
                ti.textureType = TextureImporterType.Default;
                ti.textureShape = TextureImporterShape.Texture2D;
                ti.sRGBTexture = true;
                ti.alphaIsTransparency = true;
                ti.mipmapEnabled = true;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.filterMode = FilterMode.Trilinear;
                ti.anisoLevel = 1;
                Platform(ti, TextureImporterFormat.BC7, 1024);
            }
        }
    }
}
