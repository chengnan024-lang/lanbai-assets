// ═══════════════════════════════════════════════════════════════════
//  蓝白 · Udon 挂载：旅程时间轴（时间表、天空参数、诗）、出发按钮、座位
// ═══════════════════════════════════════════════════════════════════
using System;
using System.Collections.Generic;
using UdonSharp;
using UdonSharpEditor;
using UnityEditor;
using UnityEngine;
using VRC.Udon;
using VRC.SDKBase;
using Lanbai;

namespace Lanbai.EditorTools
{
    public static class LB_Udon
    {
        const string PROGRAM_DIR = "Assets/Lanbai/UdonPrograms";
        static readonly Type[] SCRIPTS = { typeof(LB_Journey), typeof(LB_DepartButton), typeof(LB_Seat) };

        // ── 时间表（秒）：下标 = LB_Journey 的幕，全部由乐句标签推出来（LB_Cues） ──
        //   0 站牌 1 夜路 2 离地(U3) 3 触手之门(U7) 4 门内(U9) 5 投入(U12) 6 晨(F0) 7 海(F2) 8 暮(F9b 出海) 9 蓝时·星海(F12)
        //   10 白(F16) 11 假醒(末乐章结束 + 5 秒静默) 12 醒(假醒 + 71.5) 13 结束（醒之后一直停在站台，不自动重开）
        public const float FALSE_LEN = 62f + 6.5f + 3f;     // 假醒：第 62 秒第二次白（6.5 秒擦到白 + 保持 3 秒）→ 硬切到醒
        public const float WAKE_HOLD = 480f;                // 醒之后 8 分钟（天边那一线蓝变亮）；之后仍停在醒
        public static readonly float[] SEG = SegTimes();

        public static float[] SegTimes()
        {
            float fals = LB_Cues.FEnd() + LB_Cues.WHITE_SILENCE, wake = fals + FALSE_LEN;
            return new[] { 0f, 0f, LB_Cues.Ut(3), LB_Cues.Ut(7), LB_Cues.Ut(9), LB_Cues.Ut(12), LB_Cues.Ft(0), LB_Cues.Ft(2),
                           LB_Cues.Xt(LB_Cues.X_F9B), LB_Cues.Ft(12), LB_Cues.Ft(16), fals, wake, wake + WAKE_HOLD };
        }

        public static bool CheckReady(out string message)
        {
            message = null;
            if (EditorApplication.isCompiling || EditorApplication.isUpdating) { message = "Unity 还在编译 / 导入。等它停下来再点一次。"; return false; }
            bool created = false;
            foreach (var t in SCRIPTS)
            {
                if (UdonSharpEditorUtility.GetUdonSharpProgramAsset(t) != null) continue;
                var script = FindScript(t);
                if (script == null) { message = "找不到脚本 " + t.Name + ".cs（Assets/Lanbai/Scripts 完整吗？Console 里有红字吗？）"; return false; }
                LB_Builder.EnsureFolder(PROGRAM_DIR);
                string path = AssetDatabase.GenerateUniqueAssetPath(PROGRAM_DIR + "/" + t.Name + ".asset");
                var pa = ScriptableObject.CreateInstance<UdonSharpProgramAsset>();
                pa.sourceCsScript = script;
                pa.ScriptVersion = UdonSharpProgramVersion.CurrentVersion;
                AssetDatabase.CreateAsset(pa, path);
                created = true;
            }
            if (created) { AssetDatabase.SaveAssets(); AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport); }
            bool needCompile = created;
            try { needCompile |= UdonSharpProgramAsset.IsAnyProgramAssetSourceDirty(); } catch (Exception) { needCompile = true; }
            foreach (var t in SCRIPTS)
            {
                var pa = UdonSharpEditorUtility.GetUdonSharpProgramAsset(t);
                if (pa == null || pa.CompiledVersion < UdonSharpProgramVersion.CurrentVersion) needCompile = true;
            }
            if (needCompile)
            {
                EditorUtility.DisplayProgressBar("蓝白", "编译 UdonSharp 脚本…", 0.03f);
                UdonSharp.Compiler.UdonSharpCompilerV1.CompileSync();
            }
            if (UdonSharpProgramAsset.AnyUdonSharpScriptHasError()) { message = "UdonSharp 脚本编译出错了。Console 里的红字截图发给 Claude。"; return false; }
            foreach (var t in SCRIPTS)
            {
                var pa = UdonSharpEditorUtility.GetUdonSharpProgramAsset(t);
                if (pa == null) { message = "UdonSharp 程序资产还没准备好（" + t.Name + "）。等转圈停下再点一次。"; return false; }
                if (pa.ScriptVersion < UdonSharpProgramVersion.CurrentVersion) pa.ScriptVersion = UdonSharpProgramVersion.CurrentVersion;
                if (pa.CompiledVersion < UdonSharpProgramVersion.CurrentVersion) { message = "UdonSharp 脚本还没编译成功（" + t.Name + "）。"; return false; }
            }
            return true;
        }

