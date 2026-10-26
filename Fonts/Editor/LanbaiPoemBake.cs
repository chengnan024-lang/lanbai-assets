// 蓝白 · 字体套件第 5 版 · 字幕与世界字的编辑器烘焙（D-45，2026-10-25，总工程师）。
// !!! NOT COMPILED IN UNITY: Roslyn type-check only (Common/Tools~/compile_check). !!!
//
// 菜单 蓝白/Fonts/Build Subtitles (v5)：读 Fonts/strings_all.json（第 5 版），先按名字删掉上一次（含第 4 版）建的根物体
// （Lanbai_Poems、Lanbai_Subtitles、Lanbai_Letterbox、Lanbai_Board、Lanbai_PoemDriver），再建：
//   Lanbai_Poems/<poem>/<column>/...     世界字：天问天上的 20 个汉字（所有人一份），庄子字列 zh / zht 两套（关着）
//   Lanbai_Subtitles/Rig/<font>/Line_T, Line_B, Halo_T, Halo_B   字幕架：5 种字体 × 上下两行 + 两条行晕
//   Lanbai_Letterbox                     桌面黑边（一块 Quad，Lanbai/Letterbox；只在桌面开）
//   Lanbai_Board/Card/...                公告板的“乘车须知”设置卡（F.2）：左边设置、右边提示、两枚图钉、7 个 Interact
//   Lanbai_PoemDriver                    LanbaiPoemDriver（UdonSharp），所有字段由这里填
// 材质：字幕 5 个（每种字体一个，Lanbai/Subtitle，Underlay 开）、行晕 1 个、黑边 1 个，建在 <kit>/FontAssets/SubtitleMaterials/，
// 填色走 MaterialPropertyBlock（驱动每帧写），所以材质里没有颜色。世界字仍用 蓝白/Fonts/Build Poem Materials 的预设。
// 前提：字体资产（蓝白/Fonts/Build TMP Font Assets，第 5 版字表）和诗句材质（蓝白/Fonts/Build Poem Materials）已经建好；
// 行晕贴图 Textures/Lanbai_Scrim_Line.png 按 LanbaiScrimTextureImport 导成 Sprite。可以重复点。
// 之后：busRoot（场景里有名为 "Bus" 的物体时自动接）、设置卡挪进第 1 幕公告箱、跑 蓝白/Director/1 Generate Dispatcher、2 Wire Scene。
// The editor assembly (Lanbai.Fonts.Editor) cannot see Assembly-CSharp: LanbaiPoemDriver / LanbaiLangButton are reached
// by reflection, U# components are added through UdonSharpEditor by reflection, as in Director/Editor.
#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using TMPro;
using UnityEditor;
using UnityEngine;

namespace Lanbai.Fonts.Editor
{
    public static class LanbaiPoemBake
    {
        static readonly string[] Keys = { "zh", "zht", "ja", "en", "de" };
        static readonly string[] BoardKeys = { "zh", "zht", "ja", "en" };
        const string Menu = "蓝白/Fonts/Build Subtitles (v5)";

        // D-41：菜单先建 U# 程序资产（脚本旁边）、等 SDK 初始化完，再搭（Common/Editor/LanbaiUdonPrograms）
        [MenuItem(Menu)]
        public static void BuildMenu()
        {
            var types = new[] { FindType("LanbaiPoemDriver"), FindType("LanbaiLangButton") }.Where(t => t != null).ToArray();
            Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady(Menu, types, Build, Lanbai.Udon.LanbaiUdonPrograms.NextToScript);
        }

        public static void Build()
        {
            var report = new StringBuilder("[Lanbai Subtitles] ");
            string jsonPath = AssetDatabase.FindAssets("strings_all").Select(AssetDatabase.GUIDToAssetPath)
                .FirstOrDefault(p => p.EndsWith("strings_all.json", StringComparison.Ordinal));
            if (jsonPath == null) { Debug.LogError("[Lanbai Subtitles] strings_all.json not found (copy Fonts/ into Assets/Lanbai/Fonts/)"); return; }
            var J = (Dictionary<string, object>)MiniJson.Parse(File.ReadAllText(jsonPath));
            if (!J.ContainsKey("version") || F(J["version"]) < 5f || !J.ContainsKey("subtitles"))
            { Debug.LogError("[Lanbai Subtitles] " + jsonPath + " is not version 5 (no subtitles): sync Fonts/ from the repository"); return; }
            string kit = Path.GetDirectoryName(jsonPath).Replace('\\', '/');
            var driverType = FindType("LanbaiPoemDriver");
            var buttonType = FindType("LanbaiLangButton");
            if (driverType == null) { Debug.LogError("[Lanbai Subtitles] LanbaiPoemDriver is not compiled yet (copy Fonts/Runtime/)"); return; }
            if (buttonType != null) Lanbai.Udon.LanbaiUdonPrograms.RequireReady(Menu, driverType, buttonType);
            else Lanbai.Udon.LanbaiUdonPrograms.RequireReady(Menu, driverType);

            foreach (var n in new[] { "Lanbai_Poems", "Lanbai_Subtitles", "Lanbai_Letterbox", "Lanbai_Board", "Lanbai_PoemDriver" })
                foreach (var go in Resources.FindObjectsOfTypeAll<GameObject>().Where(g => g.name == n && g.scene.IsValid()).ToArray())
                    UnityEngine.Object.DestroyImmediate(go);

            var rig = (Dictionary<string, object>)J["subtitle_rig"];
            var mats = new SubtitleMaterials(kit, J, rig);
            int missing = 0;

            var dGo = new GameObject("Lanbai_PoemDriver");
            Undo.RegisterCreatedObjectUndo(dGo, Menu);
            var driver = AddUdonSharp(dGo, driverType);
            if (driver == null) { Debug.LogError("[Lanbai Subtitles] could not add LanbaiPoemDriver (UdonSharp editor not found): add it by hand to Lanbai_PoemDriver and run this menu again"); return; }

            string worldNote = BuildWorldText(J, driver, ref missing);
            string subNote = BuildSubtitles(J, rig, mats, driver, ref missing);
            string lbNote = BuildLetterbox(rig, mats, driver);
            string boardNote = BuildBoard(J, driver, buttonType, ref missing);

            var bus = GameObject.Find("Bus");
            if (bus != null) Set(driver, "busRoot", bus.transform);
            var expoType = FindType("LanbaiExposure");
            var expo = expoType != null ? UnityEngine.Object.FindObjectsOfType(expoType).FirstOrDefault() as Component : null;
            if (expo != null) Set(driver, "exposure", expo);
            CopyProxyToUdon(driver);

            report.Append(worldNote).Append(' ').Append(subNote).Append(' ').Append(lbNote).Append(' ').Append(boardNote).Append(' ');
            report.Append(mats.Note);
            report.Append(missing == 0 ? " Every font asset / material found." : " " + missing + " font asset(s) / material(s) / sprite(s) NOT found: build them first (蓝白/Fonts/Build TMP Font Assets, Build Poem Materials; the scrim texture import) and run this again.");
            report.Append(bus == null ? " busRoot: drag the bus root into Lanbai_PoemDriver." : " busRoot = Bus.");
            report.Append(expo == null ? " exposure: no LanbaiExposure in the scene (dEV = 0)." : " exposure = " + expo.name + ".");
            Debug.Log(report.ToString());
        }

