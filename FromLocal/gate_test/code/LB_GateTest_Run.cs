// 蓝白 · 触手之门 · 导入测试：定时间、核对、截图、量性能（见 LB_GateTest.cs 的头注释）
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Unity.Profiling;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.PostProcessing;
using UnityEngine.SceneManagement;
using Debug = UnityEngine.Debug;
using Object = UnityEngine.Object;

namespace Lanbai.Tests
{
    public static partial class LB_GateTest
    {
        // README_GateLayout §2.1：伤口线光源的两个端点（套件坐标，Tear_Root.TransformPoint）
        static readonly Vector3 TEAR_FOOT_OS = new Vector3(0.5f, 0.0f, -30.0f);
        static readonly Vector3 TEAR_TOP_OS = new Vector3(-59.14f, 920.36f, -30.0f);

        // ─────────────────────────────────────────────────────────────
        //  把时间定在 t
        // ─────────────────────────────────────────────────────────────
        public static string Apply(string arg)
        {
            _json = null;
            float t = ParseT(arg, 155.10f);
            var J = Json();
            var gr = Root(R_GATE);
            if (gr == null) return "ERROR：场景里没有 GateRoot（先 Build）";
            var near = Root(R_NEAR);

            Vector3 gate = GatePos(t);
            gr.transform.position = gate;
            gr.transform.rotation = Quaternion.identity;
            gr.transform.localScale = Vector3.one;
            float hb = HBus(t), H = TearH(t), kS = H / 1000f, open = TearOpen(t), rip = Rip(t);

            var MJ = G(J, "multitude");
            float g0 = KeyAt(L(G(G(G(MJ, "reveal_groups"), "group0"), "keys")), t, "value");
            float g1 = KeyAt(L(G(G(G(MJ, "reveal_groups"), "group1"), "keys")), t, "value");

            var mpb = new MaterialPropertyBlock();
            int nOn = 0, nOff = 0;
            var partial = new List<string>();
            foreach (var it in Instances())
            {
                string id = S(G(it, "id"));
                bool bus = S(G(it, "frame")) == "bus";
                bool surge = S(G(it, "layer")) == "surge";
                var parent = bus ? (near != null ? near.transform : null) : gr.transform;
                var tr = parent != null ? parent.Find(id) : null;
                if (tr == null) continue;
                Vector3 p; Quaternion q;
                Pose(it, t, out p, out q);
                tr.localPosition = p;
                tr.localRotation = q;

                float rv; int group = 0;
                var rj = G(it, "reveal");
                if (surge) { group = (int)F(G(rj, "group")); rv = group == 0 ? g0 : g1; }
                else rv = Has(rj, "keys") ? KeyAt(L(G(rj, "keys")), t, "value") : 1f;
                bool on = rv > 0f;
                if (on) nOn++; else nOff++;
                if (on && rv < 0.999f) partial.Add(id + " " + Fs(rv, "0.00"));

                Texture occ = null;
                if (surge) occ = AssetDatabase.LoadAssetAtPath<Texture2D>(GATE + "/Textures/Occlusion/T_Gate_" + S(G(it, "variant")) + "_Occlusion.png");
                float phase = Has(it, "phase") ? F(G(it, "phase")) : F(G(G(it, "material"), "_Phase"));
                foreach (var r in tr.GetComponentsInChildren<Renderer>(true))
                {
                    r.enabled = on;
                    r.GetPropertyBlock(mpb);
                    mpb.SetFloat("_Phase", phase);
                    if (Has(it, "_FogCapI")) mpb.SetFloat("_FogCapI", F(G(it, "_FogCapI")));
                    mpb.SetFloat("_RevealGroup", group);
                    mpb.SetFloat("_Reveal", surge ? 1f : rv);
                    if (occ != null) mpb.SetTexture("_OcclusionMap", occ);
                    if (surge)
                    {
                        float pr = PoseR(S(G(it, "variant")));        // 群臂：12 个姿态共用 3 个档材质，每个实例的根半径 / 长度走 MPB
                        if (pr > 0f) mpb.SetVector("_VariantDims", new Vector4(pr, F(G(it, "length_m"), 1000f) / Mathf.Max(1e-3f, F(G(it, "scale"), 1f)), 0f, 0f));
                    }
                    r.SetPropertyBlock(mpb);
                }
            }

            // 远潮：材质级 _Reveal（JSON tide.reveal），0 时关 renderer
            var tideTr = gr.transform.Find("TideRoot");
            float tideRv = KeyAt(L(G(G(G(J, "tide"), "reveal"), "keys")), t, "value");
            if (tideTr != null)
                foreach (var r in tideTr.GetComponentsInChildren<Renderer>(true))
                {
                    r.enabled = tideRv > 0f;
                    r.GetPropertyBlock(mpb); mpb.SetFloat("_Reveal", tideRv); r.SetPropertyBlock(mpb);
                }

            // 裂口
            var TJ = G(J, "tear");
            var FJ = G(TJ, "fades");
            var OJ = G(TJ, "gate_overrides");
            var tear = gr.transform.Find("Tear_Root");
            Cam seat = GetCam("U7");
            Vector3 eye = seat.eye;
            string tearInfo = "";
            if (tear != null)
            {
                tear.localScale = Vector3.one * kS;
                float kAdd = KeyAt(L(G(FJ, "cloudglow_additive_intensity_keys")), t, "x");
                float kFold = KeyAt(L(G(FJ, "skyfolds_intensity_keys")), t, "x") * F(G(OJ, "skyfolds"), 1f);
                float kLane = KeyAt(L(G(FJ, "lane_intensity_keys")), t, "x");
                float kPool = KeyAt(L(G(FJ, "pool_fade_keys")), t, "x");
                float D = Mathf.Abs(gate.z - eye.z);
                float kHalo = Mathf.Clamp01((Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(250f, 1200f, D)) - 0.25f) / 0.75f) * F(G(OJ, "halo_intensity"), 1f);
                Vector3 foot = tear.TransformPoint(TEAR_FOOT_OS);
                float Df = Vector3.Distance(eye, foot);
                SetPB(tear, "Tear_CloudGlow_Additive", mpb, kAdd > 0f, "_Intensity", 0.25f * kAdd, "_FootGlow", 2.2f * kPool);
                SetPB(tear, "Tear_CloudGlow", mpb, true, "_Intensity", 1f * kPool, "_FootGlow", 0.98f * kPool);
                SetPB(tear, "Tear_SkyFolds", mpb, kFold > 0f, "_Intensity", kFold, null, 0f);
                SetPB(tear, "Tear_Halo", mpb, kHalo >= 0.05f, "_Intensity", kHalo, null, 0f);
                SetPB(tear, "Tear_LightLane", mpb, true, "_Intensity", kLane, null, 0f);
                var lane = FindDeep(tear, "Tear_LightLane");
                float laneX = Mathf.Clamp(0.10f * Df / (kS * 420f), 0.15f, 1f);
                if (lane != null) lane.localScale = new Vector3(laneX, 1f, 1f);
                foreach (var s in L(G(G(J, "shafts"), "items")))
                {
                    var st = tear.Find(S(G(s, "id")));
                    if (st != null) SetPB(st, st.name, mpb, true, "_Intensity", F(G(OJ, "shaft"), 0.35f) * F(G(s, "gain"), 1f), null, 0f);
                }
                tearInfo = "裂口 H " + Fs(H, "0.0") + " m（缩放 " + Fs(kS, "0.000") + "）、张开 " + Fs(open, "0.000") + "、撕裂 " + Fs(rip, "0.000") +
                           "；叠加光池 ×" + Fs(kAdd, "0.00") + "、布褶 ×" + Fs(kFold, "0.00") + "、光晕 ×" + Fs(kHalo, "0.00") + "（D " + Fs(D, "0") + " m）、光路 ×" + Fs(kLane, "0.00") +
                           "（x 缩放 " + Fs(laneX, "0.000") + "）、光池 ×" + Fs(kPool, "0.00");
                // 全局量（README_GateLayout §2.1、README_Tear §5）
                Vector3 top = tear.TransformPoint(TEAR_TOP_OS);
                Shader.SetGlobalVector("_Udon_TearFoot", new Vector4(foot.x, foot.y, foot.z, 0.5f * (0.18f + 0.12f * open) * H));
                Shader.SetGlobalVector("_Udon_TearTop", new Vector4(top.x, top.y, top.z, 1f));
            }
            Vector3 moon = V3(G(G(G(J, "lights"), "moon"), "direction_to_light_unity"));
            Vector3 tearPos = gate + new Vector3(0f, -150f + 0.4f * H, 0f);
            Shader.SetGlobalVector("_Udon_CloudTop", new Vector4(-hb, 0f, 0f, 1f));
            Shader.SetGlobalVector("_Udon_TearPos", new Vector4(tearPos.x, tearPos.y, tearPos.z, 1f));
            Shader.SetGlobalVector("_Udon_TearH", new Vector4(H, 0f, 0f, 1f));
            Shader.SetGlobalVector("_Udon_MoonDir", new Vector4(moon.x, moon.y, moon.z, 1f));
            Shader.SetGlobalFloat("_Udon_GateTime", t);
            Shader.SetGlobalVector("_Udon_GateOrigin", new Vector4(gate.x, gate.y, gate.z, 1f));
            Shader.SetGlobalVector("_Udon_MultReveal", new Vector4(g0, g1, 0f, 0f));
            float disc = MoonDisc(t);
            Shader.SetGlobalVector("_Udon_MoonDisc", new Vector4(disc, 0.6f, 0f, 1f));
            Shader.SetGlobalFloat("_Udon_TearOpen", open);
            Shader.SetGlobalFloat("_Udon_RipProgress", rip);
            Shader.SetGlobalFloat("_Udon_TearHide", 0f);