        static MonoScript FindScript(Type t)
        {
            foreach (var guid in AssetDatabase.FindAssets("t:MonoScript " + t.Name))
            {
                var ms = AssetDatabase.LoadAssetAtPath<MonoScript>(AssetDatabase.GUIDToAssetPath(guid));
                if (ms != null && ms.GetClass() == t) return ms;
            }
            return null;
        }

        static T Add<T>(GameObject go) where T : UdonSharpBehaviour { return go.AddUdonSharpComponent<T>(); }

        static void Commit(UdonSharpBehaviour b, string interactText = null, float proximity = -1f)
        {
#pragma warning disable 618
            UdonSharpEditorUtility.CopyProxyToUdon(b);
#pragma warning restore 618
            var ub = UdonSharpEditorUtility.GetBackingUdonBehaviour(b);
            if (ub != null)
            {
                if (interactText != null) ub.interactText = interactText;
                if (proximity > 0f) ub.proximity = proximity;
                var attr = (UdonBehaviourSyncModeAttribute)Attribute.GetCustomAttribute(b.GetType(), typeof(UdonBehaviourSyncModeAttribute));
                if (attr != null)
                {
                    if (attr.behaviourSyncMode == BehaviourSyncMode.None || attr.behaviourSyncMode == BehaviourSyncMode.NoVariableSync) ub.SyncMethod = Networking.SyncType.None;
                    else if (attr.behaviourSyncMode == BehaviourSyncMode.Manual) ub.SyncMethod = Networking.SyncType.Manual;
                    else if (attr.behaviourSyncMode == BehaviourSyncMode.Continuous) ub.SyncMethod = Networking.SyncType.Continuous;
                }
                EditorUtility.SetDirty(ub);
            }
            EditorUtility.SetDirty(b);
        }