        // ------------------------------------------------------------------------------------- world text (v4.1 path)
        // poems that keep a layout: P09 (the sky characters, everyone: the "main" objects of layout.zh) and the Zhuangzi
        // column (layout.zh / layout.zht; column_of_key says which key reads which). Keys reading the same column share
        // the objects (the driver hides a slot only when the next key uses other objects).
        static string BuildWorldText(Dictionary<string, object> J, Component driver, ref int missing)
        {
            var fills = new Dictionary<string, Vector4>();
            foreach (Dictionary<string, object> m in (List<object>)J["materials"])
                if (m.ContainsKey("fill_linear") && m["fill_linear"] is List<object> f && f.Count >= 3)
                    fills[(string)m["name"]] = new Vector4(F(f[0]), F(f[1]), F(f[2]), 1f);
            var poems = ((List<object>)J["poems"]).Cast<Dictionary<string, object>>().Where(p => p.ContainsKey("layout")).ToList();
            var root = new GameObject("Lanbai_Poems");
            Undo.RegisterCreatedObjectUndo(root, Menu);
            int N = poems.Count, K = Keys.Length;
            var pId = new string[N]; var pT0 = new float[N]; var pTgone = new float[N];
            var pAz = new float[N]; var pEl = new float[N]; var pDist = new float[N]; var pAzKey = new float[N * K];
            var slotRoot = new Transform[N * K]; var slotObjStart = new int[N * K]; var slotObjCount = new int[N * K];
            var slotScrimStart = new int[N * K]; var slotScrimCount = new int[N * K];
            var oGo = new List<GameObject>(); var oRenderer = new List<MeshRenderer>();
            var oFill = new List<Vector4>(); var oAlpha = new List<float>(); var oStart = new List<float>(); var oFocus = new List<float>();
            var oSoftEnd = new List<float>(); var oExitT = new List<float>(); var oExitS = new List<float>(); var oDrift = new List<float>();
            var oLocalY = new List<float>();
            var sRenderer = new List<SpriteRenderer>(); var sAlpha = new List<float>(); var sStart = new List<float>();
            var sExitT = new List<float>(); var sExitS = new List<float>();
            for (int p = 0; p < N; p++)
            {
                var P = poems[p];
                string id = (string)P["id"];
                pId[p] = id;
                var place = (List<object>)P["place"];
                pAz[p] = F(place[0]); pEl[p] = F(place[1]); pDist[p] = F(place[2]);
                pT0[p] = F(P["t_appear"]); pTgone[p] = F(P["t_gone"]);
                float holdS = P.ContainsKey("hold_s") && P["hold_s"] != null ? F(P["hold_s"]) : -1f;
                string exit = P.ContainsKey("exit") ? (string)P["exit"] : "";
                // default exit: drift 0.2° up / DOWN over t_exit .. t_gone; Tianwen: dim at F13 (no drift)
                float exitT = holdS >= 0f ? pT0[p] + holdS : pTgone[p] - 1.5f;
                float exitS = Mathf.Max(0.1f, pTgone[p] - exitT);
                float drift = exit.StartsWith("DOWN", StringComparison.Ordinal) ? -1f : (id == "P09_Tianwen" ? 0f : 1f);
                var poemGo = new GameObject(id);
                poemGo.transform.SetParent(root.transform, false);
                var layout = (Dictionary<string, object>)P["layout"];
                var colOf = P.ContainsKey("column_of_key") ? (Dictionary<string, object>)P["column_of_key"] : null;
                var built = new Dictionary<string, int[]>();      // column -> {objStart, objCount, scrimStart, scrimCount}
                var builtRoot = new Dictionary<string, Transform>();
                for (int k = 0; k < K; k++)
                {
                    int slot = p * K + k;
                    string col = colOf != null ? (string)colOf[Keys[k]] : "zh";
                    var lay = (Dictionary<string, object>)layout[col];
                    pAzKey[slot] = F(((List<object>)lay["anchor"])[0]);
                    if (!built.ContainsKey(col))
                    {
                        var kGo = new GameObject(col);
                        kGo.transform.SetParent(poemGo.transform, false);
                        builtRoot[col] = kGo.transform;
                        int o0 = oGo.Count;
                        foreach (Dictionary<string, object> o in (List<object>)lay["objects"])
                        {
                            string role = (string)o["role"];
                            if (role != "main" && role != "mirror") continue;                 // v5: Tianwen's sub-lines are retired
                            bool chars = id == "P09_Tianwen";
                            var parts = new List<Dictionary<string, object>>();
                            if (chars) foreach (Dictionary<string, object> ch in (List<object>)o["char_objects"]) parts.Add(ch);
                            else parts.Add(null);
                            foreach (var ch in parts)
                            {
                                string name = ch == null ? (o.ContainsKey("id") ? (string)o["id"] : role) : "ch_" + (string)ch["char"];
                                var go = new GameObject(name);
                                go.transform.SetParent(kGo.transform, false);
                                float ly = ch == null ? F(o["local_y_m"]) : F(ch["local_y_m"]);
                                float lx = ch == null ? 0f : F(ch["local_x_m"]);
                                float sy = o.ContainsKey("scale_y") ? F(o["scale_y"]) : 1f;
                                go.transform.localPosition = new Vector3(lx, ly, 0f);
                                go.transform.localScale = new Vector3(1f, sy, 1f);
                                var tmp = go.AddComponent<TextMeshPro>();
                                var fa = FindAsset<TMP_FontAsset>((string)o["tmp_asset"]);
                                if (fa != null) tmp.font = fa; else missing++;
                                var mat = FindAsset<Material>((string)o["material"]);
                                if (mat != null) tmp.fontSharedMaterial = mat; else missing++;
                                tmp.fontSize = F(o["font_size"]);
                                tmp.characterSpacing = F(o["character_spacing"]);
                                tmp.lineSpacing = F(o["line_spacing"]);
                                tmp.alignment = TextAlignmentOptions.Baseline;
                                tmp.enableWordWrapping = false;
                                tmp.overflowMode = TextOverflowModes.Overflow;
                                tmp.extraPadding = true;
                                string rich = o.ContainsKey("tmp_text_rich") ? o["tmp_text_rich"] as string : null;
                                tmp.richText = rich != null;
                                tmp.text = ch != null ? (string)ch["char"] : (rich ?? (string)o["tmp_text"]);
                                tmp.color = new Color(1f, 1f, 1f, 1f);           // vertex colour white; alpha comes from the MPB
                                go.SetActive(false);
                                oGo.Add(go); oRenderer.Add(go.GetComponent<MeshRenderer>());
                                string mname = (string)o["material"];
                                oFill.Add(fills.ContainsKey(mname) ? fills[mname] : new Vector4(1, 1, 1, 1));
                                oAlpha.Add(F(o["alpha"]));
                                float start = pT0[p];
                                if (o.ContainsKey("appear_s")) start += F(o["appear_s"]);
                                float focus = 2.5f;
                                if (ch != null) { start += F(ch["focus_delay_s"]); focus = F(ch["focus_s"]); }
                                oStart.Add(start); oFocus.Add(focus);
                                var soft = o.ContainsKey("outline_softness_anim") ? (List<object>)o["outline_softness_anim"] : null;
                                oSoftEnd.Add(soft != null ? F(soft[1]) : 0f);
                                if (o.ContainsKey("exit_t"))
                                {
                                    oExitT.Add(F(o["exit_t"])); oExitS.Add(F(o["exit_s"]));
                                    string ex = o.ContainsKey("exit") ? (string)o["exit"] : "";
                                    oDrift.Add(ex.StartsWith("down", StringComparison.Ordinal) ? -1f : 1f);
                                }
                                else { oExitT.Add(exitT); oExitS.Add(exitS); oDrift.Add(drift); }
                                oLocalY.Add(ly);
                            }
                        }
                        int s0 = sRenderer.Count;
                        foreach (Dictionary<string, object> sc in (List<object>)lay["scrims"])
                        {
                            var go = new GameObject("scrim_" + (string)sc["for_object"]);
                            go.transform.SetParent(kGo.transform, false);
                            go.transform.localPosition = new Vector3(0f, F(sc["local_y_m"]), 0.01f);
                            var ss = (List<object>)sc["sprite_scale"];
                            go.transform.localScale = new Vector3(F(ss[0]), F(ss[1]), 1f);
                            var sr = go.AddComponent<SpriteRenderer>();
                            sr.sprite = FindAsset<Sprite>(Path.GetFileNameWithoutExtension((string)sc["texture"]));
                            var sm = FindAsset<Material>((string)sc["material"]);
                            if (sm != null) sr.sharedMaterial = sm; else missing++;
                            sr.enabled = false;
                            sRenderer.Add(sr); sAlpha.Add(F(((List<object>)sc["sprite_color"])[3]));
                            sStart.Add(pT0[p] + F(sc["appear_s"])); sExitT.Add(exitT); sExitS.Add(exitS);
                        }
                        built[col] = new[] { o0, oGo.Count - o0, s0, sRenderer.Count - s0 };
                    }
                    var b = built[col];
                    slotRoot[slot] = builtRoot[col];
                    slotObjStart[slot] = b[0]; slotObjCount[slot] = b[1];
                    slotScrimStart[slot] = b[2]; slotScrimCount[slot] = b[3];
                }
            }
            Set(driver, "poemsRoot", root.transform);
            Set(driver, "pId", pId); Set(driver, "pT0", pT0); Set(driver, "pTgone", pTgone);
            Set(driver, "pAz", pAz); Set(driver, "pEl", pEl); Set(driver, "pDist", pDist); Set(driver, "pAzKey", pAzKey);
            Set(driver, "slotRoot", slotRoot); Set(driver, "slotObjStart", slotObjStart); Set(driver, "slotObjCount", slotObjCount);
            Set(driver, "slotScrimStart", slotScrimStart); Set(driver, "slotScrimCount", slotScrimCount);
            Set(driver, "oGo", oGo.ToArray()); Set(driver, "oRenderer", oRenderer.ToArray());
            Set(driver, "oFill", oFill.ToArray()); Set(driver, "oAlpha", oAlpha.ToArray()); Set(driver, "oStart", oStart.ToArray());
            Set(driver, "oFocus", oFocus.ToArray()); Set(driver, "oSoftEnd", oSoftEnd.ToArray()); Set(driver, "oExitT", oExitT.ToArray());
            Set(driver, "oExitS", oExitS.ToArray()); Set(driver, "oDrift", oDrift.ToArray()); Set(driver, "oLocalY", oLocalY.ToArray());
            Set(driver, "sRenderer", sRenderer.ToArray()); Set(driver, "sAlpha", sAlpha.ToArray()); Set(driver, "sStart", sStart.ToArray());
            Set(driver, "sExitT", sExitT.ToArray()); Set(driver, "sExitS", sExitS.ToArray());
            return string.Format("World text: {0} poem(s) ({1}), {2} text objects, {3} scrims.", N, string.Join(", ", pId), oGo.Count, sRenderer.Count);
        }

