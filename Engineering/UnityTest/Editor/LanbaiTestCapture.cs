// 蓝白 · Unity 测试工具 · 截图、双眼近似、动态序列（闪烁热图）、贴图压缩对照
// 截图方法照门测试（FromLocal/gate_test/code/LB_GateTest_Run.cs，CONTROL §6 #10）：
//   照参考相机抄设置、挂一个新的 PostProcessLayer 并 Init；渲进 HDR（DefaultHDR，ARGBHalf）→ PPv2 → 8 位 sRGB；ss = 2 时双线性正好是 2×2 平均。
// 机位约定和渲染夹具一样（Engineering/render_harness/README）：localEulerAngles = (−pitch, yaw, roll)；hfov 是水平视角。
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.PostProcessing;
using Object = UnityEngine.Object;

namespace Lanbai.Test
{
    public static class Capture
    {
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        public sealed class Cam
        {
            public string id;
            public Vector3 eye;
            public Quaternion rot = Quaternion.identity;
            public float hfov = 90f, vfov = -1f;
            public int w = 1920, h = 1080, ss = 2;
            public float? t;
            public Dictionary<string, object> def;
            public float VFov { get { return vfov > 0f ? vfov : 2f * Mathf.Rad2Deg * Mathf.Atan(Mathf.Tan(0.5f * hfov * Mathf.Deg2Rad) * h / w); } }
        }

        // ─────────────────────────────────────────────────────────────
        public static void All(Ctx ctx)
        {
            foreach (var o in TJson.L(ctx.T("shots"))) Guard(ctx, "shot", o, () => Shoot(ctx, TJson.M(o), "shots", null));
            foreach (var o in TJson.L(ctx.T("stereo"))) Guard(ctx, "stereo", o, () => Stereo(ctx, TJson.M(o)));
            foreach (var o in TJson.L(ctx.T("sequences"))) Guard(ctx, "sequence", o, () => Sequence(ctx, TJson.M(o)));
            foreach (var o in TJson.L(ctx.T("texture_compare"))) Guard(ctx, "texture_compare", o, () => TextureCompare(ctx, TJson.M(o)));
        }

        /// <summary>一项出错只记这一项（记成一个失败的步骤），别的照跑。</summary>
        public static void Guard(Ctx ctx, string what, object item, Action a)
        {
            int mark = ctx.undo.Mark();
            try { a(); }
            catch (Exception e)
            {
                var inner = e is TargetInvocationException && e.InnerException != null ? e.InnerException : e;
                ctx.steps.Add(new Dictionary<string, object>
                {
                    { "phase", what }, { "type", what }, { "desc", TJson.S(TJson.G(item, "id"), "?") }, { "status", "error" },
                    { "error", (inner is StepException ? "" : inner.GetType().Name + ": ") + inner.Message }, { "stack", inner.StackTrace ?? "" }
                });
                Debug.LogWarning(LogCapture.TAG + " " + what + " " + TJson.S(TJson.G(item, "id"), "?") + " 失败：" + inner.Message);
            }
            finally
            {
                foreach (var e in ctx.undo.RollbackTo(mark)) ctx.Warn(e);
            }
        }

        // ── 机位 ────────────────────────────────────────────────────
        public static Cam Resolve(Ctx ctx, Dictionary<string, object> item)
        {
            string cn = TJson.S(TJson.G(item, "cam"));
            object baseDef = null;
            if (cn != null)
            {
                baseDef = TJson.G(ctx.T("cameras"), cn);
                if (baseDef == null) throw new StepException("cameras 里没有 " + cn);
            }
            var d = TJson.Merge(baseDef, item);
            var c = new Cam { def = d, id = TJson.S(TJson.G(d, "id"), cn ?? "shot") };
            float yaw = TJson.F(TJson.G(d, "yaw")), pitch = TJson.F(TJson.G(d, "pitch")), roll = TJson.F(TJson.G(d, "roll"));
            var e = TJson.Fa(TJson.G(d, "euler"));
            c.rot = e != null && e.Length >= 3 ? Quaternion.Euler(e[0], e[1], e[2]) : Quaternion.Euler(-pitch, yaw, roll);
            var eye = TJson.Fa(TJson.G(d, "eye"));
            var look = TJson.Fa(TJson.G(d, "look_at"));
            string lookObj = TJson.S(TJson.G(d, "look_at_object"));
            if (lookObj != null)
            {
                // 看一个物体：取它（和子物体）所有 renderer 包围盒的中心
                var tr = Scenes.Find(lookObj);
                if (tr == null) throw new StepException("机位 " + c.id + " 要看的物体不在：" + lookObj);
                var rs = tr.GetComponentsInChildren<Renderer>(true);
                if (rs.Length == 0) throw new StepException(lookObj + " 下面没有 renderer");
                var b = rs[0].bounds;
                foreach (var r in rs) b.Encapsulate(r.bounds);
                look = new[] { b.center.x, b.center.y, b.center.z };
            }
            var toward = TJson.Fa(TJson.G(d, "toward"));
            if (look != null && TJson.Has(d, "distance"))
            {
                // 近景：从 look_at 往回退 distance。toward 给了就退向那个点（比如主座位的眼），没给就沿 euler / yaw、pitch 的视线往回退
                var target = new Vector3(look[0], look[1], look[2]);
                float dist = TJson.F(TJson.G(d, "distance"));
                if (toward != null)
                {
                    var dir = (new Vector3(toward[0], toward[1], toward[2]) - target).normalized;
                    c.eye = target + dir * dist;
                    c.rot = Quaternion.LookRotation(target - c.eye, Vector3.up);
                }
                else c.eye = target - c.rot * Vector3.forward * dist;
            }
            else
            {
                if (eye == null) throw new StepException("机位 " + c.id + " 没有 eye");
                c.eye = new Vector3(eye[0], eye[1], eye[2]);
                if (look != null) c.rot = Quaternion.LookRotation(new Vector3(look[0], look[1], look[2]) - c.eye, Vector3.up);
            }
            c.hfov = TJson.F(TJson.G(d, "hfov"), 90f);
            c.vfov = TJson.F(TJson.G(d, "vfov"), -1f);
            c.w = TJson.I(TJson.G(d, "w"), 1920);
            c.h = TJson.I(TJson.G(d, "h"), 1080);
            c.ss = Math.Max(1, TJson.I(TJson.G(d, "ss"), 2));
            var crop = TJson.Fa(TJson.G(d, "crop_deg"));
            if (crop != null && crop.Length == 2) { c.hfov = crop[0]; c.vfov = crop[1]; }
            if (TJson.Has(d, "ppd"))
            {
                // 按 VR 像素密度出近景（D-36 #1：Index 约 20 px/°）：画面中心每度 ppd 个像素
                float ppd = TJson.F(TJson.G(d, "ppd"), 20f);
                float vf = c.vfov > 0 ? c.vfov : c.hfov * 9f / 16f;
                c.w = Mathf.RoundToInt(2f * Mathf.Tan(0.5f * c.hfov * Mathf.Deg2Rad) * ppd * Mathf.Rad2Deg);
                c.h = Mathf.RoundToInt(2f * Mathf.Tan(0.5f * vf * Mathf.Deg2Rad) * ppd * Mathf.Rad2Deg);
                c.vfov = vf;
            }
            if (TJson.Has(d, "t")) c.t = TJson.F(TJson.G(d, "t"));
            return c;
        }