        // ═════════════════════════════════════════════════════════════
        public static void Wire(Transform root)
        {
            var R = LB_Builder.R;
            var sys = LB_Builder.Child(root, "Systems", Vector3.zero);
            var jGo = LB_Builder.Child(sys.transform, "Journey", Vector3.zero);
            var j = Add<LB_Journey>(jGo);

            j.segStart = (float[])SEG.Clone();
            j.cueU = LB_Cues.UT(); j.cueF = LB_Cues.FT(); j.cueX = LB_Cues.XT();
            Motion(j);
            j.busRoot = R.busRoot.transform;
            j.busRenderers = R.busRenderers.ToArray();
            var gl = new List<Renderer>(R.glassList); gl.AddRange(R.busLabels);   // 玻璃和车上的字：淡到一半就关掉
            j.glassRenderers = gl.ToArray();
            j.doorPivot = R.doorPivot; j.doorPivot2 = R.doorPivot2; j.pendant = R.pendant; j.fan = R.fan; j.wheels = R.wheels.ToArray();
            j.cabinLights = R.cabinLights.ToArray(); j.cabinTubes = R.cabinTubes.ToArray(); j.cabinLightIntensity = LB_Builder.CABIN_LIGHT; j.cabinTubeEmission = 4.5f;
            j.spawnInBus = R.spawnInBus;
            j.busMin = R.busMin; j.busMax = R.busMax;
            j.heroEye = HERO_EYE;
            j.flickerT = (float[])LB_Cues.FLICKER_T.Clone(); j.flickerDur = (float[])LB_Cues.FLICKER_DUR.Clone();
            j.flickerLevel = (float[])LB_Cues.FLICKER_LEVEL.Clone(); j.flickerMask = (int[])LB_Cues.FLICKER_MASK.Clone();
            j.roadGroup = R.roadGroup; j.roadRoot = R.roadRoot; j.roadTiles = R.roadTiles.ToArray();
            j.tileLen = LB_Builder.TILE_LEN; j.roadSpeed = 10f;
            j.tileLamps = R.tileLamps.ToArray(); j.roadPatch = R.roadPatch; j.roadSurfaces = R.roadSurfaces.ToArray();
            j.lightSea = R.lightSea; j.cloudSea = R.cloudSea; j.truck = R.truck;
            j.groundRenderers = R.groundRenderers.ToArray(); j.rainIdle = R.rainIdle; j.rainMoving = R.rainMoving; j.rainHeadlight = R.rainHeadlight; j.lampFlipHeight = 17f;
            j.gateGroup = R.gateGroup; j.gateRoot = R.gateRoot; j.tentacleMaterial = LB_Mats.Tentacle; j.riftGlow = R.riftGlow;
            j.skyDome = R.skyDome; j.clouds = R.clouds.ToArray(); j.cloudHeight = LB_Builder.CLOUD_H; j.skyGroup = R.skyGroup;
            j.seaA = R.seaA; j.seaB = R.seaB; j.seaARenderer = R.seaAR; j.seaBRenderer = R.seaBR;
            j.deepGroup = R.deepGroup; j.motes = new Transform[0]; j.sun = R.sun; j.cloudMaterial = LB_Mats.Cloud; j.godRays = R.godRays;
            FillSky(j);
            // 第 9 幕十三面镜（占位：旧的海面）：穿越时刻来自标签（公比 r 由 F13–F16 解出，吸附到强拍）；上升速度 3 → 40 m/s
            j.starCross = (float[])LB_Cues.MIRRORS.Clone();
            j.starSpeed = new float[j.starCross.Length];
            for (int i = 0; i < j.starSpeed.Length; i++) j.starSpeed[i] = 3f * Mathf.Pow(40f / 3f, Mathf.Min(i, 11) / 11f);
            j.meteors = R.meteors; j.plankton = R.plankton; j.milkyWayNormal = new Vector3(0.3f, 0.6f, 0.74f); j.milkyWayTurn = 5f;
            j.ppNight = R.ppNight; j.ppGate = R.ppGate; j.ppDawn = R.ppDawn; j.ppDusk = R.ppDusk; j.ppStars = R.ppStars; j.ppDeep = R.ppDeep; j.ppWhite = R.ppWhite; j.ppBlack = R.ppBlack;
            j.whiteEv = 11f; j.blackEv = 14f;
            // 圣经的 15 套（LB_Grades 的槽）：profile 都在就用它们
            j.useGrades = LB_Grades.Ready(); j.ppBase = R.ppBase; j.ppGrade = R.ppGrades; j.gradePE = LB_Grades.PostExposures(); j.ppHelper = R.ppHelpers; j.expoTarget = 4f;
            j.radio = R.radio; j.radioFilter = R.radioFilter; j.radioHighPass = R.radioHighPass; j.radioNoise = R.radioNoise; j.world = R.world; j.boom = R.boom; j.splash = R.splash; j.insects = R.insects; j.rain = R.rain;
            j.urlicht = Music("LB_Urlicht"); j.finale = Music("LB_Finale");
            j.urlichtAt = LB_Cues.T_URLICHT; j.urlichtFadeA = LB_Cues.URLICHT_FADE_A; j.urlichtFadeB = LB_Cues.URLICHT_FADE_B;
            j.finaleAt = LB_Cues.F_OFFSET; j.finaleStart = LB_Cues.FINALE_START; j.finaleFadeA = LB_Cues.FINALE_FADE_A; j.finaleFadeB = LB_Cues.FINALE_FADE_B;
            j.musicVolume = 0.85f; j.radioVolume = 0.55f;
            // 电平（ffmpeg volumedetect 的平均电平）：LB_Noise −24.3 dBFS、Urlicht U0–U3 −37.8 → 噪音文件比音乐响 13.5 dB；
            // 入水 / 出水的声音比音乐低 24 dB：LB_Splash −18.3、末乐章 F2 附近 −35.6 → 再压 17.3 dB
            j.noiseTrimDb = -37.8f + 24.3f;
            j.splashVolume = j.musicVolume * Mathf.Pow(10f, (-24f - 35.6f + 18.3f) / 20f);
            j.insectsVolume = 0.35f;
            j.poem = R.poem; j.poemRoot = R.poem.transform;
            FillPoem(j);
            Commit(j);

            var db = Add<LB_DepartButton>(R.departButton);
            db.journey = j; db.click = R.click;
            Commit(db, "出发", 2.5f);

            foreach (var s in R.seats)
            {
                var seat = Add<LB_Seat>(s.gameObject);
                seat.station = s.GetComponent<VRC.SDK3.Components.VRCStation>();
                Commit(seat, "坐下", 2f);
            }
        }