        // ------------------------------------------------------------------------------------- subtitles
        static string BuildSubtitles(Dictionary<string, object> J, Dictionary<string, object> rig, SubtitleMaterials mats, Component driver, ref int missing)
        {
            var fonts = ((List<object>)rig["fonts"]).Cast<string>().ToArray();
            int NF = fonts.Length;
            float emM = F(rig["em_m_at_1m"]);
            float fsPerM = F(rig["tmp_font_size_per_m_em"]);
            var centre = (Dictionary<string, object>)rig["em_centre_above_baseline_em"];
            var pitch = (Dictionary<string, object>)rig["line_pitch_em"];
            var track = (Dictionary<string, object>)rig["tracking_em"];
            var fontInfo = (Dictionary<string, object>)J["fonts"];

            var root = new GameObject("Lanbai_Subtitles");
            Undo.RegisterCreatedObjectUndo(root, Menu);
            var rigGo = new GameObject("Rig");
            rigGo.transform.SetParent(root.transform, false);
            var fontRoot = new GameObject[NF]; var top = new TextMeshPro[NF]; var bot = new TextMeshPro[NF];
            var topR = new MeshRenderer[NF]; var botR = new MeshRenderer[NF];
            var fCentre = new float[NF]; var fPitch = new float[NF];
            for (int f = 0; f < NF; f++)
            {
                var info = (Dictionary<string, object>)fontInfo[fonts[f]];
                bool cjk = info["cjk"] is bool cb && cb;
                string cls = cjk ? "cjk" : "latin";
                fCentre[f] = F(centre[cls]); fPitch[f] = F(pitch[cls]);
                var fr = new GameObject(fonts[f]);
                fr.transform.SetParent(rigGo.transform, false);
                fontRoot[f] = fr;
                var fa = FindAsset<TMP_FontAsset>((string)info["tmp_asset"]);
                if (fa == null) missing++;
                var mat = mats.Text(fa);
                for (int li = 0; li < 2; li++)
                {
                    var go = new GameObject(li == 0 ? "Line_T" : "Line_B");
                    go.transform.SetParent(fr.transform, false);
                    var tmp = go.AddComponent<TextMeshPro>();
                    if (fa != null) tmp.font = fa;
                    if (mat != null) tmp.fontSharedMaterial = mat;
                    tmp.fontSize = emM * fsPerM;                                    // em 1.8° at 1 m (B.2); the rig scales with depth
                    tmp.characterSpacing = F(track[cls]) * 100f;                    // TMP: 1/100 em
                    tmp.alignment = TextAlignmentOptions.Baseline;                  // centred, baseline on the transform
                    tmp.enableWordWrapping = false;
                    tmp.overflowMode = TextOverflowModes.Overflow;
                    tmp.extraPadding = true;
                    tmp.richText = false;
                    tmp.text = "";
                    tmp.color = Color.white;                                        // colour and alpha come from the MPB
                    if (li == 0) { top[f] = tmp; topR[f] = go.GetComponent<MeshRenderer>(); }
                    else { bot[f] = tmp; botR[f] = go.GetComponent<MeshRenderer>(); }
                }
                fr.SetActive(false);
            }
            // halos (B.4 #4): Textures/Lanbai_Scrim_Line.png as a Sprite, Lanbai/SubtitleHalo
            var halo = (Dictionary<string, object>)rig["halo"];
            var sprite = FindAsset<Sprite>(Path.GetFileNameWithoutExtension((string)halo["texture"]));
            if (sprite == null) missing++;
            SpriteRenderer haloT = null, haloB = null;
            for (int li = 0; li < 2; li++)
            {
                var go = new GameObject(li == 0 ? "Halo_T" : "Halo_B");
                go.transform.SetParent(rigGo.transform, false);
                var sr = go.AddComponent<SpriteRenderer>();
                sr.sprite = sprite;
                if (mats.Halo != null) sr.sharedMaterial = mats.Halo;
                sr.enabled = false;
                if (li == 0) haloT = sr; else haloB = sr;
            }
            Vector2 hs = sprite != null ? (Vector2)sprite.bounds.size : Vector2.one;
            rigGo.SetActive(false);

            // poems and pages
            var subs = ((List<object>)J["subtitles"]).Cast<Dictionary<string, object>>().ToList();
            int S = subs.Count, K = Keys.Length;
            var fade = (Dictionary<string, object>)rig["fade"];
            float fadeIn = F(fade["in"]);
            var sT0 = new float[S]; var sTend = new float[S]; var sOutLast = new float[S]; var sE = new float[S]; var sHalo = new float[S];
            var sFill = new Vector4[S]; var sHaloFill = new Vector4[S];
            var sPgStart = new int[S * K]; var sPgCount = new int[S * K];
            var pgT = new List<float>(); var pgTout = new List<float>(); var pgTgone = new List<float>(); var pgFont = new List<int>();
            var pgTop = new List<string>(); var pgBot = new List<string>(); var pgTopT = new List<float>(); var pgBotT = new List<float>();
            var pgLineIn = new List<float>(); var pgTopX = new List<float>(); var pgBotX = new List<float>();
            var pgTopW = new List<float>(); var pgBotW = new List<float>(); var pgHalfW = new List<float>();
            for (int s = 0; s < S; s++)
            {
                var R = subs[s];
                sT0[s] = F(R["t_in"]); sTend[s] = F(R["t_end"]); sOutLast[s] = F(R["out_last"]);
                sE[s] = F(R["base_bottom_el"]); sHalo[s] = F(R["halo_alpha"]);
                sFill[s] = V4(R["fill_linear"]);
                sHaloFill[s] = R.ContainsKey("halo_fill_linear") ? V4(R["halo_fill_linear"]) : Vector4.zero;
                var lineT = R.ContainsKey("line_t") ? (List<object>)R["line_t"] : null;
                float lineIn = R.ContainsKey("line_in") ? F(R["line_in"]) : fadeIn;
                var keys = (Dictionary<string, object>)R["keys"];
                for (int k = 0; k < K; k++)
                {
                    int slot = s * K + k;
                    sPgStart[slot] = pgT.Count;
                    var pages = keys.ContainsKey(Keys[k]) ? (List<object>)keys[Keys[k]] : new List<object>();
                    for (int i = 0; i < pages.Count; i++)
                    {
                        var pg = (Dictionary<string, object>)pages[i];
                        var lines = ((List<object>)pg["lines"]).Cast<string>().ToList();
                        var xs = ((List<object>)pg["x_em"]).Select(F).ToList();
                        var ws = ((List<object>)pg["width_em"]).Select(F).ToList();
                        float t = F(pg["t"]);
                        int fi = Array.IndexOf(fonts, (string)pg["font"]);
                        pgT.Add(t); pgTout.Add(F(pg["t_out"])); pgTgone.Add(F(pg["t_gone"])); pgFont.Add(Mathf.Max(0, fi));
                        bool two = lines.Count > 1;
                        pgTop.Add(two ? lines[0] : ""); pgBot.Add(lines[lines.Count - 1]);
                        pgTopX.Add(two ? xs[0] : 0f); pgBotX.Add(xs[xs.Count - 1]);
                        pgTopW.Add(two ? ws[0] : 0f); pgBotW.Add(ws[ws.Count - 1]);
                        pgHalfW.Add(F(pg["half_width_deg"]));
                        // Urlicht (line_t): each line appears with the song (the first page only); otherwise both with the page
                        bool sung = lineT != null && i == 0;
                        pgTopT.Add(sung ? F(lineT[0]) : t);
                        pgBotT.Add(sung ? F(lineT[Mathf.Min(lines.Count, lineT.Count) - 1]) : t);
                        pgLineIn.Add(sung ? lineIn : fadeIn);
                    }
                    sPgCount[slot] = pgT.Count - sPgStart[slot];
                }
            }
            Set(driver, "subRig", rigGo.transform);
            Set(driver, "subFontRoot", fontRoot); Set(driver, "subTop", top); Set(driver, "subBot", bot);
            Set(driver, "subTopR", topR); Set(driver, "subBotR", botR);
            Set(driver, "fontCentre", fCentre); Set(driver, "fontPitch", fPitch);
            Set(driver, "haloTop", haloT); Set(driver, "haloBot", haloB);
            Set(driver, "haloBaseW", hs.x); Set(driver, "haloBaseH", hs.y);
            Set(driver, "haloPadEm", F(halo["pad_w_em"])); Set(driver, "haloHEm", F(halo["h_em"]));
            Set(driver, "emM", emM);
            Set(driver, "sT0", sT0); Set(driver, "sTend", sTend); Set(driver, "sOutLast", sOutLast); Set(driver, "sE", sE); Set(driver, "sHalo", sHalo);
            Set(driver, "sFill", sFill); Set(driver, "sHaloFill", sHaloFill); Set(driver, "sPgStart", sPgStart); Set(driver, "sPgCount", sPgCount);
            Set(driver, "pgT", pgT.ToArray()); Set(driver, "pgTout", pgTout.ToArray()); Set(driver, "pgTgone", pgTgone.ToArray());
            Set(driver, "pgFont", pgFont.ToArray()); Set(driver, "pgTop", pgTop.ToArray()); Set(driver, "pgBot", pgBot.ToArray());
            Set(driver, "pgTopT", pgTopT.ToArray()); Set(driver, "pgBotT", pgBotT.ToArray()); Set(driver, "pgLineIn", pgLineIn.ToArray());
            Set(driver, "pgTopX", pgTopX.ToArray()); Set(driver, "pgBotX", pgBotX.ToArray());
            Set(driver, "pgTopW", pgTopW.ToArray()); Set(driver, "pgBotW", pgBotW.ToArray()); Set(driver, "pgHalfW", pgHalfW.ToArray());
            SetRigParams(rig, driver);
            string depthNote = BakeDepth(driver);
            return string.Format("Subtitles: {0} poems, {1} pages, {2} fonts x 2 lines + 2 halos. {3}", S, pgT.Count, NF, depthNote);
        }