        /// <summary>把场景定到时间 t（测试定义的 time 步骤，比如 LB_GateTest.Apply("{t}")）。同一个 t 不重复定。</summary>
        public static void ApplyTime(Ctx ctx, float? t, bool quiet)
        {
            if (!t.HasValue) return;
            if (ctx.lastT.HasValue && Mathf.Abs(ctx.lastT.Value - t.Value) < 1e-5f) return;
            var steps = TJson.L(ctx.T("time"));
            if (steps.Count == 0) throw new StepException("这一项要 t = " + t.Value.ToString("0.###", IC) + "，但测试定义没写 time（怎么把场景定到 t）");
            if (!Steps.RunList(ctx, steps, "time", t, true, false, quiet)) { ctx.lastT = null; throw new StepException("定时间 t = " + t.Value.ToString("0.###", IC) + " 失败"); }
            ctx.lastT = t;
        }

        static void RunBefore(Ctx ctx, Dictionary<string, object> d, string key)
        {
            var l = TJson.L(TJson.G(d, key));
            if (l.Count == 0) return;
            ctx.lastT = null;   // before / after 可能动了场景，下一次照样重新定时间
            if (!Steps.RunList(ctx, l, key, null, true, true)) throw new StepException(key + " 的步骤失败");
        }

        // ── 相机 ────────────────────────────────────────────────────
        static Camera Template(Ctx ctx)
        {
            string tn = TJson.S(ctx.T("camera_template"));
            if (tn != null)
            {
                var tr = Scenes.Find(tn);
                var cam = tr != null ? tr.GetComponent<Camera>() : null;
                if (cam != null) return cam;
                ctx.Warn("参考相机 " + tn + " 没找到，退回场景里第一台带 PostProcessLayer 的相机");
            }
            Camera any = null;
            foreach (var g in Scenes.AllRoots())
                foreach (var c in g.GetComponentsInChildren<Camera>(true))
                {
                    if (c.targetTexture != null) continue;
                    if (c.GetComponent<PostProcessLayer>() != null) return c;
                    if (any == null) any = c;
                }
            return any;
        }

        static double VolumeLayer(Ctx ctx)
        {
            var t = Template(ctx);
            var l = t != null ? t.GetComponent<PostProcessLayer>() : null;
            return l != null ? (double)l.volumeLayer.value : -1;
        }

        public static GameObject MakeCam(Ctx ctx, Cam c, int w, int h, bool withPP, out bool hasPP)
        {
            var tmpl = Template(ctx);
            var go = new GameObject("LanbaiTestShotCam") { hideFlags = HideFlags.HideAndDontSave };
            var cam = go.AddComponent<Camera>();
            cam.enabled = false;
            hasPP = false;
            if (tmpl != null)
            {
                cam.clearFlags = tmpl.clearFlags;
                cam.backgroundColor = tmpl.backgroundColor;
                cam.nearClipPlane = tmpl.nearClipPlane;
                cam.farClipPlane = tmpl.farClipPlane;
                cam.allowHDR = tmpl.allowHDR;
                cam.allowMSAA = tmpl.allowMSAA;
                cam.cullingMask = tmpl.cullingMask;
                cam.depthTextureMode = tmpl.depthTextureMode;
                cam.useOcclusionCulling = tmpl.useOcclusionCulling;
                var src = tmpl.GetComponent<PostProcessLayer>();
                if (src != null && withPP)
                {
                    var ppl = go.AddComponent<PostProcessLayer>();
                    ppl.volumeLayer = src.volumeLayer;
                    ppl.volumeTrigger = go.transform;
                    ppl.stopNaNPropagation = src.stopNaNPropagation;
                    ppl.antialiasingMode = src.antialiasingMode;
                    ppl.finalBlitToCameraTarget = src.finalBlitToCameraTarget;
                    var f = typeof(PostProcessLayer).GetField("m_Resources", BindingFlags.NonPublic | BindingFlags.Instance);
                    var res = f != null ? f.GetValue(src) as PostProcessResources : null;
                    if (res != null) { ppl.Init(res); hasPP = true; }
                    else ctx.Warn("参考相机的 PostProcessLayer 读不到 m_Resources，截图没有 PPv2");
                }
            }
            else
            {
                cam.nearClipPlane = 0.05f; cam.farClipPlane = 45000f; cam.allowHDR = true;
                ctx.Warn("场景里没有相机可抄：截图用默认相机、没有 PPv2");
            }
            go.transform.position = c.eye;
            go.transform.rotation = c.rot;
            cam.aspect = (float)w / h;
            cam.fieldOfView = c.vfov > 0 ? c.vfov : 2f * Mathf.Rad2Deg * Mathf.Atan(Mathf.Tan(0.5f * c.hfov * Mathf.Deg2Rad) / cam.aspect);
            return go;
        }

