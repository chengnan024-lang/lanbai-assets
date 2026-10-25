// =====================================================================================================
//  LanbaiAct08Builder.cs   菜单 蓝白/Build/Act08：按 Act08_Dusk/Act08_Layout.json 搭第 8 幕（暮 → 蓝时）   cloud session "云"
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Roslyn-checked (Common/Tools~/compile_check) only.
//
//  Re-runnable: deletes the previous R_Dusk and rebuilds it; the driver object Act08_Driver (under Director if there is one)
//  is KEPT and refilled. Needs in the project (import order: README §0): Assets/Lanbai/Common, GateClouds/Editor
//  (AddUdonSharp / SetupUdonSharp / FindInScenePublic), Sky (蓝白/Sky/Build Sky: the presets dusk_8i, dusk_8ii, blue_hour),
//  Sea (Models/Sea_Ceiling.fbx; 蓝白/Sea/Create Materials: M_08_SeaCeiling / Edge / Fade; Textures/Cube_DuskLower_256),
//  Clouds_v2 (the dusk cards; 蓝白/Clouds v2/Build Materials is run first).
//  Builds:
//    R_Dusk (moves: y = h(t))  Sea_Ceiling at local y 1.70 (Inner M_08_SeaCeiling, Edge M_08_SeaCeilingEdge),
//                              PalaceSpecks (25 golden points 40-200 m above it, Lanbai/SeaSpecks, generated mesh),
//                              Cards/<id> (upper, lower), Wisps/<id> (Lanbai/CloudCard, uniform scale = width)
// =====================================================================================================
#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Lanbai.CloudsV2;
using Lanbai.Sky;

public static class LanbaiAct08Builder
{
    const string Kit = "Assets/Lanbai/Act08_Dusk";
    const string CloudsKit = "Assets/Lanbai/Clouds_v2";
    const string SeaRoot = "Assets/Lanbai/Sea";

    static Dictionary<string, object> D(object o) { return o as Dictionary<string, object>; }
    static List<object> L(object o) { return o as List<object>; }
    static float F(object o) { return System.Convert.ToSingle(o); }
    static Vector3 V3(List<object> l) { return new Vector3(F(l[0]), F(l[1]), F(l[2])); }
    static Vector4 V4(List<object> l) { return new Vector4(F(l[0]), l.Count > 1 ? F(l[1]) : 0f, l.Count > 2 ? F(l[2]) : 0f, l.Count > 3 ? F(l[3]) : 0f); }
    static float[] FA(List<object> l) { var a = new float[l.Count]; for (int i = 0; i < l.Count; i++) a[i] = F(l[i]); return a; }

