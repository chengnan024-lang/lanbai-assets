// 蓝白 · 触手之门 · 云 —— 一键搭建（Editor）  gate clouds kit v1, 2026-10-22, cloud art team.
// !!! NOT COMPILED IN UNITY: compile and check. !!!
//
// Menu 蓝白/Gate Clouds/Build  (or LanbaiGateCloudsBuilder.Build() from a script, e.g. the gate test's Build):
//   reads GateClouds_Layout.json next to this kit, sets the texture import settings, makes the meshes and materials
//   (in <kit>/Generated/), and builds under the scene's GateRoot:
//     GateRoot/GateClouds/Deck            the deck quad (Lanbai/GateCloudDeck)
//     GateRoot/GateClouds/Cards/<id>      37 cards (Lanbai/GateCloudCard): 9 towers, 4 far, 22 horizon, 2 mist
//     GateRoot/GateClouds/Wedges/<id>     4 shadow wedges (Lanbai/GateBeam, mode 1)
//     <Tear root>/GateBeam_<id>           2 shafts (Lanbai/GateBeam, mode 0), Tear_Root (or Tear_Kit) object space
//   and the LanbaiGateClouds driver on GateRoot/GateClouds with every array filled. Run it again any time: it
//   deletes what it built before. Nothing else in the scene is touched.
// D-44 #3 (2026-10-25): the volume cloud. If the scene draws the gate's cloud with 阿白's volume deck
//   (Lanbai/Local/VolumeCloudDeck, or this kit's Lanbai/GateVolumeDeck = the same + the root skirts), that material is
//   kept across rebuilds on GateClouds/Deck, its shader is switched to Lanbai/GateVolumeDeck (same properties), and its
//   _NoiseVolume / _Density / _CloudWind are copied into the driver (the arms read the very same density). The arms'
//   root centrelines come from GateClouds_Skirts.json (Source/seam_ref.py bake). No volume material: nothing changes.
// Menu 蓝白/Gate Clouds/Apply At U7b (or Apply(t)): edit-mode preview of the towers at time t and the cards'
//   property blocks (property blocks are not saved; Play / VRChat writes them in LanbaiGateClouds.Start).
// Put this file in an Editor folder WITHOUT an asmdef (it needs Assembly-CSharp's LanbaiGateClouds).
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

public static class LanbaiGateCloudsBuilder
{
    [Serializable] public class DeckDef
    {
        public string parent; public float local_y; public float quad_size; public string detail; public string macro;
        public string quality; public QualityDef[] quality_tiers;       // the deck's quality switch (README §3.4)
    }
    [Serializable] public class QualityDef { public string name; public float[] adapt; public float[] march_range; public int steps; }
    [Serializable] public class ShapeDef { public string shape; public string texture; public int[] size_px; public float[] scale; public float[] pivot_uv; public float[] bbox_uv; }
    [Serializable] public class CardDef
    {
        public string id; public string group; public string shape; public float[] position; public float[] size;
        public float opacity; public float gain; public float mirror; public int queue; public float[] melt; public float fog_cap; public float crop_bottom;
        public float[] sag_keys; public float[] sink_keys; public float[] alpha_keys; public string hides;
    }
    [Serializable] public class BeamDef { public string id; public string parent; public float mode; public float[] start; public float[] axis; public float half_width; public float length; public float widen; public float intensity; }
    [Serializable] public class FogBandDef { public float[] color; public float until; }
    [Serializable] public class SkirtArm { public string id; public float[] pts; public float[] r; public float[] reveal; }
    [Serializable] public class SkirtFile { public float level; public float climb; public float width; public float strength; public SkirtArm[] arms; }
    [Serializable] public class Layout { public float hero_t; public float[] window; public FogBandDef fog_band; public DeckDef deck; public ShapeDef[] shapes; public CardDef[] cards; public BeamDef[] beams; }

    const string RootName = "GateClouds";

    static string KitDir()
    {
        string[] g = AssetDatabase.FindAssets("GateClouds_Layout");
        foreach (string id in g)
        {
            string p = AssetDatabase.GUIDToAssetPath(id);
            if (p.EndsWith("GateClouds_Layout.json")) return Path.GetDirectoryName(p).Replace('\\', '/');
        }
        throw new Exception("GateClouds_Layout.json not found in Assets (copy the GateClouds kit into the project)");
    }