            // 裂口平行光（只照车厢）：从 _Udon_TearPos 指向车
            var lights = Root(R_LIGHTS);
            if (lights != null)
            {
                var lt = lights.transform.Find("Tear_CabinOnly");
                if (lt != null) lt.rotation = Quaternion.LookRotation((Vector3.zero - tearPos).normalized, Vector3.up);
            }
            // 参考相机放在主座位 U7 机位（Game 视图里看到的就是这一张）
            var camGo = Root(R_CAM);
            if (camGo != null)
            {
                camGo.transform.position = seat.eye;
                camGo.transform.rotation = Quaternion.LookRotation(seat.fwd, Vector3.up);
                camGo.GetComponent<Camera>().fieldOfView = VFov(seat.hfov, 16f / 9f);
            }
            SceneView.RepaintAll();
            return "t = " + Fs(t, "0.00") + "：GateRoot " + Vs(gate) + "，云顶 y " + Fs(-hb, "0.00") + "；臂 " + nOn + " 条显现、" + nOff + " 条关着" +
                   (partial.Count > 0 ? "（半显现：" + string.Join("，", partial) + "）" : "") + "；群臂 group0 " + Fs(g0, "0.00") + " / group1 " + Fs(g1, "0.00") +
                   "；远潮 _Reveal " + Fs(tideRv, "0.00") + "；月盘增益 " + Fs(disc, "0.00") + "；" + tearInfo;
        }