        /// <summary>一台已经建好的相机渲一帧，读回 8 位 sRGB（行 0 在最下面，和 Texture2D 一样）。</summary>
        public sealed class Renderer2
        {
            public GameObject go; public Camera cam; public RenderTexture big, small; public Texture2D tex; public int w, h, ss; public bool hasPP;
            public Renderer2(Ctx ctx, Cam c, int w, int h, int ss, bool withPP)
            {
                this.w = w; this.h = h; this.ss = ss;
                go = MakeCam(ctx, c, w, h, withPP, out hasPP);
                cam = go.GetComponent<Camera>();
                // 渲进 HDR 目标：渲进 8 位目标的话，HDR 值在进 PPv2 之前就被夹到 1
                big = new RenderTexture(w * ss, h * ss, 24, RenderTextureFormat.DefaultHDR, RenderTextureReadWrite.Linear) { antiAliasing = 1, filterMode = FilterMode.Bilinear };
                big.Create();
                small = new RenderTexture(w, h, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { filterMode = FilterMode.Bilinear };
                small.Create();
                tex = new Texture2D(w, h, TextureFormat.RGB24, false, false);
                cam.targetTexture = big;
            }
            public Color32[] Frame(int renders)
            {
                for (int k = 0; k < Math.Max(1, renders); k++) cam.Render();
                Graphics.Blit(big, small);
                var prev = RenderTexture.active;
                RenderTexture.active = small;
                tex.ReadPixels(new Rect(0, 0, w, h), 0, 0, false);
                tex.Apply(false);
                RenderTexture.active = prev;
                return tex.GetPixels32();
            }
            public void Dispose()
            {
                if (cam != null) cam.targetTexture = null;
                if (go != null) Object.DestroyImmediate(go);
                if (big != null) { big.Release(); Object.DestroyImmediate(big); }
                if (small != null) { small.Release(); Object.DestroyImmediate(small); }
                if (tex != null) Object.DestroyImmediate(tex);
            }
        }

        public static Color32[] RenderOnce(Ctx ctx, Cam c, int w, int h, int ss, bool withPP, out bool hasPP)
        {
            var r = new Renderer2(ctx, c, w, h, ss, withPP);
            try { hasPP = r.hasPP; return r.Frame(3); }
            finally { r.Dispose(); }
        }

        /// <summary>第一次截图前：同一机位开 / 关 PPv2 各渲一张小图，不一样才算 PPv2 真的生效了（批处理下要特别看这一项）。</summary>
        static void PPv2Probe(Ctx ctx, Cam c)
        {
            if (ctx.metrics.ContainsKey("capture.ppv2_effective")) return;
            bool hasPP, dummy;
            var a = RenderOnce(ctx, c, 192, 108, 1, true, out hasPP);
            var b = RenderOnce(ctx, c, 192, 108, 1, false, out dummy);
            double diff = 0;
            for (int i = 0; i < a.Length; i++) diff += Math.Abs(Img.Luma(a[i]) - Img.Luma(b[i]));
            diff /= a.Length;
            ctx.Metric("capture.ppv2_layer", hasPP ? 1 : 0, "参考相机上有 PostProcessLayer、新相机 Init 成功");
            ctx.Metric("capture.ppv2_diff", diff, "开 / 关 PPv2 两张 192×108 小图的平均亮度差（sRGB 0–255）");
            ctx.Metric("capture.ppv2_effective", hasPP && diff > 0.5 ? 1 : 0);
            if (!(hasPP && diff > 0.5)) ctx.Warn("PPv2 好像没生效（开 / 关差 " + diff.ToString("0.00", IC) + "）：截图没有调色。批处理下这样的话，改用菜单跑");
        }

        // ── 截图 ────────────────────────────────────────────────────
        public static Dictionary<string, object> Shoot(Ctx ctx, Dictionary<string, object> item, string folder, string suffix)
        {
            var c = Resolve(ctx, item);
            int mark = ctx.undo.Mark();
            try
            {
                RunBefore(ctx, c.def, "before");
                ApplyTime(ctx, c.t, false);
                PPv2Probe(ctx, c);
                bool hasPP;
                var px = RenderOnce(ctx, c, c.w, c.h, c.ss, true, out hasPP);
                string file = TJson.S(TJson.G(item, "file")) ?? (c.id + (c.t.HasValue ? "_unity_t" + c.t.Value.ToString("0.00", IC) : "") + ".png");
                if (suffix != null) file = Path.GetFileNameWithoutExtension(file) + suffix + ".png";
                string rel = folder + "/" + file;
                Img.SavePng(px, c.w, c.h, ctx.Out(rel));
                ctx.AddFile(rel);
                var st = Img.Stats(px);
                string key = "shot." + c.id + (suffix ?? "");
                ctx.Metric(key + ".apl", st[0], "平均亮度（8 位 sRGB，Rec.709 权重，0–255；和门测试、渲染夹具的 APL 同一个量）");
                ctx.Metric(key + ".dark_pct", st[1]);
                ctx.Metric(key + ".clip_pct", st[2]);
                ctx.Metric(key + ".max_luma", st[3]);
                var rec = new Dictionary<string, object>
                {
                    { "id", c.id + (suffix ?? "") }, { "file", rel }, { "w", (double)c.w }, { "h", (double)c.h }, { "ss", (double)c.ss },
                    { "eye", new List<object> { (double)c.eye.x, (double)c.eye.y, (double)c.eye.z } },
                    { "euler", new List<object> { (double)c.rot.eulerAngles.x, (double)c.rot.eulerAngles.y, (double)c.rot.eulerAngles.z } },
                    { "hfov", (double)c.hfov }, { "vfov_used", (double)c.VFov }, { "ppv2", hasPP }, { "pp_volume_layer", VolumeLayer(ctx) },
                    { "apl", st[0] }, { "dark_pct", st[1] }, { "clip_pct", st[2] }, { "max_luma", st[3] }
                };
                if (c.t.HasValue) rec["t"] = (double)c.t.Value;
                if (TJson.Has(c.def, "label")) rec["label"] = TJson.G(c.def, "label");
                if (TJson.Has(c.def, "ref")) Compare(ctx, c, px, key, rec, folder);
                RunBefore(ctx, c.def, "after");
                ctx.shots.Add(rec);
                return rec;
            }
            finally
            {
                foreach (var e in ctx.undo.RollbackTo(mark)) ctx.Warn(e);
                if (TJson.L(TJson.G(c.def, "before")).Count > 0) ctx.lastT = null;
            }
        }