    static Layout Load(string kit)
    {
        return JsonUtility.FromJson<Layout>(File.ReadAllText(kit + "/GateClouds_Layout.json"));
    }

    static Transform FindInScene(string name)
    {
        foreach (GameObject go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
        {
            if (go.name == name) return go.transform;
            Transform t = FindDeep(go.transform, name);
            if (t != null) return t;
        }
        return null;
    }

    static Transform FindDeep(Transform p, string name)
    {
        foreach (Transform c in p)
        {
            if (c.name == name) return c;
            Transform t = FindDeep(c, name);
            if (t != null) return t;
        }
        return null;
    }

    // ---- import settings ----------------------------------------------------------------------------------------
    static void SetupTexture(string path, bool srgb, bool repeat, bool uncompressed)
    {
        var ti = AssetImporter.GetAtPath(path) as TextureImporter;
        if (ti == null) { Debug.LogWarning("[GateClouds] missing texture " + path); return; }
        ti.textureType = TextureImporterType.Default;
        ti.sRGBTexture = srgb;
        ti.alphaSource = TextureImporterAlphaSource.FromInput;
        ti.alphaIsTransparency = srgb;            // cards: yes (straight alpha); deck tiles: data
        ti.wrapMode = repeat ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
        ti.mipmapEnabled = true;
        ti.mipmapFilter = TextureImporterMipFilter.BoxFilter;
        ti.filterMode = FilterMode.Trilinear;
        ti.anisoLevel = repeat ? 4 : 2;           // the deck's footprints already go through tex2Dgrad (VR r1: 16 was 4-8x the fetches)
        ti.maxTextureSize = 2048;
        ti.npotScale = TextureImporterNPOTScale.None;
        // Default platform: compression only (its format must stay Automatic); the format goes in the PC override
        ti.textureCompression = uncompressed ? TextureImporterCompression.Uncompressed : TextureImporterCompression.CompressedHQ;
        var pc = ti.GetPlatformTextureSettings("Standalone");
        pc.overridden = true;
        pc.maxTextureSize = 2048;
        pc.format = uncompressed ? TextureImporterFormat.RGBA32 : TextureImporterFormat.BC7;
        ti.SetPlatformTextureSettings(pc);
        ti.SaveAndReimport();
    }

    // ---- meshes ---------------------------------------------------------------------------------------------------
    static Mesh SaveMesh(Mesh m, string path)
    {
        m.name = Path.GetFileNameWithoutExtension(path);   // 本地 gate_clouds_test-04：网格名和文件名一致（_crop45 那几张以前对不上）
        var old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (old != null) { EditorUtility.CopySerialized(m, old); return old; }
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    static Mesh DeckQuad(float size)
    {
        float h = 0.5f * size;
        var m = new Mesh { name = "GateClouds_DeckQuad" };
        m.vertices = new[] { new Vector3(-h, 0, -h), new Vector3(h, 0, -h), new Vector3(h, 0, h), new Vector3(-h, 0, h) };
        m.uv = new[] { Vector2.zero, Vector2.right, Vector2.one, Vector2.up };
        m.normals = new[] { Vector3.up, Vector3.up, Vector3.up, Vector3.up };
        m.triangles = new[] { 0, 2, 1, 0, 3, 2 };
        m.bounds = new Bounds(Vector3.zero, new Vector3(size, 200f, size));
        return m;
    }

    static Mesh CardQuad(ShapeDef s, float cropBottom = 0f)
    {
        // the quad cropped to the cloud's alpha bbox (VR r1: ~32 % less overdraw); positions in card units (scale = size)
        float pu = s.pivot_uv[0], pv = s.pivot_uv[1];
        float u0 = s.bbox_uv[0], v0 = Mathf.Min(s.bbox_uv[1], pv), u1 = s.bbox_uv[2], v1 = s.bbox_uv[3];
        v0 += Mathf.Clamp01(cropBottom) * (v1 - v0);   // round 10: the tower back layers drop their always-hidden lower part
        var m = new Mesh { name = "GateClouds_Card_" + s.shape };
        m.vertices = new[] { new Vector3(u0 - pu, v0 - pv, 0), new Vector3(u1 - pu, v0 - pv, 0), new Vector3(u1 - pu, v1 - pv, 0), new Vector3(u0 - pu, v1 - pv, 0) };
        m.uv = new[] { new Vector2(u0, v0), new Vector2(u1, v0), new Vector2(u1, v1), new Vector2(u0, v1) };
        m.uv2 = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };   // y: 0..1 up the quad (the bottom feather)
        m.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.back };
        m.triangles = new[] { 0, 2, 1, 0, 3, 2 };
        float r = Mathf.Max(pu - u0, u1 - pu);
        m.bounds = new Bounds(new Vector3(0, 0.5f * (v0 + v1) - pv, 0), new Vector3(2 * r, v1 - v0, 2 * r));   // the yaw billboard turns
        return m;
    }