        static readonly Dictionary<string, float> _poseR = new Dictionary<string, float>();
        static float PoseR(string variant)
        {
            float r;
            if (_poseR.TryGetValue(variant, out r)) return r;
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(GATE + "/GateMultitude_v2.fbx");
            var t = fbx != null ? FindDeep(fbx.transform, variant) : null;
            var m = t != null ? Lod0Mesh(t) : null;
            string how;
            r = m != null ? RootRadius(m, out how) : -1f;
            _poseR[variant] = r;
            return r;
        }

        static void SetPB(Transform root, string name, MaterialPropertyBlock mpb, bool on, string k1, float v1, string k2, float v2)
        {
            var t = root.name == name ? root : FindDeep(root, name);
            if (t == null) return;
            var r = t.GetComponent<Renderer>();
            if (r == null) return;
            r.enabled = on;
            r.GetPropertyBlock(mpb);
            if (k1 != null) mpb.SetFloat(k1, v1);
            if (k2 != null) mpb.SetFloat(k2, v2);
            r.SetPropertyBlock(mpb);
        }

        // ─────────────────────────────────────────────────────────────
        //  截图相机（照 ReferenceCamera 抄设置，挂一个新的 PostProcessLayer 并 Init）
        // ─────────────────────────────────────────────────────────────
        static GameObject MakeCam(Cam c, int w, int h)
        {
            var tmplGo = Root(R_CAM);
            var tmpl = tmplGo != null ? tmplGo.GetComponent<Camera>() : null;
            var go = new GameObject("GateTestShotCam") { hideFlags = HideFlags.HideAndDontSave };
            var cam = go.AddComponent<Camera>();
            cam.enabled = false;
            if (tmpl != null)
            {
                cam.clearFlags = tmpl.clearFlags;
                cam.backgroundColor = tmpl.backgroundColor;
                cam.nearClipPlane = tmpl.nearClipPlane;
                cam.farClipPlane = tmpl.farClipPlane;
                cam.allowHDR = tmpl.allowHDR;
                cam.allowMSAA = tmpl.allowMSAA;
                cam.cullingMask = tmpl.cullingMask;
                var src = tmplGo.GetComponent<PostProcessLayer>();
                if (src != null)
                {
                    var ppl = go.AddComponent<PostProcessLayer>();
                    ppl.volumeLayer = src.volumeLayer;
                    ppl.volumeTrigger = go.transform;
                    ppl.stopNaNPropagation = src.stopNaNPropagation;
                    ppl.antialiasingMode = src.antialiasingMode;
                    ppl.finalBlitToCameraTarget = src.finalBlitToCameraTarget;
                    var f = typeof(PostProcessLayer).GetField("m_Resources", BindingFlags.NonPublic | BindingFlags.Instance);
                    var res = f != null ? f.GetValue(src) as PostProcessResources : null;
                    if (res != null) ppl.Init(res);
                }
            }
            else { cam.nearClipPlane = 0.05f; cam.farClipPlane = 45000f; cam.allowHDR = true; }
            go.transform.position = c.eye;
            go.transform.rotation = Quaternion.LookRotation(c.fwd, Vector3.up);
            cam.aspect = (float)w / h;
            cam.fieldOfView = VFov(c.hfov, cam.aspect);
            return go;
        }