        static void SetRigParams(Dictionary<string, object> rig, Component d)
        {
            var fade = (Dictionary<string, object>)rig["fade"];
            Set(d, "fadeIn", F(fade["in"]));
            var y = (Dictionary<string, object>)rig["yaw"];
            Set(d, "yawDeadMin", F(y["deadzone_min_deg"])); Set(d, "yawDeadMargin", F(y["deadzone_margin_deg"]));
            Set(d, "yawStopErr", F(y["stop_err_deg"])); Set(d, "yawStopVel", F(y["stop_vel_dps"])); Set(d, "omega", F(y["omega"]));
            Set(d, "maxSpeed", F(y["max_speed_dps"])); Set(d, "yawLimit", F(y["limit_deg"])); Set(d, "yawLimitBack", F(y["limit_back_deg"]));
            Set(d, "firstHold", F(y["first_page_hold_s"]));
            var p = (Dictionary<string, object>)rig["pitch"];
            Set(d, "upEnter", F(p["up_enter_rel"])); Set(d, "upExit", F(p["up_exit_rel"])); Set(d, "pitchHold", F(p["hold_s"]));
            Set(d, "upCap", F(p["up_cap_deg"])); Set(d, "lowBand", F(p["low_band_rel"])); Set(d, "lowAbove", F(p["low_above_deg"]));
            Set(d, "lowFloor", F(p["low_floor_deg"])); Set(d, "lowMove", F(p["low_move_deg"])); Set(d, "lowStop", F(p["low_stop_deg"]));
            var ft = (Dictionary<string, object>)rig["fast_turn"];
            Set(d, "fastDps", F(ft["dps"])); Set(d, "fastErr", F(ft["err_deg"])); Set(d, "fastOut", F(ft["out_s"]));
            Set(d, "settleDps", F(ft["settle_dps"])); Set(d, "settleS", F(ft["settle_s"])); Set(d, "fastIn", F(ft["in_s"]));
            Set(d, "headTau", F(rig["head_pos_tau_s"]));
            var dp = (Dictionary<string, object>)rig["depth"];
            var clamp = (List<object>)dp["clamp_m"];
            var fb = (Dictionary<string, object>)dp["fallback"];
            Set(d, "depthMain", F(dp["main_forward_m"])); Set(d, "depthMin", F(clamp[0])); Set(d, "depthMax", F(clamp[1]));
            Set(d, "depthNear", F(dp["near_factor"])); Set(d, "depthRate", F(dp["max_rate_mps"]));
            Set(d, "depthFbMain30", F(fb["main_within_30deg"])); Set(d, "depthFbMainOther", F(fb["main_other"]));
            Set(d, "depthFbOther", F(fb["other_seats"])); Set(d, "depthFbUnseated", F(fb["unseated"]));
            var dk = (Dictionary<string, object>)rig["desktop"];
            Set(d, "deskDist", F(dk["distance_m"])); Set(d, "deskEmFrac", F(dk["em_frac_h"]));
            Set(d, "deskBaseFrac", F(dk["baseline_frac_h"])); Set(d, "deskFov", F(dk["fov_fallback_deg"]));
            var fd = (Dictionary<string, object>)rig["face_dilate"];
            Set(d, "dilateVR", F(fd["vr"])); Set(d, "dilateDesk", F(fd["desktop"]));
        }