        /// <summary>主座位（右侧第一排）坐着时眼睛的位置（车的局部坐标；§9.2 视窗扫描用的同一个点）。</summary>
        public static readonly Vector3 HERO_EYE = new Vector3(0.70f, 1.77f, 0.20f);

        /// <summary>运动：全部是"平滑阶梯速度"（v = v0 + Σ dv·smoothstep），峰值加速度 = 1.5·dv/dur，都 ≤ 1.5 m/s²（§1.8）。</summary>
        static void Motion(LB_Journey j)
        {
            float U1 = LB_Cues.Ut(1), U3 = LB_Cues.Ut(3), U4 = LB_Cues.Ut(4), U6 = LB_Cues.Ut(6), U9 = LB_Cues.Ut(9);
            float LIP8 = LB_Cues.Xt(LB_Cues.X_LIP8), vg = LB_Cues.VG();
            // 前进（世界速度）：U1 起 15 秒 0 → 10 m/s（车门不关）；U3 + 8 起 36 秒 10 → 35；U4 + 20 → U6 + 5：35 → v_g（2700 m ÷ (U9 − U6)）；
            // 门内：入口 v_g → 30 m/s（30 秒）→ 最后一重光唇 15 m/s
            j.roadT0 = new[] { U1, U3 + 8f, U4 + 20f, U9, U9 + 30f };
            j.roadDur = new[] { 15f, 36f, (U6 + 5f) - (U4 + 20f), 30f, LIP8 - (U9 + 30f) };
            j.roadDv = new[] { 10f, 25f, vg - 35f, -(vg - 30f), -15f };
            // 爬升：U3 起 16 秒 0 → 12 m/s；破云前 12 秒放平到 0.62 m/s（U6 离云顶 40 m → U8 约 60 m）；
            // 进门前 20 秒再爬 90 m（到 U9 约 150 m；圣经写"最后 15 秒"，但 15 秒爬 90 m 的峰值加速度是 2.4 m/s²，超过 §1.8 的 1.5，所以拉长到 20 秒）
            j.altT0 = new[] { U3, U6 - 12f, U9 - 20f, U9 - 10f };
            j.altDur = new[] { 16f, 12f, 10f, 10f };
            j.altDv = new[] { 12f, -11.38f, 9f, -9.62f };
            // 坠落（晨）：F0 4 m/s → F1 12 → 云峡 25 → 离海面 310 m 起 23 秒刹到 2 m/s，F2 入水；
            // 海里 30 秒从 2 缓到 1 m/s；F9b 前 1 秒起 14 秒掉出海底到 15 m/s；F12 起 10 秒慢到 5 m/s
            float F0 = LB_Cues.Ft(0), F1 = LB_Cues.Ft(1), F2 = LB_Cues.Ft(2), F9b = LB_Cues.Xt(LB_Cues.X_F9B), F12 = LB_Cues.Ft(12);
            j.fallV0 = 4f;
            j.fallT0 = new[] { F0, F1, F2 - 23f, F2, F9b - 1f, F12 };
            j.fallDur = new[] { F1 - F0, 15f, 23f, 30f, 14f, 10f };
            j.fallDv = new[] { 8f, 13f, -23f, -1f, 14f, -10f };
            j.lampEndLead = 5f;
        }

        static AudioClip Music(string name)
        {
            foreach (var ext in new[] { ".ogg", ".mp3", ".wav" })
            {
                var c = AssetDatabase.LoadAssetAtPath<AudioClip>(LB_Builder.MUSIC_DIR + "/" + name + ext);
                if (c != null) return c;
            }
            Debug.LogWarning(LB_Builder.TAG + " 没找到音乐 " + LB_Builder.MUSIC_DIR + "/" + name + ".ogg");
            return null;
        }

        static Color C(string hex, float mul = 1f) { var c = LB_Builder.Hex(hex); return new Color(c.r * mul, c.g * mul, c.b * mul, 1f); }
        static Color CA(string hex, float a) { var c = LB_Builder.Hex(hex); return new Color(c.r, c.g, c.b, a); }