        // ── 和参考图比 ──────────────────────────────────────────────
        public static string ResolveRef(Ctx ctx, string r)
        {
            if (r == null) return null;
            if (r.StartsWith("repo:", StringComparison.Ordinal))
            {
                string repo = TJson.S(TJson.G(ctx.sync, "repo_path"));
                if (repo == null) return null;
                return Path.Combine(repo, r.Substring(5).Replace('/', Path.DirectorySeparatorChar));
            }
            if (r.StartsWith("assets:", StringComparison.Ordinal)) r = r.Substring(7);
            return Path.Combine(ctx.projectDir, r.Replace('/', Path.DirectorySeparatorChar));
        }

        static void Compare(Ctx ctx, Cam c, Color32[] px, string key, Dictionary<string, object> rec, string folder)
        {
            string rp = ResolveRef(ctx, TJson.S(TJson.G(c.def, "ref")));
            rec["ref"] = TJson.S(TJson.G(c.def, "ref"));
            if (rp == null || !File.Exists(rp)) { rec["ref_status"] = "参考图不在：" + (rp ?? "（repo: 路径要同步记录里的 repo_path）"); ctx.Warn((string)rec["ref_status"]); return; }
            var t = new Texture2D(2, 2, TextureFormat.RGB24, false, false);
            try
            {
                if (!t.LoadImage(File.ReadAllBytes(rp))) { rec["ref_status"] = "参考图读不了：" + rp; return; }
                int rw = t.width, rh = t.height;
                var rpx = t.GetPixels32();
                string half = TJson.S(TJson.G(c.def, "ref_half"));
                if (half == "top" || half == "bottom")
                {
                    // compare_*.png：上半张是这一版的参照，下半张是定稿（Texture2D 的行 0 在最下面）
                    int hh = rh / 2;
                    var cut = new Color32[rw * hh];
                    int y0 = half == "top" ? rh - hh : 0;
                    for (int y = 0; y < hh; y++) Array.Copy(rpx, (y0 + y) * rw, cut, y * rw, rw);
                    rpx = cut; rh = hh;
                }
                var rs = Img.Stats(rpx);
                ctx.Metric(key + ".ref_apl", rs[0]);
                ctx.Metric(key + ".apl_ratio", rs[0] > 0 ? Img.Stats(px)[0] / rs[0] : double.NaN, "Unity 截图的 APL ÷ 参考图的 APL");
                // 亮度结构：两张都缩到 64 宽，比亮度的均方根差（0–255）
                int sw = 64, sh = Math.Max(1, (int)Math.Round(64.0 * c.h / c.w));
                var a = Img.Resample(px, c.w, c.h, sw, sh);
                var b = Img.Resample(rpx, rw, rh, sw, sh);
                double se = 0;
                for (int i = 0; i < a.Length; i++) { double d = Img.Luma(a[i]) - Img.Luma(b[i]); se += d * d; }
                ctx.Metric(key + ".ref_rmse64", Math.Sqrt(se / a.Length), "两张都缩到 64 宽后亮度的均方根差（0–255）；只看大的明暗结构");
                // 对照图：Unity 在上、参考在下，同一宽度
                int W = Math.Min(c.w, 1920), H1 = (int)Math.Round((double)W * c.h / c.w), H2 = (int)Math.Round((double)W * rh / rw);
                var top = Img.Resample(px, c.w, c.h, W, H1);
                var bot = Img.Resample(rpx, rw, rh, W, H2);
                var comp = new Color32[W * (H1 + H2)];
                Array.Copy(bot, 0, comp, 0, bot.Length);           // 行 0 在最下面：先放参考
                Array.Copy(top, 0, comp, bot.Length, top.Length);
                string rel = folder + "/" + c.id + "__vs_ref.png";
                Img.SavePng(comp, W, H1 + H2, ctx.Out(rel));
                ctx.AddFile(rel);
                rec["ref_compare"] = rel;
                rec["ref_apl"] = rs[0];
                rec["ref_status"] = "ok";
            }
            finally { Object.DestroyImmediate(t); }
        }

