// Lanbai / 蓝白 -- import settings for the cabin and the bus (Cabin/ and Bus/ only; CONTROL §2.3 'only your folders').
// UNCOMPILED (cloud side): Roslyn type-check only (Common/Tools~/compile_check/check_cs.sh, editor pass).
//
//   textures  albedo sRGB (default); normals (*_N_*) = NormalMap, linear; masks (*_M_*) linear; the tube light map
//             (*TubeLM*) linear RGBAHalf, no compression, clamp, bilinear; detail maps wrap repeat, aniso 4.
//             The radio dial (Cabin_RadioDial_*) is sRGB (RGB = the face albedo; A = backlight mask, alpha is linear anyway).
//   models    keep uv1 (never generate secondary UVs over it: _CabinTubeLM lives there), mesh compression off,
//             vertex colours kept, tangents MikkTSpace. CONTROL §6 pitfall 8: Player Settings 'Vertex Compression'
//             must not compress TexCoord0..3 - a project setting this script cannot read: README step.
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public class LanbaiCabinImport : AssetPostprocessor
{
    private const string CabinRoot = "Assets/Lanbai/Cabin/";
    private const string BusRoot = "Assets/Lanbai/Bus/";

    private static bool Mine(string path)
    {
        return path.StartsWith(CabinRoot) || path.StartsWith(BusRoot);
    }

    void OnPreprocessTexture()
    {
        if (!Mine(assetPath)) return;
        TextureImporter ti = (TextureImporter)assetImporter;
        string name = System.IO.Path.GetFileNameWithoutExtension(assetPath);

        if (name.Contains("TubeLM"))
        {
            // _CabinTubeLM: RGB = tube E (linear HDR), A = AO. Baked in Blender (Bus/Source/bake_lightmap.py), not in Unity.
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = false;
            ti.alphaSource = TextureImporterAlphaSource.FromInput;
            ti.alphaIsTransparency = false;
            ti.mipmapEnabled = true;
            ti.wrapMode = TextureWrapMode.Clamp;
            ti.filterMode = FilterMode.Bilinear;
            ti.textureCompression = TextureImporterCompression.Uncompressed;
            TextureImporterPlatformSettings ps = ti.GetDefaultPlatformTextureSettings();
            ps.format = TextureImporterFormat.RGBAHalf;
            ps.textureCompression = TextureImporterCompression.Uncompressed;
            ps.overridden = true;
            ti.SetPlatformTextureSettings(ps);
            TextureImporterPlatformSettings pc = ti.GetPlatformTextureSettings("Standalone");
            pc.overridden = true;
            pc.format = TextureImporterFormat.RGBAHalf;
            pc.textureCompression = TextureImporterCompression.Uncompressed;
            ti.SetPlatformTextureSettings(pc);
            return;
        }
        if (name.Contains("_N_") || name.EndsWith("_N"))
        {
            ti.textureType = TextureImporterType.NormalMap;
            ti.sRGBTexture = false;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.anisoLevel = 4;
            ti.mipmapEnabled = true;
            return;
        }
        if (name.Contains("_M_") || name.EndsWith("_M") || name.Contains("Mask"))
        {
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = false;
            ti.alphaIsTransparency = false;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.anisoLevel = 4;
            ti.mipmapEnabled = true;
            return;
        }
        // everything else: colour (albedo, the radio dial face, the destination blind), sRGB
        ti.sRGBTexture = true;
        ti.alphaIsTransparency = false;
        ti.mipmapEnabled = true;
        ti.anisoLevel = 4;
    }

    void OnPreprocessModel()
    {
        if (!Mine(assetPath)) return;
        ModelImporter mi = (ModelImporter)assetImporter;
        mi.generateSecondaryUV = false;                 // uv1 = the _CabinTubeLM atlas: never overwrite it
        mi.meshCompression = ModelImporterMeshCompression.Off;
        mi.importNormals = ModelImporterNormals.Import;
        mi.importTangents = ModelImporterTangents.CalculateMikk;
        mi.importBlendShapes = false;
        mi.importAnimation = false;
        mi.importCameras = false;
        mi.importLights = false;
        mi.isReadable = false;
        mi.optimizeMeshVertices = true;
        mi.optimizeMeshPolygons = true;
        mi.weldVertices = false;                        // seams of uv0 (metric box projection) and uv1 stay split

        // CONTROL §6 pitfall 8: Project Settings > Player > Vertex Compression must leave TexCoord0..3 uncompressed
        // (uv0 metric detail tiling, uv1 the _CabinTubeLM atlas). There is no public API to read that mask from here,
        // so it is a README step (Cabin/README.md §1), not a check.
    }
}
#endif
