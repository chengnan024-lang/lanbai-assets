// =====================================================================================================
//  LanbaiAct06Builder.cs   菜单 蓝白/Build/Act06：按 Act06_Dawn/Act06_Layout.json 搭第 6 幕（晨）   cloud session "云"
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Roslyn-checked (Common/Tools~/compile_check) only.
//
//  Re-runnable: deletes the previous R_Dawn / R_DawnRing and rebuilds them; the driver object Act06_Driver (under
//  Director if there is one) is KEPT and refilled (the dispatcher's reference, worldSun and the two takeover switches
//  survive). Needs in the project: Assets/Lanbai/Clouds_v2 (the cards; 蓝白/Clouds v2/Build Materials is run first),
//  Assets/Lanbai/Sea (Models/Sea_Disc.fbx, Materials/M_06_Sea.mat: built by the sea's builder), Assets/Lanbai/Sky (the
//  'dawn' LanbaiSkyPreset under Lanbai_SkyPresets: 蓝白/Sky/Build Sky), Assets/Lanbai/Overlay (one LanbaiOverlay),
//  Assets/Lanbai/GateClouds/Editor (AddUdonSharp / SetupUdonSharp / FindInScenePublic).
//  Builds:
//    R_Dawn (moves: y = d(t))  Act06_Plain (Lanbai/CloudPlain proxy, M_06_CloudPlain), Sea_Plane (Sea_Disc + M_06_Sea at
//                              the layout's level), Cards/<id> (Lanbai/CloudCard, uniform scale = width)
//    R_DawnRing (fixed)        Ring_<nn>: the horizon ring (stays at the eye's horizon while R_Dawn moves)
// =====================================================================================================
#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Lanbai.CloudsV2;
using Lanbai.Sky;

public static class LanbaiAct06Builder
{
    const string Kit = "Assets/Lanbai/Act06_Dawn";
    const string CloudsKit = "Assets/Lanbai/Clouds_v2";
    const string SeaRoot = "Assets/Lanbai/Sea";

    static Dictionary<string, object> D(object o) { return o as Dictionary<string, object>; }
    static List<object> L(object o) { return o as List<object>; }
    static float F(object o) { return System.Convert.ToSingle(o); }
    static Vector4 V4(List<object> l) { return new Vector4(F(l[0]), l.Count > 1 ? F(l[1]) : 0f, l.Count > 2 ? F(l[2]) : 0f, l.Count > 3 ? F(l[3]) : 0f); }
    static Color SRGB(string hex) { Color c; ColorUtility.TryParseHtmlString(hex, out c); return c; }