        // ── 双眼近似 ────────────────────────────────────────────────
        static void Stereo(Ctx ctx, Dictionary<string, object> item)
        {
            var c = Resolve(ctx, item);
            int mark = ctx.undo.Mark();
            try
            {
                RunBefore(ctx, c.def, "before");
                ApplyTime(ctx, c.t, false);
                float half = TJson.F(TJson.G(c.def, "ipd_mm"), 64f) * 0.0005f;
                var right = c.rot * Vector3.right;
                var eyes = new Color32[2][];
                for (int e = 0; e < 2; e++)
                {
                    var ce = new Cam { id = c.id, eye = c.eye + right * (e == 0 ? -half : half), rot = c.rot, hfov = c.hfov, vfov = c.vfov, w = c.w, h = c.h, ss = c.ss, def = c.def };
                    bool pp;
                    eyes[e] = RenderOnce(ctx, ce, c.w, c.h, c.ss, true, out pp);
                }
                var sbs = new Color32[c.w * 2 * c.h];
                for (int y = 0; y < c.h; y++)
                {
                    Array.Copy(eyes[0], y * c.w, sbs, y * 2 * c.w, c.w);
                    Array.Copy(eyes[1], y * c.w, sbs, y * 2 * c.w + c.w, c.w);
                }
                string rel = "stereo/" + c.id + "_approx_LR.png";
                Img.SavePng(sbs, c.w * 2, c.h, ctx.Out(rel));
                ctx.AddFile(rel);
                double la = Img.Stats(eyes[0])[0], ra = Img.Stats(eyes[1])[0];
                ctx.Metric("stereo." + c.id + ".apl_lr_diff", Math.Abs(la - ra), "左右两台相机的 APL 差（近似，不是头显）");
                ctx.shots.Add(new Dictionary<string, object>
                {
                    { "id", c.id + "_stereo" }, { "file", rel }, { "w", (double)(c.w * 2) }, { "h", (double)c.h },
                    { "label", "双眼近似：两台普通相机各偏 ±" + (half * 1000f).ToString("0", IC) + " mm 分别渲染、左右并排；不是 SPS-I 单通道立体，不是头显测试" },
                    { "apl_left", la }, { "apl_right", ra }
                });
            }
            finally { foreach (var e in ctx.undo.RollbackTo(mark)) ctx.Warn(e); ctx.lastT = null; }
        }