    static Mesh BeamStrip(BeamDef b)
    {
        const int rows = 32;
        var v = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>();
        for (int i = 0; i <= rows; i++)
        {
            float z = i / (float)rows;
            float hw = b.half_width * (1f + (b.widen - 1f) * z);
            v.Add(new Vector3(-hw, 0, z * b.length)); uv.Add(new Vector2(0, z));
            v.Add(new Vector3(hw, 0, z * b.length)); uv.Add(new Vector2(1, z));
            if (i < rows) { int k = 2 * i; tri.AddRange(new[] { k, k + 2, k + 1, k + 1, k + 2, k + 3 }); }
        }
        var m = new Mesh { name = "GateClouds_Beam_" + b.id };
        m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(tri, 0);
        float w = b.half_width * b.widen;
        m.bounds = new Bounds(new Vector3(0, 0, 0.5f * b.length), new Vector3(2 * w, 2 * w, b.length));   // turns about the axis
        return m;
    }

    // ---- materials ------------------------------------------------------------------------------------------------
    static Material SaveMat(Shader sh, string path)
    {
        if (sh == null) throw new Exception("[GateClouds] a kit shader did not compile (Shader.Find returned null): see the Console, " + path);
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
        m.shader = sh;
        return m;
    }

    static void V(Material m, string n, params float[] f)
    {
        m.SetVector(n, new Vector4(f[0], f.Length > 1 ? f[1] : 0, f.Length > 2 ? f[2] : 0, f.Length > 3 ? f[3] : 0));
    }

    [MenuItem("蓝白/Gate Clouds/Build")]
    public static void BuildMenu()
    {
        // D-41：先等 U# 程序资产初始化完（新建的要等 SDK 在 EditorApplication.update 里升版本），再搭
        Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("蓝白/Gate Clouds/Build", new[] { typeof(LanbaiGateClouds) }, () => Build());
    }