        // C.2: Fonts/subtitle_depth.json, copied and checked by Tools~/build_fonts.py from the bus package's table:
        // {"seats": [...23 names, BusLayout order = SetSeat index], "yaw_cells": 24, "pitch_cells": 9, "yaw0": -180,
        // "yaw_step": 15, "pitch0": -40, "pitch_step": 10, "depth_m": [seat][yaw][pitch]} (final depths in metres; cells centred).
        static string BakeDepth(Component driver)
        {
            string path = AssetDatabase.FindAssets("subtitle_depth").Select(AssetDatabase.GUIDToAssetPath)
                .FirstOrDefault(p => p.EndsWith("subtitle_depth.json", StringComparison.Ordinal));
            if (path == null) { Set(driver, "depthTable", new float[0]); return "Depth: Fonts/subtitle_depth.json not there yet: the fallbacks (C.2)."; }
            var J = (Dictionary<string, object>)MiniJson.Parse(File.ReadAllText(path));
            var D = (List<object>)J["depth_m"];
            int S = D.Count, Y = (int)F(J["yaw_cells"]), P = (int)F(J["pitch_cells"]);
            bool grid = J.ContainsKey("yaw0") && F(J["yaw0"]) == -180f && F(J["yaw_step"]) == 15f && F(J["pitch0"]) == -40f && F(J["pitch_step"]) == 10f;
            if (Y != 24 || P != 9 || !grid) { Debug.LogError("[Lanbai Subtitles] " + path + ": expected 24 yaw x 9 pitch cells, got " + Y + " x " + P); Set(driver, "depthTable", new float[0]); return "Depth: table has the wrong shape: fallbacks."; }
            var t = new float[S * Y * P];
            for (int s = 0; s < S; s++)
                for (int y = 0; y < Y; y++)
                    for (int p = 0; p < P; p++)
                        t[(s * Y + y) * P + p] = F(((List<object>)((List<object>)D[s])[y])[p]);
            Set(driver, "depthTable", t);
            return "Depth: " + S + " seats from " + path + ".";
        }