        // ── 动态序列：头部微动 / 时间推进，逐像素的亮度时间标准差 + 闪烁热图 ─────
        static void Sequence(Ctx ctx, Dictionary<string, object> item)
        {
            var c = Resolve(ctx, item);
            var d = c.def;
            string kind = TJson.S(TJson.G(d, "kind"), "micro_motion");
            float fps = TJson.F(TJson.G(d, "fps"), kind == "micro_motion" ? 90f : 60f);
            int n = TJson.I(TJson.G(d, "frames"), Mathf.RoundToInt(fps * TJson.F(TJson.G(d, "duration_s"), 1f)));
            float ampM = TJson.F(TJson.G(d, "amp_cm"), 2f) * 0.01f, ampDeg = TJson.F(TJson.G(d, "amp_deg"), 1f);
            // 尺寸：机位按 ppd 算过的就用它；不然默认 1280×720。超采样默认 1（头显里也没有超采样，闪烁才看得出来）
            bool byPpd = TJson.Has(d, "ppd");
            int w = byPpd ? c.w : TJson.I(TJson.G(d, "w"), 1280), h = byPpd ? c.h : TJson.I(TJson.G(d, "h"), 720);
            int ss = Math.Max(1, TJson.I(TJson.G(item, "ss"), 1));
            float eyeOff = TJson.F(TJson.G(d, "eye_offset_mm"), 0f) * 0.001f;
            bool save = TJson.B(TJson.G(d, "save_frames"), true);
            float thr = TJson.F(TJson.G(d, "hf_threshold"), 6f), scale = TJson.F(TJson.G(d, "heat_scale"), 24f);
            float t0 = c.t ?? TJson.F(TJson.G(d, "t0"), 0f);
            float t1 = TJson.F(TJson.G(d, "t1"), t0 + n / fps);
            bool advance = kind == "time" || TJson.B(TJson.G(d, "advance_time"));
            if (kind == "time") n = Math.Max(2, Mathf.RoundToInt((t1 - t0) * fps) + 1);
            if (n < 3) throw new StepException("序列至少 3 帧");
            bool hasTime = TJson.Has(d, "t") || TJson.Has(d, "t0");

            int mark = ctx.undo.Mark();
            Renderer2 r = null;
            string dir = "seq/" + c.id;
            try
            {
                RunBefore(ctx, d, "before");
                if (hasTime) ApplyTime(ctx, t0, false);
                r = new Renderer2(ctx, c, w, h, ss, true);
                int N = w * h;
                var sum = new double[N]; var sum2 = new double[N]; var hf2 = new double[N];
                var p1 = new float[N]; var p2 = new float[N]; var cur = new float[N];
                var apl = new List<object>();
                var right = c.rot * Vector3.right;
                Vector3 baseEye = c.eye + right * eyeOff;
                r.Frame(3);   // 预热（PPv2 的自动曝光之类）
                for (int i = 0; i < n; i++)
                {
                    float s = i / fps;
                    if (advance && hasTime) { ctx.lastT = null; ApplyTime(ctx, t0 + s, true); }
                    Vector3 off = Vector3.zero; Quaternion q = Quaternion.identity;
                    if (kind == "micro_motion")
                    {
                        // 固定的伪随机头部微动：两个正弦叠加（0.6 + 0.4），所以位置在 ±amp 之内、角度在 ±amp_deg 之内；每次跑都一样
                        off = new Vector3(W(s, 0.83f, 0.3f, 2.1f, 1.7f), W(s, 0.61f, 2.2f, 1.7f, 0.4f), W(s, 0.47f, 1.1f, 1.3f, 2.9f)) * ampM;
                        q = Quaternion.Euler(W(s, 0.53f, 0.2f, 1.6f, 2.0f) * ampDeg, W(s, 0.71f, 0.9f, 1.9f, 2.4f) * ampDeg, W(s, 0.37f, 1.4f, 1.1f, 0.6f) * ampDeg * 0.5f);
                    }
                    r.go.transform.position = baseEye + c.rot * off;
                    r.go.transform.rotation = c.rot * q;
                    var px = r.Frame(1);
                    double fsum = 0;
                    for (int k = 0; k < N; k++)
                    {
                        float y = Img.Luma(px[k]);
                        cur[k] = y; fsum += y;
                        sum[k] += y; sum2[k] += (double)y * y;
                        if (i >= 2) { double dd = y - 2f * p1[k] + p2[k]; hf2[k] += dd * dd; }
                    }
                    apl.Add(fsum / N);
                    var tmp = p2; p2 = p1; p1 = cur; cur = tmp;
                    if (save)
                    {
                        string rel = dir + "/" + i.ToString("0000") + ".png";
                        Img.SavePng(px, w, h, ctx.Out(rel));
                    }
                }
                if (save) ctx.AddFile(dir + "/0000.png …（" + n + " 帧）");
                // 每个像素：时间标准差（含真实的运动）、二阶差分的均方根（只剩来回跳的那部分 = 闪烁）
                var std = new float[N]; var hf = new float[N]; var mean = new float[N];
                for (int k = 0; k < N; k++)
                {
                    double m = sum[k] / n;
                    mean[k] = (float)m;
                    std[k] = (float)Math.Sqrt(Math.Max(0, sum2[k] / n - m * m));
                    hf[k] = (float)Math.Sqrt(hf2[k] / (n - 2) / 6.0);   // ÷6：白噪声时二阶差分的方差是 6σ²，这样和 std 同一个尺度
                }
                string pre = "seq." + c.id;
                ctx.Metric(pre + ".frames", n);
                ctx.Metric(pre + ".std_mean", Avg(std), "逐像素亮度（0–255）的时间标准差，全画面平均；含真实运动带来的变化");
                ctx.Metric(pre + ".std_p99", Pct(std, 0.99));
                ctx.Metric(pre + ".hf_mean", Avg(hf), "逐像素二阶时间差分的均方根 ÷ √6（0–255）：平滑的运动几乎不算，来回跳的闪烁 / 爬动才算");
                ctx.Metric(pre + ".hf_p99", Pct(hf, 0.99));
                ctx.Metric(pre + ".hf_frac", hf.Count(x => x > thr) / (double)N, "hf > " + thr.ToString("0.#", IC) + " 的像素占比");
                var ap = apl.Select(x => (double)x).ToList();
                double maxStep = 0;
                for (int i = 1; i < ap.Count; i++) maxStep = Math.Max(maxStep, Math.Abs(ap[i] - ap[i - 1]));
                ctx.Metric(pre + ".apl_min", ap.Min());
                ctx.Metric(pre + ".apl_max", ap.Max());
                ctx.Metric(pre + ".apl_max_step", maxStep, "相邻两帧 APL 的最大跳变");
                Img.SavePng(Img.Heat(std, mean, scale), w, h, ctx.Out(dir + "/heat_std.png"));
                Img.SavePng(Img.Heat(hf, mean, scale), w, h, ctx.Out(dir + "/heat_flicker.png"));
                ctx.AddFile(dir + "/heat_std.png"); ctx.AddFile(dir + "/heat_flicker.png");
                var rec = new Dictionary<string, object>
                {
                    { "id", c.id }, { "kind", kind }, { "fps", (double)fps }, { "frames", (double)n }, { "w", (double)w }, { "h", (double)h }, { "ss", (double)ss },
                    { "amp_cm", (double)(ampM * 100f) }, { "amp_deg", (double)ampDeg }, { "eye_offset_mm", (double)(eyeOff * 1000f) },
                    { "t0", hasTime ? (object)(double)t0 : null }, { "t1", advance ? (object)(double)t1 : null }, { "advance_time", advance },
                    { "heat_scale", (double)scale }, { "hf_threshold", (double)thr }, { "apl_per_frame", apl },
                    { "heat_std", dir + "/heat_std.png" }, { "heat_flicker", dir + "/heat_flicker.png" },
                    { "note", "编辑器里普通相机逐帧渲染（不是 SPS-I、不是头显）；热图颜色 0 → " + scale.ToString("0", IC) + "（亮度 0–255），底下是平均画面的灰度" }
                };
                File.WriteAllText(ctx.Out(dir + "/numbers.json"), TJson.Write(rec));
                ctx.AddFile(dir + "/numbers.json");
                ctx.sequences.Add(rec);
            }
            finally
            {
                if (r != null) r.Dispose();
                foreach (var e in ctx.undo.RollbackTo(mark)) ctx.Warn(e);
                ctx.lastT = null;
            }
        }

        static float W(float s, float f1, float p1, float f2, float p2)
        {
            return 0.6f * Mathf.Sin(2f * Mathf.PI * f1 * s + p1) + 0.4f * Mathf.Sin(2f * Mathf.PI * f2 * s + p2);
        }
        static double Avg(float[] a) { double s = 0; foreach (var x in a) s += x; return s / a.Length; }
        static double Pct(float[] a, double q)
        {
            var b = (float[])a.Clone();
            Array.Sort(b);
            return b[Math.Min(b.Length - 1, (int)(q * (b.Length - 1)))];
        }