    public static GameObject Build()
    {
        Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Gate Clouds/Build", typeof(LanbaiGateClouds));   // D-41：没初始化完就不动场景
        string kit = KitDir();
        Layout L = Load(kit);
        string gen = kit + "/Generated";
        if (!AssetDatabase.IsValidFolder(gen)) AssetDatabase.CreateFolder(kit, "Generated");

        SetupTexture(kit + "/Textures/" + L.deck.detail, false, true, true);
        SetupTexture(kit + "/Textures/" + L.deck.macro, false, true, true);
        foreach (ShapeDef s in L.shapes) SetupTexture(kit + "/Textures/" + s.texture, true, false, false);

        Transform gateRoot = FindInScene("GateRoot");
        if (gateRoot == null) throw new Exception("[GateClouds] no GateRoot in the open scene");
        Transform tearRoot = FindDeep(gateRoot, "Tear_Root") ?? FindDeep(gateRoot, "Tear_Kit");
        Transform old = gateRoot.Find(RootName);
        // D-44 #3: the volume deck material, if the scene has one (ours first: the previous build's Deck)
        Renderer volR = FindVolumeDeck(old);
        Material volMat = volR != null ? volR.sharedMaterial : null;
        bool volOnOurDeck = volR != null && old != null && volR.transform.IsChildOf(old);
        if (volMat != null)
        {
            Shader gv = Shader.Find("Lanbai/GateVolumeDeck");
            if (gv != null && volMat.shader != gv)
            {
                Debug.Log("[GateClouds] volume deck " + volMat.name + ": shader " + volMat.shader.name + " -> Lanbai/GateVolumeDeck (+ root skirts)");
                volMat.shader = gv;
                EditorUtility.SetDirty(volMat);
            }
        }
        if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
        if (tearRoot != null)
            for (int i = tearRoot.childCount - 1; i >= 0; i--)
                if (tearRoot.GetChild(i).name.StartsWith("GateBeam_")) UnityEngine.Object.DestroyImmediate(tearRoot.GetChild(i).gameObject);

        var root = new GameObject(RootName).transform;
        root.SetParent(gateRoot, false);

        // deck
        Shader deckSh = Shader.Find("Lanbai/GateCloudDeck");
        Material deckMat = SaveMat(deckSh, gen + "/M_GateCloudDeck.mat");
        deckMat.SetTexture("_DetailTex", AssetDatabase.LoadAssetAtPath<Texture2D>(kit + "/Textures/" + L.deck.detail));
        deckMat.SetTexture("_MacroTex", AssetDatabase.LoadAssetAtPath<Texture2D>(kit + "/Textures/" + L.deck.macro));
        string lanes = Path.GetDirectoryName(kit).Replace('\\', '/') + "/Gate/Textures/Tear_CloudLanes_1024.png";
        // its import belongs to the gate's own import script (BC7, shared with Lanbai_Tear): not touched here (v1.5)
        deckMat.SetTexture("_LanesTex", AssetDatabase.LoadAssetAtPath<Texture2D>(lanes));
        // the quality tier named in the JSON (deck.quality: "default" | "auto_lite"); an unknown or empty name falls back to
        // "default" with a warning (the material is reused between builds: it must never keep the last build's tier)
        QualityDef pick = null, def = null;
        if (L.deck.quality_tiers != null)
            foreach (QualityDef q in L.deck.quality_tiers)
            {
                if (q.adapt == null || q.adapt.Length != 4 || q.march_range == null || q.march_range.Length != 4) continue;
                if (q.name == "default") def = q;
                if (q.name == L.deck.quality) pick = q;
            }
        if (pick == null)
        {
            Debug.LogWarning("[GateClouds] deck.quality \"" + L.deck.quality + "\" not found in quality_tiers: using \"default\"");
            pick = def;
        }
        if (pick != null)
        {
            V(deckMat, "_Adapt", pick.adapt);
            V(deckMat, "_MarchRange", pick.march_range);
            deckMat.SetFloat("_Steps", Mathf.Clamp(pick.steps > 0 ? pick.steps : 128, 16, 160));   // a missing "steps" reads 0
            Debug.Log("[GateClouds] deck quality: " + pick.name);
        }
        var deck = new GameObject("Deck");
        deck.transform.SetParent(root, false);
        deck.transform.localPosition = new Vector3(0, L.deck.local_y, 0);
        deck.AddComponent<MeshFilter>().sharedMesh = SaveMesh(DeckQuad(L.deck.quad_size), gen + "/GateClouds_DeckQuad.asset");
        var dr = deck.AddComponent<MeshRenderer>();
        dr.sharedMaterial = deckMat;
        if (volMat != null)
        {
            if (volOnOurDeck) dr.sharedMaterial = volMat;        // the volume deck draws on our quad (as in FullPreview)
            else
            {
                dr.enabled = false;                                  // another renderer draws it: no second deck
                Debug.Log("[GateClouds] the scene's volume deck (" + volR.name + ") draws the gate's cloud: GateClouds/Deck off");
            }
        }
        dr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        dr.receiveShadows = false;

        // cards
        Shader cardSh = Shader.Find("Lanbai/GateCloudCard");
        var shapes = new Dictionary<string, ShapeDef>();
        var meshes = new Dictionary<string, Mesh>();
        foreach (ShapeDef s in L.shapes)
        {
            shapes[s.shape] = s;
            meshes[s.shape] = SaveMesh(CardQuad(s), gen + "/GateClouds_Card_" + s.shape + ".asset");
        }
        var mats = new Dictionary<string, Material>();
        var cardsRoot = new GameObject("Cards").transform;
        cardsRoot.SetParent(root, false);
        var allR = new List<Renderer>(); var allMir = new List<float>(); var allGain = new List<float>(); var allOp = new List<float>();
        var towT = new List<Transform>(); var towR = new List<Renderer>(); var towOp = new List<float>(); var towMir = new List<float>(); var towGain = new List<float>();
        var towY = new List<float>(); var towSY = new List<float>();
        var sagK = new List<float>(); var sagS = new List<int>(); var sagN = new List<int>();
        var sinkK = new List<float>(); var sinkS = new List<int>(); var sinkN = new List<int>();
        var alK = new List<float>(); var alS = new List<int>(); var alN = new List<int>();
        foreach (CardDef c in L.cards)
        {
            ShapeDef s = shapes[c.shape];
            string key = c.shape + "_" + c.group;
            if (!mats.TryGetValue(key, out Material m))
            {
                m = SaveMat(cardSh, gen + "/M_GateCard_" + key + ".mat");
                m.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(kit + "/Textures/" + s.texture));
                V(m, "_Scale", s.scale[0], s.scale[1], s.scale[2], 0);
                V(m, "_Melt", c.melt[0], c.melt[1], 0, 0);
                V(m, "_FogDensity", 0.0006f, 1f, 0.35f, c.fog_cap);
                m.renderQueue = c.queue;
                m.enableInstancing = true;
                mats[key] = m;
            }
            var go = new GameObject(c.id);
            go.transform.SetParent(cardsRoot, false);
            go.transform.localPosition = new Vector3(c.position[0], c.position[1], c.position[2]);
            go.transform.localScale = new Vector3(c.size[0], c.size[1], c.size[0]);   // z = width: the bounds must hold the turning card
            string mk = c.crop_bottom > 0f ? c.shape + "_crop" + Mathf.RoundToInt(c.crop_bottom * 100f) : c.shape;
            if (!meshes.ContainsKey(mk)) meshes[mk] = SaveMesh(CardQuad(s, c.crop_bottom), gen + "/GateClouds_Card_" + mk + ".asset");
            go.AddComponent<MeshFilter>().sharedMesh = meshes[mk];
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = m;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            allR.Add(r); allMir.Add(c.mirror); allGain.Add(c.gain); allOp.Add(c.opacity);
            if (c.group == "tower")
            {
                towT.Add(go.transform); towR.Add(r); towOp.Add(c.opacity); towMir.Add(c.mirror); towGain.Add(c.gain);
                towY.Add(c.position[1]); towSY.Add(c.size[1]);
                Pack(c.sag_keys, sagK, sagS, sagN); Pack(c.sink_keys, sinkK, sinkS, sinkN); Pack(c.alpha_keys, alK, alS, alN);
            }
        }

