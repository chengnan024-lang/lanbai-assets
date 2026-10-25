// 蓝白 · 字体套件第 4.1 版 · 摆诗的编辑器烘焙（D-33 #5，2026-10-24，总工程师）。
// !!! NOT COMPILED IN UNITY: Roslyn type-check only (Common/Tools~/compile_check). !!!
//
// 菜单 蓝白/Fonts/Build Poem Objects：读 Fonts/strings_all.json，在场景里建
//   Lanbai_Poems/<poem>/<key>/<objects>   每首诗、每个玩家键（zh, zht, ja, en, de）一套 TextMeshPro（全部关着），
//   Lanbai_Board/<key>/line1, line2        公告板的发车提示（zh, zht, ja, en），三个语言开关按钮（中 / 日 / EN）
//   Lanbai_PoemDriver                      LanbaiPoemDriver（UdonSharp），所有字段由这里填
// 前提：字体资产（蓝白/Fonts/Build TMP Font Assets）和诗句材质（蓝白/Fonts/Build Poem Materials）已经建好；
// 衬底贴图按 LanbaiScrimTextureImport 导成 Sprite。可以重复点：先按名字删掉上一次建的三个根物体。
// 之后：把 LanbaiPoemDriver.busRoot 拖成车的根（或在场景里有名为 "Bus" 的物体时自动接），公告板挪到站牌的板面上，
// 再跑 蓝白/Director/1 Generate Dispatcher、2 Wire Scene（它有 LanbaiTick / LanbaiActivate / LanbaiWindow）。
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

        // D-41：菜单先建 U# 程序资产（脚本旁边）、等 SDK 初始化完，再搭（Common/Editor/LanbaiUdonPrograms）
        [MenuItem("蓝白/Fonts/Build Poem Objects (v4.1 runtime)")]
        public static void BuildMenu()
        {
            var types = new[] { FindType("LanbaiPoemDriver"), FindType("LanbaiLangButton") }.Where(t => t != null).ToArray();
            Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("蓝白/Fonts/Build Poem Objects (v4.1 runtime)", types, Build, Lanbai.Udon.LanbaiUdonPrograms.NextToScript);
        }

        public static void Build()
        {
            var report = new StringBuilder("[Lanbai Poems] ");
            string jsonPath = AssetDatabase.FindAssets("strings_all").Select(AssetDatabase.GUIDToAssetPath)
                .FirstOrDefault(p => p.EndsWith("strings_all.json", StringComparison.Ordinal));
            if (jsonPath == null) { Debug.LogError("[Lanbai Poems] strings_all.json not found (copy Fonts/ into Assets/Lanbai/Fonts/)"); return; }
            var J = (Dictionary<string, object>)MiniJson.Parse(File.ReadAllText(jsonPath));
            var driverType = FindType("LanbaiPoemDriver");
            var buttonType = FindType("LanbaiLangButton");
            if (driverType == null) { Debug.LogError("[Lanbai Poems] LanbaiPoemDriver is not compiled yet (copy Fonts/Runtime/)"); return; }
            if (buttonType != null) Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Fonts/Build Poem Objects", driverType, buttonType);
            else Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Fonts/Build Poem Objects", driverType);

            foreach (var n in new[] { "Lanbai_Poems", "Lanbai_Board", "Lanbai_PoemDriver" })
                foreach (var go in Resources.FindObjectsOfTypeAll<GameObject>().Where(g => g.name == n && g.scene.IsValid()).ToArray())
                    UnityEngine.Object.DestroyImmediate(go);

            // fills: material name -> linear fill (materials[] of strings_all.json)
            var fills = new Dictionary<string, Vector4>();
            foreach (Dictionary<string, object> m in (List<object>)J["materials"])
                if (m.ContainsKey("fill_linear") && m["fill_linear"] is List<object> f && f.Count >= 3)
                    fills[(string)m["name"]] = new Vector4(F(f[0]), F(f[1]), F(f[2]), 1f);

            var root = new GameObject("Lanbai_Poems");
            var dGo = new GameObject("Lanbai_PoemDriver");
            Undo.RegisterCreatedObjectUndo(root, "Lanbai poems");
            Undo.RegisterCreatedObjectUndo(dGo, "Lanbai poems");

            var poems = (List<object>)J["poems"];
            int N = poems.Count, K = Keys.Length;
            var pId = new string[N]; var pT0 = new float[N]; var pTgone = new float[N];
            var pAz = new float[N]; var pEl = new float[N]; var pDist = new float[N]; var pAzKey = new float[N * K];
            var pFixed = new bool[N]; var pGazeDeg = new float[N];
            var slotRoot = new Transform[N * K]; var slotObjStart = new int[N * K]; var slotObjCount = new int[N * K];
            var slotScrimStart = new int[N * K]; var slotScrimCount = new int[N * K];
            var slotBlkEl0 = new float[N * K]; var slotBlkEl1 = new float[N * K];
            var oGo = new List<GameObject>(); var oRenderer = new List<MeshRenderer>(); var oTmp = new List<TextMeshPro>();
            var oFill = new List<Vector4>(); var oAlpha = new List<float>(); var oStart = new List<float>(); var oFocus = new List<float>();
            var oSoftEnd = new List<float>(); var oExitT = new List<float>(); var oExitS = new List<float>(); var oDrift = new List<float>();
            var oLocalY = new List<float>(); var oCueStart = new List<int>(); var oCueCount = new List<int>(); var cueT = new List<float>();
            var cueText = new List<string>(); var oHiddenText = new List<string>();
            var sRenderer = new List<SpriteRenderer>(); var sAlpha = new List<float>(); var sStart = new List<float>();
            var sExitT = new List<float>(); var sExitS = new List<float>();
            int missing = 0;

            for (int p = 0; p < N; p++)
            {
                var P = (Dictionary<string, object>)poems[p];
                string id = (string)P["id"];
                pId[p] = id;
                var place = (List<object>)P["place"];
                pAz[p] = F(place[0]); pEl[p] = F(place[1]); pDist[p] = F(place[2]);
                pT0[p] = F(P["t_appear"]); pTgone[p] = F(P["t_gone"]);
                pFixed[p] = P.ContainsKey("mirror") && P["mirror"] is bool mb && mb || P.ContainsKey("picture");
                pGazeDeg[p] = P.ContainsKey("gaze_deg") ? F(P["gaze_deg"]) : 50f;
                float holdS = P.ContainsKey("hold_s") && P["hold_s"] != null ? F(P["hold_s"]) : -1f;
                string exit = P.ContainsKey("exit") ? (string)P["exit"] : "";
                // default exit: drift 0.2° up / DOWN over t_exit .. t_gone; Tianwen: dim at F13; Urlicht: fade in the last 1.5 s
                float exitT = holdS >= 0f ? pT0[p] + holdS : pTgone[p] - 1.5f;
                float exitS = Mathf.Max(0.1f, pTgone[p] - exitT);
                float drift = exit.StartsWith("DOWN", StringComparison.Ordinal) ? -1f : (id == "P09_Tianwen" || id == "P04b_Urlicht" ? 0f : 1f);
                var poemGo = new GameObject(id);
                poemGo.transform.SetParent(root.transform, false);
                var layout = (Dictionary<string, object>)P["layout"];
                for (int k = 0; k < K; k++)
                {
                    int slot = p * K + k;
                    var lay = (Dictionary<string, object>)layout[Keys[k]];
                    var anchor = (List<object>)lay["anchor"];
                    pAzKey[slot] = F(anchor[0]);
                    var blk = (Dictionary<string, object>)lay["block"];
                    slotBlkEl0[slot] = F(((List<object>)blk["el"])[0]);
                    slotBlkEl1[slot] = F(((List<object>)blk["el"])[1]);
                    var kGo = new GameObject(Keys[k]);
                    kGo.transform.SetParent(poemGo.transform, false);
                    slotRoot[slot] = kGo.transform;
                    slotObjStart[slot] = oGo.Count;
                    var lineCues = P.ContainsKey("line_cues_by_shown") ? (Dictionary<string, object>)P["line_cues_by_shown"] : null;
                    string shown = (string)lay["shown"];
                    foreach (Dictionary<string, object> o in (List<object>)lay["objects"])
                    {
                        bool tianwenMain = id == "P09_Tianwen" && (string)o["role"] == "main";
                        var parts = new List<Dictionary<string, object>>();
                        if (tianwenMain)
                            foreach (Dictionary<string, object> ch in (List<object>)o["char_objects"]) parts.Add(ch);
                        else
                            parts.Add(null);
                        foreach (var ch in parts)
                        {
                            string name = ch == null ? (o.ContainsKey("id") ? (string)o["id"] : (string)o["role"]) : "ch_" + (string)ch["char"];
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
                            oGo.Add(go); oRenderer.Add(go.GetComponent<MeshRenderer>()); oTmp.Add(tmp);
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
                            // Urlicht: the lines follow their cues (line_cues_by_shown[shown])
                            if (lineCues != null && lineCues.ContainsKey(shown) && ch == null && (string)o["role"] == "main")
                            {
                                oCueStart.Add(cueT.Count);
                                var lc = (List<object>)lineCues[shown];
                                foreach (Dictionary<string, object> c in lc) cueT.Add(F(c["t"]));
                                oCueCount.Add(lc.Count);
                                // 阿白 2026-10-25（FromLocal/full_preview，总工程师收）：Udon 里没有 TMP maxVisibleLines，所以每个
                                // cue 烘一段文字：已经到的行照常，还没到的行留在排版里、用 <alpha=#00> 画成透明（行位不跳）。
                                // 每行自己的 <space=…> 标签在行内，按 \n 切开不会切断标签
                                tmp.richText = true;
                                string original = tmp.text;
                                var lines = original.Split('\n');
                                oHiddenText.Add("<alpha=#00>" + original);
                                for (int c = 0; c < lc.Count; c++)
                                {
                                    int visible = Math.Min(c + 1, lines.Length);
                                    cueText.Add(string.Join("\n", lines.Take(visible).ToArray()) +
                                                (visible < lines.Length ? "<alpha=#00>\n" + string.Join("\n", lines.Skip(visible).ToArray()) : ""));
                                }
                                tmp.text = oHiddenText[oHiddenText.Count - 1];
                            }
                            else { oCueStart.Add(0); oCueCount.Add(0); oHiddenText.Add(""); }
                        }
                    }
                    slotObjCount[slot] = oGo.Count - slotObjStart[slot];
                    // scrims
                    slotScrimStart[slot] = sRenderer.Count;
                    foreach (Dictionary<string, object> sc in (List<object>)lay["scrims"])
                    {
                        var go = new GameObject("scrim_" + (string)sc["for_object"]);
                        go.transform.SetParent(kGo.transform, false);
                        go.transform.localPosition = new Vector3(0f, F(sc["local_y_m"]), 0.01f);     // behind the text (+Z away)
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
                    slotScrimCount[slot] = sRenderer.Count - slotScrimStart[slot];
                }
            }

            // notice board (D-31): line 1 = prefix + seconds + suffix, line 2 static; three switch buttons
            var board = new GameObject("Lanbai_Board");
            Undo.RegisterCreatedObjectUndo(board, "Lanbai poems");
            var ui = (List<object>)J["ui"];
            var boardRoot = new GameObject[BoardKeys.Length]; var boardLine1 = new TextMeshPro[BoardKeys.Length];
            var boardPrefix = new string[BoardKeys.Length]; var boardSuffix = new string[BoardKeys.Length];
            for (int k = 0; k < BoardKeys.Length; k++)
            {
                var kGo = new GameObject(BoardKeys[k]);
                kGo.transform.SetParent(board.transform, false);
                boardRoot[k] = kGo;
                for (int li = 1; li <= 2; li++)
                {
                    var row = ui.Cast<Dictionary<string, object>>().FirstOrDefault(u => (string)u["id"] == "UI/depart/" + BoardKeys[k] + "/" + li);
                    if (row == null) continue;
                    var go = new GameObject("line" + li);
                    go.transform.SetParent(kGo.transform, false);
                    go.transform.localPosition = new Vector3(0f, li == 1 ? 0.06f : 0f, 0f);
                    var tmp = go.AddComponent<TextMeshPro>();
                    var fa = FindAsset<TMP_FontAsset>(FontAssetOf(J, (string)row["font"]));
                    if (fa != null) tmp.font = fa; else missing++;
                    tmp.fontSize = 0.4f;                                   // placeholder: the bus / sign kit sets the board's type
                    tmp.alignment = TextAlignmentOptions.Center;
                    tmp.enableWordWrapping = false;
                    string text = (string)row["text"];
                    tmp.text = text.Replace("{0}", "--");
                    if (li == 1)
                    {
                        boardLine1[k] = tmp;
                        int at = text.IndexOf("{0}", StringComparison.Ordinal);
                        boardPrefix[k] = at >= 0 ? text.Substring(0, at) : text;
                        boardSuffix[k] = at >= 0 ? text.Substring(at + 3) : "";
                    }
                }
                kGo.SetActive(false);
            }

            // U# 1.x compiles only scripts that have a program asset (D-33 review #1): the menu made them next to the scripts and waited (D-41)
            var driver = AddUdonSharp(dGo, driverType);
            if (driver == null) { Debug.LogError("[Lanbai Poems] could not add LanbaiPoemDriver (UdonSharp editor not found): add it by hand to Lanbai_PoemDriver and run this menu again"); return; }
            Set(driver, "poemsRoot", root.transform);
            var bus = GameObject.Find("Bus");
            if (bus != null) Set(driver, "busRoot", bus.transform);
            Set(driver, "pId", pId); Set(driver, "pT0", pT0); Set(driver, "pTgone", pTgone);
            Set(driver, "pAz", pAz); Set(driver, "pEl", pEl); Set(driver, "pDist", pDist); Set(driver, "pAzKey", pAzKey); Set(driver, "pFixed", pFixed); Set(driver, "pGazeDeg", pGazeDeg);
            Set(driver, "slotRoot", slotRoot); Set(driver, "slotObjStart", slotObjStart); Set(driver, "slotObjCount", slotObjCount);
            Set(driver, "slotScrimStart", slotScrimStart); Set(driver, "slotScrimCount", slotScrimCount);
            Set(driver, "oGo", oGo.ToArray()); Set(driver, "oRenderer", oRenderer.ToArray()); Set(driver, "oTmp", oTmp.ToArray());
            Set(driver, "oFill", oFill.ToArray()); Set(driver, "oAlpha", oAlpha.ToArray()); Set(driver, "oStart", oStart.ToArray());
            Set(driver, "oFocus", oFocus.ToArray()); Set(driver, "oSoftEnd", oSoftEnd.ToArray()); Set(driver, "oExitT", oExitT.ToArray());
            Set(driver, "oExitS", oExitS.ToArray()); Set(driver, "oDrift", oDrift.ToArray()); Set(driver, "oLocalY", oLocalY.ToArray());
            Set(driver, "oCueStart", oCueStart.ToArray()); Set(driver, "oCueCount", oCueCount.ToArray()); Set(driver, "cueT", cueT.ToArray());
            Set(driver, "cueText", cueText.ToArray()); Set(driver, "oHiddenText", oHiddenText.ToArray());
            Set(driver, "sRenderer", sRenderer.ToArray()); Set(driver, "sAlpha", sAlpha.ToArray()); Set(driver, "sStart", sStart.ToArray());
            Set(driver, "sExitT", sExitT.ToArray()); Set(driver, "sExitS", sExitS.ToArray());
            Set(driver, "slotBlkEl0", slotBlkEl0); Set(driver, "slotBlkEl1", slotBlkEl1);
            string seatsNote = BakeSeats(driver);
            Set(driver, "boardRoot", boardRoot); Set(driver, "boardLine1", boardLine1);
            Set(driver, "boardPrefix", boardPrefix); Set(driver, "boardSuffix", boardSuffix);
            CopyProxyToUdon(driver);

            // the three switch buttons (中 / 日 / EN): a label + a BoxCollider + LanbaiLangButton
            var buttons = new GameObject("Buttons");
            buttons.transform.SetParent(board.transform, false);
            // 阿白 2026-10-25：TMP 要先 Awake 才能设字体，在关着的父物体下建会空引用；建的时候开着，建完再关
            buttons.SetActive(true);
            Set(driver, "boardButtons", buttons);
            CopyProxyToUdon(driver);
            if (buttonType != null)
            {
                string[] labels = { "UI/lang/zh", "UI/lang/ja", "UI/lang/en" };
                string[] events = { "_LangZh", "_LangJa", "_LangEn" };
                for (int i = 0; i < 3; i++)
                {
                    var row = ui.Cast<Dictionary<string, object>>().First(u => (string)u["id"] == labels[i]);
                    var go = new GameObject("Lang_" + events[i].Substring(5));
                    go.transform.SetParent(buttons.transform, false);
                    go.transform.localPosition = new Vector3(-0.12f + 0.12f * i, -0.10f, 0f);
                    var tmp = go.AddComponent<TextMeshPro>();
                    var fa = FindAsset<TMP_FontAsset>(FontAssetOf(J, (string)row["font"]));
                    if (fa != null) tmp.font = fa; else missing++;
                    tmp.text = (string)row["text"];
                    tmp.fontSize = 0.5f;
                    tmp.alignment = TextAlignmentOptions.Center;
                    var bc = go.AddComponent<BoxCollider>();
                    bc.size = new Vector3(0.1f, 0.08f, 0.02f);
                    var b = AddUdonSharp(go, buttonType);
                    if (b != null) { Set(b, "driver", driver); Set(b, "eventName", events[i]); CopyProxyToUdon(b); }
                }
            }
            buttons.SetActive(false);                              // on with the countdown, off after departure
            report.AppendFormat("{0} poems x {1} keys, {2} text objects, {3} scrims, board {4} languages; ", N, K, oGo.Count, sRenderer.Count, BoardKeys.Length);
            report.Append(missing == 0 ? "every font asset / material found." : missing + " font asset(s) / material(s) NOT found: build them first (蓝白/Fonts/Build TMP Font Assets, Build Poem Materials) and run this again.");
            report.Append(bus == null ? " busRoot: drag the bus root into Lanbai_PoemDriver." : " busRoot = Bus.");
            report.Append(" " + seatsNote);
            Debug.Log(report.ToString());
        }

        // D-37: the per-seat positions solved offline (Fonts/seat_positions.json, written by Tools~/build_fonts.py from the
        // bus's seat grids): {seats[], eyes[[x,y,z]], poems[], keys[], facings, default[s][p][k] = [az, el, blocked],
        // gaze[s][p][k][f] = [az, el, blocked] | null (poems that never move)}.
        static string BakeSeats(Component driver)
        {
            string path = AssetDatabase.FindAssets("seat_positions").Select(AssetDatabase.GUIDToAssetPath)
                .FirstOrDefault(p => p.EndsWith("seat_positions.json", StringComparison.Ordinal));
            if (path == null) return "Seat positions: Fonts/seat_positions.json not found: every seat uses D-33's default positions.";
            var J = (Dictionary<string, object>)MiniJson.Parse(File.ReadAllText(path));
            var seats = (List<object>)J["seats"];
            var eyesJ = (List<object>)J["eyes"];
            int S = seats.Count, Pn = ((List<object>)J["poems"]).Count, K = ((List<object>)J["keys"]).Count, Fc = (int)F(J["facings"]);
            var eyes = new Vector3[S];
            for (int s = 0; s < S; s++) { var e = (List<object>)eyesJ[s]; eyes[s] = new Vector3(F(e[0]), F(e[1]), F(e[2])); }
            var dAz = new float[S * Pn * K]; var dEl = new float[S * Pn * K];
            var gAz = new float[S * Pn * K * Fc]; var gEl = new float[S * Pn * K * Fc];
            var D = (List<object>)J["default"]; var G = (List<object>)J["gaze"];
            for (int s = 0; s < S; s++)
                for (int p = 0; p < Pn; p++)
                    for (int k = 0; k < K; k++)
                    {
                        int i = (s * Pn + p) * K + k;
                        var d = (List<object>)((List<object>)((List<object>)D[s])[p])[k];
                        dAz[i] = F(d[0]); dEl[i] = F(d[1]);
                        var gl = ((List<object>)((List<object>)G[s])[p])[k] as List<object>;
                        for (int f = 0; f < Fc; f++)
                        {
                            var gf = gl != null ? (List<object>)gl[f] : d;
                            gAz[i * Fc + f] = F(gf[0]); gEl[i * Fc + f] = F(gf[1]);
                        }
                    }
            Set(driver, "seatEye", eyes);
            Set(driver, "seatDefAz", dAz); Set(driver, "seatDefEl", dEl);
            Set(driver, "seatGazeAz", gAz); Set(driver, "seatGazeEl", gEl);
            return "Seat positions: " + S + " seats x " + Pn + " poems x " + K + " keys (+ " + Fc + " facings) from " + path + ".";
        }

        static string FontAssetOf(Dictionary<string, object> J, string fontKey)
        {
            var fonts = (Dictionary<string, object>)J["fonts"];
            return fonts.ContainsKey(fontKey) ? ((Dictionary<string, object>)fonts[fontKey])["tmp_asset"] as string : null;
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
            if (f == null) { Debug.LogWarning("[Lanbai Poems] field " + field + " not on " + c.GetType().Name); return; }
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