        // ------------------------------------------------------------------------------------- desktop letterbox
        static string BuildLetterbox(Dictionary<string, object> rig, SubtitleMaterials mats, Component driver)
        {
            var lb = (Dictionary<string, object>)rig["letterbox"];
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
            go.name = "Lanbai_Letterbox";
            Undo.RegisterCreatedObjectUndo(go, Menu);
            var col = go.GetComponent<Collider>();
            if (col != null) UnityEngine.Object.DestroyImmediate(col);
            var mr = go.GetComponent<MeshRenderer>();
            if (mats.Letterbox != null) mr.sharedMaterial = mats.Letterbox;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
            go.SetActive(false);
            var segs = ((List<object>)lb["segments"]).Cast<Dictionary<string, object>>().ToList();
            Set(driver, "lbQuad", go.transform); Set(driver, "lbRenderer", mr);
            Set(driver, "lbT0", segs.Select(s => F(s["t0"])).ToArray()); Set(driver, "lbT1", segs.Select(s => F(s["t1"])).ToArray());
            Set(driver, "lbAspect", F(lb["aspect"])); Set(driver, "lbCornerDeg", F(lb["corner_deg"]));
            Set(driver, "lbSlide", F(lb["slide_s"])); Set(driver, "lbDist", F(lb["distance_m"]));
            Set(driver, "lbCornerFrac", lb.ContainsKey("corner_frac") ? F(lb["corner_frac"]) : 0.5f);
            Set(driver, "lbSubsInBar", !lb.ContainsKey("subtitles_in_bar") || (lb["subtitles_in_bar"] is bool sib && sib));
            return "Letterbox: " + segs.Count + " segments (desktop only).";
        }

        // ------------------------------------------------------------------------------------- the board (F.2)
        // An A2 sheet (0.594 x 0.42 m) pinned in the act 1 notice box: settings on the left, notes on the right. Every text
        // is its own TMP; the language names are shared (each in its own script), everything else exists once per display
        // key (zh, zht, ja, en; de reads en). Interact colliders sit on the shared rows; the two brass pins move.
        // Positions are a first layout (阿白 moves the card into the box and may nudge rows; the driver only reads the pins'
        // row positions baked here).
        static string BuildBoard(Dictionary<string, object> J, Component driver, Type buttonType, ref int missing)
        {
            var board = new GameObject("Lanbai_Board");
            Undo.RegisterCreatedObjectUndo(board, Menu);
            var card = new GameObject("Card");
            card.transform.SetParent(board.transform, false);
            var ui = ((List<object>)J["ui"]).Cast<Dictionary<string, object>>().ToList();
            var v5 = ((List<object>)J["ui_v5"]).Cast<Dictionary<string, object>>().ToList();
            Color ink = new Color(0.137f, 0.153f, 0.180f, 1f);
            const float W = 0.594f, H = 0.42f, Lx = -0.27f, Rx = 0.03f;
            const float fsCjk = 0.30f, fsLat = 0.26f;                        // em 30 / 26 mm (§5.5: CJK >= 30, Latin >= 24 mm)
            float[] langY = { 0.115f, 0.072f, 0.029f, -0.014f };
            float[] modeY = { -0.105f, -0.148f, -0.191f };
            string[] langIds = { "UI/lang/zhs", "UI/lang/zht", "UI/lang/ja", "UI/lang/en" };
            var langRow = new TextMeshPro[4];
            for (int i = 0; i < 4; i++)
            {
                var row = v5.FirstOrDefault(u => (string)u["id"] == langIds[i]);
                if (row == null) { missing++; continue; }
                langRow[i] = Text(card.transform, "Lang_" + Keys[Math.Min(i, 3)], (string)row["text"], FontAssetOf(J, (string)row["font"]),
                                  new Vector3(Lx + 0.03f, langY[i], 0f), IsCjk(J, (string)row["font"]) ? fsCjk : fsLat, ink, false, 0f, ref missing);
            }
            var deRow = v5.FirstOrDefault(u => (string)u["id"] == "UI/lang/de_note");
            GameObject deNote = null;
            if (deRow != null)
            {
                deNote = Text(card.transform, "DeNote", (string)deRow["text"], FontAssetOf(J, (string)deRow["font"]),
                              new Vector3(Lx + 0.17f, langY[3], 0f), fsLat * 0.6f, ink, false, 0f, ref missing).gameObject;
                deNote.SetActive(false);
            }
            var sets = new GameObject[BoardKeys.Length];
            var line1 = new TextMeshPro[BoardKeys.Length];
            var prefix = new string[BoardKeys.Length]; var suffix = new string[BoardKeys.Length];
            var modeRow = new TextMeshPro[BoardKeys.Length * 3];
            string[] modeIds = { "UI/subs/follow", "UI/subs/stay", "UI/subs/off" };
            for (int k = 0; k < BoardKeys.Length; k++)
            {
                string bk = BoardKeys[k];
                var set = new GameObject(bk);
                set.transform.SetParent(card.transform, false);
                sets[k] = set;
                Func<string, Dictionary<string, object>> V = id => v5.FirstOrDefault(u => (string)u["id"] == id && (string)u["lang"] == bk);
                Func<Dictionary<string, object>, float> fs = r => r != null && IsCjk(J, (string)r["font"]) ? fsCjk : fsLat;
                var r0 = V("UI/subs/lang_head");
                if (r0 != null) Text(set.transform, "LangHead", (string)r0["text"], FontAssetOf(J, (string)r0["font"]), new Vector3(Lx, 0.165f, 0f), fs(r0), ink, false, 0f, ref missing);
                var r1 = V("UI/subs/head");
                if (r1 != null) Text(set.transform, "SubsHead", (string)r1["text"], FontAssetOf(J, (string)r1["font"]), new Vector3(Lx, -0.06f, 0f), fs(r1), ink, false, 0f, ref missing);
                for (int m = 0; m < 3; m++)
                {
                    var rm = V(modeIds[m]);
                    if (rm == null) { missing++; continue; }
                    modeRow[k * 3 + m] = Text(set.transform, "Mode_" + m, (string)rm["text"], FontAssetOf(J, (string)rm["font"]),
                                              new Vector3(Lx + 0.03f, modeY[m], 0f), fs(rm), ink, false, 0f, ref missing);
                }
                // right column: the countdown (only with a countdown), the late-joiner line, "only you", "fixed once we leave"
                var d1 = ui.FirstOrDefault(u => (string)u["id"] == "UI/depart/" + bk + "/1");
                var d2 = ui.FirstOrDefault(u => (string)u["id"] == "UI/depart/" + bk + "/2");
                float y = 0.165f;
                if (d1 != null)
                {
                    string text = (string)d1["text"];
                    var t1 = Text(set.transform, "Depart1", text.Replace("{0}", "--"), FontAssetOf(J, (string)d1["font"]), new Vector3(Rx, y, 0f), fs(d1) * 0.8f, ink, true, W / 2 - 0.06f, ref missing);
                    line1[k] = t1;
                    int at = text.IndexOf("{0}", StringComparison.Ordinal);
                    prefix[k] = at >= 0 ? text.Substring(0, at) : text;
                    suffix[k] = at >= 0 ? text.Substring(at + 3) : "";
                    t1.gameObject.SetActive(false);
                }
                y -= 0.07f;
                foreach (var r in new[] { d2, V("UI/subs/local"), V("UI/subs/lock") })
                {
                    if (r == null) { missing++; continue; }
                    Text(set.transform, "Note", (string)r["text"], FontAssetOf(J, (string)r["font"]), new Vector3(Rx, y, 0f), fs(r) * 0.8f, ink, true, W / 2 - 0.06f, ref missing);
                    y -= 0.075f;
                }
                set.SetActive(false);
            }
            // pins: placeholders (brass, 12 mm); their row positions are baked
            var pinL = Pin(card.transform, "Pin_Lang"); var pinM = Pin(card.transform, "Pin_Mode");
            var pinLangPos = langY.Select(y => new Vector3(Lx + 0.008f, y + 0.008f, -0.004f)).ToArray();
            var pinModePos = modeY.Select(y => new Vector3(Lx + 0.008f, y + 0.008f, -0.004f)).ToArray();
            // Interact colliders (2 m reach set on the U# behaviour by its default; F.2): 4 languages, 3 modes
            var buttons = new GameObject("Buttons");
            buttons.transform.SetParent(card.transform, false);
            string[] events = { "_LangZhs", "_LangZht", "_LangJa", "_LangEn", "_SubFollow", "_SubStay", "_SubOff" };
            float[] ys = { langY[0], langY[1], langY[2], langY[3], modeY[0], modeY[1], modeY[2] };
            int nb = 0;
            for (int i = 0; i < events.Length; i++)
            {
                var go = new GameObject("Btn" + events[i]);
                go.transform.SetParent(buttons.transform, false);
                go.transform.localPosition = new Vector3(Lx + 0.12f, ys[i] + 0.01f, -0.01f);
                var bc = go.AddComponent<BoxCollider>();
                bc.size = new Vector3(0.24f, 0.04f, 0.01f);
                if (buttonType != null)
                {
                    var b = AddUdonSharp(go, buttonType);
                    if (b != null) { Set(b, "driver", driver); Set(b, "eventName", events[i]); CopyProxyToUdon(b); nb++; }
                }
            }
            buttons.SetActive(false);                              // on with the card, off after departure (§6·12)
            card.SetActive(false);
            Set(driver, "boardCard", card); Set(driver, "boardLangSet", sets); Set(driver, "boardLine1", line1);
            Set(driver, "boardPrefix", prefix); Set(driver, "boardSuffix", suffix);
            Set(driver, "boardLangRow", langRow); Set(driver, "boardModeRow", modeRow); Set(driver, "boardDeNote", deNote);
            Set(driver, "boardPinLang", pinL); Set(driver, "boardPinMode", pinM);
            Set(driver, "boardPinLangPos", pinLangPos); Set(driver, "boardPinModePos", pinModePos);
            Set(driver, "boardButtons", buttons); Set(driver, "boardInk", ink);
            return string.Format("Board: card {0:0.000} x {1:0.000} m, {2} languages, {3} buttons.", W, H, BoardKeys.Length, nb);
        }

