// =====================================================================================================
//  LanbaiPalaceBuilder.cs   蓝白 · 菜单 蓝白/Build/7b 宫殿：按 Palace/PalaceLayout.json（编进 LanbaiPalaceData.cs）把河伯宫殿搭起来
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn), never in Unity. !!!
//
//  可重复运行：先删上一次搭的 R_Palace。做的事：
//   1. R_Palace：有 R_Sea 就挂在它下面，局部位置 (0, −TerraceDepth, 0)（海的约定：R_Sea = (0, depth, −fwd) → R_Palace = −busPos(t)）；
//      没有 R_Sea 时放在场景根上并警告（单独看宫殿用）。会移动的根：Batching Static / Occlusion Static 关、Contribute GI 开（圣经 §1.6）。
//   2. Palace/Models/*.fbx 实例化在 R_Palace 下（局部变换为单位：顶点就是宫殿坐标）；<名>_LOD0 / _LOD1 自己建 LODGroup（CONTROL §6 第 4 条）。
//   3. 材质 Palace/Materials/M_07b_*.mat（Lanbai/Palace 等），按网格里的槽名（M_07b_<槽>）挂上。
//   4. 烘焙灯：每盏宫灯两盏 Baked 点光（暖 #FF9C2F range 4、软阴影；靛 #2A557B range 12、无阴影），门里一盏 Baked 面光。
//      Inspector 强度 = PalaceLayout.json 的 intensity（D-00：Inspector = E；点光在 d 处 E = I / d² × 范围窗，按灰卡校，README §4）。
//   5. 驱动 LanbaiPalaceDriver（U#，CONTROL §5），程序资产按 GateClouds 的做法建。
//  不做：烘焙本身（README §4 的步骤，本地做）、R_Sea 的运动（海）、_Udon_PalaceVeil（海）。
// =====================================================================================================
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class LanbaiPalaceBuilder
{
    const string Root = "Assets/Lanbai/Palace/";
    const string MatDir = Root + "Materials/";
    const string TexDir = Root + "Textures/";
    const string ModelDir = Root + "Models/";
    static readonly string[] Models = { "Palace_Terrace", "Palace_Weeds", "Palace_Lamps", "Palace_Hall", "Palace_Que", "Palace_Houses", "Palace_Door", "Palace_Flames", "Palace_Fish" };
    // LOD 切换（屏幕高度比例）：LOD0 → LOD1 → 剔除
    static readonly Dictionary<string, float[]> LodCut = new Dictionary<string, float[]>
    {
        { "Lamps", new[] { 0.06f, 0.0f } }, { "Houses", new[] { 0.08f, 0.0f } }, { "Hall", new[] { 0.10f, 0.0f } },
        { "Que", new[] { 0.12f, 0.0f } }, { "Terrace", new[] { 0.15f, 0.0f } },
    };
    // 光照贴图分辨率比例（每个渲染器）：近处细，远处粗
    static readonly Dictionary<string, float> LmScale = new Dictionary<string, float>
    {
        { "Terrace", 0.25f }, { "Weeds", 0.5f }, { "Lamps", 2.0f }, { "Hall", 0.6f }, { "Que", 0.8f }, { "Houses", 0.6f },
    };

    [MenuItem("蓝白/Build/7b 宫殿")]
    public static void Build()
    {
        // ---- 1. 根
        Transform rSea = FindInScene("R_Sea");
        var old = rSea != null ? rSea.Find("R_Palace") : null;
        if (old == null) { var o2 = GameObject.Find("R_Palace"); if (o2 != null) old = o2.transform; }
        if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var root = new GameObject("R_Palace");
        if (rSea != null)
        {
            root.transform.SetParent(rSea, false);
            root.transform.localPosition = new Vector3(0f, -LanbaiPalaceData.TerraceDepth, 0f);
        }
        else Debug.LogWarning("[Palace] 场景里没有 R_Sea：R_Palace 放在根上（只能单独看宫殿；第 7 幕要先跑 蓝白/Build/Act07a）");
        // ---- 2. 材质
        var mats = BuildMaterials();
        // ---- 3. 模型
        var renderers = new List<Renderer>();
        Renderer fishR = null;
        foreach (string m in Models)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(ModelDir + m + ".fbx");
            if (asset == null) { Debug.LogWarning("[Palace] 缺 " + ModelDir + m + ".fbx"); continue; }
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(asset, root.transform);
            PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            inst.name = m;
            inst.transform.localPosition = Vector3.zero;
            inst.transform.localRotation = Quaternion.identity;
            inst.transform.localScale = Vector3.one;
            foreach (var r in inst.GetComponentsInChildren<MeshRenderer>(true))
            {
                AssignMaterials(r, m, mats);
                renderers.Add(r);
                if (m == "Palace_Fish") fishR = r;
            }
            MakeLods(inst.transform);
        }
        foreach (var r in renderers) SetupStatic(r);
        // ---- 4. 灯
        var lights = new GameObject("Palace_BakedLights");
        lights.transform.SetParent(root.transform, false);
        int n = LanbaiPalaceData.Flames.Length / 3;
        var lampLocal = new Vector3[n];
        for (int i = 0; i < n; i++)
        {
            var p = new Vector3(LanbaiPalaceData.Flames[3 * i], LanbaiPalaceData.Flames[3 * i + 1], LanbaiPalaceData.Flames[3 * i + 2]);
            lampLocal[i] = p;
            Baked(lights.transform, LanbaiPalaceData.LampIds[i] + "_Warm", p, LanbaiPalaceData.WarmColor, LanbaiPalaceData.WarmI, LanbaiPalaceData.WarmRange, true);
            Baked(lights.transform, LanbaiPalaceData.LampIds[i] + "_Indigo", p + new Vector3(0f, LanbaiPalaceData.IndigoLift, 0f), LanbaiPalaceData.IndigoColor, LanbaiPalaceData.IndigoI, LanbaiPalaceData.IndigoRange, false);
        }
        var dg = new GameObject("DoorSpill");
        dg.transform.SetParent(lights.transform, false);
        dg.transform.localPosition = V3(LanbaiPalaceData.DoorSpillPos, 0);
        dg.transform.localRotation = Quaternion.LookRotation(Vector3.back, Vector3.up);   // 面光朝 −z（朝外）
        var dl = dg.AddComponent<Light>();
        dl.type = LightType.Rectangle;
        dl.lightmapBakeType = LightmapBakeType.Baked;
        dl.areaSize = new Vector2(LanbaiPalaceData.DoorSpillSize[0], LanbaiPalaceData.DoorSpillSize[1]);
        dl.color = Lin(LanbaiPalaceData.DoorColor).gamma;
        dl.intensity = LanbaiPalaceData.DoorAreaI;
        // ---- 5. 驱动
        var oldD = GameObject.Find("LanbaiPalaceDriver");
        if (oldD != null) UnityEngine.Object.DestroyImmediate(oldD);
        var dGo = new GameObject("LanbaiPalaceDriver");
        // 驱动放在场景根上：R_Sea / R_Palace 关着时它也要能被 Dispatcher 调到
        var d = (LanbaiPalaceDriver)LanbaiGateCloudsBuilder.AddUdonSharp(dGo, typeof(LanbaiPalaceDriver));
        d.rPalace = root;
        d.rPalaceTf = root.transform;
        d.fish = fishR;
        d.lampLocal = lampLocal;
        d.lampIntensity = LanbaiPalaceData.WarmI;
        d.lampColorLinear = Lin(LanbaiPalaceData.WarmColor);
        LanbaiGateCloudsBuilder.SetupUdonSharp(d);
        EditorUtility.SetDirty(d);
        AssetDatabase.SaveAssets();
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(root.scene);
        Debug.Log(string.Format("[Palace] built: {0} renderers, {1} lamps x 2 baked lights + door; parent {2}. 下一步：README §4 烘焙。",
                                renderers.Count, n, rSea != null ? "R_Sea" : "(scene root)"));
    }

    // ------------------------------------------------------------------ 材质
    static Dictionary<string, Material> BuildMaterials()
    {
        if (!AssetDatabase.IsValidFolder(Root + "Materials")) AssetDatabase.CreateFolder(Root.TrimEnd('/'), "Materials");
        var d = new Dictionary<string, Material>();
        Shader pal = Shader.Find("Lanbai/Palace");
        // 名字、反照率贴图、法线、掩码、模式、光滑度（无掩码时）、金属（模式 0）、淤泥覆盖、色调
        Std(d, pal, "Lacquer", "Lacquer", "Lacquer", "Lacquer", 0, 0.8f, 0f, 0.55f, "#FFFFFF");
        Std(d, pal, "LacquerBlack", null, null, null, 0, 0.75f, 0f, 0.4f, "#282426");
        Std(d, pal, "LacquerBand", "LacquerBand", null, "LacquerBand", 0, 0.78f, 0f, 0.3f, "#FFFFFF");
        Std(d, pal, "Gilt", null, null, null, 0, 0.60f, 1f, 0.3f, "#C9A56A");
        Std(d, pal, "Bronze", "Bronze", "Bronze", "Bronze", 1, 0.55f, 0f, 0.2f, "#FFFFFF");
        Std(d, pal, "Verdigris", null, null, null, 0, 0.32f, 0f, 0.3f, "#3E7A68");
        Std(d, pal, "Stone", "Stone", "Stone", "Stone", 0, 0.30f, 0f, 0.6f, "#FFFFFF");
        Std(d, pal, "StoneDark", "Stone", "Stone", "Stone", 0, 0.30f, 0f, 0.4f, "#CCCCCC");
        Std(d, pal, "FishScale", "FishScale", "FishScale", "FishScale", 2, 0.86f, 0f, 0.25f, "#FFFFFF");
        Std(d, pal, "Cowrie", "Cowrie", "Cowrie", "Cowrie", 3, 0.92f, 0f, 0.2f, "#FFFFFF");
        Std(d, pal, "Tile", "Stone", "Stone", null, 0, 0.35f, 0f, 0.7f, "#F2F8FF");
        Std(d, pal, "Wood", null, null, null, 0, 0.35f, 0f, 0.2f, "#2C2522");
        Std(d, pal, "Rock", "Rock", "Rock", "Rock", 0, 0.22f, 0f, 0.5f, "#FFFFFF");
        Std(d, pal, "Weed", null, null, null, 0, 0.55f, 0f, 0f, "#2E3A26");
        d["Weed"].SetFloat("_SwayAmp", 0.25f);
        d["Weed"].SetFloat("_Cull", 0f);
        // 鱼
        var fish = Mat("Fish", Shader.Find("Lanbai/PalaceFish"));
        fish.SetVector("_Centre", V4(LanbaiPalaceData.FishCentre, 0f));
        fish.SetVector("_Torus", new Vector4(LanbaiPalaceData.FishR, LanbaiPalaceData.FishTube, LanbaiPalaceData.FishRev, 6f));
        fish.SetVector("_PassPoint", new Vector4(LanbaiPalaceData.FishPassPoint[0], LanbaiPalaceData.FishPassPoint[1], LanbaiPalaceData.FishPassPoint[2], LanbaiPalaceData.FishPassPoint[3]));
        fish.SetVector("_PassVel", new Vector4(LanbaiPalaceData.FishPassVel[0], LanbaiPalaceData.FishPassVel[1], LanbaiPalaceData.FishPassVel[2], 0f));
        d["Fish"] = fish;
        // 门里的光（不透明）与门口的锥形光卡（加色）
        var glow = Mat("DoorGlow", Shader.Find("Lanbai/PalaceGlow"));
        glow.SetVector("_Glow", new Vector4(3f * LanbaiPalaceData.DoorColor[0], 3f * LanbaiPalaceData.DoorColor[1], 3f * LanbaiPalaceData.DoorColor[2], 0f));
        d["DoorGlow"] = glow;
        var cone = Mat("DoorCone", Shader.Find("Lanbai/PalaceGlow"));
        cone.SetVector("_Glow", glow.GetVector("_Glow"));
        cone.SetFloat("_Additive", 1f);
        cone.SetFloat("_SrcBlend", (float)BlendMode.One);
        cone.SetFloat("_DstBlend", (float)BlendMode.One);
        cone.SetFloat("_ZWrite", 0f);
        cone.renderQueue = 3000;
        d["DoorCone"] = cone;
        // 灯焰与灯晕
        var fl = Mat("Flame", Shader.Find("Lanbai/PalaceFlame"));
        fl.SetTexture("_FlipTex", AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "T_07b_Flame_Flip4x2.png"));
        fl.SetVector("_FlameColor", V4(LanbaiPalaceData.FlameLinear, 0f));
        fl.SetVector("_HaloMid", V4(LanbaiPalaceData.HaloMid, 0f));
        d["Flame"] = fl;
        foreach (var m in d.Values) EditorUtility.SetDirty(m);
        return d;
    }

    static void Std(Dictionary<string, Material> d, Shader sh, string name, string alb, string nrm, string mask, int mode, float smooth, float metal, float silt, string tint)
    {
        var m = Mat(name, sh);
        if (alb != null) m.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "T_07b_" + alb + "_Albedo.png"));
        if (nrm != null) m.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "T_07b_" + nrm + "_Normal.png"));
        if (mask != null) m.SetTexture("_MaskMap", AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "T_07b_" + mask + "_Mask.png"));
        m.SetFloat("_UseMask", mask != null ? 1f : 0f);
        m.SetFloat("_SmoothnessConst", smooth);
        m.SetFloat("_Mode", mode);
        m.SetFloat("_Metallic", metal);
        m.SetFloat("_SiltAmount", silt);
        Color c;
        ColorUtility.TryParseHtmlString(tint, out c);
        m.SetColor("_Color", c);
        // 贴图是 1 UV = 一个平铺（网格的 UV0 已按米 / 平铺长度给），所以 ST = (1, 1, 0, 0)
        m.enableInstancing = true;
        d[name] = m;
    }

    static Material Mat(string name, Shader sh)
    {
        string p = MatDir + "M_07b_" + name + ".mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(p);
        if (m == null)
        {
            m = new Material(sh != null ? sh : Shader.Find("Standard"));
            AssetDatabase.CreateAsset(m, p);
        }
        if (sh != null) m.shader = sh;
        else Debug.LogError("[Palace] shader 找不到：M_07b_" + name + "（Palace/Shaders 是否在 Assets/Lanbai/Palace/Shaders？）");
        return m;
    }

    static void AssignMaterials(MeshRenderer r, string model, Dictionary<string, Material> mats)
    {
        var src = r.sharedMaterials;
        var dst = new Material[src.Length];
        for (int i = 0; i < dst.Length; i++)
        {
            string slot = src[i] != null ? src[i].name.Replace("M_07b_", "") : "";
            if (model == "Palace_Flames") slot = "Flame";
            if (model == "Palace_Door" && r.name.StartsWith("DoorCones")) slot = "DoorCone";
            if (model == "Palace_Fish") slot = "Fish";
            Material m;
            if (!mats.TryGetValue(slot, out m))
            {
                Debug.LogWarning("[Palace] " + r.name + " 的槽 '" + slot + "' 没有材质，用 Stone");
                m = mats["Stone"];
            }
            dst[i] = m;
        }
        r.sharedMaterials = dst;
        r.shadowCastingMode = (model == "Palace_Flames" || model == "Palace_Door" || model == "Palace_Fish") ? ShadowCastingMode.Off : ShadowCastingMode.On;
        r.receiveShadows = false;
        r.lightProbeUsage = LightProbeUsage.Off;
        r.reflectionProbeUsage = ReflectionProbeUsage.Off;
    }

    static void SetupStatic(Renderer r)
    {
        string key = null;
        foreach (var k in LmScale.Keys) if (r.name.StartsWith(k)) key = k;
        bool lightmapped = key != null;
        var flags = lightmapped ? StaticEditorFlags.ContributeGI : 0;      // 会移动的根：不批处理、不遮挡剔除（圣经 §1.6）
        GameObjectUtility.SetStaticEditorFlags(r.gameObject, flags);
        if (lightmapped)
        {
            var so = new SerializedObject(r);
            var p = so.FindProperty("m_ScaleInLightmap");
            if (p != null) { p.floatValue = LmScale[key]; so.ApplyModifiedPropertiesWithoutUndo(); }
            var mr = r as MeshRenderer;
            if (mr != null) mr.receiveGI = ReceiveGI.Lightmaps;
        }
    }

    static void MakeLods(Transform inst)
    {
        var byBase = new Dictionary<string, Renderer[]>();
        foreach (var r in inst.GetComponentsInChildren<MeshRenderer>(true))
        {
            int k = r.name.LastIndexOf("_LOD");
            if (k < 0) continue;
            string b = r.name.Substring(0, k);
            int lod = r.name.EndsWith("1") ? 1 : 0;
            Renderer[] a;
            if (!byBase.TryGetValue(b, out a)) { a = new Renderer[2]; byBase[b] = a; }
            a[lod] = r;
        }
        foreach (var kv in byBase)
        {
            if (kv.Value[1] == null) continue;           // 只有 LOD0：不建 LODGroup
            var g = new GameObject(kv.Key + "_LODGroup");
            g.transform.SetParent(inst, false);
            kv.Value[0].transform.SetParent(g.transform, true);
            kv.Value[1].transform.SetParent(g.transform, true);
            var lg = g.AddComponent<LODGroup>();
            float[] cut = new[] { 0.08f, 0.0f };
            foreach (var c in LodCut) if (kv.Key.StartsWith(c.Key)) cut = c.Value;
            lg.SetLODs(new[] { new LOD(cut[0], new[] { kv.Value[0] }), new LOD(cut[1] > 0f ? cut[1] : 0.002f, new[] { kv.Value[1] }) });
            lg.RecalculateBounds();
        }
    }

    static void Baked(Transform parent, string name, Vector3 p, float[] lin, float intensity, float range, bool shadows)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.transform.localPosition = p;
        var l = go.AddComponent<Light>();
        l.type = LightType.Point;
        l.lightmapBakeType = LightmapBakeType.Baked;
        l.color = Lin(lin).gamma;
        l.intensity = intensity;
        l.range = range;
        l.shadows = shadows ? LightShadows.Soft : LightShadows.None;
        l.shadowRadius = 0.10f;
        l.renderMode = LightRenderMode.ForceVertex;
    }

    static Color Lin(float[] c) { return new Color(c[0], c[1], c[2], 1f); }
    static Vector3 V3(float[] a, int i) { return new Vector3(a[i], a[i + 1], a[i + 2]); }
    static Vector4 V4(float[] a, float w) { return new Vector4(a[0], a[1], a[2], a.Length > 3 ? a[3] : w); }

    static Transform FindInScene(string name)
    {
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
        {
            if (go.name == name) return go.transform;
            var t = FindDeep(go.transform, name);
            if (t != null) return t;
        }
        return null;
    }

    static Transform FindDeep(Transform p, string name)
    {
        foreach (Transform c in p)
        {
            if (c.name == name) return c;
            var t = FindDeep(c, name);
            if (t != null) return t;
        }
        return null;
    }
}