        // 天空的样子：0 雾夜 1 深蓝夜空（破云后）2 晨 3 暮 4 星夜 5 天上有海 6 深海 7 蓝时（8b：圣经 §6·8b 的数）
        static void FillSky(LB_Journey j)
        {
            j.skyTop = new[] { C("#0a0c11"), C("#030616"), C("#2b4f9e"), C("#22183f"), C("#060b20"), C("#041a2e"), C("#2f80b4"), C("#16223f") };
            j.skyHorizon = new[] { C("#3a3228"), C("#0d1530"), C("#e8b898"), C("#ff9a5c"), C("#141f3c"), C("#0a2a44"), C("#0e3a5e"), C("#8093c2") };
            j.skyBottom = new[] { C("#121214"), C("#04060e"), C("#4a6a94"), C("#2e2238"), C("#030510"), C("#050810"), C("#02070f"), C("#1a2a4e") };
            j.sunDir = new[] { new Vector4(0.3f, 0.5f, 0.8f, 1f), new Vector4(0.2f, 0.45f, 0.87f, 1.2f), new Vector4(0.645f, 0.08f, 0.76f, 2.2f), new Vector4(0.612f, 0.036f, 0.79f, 2.8f), new Vector4(-0.35f, 0.55f, 0.75f, 1.6f), new Vector4(0f, 1f, 0f, 1f), new Vector4(0.15f, 0.95f, 0.2f, 5.5f), new Vector4(0.612f, 0.036f, 0.79f, 1f) };   // w = 角半径（度）
            j.sunColor = new[] { Color.black, C("#c9d4ee", 0.8f), Color.black, Color.black, Color.black, Color.black, C("#8fd0ff", 0.9f), Color.black };
            j.starAmount = new[] { 0f, 0.8f, 0f, 0.15f, 1f, 0f, 0f, 0.2f };
            j.fogColor = new[] { C("#24262c"), C("#0a0e1c"), C("#d8b8a0"), C("#6a4a5a"), C("#060a16"), C("#0c1a28"), C("#0d3050"), C("#3f5790") };
            j.fogDensity = new[] { 0.0085f, 0.0015f, 0.0004f, 0.0009f, 0.0008f, 0.005f, 0.0045f, 0.0003f };
            j.ambient = new[] { C("#22242a"), C("#0c1020"), C("#8a98b0"), C("#5a4060"), C("#0a1020"), C("#0e1a26"), C("#123a58"), C("#2a3a60") };
            j.sunLight = new[] { CA("#8a94a8", 0.10f), CA("#aab8de", 0.35f), CA("#fff0d0", 1.1f), CA("#ffb080", 0.8f), CA("#b0c0e8", 0.45f), CA("#8fb0c8", 0.3f), CA("#7fc0e8", 0.5f), CA("#6f86b0", 0.15f) };
            // 真的天空：晨光、暮色是 Poly Haven 的 HDRI（CC0），星夜是 NASA 的深空星图；太阳方向从 HDRI 里最亮的点算出来
            j.skyTex = new Texture[8];
            j.skyTex[LB_Journey.SKY_DAWN] = LB_Mats.SkyTex("Assets/Lanbai/Sky/sky_dawn_4k.hdr");
            j.skyTex[LB_Journey.SKY_DUSK] = LB_Mats.SkyTex("Assets/Lanbai/Sky/sky_dusk_4k.hdr");
            j.skyTex[LB_Journey.SKY_STARS] = LB_Mats.SkyTex("Assets/Lanbai/Sky/starmap_nasa_4k.hdr");
            j.skyTexExposure = new[] { 1f, 1f, 0.8f, 0.7f, 2.4f, 1f, 1f, 1f };
            j.skyClouds = new[] { 1f, 0f, 0f, 0f, 0f, 0f, 0f, 0f };
            j.skyTexRot = new[] { 0f, 0f, 0f, 0f, 0f, 0f, 0f, 0f };
            j.horizonFog = new[] { 0.85f, 0.5f, 0.32f, 0.42f, 0.32f, 0.5f, 0.6f, 0.4f };
            j.deepFog = C("#0a2540"); j.deepFogDensity = 0.0065f; j.deepAmbient = C("#0e2a44");
        }