        // beams: shafts under the tear root (its object space), wedges under GateRoot
        Shader beamSh = Shader.Find("Lanbai/GateBeam");
        var wedges = new GameObject("Wedges").transform;
        wedges.SetParent(root, false);
        foreach (BeamDef b in L.beams)
        {
            Transform parent = b.parent == "Tear_Root" ? tearRoot : wedges;
            if (parent == null) { Debug.LogWarning("[GateClouds] no Tear_Root / Tear_Kit under GateRoot: shaft " + b.id + " skipped"); continue; }
            Material m = SaveMat(beamSh, gen + "/M_GateBeam_" + b.id + ".mat");
            m.SetFloat("_Mode", b.mode);
            m.SetFloat("_SrcBlend", b.mode < 0.5f ? (float)UnityEngine.Rendering.BlendMode.One : (float)UnityEngine.Rendering.BlendMode.Zero);
            m.SetFloat("_DstBlend", b.mode < 0.5f ? (float)UnityEngine.Rendering.BlendMode.One : (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            V(m, "_Beam", b.half_width, b.length, b.widen, 0.85f);
            if (b.mode > 0.5f) V(m, "_ViewCone", 25f, 40f, 0f, 0f);    // wedges: only toward the wound (VR r1: 1.86 FSE at U8side)
            m.SetFloat("_Intensity", b.intensity);
            if (b.mode > 0.5f) V(m, "_NearFadeM", 0, 1, 0, 0);       // wedges: no near fade (they start behind the arms)
            m.renderQueue = b.mode < 0.5f ? 2998 : 2991;                 // wedges after the far cards (tech r1 #13)
            var go = new GameObject((b.parent == "Tear_Root" ? "GateBeam_" : "") + b.id);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(b.start[0], b.start[1], b.start[2]);
            go.transform.localRotation = Quaternion.LookRotation(new Vector3(b.axis[0], b.axis[1], b.axis[2]).normalized, Vector3.up);
            go.AddComponent<MeshFilter>().sharedMesh = SaveMesh(BeamStrip(b), gen + "/GateClouds_Beam_" + b.id + ".asset");
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = m;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
        }

        // driver: on an ALWAYS-ACTIVE object (Director v1: LanbaiActivate switches `root`, never the driver's own object):
        // under the scene's "Director" if there is one, else its own top-level object "GateClouds_Driver"
        Transform oldDrv = FindInScene("GateClouds_Driver");                // inactive ones too (tech r2 #8)
        if (oldDrv != null) UnityEngine.Object.DestroyImmediate(oldDrv.gameObject);
        var drvGo = new GameObject("GateClouds_Driver");
        Transform director = FindInScene("Director");
        if (director != null) drvGo.transform.SetParent(director, false);
        var drv = AddDriver(drvGo);
        drv.root = root.gameObject;
        if (L.window != null && L.window.Length == 2) { drv.windowStart = L.window[0]; drv.windowEnd = L.window[1]; }
        // fog_band: read by Gate/Editor/LanbaiGateDriverBuilder.cs (the gate driver's fallback when the sky kit is missing)
        drv.cardRenderers = allR.ToArray(); drv.cardMirror = allMir.ToArray(); drv.cardGain = allGain.ToArray(); drv.cardOpacity = allOp.ToArray();
        drv.towers = towT.ToArray(); drv.towerRenderers = towR.ToArray(); drv.towerOpacity = towOp.ToArray();
        drv.towerMirror = towMir.ToArray(); drv.towerGain = towGain.ToArray();
        drv.towerBaseY = towY.ToArray(); drv.towerBaseScaleY = towSY.ToArray();
        drv.sagKeys = sagK.ToArray(); drv.sagStart = sagS.ToArray(); drv.sagCount = sagN.ToArray();
        drv.sinkKeys = sinkK.ToArray(); drv.sinkStart = sinkS.ToArray(); drv.sinkCount = sinkN.ToArray();
        drv.alphaKeys = alK.ToArray(); drv.alphaStart = alS.ToArray(); drv.alphaCount = alN.ToArray();
        FillVolume(drv, volMat, gateRoot, kit);
        SetupUdonSharp(drv);
        // the deck now draws the tear's pool itself (tech r1 #4): the flat cloud-top layers would be cut by the billows;
        // round 4: the foot's skyline cards (art r2: dark lumps; the deck's billows and crevasse take the lens foot now)
        // and the gate test's old even-width shafts (tech r2 #2: two sets of beams next to GateBeam_Shaft_*)
        if (tearRoot != null)
            foreach (string n in new[] { "Tear_CloudGlow", "Tear_CloudGlow_Additive", "Tear_LightLane", "Tear_FootSkyline",
                                         "Tear_FootSkylineIn", "Shaft_00", "Shaft_01" })
            {
                Transform t = FindDeep(tearRoot, n);
                var rr = t != null ? t.GetComponent<Renderer>() : null;
                if (rr != null) { rr.enabled = false; Debug.Log("[GateClouds] turned off " + n + " (GateClouds replaces it)"); }
            }
        EditorUtility.SetDirty(drv);
        AssetDatabase.SaveAssets();
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(root.gameObject.scene);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(drvGo.scene);
        Apply(L.hero_t);
        Debug.Log(string.Format("[GateClouds] built: deck, {0} cards ({1} towers), {2} beams", allR.Count, towT.Count, L.beams.Length));
        return root.gameObject;
    }

    // UdonSharp 1.x：D-41 起全部走共用的 Common/Editor/LanbaiUdonPrograms（按 Type 查程序资产、等 SDK 初始化完、
    // CopyProxyToUdon 出错照实报）。以前这里按 MonoScript 反射去查，SDK 3.10.5 里那个重载是 private，永远查不到，
    // 每次都新建程序资产、马上 CopyProxyToUdon，于是 “outdated script version”（本地 gate_clouds_test-03）。
    static LanbaiGateClouds AddDriver(GameObject go) { return (LanbaiGateClouds)AddUdonSharp(go, typeof(LanbaiGateClouds)); }
    static void SetupUdonSharp(LanbaiGateClouds drv) { SetupUdonSharp((MonoBehaviour)drv); }

    // any UdonSharpBehaviour type (Gate、Act06、Act07 的搭建脚本也调它)：程序资产要已经初始化完（搭建菜单用 RunWhenReady 等）
    public static MonoBehaviour AddUdonSharp(GameObject go, Type type)
    {
        return (MonoBehaviour)Lanbai.Udon.LanbaiUdonPrograms.AddComponent(go, type);
    }

    // after the fields are filled: copy them into the backing UdonBehaviour; a missing backing behaviour is an error
    public static void SetupUdonSharp(MonoBehaviour b)
    {
        Lanbai.Udon.LanbaiUdonPrograms.CopyProxyToUdon(b);
    }

    public static Transform FindInScenePublic(string name) { return FindInScene(name); }
    public static Transform FindDeepPublic(Transform p, string name) { return FindDeep(p, name); }

    static bool IsVolumeShader(Shader sh)
    {
        return sh != null && (sh.name == "Lanbai/GateVolumeDeck" || sh.name == "Lanbai/Local/VolumeCloudDeck");
    }

    // the renderer that draws the volume cloud: under the previous GateClouds first, else anywhere in the open scenes
    static Renderer FindVolumeDeck(Transform oldRoot)
    {
        if (oldRoot != null)
            foreach (Renderer r in oldRoot.GetComponentsInChildren<Renderer>(true))
                if (r.sharedMaterial != null && IsVolumeShader(r.sharedMaterial.shader)) return r;
        foreach (Renderer r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None || !r.gameObject.scene.IsValid()) continue;
            if (r.sharedMaterial != null && IsVolumeShader(r.sharedMaterial.shader)) return r;
        }
        return null;
    }

