// 蓝白 · Unity 测试工具 · 性能（编辑器里的估算，不是头显）
// 测法照门测试的 LB_GateTest.Perf（10-08 起一直这么量，数可以和以前的对上）：
//   * 一次渲染的 draw call / batches / SetPass / 三角面 / 投影物体：ProfilerRecorder 渲染前后的差 + UnityStats；
//   * 帧时间：同一台相机渲进 HDR RT（含 PPv2），渲染前后各读 1 个像素做 GPU 同步，预热 4 次、取 24 次的中位数；
//     合计 = CPU 提交 + 等 GPU 画完（不重叠地算，偏保守）。电脑 1920×1080 一次；VR 估算 1832×1920 渲两次（竖直视角 100°，同一方向）。
// 每个性能项可以有几种“状态”（全开 / 关掉云海 / 关掉整个云……），每种状态的步骤做完量、量完改回。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Linq;
using Unity.Profiling;
using UnityEditor;
using UnityEngine;
using Debug = UnityEngine.Debug;
using Object = UnityEngine.Object;

namespace Lanbai.Test
{
    public static class Perf
    {
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        public static void All(Ctx ctx)
        {
            foreach (var o in TJson.L(ctx.T("perf")))
            {
                var item = TJson.M(o);
                var states = TJson.L(TJson.G(item, "states"));
                if (states.Count == 0) states = new List<object> { new Dictionary<string, object> { { "id", "all_on" } } };
                foreach (var so in states)
                {
                    var st = TJson.M(so);
                    Capture.Guard(ctx, "perf", new Dictionary<string, object> { { "id", TJson.S(TJson.G(item, "id")) + "/" + TJson.S(TJson.G(st, "id")) } }, () => One(ctx, item, st));
                    // 状态里重搭过的（比如 auto_lite 档），改回以后按 teardown 再搭一次
                    var td = TJson.L(TJson.G(st, "teardown"));
                    if (td.Count > 0) { ctx.lastT = null; Steps.RunList(ctx, td, "perf_teardown", null, true); }
                }
            }
        }

        static void One(Ctx ctx, Dictionary<string, object> item, Dictionary<string, object> state)
        {
            string id = TJson.S(TJson.G(item, "id"), "perf"), sid = TJson.S(TJson.G(state, "id"), "all_on");
            var c = Capture.Resolve(ctx, item);
            int mark = ctx.undo.Mark();
            var stSteps = TJson.L(TJson.G(state, "steps"));
            if (stSteps.Count > 0)
            {
                ctx.lastT = null;
                if (!Steps.RunList(ctx, stSteps, "perf_state " + id + "/" + sid, null, true, true)) throw new StepException("状态 " + sid + " 的步骤失败");
            }
            try
            {
                Capture.ApplyTime(ctx, c.t, false);
                var rec = new Dictionary<string, object> { { "id", id }, { "state", sid }, { "cam", TJson.S(TJson.G(item, "cam")) } };
                if (c.t.HasValue) rec["t"] = (double)c.t.Value;
                if (TJson.Has(state, "label")) rec["label"] = TJson.G(state, "label");
                var probe = new Texture2D(1, 1, TextureFormat.RGBA32, false);
                try
                {
                    rec["render_stats"] = Stats(ctx, c, probe);
                    var desk = Time(ctx, c, 1920, 1080, 1, -1f, probe);
                    var vr = Time(ctx, c, 1832, 1920, 2, 100f, probe);
                    rec["desktop_1920x1080"] = desk;
                    rec["vr_estimate_1832x1920x2"] = vr;
                    string k = "perf." + id + "." + sid;
                    ctx.Metric(k + ".desktop_ms", (double)desk["total_ms"], "编辑器估算：电脑 1920×1080 一帧（CPU 提交 + 等 GPU）中位数");
                    ctx.Metric(k + ".vr_ms", (double)vr["total_ms"], "编辑器估算：1832×1920 渲两次（VR 两只眼，同一方向）中位数；不是头显实测");
                    ctx.Metric(k + ".vr_cpu_ms", (double)vr["cpu_ms"]);
                    var rs = (Dictionary<string, object>)rec["render_stats"];
                    foreach (var name in new[] { "draw_calls", "batches", "setpass", "triangles", "vertices", "shadow_casters" })
                        if (rs.ContainsKey(name)) ctx.Metric(k + "." + name, (double)rs[name]);
                }
                finally { Object.DestroyImmediate(probe); }
                ctx.perf.Add(rec);
            }
            finally
            {
                foreach (var e in ctx.undo.RollbackTo(mark)) ctx.Warn(e);
                if (stSteps.Count > 0) ctx.lastT = null;
            }
        }