        // ═════════════════════════════════════════════════════════════
        //  诗（圣经 §7.4、§7.5）：时刻绑乐句；停留、方位 / 仰角 / 距离、字高、颜色照表。
        //  语言（§7.4.7）：中文诗——中文玩家只看原文，日文玩家原文 + 書き下し，其他人原文 + 英文；
        //  德文 / 英文诗——原文 + 中 / 日 / 英译（英文玩家看英文诗只看原文）。
        //  每句 3 个阶段（逐句揭示用：后面没到的行用 <alpha=#00> 先藏着，版式不跳）；没有揭示的句子 3 个阶段一样。
        //  译文和原文交错排（一行原文、下面一行它的译文），这样没揭示的永远是末尾，淡入淡出靠整体的 color.a。
        // ═════════════════════════════════════════════════════════════
        class Poem
        {
            public float at, hold, fin = 2.5f, fout = 3f, rev1, rev2, az, el, dist, size, drift = 1f; public bool fix; public Color color;
            public List<string> orig = new List<string>();        // 原文的行
            public List<int> stage = new List<int>();             // 每行在第几阶段出现
            public List<string> zh = new List<string>(), ja = new List<string>(), en = new List<string>();   // 每行的译文（null = 这种语言不加译文）
            public float trSize = 0.75f;                          // 译文字号（相对主行）
            public bool italic;
        }

        static string Stage(Poem p, List<string> tr, int s)
        {
            var sb = new System.Text.StringBuilder();
            bool hidden = false;
            for (int i = 0; i < p.orig.Count; i++)
            {
                if (!hidden && p.stage[i] > s) { sb.Append("<alpha=#00>"); hidden = true; }
                if (i > 0) sb.Append('\n');
                sb.Append(p.italic ? "<i>" + p.orig[i] + "</i>" : p.orig[i]);
                if (tr != null && i < tr.Count && !string.IsNullOrEmpty(tr[i]))
                {
                    sb.Append('\n').Append("<size=").Append(Mathf.RoundToInt(p.trSize * 100f)).Append("%>");
                    sb.Append(tr[i]).Append("</size>");
                }
            }
            return sb.ToString();
        }

