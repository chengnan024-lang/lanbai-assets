// 蓝白 · Unity 测试工具 · 性能（编辑器里的估算，不是头显）
// 测法照门测试的 LB_GateTest.Perf（10-08 起一直这么量，数可以和以前的对上）：
//   * 一次渲染的 draw call / batches / SetPass / 三角面 / 投影物体：ProfilerRecorder 渲染前后的差 + UnityStats；
//   * 帧时间：同一台相机渲进 HDR RT（含 PPv2），渲染前后各读 1 个像素做 GPU 同步，预热 4 次、取 24 次的中位数；
//     合计 = CPU 提交 + 等 GPU 画完（不重叠地算，偏保守）。电脑 1920×1080 一次；VR 估算 1832×1920 渲两次（竖直视角 100°，同一方向）。
//   * 1.2.2（阿白 10-25 后台量 GPU 只报 0.05 ms）：这里的计时不靠 Game 视图、不靠 Profiler 的 GPU 计数，而是每次手动 Render 后
//     读回 1 个像素逼 GPU 画完，所以编辑器在后台也成立。另加：先连续渲 0.5 s 让 GPU 升频（后台时显卡常降频）；同样大小的空渲染
//     （什么都不画，只清屏 + 读回）的时间记成 sync_ms，gpu_est_ms = 合计 − sync_ms；样本的离散度（p90 / 中位数）> 1.5 记警告。
//   * 显存（Windows）：读这个 Unity 进程的“GPU Process Memory\Dedicated Usage”（物理显存，按进程；含编辑器自己），每个状态量一次，
//     看状态之间的差；有 nvidia-smi 时另记整卡已用。量不到就记 null，不估。
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
                    if (td.Count > 0)
                    {
                        ctx.lastT = null;
                        if (!Steps.RunList(ctx, td, "perf_teardown", null, true))
                        {
                            // 没搭回去：后面量的就不是测试定义说的那个场景了，停掉剩下的性能项
                            ctx.Warn("性能状态 " + TJson.S(TJson.G(st, "id")) + " 的 teardown 失败，剩下的性能项不量了（量出来的会贴错标签）");
                            return;
                        }
                    }
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
                    rec["vram"] = Vram(ctx);
                    var desk = Time(ctx, c, 1920, 1080, 1, -1f, probe);
                    var vr = Time(ctx, c, 1832, 1920, 2, 100f, probe);
                    rec["desktop_1920x1080"] = desk;
                    rec["vr_estimate_1832x1920x2"] = vr;
                    string k = "perf." + id + "." + sid;
                    ctx.Metric(k + ".desktop_ms", (double)desk["total_ms"], "编辑器估算：电脑 1920×1080 一帧（CPU 提交 + 等 GPU）中位数");
                    ctx.Metric(k + ".vr_ms", (double)vr["total_ms"], "编辑器估算：1832×1920 渲两次（VR 两只眼，同一方向）中位数；不是头显实测");
                    ctx.Metric(k + ".vr_cpu_ms", (double)vr["cpu_ms"]);
                    ctx.Metric(k + ".desktop_gpu_est_ms", (double)desk["gpu_est_ms"], "合计 − 同尺寸空渲染（清屏 + 读回）的时间：近似 GPU 画这一帧的时间");
                    ctx.Metric(k + ".vr_gpu_est_ms", (double)vr["gpu_est_ms"]);
                    var vm = (Dictionary<string, object>)rec["vram"];
                    if (vm["process_dedicated_mb"] != null) ctx.Metric(k + ".vram_process_mb", (double)vm["process_dedicated_mb"], "Unity 进程占的物理显存（含编辑器）；看状态之间的差");
                    var rs = (Dictionary<string, object>)rec["render_stats"];
                    foreach (var name in new[] { "draw_calls", "batches", "setpass", "triangles", "vertices", "shadow_casters" })
                        if (rs.ContainsKey(name) && rs[name] != null) ctx.Metric(k + "." + name, (double)rs[name]);
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
                    // 编辑模式手动 Render 时 ProfilerRecorder 常常读成 0（HANDOFF_CHATGPT §G）：读到 0 就记“没量到”（null），不当成 0
                    bool zero = !rDraw.Valid || (d1 - d0 == 0 && t1 - t0 == 0);
                    r["recorder_zero"] = zero;
                    r["draw_calls"] = zero ? null : (object)(double)(d1 - d0);
                    r["batches"] = zero ? null : (object)(double)(b1 - b0);
                    r["setpass"] = zero ? null : (object)(double)(s1 - s0);
                    r["triangles"] = zero ? null : (object)(double)(t1 - t0);
                    r["vertices"] = zero ? null : (object)(double)(v1 - v0);
                    r["shadow_casters"] = zero ? null : (object)(double)(c1 - c0);
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

        // 物理显存（Windows）：这个进程的 GPU Process Memory\Dedicated Usage（性能计数器，和任务管理器“专用 GPU 内存”同一个数），
        // 另记 nvidia-smi 的整卡已用。都是外部命令，各限 10 s；拿不到就 null（不估）。
        static Dictionary<string, object> Vram(Ctx ctx)
        {
            var r = new Dictionary<string, object> { { "process_dedicated_mb", null }, { "card_used_mb", null }, { "card_total_mb", null } };
            if (Application.platform != RuntimePlatform.WindowsEditor) { r["note"] = "只在 Windows 编辑器里量"; return r; }
            int pid = Process.GetCurrentProcess().Id;
            string ps = "$s = (Get-Counter -Counter '\\GPU Process Memory(pid_" + pid + "_*)\\Dedicated Usage' -ErrorAction SilentlyContinue).CounterSamples; " +
                        "if ($s) { [Math]::Round((($s | Measure-Object CookedValue -Sum).Sum) / 1MB, 1) }";
            string a = Run("powershell", "-NoProfile -NonInteractive -Command \"" + ps + "\"");
            double v;
            if (a != null && double.TryParse(a.Trim(), NumberStyles.Float, IC, out v)) r["process_dedicated_mb"] = v;
            string n = Run("nvidia-smi", "--query-gpu=memory.used,memory.total --format=csv,noheader,nounits");
            if (n != null)
            {
                var parts = n.Split('\n')[0].Split(',');
                double u, t;
                if (parts.Length >= 2 && double.TryParse(parts[0].Trim(), NumberStyles.Float, IC, out u) && double.TryParse(parts[1].Trim(), NumberStyles.Float, IC, out t))
                { r["card_used_mb"] = u; r["card_total_mb"] = t; }
            }
            r["note"] = "process_dedicated_mb：Unity 进程（含编辑器、场景视图、所有打开的资源）占的物理显存；比状态之间的差，不当作世界的绝对值。card_used_mb：整张卡（含别的程序）";
            return r;
        }

        static string Run(string exe, string args)
        {
            try
            {
                var psi = new ProcessStartInfo(exe, args) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true };
                using (var p = Process.Start(psi))
                {
                    string o = p.StandardOutput.ReadToEnd();
                    if (!p.WaitForExit(10000)) { try { p.Kill(); } catch { } return null; }
                    return p.ExitCode == 0 ? o : null;
                }
            }
            catch { return null; }
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
            var cpu = new List<double>(); var tot = new List<double>(); var empty = new List<double>();
            try
            {
                cam.targetTexture = rt;
                // 升频：连续渲 0.5 s（至少 4 次）再开始计
                var warm = Stopwatch.StartNew();
                for (int f = 0; f < 4 || warm.Elapsed.TotalMilliseconds < 500; f++) { cam.Render(); Sync(rt, probe); if (f > 400) break; }
                for (int f = 0; f < 24; f++)
                {
                    Sync(rt, probe);
                    var sw = Stopwatch.StartNew();
                    for (int e = 0; e < eyes; e++) cam.Render();
                    double c1 = sw.Elapsed.TotalMilliseconds;
                    Sync(rt, probe);
                    double t1 = sw.Elapsed.TotalMilliseconds;
                    cpu.Add(c1); tot.Add(t1);
                }
                // 空渲染：同一台相机，什么都不画（cullingMask 0、纯色清屏、关 PPv2），量提交 + 读回本身的开销
                var mask = cam.cullingMask; var flags = cam.clearFlags;
                var ppl = go.GetComponent<UnityEngine.Rendering.PostProcessing.PostProcessLayer>();
                bool ppOn = ppl != null && ppl.enabled;
                cam.cullingMask = 0; cam.clearFlags = CameraClearFlags.SolidColor;
                if (ppl != null) ppl.enabled = false;
                for (int f = 0; f < 16; f++)
                {
                    Sync(rt, probe);
                    var sw = Stopwatch.StartNew();
                    for (int e = 0; e < eyes; e++) cam.Render();
                    Sync(rt, probe);
                    empty.Add(sw.Elapsed.TotalMilliseconds);
                }
                cam.cullingMask = mask; cam.clearFlags = flags;
                if (ppl != null) ppl.enabled = ppOn;
            }
            finally { cam.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(go); }
            cpu.Sort(); tot.Sort(); empty.Sort();
            double med = tot[tot.Count / 2], p90 = tot[(int)(tot.Count * 0.9)], sync = empty[empty.Count / 2];
            if (p90 > 1.5 * med) ctx.Warn("性能 " + c.id + " " + w + "×" + h + "：样本很散（p90 " + p90.ToString("0.00", IC) + " / 中位 " + med.ToString("0.00", IC) + " ms），机器上有别的负载或显卡在降频，这一组只作参考");
            return new Dictionary<string, object>
            {
                { "w", (double)w }, { "h", (double)h }, { "renders_per_frame", (double)eyes }, { "vfov", (double)fovUsed },
                { "total_ms", Math.Round(med, 2) }, { "cpu_ms", Math.Round(cpu[cpu.Count / 2], 2) },
                { "sync_ms", Math.Round(sync, 2) }, { "gpu_est_ms", Math.Round(Math.Max(0, med - sync), 2) }, { "p90_ms", Math.Round(p90, 2) },
                { "min_ms", Math.Round(tot[0], 2) }, { "max_ms", Math.Round(tot[tot.Count - 1], 2) }, { "samples", (double)tot.Count }, { "ppv2", pp }
            };
        }
    }
}
