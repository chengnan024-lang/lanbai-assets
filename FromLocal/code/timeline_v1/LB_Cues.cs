// ═══════════════════════════════════════════════════════════════════
//  蓝白 · 乐句标签（本地实测 2026-09-30；由 tools/gen_cues.py 从 lanbai-assets/FromLocal/cues.json 生成，别手改）
//  时间轴 t：出发 = 0。前 3.0 秒收音机调台噪音，Urlicht 文件 0 秒在 t = 3.0；末乐章 t = 文件秒 + 240.36。
//  所有幕的起点、运动、诗、闪烁都从这些标签推出来（LB_Udon 用）。
// ═══════════════════════════════════════════════════════════════════
namespace Lanbai.EditorTools
{
    public static class LB_Cues
    {
        public const float T_URLICHT = 3f;        // Urlicht 文件 0 秒在时间轴上的位置（前面是调台噪音）
        public const float F_OFFSET = 240.36f;       // 末乐章：t = 文件秒 + F_OFFSET（U12 → F0 恰好 3.0 秒数字静音）
        public const float FINALE_START = 11.18f;   // 末乐章从文件第几秒开始放（F0 前 0.1 秒，0.1 秒淡入）
        public const float URLICHT_FADE_A = 243.9f, URLICHT_FADE_B = 245.64f;   // 文件秒：录音在 −47 dBFS 被截断，播放时淡出（文件不改）
        public const float FINALE_FADE_A = 930.6f, FINALE_FADE_B = 933.1f;
        public const float WHITE_SILENCE = 5f;      // 末乐章结束后白里的数字静默（§6·10）

        /// <summary>U0–U12：Urlicht 文件秒。</summary>
        public static readonly float[] U_FILE = { 0.9f, 14.5f, 31f, 47.3f, 72.8f, 104.5f, 130.8f, 147.3f, 163.15f, 176.55f, 182.95f, 199.4f, 245.64f };
        /// <summary>F0–F16：末乐章文件秒。</summary>
        public static readonly float[] F_FILE = { 11.28f, 41.5f, 111.7f, 126.85f, 205.65f, 404.6f, 495.2f, 507.9f, 594.8f, 688.75f, 701.9f, 729.4f, 746.7f, 777.85f, 819.3f, 875f, 908.95f };

        // 细分标签（下标 = LB_Journey.X_*）
        public const int X_U6K = 0, X_U7B = 1, X_U8B = 2, X_U8C = 3, X_LIP1 = 4, X_LIP2 = 5, X_LIP3 = 6, X_LIP4 = 7, X_LIP5 = 8, X_LIP6 = 9, X_LIP7 = 10, X_LIP8 = 11, X_UVOICEEND = 12, X_F2H = 13, X_F9B = 14, X_F11B = 15, X_F16R = 16, X_FEND = 17;
        public static readonly string[] X_NAME = { "U6k", "U7b", "U8b", "U8c", "LIP1", "LIP2", "LIP3", "LIP4", "LIP5", "LIP6", "LIP7", "LIP8", "U_voiceEnd", "F2h", "F9b", "F11b", "F16r", "F_end" };
        public static readonly bool[] X_IS_U = { true, true, true, true, true, true, true, true, true, true, true, true, true, false, false, false, false, false };
        public static readonly float[] X_FILE = { 126.1f, 152.1f, 164.9f, 168.4f, 176.55f, 179.9f, 182.95f, 190.9f, 199.4f, 204.15f, 211.05f, 221.75f, 230.8f, 122.9f, 700f, 736f, 930.4f, 933.1f };
        //   U6k        U 文件  126.10  t   129.10  调性转换，Etwas bewegter 管弦先进
        //   U7b        U 文件  152.10  t   155.10  …und wollt' mich abweisen
        //   U8b        U 文件  164.90  t   167.90  Ich ließ mich nicht abweisen!（第一遍）
        //   U8c        U 文件  168.40  t   171.40  第二遍 Ach nein! Ich ließ mich nicht abweisen!
        //   LIP1       U 文件  176.55  t   179.55  光唇 1 = U9 Ich bin von Gott（入口）
        //   LIP2       U 文件  179.90  t   182.90  光唇 2 = …und will wieder zu Gott
        //   LIP3       U 文件  182.95  t   185.95  光唇 3 = U10 Der liebe Gott
        //   LIP4       U 文件  190.90  t   193.90  光唇 4 = …wird mir ein Lichtchen geben
        //   LIP5       U 文件  199.40  t   202.40  光唇 5 = U11 wird leuchten mir
        //   LIP6       U 文件  204.15  t   207.15  光唇 6 = …bis in das ewig
        //   LIP7       U 文件  211.05  t   214.05  光唇 7 = selig
        //   LIP8       U 文件  221.75  t   224.75  光唇 8 = 长音 Leben
        //   U_voiceEnd U 文件  230.80  t   233.80  人声完全结束，管弦尾声 230.8–245.64
        //   F2h        F 文件  122.90  t   363.26  大召唤之后真正的静（持续和弦结束）
        //   F9b        F 文件  700.00  t   940.36  …Nun bist du bezwungen! 结束
        //   F11b       F 文件  736.00  t   976.36  合唱的 entschweben（窗帘松开横杆）
        //   F16r       F 文件  930.40  t  1170.76  终和弦收（乐队停）
        //   F_end      F 文件  933.10  t  1173.46  文件结束（−47 dBFS 的尾巴被截断）

