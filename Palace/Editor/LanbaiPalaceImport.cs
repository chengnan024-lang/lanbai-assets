// =====================================================================================================
//  LanbaiPalaceImport.cs   蓝白 · 第 7b 幕宫殿的导入设置（AssetPostprocessor，只管 Assets/Lanbai/Palace/）
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn), never in Unity. !!!
//  模型：米、材质留在模型里（只为了保住槽名）、关网格压缩；一般网格生成光照贴图 UV（uv2）；鱼、灯焰、远处灯点不生成（它们的 uv2 存着编号 / 种类 / flux）。
//        鱼、灯焰的包围盒放大（顶点在 shader 里移动：鱼绕大殿、灯焰展开成公告板），免得被视锥剔掉。
//  贴图：_Albedo sRGB；_Normal = 法线贴图；_Mask / 灯焰 / 灯晕线性；灯焰、灯晕不要 mipmap 偏移、Clamp。
//  CONTROL §6 第 8 条：Project Settings → Player → Vertex Compression 里 TexCoord0–3 的压缩要关（鱼的编号在 uv2 里）。
// =====================================================================================================
using UnityEditor;
using UnityEngine;

public class LanbaiPalaceImport : AssetPostprocessor
{
    const string Root = "Assets/Lanbai/Palace/";

    static bool Mine(string p) { return p.Replace('\\', '/').StartsWith(Root); }

    void OnPreprocessModel()
    {
        if (!Mine(assetPath)) return;
        var mi = (ModelImporter)assetImporter;
        mi.globalScale = 1f;
        mi.useFileScale = true;
        // 材质按 FBX 里的名字留在模型里（M_07b_<槽>），搭建脚本按名字换成 Palace/Materials 的材质
        mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
        mi.meshCompression = ModelImporterMeshCompression.Off;
        mi.isReadable = false;
        mi.importAnimation = false;
        mi.importBlendShapes = false;
        mi.importCameras = false;
        mi.importLights = false;
        mi.optimizeMeshVertices = true;
        mi.importNormals = ModelImporterNormals.Import;
        mi.importTangents = ModelImporterTangents.CalculateMikk;
        bool special = assetPath.EndsWith("Palace_Fish.fbx") || assetPath.EndsWith("Palace_Flames.fbx") || assetPath.EndsWith("PalaceSpecks_Points.fbx");
        bool noLightmapUV = special;
        mi.generateSecondaryUV = !noLightmapUV;
        if (special)
        {
            mi.optimizeMeshVertices = false;       // 鱼 / 灯焰：顶点顺序与编号对应，别重排（也别焊接：灯焰四个角在同一点）
            mi.weldVertices = false;
        }
    }

    void OnPostprocessModel(GameObject g)
    {
        if (!Mine(assetPath)) return;
        float grow = 0f;
        if (assetPath.EndsWith("Palace_Fish.fbx")) grow = 60f;          // 环面 35 + 9，B 群一路游走：用一个大盒子
        if (assetPath.EndsWith("Palace_Flames.fbx")) grow = 4f;         // 公告板展开 1.5 m + 最小像素放大
        if (grow <= 0f) return;
        foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
        {
            var m = mf.sharedMesh;
            if (m == null) continue;
            var b = m.bounds;
            if (assetPath.EndsWith("Palace_Fish.fbx"))
                b = new Bounds(new Vector3(-30f, 14f, 300f), new Vector3(140f, 70f, 260f));
            else
                b.Expand(grow);
            m.bounds = b;
        }
    }

    void OnPreprocessTexture()
    {
        if (!Mine(assetPath)) return;
        var ti = (TextureImporter)assetImporter;
        string n = System.IO.Path.GetFileNameWithoutExtension(assetPath);
        ti.mipmapEnabled = true;
        ti.anisoLevel = 4;
        ti.wrapMode = TextureWrapMode.Repeat;
        ti.sRGBTexture = n.EndsWith("_Albedo");
        ti.textureType = n.EndsWith("_Normal") ? TextureImporterType.NormalMap : TextureImporterType.Default;
        ti.crunchedCompression = true;
        ti.compressionQuality = n.EndsWith("_Normal") ? 100 : 90;      // 圣经 §1.9：DXT Crunch 90–100，法线 100
        ti.maxTextureSize = 2048;
        if (n.StartsWith("T_07b_Flame") || n.StartsWith("T_07b_Halo"))
        {
            ti.sRGBTexture = false;
            ti.wrapMode = TextureWrapMode.Clamp;
            ti.crunchedCompression = false;
            ti.textureCompression = TextureImporterCompression.Uncompressed;
        }
    }
}
