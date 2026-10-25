// =====================================================================================================
//  LanbaiAct07Builder.cs   蓝白 · 第 7a 幕的搭建脚本（编辑器）
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (Roslyn). !!!
//
//  菜单 蓝白/Build/Act07a（可以重复运行：先删上一次搭的 R_Act07；Act07_Driver 物体和组件**留着重用**——手接的 worldSun、
//  两个接管开关、分发层里的引用都不丢（终审 7a 一 #3）。然后照 README §0：1 Generate → 等编译 → 2 Wire Scene → 3 Report）：
//    1. 读 Assets/Lanbai/Act07_Sea/Act07_Layout.json 的 'unity'（光柱的数也在这里，平铺）/ 'particles' / 'ridge' 块（唯一的数据源）；
//    2. 先跑 蓝白/Sea/Create Materials（海的材质），再在 Act07_Sea/Materials/ 建本幕的材质（光柱、粒子 ×5、石壁、暖点、穹顶）；
//    3. 在 Act07_Sea/Meshes/ 生成网格（.asset）：光柱 16 条 + 最后一道、海雪 1 200、播下的光 200、船体荧光池 900、
//       气泡 120 + 40、海脊石壁、暖点；网格的 bounds 按 shader 实际画到的地方给（粒子在顶点着色器里移动）；
//    4. 场景：R_Act07 { R_Sea（跟水走：海面 Sea_Disc、光柱、石壁、暖点），R_Act07Bus（在原点：粒子、最后一道光柱、穹顶、
//       座椅上的聚光）}；水下的太阳不另建灯：驱动接管世界主光（D-24 唯一带阴影的那一盏 = RenderSettings.sun），焦散 cookie
//       是 Act07_Sea/Materials/Act07_CausticsCookie.asset（CRT），水下由驱动挂到主光上；
//    5. Act07_Driver（场景里有 Director 就挂在它下面）：LanbaiAct07Driver（U#），填好所有数组。U# 程序资产 / 编译 /
//       CopyProxyToUdon 用 GateClouds 的同一套（LanbaiGateCloudsBuilder.AddUdonSharp / SetupUdonSharp）。
//  不碰：车厢、PPv2、云的海（第 6 幕）、LB_Journey。RenderSettings 由驱动在第 7 幕窗口里写（README_集成 §3 的接管开关）。
// =====================================================================================================
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class LanbaiAct07Builder
{
    const string Root = "Assets/Lanbai/Act07_Sea";
    const string SeaRoot = "Assets/Lanbai/Sea";

    // ---- the JSON (JsonUtility: flat arrays and arrays of records only) ----
    [Serializable] public class U
    {
        public float window_t0, window_t1, entry, eye_under, exit, F3i, F4, F5, D0;
        public float sink_T0, sink_v0, fwd_T0, fwd_v0;
        public float[] sink_seg_t0, sink_seg_dur, sink_seg_dv, fwd_seg_t0, fwd_seg_dur, fwd_seg_dv;
        public float[] water_depth, water_density, water_up, water_mid, water_down;
        public float[] caustics_colour; public float caustics_depth0, caustics_depth1;
        public float[] sun_colour; public float sun_E0, sun_depth1, sun_elevation, sun_azimuth;
        public float[] amb_sky, amb_equator, amb_ground;
        public float[] win_gain_t, win_gain_v, core_desktop, core_vr; public float erosion_t0, erosion_t1, erosion_max;
        public float[] shaft_centre, shaft_axis, shaft_half_width, shaft_length, shaft_seed, shaft_alpha, shaft_colour;
        public float shaft_depth_full, shaft_depth_gone, gather_t0, gather_t1, shafts_gone_t; public float[] gather_point_bus;
        public float last_t0, last_in, last_sweep, last_out, last_half_width, last_length, last_alpha;
        public float[] last_from, last_to, last_target, last_target_to; public float last_top;
        public float beam_angle, beam_range, beam_gather_E, beam_last_E; public float[] beam_gather_pos, beam_gather_aim;
        public float snow_sphere, snow_box;
        public float F8, F8b, F8c, c7_mirror_y, c7_mirror_z, c7_caus_t0, c7_caus_ramp, c7_rose_range;
        public float[] c7_wave_t, c7_wave_v, c7_win_t, c7_win_v, c7_fog_t, c7_fog_density, c7_fog_up, c7_fog_mid, c7_fog_down;
        public float[] c7_caus_colour, c7_rose_pos, c7_rose_colour, c7_rose_t, c7_rose_v, c7_tri_sky, c7_tri_equator, c7_tri_ground_t, c7_tri_ground;
        public float[] wl_entry, wl_exit;
        public float[] warm_position, warm_colour; public float warm_flux, warm_radius, warm_fade, warm_halo_flux, warm_halo_radius;
        public float[] ridge_base, ridge_rim; public float ridge_reach, ridge_near, ridge_wrap, ridge_face, ridge_edge;
    }
    [Serializable] public class Snow { public int count; public float[] colour, positions, radius, alpha, seed; }
    [Serializable] public class Seeds { public int count; public float[] colour, positions, radius, birth_t, steady, seed; }
    [Serializable] public class Trails { public int count; public float[] colour, positions, radius, phase, life, seed; public float T0, rate, pool; }
    [Serializable] public class Bubbles { public string name; public int count, queue; public float[] positions, radius, delay, duration, colour, seed; public float alpha, T0, loop, rise; }
    [Serializable] public class Particles { public Snow snow; public Seeds seeds; public Trails trails; public Bubbles[] bubbles; public float snow_sink; public float[] near_fade; public float min_px; }
    [Serializable] public class Grid { public float z0, dz, y0, dy; public int nz, ny; }
    [Serializable] public class Ridge { public Grid grid; public float[] x; }
    [Serializable] public class Layout { public U unity; public Particles particles; public Ridge ridge; }

    static Vector3 V3(float[] a, int o = 0) { return new Vector3(a[o], a[o + 1], a[o + 2]); }
    static Vector4 V4(float[] a, int o = 0) { return new Vector4(a[o], a[o + 1], a[o + 2], 0f); }
    static Color C(float[] a) { return new Color(a[0], a[1], a[2], 1f); }
    static int Mask(params string[] names)
    {
        int m = 0;
        foreach (string n in names) { int l = LayerMask.NameToLayer(n); if (l >= 0) m |= 1 << l; else Debug.LogWarning("[Act07] layer '" + n + "' missing"); }
        return m != 0 ? m : ~0;
    }
    // Light.color and RenderSettings.ambient* / fogColor are sRGB (gamma) values in a linear project: Unity linearises them
    static Color Gamma(float[] lin) { return new Color(lin[0], lin[1], lin[2], 1f).gamma; }

    static void Folder(string parent, string name) { if (!AssetDatabase.IsValidFolder(parent + "/" + name)) AssetDatabase.CreateFolder(parent, name); }

    static Mesh SaveMesh(Mesh m, string path)
    {
        var old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (old != null) AssetDatabase.DeleteAsset(path);
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    static Material Mat(string name, string shader)
    {
        var sh = Shader.Find(shader);
        if (sh == null) throw new Exception("[Act07] shader " + shader + " not found (did it compile?)");
        string path = Root + "/Materials/" + name + ".mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
        m.shader = sh;
        return m;
    }

    static readonly Vector2[] Corners = { new Vector2(-1, -1), new Vector2(1, -1), new Vector2(1, 1), new Vector2(-1, 1) };

    // one quad per point: 4 vertices at the SAME position, UV0 = corner (the particles / specks contract)
    static Mesh Points(string name, int n, Func<int, Vector3> pos, Func<int, Vector4> uv1, Func<int, Vector4> uv2, Func<int, Color> col, Bounds b)
    {
        var v = new Vector3[4 * n]; var u0 = new List<Vector2>(4 * n); var u1 = new List<Vector4>(4 * n); var u2 = new List<Vector4>(4 * n);
        var c = new Color[4 * n]; var idx = new int[6 * n];
        for (int i = 0; i < n; i++)
        {
            Vector3 p = pos(i); Vector4 a = uv1(i), d = uv2(i); Color k = col(i);
            for (int j = 0; j < 4; j++) { v[4 * i + j] = p; u0.Add(Corners[j]); u1.Add(a); u2.Add(d); c[4 * i + j] = k; }
            idx[6 * i] = 4 * i; idx[6 * i + 1] = 4 * i + 2; idx[6 * i + 2] = 4 * i + 1;
            idx[6 * i + 3] = 4 * i; idx[6 * i + 4] = 4 * i + 3; idx[6 * i + 5] = 4 * i + 2;
        }
        var m = new Mesh { name = name, indexFormat = (4 * n > 65000) ? IndexFormat.UInt32 : IndexFormat.UInt16 };
        m.vertices = v; m.SetUVs(0, u0); m.SetUVs(1, u1); m.SetUVs(2, u2); m.colors = c; m.triangles = idx;
        m.bounds = b;                                            // the vertex shader moves them: bounds = where they draw
        return m;
    }

    // the shaft contract (Lanbai/SeaShaft): POSITION = centre, NORMAL = axis, UV0 corner (x -1/+1 across, y 0 top .. 1 bottom),
    // UV1 = (half width, length, seed, alpha)
    static Mesh Shafts(string name, int n, Func<int, Vector3> centre, Func<int, Vector3> axis, Func<int, Vector4> uv1, Bounds b)
    {
        var v = new Vector3[4 * n]; var nr = new Vector3[4 * n]; var u0 = new List<Vector2>(4 * n); var u1 = new List<Vector4>(4 * n);
        var idx = new int[6 * n];
        Vector2[] cs = { new Vector2(-1, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(-1, 1) };
        for (int i = 0; i < n; i++)
        {
            for (int j = 0; j < 4; j++) { v[4 * i + j] = centre(i); nr[4 * i + j] = axis(i); u0.Add(cs[j]); u1.Add(uv1(i)); }
            idx[6 * i] = 4 * i; idx[6 * i + 1] = 4 * i + 2; idx[6 * i + 2] = 4 * i + 1;
            idx[6 * i + 3] = 4 * i; idx[6 * i + 4] = 4 * i + 3; idx[6 * i + 5] = 4 * i + 2;
        }
        var m = new Mesh { name = name };
        m.vertices = v; m.normals = nr; m.SetUVs(0, u0); m.SetUVs(1, u1); m.triangles = idx;
        m.bounds = b;
        return m;
    }

    static Mesh RidgeMesh(Ridge r)
    {
        Grid g = r.grid;
        var v = new Vector3[g.nz * g.ny];
        for (int j = 0; j < g.ny; j++)
            for (int i = 0; i < g.nz; i++)
                v[j * g.nz + i] = new Vector3(r.x[j * g.nz + i], g.y0 + g.dy * j, g.z0 + g.dz * i);
        var idx = new List<int>();
        for (int j = 0; j < g.ny - 1; j++)
            for (int i = 0; i < g.nz - 1; i++)
            {
                int a = j * g.nz + i, b = a + 1, c = a + g.nz, d = c + 1;
                // the face looks toward -x (the bus): Unity's front face normal is Cross(b - a, c - a)
                if (Vector3.Cross(v[b] - v[a], v[c] - v[a]).x < 0f) { idx.Add(a); idx.Add(b); idx.Add(c); idx.Add(b); idx.Add(d); idx.Add(c); }
                else { idx.Add(a); idx.Add(c); idx.Add(b); idx.Add(b); idx.Add(c); idx.Add(d); }
            }
        var m = new Mesh { name = "Act07_Ridge", indexFormat = v.Length > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
        m.vertices = v; m.triangles = idx.ToArray();
        m.RecalculateNormals(); m.RecalculateBounds();
        return m;
    }

    static GameObject Child(Transform parent, string name)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        return go;
    }

    static Renderer Draw(Transform parent, string name, Mesh mesh, Material mat)
    {
        var go = Child(parent, name);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        var r = go.AddComponent<MeshRenderer>();
        r.sharedMaterial = mat;
        r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
        r.lightProbeUsage = LightProbeUsage.Off; r.reflectionProbeUsage = ReflectionProbeUsage.Off;
        return r;
    }

    static void ParticleMat(Material m, string kind, bool additive, int queue)
    {
        m.SetFloat("_KIND", kind == "SNOW" ? 0 : kind == "SEED" ? 1 : kind == "TRAIL" ? 2 : 3);
        foreach (string k in new[] { "_KIND_SNOW", "_KIND_SEED", "_KIND_TRAIL", "_KIND_BUBBLE" }) m.DisableKeyword(k);
        m.EnableKeyword("_KIND_" + kind);
        m.SetFloat("_Additive", additive ? 1 : 0);
        m.SetFloat("_SrcBlend", (float)BlendMode.One);
        m.SetFloat("_DstBlend", (float)(additive ? BlendMode.One : BlendMode.OneMinusSrcAlpha));
        m.renderQueue = queue;
    }

    // D-41：菜单先等 U# 程序资产初始化完再搭；直接调 Build() 时没初始化完就不动场景（Common/Editor/LanbaiUdonPrograms）
    [MenuItem("蓝白/Build/Act07a")]
    public static void BuildMenu()
    {
        Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("蓝白/Build/Act07a", new[] { typeof(LanbaiAct07Driver) }, Build);
    }

    public static void Build()
    {
        Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Build/Act07a", typeof(LanbaiAct07Driver));
        string path = Root + "/Act07_Layout.json";
        if (!File.Exists(path)) throw new Exception("[Act07] " + path + " not found (copy Act07_Sea/ to Assets/Lanbai/Act07_Sea/)");
        Layout J = JsonUtility.FromJson<Layout>(File.ReadAllText(path));
        U u = J.unity;
        Folder(Root, "Materials"); Folder(Root, "Meshes");
        Lanbai.Sea.Editor.LanbaiSeaMaterials.CreateAll();             // the sea's own materials (SeaMaterials.json)

        // ---- clean
        Transform old = LanbaiGateCloudsBuilder.FindInScenePublic("R_Act07");
        if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
        Transform oldD = LanbaiGateCloudsBuilder.FindInScenePublic("Act07_Driver");   // kept and reused (see the header)

        var root = new GameObject("R_Act07").transform;
        var rSea = Child(root, "R_Sea").transform;
        var rBus = Child(root, "R_Act07Bus").transform;
        Bounds near = new Bounds(new Vector3(0f, 1.2f, 0f), new Vector3(120f, 120f, 120f));
        Bounds far = new Bounds(Vector3.zero, new Vector3(4000f, 4000f, 4000f));

        // ---- the plane (under R_Sea, water y 0)
        var disc = AssetDatabase.LoadAssetAtPath<GameObject>(SeaRoot + "/Models/Sea_Disc.fbx");
        var above = AssetDatabase.LoadAssetAtPath<Material>(SeaRoot + "/Materials/M_06_Sea.mat");
        var below = AssetDatabase.LoadAssetAtPath<Material>(SeaRoot + "/Materials/M_07a_SeaSurface.mat");
        Renderer sea = null;
        if (disc != null)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(disc, rSea);
            go.name = "Sea_Plane";
            sea = go.GetComponentInChildren<Renderer>();
            // built with BELOW: the dispatcher's prewarm frames then draw the _SEA_BELOW variant once (first used at 363.615);
            // the driver's first Tick swaps it to ABOVE until the eye is under
            if (sea != null) { sea.sharedMaterial = below; sea.shadowCastingMode = ShadowCastingMode.Off; sea.receiveShadows = false; }
        }
        else Debug.LogError("[Act07] " + SeaRoot + "/Models/Sea_Disc.fbx not found (copy Sea/ first)");
        // 7c: the mirror below = a second disc at the water y the eye crosses at the exit, centred under the bus (README §9)
        var mirrorMat = AssetDatabase.LoadAssetAtPath<Material>(SeaRoot + "/Materials/M_07c_SeaMirror.mat");
        Renderer mirror = null;
        if (disc != null)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(disc, rSea);
            go.name = "Sea_Mirror";
            go.transform.localPosition = new Vector3(0f, u.c7_mirror_y, u.c7_mirror_z);
            mirror = go.GetComponentInChildren<Renderer>();
            if (mirror != null) { mirror.sharedMaterial = mirrorMat; mirror.shadowCastingMode = ShadowCastingMode.Off; mirror.receiveShadows = false; }
            if (mirrorMat == null) Debug.LogError("[Act07] M_07c_SeaMirror.mat missing (蓝白/Sea/Create Materials)");
        }

        // ---- shafts (R_Sea object space = WATER frame); bounds cover the shafts and the gather point all the way down
        var mShaft = Mat("M_07_Shafts", "Lanbai/SeaShaft");
        mShaft.SetVector("_Color", V4(u.shaft_colour));
        mShaft.SetTexture("_Streaks", AssetDatabase.LoadAssetAtPath<Texture2D>(SeaRoot + "/Textures/ShaftStreaks_256.png"));
        int ns = u.shaft_half_width.Length;
        var shaftMesh = SaveMesh(Shafts("Act07_Shafts", ns, i => V3(u.shaft_centre, 3 * i), i => V3(u.shaft_axis, 3 * i),
                                        i => new Vector4(u.shaft_half_width[i], u.shaft_length[i], u.shaft_seed[i], u.shaft_alpha[i]),
                                        new Bounds(new Vector3(0f, -150f, 0f), new Vector3(200f, 400f, 200f))), Root + "/Meshes/Act07_Shafts.asset");
        var shafts = Draw(rSea, "Act07_Shafts", shaftMesh, mShaft);
        // the quad's top sits last_top above the transform (the moving centre), so the seats ~13 m down sit at uv.y ~0.45
        var lastMesh = SaveMesh(Shafts("Act07_ShaftLast", 1, i => Vector3.down * (0.5f * u.last_length - u.last_top), i => Vector3.down,
                                      i => new Vector4(u.last_half_width, u.last_length, 0.37f, u.last_alpha), new Bounds(Vector3.zero, Vector3.one * 80f)),
                                Root + "/Meshes/Act07_ShaftLast.asset");
        var lastShaft = Draw(rBus, "Act07_ShaftLast", lastMesh, mShaft);

        // ---- particles (objects at the world origin: the shader's bus origin)
        Particles P = J.particles;
        var mSnow = Mat("M_07_Snow", "Lanbai/SeaParticles"); ParticleMat(mSnow, "SNOW", false, 2990);
        mSnow.SetFloat("_Sink", P.snow_sink); mSnow.SetFloat("_Sphere", u.snow_sphere); mSnow.SetFloat("_Box", u.snow_box);
        mSnow.SetVector("_NearFade", new Vector4(P.near_fade[0], P.near_fade[1], 0, 0)); mSnow.SetFloat("_MinPx", P.min_px);
        Snow S = P.snow;
        var snow = Draw(rBus, "Act07_Snow", SaveMesh(Points("Act07_Snow", S.count, i => V3(S.positions, 3 * i),
            i => new Vector4(S.seed[i], S.radius[i], 0, 0), i => Vector4.zero, i => new Color(S.colour[0], S.colour[1], S.colour[2], S.alpha[i]), near),
            Root + "/Meshes/Act07_Snow.asset"), mSnow);

        var mSeed = Mat("M_07_Seeds", "Lanbai/SeaParticles"); ParticleMat(mSeed, "SEED", true, 2990);
        mSeed.SetFloat("_FlashGain", 7f); mSeed.SetFloat("_FlashTime", 0.2f); mSeed.SetFloat("_MinPx", P.min_px);
        Seeds D = P.seeds;
        var seeds = Draw(rBus, "Act07_Seeds", SaveMesh(Points("Act07_Seeds", D.count, i => V3(D.positions, 3 * i),
            i => new Vector4(D.seed[i], D.radius[i], 0, 0), i => new Vector4(D.birth_t[i], D.steady[i], 0, 0),
            i => new Color(D.colour[0], D.colour[1], D.colour[2], 1f), far), Root + "/Meshes/Act07_Seeds.asset"), mSeed);

        var mTrail = Mat("M_07_Trails", "Lanbai/SeaParticles"); ParticleMat(mTrail, "TRAIL", true, 2990);
        Trails T = P.trails;
        mTrail.SetFloat("_T0", T.T0); mTrail.SetFloat("_PoolRate", T.rate); mTrail.SetFloat("_PoolCount", T.pool); mTrail.SetFloat("_MinPx", P.min_px);
        var trails = Draw(rBus, "Act07_Trails", SaveMesh(Points("Act07_Trails", T.count, i => V3(T.positions, 3 * i),
            i => new Vector4(T.seed[i], T.radius[i], 0, 0), i => new Vector4(T.phase[i], T.life[i], 0, 0),
            i => new Color(T.colour[0], T.colour[1], T.colour[2], 1f), near), Root + "/Meshes/Act07_Trails.asset"), mTrail);

        Renderer bGlass = null, bSeats = null;
        foreach (Bubbles B in P.bubbles)
        {
            var mb = Mat("M_07_Bubbles" + B.name, "Lanbai/SeaParticles"); ParticleMat(mb, "BUBBLE", false, B.queue);
            mb.SetFloat("_T0", B.T0); mb.SetFloat("_Loop", B.loop); mb.SetFloat("_Rise", B.rise); mb.SetFloat("_MinPx", P.min_px);
            Bubbles b = B;
            var r = Draw(rBus, "Act07_Bubbles" + B.name, SaveMesh(Points("Act07_Bubbles" + b.name, b.count, i => V3(b.positions, 3 * i),
                i => new Vector4(b.seed[i], b.radius[i], 0, 0), i => new Vector4(b.loop > 0f ? b.delay[i] / Mathf.Max(b.loop, 1e-3f) : b.delay[i], b.duration[i], 0, 0),
                i => new Color(b.colour[0], b.colour[1], b.colour[2], b.alpha), near), Root + "/Meshes/Act07_Bubbles" + b.name + ".asset"), mb);
            if (B.name == "Glass") bGlass = r; else bSeats = r;
        }

        // ---- the ridge wall (WATER frame)
        var mRidge = Mat("M_07_Ridge", "Lanbai/SeaRidge");
        mRidge.SetVector("_Base", V4(u.ridge_base)); mRidge.SetVector("_Rim", V4(u.ridge_rim)); mRidge.SetFloat("_RimReach", u.ridge_reach);
        mRidge.SetFloat("_RimNear", u.ridge_near); mRidge.SetFloat("_RimWrap", u.ridge_wrap); mRidge.SetFloat("_RimFace", u.ridge_face); mRidge.SetFloat("_RimEdge", u.ridge_edge);
        var ridge = Draw(rSea, "Act07_Ridge", SaveMesh(RidgeMesh(J.ridge), Root + "/Meshes/Act07_Ridge.asset"), mRidge);

        // ---- the warm point (WATER frame; the palace's own lamp replaces it)
        var mWarm = Mat("M_07_WarmPoint", "Lanbai/SeaSpecks");
        mWarm.SetFloat("_CeilingMode", 0f); mWarm.SetFloat("_Flicker", 0.05f); mWarm.SetFloat("_MinFWHM", 1.5f);   // D-06
        // two points at the same place: the lamp, and its soft halo (~1.6 deg, <= 2 deg) so it can be found (终审 7a 二)
        var warm = Draw(rSea, "Act07_WarmPoint", SaveMesh(Points("Act07_WarmPoint", 2, i => V3(u.warm_position),
            i => i == 0 ? new Vector4(u.warm_flux, u.warm_radius, 0, 0) : new Vector4(u.warm_halo_flux, u.warm_halo_radius, 0, 0),
            i => new Vector4(0.3f, 0.6f, 0, 0),
            i => new Color(u.warm_colour[0], u.warm_colour[1], u.warm_colour[2], 0.5f), new Bounds(V3(u.warm_position), Vector3.one * 4f)),
            Root + "/Meshes/Act07_WarmPoint.asset"), mWarm);

        // ---- the underwater dome (follows the eye in its vertex shader; only its bounds matter)
        Renderer dome = null;
        var domeFbx = AssetDatabase.LoadAssetAtPath<GameObject>(SeaRoot + "/Models/Sea_Dome.fbx");
        if (domeFbx != null)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(domeFbx, rBus);
            go.name = "Sea_Dome";
            dome = go.GetComponentInChildren<Renderer>();
            if (dome != null) { dome.sharedMaterial = Mat("M_07_Dome", "Lanbai/SeaDome"); dome.shadowCastingMode = ShadowCastingMode.Off; }
        }

        // ---- the sun through the water = the world's main light, driven (D-24): its rotation and the caustic cookie
        float el = u.sun_elevation * Mathf.Deg2Rad, az = u.sun_azimuth * Mathf.Deg2Rad;
        Vector3 toSun = new Vector3(Mathf.Cos(el) * Mathf.Sin(az), Mathf.Sin(el), Mathf.Cos(el) * Mathf.Cos(az));
        Quaternion sunRot = Quaternion.LookRotation(-toSun, Vector3.up);
        var cookieMat = Mat("M_07_CausticsCookie", "Lanbai/SeaCausticsCookie");
        string crtPath = Root + "/Materials/Act07_CausticsCookie.asset";
        var crt = AssetDatabase.LoadAssetAtPath<CustomRenderTexture>(crtPath);
        if (crt == null)
        {
            crt = new CustomRenderTexture(256, 256, RenderTextureFormat.ARGBHalf);   // a cookie reads ALPHA: the format must have it
            AssetDatabase.CreateAsset(crt, crtPath);
        }
        crt.material = cookieMat; crt.updateMode = CustomRenderTextureUpdateMode.Realtime; crt.updatePeriod = 0f;
        crt.initializationMode = CustomRenderTextureUpdateMode.OnLoad; crt.wrapMode = TextureWrapMode.Repeat;
        EditorUtility.SetDirty(crt);

        // ---- 7c: the rose point lights under the bus (bible §6·7c 光), Not Important (SH: free), no shadows
        var rose = new Light[u.c7_rose_pos.Length / 3];
        for (int i = 0; i < rose.Length; i++)
        {
            var rg = Child(rBus, "Act07_Rose" + i);
            rg.transform.localPosition = V3(u.c7_rose_pos, 3 * i);
            var l = rg.AddComponent<Light>();
            l.type = LightType.Point; l.shadows = LightShadows.None; l.renderMode = LightRenderMode.ForceVertex;
            l.color = Gamma(u.c7_rose_colour); l.range = u.c7_rose_range; l.intensity = 0f;
            l.cullingMask = Mask("Bus", "Player", "PlayerLocal");
            l.enabled = false;
            rose[i] = l;
        }

        // ---- the beam (F4p gather, F3e1 last shaft): a spot in the bus frame that lands on the seats and your hands
        var beamGo = Child(rBus, "Act07_Beam");
        var beam = beamGo.AddComponent<Light>();
        beam.type = LightType.Spot; beam.shadows = LightShadows.None; beam.renderMode = LightRenderMode.ForcePixel;
        beam.color = Gamma(u.sun_colour); beam.intensity = 0f; beam.spotAngle = u.beam_angle; beam.range = u.beam_range;
        beam.cullingMask = Mask("Bus", "Player", "PlayerLocal");  // the seats and your hands (bible §1.6 culling)
        beam.enabled = false;

        // ---- the driver
        // reuse the old driver object and component: the dispatcher's references, the hand-wired worldSun and the two
        // takeover switches survive a rebuild (the switches default to false and are never touched here)
        GameObject dGo = oldD != null ? oldD.gameObject : new GameObject("Act07_Driver");
        Transform director = LanbaiGateCloudsBuilder.FindInScenePublic("Director");
        if (oldD == null && director != null) dGo.transform.SetParent(director, false);
        var d = dGo.GetComponent<LanbaiAct07Driver>();
        if (d == null) d = (LanbaiAct07Driver)LanbaiGateCloudsBuilder.AddUdonSharp(dGo, typeof(LanbaiAct07Driver));
        if (d.worldSun == null) d.worldSun = RenderSettings.sun;   // D-24: the one shadowed main light is RenderSettings.sun
        if (d.worldSun == null) Debug.LogWarning("[Act07] RenderSettings.sun is empty: wire Act07_Driver.worldSun to the world's main light by hand");
        d.roots = new[] { rSea.gameObject, rBus.gameObject };
        d.rSea = rSea; d.seaRenderer = sea; d.seaAbove = above; d.seaBelow = below;
        d.shafts = shafts; d.lastShaft = lastShaft; d.lastShaftTf = lastShaft.transform; d.ridge = ridge; d.warmPoint = warm;
        d.snow = snow; d.seeds = seeds; d.trails = trails; d.bubblesGlass = bGlass; d.bubblesSeats = bSeats; d.dome = dome;
        d.beam = beam; d.sunCookie = crt; d.sunCookieSize = 1.5f; d.sunRotation = sunRot;
        d.causticsTex = AssetDatabase.LoadAssetAtPath<Texture2D>(SeaRoot + "/Textures/Caustics_8x8_2048.png");
        d.windowStart = u.window_t0; d.windowEnd = u.window_t1;
        d.tEntry = u.entry; d.tEyeUnder = u.eye_under; d.tExit = u.exit; d.tF3i = u.F3i; d.tF4 = u.F4; d.tF5 = u.F5;
        d.D0 = u.D0;
        d.sinkT0 = u.sink_T0; d.sinkV0 = u.sink_v0; d.sinkSegT0 = u.sink_seg_t0; d.sinkSegDur = u.sink_seg_dur; d.sinkSegDv = u.sink_seg_dv;
        d.fwdT0 = u.fwd_T0; d.fwdV0 = u.fwd_v0; d.fwdSegT0 = u.fwd_seg_t0; d.fwdSegDur = u.fwd_seg_dur; d.fwdSegDv = u.fwd_seg_dv;
        int nw = u.water_depth.Length;
        d.wDepth = u.water_depth; d.wDensity = u.water_density;
        d.wUp = new Vector4[nw]; d.wMid = new Vector4[nw]; d.wDown = new Vector4[nw];
        d.wFogGamma = new Color[nw];
        for (int i = 0; i < nw; i++)
        {
            d.wUp[i] = V4(u.water_up, 3 * i) + new Vector4(0, 0, 0, 1); d.wMid[i] = V4(u.water_mid, 3 * i) + new Vector4(0, 0, 0, 1);
            d.wDown[i] = V4(u.water_down, 3 * i) + new Vector4(0, 0, 0, 1);
            d.wFogGamma[i] = new Color(u.water_mid[3 * i], u.water_mid[3 * i + 1], u.water_mid[3 * i + 2], 1f).gamma;
        }
        d.causticsColor = V4(u.caustics_colour); d.causticsDepth0 = u.caustics_depth0; d.causticsDepth1 = u.caustics_depth1;
        d.sunColor = Gamma(u.sun_colour); d.sunE0 = u.sun_E0; d.sunDepth1 = u.sun_depth1;
        d.ambSky = Gamma(u.amb_sky); d.ambEquator = Gamma(u.amb_equator); d.ambGround = Gamma(u.amb_ground);
        d.winGainT = u.win_gain_t; d.winGainV = u.win_gain_v;
        d.baseWindowGain = below != null ? below.GetFloat("_WindowGain") : 18f;
        d.coreDesktop = new Vector4(u.core_desktop[0], u.core_desktop[1], u.core_desktop[2], u.core_desktop[3]);
        d.coreVR = new Vector4(u.core_vr[0], u.core_vr[1], u.core_vr[2], u.core_vr[3]);
        d.erosionT0 = u.erosion_t0; d.erosionT1 = u.erosion_t1; d.erosionMax = u.erosion_max;
        d.shaftDepthFull = u.shaft_depth_full; d.shaftDepthGone = u.shaft_depth_gone;
        d.gatherT0 = u.gather_t0; d.gatherT1 = u.gather_t1; d.shaftsGoneT = u.shafts_gone_t; d.gatherPointBus = V3(u.gather_point_bus);
        d.lastT0 = u.last_t0; d.lastIn = u.last_in; d.lastSweep = u.last_sweep; d.lastOut = u.last_out;
        d.lastFromBus = V3(u.last_from); d.lastToBus = V3(u.last_to); d.lastTargetBus = V3(u.last_target); d.lastTargetToBus = V3(u.last_target_to);
        d.beamGatherPos = V3(u.beam_gather_pos); d.beamGatherAim = V3(u.beam_gather_aim); d.beamGatherE = u.beam_gather_E; d.beamLastE = u.beam_last_E;
        d.warmFadeIn = u.warm_fade;
        // act 7c
        d.tF8 = u.F8; d.tF8b = u.F8b; d.tF8c = u.F8c;
        d.mirrorRenderer = mirror; d.mirrorWaterY = u.c7_mirror_y;
        // the dark mirror's reflection cube: the stand-in until Control's Refl_S7c (README §0 #12); a hand-wired one survives
        if (d.reflCube7c == null) d.reflCube7c = AssetDatabase.LoadAssetAtPath<Cubemap>(SeaRoot + "/Textures/Cube_Refl7c_Standin_512.exr");
        d.baseMirrorWindowGain = mirrorMat != null ? mirrorMat.GetFloat("_WindowGain") : 0.25f;
        d.c7WaveT = u.c7_wave_t; d.c7WaveV = u.c7_wave_v; d.c7WinT = u.c7_win_t; d.c7WinV = u.c7_win_v;
        int n7 = u.c7_fog_t.Length;
        d.c7FogT = u.c7_fog_t; d.c7FogDens = u.c7_fog_density;
        d.c7FogUp = new Vector4[n7]; d.c7FogMid = new Vector4[n7]; d.c7FogDown = new Vector4[n7]; d.c7FogGamma = new Color[n7];
        for (int i = 0; i < n7; i++)
        {
            d.c7FogUp[i] = V4(u.c7_fog_up, 3 * i) + new Vector4(0, 0, 0, 1); d.c7FogMid[i] = V4(u.c7_fog_mid, 3 * i) + new Vector4(0, 0, 0, 1);
            d.c7FogDown[i] = V4(u.c7_fog_down, 3 * i) + new Vector4(0, 0, 0, 1);
            d.c7FogGamma[i] = new Color(u.c7_fog_mid[3 * i], u.c7_fog_mid[3 * i + 1], u.c7_fog_mid[3 * i + 2], 1f).gamma;
        }
        d.c7CausT0 = u.c7_caus_t0; d.c7CausRamp = u.c7_caus_ramp; d.c7CausColor = V4(u.c7_caus_colour);
        d.roseLights = rose; d.c7RoseT = u.c7_rose_t; d.c7RoseV = u.c7_rose_v;
        d.c7TriSky = Gamma(u.c7_tri_sky); d.c7TriEquator = Gamma(u.c7_tri_equator); d.c7TriGroundT = u.c7_tri_ground_t;
        d.c7TriGround = new Color[u.c7_tri_ground_t.Length];
        for (int i = 0; i < d.c7TriGround.Length; i++) d.c7TriGround[i] = Gamma(new[] { u.c7_tri_ground[3 * i], u.c7_tri_ground[3 * i + 1], u.c7_tri_ground[3 * i + 2] });
        d.wlEntry0 = u.wl_entry[0]; d.wlEntry1 = u.wl_entry[1]; d.wlExit0 = u.wl_exit[0]; d.wlExit1 = u.wl_exit[1];
        // d.waterlines: copies of the glass meshes with Lanbai/SeaWaterline, wired locally (README §0); kept across rebuilds
        LanbaiGateCloudsBuilder.SetupUdonSharp(d);
        EditorUtility.SetDirty(d);
        foreach (Material m in new[] { mShaft, mSnow, mSeed, mTrail, mRidge, mWarm, cookieMat }) EditorUtility.SetDirty(m);
        AssetDatabase.SaveAssets();
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(root.gameObject.scene);
        Debug.Log(string.Format("[Act07] built: {0} shafts, {1} snow, {2} seeds, {3} trail quads, ridge {4}x{5}; driver window {6}..{7}",
                                ns, S.count, D.count, T.count, J.ridge.grid.nz, J.ridge.grid.ny, u.window_t0, u.window_t1));
    }
}
#endif
