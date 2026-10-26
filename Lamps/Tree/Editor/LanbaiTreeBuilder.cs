// =====================================================================================================
//  LanbaiTreeBuilder.cs     蓝白 · 样板树（D-44 #6）的预制体搭建 + 导入设置
//
//  !!! NOT COMPILED IN UNITY. Type-checked with Common/Tools~/compile_check/check_cs.sh (Roslyn, editor pass). !!!
//
//  Menu 蓝白/Build/Sample Trees: for every Models/Tree_*.fbx under this kit, make (or refresh)
//      Generated/M_Tree_Bark.mat, Generated/M_Tree_Leaf.mat, Generated/M_Tree_Impostor_<name>.mat
//      Prefabs/<name>.prefab  = the FBX + materials + a LODGroup (LOD0 > 25 %, LOD1 > 8 %, LOD2 > 1.2 % of the screen
//                               height, culled below), Batching Static OFF (the trees ride on the moving R_Road /
//                               R_Stop roots, bible §1.6), shadows on for LOD0/1, off for LOD2.
//  Re-running replaces what it made before (same paths), nothing else is touched.
//  The importer (LanbaiTreeImport) only acts inside .../Lamps/Tree/.
// =====================================================================================================
#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Lamps
{
    public static class LanbaiTreeBuilder
    {
        public static readonly float[] LodHeights = { 0.25f, 0.08f, 0.012f };

        static string KitRoot()
        {
            string[] g = AssetDatabase.FindAssets("LanbaiTreeBuilder t:MonoScript");
            foreach (string id in g)
            {
                string p = AssetDatabase.GUIDToAssetPath(id).Replace('\\', '/');
                if (p.EndsWith("/Tree/Editor/LanbaiTreeBuilder.cs"))
                    return p.Substring(0, p.Length - "/Editor/LanbaiTreeBuilder.cs".Length);
            }
            return "Assets/Lanbai/Lamps/Tree";
        }

        static Material MakeMat(string path, string shaderName)
        {
            Shader sh = Shader.Find(shaderName);
            if (sh == null)
            {
                Debug.LogError("[LanbaiTree] shader not found: " + shaderName);
                return null;
            }
            Material m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(sh);
                AssetDatabase.CreateAsset(m, path);
            }
            else
            {
                m.shader = sh;
            }
            return m;
        }

        static Texture2D Tex(string root, string file)
        {
            return AssetDatabase.LoadAssetAtPath<Texture2D>(root + "/Textures/" + file);
        }

        [MenuItem("蓝白/Build/Sample Trees")]
        public static void BuildMenu()
        {
            Debug.Log(Build());
        }

        /// <summary>Returns a one-line report; "ERROR ..." on failure (test tool convention).</summary>
        public static string Build()
        {
            string root = KitRoot();
            string gen = root + "/Generated";
            string pre = root + "/Prefabs";
            if (!AssetDatabase.IsValidFolder(gen)) AssetDatabase.CreateFolder(root, "Generated");
            if (!AssetDatabase.IsValidFolder(pre)) AssetDatabase.CreateFolder(root, "Prefabs");

            Material bark = MakeMat(gen + "/M_Tree_Bark.mat", "Lanbai/TreeBark");
            Material leaf = MakeMat(gen + "/M_Tree_Leaf.mat", "Lanbai/TreeLeaf");
            if (bark == null || leaf == null) return "ERROR shaders Lanbai/TreeBark or Lanbai/TreeLeaf missing";
            bark.SetTexture("_MainTex", Tex(root, "T_Tree_Bark_Albedo.png"));
            bark.SetTexture("_BumpMap", Tex(root, "T_Tree_Bark_Normal.png"));
            bark.SetTexture("_MaskTex", Tex(root, "T_Tree_Bark_Mask.png"));
            bark.SetFloat("_WindStrength", 0.03f);
            bark.enableInstancing = true;
            leaf.SetTexture("_MainTex", Tex(root, "T_Tree_LeafCluster_Albedo.png"));
            leaf.SetTexture("_BumpMap", Tex(root, "T_Tree_LeafCluster_Normal.png"));
            leaf.SetTexture("_MaskTex", Tex(root, "T_Tree_LeafCluster_Mask.png"));
            leaf.SetFloat("_WindStrength", 0.05f);
            leaf.enableInstancing = true;
            EditorUtility.SetDirty(bark);
            EditorUtility.SetDirty(leaf);

            string[] fbx = Directory.GetFiles(root + "/Models", "Tree_*.fbx");
            int made = 0;
            foreach (string f in fbx)
            {
                string path = f.Replace('\\', '/');
                string name = Path.GetFileNameWithoutExtension(path);
                GameObject src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (src == null) return "ERROR cannot load " + path;
                GameObject go = (GameObject)PrefabUtility.InstantiatePrefab(src);
                go.name = name;
                GameObjectUtility.SetStaticEditorFlags(go, 0);

                Material imp = MakeMat(gen + "/M_Tree_Impostor_" + name + ".mat", "Lanbai/TreeLeaf");
                imp.SetTexture("_MainTex", Tex(root, "T_Tree_Impostor_" + name + ".png"));
                imp.SetTexture("_MaskTex", Texture2D.whiteTexture);
                imp.SetFloat("_Impostor", 1f);
                imp.EnableKeyword("_LANBAI_IMPOSTOR");
                imp.SetFloat("_Flutter", 0f);
                imp.SetFloat("_WindStrength", 0.03f);
                imp.enableInstancing = true;

                LOD[] lods = new LOD[3];
                for (int k = 0; k < 3; k++)
                {
                    Transform t = FindDeep(go.transform, name + "_LOD" + k);
                    if (t == null) { Object.DestroyImmediate(go); return "ERROR " + name + "_LOD" + k + " not found in " + path; }
                    Renderer r = t.GetComponent<Renderer>();
                    if (k < 2)
                    {
                        r.sharedMaterials = new Material[] { bark, leaf };
                        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
                    }
                    else
                    {
                        r.sharedMaterials = new Material[] { imp };
                        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                        MeshFilter mf = t.GetComponent<MeshFilter>();
                        Bounds b = mf != null && mf.sharedMesh != null ? mf.sharedMesh.bounds : new Bounds(new Vector3(0, 6, 0), new Vector3(8, 12, 8));
                        imp.SetVector("_ImpostorCentre", new Vector4(b.center.x, b.center.y + b.extents.y * 0.25f, b.center.z, b.extents.y));
                    }
                    r.receiveShadows = true;
                    r.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off;      // bible §1.6: no light probes
                    r.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
                    lods[k] = new LOD(LodHeights[k], new Renderer[] { r });
                }
                LODGroup lg = go.GetComponent<LODGroup>();
                if (lg == null) lg = go.AddComponent<LODGroup>();
                lg.fadeMode = LODFadeMode.None;
                lg.SetLODs(lods);
                lg.RecalculateBounds();
                EditorUtility.SetDirty(imp);
                AssetDatabase.SaveAssetIfDirty(imp);
                PrefabUtility.SaveAsPrefabAsset(go, pre + "/" + name + ".prefab");
                Object.DestroyImmediate(go);
                made++;
            }
            // save only this kit's materials (a global SaveAssets wrote unrelated dirty assets: local check 10-25)
            AssetDatabase.SaveAssetIfDirty(bark);
            AssetDatabase.SaveAssetIfDirty(leaf);
            return "OK sample trees: " + made + " prefabs in " + pre;
        }

        // FromLocal/trees/README.md: the 7 comparison positions (Unity x, z); B only at the paddy side (director)
        static readonly float[] RowX = { 9f, 12.5f, 8.5f, 15f, -8.5f, -11f, -9f };
        static readonly float[] RowZ = { 16f, 24f, 33f, 40f, 14f, 26f, 38f };
        static readonly string[] RowName = { "Tree_A1", "Tree_A2", "Tree_A3", "Tree_B1", "Tree_A3", "Tree_A1", "Tree_A2" };
        static readonly float[] RowYaw = { 20f, 140f, 260f, 0f, 70f, 200f, 310f };

        /// <summary>Test helper (Engineering/UnityTest): put the 7 sample trees where the local comparison had its
        /// poplars / Linluo trees, under a root "Lanbai_TreeTestRow" (replaced on re-run), and hide the scene's other
        /// trees (renderers whose name starts with Poplar_, Bush_ or Tree-). arg unused.</summary>
        public static string TestRow(string arg)
        {
            string root = KitRoot();
            GameObject old = GameObject.Find("Lanbai_TreeTestRow");
            if (old != null) Object.DestroyImmediate(old);
            GameObject row = new GameObject("Lanbai_TreeTestRow");
            int hidden = 0;
            foreach (Renderer r in Object.FindObjectsOfType<Renderer>())
            {
                string n = r.gameObject.name;
                if (n.StartsWith("Poplar_") || n.StartsWith("Bush_") || n.StartsWith("Tree-")) { r.enabled = false; hidden++; }
            }
            for (int i = 0; i < RowX.Length; i++)
            {
                GameObject pf = AssetDatabase.LoadAssetAtPath<GameObject>(root + "/Prefabs/" + RowName[i] + ".prefab");
                if (pf == null) return "ERROR prefab " + RowName[i] + " missing: run 蓝白/Build/Sample Trees first";
                GameObject go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
                go.transform.SetParent(row.transform, false);
                go.transform.localPosition = new Vector3(RowX[i], 0f, RowZ[i]);
                go.transform.localRotation = Quaternion.Euler(0f, RowYaw[i], 0f);
            }
            return "OK tree test row: 7 trees, hid " + hidden + " old tree renderers";
        }

        static Transform FindDeep(Transform t, string name)
        {
            if (t.name == name) return t;
            for (int i = 0; i < t.childCount; i++)
            {
                Transform r = FindDeep(t.GetChild(i), name);
                if (r != null) return r;
            }
            return null;
        }
    }

    /// <summary>Import settings, only for assets under .../Lamps/Tree/ (CONTROL §2 #3).</summary>
    public class LanbaiTreeImport : AssetPostprocessor
    {
        static bool Mine(string p)
        {
            return p.Replace('\\', '/').Contains("/Lamps/Tree/");
        }

        void OnPreprocessTexture()
        {
            if (!Mine(assetPath)) return;
            TextureImporter ti = (TextureImporter)assetImporter;
            string f = Path.GetFileName(assetPath);
            ti.mipmapEnabled = true;
            ti.alphaIsTransparency = false;
            ti.streamingMipmaps = false;
            ti.wrapMode = f.Contains("Bark") ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
            ti.anisoLevel = 4;
            if (f.Contains("_Normal"))
            {
                ti.textureType = TextureImporterType.NormalMap;
                ti.sRGBTexture = false;
            }
            else if (f.Contains("_Mask"))
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = false;
            }
            else
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = true;
            }
            if (f.Contains("LeafCluster_Albedo") || f.Contains("Impostor"))
            {
                // keep the leaf area at every mip (alpha-to-coverage, director note 2: no thinning, no shimmer)
                ti.mipMapsPreserveCoverage = true;
                ti.alphaTestReferenceValue = 0.5f;
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
            }
            ti.textureCompression = TextureImporterCompression.CompressedHQ;    // BC7 on PC
            ti.crunchedCompression = false;
        }

        void OnPreprocessModel()
        {
            if (!Mine(assetPath)) return;
            ModelImporter mi = (ModelImporter)assetImporter;
            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.CalculateMikk;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.isReadable = false;
            mi.importAnimation = false;
            mi.importCameras = false;
            mi.importLights = false;
            mi.optimizeMeshVertices = true;
            mi.optimizeMeshPolygons = true;
        }
    }
}
#endif
