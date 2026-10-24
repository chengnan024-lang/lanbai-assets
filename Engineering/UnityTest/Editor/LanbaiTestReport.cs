// 蓝白 · Unity 测试工具 · 输出：manifest.json、console.jsonl、perf.json、summary.md、result.json
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Test
{
    public static class Report
    {
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;
        static readonly UTF8Encoding U8 = new UTF8Encoding(false);

        public static void WriteAll(Ctx ctx, int exit)
        {
            ctx.log.WriteJsonl(ctx.Out("console.jsonl"));
            ctx.AddFile("console.jsonl");
            if (ctx.perf.Count > 0)
            {
                File.WriteAllText(ctx.Out("perf.json"), TJson.Write(new Dictionary<string, object>
                {
                    { "note", "编辑器里的估算（Unity 编辑模式、手动渲染到 RenderTexture），不是头显实测；VR 一列是 1832×1920 渲两次的估算" },
                    { "gpu", Gpu() }, { "entries", ctx.perf.Cast<object>().ToList() }
                }), U8);
                ctx.AddFile("perf.json");
            }
            var m = Manifest(ctx, exit);
            File.WriteAllText(ctx.Out("summary.md"), Summary(ctx, exit, m), U8);
            ctx.AddFile("summary.md");
            ctx.AddFile("manifest.json");
            ctx.AddFile("result.json");
            m["files"] = ctx.files.Cast<object>().ToList();
            File.WriteAllText(ctx.Out("manifest.json"), TJson.Write(m), U8);
            var res = new Dictionary<string, object>
            {
                { "test", ctx.testId }, { "run", ctx.runId }, { "exit", (double)exit }, { "status", Runner.StatusOf(exit) }, { "out", ctx.outDir },
                { "blocked_reason", ctx.blockedReason }, { "error", ctx.error }
            };
            File.WriteAllText(ctx.Out("result.json"), TJson.Write(res), U8);
            // 最近一次的结果另存一份在测试文件夹上一层，好找
            File.WriteAllText(Path.Combine(Path.GetDirectoryName(ctx.outDir), "last_result.json"), TJson.Write(res), U8);
        }

        static Dictionary<string, object> Gpu()
        {
            return new Dictionary<string, object>
            {
                { "name", SystemInfo.graphicsDeviceName }, { "vendor", SystemInfo.graphicsDeviceVendor }, { "api", SystemInfo.graphicsDeviceType.ToString() },
                { "version", SystemInfo.graphicsDeviceVersion }, { "vram_mb", (double)SystemInfo.graphicsMemorySize },
                { "cpu", SystemInfo.processorType }, { "cpu_threads", (double)SystemInfo.processorCount }, { "ram_mb", (double)SystemInfo.systemMemorySize },
                { "os", SystemInfo.operatingSystem }
            };
        }

        static Dictionary<string, object> Manifest(Ctx ctx, int exit)
        {
            var m = new Dictionary<string, object>();
            m["tool"] = "Lanbai.Test.Runner";
            m["tool_version"] = Runner.VERSION;
            m["test_id"] = ctx.testId;
            m["run_id"] = ctx.runId;
            m["fromlocal"] = "FromLocal/" + ctx.testId + "/" + ctx.runId + "/";   // HANDOFF_CHATGPT 的约定：FromLocal/<test-id>/<YYYYMMDD-HHMMSS>/
            m["test_file"] = ctx.testFile;
            m["test_sha256"] = ctx.testSha;
            m["mode"] = ctx.mode;
            m["started_utc"] = ctx.started.ToString("o", IC);
            m["finished_utc"] = DateTime.UtcNow.ToString("o", IC);
            m["duration_s"] = Math.Round((DateTime.UtcNow - ctx.started).TotalSeconds, 1);
            m["exit_code"] = (double)exit;
            m["status"] = Runner.StatusOf(exit);
            m["blocked_reason"] = ctx.blockedReason;
            m["error"] = ctx.error;
            if (ctx.errorStack != null) m["error_stack"] = ctx.errorStack;
            if (ctx.toolErrors.Count > 0) m["tool_errors"] = ctx.toolErrors.Cast<object>().ToList();

            var repo = new Dictionary<string, object>();
            if (ctx.sync != null)
                foreach (var k in new[] { "repo_commit", "repo_branch", "repo_dirty", "repo_path", "entry", "synced_at", "paths", "tool_version" })
                    repo[k] = TJson.G(ctx.sync, k);
            else repo["status"] = "没有同步记录（" + Preflight.SYNC_RECORD + "），提交号不明";
            m["repo"] = repo;

            var pk = new Dictionary<string, object>();
            foreach (var n in new[] { "com.vrchat.worlds", "com.vrchat.base", "com.vrchat.udonsharp", "com.unity.postprocessing", "com.unity.textmeshpro", "com.vrchat.clientsim" })
            {
                string src; string v = Preflight.PackageVersion(n, out src);
                if (v != null) pk[n] = v;
            }
            m["unity"] = new Dictionary<string, object>
            {
                { "version", Application.unityVersion }, { "batch", Application.isBatchMode }, { "color_space", PlayerSettings.colorSpace.ToString() },
                { "quality", QualitySettings.names[QualitySettings.GetQualityLevel()] }, { "build_target", EditorUserBuildSettings.activeBuildTarget.ToString() },
                { "scene", ctx.scenePath }
            };
            m["packages"] = pk;
            m["gpu"] = Gpu();

            // 三层状态（D-40a #6）：工具只填 Unity 桌面这一层；头显这一层固定 not_tested
            m["layers"] = new Dictionary<string, object>
            {
                { "blender_offline", new Dictionary<string, object> { { "status", "pending_cloud" }, { "note", "云端对照 Blender 参考帧后填；工具不填" } } },
                { "unity_desktop", new Dictionary<string, object> { { "status", Runner.StatusOf(exit) }, { "note", "Unity 编辑器里的桌面渲染和编辑器估算的性能" } } },
                { "vr_headset", new Dictionary<string, object> { { "status", "not_tested" }, { "note", "工具不测头显，也不会把这一层标成通过；看 summary.md 末尾的头显清单" } } },
            };
            m["preflight"] = ctx.preflight.Cast<object>().ToList();
            m["preconditions"] = ctx.preconditions.Cast<object>().ToList();
            m["git_status_porcelain"] = ctx.gitStatus;
            m["steps"] = ctx.steps.Cast<object>().ToList();
            m["settings"] = ctx.settings.Cast<object>().ToList();
            m["checks"] = ctx.checks.Cast<object>().ToList();
            m["shots"] = ctx.shots.Cast<object>().ToList();
            m["sequences"] = ctx.sequences.Select(s => (object)s.Where(kv => kv.Key != "apl_per_frame").ToDictionary(kv => kv.Key, kv => kv.Value)).ToList();
            m["textures"] = ctx.textures.Cast<object>().ToList();
            m["metrics"] = ctx.metrics.OrderBy(kv => kv.Key, StringComparer.Ordinal).ToDictionary(kv => kv.Key, kv => (object)kv.Value);
            m["metric_notes"] = ctx.metricNotes.ToDictionary(kv => kv.Key, kv => (object)kv.Value);
            m["writes"] = ctx.writes;
            m["allowed_writes"] = TJson.Sa(TJson.G(ctx.test, "allowed_writes")).Cast<object>().ToList();   // 每次都写全（总导演 D-40 回复 #1）
            m["allowed_writes_why"] = TJson.G(ctx.test, "allowed_writes_why");
            m["backup_before"] = TJson.Sa(TJson.G(ctx.test, "backup_before")).Cast<object>().ToList();
            m["warnings"] = ctx.warnings.Cast<object>().ToList();
            return m;
        }

        // ─────────────────────────────────────────────────────────────
        static string Summary(Ctx ctx, int exit, Dictionary<string, object> m)
        {
            var sb = new StringBuilder();
            string title = TJson.S(TJson.G(ctx.test, "title"), ctx.testId);
            sb.AppendLine("# " + title + " · " + ctx.runId);
            sb.AppendLine();
            string verdict;
            switch (exit)
            {
                case 0: verdict = "✅ 跑完了，检查全过（退出码 0）"; break;
                case 1: verdict = "❌ 跑完了，有检查没过（退出码 1）"; break;
                case 2: verdict = "⛔ BLOCKED：预检或前置条件不满足，没跑（退出码 2）"; break;
                default: verdict = "💥 工具自己出了异常（退出码 3）"; break;
            }
            sb.AppendLine("**" + verdict + "**");
            if (ctx.blockedReason != null) sb.AppendLine("\n原因：" + ctx.blockedReason);
            if (ctx.error != null) sb.AppendLine("\n异常：`" + ctx.error + "`（堆栈在 manifest.json 的 error_stack）");
            sb.AppendLine();
            sb.AppendLine("- 测试：`" + ctx.testId + "`（" + TJson.S(TJson.G(ctx.test, "source"), "") + "）");
            sb.AppendLine("- 三层状态：Blender 离线 **云端填**；Unity 桌面 **" + Runner.StatusOf(exit) + "**；头显 **not_tested**（工具不测头显）");
            sb.AppendLine("- 工具 " + Runner.VERSION + "，Unity " + Application.unityVersion + (Application.isBatchMode ? "（批处理）" : "（菜单）") + "，显卡 " + SystemInfo.graphicsDeviceName + "（" + SystemInfo.graphicsDeviceType + "）");
            var repo = TJson.M(m["repo"]);
            sb.AppendLine("- 仓库：" + (ctx.sync != null ? "提交 `" + TJson.S(TJson.G(repo, "repo_commit"), "?") + "`，" + TJson.S(TJson.G(repo, "synced_at"), "?") + " 同步，条目「" + TJson.S(TJson.G(repo, "entry"), "?") + "」" : "没有同步记录，提交号不明"));
            sb.AppendLine("- 场景：" + (ctx.scenePath ?? "（没打开）") + "；用时 " + m["duration_s"] + " s");
            sb.AppendLine("- **交回**：把整个文件夹 `" + ctx.outDir + "` 拷到仓库的 `" + m["fromlocal"] + "`，再推。看到的问题写进 `FromLocal/" + ctx.testId + "/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。");
            sb.AppendLine();

            if (ctx.checks.Count > 0)
            {
                sb.AppendLine("## 检查项");
                sb.AppendLine("| 结果 | 检查 | 量到 | 要求 | 说明 |");
                sb.AppendLine("|---|---|---|---|---|");
                foreach (var c in ctx.checks.OrderBy(c => (string)c["status"] == "fail" ? 0 : (string)c["status"] == "warn" ? 1 : 2))
                {
                    string st = (string)c["status"];
                    string icon = st == "pass" ? "✅" : st == "warn" ? "⚠️" : "❌";
                    sb.AppendLine("| " + icon + " " + st + " | `" + c["id"] + "` | " + (c.ContainsKey("measured") ? N((double)c["measured"]) : "—") + " | " +
                                  (c.ContainsKey("expect") ? (string)c["expect"] : TJson.S(c["value"], "")) + (TJson.B(c["gate"]) ? "" : "（不卡）") + " | " +
                                  Esc(TJson.S(TJson.G(c, "why"), "") + (c.ContainsKey("detail") ? " " + c["detail"] : "")) + " |");
                }
                sb.AppendLine();
            }

            sb.AppendLine("## 预检（只读）");
            foreach (var p in ctx.preflight) sb.AppendLine("- " + Icon((string)p["status"]) + " " + p["item"] + "：" + Esc((string)p["detail"]));
            if (ctx.preconditions.Count > 0)
            {
                sb.AppendLine();
                sb.AppendLine("## 前置条件");
                foreach (var p in ctx.preconditions) sb.AppendLine("- " + ((string)p["status"] == "ok" ? "✅" : "⛔") + " " + Esc((string)p["item"]) + ((string)p["status"] == "ok" ? "" : "：" + Esc((string)p["detail"])));
            }
            sb.AppendLine();

            if (ctx.steps.Count > 0)
            {
                sb.AppendLine("## 步骤");
                foreach (var s in ctx.steps)
                {
                    string st = TJson.S(TJson.G(s, "status"), "?");
                    sb.AppendLine("- " + (st == "ok" ? "✅" : st == "skipped" ? "⏭️" : "❌") + " [" + s["phase"] + "] " + Esc(TJson.S(TJson.G(s, "desc"), "")) +
                                  (s.ContainsKey("ms") ? "（" + N((double)s["ms"]) + " ms）" : "") + (s.ContainsKey("error") ? "\n  - **" + Esc((string)s["error"]) + "**" : ""));
                }
                sb.AppendLine();
            }

            if (ctx.shots.Count > 0)
            {
                sb.AppendLine("## 截图");
                sb.AppendLine("| 机位 | t | 尺寸 | APL | < 12 % | 参考 APL | 文件 |");
                sb.AppendLine("|---|---|---|---|---|---|---|");
                foreach (var s in ctx.shots)
                    sb.AppendLine("| " + s["id"] + " | " + (s.ContainsKey("t") ? N((double)s["t"]) : "") + " | " + N((double)s["w"]) + "×" + N((double)s["h"]) + " | " +
                                  (s.ContainsKey("apl") ? N((double)s["apl"]) : "") + " | " + (s.ContainsKey("dark_pct") ? N((double)s["dark_pct"]) : "") + " | " +
                                  (s.ContainsKey("ref_apl") ? N((double)s["ref_apl"]) : (s.ContainsKey("ref_status") ? Esc((string)s["ref_status"]) : "")) + " | `" + s["file"] + "`" +
                                  (s.ContainsKey("label") ? " " + Esc((string)s["label"]) : "") + " |");
                sb.AppendLine();
            }

            if (ctx.sequences.Count > 0)
            {
                sb.AppendLine("## 动态序列（闪烁）");
                sb.AppendLine("编辑器里普通相机逐帧渲染：`hf` 是逐像素亮度的二阶时间差分（÷√6，0–255），平滑的运动几乎不算、来回跳的闪烁和爬动才算；`std` 含真实运动。热图在 `seq/<id>/heat_*.png`。**这是近似，不是头显。**");
                sb.AppendLine();
                sb.AppendLine("| 序列 | 种类 | 帧 | std 平均 / p99 | hf 平均 / p99 | hf 超阈值的像素 | APL 最小 / 最大 / 最大跳变 |");
                sb.AppendLine("|---|---|---|---|---|---|---|");
                foreach (var s in ctx.sequences)
                {
                    string k = "seq." + s["id"];
                    sb.AppendLine("| " + s["id"] + " | " + s["kind"] + " | " + N((double)s["frames"]) + " | " + Mt(ctx, k + ".std_mean") + " / " + Mt(ctx, k + ".std_p99") + " | " +
                                  Mt(ctx, k + ".hf_mean") + " / " + Mt(ctx, k + ".hf_p99") + " | " + Pc(ctx, k + ".hf_frac") + " | " +
                                  Mt(ctx, k + ".apl_min") + " / " + Mt(ctx, k + ".apl_max") + " / " + Mt(ctx, k + ".apl_max_step") + " |");
                }
                sb.AppendLine();
            }

            if (ctx.perf.Count > 0)
            {
                sb.AppendLine("## 性能（编辑器估算，不是头显）");
                sb.AppendLine("| 项 / 状态 | t | 电脑 1920×1080 ms | VR 估算 ms（CPU） | draw call | SetPass | 三角面 |");
                sb.AppendLine("|---|---|---|---|---|---|---|");
                foreach (var p in ctx.perf)
                {
                    var d = (Dictionary<string, object>)p["desktop_1920x1080"];
                    var v = (Dictionary<string, object>)p["vr_estimate_1832x1920x2"];
                    var r = (Dictionary<string, object>)p["render_stats"];
                    sb.AppendLine("| " + p["id"] + " / " + p["state"] + " | " + (p.ContainsKey("t") ? N((double)p["t"]) : "") + " | " + N((double)d["total_ms"]) + " | " +
                                  N((double)v["total_ms"]) + "（" + N((double)v["cpu_ms"]) + "） | " + N((double)r["draw_calls"]) + " | " + N((double)r["setpass"]) + " | " + N((double)r["triangles"]) + " |");
                }
                sb.AppendLine();
            }

            if (ctx.textures.Count > 0)
            {
                sb.AppendLine("## 贴图压缩对照（沙盒里的拷贝）");
                foreach (var t in ctx.textures)
                {
                    sb.AppendLine("- `" + t["id"] + "`：");
                    foreach (var kv in (Dictionary<string, object>)t["variants"])
                    {
                        var vr = (Dictionary<string, object>)kv.Value;
                        sb.AppendLine("  - " + kv.Key + "：存储 " + N((double)vr["storage_mb"]) + " MB；" +
                                      string.Join("，", vr.Where(x => x.Key.EndsWith("_psnr")).Select(x => x.Key.Replace("_psnr", "") + " PSNR " + N((double)x.Value) + " dB").ToArray()));
                    }
                }
                sb.AppendLine();
            }

            if (ctx.settings.Count > 0)
            {
                sb.AppendLine("## 项目设置（只查不改）");
                foreach (var s in ctx.settings) sb.AppendLine("- " + Icon((string)s["status"]) + " " + s["item"] + "：" + Esc((string)s["detail"]));
                sb.AppendLine();
            }

            if (ctx.writes != null)
            {
                var und = (List<object>)ctx.writes["undeclared"];
                var dec = (List<object>)ctx.writes["declared"];
                sb.AppendLine("## 写入");
                var aw = TJson.Sa(TJson.G(ctx.test, "allowed_writes"));
                sb.AppendLine("- 允许搭建脚本写的地方（沙盒规则的例外，" + aw.Count + " 条）：" + (aw.Count == 0 ? "没有" : string.Join("、", aw.Select(x => "`" + x + "`").ToArray())) +
                              (TJson.Has(ctx.test, "allowed_writes_why") ? "。为什么：" + Esc(TJson.S(TJson.G(ctx.test, "allowed_writes_why"))) : ""));
                var bb = TJson.Sa(TJson.G(ctx.test, "backup_before"));
                if (bb.Count > 0) sb.AppendLine("- 开搭之前原样备份进 `backup_before/` 的：" + string.Join("、", bb.Select(x => "`" + x + "`").ToArray()));
                sb.AppendLine("- 沙盒 `" + Sandbox.DIR + "/`（下次跑会删掉重建，也可以手动删）");
                sb.AppendLine("- 搭建脚本按测试定义允许写的地方：" + dec.Count + " 个文件（清单在 manifest.json 的 writes.declared）");
                sb.AppendLine("- **没声明的写入：" + und.Count + "**" + (und.Count > 0 ? "：" + string.Join("；", und.Take(20).Select(x => (string)x).ToArray()) + (und.Count > 20 ? " …" : "") : ""));
                var ps = (List<object>)ctx.writes["project_settings_changed"];
                if (ps.Count > 0) sb.AppendLine("- **ProjectSettings 被改了**：" + string.Join("、", ps.Select(x => (string)x).ToArray()));
                var tt = ctx.writes.ContainsKey("tool_touched_restored") ? (List<object>)ctx.writes["tool_touched_restored"] : new List<object>();
                if (tt.Count > 0) sb.AppendLine("- 工具临时改过、已改回的（不算没声明的写入）：" + tt.Count + " 个（清单在 manifest.json 的 writes.tool_touched_restored）");
                sb.AppendLine("- 工具不保存场景。");
                sb.AppendLine();
            }

            if (ctx.warnings.Count > 0)
            {
                sb.AppendLine("## 警告");
                foreach (var w in ctx.warnings) sb.AppendLine("- " + Esc(w));
                sb.AppendLine();
            }

            int errs = ctx.log.CountWhere(r => (LogCapture.Type(r) == "Error" || LogCapture.Type(r) == "Exception" || LogCapture.Type(r) == "CompileError") && !LogCapture.IsTool(r));
            sb.AppendLine("## Console");
            sb.AppendLine("全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 " + errs + " 条" +
                          (errs > 0 ? "，前几条：" : "。"));
            foreach (var s in ctx.log.MessagesWhere(r => (LogCapture.Type(r) == "Error" || LogCapture.Type(r) == "Exception" || LogCapture.Type(r) == "CompileError") && !LogCapture.IsTool(r), 8))
                sb.AppendLine("  - `" + Esc(s.Length > 200 ? s.Substring(0, 200) + "…" : s) + "`");
            sb.AppendLine();

            sb.AppendLine("## 头显里还要看的（工具不测；空着 = 没验过，不是过了）");
            foreach (var h in TJson.Sa(TJson.G(ctx.test, "headset_checklist"))) sb.AppendLine("- [ ] " + h);
            sb.AppendLine("- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）");
            sb.AppendLine("- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）");
            sb.AppendLine("- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）");
            foreach (var h in TJson.Sa(TJson.G(ctx.test, "manual"))) sb.AppendLine("- [ ] （手动）" + h);
            return sb.ToString();
        }

        static string Icon(string s) { return s == "ok" ? "✅" : s == "blocked" || s == "fail" ? "⛔" : s == "warn" ? "⚠️" : "ℹ️"; }
        static string N(double v) { return Math.Abs(v) >= 1000 ? v.ToString("N0", IC) : v.ToString("0.##", IC); }
        static string Mt(Ctx ctx, string k) { double v; return ctx.metrics.TryGetValue(k, out v) ? N(v) : "—"; }
        static string Pc(Ctx ctx, string k) { double v; return ctx.metrics.TryGetValue(k, out v) ? (100 * v).ToString("0.###", IC) + " %" : "—"; }
        static string Esc(string s) { return (s ?? "").Replace("|", "\\|").Replace("\n", " "); }
    }
}