    // D-44 #3: the volume globals' sources and the arms' skirts
    static void FillVolume(LanbaiGateClouds drv, Material volMat, Transform gateRoot, string kit)
    {
        drv.gateRoot = gateRoot;
        drv.cloudVolumeTex = null;
        if (volMat == null)
        {
            Debug.Log("[GateClouds] no volume deck in the scene: the arms keep TentacleSway v2.7d's cloud-top fade");
            return;
        }
        drv.cloudVolumeTex = volMat.GetTexture("_NoiseVolume") as Texture3D;
        if (drv.cloudVolumeTex == null) Debug.LogWarning("[GateClouds] the volume deck has no 3D _NoiseVolume: volume mode off");
        drv.cloudVolume = new Vector4(1f, volMat.HasProperty("_Density") ? volMat.GetFloat("_Density") : 0.036f, 520f, 260f);
        Vector4 w = volMat.HasProperty("_CloudWind") ? volMat.GetVector("_CloudWind") : new Vector4(8f, 3f, 0f, 0f);
        drv.cloudWind = new Vector4(w.x, w.y, 0f, 0f);
        string path = kit + "/GateClouds_Skirts.json";
        if (!File.Exists(path)) { Debug.LogWarning("[GateClouds] " + path + " missing: no skirts"); return; }
        SkirtFile F = JsonUtility.FromJson<SkirtFile>(File.ReadAllText(path));
        var arms = new List<Transform>();
        var pts = new List<float>(); var ps = new List<int>(); var pc = new List<int>(); var rr = new List<float>();
        var rk = new List<float>(); var rs = new List<int>(); var rc = new List<int>();
        int missing = 0;
        foreach (SkirtArm a in F.arms)
        {
            Transform tr = FindInScene(a.id);                        // GateRoot/<id> or NearRoot_busRelative/<id>
            if (tr == null || a.pts == null || a.r == null || a.pts.Length != 3 * a.r.Length) { missing++; continue; }
            arms.Add(tr);
            ps.Add(pts.Count / 3); pc.Add(a.r.Length);
            pts.AddRange(a.pts); rr.AddRange(a.r);
            Pack(a.reveal, rk, rs, rc);
        }
        drv.skirtArms = arms.ToArray();
        drv.skirtPts = pts.ToArray(); drv.skirtPtStart = ps.ToArray(); drv.skirtPtCount = pc.ToArray(); drv.skirtR = rr.ToArray();
        drv.skirtRevKeys = rk.ToArray(); drv.skirtRevStart = rs.ToArray(); drv.skirtRevCount = rc.ToArray();
        drv.skirtLevel = F.level;
        drv.skirtK = new Vector4(0f, F.width, F.climb, F.strength);
        Debug.Log(string.Format("[GateClouds] volume deck {0}: {1} arms for the skirts{2}", volMat.name, arms.Count,
                                missing > 0 ? " (" + missing + " not found in the scene)" : ""));
    }