        // ── 贴图压缩对照（Crunch / BC7 / 不压缩），只在沙盒里的拷贝上做 ─────────
        static void TextureCompare(Ctx ctx, Dictionary<string, object> item)
        {
            string id = TJson.S(TJson.G(item, "id"), "tex");
            var mats = Steps.SelectMaterials(item);
            if (mats.Count == 0) throw new StepException("texture_compare " + id + "：没选到材质");
            var variants = TJson.Sa(TJson.G(item, "variants"));
            if (variants.Count == 0) variants = new List<string> { "raw", "bc7", "crunch" };
            if (!variants.Contains("raw")) variants.Insert(0, "raw");          // 不压缩的那张是比较的基准
            int quality = TJson.I(TJson.G(item, "crunch_quality"), 50);
            var shots = TJson.Sa(TJson.G(item, "shots"));

            // 原贴图（材质上所有贴图属性里的 Texture2D 资产）
            var texProps = new Dictionary<Material, List<KeyValuePair<string, Texture2D>>>();
            var texInfo = new List<object>();
            var seen = new HashSet<Texture2D>();
            foreach (var m in mats)
            {
                var l = new List<KeyValuePair<string, Texture2D>>();
                foreach (var pn in m.GetTexturePropertyNames())
                {
                    var t2 = m.GetTexture(pn) as Texture2D;
                    if (t2 == null || string.IsNullOrEmpty(AssetDatabase.GetAssetPath(t2))) continue;
                    l.Add(new KeyValuePair<string, Texture2D>(pn, t2));
                    if (seen.Add(t2))
                    {
                        var ti = AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(t2)) as TextureImporter;
                        texInfo.Add(new Dictionary<string, object>
                        {
                            { "path", AssetDatabase.GetAssetPath(t2) }, { "size", t2.width + "×" + t2.height }, { "format_now", t2.format.ToString() },
                            { "mip", ti != null && ti.mipmapEnabled }, { "aniso", (double)(ti != null ? ti.anisoLevel : t2.anisoLevel) },
                            { "filter", (ti != null ? ti.filterMode : t2.filterMode).ToString() }, { "srgb", ti != null && ti.sRGBTexture },
                            { "type", ti != null ? ti.textureType.ToString() : "?" }, { "storage_mb_now", Img.StorageMB(t2) }
                        });
                    }
                }
                texProps[m] = l;
            }
            var rec = new Dictionary<string, object> { { "id", id }, { "materials", mats.Select(m => (object)AssetDatabase.GetAssetPath(m)).ToList() }, { "textures", texInfo }, { "crunch_quality", (double)quality } };
            var basePx = new Dictionary<string, Color32[]>();
            var perVar = new Dictionary<string, object>();
            foreach (var v in variants)
            {
                // 1) 贴图拷进沙盒、按这一档设导入
                string tdir = Sandbox.DIR + "/tex_" + id + "_" + v;
                AssetDatabase.CreateFolder(Sandbox.DIR, "tex_" + id + "_" + v);
                var map = new Dictionary<Texture2D, Texture2D>();
                double mb = 0;
                foreach (var t2 in seen)
                {
                    string src = AssetDatabase.GetAssetPath(t2);
                    string dst = tdir + "/" + Path.GetFileName(src);
                    if (!AssetDatabase.CopyAsset(src, dst)) throw new StepException("拷贝贴图失败 " + src);
                    var ti = (TextureImporter)AssetImporter.GetAtPath(dst);
                    var pc = ti.GetPlatformTextureSettings("Standalone");
                    pc.overridden = true;
                    pc.maxTextureSize = Math.Max(pc.maxTextureSize, ti.maxTextureSize);
                    if (v == "raw") pc.format = TextureImporterFormat.RGBA32;
                    else if (v == "bc7") pc.format = TextureImporterFormat.BC7;
                    else if (v == "crunch") { pc.format = ti.DoesSourceTextureHaveAlpha() || ti.textureType == TextureImporterType.NormalMap ? TextureImporterFormat.DXT5Crunched : TextureImporterFormat.DXT1Crunched; pc.crunchedCompression = true; pc.compressionQuality = quality; }
                    else throw new StepException("不认识的压缩档 " + v + "（raw / bc7 / crunch）");
                    ti.SetPlatformTextureSettings(pc);
                    ti.SaveAndReimport();
                    var nt = AssetDatabase.LoadAssetAtPath<Texture2D>(dst);
                    map[t2] = nt;
                    mb += Img.StorageMB(nt);
                }
                // 2) 材质拷贝（在沙盒里），换上这一档的贴图
                var clone = new Dictionary<Material, Material>();
                foreach (var m in mats)
                {
                    var cm = new Material(m) { name = m.name + "_" + v };
                    foreach (var kv in texProps[m]) cm.SetTexture(kv.Key, map[kv.Value]);
                    AssetDatabase.CreateAsset(cm, tdir + "/" + m.name + "_" + v + ".mat");
                    clone[m] = cm;
                }
                // 3) 场景里用到这些材质的 renderer 临时换成拷贝（结束时换回；场景不存）
                int mark = ctx.undo.Mark();
                int swapped = 0;
                foreach (var g in Scenes.AllRoots())
                    foreach (var rr in g.GetComponentsInChildren<Renderer>(true))
                    {
                        var sm = rr.sharedMaterials;
                        bool hit = false;
                        for (int k = 0; k < sm.Length; k++) if (sm[k] != null && clone.ContainsKey(sm[k])) { sm[k] = clone[sm[k]]; hit = true; }
                        if (!hit) continue;
                        var old = rr.sharedMaterials; var r3 = rr;
                        rr.sharedMaterials = sm;
                        ctx.undo.Push("材质换回 " + rr.name, () => { if (r3 != null) r3.sharedMaterials = old; });
                        swapped++;
                    }
                var vrec = new Dictionary<string, object> { { "storage_mb", mb }, { "renderers_swapped", (double)swapped } };
                ctx.Metric("tex." + id + "." + v + ".storage_mb", mb, "这一档全部贴图的显存 / 存储读数（编辑器 TextureUtil；Crunch 的下载体积更小，以构建报告为准）");
                try
                {
                    if (swapped == 0) throw new StepException("场景里没有 renderer 用这些材质");
                    foreach (var sid in shots)
                    {
                        var s = Shoot(ctx, new Dictionary<string, object> { { "cam", sid } }, "tex/" + id, "__" + v);
                        string f = (string)s["file"];
                        var px = Img.LoadPng(ctx.Out(f));
                        if (v == "raw") basePx[sid] = px;
                        else if (basePx.ContainsKey(sid))
                        {
                            double psnr = Img.Psnr(px, basePx[sid]);
                            ctx.Metric("tex." + id + "." + v + "." + sid + ".psnr", psnr, "和不压缩那张比的 PSNR（dB，8 位 RGB）；越高越像");
                            vrec[sid + "_psnr"] = psnr;
                        }
                    }
                }
                finally { foreach (var e in ctx.undo.RollbackTo(mark)) ctx.Warn(e); }
                perVar[v] = vrec;
            }
            rec["variants"] = perVar;
            rec["note"] = "贴图和材质都是沙盒里的拷贝，原资产的导入设置没动；场景里只是临时换了材质，没存";
            ctx.textures.Add(rec);
        }
    }