    static GameObject Child(Transform parent, string name)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        return go;
    }

    // two quads (object y = -1 under the eye, +1 over it), 32 km: the CloudPlain proxy
    static Mesh ProxyMesh()
    {
        string path = Kit + "/Generated/Mesh_PlainProxy.asset";
        Mesh m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        bool fresh = m == null;
        if (fresh) m = new Mesh();
        m.Clear();
        float s = 16000f;
        m.vertices = new[] {
            new Vector3(-s, -1, -s), new Vector3(s, -1, -s), new Vector3(s, -1, s), new Vector3(-s, -1, s),
            new Vector3(-s, 1, -s), new Vector3(s, 1, -s), new Vector3(s, 1, s), new Vector3(-s, 1, s) };
        m.triangles = new[] { 0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7 };
        m.bounds = new Bounds(Vector3.zero, new Vector3(2 * s, 8000f, 2 * s));
        if (fresh) AssetDatabase.CreateAsset(m, path);
        return m;
    }

    [MenuItem("蓝白/Build/Act06")]
    public static string Build()
    {
        string log = LanbaiCloudsV2Builder.BuildMaterials();
        if (!AssetDatabase.IsValidFolder(Kit + "/Generated")) AssetDatabase.CreateFolder(Kit, "Generated");
        string proj = Path.GetDirectoryName(Application.dataPath);
        var J = D(MiniJson.Parse(File.ReadAllText(Path.Combine(proj, Kit, "Act06_Layout.json"))));
        var CJ = D(MiniJson.Parse(File.ReadAllText(Path.Combine(proj, CloudsKit, "Textures", "cards_v2.json"))));
        var cardInfo = D(CJ["cards"]);
        var dawnCol = D(D(CJ["colours"])["dawn"]);

        foreach (string n in new[] { "R_Dawn", "R_DawnRing" })
        {
            Transform old = LanbaiGateCloudsBuilder.FindInScenePublic(n);
            if (old != null) Object.DestroyImmediate(old.gameObject);
        }
        Transform oldD = LanbaiGateCloudsBuilder.FindInScenePublic("Act06_Driver");
        var rDawn = new GameObject("R_Dawn").transform;
        var rRing = new GameObject("R_DawnRing").transform;

        // ---- the cloud body
        var body = D(J["body"]);
        var slot = D(body["slot"]); var lip = D(body["lip"]); var edge = D(body["edge"]);
        var sun = D(J["sun"]);
        Shader shPlain = Shader.Find("Lanbai/CloudPlain");
        string matPath = Kit + "/Generated/M_06_CloudPlain.mat";
        Material mPlain = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (mPlain == null) { mPlain = new Material(shPlain); AssetDatabase.CreateAsset(mPlain, matPath); }
        mPlain.shader = shPlain;
        // r2 (review r1): the two tiles are DATA: sRGB off, RGBA32 uncompressed, Repeat, mips, aniso 16
        foreach (string tp in new[] { Kit + "/Textures/Plain_Detail_1024.png", Kit + "/Textures/Plain_Macro_512.png" })
        {
            var ti = AssetImporter.GetAtPath(tp) as TextureImporter;
            if (ti == null) { log += "\n[Act06] missing " + tp; continue; }
            bool dirty = ti.sRGBTexture || ti.textureCompression != TextureImporterCompression.Uncompressed || ti.wrapMode != TextureWrapMode.Repeat
                         || !ti.mipmapEnabled || ti.anisoLevel != 16;
            if (dirty)
            {
                ti.sRGBTexture = false; ti.textureCompression = TextureImporterCompression.Uncompressed; ti.wrapMode = TextureWrapMode.Repeat;
                ti.mipmapEnabled = true; ti.anisoLevel = 16; ti.filterMode = FilterMode.Trilinear;
                var ps = ti.GetDefaultPlatformTextureSettings(); ps.format = TextureImporterFormat.RGBA32; ti.SetPlatformTextureSettings(ps);
                ti.SaveAndReimport();
            }
        }
        mPlain.SetTexture("_DetailTex", AssetDatabase.LoadAssetAtPath<Texture2D>(Kit + "/Textures/Plain_Detail_1024.png"));
        mPlain.SetTexture("_MacroTex", AssetDatabase.LoadAssetAtPath<Texture2D>(Kit + "/Textures/Plain_Macro_512.png"));
        mPlain.SetVector("_Body", new Vector4(F(body["top"]), F(body["bottom"]), F(sun["az_deg"]), 0));
        mPlain.SetVector("_Slot", new Vector4(F(slot["axis_az"]), F(slot["half_width"]), F(slot["s0"]), F(slot["s1"])));
        mPlain.SetVector("_SlotB", new Vector4(F(slot["soft"]), F(slot["floor_top"]), F(slot["center_q"]), 0));
        mPlain.SetVector("_Lip", new Vector4(F(lip["top"]), F(lip["soft"]), 0, 0));
        mPlain.SetVector("_Edge", new Vector4(F(edge["r0"]), F(edge["r_sun"]), F(edge["sun_lobe_deg"]), F(edge["soft"])));
        mPlain.SetVector("_SunColor", V4(L(dawnCol["SunColor"])));
        mPlain.SetVector("_SkyUpColor", V4(L(dawnCol["SkyUpColor"])));
        mPlain.SetVector("_GroundColor", V4(L(dawnCol["GroundColor"])));
        var sd = L(sun["dir"]);
        mPlain.SetVector("_SunDirFallback", new Vector4(F(sd[0]), F(sd[1]), F(sd[2]), 0));
        EditorUtility.SetDirty(mPlain);
        var pGo = Child(rDawn, "Act06_Plain");
        pGo.AddComponent<MeshFilter>().sharedMesh = ProxyMesh();
        var pR = pGo.AddComponent<MeshRenderer>();
        pR.sharedMaterial = mPlain;
        pR.shadowCastingMode = ShadowCastingMode.Off;          // its ShadowCaster pass serves the camera depth only
        pR.receiveShadows = false;

        // ---- r2: the slot's mist (Lanbai/CloudPlainMist): the same proxy, a second renderer (Transparent-5)
        var mist = D(body["mist"]);
        Shader shMist = Shader.Find("Lanbai/CloudPlainMist");
        string mistPath = Kit + "/Generated/M_06_PlainMist.mat";
        Material mMist = AssetDatabase.LoadAssetAtPath<Material>(mistPath);
        if (mMist == null) { mMist = new Material(shMist); AssetDatabase.CreateAsset(mMist, mistPath); }
        mMist.shader = shMist;
        mMist.SetVector("_Mist", new Vector4(F(mist["y_top"]), F(mist["y_peak"]), F(mist["y_bot"]), F(mist["sigma"])));
        mMist.SetVector("_MistColor", V4(L(mist["color_linear"])));
        // r3 (D-35 #1 / #4): the clear wedge toward the sun, depth, undulation, rolling top, wisps
        var mvy = L(mist["wedge_vy"]); var mph = L(mist["phase"]); var mcut = L(mist["wisp_cut"]);
        mMist.SetTexture("_DetailTex", AssetDatabase.LoadAssetAtPath<Texture2D>(Kit + "/Textures/Plain_Detail_1024.png"));
        mMist.SetVector("_MistPhase", new Vector4(F(mph[0]), F(mph[1]), F(mph[2]), 0));
        mMist.SetVector("_MistWedge", new Vector4(F(mist["wedge_full_deg"]), F(mist["wedge_zero_deg"]), F(mvy[0]), F(mvy[1])));
        mMist.SetVector("_MistShade", new Vector4(F(mist["shade_dark"]), F(mist["shade_pow"]), F(mist["shade_depth"]), F(mist["roll_amp"])));
        mMist.SetVector("_MistUnd", new Vector4(F(mist["und_period"]), F(mist["und_amp"]), F(mist["und_col"]), F(mist["und_drift"])));
        mMist.SetVector("_MistRoll", new Vector4(F(mist["roll_period"]), 0, 0, 0));
        mMist.SetVector("_MistWisp", new Vector4(F(mist["wisp_lo"]), F(mist["wisp_mid"]), F(mist["wisp_hi"]), F(mist["wisp_sigma"])));
        mMist.SetVector("_MistWispB", new Vector4(F(mist["wisp_period"]), F(mist["wisp_drift"]), F(mcut[0]), F(mcut[1])));
        mMist.SetVector("_MistSteps", new Vector4(F(mist["steps"]), F(mist["max_len"]), 0, 0));
        mMist.SetVector("_Slot", mPlain.GetVector("_Slot"));
        mMist.SetVector("_SlotB", mPlain.GetVector("_SlotB"));
        mMist.SetVector("_SunDirFallback", mPlain.GetVector("_SunDirFallback"));
        EditorUtility.SetDirty(mMist);
        var mGo = Child(rDawn, "Act06_PlainMist");
        mGo.AddComponent<MeshFilter>().sharedMesh = ProxyMesh();
        var mR = mGo.AddComponent<MeshRenderer>();
        mR.sharedMaterial = mMist;
        mR.shadowCastingMode = ShadowCastingMode.Off;
        mR.receiveShadows = false;

        // ---- the sea (ABOVE; the sea's own material)
        var seaJ = D(J["sea"]);
        Renderer seaR = null;
        var disc = AssetDatabase.LoadAssetAtPath<GameObject>(SeaRoot + "/Models/Sea_Disc.fbx");
        var mSea = AssetDatabase.LoadAssetAtPath<Material>(SeaRoot + "/Materials/M_06_Sea.mat");
        if (disc != null)
        {
            var sGo = (GameObject)PrefabUtility.InstantiatePrefab(disc, rDawn);
            sGo.name = "Sea_Plane";
            sGo.transform.localPosition = new Vector3(0f, F(seaJ["level_local"]), 0f);
            seaR = sGo.GetComponentInChildren<Renderer>();
            if (seaR != null) { seaR.sharedMaterial = mSea; seaR.shadowCastingMode = ShadowCastingMode.Off; seaR.receiveShadows = false; seaR.enabled = false; }
        }
        else log += "\n[Act06] Sea/Models/Sea_Disc.fbx not found: no sea";
        if (mSea == null) log += "\n[Act06] Sea/Materials/M_06_Sea.mat not found: run the sea's builder first";

        // ---- the cards and the ring
        var renderers = new List<Renderer>();
        var gains = new List<float>(); var mirrors = new List<float>(); var isRing = new List<bool>();
        var ids = new List<string>();
        var cardsRoot = Child(rDawn, "Cards").transform;
        float eyeY = 1.70f;
        foreach (object o in L(J["cards"]))
        {
            var c = D(o);
            string card = (string)c["card"];
            if (!cardInfo.ContainsKey(card)) { log += "\n[Act06] card missing: " + card; continue; }
            var r = PlaceCard(cardsRoot, (string)c["id"], card, V3(L(c["position_local"])), F(c["width_m"]), V4(L(c["melt"])));
            if (r == null) continue;
            renderers.Add(r); gains.Add(F(c["gain"])); mirrors.Add(F(c["mirror"])); isRing.Add(false); ids.Add((string)c["id"]);
        }
        foreach (object o in L(J["ring"]))
        {
            var c = D(o);
            string card = (string)c["card"];
            if (!cardInfo.ContainsKey(card)) card = "CloudSeaV2_1_dawn";
            if (!cardInfo.ContainsKey(card)) continue;
            var ci = D(cardInfo[card]);
            var size = L(ci["size"]);
            float aspect = F(size[1]) / F(size[0]);
            var pl = L(c["position_local"]);
            float R = Mathf.Sqrt(F(pl[0]) * F(pl[0]) + F(pl[2]) * F(pl[2]));
            float topY = eyeY + R * Mathf.Tan(F(c["top_el_deg"]) * Mathf.Deg2Rad);
            float vTop = F(L(ci["opaque_bbox_uv"])[3]);
            float pivY = topY - (vTop - F(ci["cloud_base_v"])) * aspect * F(c["width_m"]);
            var r = PlaceCard(rRing, (string)c["id"], card, new Vector3(F(pl[0]), pivY, F(pl[2])), F(c["width_m"]), new Vector4(-0.02f, 0.10f, 0, 0));
            if (r == null) continue;
            renderers.Add(r); gains.Add(F(c["gain"])); mirrors.Add(F(c["mirror"])); isRing.Add(true); ids.Add((string)c["id"]);
        }

        // ---- the driver
        GameObject dGo = oldD != null ? oldD.gameObject : new GameObject("Act06_Driver");
        Transform director = LanbaiGateCloudsBuilder.FindInScenePublic("Director");
        if (oldD == null && director != null) dGo.transform.SetParent(director, false);
        var d = dGo.GetComponent<LanbaiAct06Driver>();
        if (d == null) d = (LanbaiAct06Driver)LanbaiGateCloudsBuilder.AddUdonSharp(dGo, typeof(LanbaiAct06Driver));
        if (d.worldSun == null) d.worldSun = RenderSettings.sun;
        if (d.worldSun == null) log += "\n[Act06] RenderSettings.sun is empty: wire Act06_Driver.worldSun to the world's main light (D-24) by hand";
        d.roots = new[] { rDawn.gameObject, rRing.gameObject };
        d.rDawn = rDawn; d.plain = pR; d.plainMist = mR; d.seaRenderer = seaR;
        d.cards = renderers.ToArray(); d.cardGain = gains.ToArray(); d.cardMirror = mirrors.ToArray(); d.cardIsRing = isRing.ToArray();
        foreach (var sp in Object.FindObjectsOfType<LanbaiSkyPreset>())
            if (sp.presetName == "dawn") d.skyPreset = sp;
        if (d.skyPreset == null) log += "\n[Act06] no LanbaiSkyPreset 'dawn' in the scene: run 蓝白/Sky/Build Sky";
        // r2 (review r1 S5): the sea's mirror needs _Udon_ReflCube and has no fallback of its own. Until Control bakes
        // Refl_S6, render a stand-in here: 2 m above the sea, under the cover (R_Dawn is at y = 0 while building, so
        // the field's local = world), whatever sky the scene has now (apply the dawn preset first for the right one).
        if (d.reflCube == null || d.reflCube.name == "Refl_S6_standin")
        {
            string cubePath = Kit + "/Generated/Refl_S6_standin.asset";
            var cube = new Cubemap(256, TextureFormat.RGBAHalf, false);
            var camGo = new GameObject("Act06_ReflCam");
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.5f; cam.farClipPlane = 30000f; cam.allowHDR = true;
            camGo.transform.position = new Vector3(0f, F(seaJ["level_local"]) + 2f, 0f);
            bool ok = cam.RenderToCubemap(cube);
            Object.DestroyImmediate(camGo);
            if (ok)
            {
                cube.name = "Refl_S6_standin";
                var oldCube = AssetDatabase.LoadAssetAtPath<Cubemap>(cubePath);
                if (oldCube != null) AssetDatabase.DeleteAsset(cubePath);
                AssetDatabase.CreateAsset(cube, cubePath);
                d.reflCube = cube;
                log += "\n[Act06] _Udon_ReflCube: a stand-in cube (Generated/Refl_S6_standin), replace with Control's Refl_S6";
            }
            else log += "\n[Act06] RenderToCubemap failed: the sea mirror has no cube (assign Act06_Driver.reflCube by hand)";
        }
        d.overlay = Object.FindObjectOfType<LanbaiOverlay>();
        if (d.overlay == null) log += "\n[Act06] no LanbaiOverlay in the scene: the dawn reveal will not be drawn (Overlay/)";

        var win = L(J["window"]); d.windowStart = F(win[0]); d.windowEnd = F(win[1]);
        var B = D(J["beats"]);
        var labels = D(J["labels"]);
        d.tApplySky = F(B["apply_sky_t"]); d.tLight0 = F(B["main_light_t0"]); d.tLight1 = F(B["main_light_t1"]);
        d.tRS1 = F(B["render_settings_t1"]); d.tF0 = F(labels["F0"]); d.tSeaOn = F(B["sea_on"]); d.tEntry = F(B["entry"]);
        d.tPreroll0 = F(B["preroll_t0"]); d.tDawn0 = F(B["dawn_t0"]); d.dawnT = F(B["dawn_per_dir_s"]);
        { var sg = D(B["stagger"]); var lb = D(B["lobes"]);
          d.leadZenith = F(sg["skylight_zenith"]); d.leadBelow = F(sg["below"]); d.leadSun = F(sg["sun_sector"]); d.leadElse = F(sg["horizon"]);
          d.lobeZenithDeg = F(lb["zenith_deg"]); d.lobeBelowDeg = F(lb["below_deg"]); d.lobeSunDeg = F(lb["sun_deg"]); d.leadSoft = F(lb["else_soft_deg"]); } d.tOverlayOff = F(B["dawn_t1"]) + 0.1f;
        var so = L(B["slot_open"]); d.slotOpen0 = F(so[0]); d.slotOpen1 = F(so[1]);
        var ro = D(B["ring_off"]); d.ringOff0 = F(ro["t0"]); d.ringOff1 = F(ro["t1"]);
        var ans = L(B["tower_answer"]);
        d.answerT0 = new float[ans.Count]; d.answerCard = new int[ans.Count];
        for (int i = 0; i < ans.Count; i++) { var a = D(ans[i]); d.answerT0[i] = F(a["t0"]); d.answerCard[i] = ids.IndexOf((string)a["id"]); }
        var cp = D(B["sea_calm_patch"]); d.calmPatchT0 = F(cp["t0"]); d.calmPatchDur = F(cp["dur"]); d.calmPatchR = F(cp["radius"]);
        var ca = D(B["sea_calm_all"]); d.calmAllT0 = F(ca["t0"]); d.calmAllDur = F(ca["dur"]); d.calmAllV = F(ca["v1"]);
        var mo = D(J["motion"]); var segs = L(mo["segments"]);
        d.vStart = F(mo["v_start"]);
        d.segT0 = new float[segs.Count]; d.segDur = new float[segs.Count]; d.segV0 = new float[segs.Count]; d.segV1 = new float[segs.Count];
        for (int i = 0; i < segs.Count; i++) { var s = D(segs[i]); d.segT0[i] = F(s["t0"]); d.segDur[i] = F(s["dur"]); d.segV0[i] = F(s["v0"]); d.segV1[i] = F(s["v1"]); }
        d.seaLevelLocal = F(seaJ["level_local"]);
        d.sunDir = new Vector3(F(sd[0]), F(sd[1]), F(sd[2]));
        d.sunColor = SRGB((string)sun["color_srgb"]); d.sunE = F(sun["E"]);
        var st = D(J["sun_table"]); var vis = L(st["vis"]);
        d.sunTabT0 = F(st["t0"]); d.sunTabDt = F(st["dt"]); d.sunSmooth = F(st["smoothing_s"]);
        d.sunTab = new float[vis.Count];
        for (int i = 0; i < vis.Count; i++) d.sunTab[i] = F(vis[i]);
        var lt = D(J["light"]); var tri = D(lt["trilight_srgb"]);
        d.triSky = SRGB((string)tri["sky"]); d.triEquator = SRGB((string)tri["equator"]); d.triGround = SRGB((string)tri["ground"]);
        d.sunFloorOccluded = F(lt["sun_occluded_floor"]);
        d.fogDensity = F(D(J["fog"])["density"]);
        { var fb = D(D(J["fog"])["model_b"]); var fa = L(fb["far_act06"]); var na = L(fb["nadir_act06"]);
          d.fogFarAct = new Vector4(F(fa[0]), F(fa[1]), F(fa[2]), 1f); d.fogNadirAct = new Vector4(F(na[0]), F(na[1]), F(na[2]), 1f);
          d.fogWidthAct = F(fb["width_act06"]);
          var ne = L(fb["near"]); var ze = L(fb["zenith"]);
          d.fogNearAct = new Vector4(F(ne[0]), F(ne[1]), F(ne[2]), 1f); d.fogZenithAct = new Vector4(F(ze[0]), F(ze[1]), F(ze[2]), 1f);
          d.fogColourK = F(D(B["fog_under_cover"])["colour_k"]);
          d.fogColorGamma = new Color(F(fa[0]), F(fa[1]), F(fa[2])).gamma; }   // the built-in fog colour = the far horizon
        var fu = D(B["fog_under_cover"]);
        d.fogUnder = F(fu["under"]); d.fogDownT0 = F(fu["down_t0"]); d.fogUpT0 = F(fu["up_t0"]); d.fogDur = F(fu["dur"]);
        // (r3: no longer the preset's fogColor: act 6 writes its own far horizon, D-35 #3)
        LanbaiGateCloudsBuilder.SetupUdonSharp(d);
        EditorUtility.SetDirty(d);
        AssetDatabase.SaveAssets();
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(rDawn.gameObject.scene);
        string rep = string.Format("[Act06] built: plain, sea {0}, {1} cards (+ ring), driver window {2}..{3}{4}",
            seaR != null ? "yes" : "NO", renderers.Count, d.windowStart, d.windowEnd, log);
        Debug.Log(rep);
        return rep;
    }

    static Vector3 V3(List<object> l) { return new Vector3(F(l[0]), F(l[1]), F(l[2])); }

    static Renderer PlaceCard(Transform parent, string id, string card, Vector3 pos, float width, Vector4 melt)
    {
        var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(CloudsKit + "/Generated/Mesh_" + card + ".asset");
        var mat = AssetDatabase.LoadAssetAtPath<Material>(CloudsKit + "/Generated/M_CloudV2_" + card + ".mat");
        if (mesh == null || mat == null) { Debug.LogWarning("[Act06] no mesh / material for " + card + " (蓝白/Clouds v2/Build Materials)"); return null; }
        var go = Child(parent, id);
        go.transform.localPosition = pos;
        go.transform.localScale = new Vector3(width, width, width);       // uniform = the card width (Clouds_v2 README §0)
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        var r = go.AddComponent<MeshRenderer>();
        r.sharedMaterial = mat;
        r.shadowCastingMode = ShadowCastingMode.Off;
        r.receiveShadows = false;
        r.lightProbeUsage = LightProbeUsage.Off;
        r.reflectionProbeUsage = ReflectionProbeUsage.Off;
        return r;
    }
}
#endif