        public static string Shoot(string arg)
        {
            var a = Args(arg);
            string cn; if (!a.TryGetValue("cam", out cn)) cn = "U7";
            _json = null;
            Cam c = GetCam(cn);
            float t = ArgF(a, "t", c.t);
            int w = (int)ArgF(a, "w", 1920), h = (int)ArgF(a, "h", 1080), ss = (int)ArgF(a, "ss", 2);
            string file; if (!a.TryGetValue("file", out file)) file = "LanbaiReports/GateTest/" + cn + ".png";
            if (!Path.IsPathRooted(file)) file = Path.GetFullPath(Path.Combine(Application.dataPath, "..", file));
            Directory.CreateDirectory(Path.GetDirectoryName(file));
            string ap = Apply(Fs(t, "0.###"));
            GameObject go = null; RenderTexture big = null, small = null; Texture2D tex = null;
            var prev = RenderTexture.active;
            try
            {
                go = MakeCam(c, w, h);
                var cam = go.GetComponent<Camera>();
                // 相机渲进 HDR（ARGBHalf）目标：渲进 8 位目标的话，场景的 HDR 值在进 PPv2 之前就被夹到 1，裂口的白会被压成一块平的灰
                big = new RenderTexture(w * ss, h * ss, 24, RenderTextureFormat.DefaultHDR, RenderTextureReadWrite.Linear) { antiAliasing = 1, filterMode = FilterMode.Bilinear };
                big.Create();
                cam.targetTexture = big;
                for (int k = 0; k < 3; k++) cam.Render();
                // PPv2 的输出（已色调映射、线性）→ 8 位 sRGB；ss = 2 时双线性正好是 2×2 平均
                small = new RenderTexture(w, h, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { filterMode = FilterMode.Bilinear };
                small.Create();
                Graphics.Blit(big, small);
                RenderTexture src = small;
                RenderTexture.active = src;
                tex = new Texture2D(w, h, TextureFormat.RGB24, false, false);
                tex.ReadPixels(new Rect(0, 0, w, h), 0, 0, false);
                tex.Apply(false);
                RenderTexture.active = prev;
                File.WriteAllBytes(file, tex.EncodeToPNG());
                var px = tex.GetPixels32();
                double sum = 0; int dark = 0;
                foreach (var p in px)
                {
                    double y = 0.2126 * p.r + 0.7152 * p.g + 0.0722 * p.b;
                    sum += y; if (y < 12) dark++;
                }
                return cn + " 截图 " + w + "×" + h + "（HDR 渲染，超采样 " + ss + "×，竖直视角 " + Fs(cam.fieldOfView, "0.00") + "°）→ " + file +
                       "；平均亮度（sRGB 0–255，Rec.709 权重）" + Fs((float)(sum / px.Length), "0.0") + "，< 12 的像素 " + Fs(100f * dark / px.Length, "0.0") + "%\n" + ap;
            }
            finally
            {
                RenderTexture.active = prev;
                if (go != null) { var cc = go.GetComponent<Camera>(); if (cc != null) cc.targetTexture = null; Object.DestroyImmediate(go); }
                if (big != null) { big.Release(); Object.DestroyImmediate(big); }
                if (small != null) { small.Release(); Object.DestroyImmediate(small); }
                if (tex != null) Object.DestroyImmediate(tex);
            }
        }

        // ─────────────────────────────────────────────────────────────
        //  性能：帧时间（编辑器里，和 LB_PerfCheck 同一种测法）、draw call、三角面
        // ─────────────────────────────────────────────────────────────
        public static string Perf(string arg)
        {
            var a = Args(arg);
            string cn; if (!a.TryGetValue("cam", out cn)) cn = "U7";
            _json = null;
            Cam c = GetCam(cn);
            float t = ArgF(a, "t", c.t);
            Apply(Fs(t, "0.###"));
            var sb = new StringBuilder();
            sb.AppendLine("机位 " + cn + "，t = " + Fs(t, "0.00") + "；显卡 " + SystemInfo.graphicsDeviceName + "（" + SystemInfo.graphicsDeviceType + "），CPU " + SystemInfo.processorType);
            sb.AppendLine("Unity 编辑器、编辑模式里用一台相机直接渲染到 HDR 的 RenderTexture（ARGBHalf，含 PPv2），渲染前后各读 1 个像素做 GPU 同步；" +
                          "QualitySettings：LOD Bias " + Fs(QualitySettings.lodBias, "0.00") + "，像素光 " + QualitySettings.pixelLightCount +
                          "，阴影距离 " + Fs(QualitySettings.shadowDistance, "0") + "，" + QualitySettings.shadowCascades + " 级，MSAA " + QualitySettings.antiAliasing);
            var probe = new Texture2D(1, 1, TextureFormat.RGBA32, false);
            try
            {
                // 1) 一次渲染的 draw call / 三角面（三种读法）
                using (var rDraw = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Draw Calls Count"))
                using (var rBatch = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Batches Count"))
                using (var rSet = ProfilerRecorder.StartNew(ProfilerCategory.Render, "SetPass Calls Count"))
                using (var rTri = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Triangles Count"))
                using (var rVert = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Vertices Count"))
                using (var rShadow = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Shadow Casters Count"))
                {
                    var go = MakeCam(c, 1920, 1080);
                    var cam = go.GetComponent<Camera>();
                    var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.DefaultHDR, RenderTextureReadWrite.Linear) { antiAliasing = 1 };
                    rt.Create();
                    cam.targetTexture = rt;
                    cam.Render(); Sync(rt, probe);                      // 先热一下
                    long d0 = rDraw.CurrentValue, b0 = rBatch.CurrentValue, s0 = rSet.CurrentValue, t0 = rTri.CurrentValue, v0 = rVert.CurrentValue, c0 = rShadow.CurrentValue;
                    int ud0 = UnityStats.drawCalls, ub0 = UnityStats.batches, us0 = UnityStats.setPassCalls, ut0 = UnityStats.triangles, uv0 = UnityStats.vertices;
                    cam.Render(); Sync(rt, probe);
                    long d1 = rDraw.CurrentValue, b1 = rBatch.CurrentValue, s1 = rSet.CurrentValue, t1 = rTri.CurrentValue, v1 = rVert.CurrentValue, c1 = rShadow.CurrentValue;
                    int ud1 = UnityStats.drawCalls, ub1 = UnityStats.batches, us1 = UnityStats.setPassCalls, ut1 = UnityStats.triangles, uv1 = UnityStats.vertices;
                    sb.AppendLine("一次渲染（1920×1080）：");
                    sb.AppendLine("  ProfilerRecorder（这一帧里渲染前后的差）：draw call " + (d1 - d0) + "、batches " + (b1 - b0) + "、SetPass " + (s1 - s0) +
                                  "、三角面 " + (t1 - t0).ToString("N0") + "、顶点 " + (v1 - v0).ToString("N0") + "、投影物体 " + (c1 - c0) +
                                  "（渲染后的累计值：draw " + d1 + "、三角 " + t1.ToString("N0") + "；recorder 有效 " + rDraw.Valid + "）");
                    sb.AppendLine("  UnityStats（渲染后 / 渲染前）：draw call " + ud1 + " / " + ud0 + "、batches " + ub1 + " / " + ub0 + "、SetPass " + us1 + " / " + us0 +
                                  "、三角面 " + ut1.ToString("N0") + " / " + ut0.ToString("N0") + "、顶点 " + uv1.ToString("N0") + " / " + uv0.ToString("N0"));
                    sb.Append(Analytic(cam));
                    cam.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(go);
                }

                // 2) 帧时间
                sb.AppendLine("帧时间（预热 4 次、取 24 次的中位数；合计 = CPU 提交 + 等 GPU 画完，不重叠地算，偏保守）：");
                sb.AppendLine("  " + TimeView(c, 1920, 1080, 1, c.hfov, probe, "电脑 1920×1080"));
                sb.AppendLine("  " + TimeView(c, 1832, 1920, 2, -100f, probe, "VR 两只眼 1832×1920×2（竖直视角 100°，同一方向渲两次）"));
            }
            finally { Object.DestroyImmediate(probe); }
            string text = sb.ToString();
            WriteReport("GateTest_Perf_" + cn + ".txt", text);
            return text;
        }

        // ---- Play 里读 Game 视图那一帧的统计（编辑模式里手动 Render 不进 UnityStats / ProfilerRecorder）
        static ProfilerRecorder[] _rec;
        static readonly string[] REC = { "Draw Calls Count", "Batches Count", "SetPass Calls Count", "Triangles Count", "Vertices Count", "Shadow Casters Count", "Visible Skinned Meshes Count" };
        public static string StatsBegin(string arg)
        {
            StatsEnd();
            var a = Args(arg);
            string cn; if (!a.TryGetValue("cam", out cn)) cn = "U7";
            var c = GetCam(cn);
            var camGo = Root(R_CAM);
            if (camGo != null)
            {
                var cam = camGo.GetComponent<Camera>();
                camGo.transform.position = c.eye;
                camGo.transform.rotation = Quaternion.LookRotation(c.fwd, Vector3.up);
                cam.fieldOfView = VFov(c.hfov, (float)Screen.width / Mathf.Max(1, Screen.height));
            }
            _rec = REC.Select(n => ProfilerRecorder.StartNew(ProfilerCategory.Render, n, 30)).ToArray();
            return "开始记：" + string.Join("、", REC) + "；Game 视图 " + Screen.width + "×" + Screen.height + "，Play " + EditorApplication.isPlaying;
        }
        public static string StatsRead(string arg)
        {
            var sb = new StringBuilder();
            sb.AppendLine("Game 视图 " + Screen.width + "×" + Screen.height + "（Play " + EditorApplication.isPlaying + "），相机竖直视角 " +
                          (Root(R_CAM) != null ? Fs(Root(R_CAM).GetComponent<Camera>().fieldOfView, "0.00") : "?") + "°（按这个宽高比把水平视角对到 90°）");
            sb.AppendLine("UnityStats（Game 视图上一帧，和 Stats 窗口同一个来源）：draw call " + UnityStats.drawCalls + "、batches " + UnityStats.batches + "、SetPass " + UnityStats.setPassCalls +
                          "、三角面 " + UnityStats.triangles.ToString("N0") + "、顶点 " + UnityStats.vertices.ToString("N0") + "、投影物体 " + UnityStats.shadowCasters +
                          "、动态合批 " + UnityStats.dynamicBatchedDrawCalls + " / 实例化合批 " + UnityStats.instancedBatchedDrawCalls + "、渲染纹理切换 " + UnityStats.renderTextureChanges);
            if (_rec != null)
            {
                sb.Append("ProfilerRecorder（每帧总数：上一帧 / 最近 30 帧的中位数）：");
                for (int k = 0; k < _rec.Length; k++)
                {
                    var r = _rec[k];
                    var vals = new List<long>();
                    for (int i = 0; i < r.Count; i++) vals.Add(r.GetSample(i).Value);
                    vals.Sort();
                    sb.Append(REC[k] + " " + (r.Valid ? r.LastValue.ToString("N0") + " / " + (vals.Count > 0 ? vals[vals.Count / 2].ToString("N0") : "-") : "无效") + (k < _rec.Length - 1 ? "，" : ""));
                }
                sb.AppendLine();
            }
            StatsEnd();
            return sb.ToString();
        }
        static void StatsEnd()
        {
            if (_rec != null) foreach (var r in _rec) r.Dispose();
            _rec = null;
        }

        static void Sync(RenderTexture rt, Texture2D probe)
        {
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            probe.ReadPixels(new Rect(0, 0, 1, 1), 0, 0, false);
            probe.Apply(false);
            RenderTexture.active = prev;
        }

        static string TimeView(Cam c, int w, int h, int eyes, float fov, Texture2D probe, string label)
        {
            var go = MakeCam(c, w, h);
            var cam = go.GetComponent<Camera>();
            if (fov < 0f) cam.fieldOfView = -fov;
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.DefaultHDR, RenderTextureReadWrite.Linear) { antiAliasing = 1 };
            rt.Create();
            cam.targetTexture = rt;
            var cpu = new List<double>(); var tot = new List<double>();
            for (int f = 0; f < 28; f++)
            {
                Sync(rt, probe);
                var sw = Stopwatch.StartNew();
                for (int e = 0; e < eyes; e++) cam.Render();
                double c1 = sw.Elapsed.TotalMilliseconds;
                Sync(rt, probe);
                double t1 = sw.Elapsed.TotalMilliseconds;
                if (f >= 4) { cpu.Add(c1); tot.Add(t1); }
            }
            cam.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(go);
            cpu.Sort(); tot.Sort();
            double mc = cpu[cpu.Count / 2], mt = tot[tot.Count / 2];
            return label + "：合计 " + mt.ToString("0.0", IC) + " ms（约 " + (1000.0 / Math.Max(0.1, mt)).ToString("0", IC) + " fps），其中 CPU " + mc.ToString("0.0", IC) +
                   " ms；最快 / 最慢 " + tot[0].ToString("0.0", IC) + " / " + tot[tot.Count - 1].ToString("0.0", IC) + " ms";
        }

        /// <summary>按视锥和 LODGroup 的规则数这台相机看得见什么（不经过渲染器的统计，用来核对上面两种读法）。</summary>
        static string Analytic(Camera cam)
        {
            var planes = GeometryUtility.CalculateFrustumPlanes(cam);
            var lodOf = new Dictionary<Renderer, int>();
            var culledByLod = new HashSet<Renderer>();
            float tanH = Mathf.Tan(0.5f * cam.fieldOfView * Mathf.Deg2Rad);
            foreach (var lg in Object.FindObjectsOfType<LODGroup>())
            {
                var lods = lg.GetLODs();
                var tr = lg.transform;
                float scale = Mathf.Max(Mathf.Abs(tr.lossyScale.x), Mathf.Max(Mathf.Abs(tr.lossyScale.y), Mathf.Abs(tr.lossyScale.z)));
                float size = lg.size * scale;
                float dist = Vector3.Distance(cam.transform.position, tr.TransformPoint(lg.localReferencePoint));
                float rel = size / (2f * Mathf.Max(dist, 1e-3f) * tanH) * QualitySettings.lodBias;
                int pick = -1;
                for (int k = 0; k < lods.Length; k++) if (rel >= lods[k].screenRelativeTransitionHeight) { pick = k; break; }
                for (int k = 0; k < lods.Length; k++)
                    foreach (var r in lods[k].renderers)
                    {
                        if (r == null) continue;
                        if (k == pick) lodOf[r] = k; else culledByLod.Add(r);
                    }
            }
            long tris = 0; int vis = 0, sub = 0, shadow = 0;
            var lodCount = new int[3];
            var byGroup = new Dictionary<string, long>();
            foreach (var r in Object.FindObjectsOfType<Renderer>())
            {
                if (!r.enabled || !r.gameObject.activeInHierarchy) continue;
                if (culledByLod.Contains(r) && !lodOf.ContainsKey(r)) continue;
                if ((cam.cullingMask & (1 << r.gameObject.layer)) == 0) continue;
                if (!GeometryUtility.TestPlanesAABB(planes, r.bounds)) continue;
                var mf = r.GetComponent<MeshFilter>();
                if (mf == null || mf.sharedMesh == null) continue;
                vis++;
                int lv; if (lodOf.TryGetValue(r, out lv) && lv < 3) lodCount[lv]++;
                long tr = 0;
                for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) tr += mf.sharedMesh.GetIndexCount(s) / 3;
                int nm = r.sharedMaterials.Length;
                if (nm > mf.sharedMesh.subMeshCount) tr += (nm - mf.sharedMesh.subMeshCount) * (mf.sharedMesh.GetIndexCount(mf.sharedMesh.subMeshCount - 1) / 3);
                tris += tr;
                sub += Mathf.Max(nm, mf.sharedMesh.subMeshCount);
                if (r.shadowCastingMode != ShadowCastingMode.Off) shadow++;
                string grp = r.transform.root.name;
                var tr2 = r.transform;
                while (tr2.parent != null && tr2.parent.parent != null) tr2 = tr2.parent;
                grp = tr2.parent != null ? tr2.parent.name + "/" + (tr2.name.StartsWith("Mult_") ? "Mult_*" : tr2.name) : tr2.name;
                long cur; byGroup.TryGetValue(grp, out cur); byGroup[grp] = cur + tr;
            }
            var sb = new StringBuilder();
            sb.AppendLine("  按视锥 + LODGroup 规则数（每个子网格 / 材质算一次，不算阴影和后处理的 pass）：看得见的 renderer " + vis + " 个（LOD0 " + lodCount[0] + "、LOD1 " + lodCount[1] + "、LOD2 " + lodCount[2] +
                          "），子网格 × 材质 " + sub + "，三角面 " + tris.ToString("N0") + "，其中投影的 " + shadow + " 个");
            foreach (var kv in byGroup.OrderByDescending(x => x.Value).Take(12))
                sb.AppendLine("    " + kv.Key + "：" + kv.Value.ToString("N0") + " 三角");
            return sb.ToString();
        }

        // ─────────────────────────────────────────────────────────────
        //  核对
        // ─────────────────────────────────────────────────────────────
        public static string Verify(string arg)
        {
            _json = null;
            var sb = new StringBuilder();
            // 1) shader
            sb.AppendLine("【shader】");
            foreach (var n in new[] { "Lanbai/TentacleSway", "Lanbai/TentacleTide", "Lanbai/GateAirSky", "Lanbai/Tear", "Lanbai/Debug/TestPatch" })
            {
                var s = Shader.Find(n);
                if (s == null) { sb.AppendLine("  " + n + "：没找到（没导入或编译失败）"); continue; }
                var msgs = ShaderUtil.GetShaderMessages(s);
                sb.AppendLine("  " + n + "：" + (ShaderUtil.ShaderHasError(s) ? "有错误" : "没有错误") + "，消息 " + msgs.Length + " 条，pass 数 " + s.passCount + "，isSupported " + s.isSupported +
                              "（" + AssetDatabase.GetAssetPath(s) + "）");
                foreach (var m in msgs)
                    sb.AppendLine("    [" + m.severity + "] " + m.message + (string.IsNullOrEmpty(m.file) ? "" : "  " + m.file + ":" + m.line) + "  (" + m.platform + ")" +
                                  (string.IsNullOrEmpty(m.messageDetails) ? "" : "\n      " + m.messageDetails.Replace("\n", "\n      ")));
            }
            // 2) FBX
            sb.AppendLine("【FBX】");
            foreach (var p in new[] { GATE + "/GateArms_v4.fbx", GATE + "/GateMultitude_v2.fbx", GATE + "/TentacleTide_v2.fbx", GATE + "/GateLayout_v2.fbx", TEAR + "/FBX/Tear_Kit.fbx", TEAR + "/FBX/Tear_ShaftCard.fbx" })
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(p);
                if (go == null) { sb.AppendLine("  " + p + "：没导入"); continue; }
                var mfs = go.GetComponentsInChildren<MeshFilter>(true);
                long tri = 0; foreach (var mf in mfs) if (mf.sharedMesh != null) for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) tri += mf.sharedMesh.GetIndexCount(s) / 3;
                sb.AppendLine("  " + Path.GetFileName(p) + "：根 " + go.name + "，子物体 " + go.transform.childCount + "，网格 " + mfs.Length + "，三角 " + tri.ToString("N0") +
                              "，LODGroup " + go.GetComponentsInChildren<LODGroup>(true).Length);
                var m0 = mfs.Select(x => x.sharedMesh).FirstOrDefault(x => x != null);
                if (m0 != null)
                {
                    var ch = new List<string>();
                    for (int k = 0; k < 8; k++) { var dim = m0.GetVertexAttributeDimension((VertexAttribute)((int)VertexAttribute.TexCoord0 + k)); if (dim > 0) ch.Add("UV" + k + "×" + dim); }
                    sb.AppendLine("    第一个网格 " + m0.name + "：顶点 " + m0.vertexCount + "，" + string.Join(" ", ch) + (m0.HasVertexAttribute(VertexAttribute.Color) ? " 顶点色" : "") +
                                  (m0.HasVertexAttribute(VertexAttribute.Tangent) ? " 切线" : "") + "，子网格 " + m0.subMeshCount + "，isReadable " + m0.isReadable);
                }
                if (p.EndsWith("Tear_Kit.fbx") || p.EndsWith("TentacleTide_v2.fbx") || p.EndsWith("Tear_ShaftCard.fbx"))
                    foreach (var mf in mfs) sb.AppendLine("    " + PathOf(mf.transform) + "  " + (mf.sharedMesh != null ? mf.sharedMesh.vertexCount + " 顶点 / " + mf.sharedMesh.subMeshCount + " 子网格" : "无网格") +
                                                          "  局部 " + Vs(mf.transform.localPosition) + " " + Vs(mf.transform.localEulerAngles) + " " + Vs(mf.transform.localScale));
            }
            // 3) 布局 FBX（空物体）对照 JSON 的终态位置
            var lay = AssetDatabase.LoadAssetAtPath<GameObject>(GATE + "/GateLayout_v2.fbx");
            if (lay != null)
            {
                var gateT = FindDeep(lay.transform, "GateRoot");
                float worst = 0f, worstR = 0f; string wid = "", widR = ""; int found = 0, miss = 0;
                foreach (var it in Instances())
                {
                    if (S(G(it, "frame")) != "GateRoot") continue;
                    string id = S(G(it, "id"));
                    var e = gateT != null ? FindDeep(gateT, id) : null;
                    if (e == null) { miss++; continue; }
                    found++;
                    Vector3 lp = gateT.InverseTransformPoint(e.position);
                    float d = (lp - V3(G(it, "position"))).magnitude;
                    if (d > worst) { worst = d; wid = id; }
                    Quaternion lq = Quaternion.Inverse(gateT.rotation) * e.rotation;
                    float da = Quaternion.Angle(lq, Q(G(it, "rotation_xyzw")));
                    if (da > worstR) { worstR = da; widR = id; }
                }
                sb.AppendLine("【GateLayout_v2.fbx 对照 JSON position / rotation_xyzw】GateRoot " + (gateT != null ? "在" : "不在") + "，找到 " + found + " 个实例空物体、缺 " + miss +
                              "；位置最大差 " + Fs(worst, "0.000") + " m（" + wid + "），转角最大差 " + Fs(worstR, "0.00") + "°（" + widR + "）");
            }
            // 4) 场景里的东西
            var gr = Root(R_GATE);
            if (gr != null)
            {
                sb.AppendLine("【场景】GateRoot 子物体 " + gr.transform.childCount + "，renderer " + gr.GetComponentsInChildren<Renderer>(true).Length +
                              "，LODGroup " + gr.GetComponentsInChildren<LODGroup>(true).Length);
                var lg = gr.GetComponentInChildren<LODGroup>(true);
                if (lg != null) sb.AppendLine("  LOD 例（" + lg.name + "）：" + string.Join(" / ", lg.GetLODs().Select(l => Fs(l.screenRelativeTransitionHeight, "0.###") + "（" + l.renderers.Length + "）")));
            }
            // 5) 项目设置（只查）
            sb.AppendLine("【项目设置（只查不改）】色彩空间 " + PlayerSettings.colorSpace + "，lightsUseLinearIntensity " + GraphicsSettings.lightsUseLinearIntensity +
                          "，lightsUseColorTemperature " + GraphicsSettings.lightsUseColorTemperature + "，顶点压缩 " + VertexCompression() +
                          "，LOD Bias " + Fs(QualitySettings.lodBias, "0.00") + "，Quality " + QualitySettings.names[QualitySettings.GetQualityLevel()]);
            foreach (GraphicsTier tier in Enum.GetValues(typeof(GraphicsTier)))
            {
                var ts = UnityEditor.Rendering.EditorGraphicsSettings.GetTierSettings(BuildTargetGroup.Standalone, tier);
                sb.AppendLine("  " + tier + "：HDR " + ts.hdr + " " + ts.hdrMode + "，渲染路径 " + ts.renderingPath);
            }
            string text = sb.ToString();
            WriteReport("GateTest_Verify.txt", text);
            return text;
        }

        static string VertexCompression()
        {
            try
            {
                foreach (var line in File.ReadAllLines(Path.Combine(Application.dataPath, "..", "ProjectSettings", "ProjectSettings.asset")))
                    if (line.Trim().StartsWith("VertexChannelCompressionMask:")) return line.Trim().Substring("VertexChannelCompressionMask:".Length).Trim() + "（ProjectSettings.asset 原文）";
            }
            catch (Exception e) { return "读不到（" + e.Message + "）"; }
            return "没找到";
        }

        static string PathOf(Transform t)
        {
            var s = t.name;
            while (t.parent != null) { t = t.parent; s = t.name + "/" + s; }
            return s;
        }
    }
}