    // ─────────────────────────────────────────────────────────────────
    //  图像小工具（行 0 在最下面，和 Texture2D 一样）
    // ─────────────────────────────────────────────────────────────────
    public static class Img
    {
        public static float Luma(Color32 c) { return 0.2126f * c.r + 0.7152f * c.g + 0.0722f * c.b; }

        /// <summary>[APL, 暗像素 % (&lt; 12), 削顶 % (≥ 250), 最亮]</summary>
        public static double[] Stats(Color32[] px)
        {
            double sum = 0, mx = 0; int dark = 0, clip = 0;
            foreach (var p in px)
            {
                double y = Luma(p);
                sum += y; if (y < 12) dark++; if (y >= 250) clip++; if (y > mx) mx = y;
            }
            int n = Math.Max(1, px.Length);
            return new[] { sum / n, 100.0 * dark / n, 100.0 * clip / n, mx };
        }

        public static void SavePng(Color32[] px, int w, int h, string path)
        {
            var t = new Texture2D(w, h, TextureFormat.RGB24, false, false);
            try { t.SetPixels32(px); t.Apply(false); File.WriteAllBytes(path, t.EncodeToPNG()); }
            finally { Object.DestroyImmediate(t); }
        }

        public static Color32[] LoadPng(string path)
        {
            var t = new Texture2D(2, 2, TextureFormat.RGB24, false, false);
            try { t.LoadImage(File.ReadAllBytes(path)); return t.GetPixels32(); }
            finally { Object.DestroyImmediate(t); }
        }

        /// <summary>缩小按面积平均，放大取最近的像素。</summary>
        public static Color32[] Resample(Color32[] src, int sw, int sh, int dw, int dh)
        {
            var dst = new Color32[dw * dh];
            for (int y = 0; y < dh; y++)
            {
                int y0 = y * sh / dh, y1 = Math.Max(y0 + 1, (y + 1) * sh / dh);
                for (int x = 0; x < dw; x++)
                {
                    int x0 = x * sw / dw, x1 = Math.Max(x0 + 1, (x + 1) * sw / dw);
                    int r = 0, g = 0, b = 0, n = 0;
                    for (int yy = y0; yy < y1 && yy < sh; yy++)
                        for (int xx = x0; xx < x1 && xx < sw; xx++) { var c = src[yy * sw + xx]; r += c.r; g += c.g; b += c.b; n++; }
                    n = Math.Max(1, n);
                    dst[y * dw + x] = new Color32((byte)(r / n), (byte)(g / n), (byte)(b / n), 255);
                }
            }
            return dst;
        }

        public static double Psnr(Color32[] a, Color32[] b)
        {
            if (a.Length != b.Length) return double.NaN;
            double se = 0;
            for (int i = 0; i < a.Length; i++)
            {
                double dr = a[i].r - b[i].r, dg = a[i].g - b[i].g, db = a[i].b - b[i].b;
                se += dr * dr + dg * dg + db * db;
            }
            double mse = se / (3.0 * a.Length);
            return mse <= 1e-12 ? 99.0 : 10.0 * Math.Log10(255.0 * 255.0 / mse);
        }

        static readonly Color32[] RAMP =
        {
            new Color32(0, 0, 4, 255), new Color32(87, 16, 110, 255), new Color32(188, 55, 84, 255), new Color32(249, 142, 9, 255), new Color32(252, 255, 164, 255)
        };

        /// <summary>热图：值 0 → scale 走黑 → 紫 → 红 → 橙 → 浅黄；值很小的地方显示平均画面的暗灰，好认出是哪里。</summary>
        public static Color32[] Heat(float[] v, float[] mean, float scale)
        {
            var o = new Color32[v.Length];
            for (int i = 0; i < v.Length; i++)
            {
                float x = Mathf.Clamp01(v[i] / scale);
                if (x < 0.04f) { byte g = (byte)(mean[i] * 0.35f); o[i] = new Color32(g, g, g, 255); continue; }
                float f = x * (RAMP.Length - 1);
                int k = Math.Min(RAMP.Length - 2, (int)f);
                o[i] = Color32.Lerp(RAMP[k], RAMP[k + 1], f - k);
            }
            return o;
        }

        /// <summary>编辑器里的贴图存储大小（TextureUtil.GetStorageMemorySizeLong，内部 API；读不到就用运行时内存）。</summary>
        public static double StorageMB(Texture t)
        {
            try
            {
                var tu = typeof(EditorWindow).Assembly.GetType("UnityEditor.TextureUtil");
                var m = tu != null ? tu.GetMethod("GetStorageMemorySizeLong", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic) : null;
                if (m != null) return Convert.ToDouble(m.Invoke(null, new object[] { t })) / (1024.0 * 1024.0);
            }
            catch { }
            return UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(t) / (1024.0 * 1024.0);
        }
    }
}