    static GameObject Child(Transform parent, string name)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        return go;
    }

    // the palace points: Lanbai/SeaSpecks' mesh contract (one quad = 4 vertices at the SAME position, UV0 corners,
    // UV1 = (flux, radius m), COLOR = linear colour + flicker, UV2 = (phase, Hz)); 4 km bounds
    static Mesh SpecksMesh(Dictionary<string, object> S)
    {
        string path = Kit + "/Generated/Mesh_PalaceSpecks.asset";
        Mesh m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        bool fresh = m == null;
        if (fresh) m = new Mesh();
        m.Clear();
        int n = (int)F(S["count"]);
        var y = L(S["y_above"]); var col = L(S["colour_linear"]);
        var rnd = new System.Random((int)F(S["seed"]));
        var pos = new List<Vector3>(); var uv0 = new List<Vector2>(); var uv1 = new List<Vector2>(); var uv2 = new List<Vector2>();
        var cols = new List<Color>(); var tris = new List<int>();
        Vector2[] corners = { new Vector2(-1, -1), new Vector2(1, -1), new Vector2(1, 1), new Vector2(-1, 1) };
        Color c = new Color(F(col[0]), F(col[1]), F(col[2]), F(S["flicker"]));
        for (int i = 0; i < n; i++)
        {
            float r = F(S["r_max"]) * Mathf.Sqrt((float)rnd.NextDouble());
            float th = (float)rnd.NextDouble() * 2f * Mathf.PI;
            float h = Mathf.Lerp(F(y[0]), F(y[1]), (float)rnd.NextDouble());
            var p = new Vector3(r * Mathf.Sin(th), h, r * Mathf.Cos(th));
            float phase = (float)rnd.NextDouble() * 6.283f, hz = 0.3f + 0.5f * (float)rnd.NextDouble();
            int b = pos.Count;
            for (int k = 0; k < 4; k++)
            {
                pos.Add(p); uv0.Add(corners[k]); uv1.Add(new Vector2(F(S["flux"]), F(S["radius_m"])));
                uv2.Add(new Vector2(phase, hz)); cols.Add(c);
            }
            tris.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
        }
        m.SetVertices(pos); m.SetUVs(0, uv0); m.SetUVs(1, uv1); m.SetUVs(2, uv2); m.SetColors(cols); m.SetTriangles(tris, 0);
        m.bounds = new Bounds(Vector3.zero, new Vector3(8000f, 8000f, 8000f));
        if (fresh) AssetDatabase.CreateAsset(m, path);
        return m;
    }

    static Renderer PlaceCard(Transform parent, string id, string card, Vector3 pos, float width)
    {
        var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(CloudsKit + "/Generated/Mesh_" + card + ".asset");
        var mat = AssetDatabase.LoadAssetAtPath<Material>(CloudsKit + "/Generated/M_CloudV2_" + card + ".mat");
        if (mesh == null || mat == null) { Debug.LogWarning("[Act08] no mesh / material for " + card + " (render the dusk cards, then 蓝白/Clouds v2/Build Materials)"); return null; }
        var go = Child(parent, id);
        go.transform.localPosition = pos;
        go.transform.localScale = new Vector3(width, width, width);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        var r = go.AddComponent<MeshRenderer>();
        r.sharedMaterial = mat;
        r.shadowCastingMode = ShadowCastingMode.Off;
        r.receiveShadows = false;
        r.lightProbeUsage = LightProbeUsage.Off;
        r.reflectionProbeUsage = ReflectionProbeUsage.Off;
        return r;
    }

    [MenuItem("蓝白/Build/Act08")]
    public static string Build()
    {
        string log = LanbaiCloudsV2Builder.BuildMaterials();
        if (!AssetDatabase.IsValidFolder(Kit + "/Generated")) AssetDatabase.CreateFolder(Kit, "Generated");
        string proj = Path.GetDirectoryName(Application.dataPath);
        var J = D(MiniJson.Parse(File.ReadAllText(Path.Combine(proj, Kit, "Act08_Layout.json"))));
        var CJ = D(MiniJson.Parse(File.ReadAllText(Path.Combine(proj, CloudsKit, "Textures", "cards_v2.json"))));
        var B = D(J["beats"]);
        var oldD = Object.FindObjectOfType<LanbaiAct08Driver>();

        var old = GameObject.Find("R_Dusk");
        if (old != null) Object.DestroyImmediate(old);
        var rDusk = new GameObject("R_Dusk").transform;

        // ---- the sea ceiling (the sea kit's model and materials; README_Sea接口 §4 act 8)
        var ceil = D(J["ceiling"]);
        Renderer inner = null, edge = null;
        var mCeil = AssetDatabase.LoadAssetAtPath<Material>(SeaRoot + "/Materials/M_08_SeaCeiling.mat");
        var mEdge = AssetDatabase.LoadAssetAtPath<Material>(SeaRoot + "/Materials/M_08_SeaCeilingEdge.mat");
        var mFade = AssetDatabase.LoadAssetAtPath<Material>(SeaRoot + "/Materials/M_08_SeaCeilingFade.mat");
        if (mCeil == null || mEdge == null || mFade == null) log += "\n[Act08] Sea/Materials/M_08_* missing: run 蓝白/Sea/Create Materials";
        var ceilFbx = AssetDatabase.LoadAssetAtPath<GameObject>(SeaRoot + "/Models/Sea_Ceiling.fbx");
        if (ceilFbx != null)
        {
            var cGo = (GameObject)PrefabUtility.InstantiatePrefab(ceilFbx, rDusk);
            cGo.name = "Sea_Ceiling";
            cGo.transform.localPosition = new Vector3(0f, F(ceil["y_local"]), 0f);
            foreach (var r in cGo.GetComponentsInChildren<Renderer>())
            {
                r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
                if (r.name.Contains("Inner")) { inner = r; r.sharedMaterial = mCeil; }
                else if (r.name.Contains("Edge")) { edge = r; r.sharedMaterial = mEdge; }
                r.enabled = false;
            }
            if (inner == null || edge == null) log += "\n[Act08] Sea_Ceiling.fbx: Sea_Ceiling_Inner / Sea_Ceiling_Edge not found";
        }
        else log += "\n[Act08] Sea/Models/Sea_Ceiling.fbx not found: no ceiling";

        // ---- the palace points (Lanbai/SeaSpecks, ceiling mode, queue 2995)
        var S = D(J["specks"]);
        Renderer specksR = null;
        Shader shSpecks = Shader.Find("Lanbai/SeaSpecks");
        if (shSpecks != null)
        {
            string mp = Kit + "/Generated/M_08_PalaceSpecks.mat";
            var mS = AssetDatabase.LoadAssetAtPath<Material>(mp);
            if (mS == null) { mS = new Material(shSpecks); AssetDatabase.CreateAsset(mS, mp); }
            mS.shader = shSpecks;
            mS.SetFloat("_CeilingMode", 1f);
            mS.SetFloat("_DissolveTime", -1f);
            mS.renderQueue = 2995;
            EditorUtility.SetDirty(mS);
            var sGo = Child(rDusk, "PalaceSpecks");
            sGo.transform.localPosition = new Vector3(0f, F(ceil["y_local"]), 0f);
            sGo.AddComponent<MeshFilter>().sharedMesh = SpecksMesh(S);
            specksR = sGo.AddComponent<MeshRenderer>();
            specksR.sharedMaterial = mS;
            specksR.shadowCastingMode = ShadowCastingMode.Off; specksR.receiveShadows = false;
            specksR.enabled = false;
        }
        else log += "\n[Act08] shader Lanbai/SeaSpecks not found (the sea kit)";

        // ---- the cards: upper (8-i / 8-ii), lower (the other sky, 8-ii), wisps
        var renderers = new List<Renderer>(); var groups = new List<int>(); var gains = new List<float>();
        var caps = new List<float>(); var melts = new List<Vector4>(); var tops = new List<float>(); var dists = new List<float>();
        var wBase = new List<Vector3>(); var wTan = new List<Vector3>(); var wDrift = new List<float>();
        var cardsRoot = Child(rDusk, "Cards").transform;
        var cardInfo = D(CJ["cards"]);
        foreach (object o in L(J["cards"]))
        {
            var c = D(o);
            string card = (string)c["card"];
            Vector3 pos = V3(L(c["position_local"]));
            float width = F(c["width_m"]);
            bool lower = (string)c["group"] == "lower";
            if (lower && cardInfo.ContainsKey(card))
            {
                // the lower card's TOP sits at the given elevation (it is seen from above): pivot one card height lower
                var ci = D(cardInfo[card]); var size = L(ci["size"]); var ob = L(ci["opaque_bbox_uv"]);
                float aspect = F(size[1]) / F(size[0]);
                pos.y -= (F(ob[3]) - F(ci["cloud_base_v"])) * aspect * width;
            }
            var r = PlaceCard(cardsRoot, (string)c["id"], card, pos, width);
            if (r == null) continue;
            renderers.Add(r); gains.Add(F(c["gain"]));
            groups.Add(lower ? 2 : ((string)c["show_from"] == "8i" ? 0 : 1));
            caps.Add(c.ContainsKey("fog_cap") ? F(c["fog_cap"]) : 1f);
            melts.Add(c.ContainsKey("melt") ? V4(L(c["melt"])) : new Vector4(-0.02f, 0.10f, 0f, 0f));
            tops.Add(c.ContainsKey("top_y_local") ? F(c["top_y_local"]) : pos.y); dists.Add(F(c["dist"]));
        }
        var wispRoot = Child(rDusk, "Wisps").transform;
        foreach (object o in L(J["wisps"]))
        {
            var w = D(o);
            Vector3 pos = V3(L(w["position_local"]));
            var r = PlaceCard(wispRoot, (string)w["id"], (string)w["card"], pos, F(w["width_m"]));
            if (r == null) continue;
            renderers.Add(r); gains.Add(F(w["gain"])); groups.Add(3); caps.Add(1f); melts.Add(new Vector4(-0.02f, 0.10f, 0f, 0f));
            tops.Add(pos.y); dists.Add(500f);
            wBase.Add(pos); wTan.Add(V3(L(w["tangent"]))); wDrift.Add(F(w["drift"]));
        }

        // ---- the driver
        GameObject dGo = oldD != null ? oldD.gameObject : new GameObject("Act08_Driver");
        Transform director = LanbaiGateCloudsBuilder.FindInScenePublic("Director");
        if (oldD == null && director != null) dGo.transform.SetParent(director, false);
        var d = dGo.GetComponent<LanbaiAct08Driver>();
        if (d == null) d = (LanbaiAct08Driver)LanbaiGateCloudsBuilder.AddUdonSharp(dGo, typeof(LanbaiAct08Driver));
        if (d.worldSun == null) d.worldSun = RenderSettings.sun;
        if (d.worldSun == null) log += "\n[Act08] RenderSettings.sun is empty: wire Act08_Driver.worldSun to the world's main light (D-24) by hand";
        d.roots = new[] { rDusk.gameObject };
        d.rDusk = rDusk; d.ceilingInner = inner; d.ceilingEdge = edge; d.specks = specksR;
        d.matCeiling = mCeil; d.matCeilingFade = mFade;
        d.cards = renderers.ToArray(); d.cardGroup = groups.ToArray(); d.cardGain = gains.ToArray();
        d.cardFogCap = caps.ToArray(); d.cardMelt = melts.ToArray(); d.cardTopY = tops.ToArray(); d.cardDist = dists.ToArray();
        d.ceilingOuterR = F(ceil["radius"]) + 0.5f * F(ceil["band"]);
        d.wispBase = wBase.ToArray(); d.wispTangent = wTan.ToArray(); d.wispDrift = wDrift.ToArray();
        foreach (var sp in Object.FindObjectsOfType<LanbaiSkyPreset>())
        {
            if (sp.presetName == "dusk_8i") d.dusk8i = sp;
            else if (sp.presetName == "dusk_8ii") d.dusk8ii = sp;
            else if (sp.presetName == "blue_hour") d.blueHour = sp;
        }
        if (d.dusk8i == null || d.dusk8ii == null || d.blueHour == null)
            log += "\n[Act08] a LanbaiSkyPreset (dusk_8i / dusk_8ii / blue_hour) is missing: run 蓝白/Sky/Build Sky";
        if (d.reflCube == null)
        {
            d.reflCube = AssetDatabase.LoadAssetAtPath<Texture>(SeaRoot + "/Textures/Cube_DuskLower_256.exr");
            if (d.reflCube == null) log += "\n[Act08] Sea/Textures/Cube_DuskLower_256.exr not found: assign ReflCube_DuskLower by hand";
        }

        // timeline and data
        var win = L(J["window"]);
        d.windowStart = F(win[0]); d.windowEnd = F(win[1]);
        d.tExit = F(B["exit"]); d.tF10e = F(B["F10e"]); d.tF12 = F(B["F12"]); d.tEnd8 = F(B["end8"]);
        d.tCeilingOff = F(ceil["dissolve_end"]); d.ceilingLocalY = F(ceil["y_local"]);
        var bc = D(B["cards"]); var wo = L(bc["wisp_out"]); var ci2 = L(bc["upper_8ii_in"]); var dk = L(bc["dark"]);
        d.wispOut0 = F(wo[0]); d.wispOut1 = F(wo[1]); d.cardsIn0 = F(ci2[0]); d.cardsIn1 = F(ci2[1]); d.darkDur = F(dk[1]) - F(dk[0]);
        var mo = D(J["motion"]); d.v0 = F(mo["v0"]);
        var segs = L(mo["segments"]);
        d.segT0 = new float[segs.Count]; d.segDur = new float[segs.Count]; d.segV0 = new float[segs.Count]; d.segV1 = new float[segs.Count];
        for (int i = 0; i < segs.Count; i++) { var s = D(segs[i]); d.segT0[i] = F(s["t0"]); d.segDur[i] = F(s["dur"]); d.segV0[i] = F(s["v0"]); d.segV1[i] = F(s["v1"]); }
        var sun = D(J["sun"]); var sd = L(sun["dir"]);
        d.sunDir = new Vector3(F(sd[0]), F(sd[1]), F(sd[2])); d.discRadius = F(sun["disc_radius_deg"]);
        var lt = D(B["light"]); Color sc; ColorUtility.TryParseHtmlString((string)lt["colour_srgb"], out sc);
        d.sunColor = sc; d.sunE = F(lt["E"]); d.sunFloor = F(lt["floor"]);
        var rv = D(J["reveal"]); d.revealT0 = F(rv["t0"]); d.revealDt = F(rv["dt"]); d.reveal = FA(L(rv["frac"]));
        var sl = D(B["sun_line"]); var gr = L(sl["grow"]); d.lineDeg = F(gr[2]); d.lineGrow0 = F(gr[0]); d.lineGrow = F(gr[1]) - F(gr[0]);
        var cl = L(sl["collapse"]); d.lineCollapse = F(cl[1]) - F(cl[0]);
        var sk = D(B["sun_sink"]); var skt = L(sk["t"]); var ske = L(sk["el"]);
        d.sunEl0 = F(ske[0]); d.sunSinkDur = F(skt[1]) - F(skt[0]);
        var fg = D(B["fog"]); d.fogWater = F(fg["water"]); d.fogAir = F(fg["air"]); d.fogII = F(fg["ii"]);
        if (J.ContainsKey("grade")) { var g = D(J["grade"]); d.gradeT = FA(L(g["t"])); d.gradeDev = FA(L(g["dev"])); }
        else log += "\n[Act08] Act08_Layout.json has no grade table (Source/act08_grade.py): LanbaiGrade reports nothing";

        // card colours (D-25: per act; Clouds_v2 cards_v2.json colours.duskU / duskD / blue)
        var cols = CJ.ContainsKey("colours") ? D(CJ["colours"]) : null;
        if (cols != null && cols.ContainsKey("duskU") && cols.ContainsKey("duskD"))
        {
            var u = D(cols["duskU"]); var lo = D(cols["duskD"]);
            var tint = L(D(J["other"])["tint"]);
            Vector4 tn = new Vector4(F(tint[0]), F(tint[1]), F(tint[2]), 1f);
            d.upSun = V4(L(u["SunColor"])); d.upSky = V4(L(u["SkyUpColor"])); d.upGround = V4(L(u["GroundColor"]));
            d.loSun = Vector4.Scale(V4(L(lo["SunColor"])), tn); d.loSky = Vector4.Scale(V4(L(lo["SkyUpColor"])), tn);
            d.loGround = Vector4.Scale(V4(L(lo["GroundColor"])), tn);
        }
        else log += "\n[Act08] cards_v2.json has no colours.duskU / duskD yet (render + solve the dusk cards): the cards stay black";
        if (J.ContainsKey("blue_colours"))
        {
            var bh = D(J["blue_colours"]);
            d.blueSky = V4(L(bh["SkyUpColor"])); d.blueGround = V4(L(bh["GroundColor"]));
        }

        LanbaiGateCloudsBuilder.SetupUdonSharp(d);
        EditorUtility.SetDirty(d);
        AssetDatabase.SaveAssets();
        string rep = string.Format("[Act08] built: ceiling {0}, {1} palace points, {2} cards + wisps, driver window {3}..{4}{5}",
            inner != null ? "ok" : "MISSING", (int)F(S["count"]), renderers.Count, d.windowStart, d.windowEnd, log);
        Debug.Log(rep);
        return rep;
    }
}
#endif