        static Dictionary<string, object> Stats(Ctx ctx, Capture.Cam c, Texture2D probe)
        {
            var r = new Dictionary<string, object>();
            using (var rDraw = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Draw Calls Count"))
            using (var rBatch = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Batches Count"))
            using (var rSet = ProfilerRecorder.StartNew(ProfilerCategory.Render, "SetPass Calls Count"))
            using (var rTri = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Triangles Count"))
            using (var rVert = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Vertices Count"))
            using (var rShadow = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Shadow Casters Count"))
            {
                bool pp;
                var go = Capture.MakeCam(ctx, c, 1920, 1080, true, out pp);
                var cam = go.GetComponent<Camera>();
                var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.DefaultHDR, RenderTextureReadWrite.Linear) { antiAliasing = 1 };
                rt.Create();
                try
                {
                    cam.targetTexture = rt;
                    cam.Render(); Sync(rt, probe);
                    long d0 = rDraw.CurrentValue, b0 = rBatch.CurrentValue, s0 = rSet.CurrentValue, t0 = rTri.CurrentValue, v0 = rVert.CurrentValue, c0 = rShadow.CurrentValue;
                    cam.Render(); Sync(rt, probe);
                    long d1 = rDraw.CurrentValue, b1 = rBatch.CurrentValue, s1 = rSet.CurrentValue, t1 = rTri.CurrentValue, v1 = rVert.CurrentValue, c1 = rShadow.CurrentValue;
                    r["recorder_valid"] = rDraw.Valid;
                    r["draw_calls"] = (double)(d1 - d0);
                    r["batches"] = (double)(b1 - b0);
                    r["setpass"] = (double)(s1 - s0);
                    r["triangles"] = (double)(t1 - t0);
                    r["vertices"] = (double)(v1 - v0);
                    r["shadow_casters"] = (double)(c1 - c0);
                    r["unitystats_after"] = new Dictionary<string, object>
                    {
                        { "draw_calls", (double)UnityStats.drawCalls }, { "batches", (double)UnityStats.batches }, { "setpass", (double)UnityStats.setPassCalls },
                        { "triangles", (double)UnityStats.triangles }, { "vertices", (double)UnityStats.vertices }
                    };
                    r["ppv2"] = pp;
                    r["note"] = "ProfilerRecorder：同一帧里第二次渲染前后的差（编辑模式手动 Render 时可能读成 0，那就看 Game 视图 / Frame Debugger）；UnityStats 是上一帧的读数";
                }
                finally
                {
                    cam.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(go);
                }
            }
            r["quality"] = QualitySettings.names[QualitySettings.GetQualityLevel()];
            r["lod_bias"] = (double)QualitySettings.lodBias;
            r["pixel_lights"] = (double)QualitySettings.pixelLightCount;
            r["shadow_distance"] = (double)QualitySettings.shadowDistance;
            r["msaa"] = (double)QualitySettings.antiAliasing;
            return r;
        }

        static void Sync(RenderTexture rt, Texture2D probe)
        {
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            probe.ReadPixels(new Rect(0, 0, 1, 1), 0, 0, false);
            probe.Apply(false);
            RenderTexture.active = prev;
        }

        static Dictionary<string, object> Time(Ctx ctx, Capture.Cam c, int w, int h, int eyes, float vfov, Texture2D probe)
        {
            bool pp;
            var go = Capture.MakeCam(ctx, c, w, h, true, out pp);
            var cam = go.GetComponent<Camera>();
            if (vfov > 0f) cam.fieldOfView = vfov;
            float fovUsed = cam.fieldOfView;
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.DefaultHDR, RenderTextureReadWrite.Linear) { antiAliasing = 1 };
            rt.Create();
            var cpu = new List<double>(); var tot = new List<double>();
            try
            {
                cam.targetTexture = rt;
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
            }
            finally { cam.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(go); }
            cpu.Sort(); tot.Sort();
            return new Dictionary<string, object>
            {
                { "w", (double)w }, { "h", (double)h }, { "renders_per_frame", (double)eyes }, { "vfov", (double)fovUsed },
                { "total_ms", Math.Round(tot[tot.Count / 2], 2) }, { "cpu_ms", Math.Round(cpu[cpu.Count / 2], 2) },
                { "min_ms", Math.Round(tot[0], 2) }, { "max_ms", Math.Round(tot[tot.Count - 1], 2) }, { "samples", (double)tot.Count }, { "ppv2", pp }
            };
        }
    }
}