        static TextMeshPro Text(Transform parent, string name, string text, string fontAsset, Vector3 pos, float size, Color ink, bool wrap, float width, ref int missing)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            var tmp = go.AddComponent<TextMeshPro>();
            var fa = FindAsset<TMP_FontAsset>(fontAsset);
            if (fa != null) tmp.font = fa; else missing++;
            tmp.fontSize = size;
            tmp.richText = false;
            tmp.enableWordWrapping = wrap;
            tmp.overflowMode = TextOverflowModes.Overflow;
            tmp.alignment = wrap ? TextAlignmentOptions.TopLeft : TextAlignmentOptions.BaselineLeft;
            if (wrap && tmp.rectTransform != null) { tmp.rectTransform.pivot = new Vector2(0f, 1f); tmp.rectTransform.sizeDelta = new Vector2(width, 0.1f); }
            else if (tmp.rectTransform != null) { tmp.rectTransform.pivot = new Vector2(0f, 0.5f); tmp.rectTransform.sizeDelta = new Vector2(0.3f, 0.05f); }
            tmp.text = text;
            tmp.color = ink;
            return tmp;
        }

        static Transform Pin(Transform parent, string name)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = name;
            var c = go.GetComponent<Collider>();
            if (c != null) UnityEngine.Object.DestroyImmediate(c);
            go.transform.SetParent(parent, false);
            go.transform.localScale = new Vector3(0.012f, 0.012f, 0.006f);
            return go.transform;
        }

        // ------------------------------------------------------------------------------------- materials
        class SubtitleMaterials
        {
            public Material Halo, Letterbox;
            public string Note = "";
            readonly string _dir;
            readonly Dictionary<string, object> _rig;
            readonly Dictionary<string, Material> _text = new Dictionary<string, Material>();

            public SubtitleMaterials(string kit, Dictionary<string, object> J, Dictionary<string, object> rig)
            {
                _rig = rig;
                if (!AssetDatabase.IsValidFolder(kit + "/FontAssets")) AssetDatabase.CreateFolder(kit, "FontAssets");
                _dir = kit + "/FontAssets/SubtitleMaterials";
                if (!AssetDatabase.IsValidFolder(_dir)) AssetDatabase.CreateFolder(kit + "/FontAssets", "SubtitleMaterials");
                Halo = Make("Lanbai_SubtitleHalo", "Lanbai/SubtitleHalo", 4009);
                Letterbox = Make("Lanbai_Letterbox", "Lanbai/Letterbox", 4005);
                AssetDatabase.SaveAssets();
            }

            Material Make(string name, string shader, int queue)
            {
                var sh = Shader.Find(shader);
                if (sh == null) { Note += " Shader " + shader + " not found (copy Fonts/Shaders/)."; return null; }
                string path = _dir + "/" + name + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (m == null) { m = new Material(sh) { name = name }; AssetDatabase.CreateAsset(m, path); }
                else m.shader = sh;
                m.renderQueue = queue;
                EditorUtility.SetDirty(m);
                return m;
            }

            // one per font asset: a copy of the font asset's material (atlas, SDF ratios) on Lanbai/Subtitle, Underlay on
            public Material Text(TMP_FontAsset fa)
            {
                if (fa == null || fa.material == null) return null;
                if (_text.ContainsKey(fa.name)) return _text[fa.name];
                var sh = Shader.Find("Lanbai/Subtitle");
                if (sh == null) { Note += " Shader Lanbai/Subtitle not found (copy Fonts/Shaders/)."; return null; }
                string path = _dir + "/" + fa.name + " - Subtitle.mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (m == null) { m = new Material(fa.material) { name = fa.name + " - Subtitle" }; AssetDatabase.CreateAsset(m, path); }
                else m.CopyPropertiesFromMaterial(fa.material);
                m.shader = sh;
                var u = (Dictionary<string, object>)_rig["underlay"];
                m.SetColor("_UnderlayColor", new Color(0f, 0f, 0f, F(u["alpha"])));
                m.SetFloat("_UnderlayDilate", F(u["dilate"]));
                m.SetFloat("_UnderlaySoftness", F(u["softness"]));
                m.SetFloat("_UnderlayOffsetX", 0f);
                m.SetFloat("_UnderlayOffsetY", 0f);
                m.SetFloat("_Sharpness", F(_rig["sharpness"]));
                m.SetFloat("_FaceDilate", F(((Dictionary<string, object>)_rig["face_dilate"])["vr"]));
                m.EnableKeyword("UNDERLAY_ON");
                m.renderQueue = 4010;
                EditorUtility.SetDirty(m);
                _text[fa.name] = m;
                return m;
            }
        }

        // ------------------------------------------------------------------------------------- helpers
        static bool IsCjk(Dictionary<string, object> J, string fontKey)
        {
            var fonts = (Dictionary<string, object>)J["fonts"];
            return fonts.ContainsKey(fontKey) && ((Dictionary<string, object>)fonts[fontKey])["cjk"] is bool b && b;
        }

        static string FontAssetOf(Dictionary<string, object> J, string fontKey)
        {
            var fonts = (Dictionary<string, object>)J["fonts"];
            return fonts.ContainsKey(fontKey) ? ((Dictionary<string, object>)fonts[fontKey])["tmp_asset"] as string : null;
        }

        static Vector4 V4(object o)
        {
            var l = (List<object>)o;
            return new Vector4(F(l[0]), F(l[1]), F(l[2]), 1f);
        }

        static T FindAsset<T>(string name) where T : UnityEngine.Object
        {
            if (string.IsNullOrEmpty(name)) return null;
            foreach (var g in AssetDatabase.FindAssets(name + " t:" + typeof(T).Name))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                foreach (var a in AssetDatabase.LoadAllAssetsAtPath(path))
                    if (a is T t && a.name == name) return t;
            }
            return null;
        }

        static float F(object o)
        {
            if (o is double d) return (float)d;
            if (o is long l) return l;
            if (o is string s) return float.Parse(s, CultureInfo.InvariantCulture);
            return 0f;
        }

        static void Set(Component c, string field, object value)
        {
            var f = c.GetType().GetField(field, BindingFlags.Public | BindingFlags.Instance);
            if (f == null) { Debug.LogWarning("[Lanbai Subtitles] field " + field + " not on " + c.GetType().Name); return; }
            if (value != null && f.FieldType.IsArray && value.GetType() != f.FieldType)
            {
                // Component[] -> TextMeshPro[] etc.
                var src = (Array)value;
                var dst = Array.CreateInstance(f.FieldType.GetElementType(), src.Length);
                Array.Copy(src, dst, src.Length);
                value = dst;
            }
            f.SetValue(c, value);
            EditorUtility.SetDirty(c);
        }

        static Type FindType(string name)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType(name, false);
                if (t != null) return t;
            }
            return null;
        }

        static Component AddUdonSharp(GameObject go, Type t) { return Lanbai.Udon.LanbaiUdonPrograms.AddComponent(go, t); }

        // D-41：SDK 抛的异常不再吞掉（以前 catch {} 把 “outdated script version” 藏起来了）
        static void CopyProxyToUdon(Component proxy) { Lanbai.Udon.LanbaiUdonPrograms.CopyProxyToUdon(proxy); }
    }

    /// <summary>Minimal JSON reader (objects -> Dictionary, arrays -> List, numbers -> double / long, null, bool, string).</summary>
    public static class MiniJson
    {
        public static object Parse(string s) { int i = 0; var v = Value(s, ref i); return v; }

        static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

        static object Value(string s, ref int i)
        {
            Ws(s, ref i);
            char c = s[i];
            if (c == '{')
            {
                var d = new Dictionary<string, object>(); i++;
                Ws(s, ref i);
                if (s[i] == '}') { i++; return d; }
                while (true)
                {
                    Ws(s, ref i); string k = Str(s, ref i); Ws(s, ref i); i++;      // ':'
                    d[k] = Value(s, ref i); Ws(s, ref i);
                    if (s[i] == ',') { i++; continue; }
                    i++; return d;                                                     // '}'
                }
            }
            if (c == '[')
            {
                var l = new List<object>(); i++;
                Ws(s, ref i);
                if (s[i] == ']') { i++; return l; }
                while (true)
                {
                    l.Add(Value(s, ref i)); Ws(s, ref i);
                    if (s[i] == ',') { i++; continue; }
                    i++; return l;                                                     // ']'
                }
            }
            if (c == '"') return Str(s, ref i);
            if (s.Substring(i).StartsWith("true", StringComparison.Ordinal)) { i += 4; return true; }
            if (s.Substring(i).StartsWith("false", StringComparison.Ordinal)) { i += 5; return false; }
            if (s.Substring(i).StartsWith("null", StringComparison.Ordinal)) { i += 4; return null; }
            int a = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            string num = s.Substring(a, i - a);
            if (num.IndexOfAny(new[] { '.', 'e', 'E' }) < 0 && long.TryParse(num, NumberStyles.Integer, CultureInfo.InvariantCulture, out long lv)) return lv;
            return double.Parse(num, CultureInfo.InvariantCulture);
        }

        static string Str(string s, ref int i)
        {
            var sb = new StringBuilder(); i++;                                       // opening quote
            while (s[i] != '"')
            {
                if (s[i] == '\\')
                {
                    i++;
                    char e = s[i];
                    if (e == 'u') { sb.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; }
                    else sb.Append(e == 'n' ? '\n' : e == 't' ? '\t' : e == 'r' ? '\r' : e == 'b' ? '\b' : e == 'f' ? '\f' : e);
                }
                else sb.Append(s[i]);
                i++;
            }
            i++;
            return sb.ToString();
        }
    }
}
#endif
