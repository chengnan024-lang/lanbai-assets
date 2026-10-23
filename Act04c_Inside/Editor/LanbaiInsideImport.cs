// Lanbai / 蓝白 -- import settings for Assets/Lanbai/Act04c_Inside/ ONLY (gate test pitfall: a postprocessor that touches
// every model re-imports the whole project). UNCOMPILED (cloud side).
//  Models: no mesh compression (UV1 carries metres to the edge / along the edge; the loose threads carry their motion in
//  UV1-3), read/write off, normals imported, no lightmap UVs (they would overwrite UV1), no materials / cameras / lights /
//  animation. Inside_Extras: the dot quad and the loose threads are moved in the vertex shader, so their mesh bounds are
//  enlarged (otherwise Unity culls them where they were modelled).
//  Textures: linear (sRGB off), mip-mapped, Inside_Fringe wraps U / clamps V, aniso 4, BC7.
//  PROJECT SETTING (not touched here, README §0): Player > Vertex Compression: untick TexCoord0..3.
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

namespace Lanbai.Inside.Editor
{
    public class LanbaiInsideImport : AssetPostprocessor
    {
        const string Root = "Assets/Lanbai/Act04c_Inside/";

        // bump when the postprocessing changes, so models imported before (e.g. Skylight_Spot without its bounds) re-import
        public override uint GetVersion() { return 2; }

        void OnPreprocessModel()
        {
            if (!assetPath.StartsWith(Root)) return;
            var mi = (ModelImporter)assetImporter;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.isReadable = false;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.None;
            mi.generateSecondaryUV = false;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importAnimation = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.weldVertices = false;
            mi.optimizeMeshVertices = false;
            mi.globalScale = 1f;
        }

        void OnPostprocessModel(GameObject g)
        {
            if (!assetPath.StartsWith(Root)) return;
            if (assetPath.EndsWith("Skylight_Spot.fbx"))
            {
                // 总导演终审 #8: the spot / beam / dust are placed in the vertex shader from the tear: the modelled
                // bounds are a point; give them the volume they can occupy (the aisle and the skylight shaft)
                foreach (var mf in g.GetComponentsInChildren<MeshFilter>(true))
                    if (mf.sharedMesh != null) mf.sharedMesh.bounds = new Bounds(new Vector3(0.5f, 1.6f, 1.0f), new Vector3(12f, 6f, 20f));
                return;
            }
            if (!assetPath.EndsWith("Inside_Extras.fbx")) return;
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>(true))
            {
                if (mf.sharedMesh == null) continue;
                if (mf.name == "Inside_Dot") mf.sharedMesh.bounds = new Bounds(Vector3.zero, Vector3.one * 600f);
                if (mf.name == "Inside_Loose") mf.sharedMesh.bounds = new Bounds(new Vector3(0f, 1.6f, 0f), new Vector3(60f, 60f, 120f));
            }
        }

        void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith(Root)) return;
            var ti = (TextureImporter)assetImporter;
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = false;
            ti.alphaIsTransparency = false;
            ti.mipmapEnabled = true;
            ti.anisoLevel = 4;
            ti.filterMode = FilterMode.Trilinear;
            ti.wrapModeU = TextureWrapMode.Repeat;
            ti.wrapModeV = assetPath.Contains("Fringe") ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            var ps = ti.GetDefaultPlatformTextureSettings();
            ps.format = TextureImporterFormat.BC7;
            ps.maxTextureSize = 2048;
            ti.SetPlatformTextureSettings(ps);
        }
    }
}
#endif