    static void Pack(float[] keys, List<float> all, List<int> start, List<int> count)
    {
        start.Add(all.Count);
        int n = keys == null ? 0 : keys.Length / 2;
        count.Add(n);
        if (n > 0) all.AddRange(keys);
    }

    [MenuItem("蓝白/Gate Clouds/Apply At U7b")]
    public static void ApplyMenu() { Apply(155.1f); }

    static float Smooth(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }

    static float Key(float[] k, int s, int n, float t, float d)
    {
        if (n <= 0) return d;
        if (t <= k[s]) return k[s + 1];
        int last = s + 2 * (n - 1);
        if (t >= k[last]) return k[last + 1];
        for (int i = s; i < last; i += 2)
            if (t >= k[i] && t <= k[i + 2]) return Mathf.Lerp(k[i + 1], k[i + 3], Smooth((t - k[i]) / Mathf.Max(k[i + 2] - k[i], 1e-4f)));
        return k[last + 1];
    }

    // edit-mode preview: the same evaluation as LanbaiGateClouds.Apply, plus every card's property block
    public static void Apply(float t)
    {
        Transform dg = FindInScene("GateClouds_Driver");
        var d = dg != null ? dg.GetComponent<LanbaiGateClouds>() : null;
        if (d == null) { Debug.LogWarning("[GateClouds] not built"); return; }
        var mpb = new MaterialPropertyBlock();
        int missing = 0;                     // v1.5 (总导演 A4): the gate's Build ran after ours -> skip and say so, never throw
        for (int i = 0; i < d.cardRenderers.Length; i++)
        {
            if (d.cardRenderers[i] == null) { missing++; continue; }
            mpb.Clear();
            mpb.SetFloat("_Mirror", d.cardMirror[i]); mpb.SetFloat("_Gain", d.cardGain[i]); mpb.SetFloat("_Alpha", d.cardOpacity[i]);
            d.cardRenderers[i].SetPropertyBlock(mpb);
            d.cardRenderers[i].enabled = true;
        }
        for (int i = 0; i < d.towers.Length; i++)
        {
            float sag = Key(d.sagKeys, d.sagStart[i], d.sagCount[i], t, 1f);
            float sink = Key(d.sinkKeys, d.sinkStart[i], d.sinkCount[i], t, 0f);
            float a = Key(d.alphaKeys, d.alphaStart[i], d.alphaCount[i], t, 1f);
            Transform tr = d.towers[i];
            if (tr == null || d.towerRenderers[i] == null) { missing++; continue; }
            Vector3 s = tr.localScale; s.y = d.towerBaseScaleY[i] * sag; tr.localScale = s;
            Vector3 p = tr.localPosition; p.y = d.towerBaseY[i] + sink; tr.localPosition = p;
            d.towerRenderers[i].enabled = a > 0.001f;
            mpb.Clear();
            mpb.SetFloat("_Mirror", d.towerMirror[i]); mpb.SetFloat("_Gain", d.towerGain[i]); mpb.SetFloat("_Alpha", d.towerOpacity[i] * a);
            d.towerRenderers[i].SetPropertyBlock(mpb);
        }
        if (missing > 0)
            Debug.LogWarning("[GateClouds] " + missing + " card / tower renderers are missing (the gate was rebuilt after the clouds): please re-run 蓝白/Gate Clouds/Build");
    }
}