        static void FillPoem(LB_Journey j)
        {
            float U3 = LB_Cues.Ut(3), U6 = LB_Cues.Ut(6), U7 = LB_Cues.Ut(7), U8 = LB_Cues.Ut(8);
            float U7b = LB_Cues.Xt(LB_Cues.X_U7B), U8b = LB_Cues.Xt(LB_Cues.X_U8B);
            float F0 = LB_Cues.Ft(0), F6 = LB_Cues.Ft(6), F11 = LB_Cues.Ft(11), F12 = LB_Cues.Ft(12), F13 = LB_Cues.Ft(13), F9b = LB_Cues.Xt(LB_Cues.X_F9B);
            float fals = SEG[LB_Journey.S_FALSE], wake = SEG[LB_Journey.S_WAKE];
            var list = new List<Poem>();
            Poem P(float at, float hold, float az, float el, float dist, float size, string hex, float alpha = 0.9f)
            {
                var p = new Poem { at = at, hold = hold, az = az, el = el, dist = dist, size = size };
                var c = LB_Builder.Hex(hex); p.color = new Color(c.r, c.g, c.b, alpha);
                list.Add(p); return p;
            }
            void L(Poem p, int stage, string orig, string zh, string ja, string en)
            { p.orig.Add(orig); p.stage.Add(stage); p.zh.Add(zh); p.ja.Add(ja); p.en.Add(en); }

            // 3 · 李白《梦游天姥吟留别》：灯海完全揭示 ≈ U3 + 20，11 秒，+50° / −9° / 40 m（灯海之上），2.4°，暖白
            var p1 = P(U3 + 20f, 11f, 50f, -9f, 40f, 2.4f, "#E2DDD4");
            L(p1, 0, "我欲因之梦吴越", null, "我 之に因りて 呉越を夢みんと欲す", "I would dream my way to Wu and Yue —");
            L(p1, 0, "一夜飞度镜湖月", null, "一夜 飛びて度る 鏡湖の月", "in one night fly across the Mirror Lake moon");

            // 4a · 里尔克《杜伊诺哀歌》第一首：U6 + 4，10 秒，+20° / +3° / 60 m，德文斜体 2.2° + 译文 1.8°（预言：在意象之前）
            var p2 = P(U6 + 4f, 10f, 20f, 3f, 60f, 2.2f, "#D8DDE6"); p2.italic = true; p2.trSize = 0.82f;
            L(p2, 0, "Denn das Schöne ist nichts", "因为美不过是", "美しいものとは", "For beauty is nothing");
            L(p2, 0, "als des Schrecklichen Anfang", "恐怖的开端", "恐ろしいものの始まりにほかならない", "but the beginning of terror");

            // 4b · Urlicht 唱词：与歌声同步（U7 / U7b，U8 / U8b），0° / −6° / 30 m，德 1.8° + 译 1.8°；每句唱完 1.5 秒内淡出
            //   （第一句唱完约在文件 157.8 秒；第二句连同第二遍 Ach nein 约在 173.5 秒；进门前 1.5 秒安静）
            var p3 = P(U7, (157.8f + LB_Cues.T_URLICHT + 1.5f) - U7, 0f, -6f, 30f, 1.8f, "#D8DDE6"); p3.italic = true; p3.trSize = 1f;
            p3.fin = 0.6f; p3.fout = 1.5f; p3.rev1 = U7b - U7;
            L(p3, 0, "Da kam ein Engelein", "来了一个小天使", "小さな天使がやって来て", "Then came a little angel");
            L(p3, 1, "und wollt' mich abweisen.", "要把我赶回去", "私を追い返そうとした", "who wished to turn me away.");
            var p4 = P(U8, (LB_Cues.Ut(9) - 1.5f) - U8, 0f, -6f, 30f, 1.8f, "#D8DDE6"); p4.italic = true; p4.trSize = 1f;
            p4.fin = 0.6f; p4.fout = 1.5f; p4.rev1 = U8b - U8;
            L(p4, 0, "Ach nein!", "啊，不！", "ああ、いいえ！", "Ah no!");
            L(p4, 1, "Ich ließ mich nicht abweisen!", "我不让自己被赶回去！", "私は追い返されはしなかった！", "I would not be turned away!");

            // 6 · 小楠：我从天空坠入深海 —— F0 + 20（两次号角之间），9 秒，−15° / −12° / 40 m，深墨色，退场向下漂
            var p5 = P(F0 + 20f, 9f, -15f, -12f, 40f, 2.4f, "#1F2A3A"); p5.drift = -1f;
            L(p5, 0, "我从天空坠入深海", null, "私は空から深い海へ落ちた", "I fell from the sky into the deep sea");

            // 7b · 屈原《九歌·河伯》：大殿门完全进入视野（F6）+ 8 秒，13 秒，−25° / +6° / 15 m，2.2°
            var p6 = P(F6 + 8f, 13f, -25f, 6f, 15f, 2.2f, "#D9E2E7"); p6.trSize = 0.82f;
            L(p6, 0, "鱼鳞屋兮龙堂", null, "魚鱗の屋 龍の堂", "Fish-scale roofs, a dragon hall,");
            L(p6, 0, "紫贝阙兮朱宫", null, "紫貝の闕 朱の宮", "gates of purple shell, a cinnabar palace —");
            L(p6, 0, "灵何为兮水中", null, "霊 何為れぞ水中に", "spirit, what are you doing in the water?");

            // 8 · 小楠：自深海坠入另一片天空 —— 出海 + 12 秒，10 秒，与晨那句同一处，亮字，退场向下漂
            var p7 = P(F9b + 12f, 10f, -15f, -12f, 40f, 2.4f, "#EADCD6"); p7.drift = -1f;
            L(p7, 0, "自深海坠入另一片天空", null, "深い海から、もう一つの空へ落ちた", "and from the deep sea into another sky");

            // 8-ii · 庄子《逍遥游》：F11 + 4，分三行（+6、+13 秒），保持到 +22 秒再 4 秒退场；+35° / 0°（地平线上）/ 60 m，固定位置
            //   （第三行在地平线下；镜像字等云端的诗句系统）
            var p8 = P(F11 + 4f, 26f, 35f, 0f, 60f, 2.2f, "#EADCD6"); p8.fix = true; p8.fout = 4f; p8.rev1 = 6f; p8.rev2 = 13f; p8.trSize = 0.82f;
            L(p8, 0, "天之苍苍，其正色邪？", null, "天の蒼蒼たるは、其れ正色なるか", "Is the blue of the sky its true color?");
            L(p8, 1, "其远而无所至极邪？", null, "其れ遠くして至極する所無ければか", "Or is it only far, and without end?");
            L(p8, 2, "", null, null, null);
            L(p8, 2, "其视下也，亦若是则已矣", null, "其の下を視るや、亦た是くの若くならんのみ", "Looking down, it would look the same.");

            // 9a · 屈原《天问》：蓝时变暗结束（F12 + 23）到 F13（≥ 8 秒），F13 时 1.2 秒暗下去（字变成星——等云端）；0° / +8° / 50 m
            var p9 = P(F12 + 23f, (F13 - (F12 + 23f)) + 1.2f, 0f, 8f, 50f, 2.2f, "#D9E2E7"); p9.fout = 1.2f; p9.drift = 0f; p9.trSize = 0.82f;
            L(p9, 0, "遂古之初，谁传道之？", null, "遂古の初め、誰か之を伝え道う", "Of the beginning of old, who told the tale?");
            L(p9, 0, "上下未形，何由考之？", null, "上下未だ形れず、何に由りて之を考えん", "When above and below had no form, how was it known?");

            // 11 · 庄子《齐物论》：假醒第 28 秒，12 秒，0° / +8° / 10 m，2.0°，80%
            var p10 = P(fals + 28f, 12f, 0f, 8f, 10f, 2.0f, "#E0D6C4", 0.8f);
            L(p10, 0, "不知周之梦为胡蝶与", null, "知らず 周の夢に胡蝶と為れるか", "Did Zhou dream he was a butterfly,");
            L(p10, 0, "胡蝶之梦为周与", null, "胡蝶の夢に周と為れるか", "or does a butterfly dream it is Zhou?");

            // 12 · 李白：醒（第二次白收缩进灯管起）第 16 秒，11 秒，与第 3 幕李白同一处
            var p11 = P(wake + 16f, 11f, 50f, -9f, 40f, 2.4f, "#D9E2E7");
            L(p11, 0, "惟觉时之枕席", null, "惟だ覚むる時の枕席のみ", "Only the pillow and mat of waking —");
            L(p11, 0, "失向来之烟霞", null, "向来の煙霞を失う", "lost, the mists and glow of before");

            // 12 · 济慈《夜莺颂》：第 70 秒，10 秒，+50° / −14° / 25 m，斜体 1.6° + 译文 1.8°——世界里最后的字
            var p12 = P(wake + 70f, 10f, 50f, -14f, 25f, 1.6f, "#D9E2E7"); p12.italic = true; p12.trSize = 1.12f;
            L(p12, 0, "Fled is that music:—", "那音乐已经远去——", "あの音楽は去った——", null);
            L(p12, 0, "Do I wake or sleep?", "我是醒着，还是睡着？", "私は目覚めているのか、眠っているのか", null);

            int n = list.Count;
            j.poemText = new string[n * 3]; j.poemTextJa = new string[n * 3]; j.poemTextEn = new string[n * 3];
            j.poemAt = new float[n]; j.poemHold = new float[n]; j.poemIn = new float[n]; j.poemOut = new float[n];
            j.poemReveal1 = new float[n]; j.poemReveal2 = new float[n];
            j.poemAz = new float[n]; j.poemEl = new float[n]; j.poemDist = new float[n]; j.poemSize = new float[n];
            j.poemColor = new Color[n]; j.poemDrift = new float[n]; j.poemFixed = new bool[n];
            for (int i = 0; i < n; i++)
            {
                var p = list[i];
                for (int s = 0; s < 3; s++)
                {
                    j.poemText[i * 3 + s] = Stage(p, p.zh, s);
                    j.poemTextJa[i * 3 + s] = Stage(p, p.ja, s);
                    j.poemTextEn[i * 3 + s] = Stage(p, p.en, s);
                }
                j.poemAt[i] = p.at; j.poemHold[i] = p.hold; j.poemIn[i] = p.fin; j.poemOut[i] = p.fout;
                j.poemReveal1[i] = p.rev1; j.poemReveal2[i] = p.rev2;
                j.poemAz[i] = p.az; j.poemEl[i] = p.el; j.poemDist[i] = p.dist; j.poemSize[i] = p.size;
                j.poemColor[i] = p.color; j.poemDrift[i] = p.drift; j.poemFixed[i] = p.fix;
            }
        }
    }
}