        /// <summary>第 9 幕十三面镜的穿越时刻（时间轴 t；公比 r = 1.2265，吸附到 ±0.8 s 内的强拍；第 13 面 = F16）。</summary>
        public static readonly float[] MIRRORS = { 1032.41f, 1034.91f, 1037.98f, 1041.74f, 1045.82f, 1052.3f, 1058.95f, 1067.46f, 1077.21f, 1089.91f, 1106.41f, 1125.55f, 1149.31f };

        // 第 4 幕管灯闪烁表（云端 lens_tech/out/FlickerTable.cs，seed 20260928；t 相对 U9 "Gott"；≤ 2 次/秒，入口前 1.5 秒安静）
        public static readonly float[] FLICKER_T = { -98.275f, -96.169f, -79.288f, -77.682f, -74.181f, -48.122f, -45.349f, -43.566f, -42.489f, -39.673f, -36.308f, -33.874f, -32.804f, -30.942f, -27.823f, -25.755f, -22.696f, -21.774f, -20.727f, -20.038f, -18.491f, -17.308f, -16.373f, -15.459f, -14.562f, -13.854f, -13.246f, -12.509f, -11.452f, -10.765f, -10.164f, -9.113f, -7.758f, -7.035f, -6.403f, -5.667f, -4.906f, -4.270f, -3.644f, -2.952f, -2.284f, -1.661f };
        public static readonly float[] FLICKER_DUR = { 0.096f, 0.116f, 0.149f, 0.142f, 0.125f, 0.132f, 0.149f, 0.133f, 0.148f, 0.077f, 0.121f, 0.079f, 0.139f, 0.072f, 0.123f, 0.081f, 0.092f, 0.106f, 0.110f, 0.118f, 0.074f, 0.092f, 0.131f, 0.135f, 0.076f, 0.149f, 0.145f, 0.114f, 0.109f, 0.074f, 0.076f, 0.121f, 0.098f, 0.113f, 0.128f, 0.085f, 0.081f, 0.114f, 0.130f, 0.083f, 0.134f, 0.090f };
        public static readonly float[] FLICKER_LEVEL = { 0.246f, 0.240f, 0.283f, 0.342f, 0.332f, 0.172f, 0.205f, 0.145f, 0.151f, 0.198f, 0.159f, 0.208f, 0.157f, 0.116f, 0.187f, 0.162f, 0.138f, 0.149f, 0.084f, 0.088f, 0.073f, 0.092f, 0.130f, 0.228f, 0.197f, 0.115f, 0.090f, 0.056f, 0.206f, 0.191f, 0.134f, 0.179f, 0.045f, 0.121f, 0.188f, 0.068f, 0.096f, 0.193f, 0.080f, 0.198f, 0.089f, 0.057f };
        public static readonly int[] FLICKER_MASK = { 16, 6, 192, 768, 192, 512, 4, 64, 16, 512, 24, 12, 128, 256, 192, 4, 192, 128, 768, 8, 2, 6, 768, 6, 3, 128, 256, 16, 8, 256, 4, 24, 128, 512, 4, 512, 1, 768, 2, 96, 128, 16 };

        public static float Ut(int i) { return U_FILE[i] + T_URLICHT; }
        public static float Ft(int i) { return F_FILE[i] + F_OFFSET; }
        public static float Xt(int i) { return X_FILE[i] + (X_IS_U[i] ? T_URLICHT : F_OFFSET); }
        public static float FEnd() { return FINALE_FADE_B + F_OFFSET; }
        /// <summary>第 4 幕世界速度 v_g = 2 700 m ÷ (U9 − U6)（§6·4）。</summary>
        public static float VG() { return 2700f / (Ut(9) - Ut(6)); }
        public static float[] UT() { var a = new float[U_FILE.Length]; for (int i = 0; i < a.Length; i++) a[i] = Ut(i); return a; }
        public static float[] FT() { var a = new float[F_FILE.Length]; for (int i = 0; i < a.Length; i++) a[i] = Ft(i); return a; }
        public static float[] XT() { var a = new float[X_FILE.Length]; for (int i = 0; i < a.Length; i++) a[i] = Xt(i); return a; }
    }
}
