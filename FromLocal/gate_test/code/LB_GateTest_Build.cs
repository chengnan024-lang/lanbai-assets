// 蓝白 · 触手之门 · 导入测试：建场景、建材质、按 JSON 搭（见 LB_GateTest.cs 的头注释）
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.PostProcessing;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace Lanbai.Tests
{
    public static partial class LB_GateTest
    {
        // 名字（场景里的根物体）
        const string R_GATE = "GateRoot", R_NEAR = "NearRoot_bus", R_LIGHTS = "Gate_Lights", R_CAM = "ReferenceCamera";
        // 每实例的 instanced 属性：写进每个 LOD renderer 自己的 MaterialPropertyBlock（README_GateLayout §2.1）
        static readonly string[] INSTANCED = { "_Phase", "_Reveal", "_FogCapI", "_RevealGroup" };

        // ─────────────────────────────────────────────────────────────
        //  1. 测试场景
        // ─────────────────────────────────────────────────────────────
        public static string NewScene(string arg)
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) return "ERROR：先退出 Play";
            var cur = SceneManager.GetActiveScene();
            bool force = arg != null && arg.Contains("force");
            if (File.Exists(SCENE) && !force)
            {
                if (cur.path != SCENE)
                {
                    if (cur.isDirty && !string.IsNullOrEmpty(cur.path)) return "ERROR：当前场景 " + cur.path + " 有没保存的改动，不动它";
                    EditorSceneManager.OpenScene(SCENE, OpenSceneMode.Single);
                }
                SelectCamera();
                return "测试场景已经有了，已打开：" + SCENE;
            }
            if (cur.isDirty && !string.IsNullOrEmpty(cur.path)) return "ERROR：当前场景 " + cur.path + " 有没保存的改动，不动它";
            EnsureFolder("Assets/Lanbai/Tests");
            var sc = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var go = new GameObject(R_CAM);
            go.tag = "MainCamera";
            var cam = go.AddComponent<Camera>();
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 45000f;
            cam.allowHDR = true;
            cam.allowMSAA = true;
            cam.clearFlags = CameraClearFlags.Skybox;
            go.transform.position = new Vector3(0.55f, 1.70f, 2.05f);
            go.transform.rotation = Quaternion.identity;
            cam.fieldOfView = VFov(90f, 16f / 9f);
            var note = new GameObject("_说明");
            note.tag = "EditorOnly";
            EditorSceneManager.SaveScene(sc, SCENE);
            SelectCamera();
            return "新建了测试场景 " + SCENE + "（只有 ReferenceCamera；没有 VRC 场景描述符，不进 Build Settings）";
        }

        static void SelectCamera()
        {
            var c = Root(R_CAM);
            if (c != null) Selection.activeGameObject = c;
        }

        // ─────────────────────────────────────────────────────────────
        //  2. 贴图、shader
        // ─────────────────────────────────────────────────────────────
        static T LoadA<T>(string path, List<string> missing) where T : Object
        {
            var a = AssetDatabase.LoadAssetAtPath<T>(path);
            if (a == null && missing != null) missing.Add(path);
            return a;
        }
        static Shader Sh(string name, List<string> missing)
        {
            var s = Shader.Find(name);
            if (s == null) missing.Add("shader " + name);
            return s;
        }
        static Material MatAsset(string name, Shader sh)
        {
            EnsureFolder(MATS);
            string p = MATS + "/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (m == null)
            {
                m = new Material(sh != null ? sh : Shader.Find("Standard")) { name = name };
                AssetDatabase.CreateAsset(m, p);
            }
            else if (sh != null && m.shader != sh) m.shader = sh;
            return m;
        }

        /// <summary>把 JSON 的一个材质块照抄进材质：按 shader 里声明的属性类型写（Float / Range / Vector / Color）。返回 shader 里没有的键。</summary>
        static List<string> ApplyJsonMat(Material m, object jm, bool skipInstanced)
        {
            var missing = new List<string>();
            var d = M(jm);
            if (d == null) return missing;
            var sh = m.shader;
            foreach (var kv in d)
            {
                string k = kv.Key;
                if (k == "material_name") continue;
                if (skipInstanced && INSTANCED.Contains(k)) continue;
                int idx = sh.FindPropertyIndex(k);
                if (idx < 0) { missing.Add(k); continue; }
                var ty = sh.GetPropertyType(idx);
                var v = kv.Value;
                if (v is double)
                {
                    float f = F(v);
                    if (ty == ShaderPropertyType.Color) m.SetColor(k, new Color(f, f, f, 1f));    // 例：后窗 _Color 0.735（sRGB 填值）
                    else if (ty == ShaderPropertyType.Vector) m.SetVector(k, new Vector4(f, f, f, f));
                    else m.SetFloat(k, f);
                }
                else if (v is bool) m.SetFloat(k, (bool)v ? 1f : 0f);
                else if (v is List<object>)
                {
                    var a = V4(v);
                    if (L(v).Count < 4 && ty == ShaderPropertyType.Color) a.w = 1f;
                    if (ty == ShaderPropertyType.Color) m.SetColor(k, new Color(a.x, a.y, a.z, a.w));
                    else m.SetVector(k, a);
                }
            }
            return missing;
        }

        static void SetPart(Material m, string part, int idx)
        {
            foreach (var p in new[] { "LENS", "RIP", "FLAP", "FIBRE", "HALO", "SHAFT", "FOLDS", "CLOUDGLOW", "FOOTCLOUD", "SKYLINE", "LANE" })
                m.DisableKeyword("_PART_" + p);
            m.SetFloat("_Part", idx);
            m.EnableKeyword("_PART_" + part);
        }
        static void SetBlend(Material m, UnityEngine.Rendering.BlendMode src, UnityEngine.Rendering.BlendMode dst, bool zwrite, CullMode cull, bool a2m, int queue)
        {
            m.SetFloat("_SrcBlend", (float)src);
            m.SetFloat("_DstBlend", (float)dst);
            m.SetFloat("_ZWrite", zwrite ? 1f : 0f);
            m.SetFloat("_Cull", (float)cull);
            m.SetFloat("_AlphaToMask", a2m ? 1f : 0f);
            m.renderQueue = queue;
        }

        // ─────────────────────────────────────────────────────────────
        //  3. 网格量出来的数（README §4.2 的贴图平铺规则、_VariantDims）
        // ─────────────────────────────────────────────────────────────
        /// <summary>根半径（物体空间）：UV1.x（t）最小的那一圈顶点，到它们中心的距离 ÷ UV2.x（= 半径 / 根半径）。</summary>
        static float RootRadius(Mesh mesh, out string how)
        {
            how = "";
            try
            {
                var vs = mesh.vertices;
                var u1 = new List<Vector2>(); mesh.GetUVs(1, u1);
                var u2 = new List<Vector2>(); mesh.GetUVs(2, u2);
                if (vs.Length == 0 || u1.Count != vs.Length || u2.Count != vs.Length) { how = "网格没有 UV1 / UV2（" + u1.Count + " / " + u2.Count + " / " + vs.Length + "）"; return -1f; }
                float tmin = u1.Min(u => u.x);
                var ring = Enumerable.Range(0, vs.Length).Where(k => u1[k].x <= tmin + 0.002f && u2[k].x > 0.05f).ToList();
                if (ring.Count < 6) { how = "根部那一圈只有 " + ring.Count + " 个顶点"; return -1f; }
                Vector3 c = Vector3.zero;
                foreach (int k in ring) c += vs[k];
                c /= ring.Count;
                // 去掉封口中心那种离轴很近的点（它们会把平均拉低），取中位数
                float rmax = ring.Max(k => (vs[k] - c).magnitude);
                var est = ring.Where(k => (vs[k] - c).magnitude > 0.5f * rmax).Select(k => (vs[k] - c).magnitude / u2[k].x).OrderBy(x => x).ToList();
                if (est.Count < 4) { how = "根部可用的点太少"; return -1f; }
                how = "根部 " + est.Count + " / " + ring.Count + " 个顶点";
                return est[est.Count / 2];
            }
            catch (Exception e) { how = "读不到网格（" + e.GetType().Name + "：" + e.Message + "）"; return -1f; }
        }
        static Mesh Lod0Mesh(Transform inst)
        {
            foreach (var mf in inst.GetComponentsInChildren<MeshFilter>(true))
                if (mf.name.EndsWith("_LOD0") && mf.sharedMesh != null) return mf.sharedMesh;
            var any = inst.GetComponentInChildren<MeshFilter>(true);
            return any != null ? any.sharedMesh : null;
        }

        // 自定义中心线的巨物（arms4.COLOSSUS_KEYS + BG*）：宏观起伏、主贴图按根半径平铺
        static bool IsColossusKey(string key) { return key == "PR" || key == "PL" || key == "ENG" || key == "C2" || key == "C1" || key.StartsWith("BG"); }
        static readonly Dictionary<string, Vector2> LIB_DIMS = new Dictionary<string, Vector2>
        {
            { "A", new Vector2(0.70f, 25f) }, { "B", new Vector2(0.95f, 32f) }, { "C", new Vector2(1.35f, 61.8f) }, { "D", new Vector2(2.00f, 72f) },
            { "E", new Vector2(2.75f, 100f) }, { "F", new Vector2(3.90f, 140f) }, { "G", new Vector2(10.0f, 300f) }, { "H", new Vector2(12.5f, 447f) },
        };

        // ─────────────────────────────────────────────────────────────
        //  4. 搭
        // ─────────────────────────────────────────────────────────────
        public static string Build(string arg)
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) return "ERROR：先退出 Play";
            _json = null;
            RequireTestScene();
            float t = ParseT(arg, 155.10f);
            var log = new StringBuilder();
            var missing = new List<string>();
            var J = Json();

            // ---- 清掉上一次搭的（ReferenceCamera、Lanbai_Grades 留着）
            foreach (var n in new[] { R_GATE, R_NEAR, R_LIGHTS })
            {
                var old = Root(n);
                if (old != null) Object.DestroyImmediate(old);
            }

            // ---- shader 与贴图
            var shArm = Sh("Lanbai/TentacleSway", missing);
            var shTide = Sh("Lanbai/TentacleTide", missing);
            var shSky = Sh("Lanbai/GateAirSky", missing);
            var shTear = Sh("Lanbai/Tear", missing);
            var texAlb = LoadA<Texture2D>(TENT + "/Textures/T_Tentacle_Albedo.png", missing);
            var texNrm = LoadA<Texture2D>(TENT + "/Textures/T_Tentacle_Normal.png", missing);
            var texMS = LoadA<Texture2D>(TENT + "/Textures/T_Tentacle_MetallicSmoothness.png", missing);
            var texDet = LoadA<Texture2D>(TENT + "/Textures/T_Tentacle_DetailNormal.png", missing);
            var armsFbx = LoadA<GameObject>(GATE + "/GateArms_v4.fbx", missing);
            var multFbx = LoadA<GameObject>(GATE + "/GateMultitude_v2.fbx", missing);
            var tideFbx = LoadA<GameObject>(GATE + "/TentacleTide_v2.fbx", missing);
            var tearFbx = LoadA<GameObject>(TEAR + "/FBX/Tear_Kit.fbx", missing);
            var shaftFbx = LoadA<GameObject>(TEAR + "/FBX/Tear_ShaftCard.fbx", missing);
            if (shArm == null || armsFbx == null) return "ERROR：缺 " + string.Join("，", missing);

            var gateRoot = new GameObject(R_GATE);
            var nearRoot = new GameObject(R_NEAR);
            int nSingle = 0, nMult = 0, nLodBuilt = 0;
            var notes = new List<string>();

            // ---- 单独的臂（28 条，GateArms_v4.fbx）+ 群臂（36 条，GateMultitude_v2.fbx）
            var tierMats = new Dictionary<string, Material>();
            var rootR = new Dictionary<string, float>();
            foreach (var it in Instances())
            {
                string id = S(G(it, "id"));
                bool surge = S(G(it, "layer")) == "surge";
                bool bus = S(G(it, "frame")) == "bus";
                string variant = S(G(it, "variant"));
                string texKey = S(G(it, "texture_variant")) ?? variant;
                var src = surge ? (multFbx != null ? FindDeep(multFbx.transform, variant) : null) : FindDeep(armsFbx.transform, id);
                if (src == null) { missing.Add((surge ? "GateMultitude_v2.fbx: " + variant : "GateArms_v4.fbx: " + id)); continue; }
                var go = (GameObject)Object.Instantiate(src.gameObject);
                go.name = id;
                go.transform.SetParent(bus ? nearRoot.transform : gateRoot.transform, false);
                go.transform.localPosition = Vector3.zero;
                go.transform.localRotation = Quaternion.identity;
                float sc = F(G(it, "scale"), 1f);
                go.transform.localScale = Vector3.one * sc;

                // LODGroup：LOD0 > 25 %、LOD1 > 6 %、LOD2 > 0.5 %（README §9）。
                // Unity 的导入器只在 FBX 的根上建了一个 LODGroup（GateArms_v4 / GateMultitude_v2 各一个，管全部 84 / 36 个网格），
                // 每个实例自己的 <id>_LOD0/1/2 没有分组——所以这里按名字给每个实例建一个
                float[] hts = { 0.25f, 0.06f, 0.005f };
                var lg = go.GetComponent<LODGroup>();
                if (lg == null)
                {
                    var byLod = new List<Renderer>[3] { new List<Renderer>(), new List<Renderer>(), new List<Renderer>() };
                    foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                        for (int k = 0; k < 3; k++) if (r.name.EndsWith("_LOD" + k)) byLod[k].Add(r);
                    int nl = byLod.Count(x => x.Count > 0);
                    if (nl > 0)
                    {
                        lg = go.AddComponent<LODGroup>();
                        var lods = new List<LOD>();
                        for (int k = 0; k < 3; k++) if (byLod[k].Count > 0) lods.Add(new LOD(hts[k], byLod[k].ToArray()));
                        lg.SetLODs(lods.ToArray());
                        lg.RecalculateBounds();
                        nLodBuilt++;
                    }
                    else notes.Add(id + "：子物体里没有 _LOD0/1/2");
                }
                else
                {
                    var lods = lg.GetLODs();
                    for (int k = 0; k < lods.Length && k < 3; k++) lods[k].screenRelativeTransitionHeight = hts[k];
                    lg.SetLODs(lods);
                    lg.RecalculateBounds();
                }

                // 根半径（网格量的）→ 贴图平铺、_VariantDims
                var mesh = Lod0Mesh(go.transform);
                string how;
                float R;
                string rkey = surge ? variant : id;
                if (!rootR.TryGetValue(rkey, out R)) { R = mesh != null ? RootRadius(mesh, out how) : -1f; rootR[rkey] = R; if (R <= 0f) notes.Add(rkey + " 根半径：" + (mesh == null ? "没有网格" : "量不出")); }
                float Lobj = F(G(it, "length_m"), 300f) / Mathf.Max(1e-3f, sc);
                bool custom = !LIB_DIMS.ContainsKey(texKey);
                Vector2 dims;
                if (!custom) dims = LIB_DIMS[texKey];                                      // 库里的变体：README_Tentacles 的表（量出来的写进报告）
                else dims = new Vector2(R > 0f ? R : 10f, Lobj);
                float Rm = dims.x * sc;
                float til = 1f, dtil = 1f;
                if (surge) { til = 1f; dtil = 4f; }                                         // 群臂固定 (1, 4)
                else if (custom) { til = Mathf.Clamp(Rm / 25f, 1f, 3f); dtil = Mathf.Clamp(Rm / 4f, 1f, 16f); }   // arms4.skin_tiling
                bool colossus = custom && IsColossusKey(texKey);
                string occl = custom ? GATE + "/Textures/Occlusion/T_Gate_" + texKey + "_Occlusion.png" : TENT + "/Textures/T_Tentacle_" + texKey + "_Occlusion.png";
                var texOcc = LoadA<Texture2D>(occl, missing);

                Material mat;
                if (surge)
                {
                    string mn = S(G(G(it, "material"), "material_name")) ?? "M_Multitude";
                    if (!tierMats.TryGetValue(mn, out mat))
                    {
                        mat = MatAsset(mn, shArm);
                        ArmTextures(mat, texAlb, texNrm, texMS, texDet, null, til, dtil);
                        mat.SetFloat("_Colossus", 0f);
                        mat.SetVector("_VariantDims", new Vector4(dims.x, dims.y, 0f, 0f));
                        var miss = ApplyJsonMat(mat, G(it, "material"), true);
                        if (miss.Count > 0) notes.Add(mn + "：shader 里没有 " + string.Join(" ", miss));
                        mat.enableInstancing = true;
                        EditorUtility.SetDirty(mat);
                        tierMats[mn] = mat;
                    }
                    nMult++;
                }
                else
                {
                    mat = MatAsset("M_Gate_" + id, shArm);
                    ArmTextures(mat, texAlb, texNrm, texMS, texDet, texOcc, til, dtil);
                    mat.SetFloat("_Colossus", colossus ? 1f : 0f);
                    mat.SetVector("_VariantDims", new Vector4(dims.x, dims.y, 0f, 0f));
                    var miss = ApplyJsonMat(mat, G(it, "material"), false);
                    if (miss.Count > 0) notes.Add("M_Gate_" + id + "：shader 里没有 " + string.Join(" ", miss));
                    mat.enableInstancing = true;
                    EditorUtility.SetDirty(mat);
                    nSingle++;
                }
                foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                {
                    var arr = r.sharedMaterials;
                    for (int k = 0; k < arr.Length; k++) arr[k] = mat;
                    r.sharedMaterials = arr;
                    r.shadowCastingMode = bus ? ShadowCastingMode.On : ShadowCastingMode.Off;   // 只有近处 3 条投影
                }
                log.AppendLine(id + "  " + (surge ? "pose " + variant + "  " + S(G(G(it, "material"), "material_name")) : "M_Gate_" + id) +
                               "  R_root " + Fs(dims.x, "0.###") + (custom ? "" : "（库表；网格量得 " + Fs(R, "0.###") + "）") + " m（物体空间）× 缩放 " + Fs(sc, "0.###") + "  L " + Fs(dims.y, "0.#") +
                               "  平铺 主 " + Fs(til, "0.###") + " / 细节 " + Fs(4f * dtil, "0.##") + "×" + Fs(4.6f * dtil, "0.##") +
                               (colossus ? "  _Colossus 1" : "") + (texOcc != null ? "  遮罩 " + Path.GetFileName(occl) : "  遮罩缺"));
            }

            // ---- 远潮（TentacleTide_v2.fbx，挂 GateRoot、本地单位变换）
            if (tideFbx != null && shTide != null)
            {
                var tide = (GameObject)Object.Instantiate(tideFbx);
                tide.name = "TideRoot";
                tide.transform.SetParent(gateRoot.transform, false);
                tide.transform.localPosition = Vector3.zero; tide.transform.localRotation = Quaternion.identity; tide.transform.localScale = Vector3.one;
                var mA = MatAsset("M_TentacleTide_v3_A", shTide);
                var mB = MatAsset("M_TentacleTide_v3_B", shTide);
                mA.SetTexture("_MainTex", LoadA<Texture2D>(GATE + "/Textures/TentacleTide_v3_Atlas_A.png", missing));
                mB.SetTexture("_MainTex", LoadA<Texture2D>(GATE + "/Textures/TentacleTide_v3_Atlas_B.png", missing));
                EditorUtility.SetDirty(mA); EditorUtility.SetDirty(mB);
                foreach (var r in tide.GetComponentsInChildren<Renderer>(true))
                {
                    var arr = r.sharedMaterials;
                    var names = new List<string>();
                    for (int k = 0; k < arr.Length; k++)
                    {
                        string nm = arr[k] != null ? arr[k].name : "(空)";
                        names.Add(nm);
                        bool isB = nm.EndsWith("B") || nm.Contains("_B") || nm.Contains("Atlas_B");
                        arr[k] = isB ? mB : mA;
                    }
                    r.sharedMaterials = arr;
                    r.shadowCastingMode = ShadowCastingMode.Off;
                    r.receiveShadows = false;
                    r.lightProbeUsage = LightProbeUsage.Off;
                    log.AppendLine("远潮 " + r.name + "：子网格的 FBX 材质名 [" + string.Join(", ", names) + "] → [" + string.Join(", ", arr.Select(x => x.name)) + "]");
                }
            }

            // ---- 裂口（Tear_Kit.fbx v6.1：Tear_Root 挂 GateRoot，(0, −150, 0)、(0, 180, 0)、缩放 H/1000）
            if (tearFbx != null && shTear != null) BuildTear(gateRoot.transform, tearFbx, shaftFbx, shTear, missing, log, notes);

            // ---- 光（JSON lights；强度 = JSON 的 "inspector" 栏，原样）
            var lights = new GameObject(R_LIGHTS);
            var LJ = G(J, "lights");
            {
                var mo = G(LJ, "moon");
                var l = NewLight(lights.transform, "Moon", Hex(S(G(mo, "color"))), F(G(mo, "inspector"), 1f), LightShadows.Soft);
                l.transform.rotation = Quaternion.LookRotation(-V3(G(mo, "direction_to_light_unity")).normalized, Vector3.up);
                var fi = G(LJ, "fill");
                var lf = NewLight(lights.transform, "Fill_from_below", Hex(S(G(fi, "color"))), F(G(fi, "inspector"), 0.52f), LightShadows.None);
                lf.transform.rotation = Quaternion.LookRotation(Vector3.up, Vector3.forward);          // JSON：from_below（没给方位，取正下方往上）
                var te = G(LJ, "tear");
                var lt = NewLight(lights.transform, "Tear_CabinOnly", Hex(S(G(te, "color"))), F(G(te, "inspector"), 0.9f), LightShadows.None);
                lt.cullingMask = 0;                                                                         // 只照车厢；测试场景里没有车厢
                notes.Add("裂口平行光只照车厢层（JSON lights.tear）：测试场景没有车，Culling Mask 设成 Nothing");
            }

            // ---- 天空、雾
            var sky = MatAsset("M_GateAirSky", shSky);
            RenderSettings.skybox = sky;
            var FJ = G(J, "fog");
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;
            RenderSettings.fogDensity = F(G(FJ, "density"), 0.0006f);
            RenderSettings.fogColor = Hex(S(G(FJ, "global_color")) ?? "#505466");
            RenderSettings.sun = lights.transform.Find("Moon").GetComponent<Light>();
            DynamicGI.UpdateEnvironment();

            // ---- 相机
            var camGo = Root(R_CAM);
            if (camGo == null) notes.Add("没有 ReferenceCamera（先 NewScene）");

            AssetDatabase.SaveAssets();
            string ap = Apply(Fs(t, "0.###"));
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene());

            var sb = new StringBuilder();
            sb.AppendLine("搭好了：单独的臂 " + nSingle + " 条、群臂 " + nMult + " 条（" + tierMats.Count + " 个档材质），给 " + nLodBuilt + " 个实例建了 LODGroup。" + ap);
            if (missing.Count > 0) sb.AppendLine("缺：" + string.Join("；", missing.Distinct()));
            if (notes.Count > 0) { sb.AppendLine("备注："); foreach (var n in notes) sb.AppendLine("  · " + n); }
            sb.AppendLine("—— 逐条 ——");
            sb.Append(log);
            WriteReport("GateTest_Build.txt", sb.ToString());
            return sb.ToString();
        }

        static void ArmTextures(Material m, Texture2D alb, Texture2D nrm, Texture2D ms, Texture2D det, Texture2D occ, float til, float dtil)
        {
            m.SetTexture("_MainTex", alb);
            m.SetTextureScale("_MainTex", new Vector2(til, til));
            m.SetTexture("_MetallicGlossMap", ms);
            m.SetTexture("_BumpMap", nrm);
            m.SetTexture("_DetailNormalMap", det);
            m.SetTextureScale("_DetailNormalMap", new Vector2(4f * dtil, 4.6f * dtil));
            if (occ != null) m.SetTexture("_OcclusionMap", occ);
            m.SetFloat("_Glossiness", 1f);
        }

        static Light NewLight(Transform parent, string name, Color c, float intensity, LightShadows sh)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var l = go.AddComponent<Light>();
            l.type = LightType.Directional;
            l.color = c;
            l.intensity = intensity;
            l.shadows = sh;
            l.lightmapBakeType = LightmapBakeType.Realtime;
            return l;
        }

        // ─────────────────────────────────────────────────────────────
        //  裂口（Tear/README_Tear.md §4 的材质表照抄；门里的覆盖值来自 JSON tear.*）
        // ─────────────────────────────────────────────────────────────
        static readonly Vector4 HAZE = new Vector4(0.1085f, 0.1130f, 0.1641f, 1f);
        static readonly Vector4 FOOTMIST = new Vector4(1.64f, 1.56f, 1.96f, 1f);

        static Material TearMat(string name, Shader sh, string part, int partIdx, Texture tex)
        {
            var m = MatAsset("M_" + name, sh);
            SetPart(m, part, partIdx);
            if (tex != null) m.SetTexture("_MainTex", tex);
            m.SetVector("_HazeColor", HAZE);
            return m;
        }

        static void BuildTear(Transform gateRoot, GameObject tearFbx, GameObject shaftFbx, Shader sh, List<string> missing, StringBuilder log, List<string> notes)
        {
            var J = Json();
            var TJ = G(J, "tear");
            Func<string, Texture2D> T = n => LoadA<Texture2D>(TEAR + "/Textures/" + n, missing);
            // Part 序号 = KeywordEnum 的顺序
            const int LENS = 0, RIP = 1, FLAP = 2, HALO = 4, SHAFT = 5, FOLDS = 6, CLOUDGLOW = 7, SKYLINE = 9, LANE = 10;

            var mGlowAdd = TearMat("Tear_CloudGlow", sh, "CLOUDGLOW", CLOUDGLOW, T("Halo_512.png"));
            SetBlend(mGlowAdd, UnityEngine.Rendering.BlendMode.One, UnityEngine.Rendering.BlendMode.One, false, CullMode.Off, false, 2988);
            mGlowAdd.SetVector("_Tint", new Vector4(0.1413f, 0.1590f, 0.2664f, 1f));
            mGlowAdd.SetFloat("_Intensity", 0.25f);
            mGlowAdd.SetFloat("_NearFootCut", 1f);
            mGlowAdd.SetFloat("_FootAddK", 0.25f);
            mGlowAdd.SetFloat("_FootGlow", 2.2f);
            mGlowAdd.SetVector("_FootLobe", new Vector4(-0.5f, 159f, -60f, 220f));
            var lanes = LoadA<Texture2D>(GATE + "/Textures/Tear_CloudLanes_1024.png", missing);
            mGlowAdd.SetTexture("_LanesTex", lanes);

            var mGlowLit = TearMat("Tear_CloudGlow_Lit", sh, "CLOUDGLOW", CLOUDGLOW, T("Halo_512.png"));
            SetBlend(mGlowLit, UnityEngine.Rendering.BlendMode.DstColor, UnityEngine.Rendering.BlendMode.One, false, CullMode.Off, false, 2989);
            mGlowLit.SetVector("_Tint", new Vector4(0.607f, 0.683f, 1.144f, 1f));
            mGlowLit.SetFloat("_FootGlow", 0.98f);
            mGlowLit.SetFloat("_Intensity", 1f);
            mGlowLit.SetTexture("_LanesTex", lanes);      // JSON clouds.pool：光池的权重 × Tear_CloudLanes（两层都乘）

            var mSky = TearMat("Tear_FootSkyline", sh, "SKYLINE", SKYLINE, T("Tear_FootSkyline_1024x160.png"));
            var mSkyIn = TearMat("Tear_FootSkylineIn", sh, "SKYLINE", SKYLINE, T("Tear_FootSkylineIn_512x160.png"));
            foreach (var m in new[] { mSky, mSkyIn })
            {
                SetBlend(m, UnityEngine.Rendering.BlendMode.One, UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha, false, CullMode.Off, false, 2989);
                m.SetVector("_SkyCloud", new Vector4(0.060f, 0.066f, 0.082f, 1f));    // README：渲染里 U7 的云海月光色（Unity 里没有 CloudSea 卡可抄）
                m.SetFloat("_SkyRim", F(G(G(TJ, "foot_skyline"), "_SkyRim"), 1.2f));
                m.SetFloat("_SkyNear", F(G(G(TJ, "foot_skyline"), "_SkyNear"), 0.27f));
                m.SetVector("_FootMist", FOOTMIST);
            }

            var mLane = TearMat("Tear_LightLane", sh, "LANE", LANE, null);           // Lane 不采样贴图（shader 里是逐像素算的）
            SetBlend(mLane, UnityEngine.Rendering.BlendMode.DstColor, UnityEngine.Rendering.BlendMode.One, false, CullMode.Off, false, 2989);
            var LJ = G(TJ, "light_lane");
            mLane.SetVector("_LaneW", V4(G(LJ, "_LaneW")));
            mLane.SetVector("_LaneFoot", V4(G(LJ, "_LaneFoot")));
            mLane.SetVector("_LaneNear", V4(G(LJ, "_LaneNear")));
            mLane.SetFloat("_Intensity", 1f);

            var mFolds = TearMat("Tear_SkyFolds", sh, "FOLDS", FOLDS, T("Tear_SkyFolds_1024.png"));
            SetBlend(mFolds, UnityEngine.Rendering.BlendMode.One, UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha, false, CullMode.Off, false, 2990);
            mFolds.SetVector("_Tint", Vector4.one);

            var mHalo = TearMat("Tear_Halo", sh, "HALO", HALO, T("Halo_512.png"));
            SetBlend(mHalo, UnityEngine.Rendering.BlendMode.One, UnityEngine.Rendering.BlendMode.One, false, CullMode.Off, false, 2992);
            mHalo.SetVector("_Tint", Vector4.one);

            var mLens = TearMat("Tear_Lens", sh, "LENS", LENS, T("Tear_Emission_2048x512.png"));
            SetBlend(mLens, UnityEngine.Rendering.BlendMode.One, UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha, false, CullMode.Off, false, 2994);
            mLens.SetFloat("_EmissionScale", 4f);
            mLens.SetFloat("_DepthPrepass", 1f);
            mLens.SetVector("_FootMist", FOOTMIST);
            mLens.SetFloat("_FootMistM", 50f);
            mLens.SetVector("_FootCut", new Vector4(-30f, 18f, 35f, 80f));

            var mRip = TearMat("Tear_Rip", sh, "RIP", RIP, T("Tear_Rip_1024x128.png"));
            SetBlend(mRip, UnityEngine.Rendering.BlendMode.One, UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha, false, CullMode.Off, false, 2995);
            mRip.SetFloat("_EmissionScale", 4f);
            mRip.SetFloat("_Intensity", 0.55f);
            mRip.SetFloat("_RipFront", 0.1f);

            var mShaft = TearMat("Tear_Shaft", sh, "SHAFT", SHAFT, T("Shaft_Gradient_256x1024.png"));
            SetBlend(mShaft, UnityEngine.Rendering.BlendMode.One, UnityEngine.Rendering.BlendMode.One, false, CullMode.Off, false, 2998);
            mShaft.SetVector("_Tint", new Vector4(0.0362f, 0.0343f, 0.0873f, 1f));
            mShaft.SetFloat("_Intensity", F(G(G(TJ, "gate_overrides"), "shaft"), 0.35f));

            var mFlap = TearMat("Tear_Flap", sh, "FLAP", FLAP, T("Tear_Flaps_1024.png"));
            SetBlend(mFlap, UnityEngine.Rendering.BlendMode.One, UnityEngine.Rendering.BlendMode.Zero, true, CullMode.Off, true, 2450);
            mFlap.SetVector("_FlapOuterNear", new Vector4(0.0181f, 0.0198f, 0.0342f, 1f));
            mFlap.SetVector("_FlapOuterFar", new Vector4(0.0090f, 0.0098f, 0.0135f, 1f));
            mFlap.SetVector("_FlapInner", new Vector4(0.0592f, 0.0499f, 0.1231f, 1f));
            mFlap.SetVector("_FlapEdge", new Vector4(0.5495f, 0.4188f, 1.3912f, 1f));
            mFlap.SetFloat("_FlapTrans", 0.6f);
            mFlap.SetFloat("_SheenMul", 0.35f);
            mFlap.SetFloat("_OuterSky", 0f);
            mFlap.SetFloat("_FoldBleed", 0f);
            mFlap.SetFloat("_Cutoff", 0.5f);

            foreach (var m in new[] { mGlowAdd, mGlowLit, mSky, mSkyIn, mLane, mFolds, mHalo, mLens, mRip, mShaft, mFlap }) EditorUtility.SetDirty(m);

            // FBX 里只有一个根空物体 Tear_Root 时，Unity 把它并进模型根（叫 Tear_Kit），12 个网格直接挂在下面
            var src = FindDeep(tearFbx.transform, "Tear_Root") ?? tearFbx.transform;
            if (src != tearFbx.transform) log.AppendLine("Tear_Root 在 FBX 里是单独的物体");
            else log.AppendLine("Tear_Kit.fbx 的根（" + tearFbx.name + "）就是 Tear_Root（Unity 导入时把唯一的根空物体并进了模型根），按它来挂");
            var root = (GameObject)Object.Instantiate(src.gameObject);
            root.name = "Tear_Root";
            root.transform.SetParent(gateRoot, false);
            var RJ = G(TJ, "Tear_Root");
            root.transform.localPosition = V3(G(RJ, "localPosition"));
            root.transform.localEulerAngles = V3(G(RJ, "localEulerAngles"));
            root.transform.localScale = Vector3.one * 0.64f;

            var map = new Dictionary<string, Material[]>
            {
                { "Tear_Lens", new[] { mLens } }, { "Tear_Flap_L", new[] { mFlap } }, { "Tear_Flap_R", new[] { mFlap } },
                { "Tear_Rip_Branch_A", new[] { mRip } }, { "Tear_Rip_Branch_B", new[] { mRip } }, { "Tear_Rip_Hairline", new[] { mRip } },
                { "Tear_Halo", new[] { mHalo } }, { "Tear_SkyFolds", new[] { mFolds } }, { "Tear_CloudGlow", new[] { mGlowLit } },
                { "Tear_FootSkyline", new[] { mSky } }, { "Tear_FootSkylineIn", new[] { mSkyIn } }, { "Tear_LightLane", new[] { mLane } },
                { "Tear_Shafts", new[] { mShaft } },
            };
            foreach (var r in root.GetComponentsInChildren<Renderer>(true))
            {
                Material[] ms;
                if (!map.TryGetValue(r.name, out ms)) { notes.Add("裂口套件里多出来的网格 " + r.name + "（没在 README 的表里，关掉）"); r.enabled = false; continue; }
                var arr = new Material[Mathf.Max(1, r.sharedMaterials.Length)];
                for (int k = 0; k < arr.Length; k++) arr[k] = ms[Mathf.Min(k, ms.Length - 1)];
                r.sharedMaterials = arr;
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = false;
                r.lightProbeUsage = LightProbeUsage.Off;
                r.reflectionProbeUsage = ReflectionProbeUsage.Off;
                if (r.name == "Tear_Shafts") { r.gameObject.SetActive(false); log.AppendLine("Tear_Shafts（套件自带的 12 张光束扇）：关掉——门里只用 JSON shafts 的 2 束"); }
            }
            foreach (var n in map.Keys)
                if (FindDeep(root.transform, n) == null) notes.Add("Tear_Kit.fbx 里没找到 " + n);

            // CloudGlow：README 说"同一网格两个材质"。叠加那一层要能在 0 时单独关 renderer（JSON tear.fades），所以拆成两个物体、共用同一个网格
            var cg = FindDeep(root.transform, "Tear_CloudGlow");
            if (cg != null && cg.GetComponent<MeshFilter>() != null)
            {
                var add = new GameObject("Tear_CloudGlow_Additive");
                add.transform.SetParent(cg.parent, false);
                add.transform.localPosition = cg.localPosition; add.transform.localRotation = cg.localRotation; add.transform.localScale = cg.localScale;
                add.AddComponent<MeshFilter>().sharedMesh = cg.GetComponent<MeshFilter>().sharedMesh;
                var mr = add.AddComponent<MeshRenderer>();
                mr.sharedMaterial = mGlowAdd;
                mr.shadowCastingMode = ShadowCastingMode.Off; mr.receiveShadows = false; mr.lightProbeUsage = LightProbeUsage.Off; mr.reflectionProbeUsage = ReflectionProbeUsage.Off;
            }

            // 光束 2 束（JSON shafts，挂 Tear_Root，套件坐标）：Tear_ShaftCard 轴 = 本地 +Z、长 1 m、半宽 40 m（UV2.x）
            if (shaftFbx != null)
            {
                var card = shaftFbx.GetComponentInChildren<MeshFilter>(true);
                foreach (var s in L(G(G(J, "shafts"), "items")))
                {
                    var go = new GameObject(S(G(s, "id")));
                    go.transform.SetParent(root.transform, false);
                    go.transform.localPosition = V3(G(s, "start_os"));
                    go.transform.localRotation = Quaternion.LookRotation(V3(G(s, "axis_os")).normalized, Vector3.up);
                    float hw = F(G(s, "half_width_m"), 40f) / 40f;
                    go.transform.localScale = new Vector3(hw, hw, F(G(s, "length_m"), 1000f));
                    if (card != null)
                    {
                        go.AddComponent<MeshFilter>().sharedMesh = card.sharedMesh;
                        var mr = go.AddComponent<MeshRenderer>();
                        mr.sharedMaterial = mShaft;
                        mr.shadowCastingMode = ShadowCastingMode.Off; mr.receiveShadows = false; mr.lightProbeUsage = LightProbeUsage.Off; mr.reflectionProbeUsage = ReflectionProbeUsage.Off;
                    }
                    log.AppendLine("光束 " + go.name + "：起点 " + Vs(go.transform.localPosition) + "，半宽 " + Fs(F(G(s, "half_width_m"))) + " 套件米（卡的横截面缩放 " + Fs(hw) + "），长 " +
                                   Fs(F(G(s, "length_m"))) + "，增益 " + Fs(F(G(s, "gain"))) + "；JSON 的 widen " + Fs(F(G(s, "widen"))) + " 没有可对应的参数（卡是等宽的）");
                }
            }
        }

        static void WriteReport(string name, string text)
        {
            string dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "LanbaiReports"));
            Directory.CreateDirectory(dir);
            File.WriteAllText(Path.Combine(dir, name), text, new UTF8Encoding(false));
        }
    }
}
