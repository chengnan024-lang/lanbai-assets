// 蓝白 · 菜单 蓝白/Build/Mirrors：搭十三面白铜镜（可重复运行：先删上一次搭的 R_Mirrors 和 Lanbai_MirrorsDriver，含未激活的）。
// 数据来自 LanbaiMirrorsData.cs（bake_cs.py 从 MirrorSchedule.json 生成）。搭完跑 蓝白/Director/1 Generate Dispatcher 与 2 Wire Scene。
// 第 9 幕的搭建脚本（Act09_StarSea）要把 R_Mirrors 挂进 R_StarSea 时，直接调 LanbaiMirrorsBuild.Build() 即可。
// !!! NOT COMPILED IN UNITY: Roslyn type-check only (Common/Tools~/compile_check/check_cs.sh). !!!
// Needs: 蓝白/Sky/Build Star Mesh (Sky/Generated/StarPoints_BSC5.asset) for the reflected stars, Sky/Textures/StarSky_Glow.
using System;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Mirrors.EditorTools
{
    public static class LanbaiMirrorsBuild
    {
        const string RootName = "R_Mirrors", DriverName = "Lanbai_MirrorsDriver";
        const int Slots = 6;                       // stencil slots for mirrors 1-12 (k-1) % 6; mirror 13 = slot 6
        const int DustPerSlot = 250;

        public static string KitRoot()
        {
            foreach (string id in AssetDatabase.FindAssets("MirrorSchedule"))
            {
                string p = AssetDatabase.GUIDToAssetPath(id);
                if (p.EndsWith("/MirrorSchedule.json")) return p.Substring(0, p.Length - "/MirrorSchedule.json".Length);
            }
            return "Assets/Lanbai/Mirrors";
        }

        static string LanbaiRoot()
        {
            string k = KitRoot();
            return k.Substring(0, k.LastIndexOf('/'));
        }

        [MenuItem("蓝白/Build/Mirrors")]
        public static void Build()
        {
            string kit = KitRoot();
            EnsureProgramAsset("LanbaiMirrorsDriver");
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(kit + "/Models/BronzeMirror.fbx");
            Shader shMirror = Shader.Find("Lanbai/BronzeMirror");
            Shader shStars = Shader.Find("Lanbai/MirrorStars");
            Shader shDust = Shader.Find("Lanbai/MirrorDust");
            if (model == null || shMirror == null || shStars == null || shDust == null)
            {
                Debug.LogError("[Mirrors] missing the model or a shader (BronzeMirror.fbx, Lanbai/BronzeMirror, MirrorStars, MirrorDust)");
                return;
            }
            Mesh starMesh = AssetDatabase.LoadAssetAtPath<Mesh>(LanbaiRoot() + "/Sky/Generated/StarPoints_BSC5.asset");
            if (starMesh == null) Debug.LogWarning("[Mirrors] no Sky/Generated/StarPoints_BSC5.asset (run 蓝白/Sky/Build Star Mesh): the mirrors will show no reflected stars");
            Texture glow = AssetDatabase.LoadAssetAtPath<Texture>(LanbaiRoot() + "/Sky/Textures/StarSky_Glow_8192x4096.png");
            if (glow == null) Debug.LogWarning("[Mirrors] no Sky/Textures/StarSky_Glow_8192x4096.png: the mirrors will reflect only the star floor");

            string gen = kit + "/Generated";
            if (!AssetDatabase.IsValidFolder(gen)) AssetDatabase.CreateFolder(kit, "Generated");

            // earlier builds (active or not)
            foreach (GameObject g in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
                if (g.name == RootName || g.name == DriverName) Undo.DestroyObjectImmediate(g);
            foreach (LanbaiMirrorsDriver od in UnityEngine.Object.FindObjectsOfType<LanbaiMirrorsDriver>(true))
                if (od != null) Undo.DestroyObjectImmediate(od.gameObject);

            GameObject root = new GameObject(RootName);
            Undo.RegisterCreatedObjectUndo(root, "蓝白 Mirrors build");
            int n = LanbaiMirrorsData.TCross.Length;
            Transform[] mirrors = new Transform[n];
            Renderer[] lods = new Renderer[n * 3];
            for (int k = 0; k < n; k++)
            {
                int slot = (k == n - 1) ? Slots : (k % Slots);
                Material mat = MirrorMaterial(gen, kit, shMirror, glow, k, slot);
                GameObject inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
                PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                inst.name = "Mirror_" + (k + 1).ToString("00");
                inst.transform.SetParent(root.transform, false);
                inst.transform.localScale = Vector3.one * LanbaiMirrorsData.Diameter[k];
                // the FBX importer builds no LODGroup per instance (CONTROL §6 pitfall 4): build it here
                LODGroup lg = inst.GetComponent<LODGroup>();
                if (lg == null) lg = inst.AddComponent<LODGroup>();
                Renderer[] rs = new Renderer[3];
                for (int l = 0; l < 3; l++)
                {
                    Transform c = inst.transform.Find("BronzeMirror_LOD" + l);
                    if (c == null) continue;
                    Renderer r = c.GetComponent<Renderer>();
                    r.sharedMaterial = mat;
                    r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                    r.receiveShadows = false;
                    r.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.BlendProbes;
                    r.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
                    r.allowOcclusionWhenDynamic = false;
                    rs[l] = r;
                    lods[3 * k + l] = r;
                }
                // the eye is usually INSIDE the disc's bounds: screen height is huge -> LOD0; LOD1/2 only for the far column
                lg.SetLODs(new LOD[] { new LOD(0.25f, new Renderer[] { rs[0] }), new LOD(0.06f, new Renderer[] { rs[1] }), new LOD(0.0f, new Renderer[] { rs[2] }) });
                lg.RecalculateBounds();
                mirrors[k] = inst.transform;
                inst.SetActive(false);                  // the driver switches each mirror inside its active window
            }

            // reflected-star copies, one per stencil slot
            Renderer[] stars = new Renderer[Slots + 1];
            for (int s = 0; s <= Slots; s++)
            {
                Material m = LoadOrCreate(gen + "/M_09_MirrorStars_Slot" + s + ".mat", shStars);
                m.SetFloat("_StencilRef", 64 + s);
                EditorUtility.SetDirty(m);
                stars[s] = MakeRenderer(root, "MirrorStars_Slot" + s, starMesh, m);
                stars[s].enabled = false;
            }
            // dust: 3 slots x 250 motes, a closed-form shader on a static mesh
            Mesh dust = DustMesh(gen + "/MirrorDust_250.asset");
            Material dm = LoadOrCreate(gen + "/M_09_MirrorDust.mat", shDust);
            Renderer[] dustR = new Renderer[3];
            for (int s = 0; s < 3; s++)
            {
                dustR[s] = MakeRenderer(root, "MirrorDust_Slot" + s, dust, dm);
                dustR[s].enabled = false;
            }

            GameObject drv = new GameObject(DriverName);
            Undo.RegisterCreatedObjectUndo(drv, "蓝白 Mirrors build");
            LanbaiMirrorsDriver c2 = AddUdon(drv);
            c2.root = root; c2.mirrors = mirrors; c2.lodRenderers = lods; c2.starCopies = stars; c2.dustSlots = dustR;
            c2.tCross = LanbaiMirrorsData.TCross; c2.diameter = LanbaiMirrorsData.Diameter;
            c2.centreX = LanbaiMirrorsData.CentreX; c2.centreZ = LanbaiMirrorsData.CentreZ;
            c2.emissionK = LanbaiMirrorsData.EmissionK; c2.pulseEV = LanbaiMirrorsData.PulseEV;
            c2.activeStart = LanbaiMirrorsData.ActiveStart; c2.activeEnd = LanbaiMirrorsData.ActiveEnd;
            c2.dissolveEnd = LanbaiMirrorsData.DissolveEnd; c2.crossSpeed = LanbaiMirrorsData.CrossSpeed;
            c2.knotStart = LanbaiMirrorsData.KnotStart; c2.knotCount = LanbaiMirrorsData.KnotCount;
            c2.knotT = LanbaiMirrorsData.KnotT; c2.knotY = LanbaiMirrorsData.KnotY; c2.knotV = LanbaiMirrorsData.KnotV;
            c2.visStart = LanbaiMirrorsData.VisStart; c2.visCount = LanbaiMirrorsData.VisCount;
            c2.visT = LanbaiMirrorsData.VisT; c2.visV = LanbaiMirrorsData.VisV;
            c2.eye = new Vector3(LanbaiMirrorsData.Eye[0], LanbaiMirrorsData.Eye[1], LanbaiMirrorsData.Eye[2]);
            EditorUtility.SetDirty(c2);
            root.SetActive(false);                      // the dispatcher's LanbaiActivate(true) at the window start (1010, in the black)
            AssetDatabase.SaveAssets();
            Debug.Log("[Mirrors] R_Mirrors (13 mirrors, " + (Slots + 1) + " star copies, 3 dust slots) + " + DriverName + " built. Now run 蓝白/Director/1 Generate Dispatcher and 2 Wire Scene.");
        }

        static Material MirrorMaterial(string gen, string kit, Shader sh, Texture glow, int k, int slot)
        {
            Material m = LoadOrCreate(gen + "/M_09_BronzeMirror_" + (k + 1).ToString("00") + ".mat", sh);
            m.SetFloat("_StencilRef", 64 + slot);
            m.SetFloat("_RadiusM", 0.5f * LanbaiMirrorsData.Diameter[k]);
            m.SetFloat("_MirrorK", k + 1);
            m.SetFloat("_EmissionK", LanbaiMirrorsData.EmissionK[k]);
            m.SetTexture("_FaceTex", AssetDatabase.LoadAssetAtPath<Texture>(kit + "/Textures/T_MirrorFace_2048.png"));
            m.SetTexture("_BackNormal", AssetDatabase.LoadAssetAtPath<Texture>(kit + "/Textures/T_MirrorBack_Normal_2048.png"));
            m.SetTexture("_BackMask", AssetDatabase.LoadAssetAtPath<Texture>(kit + "/Textures/T_MirrorBack_Mask_2048.png"));
            m.SetTexture("_BackCentreNormal", AssetDatabase.LoadAssetAtPath<Texture>(kit + "/Textures/T_MirrorBack_Centre_Normal_2048.png"));
            m.SetTexture("_BackCentreMask", AssetDatabase.LoadAssetAtPath<Texture>(kit + "/Textures/T_MirrorBack_Centre_Mask_2048.png"));
            m.SetTexture("_Glyphs", AssetDatabase.LoadAssetAtPath<Texture>(kit + "/Textures/T_MirrorGlyphs_1024.png"));
            if (glow != null) m.SetTexture("_GlowTex", glow);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Material LoadOrCreate(string path, Shader sh)
        {
            Material m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
            else if (m.shader != sh) m.shader = sh;
            return m;
        }

        static Renderer MakeRenderer(GameObject root, string name, Mesh mesh, Material mat)
        {
            GameObject go = new GameObject(name);
            Undo.RegisterCreatedObjectUndo(go, "蓝白 Mirrors build");
            go.transform.SetParent(root.transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            MeshRenderer r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off;
            r.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
            r.allowOcclusionWhenDynamic = false;
            // the vertices are directions / the origin; the shader places everything: never frustum-cull
            // (Renderer.localBounds exists from 2021.2; set by reflection so the 2021.1 reference check also compiles)
            System.Reflection.PropertyInfo lb = typeof(Renderer).GetProperty("localBounds");
            if (lb != null && lb.CanWrite) lb.SetValue(r, new Bounds(Vector3.zero, Vector3.one * 100000f));
            return r;
        }

        // 250 quads, all vertices at the origin; UV0 = corner, UV1 / UV2 = deterministic uniform seeds
        static Mesh DustMesh(string path)
        {
            Mesh m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            bool isNew = m == null;
            if (isNew) m = new Mesh();
            m.Clear();
            m.name = "MirrorDust_250";
            int nv = DustPerSlot * 4;
            Vector3[] v = new Vector3[nv];
            Vector2[] uv0 = new Vector2[nv], uv1 = new Vector2[nv], uv2 = new Vector2[nv];
            int[] idx = new int[DustPerSlot * 6];
            System.Random rng = new System.Random(20261024);
            Vector2[] corners = { new Vector2(-1, -1), new Vector2(1, -1), new Vector2(1, 1), new Vector2(-1, 1) };
            for (int i = 0; i < DustPerSlot; i++)
            {
                Vector2 s1 = new Vector2((float)rng.NextDouble(), (float)rng.NextDouble());
                Vector2 s2 = new Vector2((float)rng.NextDouble(), (float)rng.NextDouble());
                for (int c = 0; c < 4; c++)
                {
                    v[4 * i + c] = Vector3.zero; uv0[4 * i + c] = corners[c]; uv1[4 * i + c] = s1; uv2[4 * i + c] = s2;
                }
                idx[6 * i] = 4 * i; idx[6 * i + 1] = 4 * i + 2; idx[6 * i + 2] = 4 * i + 1;
                idx[6 * i + 3] = 4 * i; idx[6 * i + 4] = 4 * i + 3; idx[6 * i + 5] = 4 * i + 2;
            }
            m.vertices = v; m.uv = uv0; m.uv2 = uv1; m.uv3 = uv2; m.triangles = idx;
            m.bounds = new Bounds(Vector3.zero, Vector3.one * 100000f);
            if (isNew) AssetDatabase.CreateAsset(m, path); else EditorUtility.SetDirty(m);
            return m;
        }

        static LanbaiMirrorsDriver AddUdon(GameObject go)
        {
            Type addType = Type.GetType("UdonSharpEditor.UdonSharpUndo, UdonSharp.Editor");
            if (addType != null)
                foreach (System.Reflection.MethodInfo mi in addType.GetMethods())
                    if (mi.Name == "AddComponent" && mi.IsGenericMethodDefinition)
                        return (LanbaiMirrorsDriver)mi.MakeGenericMethod(typeof(LanbaiMirrorsDriver)).Invoke(null, new object[] { go });
            return go.AddComponent<LanbaiMirrorsDriver>();
        }

        // U# 1.x only compiles scripts that have a program asset (CONTROL §6 pitfall 11)
        public static void EnsureProgramAsset(string scriptName)
        {
            Type progType = Type.GetType("UdonSharp.UdonSharpProgramAsset, UdonSharp.Editor");
            if (progType == null) { Debug.LogWarning("[Mirrors] UdonSharp not found: create the U# program asset for " + scriptName + " by hand"); return; }
            foreach (string id in AssetDatabase.FindAssets(scriptName + " t:MonoScript"))
            {
                string sp = AssetDatabase.GUIDToAssetPath(id);
                if (!sp.EndsWith("/" + scriptName + ".cs")) continue;
                string ap = sp.Substring(0, sp.Length - 3) + ".asset";
                if (AssetDatabase.LoadAssetAtPath<ScriptableObject>(ap) != null) return;
                ScriptableObject prog = ScriptableObject.CreateInstance(progType);
                System.Reflection.FieldInfo f = progType.GetField("sourceCsScript");
                if (f != null) f.SetValue(prog, AssetDatabase.LoadAssetAtPath<MonoScript>(sp));
                AssetDatabase.CreateAsset(prog, ap);
                AssetDatabase.SaveAssets();
                return;
            }
        }
    }

    // import settings for this kit only (CONTROL §2.3): data textures linear, normals as normal maps, the FBX with
    // vertex colours and full-precision UVs, no generated LODGroup surprises
    public class LanbaiMirrorsImport : AssetPostprocessor
    {
        static bool Mine(string p) { return p.Contains("/Mirrors/") && !p.Contains("~"); }

        void OnPreprocessTexture()
        {
            if (!Mine(assetPath)) return;
            TextureImporter ti = (TextureImporter)assetImporter;
            string f = System.IO.Path.GetFileName(assetPath);
            ti.mipmapEnabled = true;
            ti.anisoLevel = 4;
            ti.wrapMode = f.StartsWith("T_MirrorBack") ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
            if (f.Contains("_Normal_"))
            {
                ti.textureType = TextureImporterType.NormalMap;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
            }
            else
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = false;                 // masks, face data and glyph coverage are data, not colour
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
            }
        }

        void OnPreprocessModel()
        {
            if (!Mine(assetPath)) return;
            ModelImporter mi = (ModelImporter)assetImporter;
            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.bakeAxisConversion = false;
            mi.importBlendShapes = false;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importAnimation = false;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.importNormals = ModelImporterNormals.Import;
            mi.weldVertices = false;
            mi.isReadable = false;
        }
    }
}
