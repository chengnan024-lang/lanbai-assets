// ═══════════════════════════════════════════════════════════════════
//  蓝白 · PPv2 管线骨架（圣经 §1.4）
//    · 项目设置：线性色彩空间、雾只留 Exponential、灯光强度线性（VRChat SDK 的 EnvConfig 就是这么设的，和客户端一致；圣经 §1.5 写反了）、HDR FP16（只查）
//    · 15 套场景调色 + 助手（EXPO_UP / EXPO_DOWN / WHITE_SAT / WHITE_BLOOM）+ 桌面镜头层（LENS_CLEAN / LENS_ARCHIVE）的 volume 槽：
//      每个槽一个全局 volume、priority 按 grades_final.json、weight 0；profile 从固定路径拿（LanbaiGradeBuilder 生成到这里）：
//        Assets/Lanbai/Grades/Profiles/Lanbai_<键>.asset      键 = grades_final.json 的 S1 … S12、EXPO_UP …
//      15 套都在 → 时间轴用它们（旧的 8 套 ACES 权重归 0）；缺任何一套 → 还用旧的 8 套。
// ═══════════════════════════════════════════════════════════════════
using System.Text;
using UnityEditor;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.PostProcessing;

namespace Lanbai.EditorTools
{
    public static class LB_Grades
    {
        public const string PROFILE_DIR = "Assets/Lanbai/Grades/Profiles";
        /// <summary>场景调色（下标 = LB_Journey.G_*，priority = 下标 + 1，时间顺序）。</summary>
        public static readonly string[] KEYS = { "S1", "S2", "S3", "S4", "S4c", "S6", "S7a", "S7b", "S8", "S8b", "S9a", "S9b", "S10", "S11", "S12" };
        /// <summary>圣经附录 B 的 postExposure（profile 在的时候以 profile 里的值为准）。</summary>
        public static readonly float[] PE = { 0f, -0.15f, -0.9f, -0.85f, -0.9f, -0.75f, -0.8f, -0.4f, -0.5f, -0.3f, 0.3f, 0.3f, 0f, -0.15f, 0f };
        /// <summary>助手（下标 = LB_Journey.H_*）。</summary>
        public static readonly string[] HELPERS = { "EXPO_UP", "EXPO_DOWN", "WHITE_SAT", "WHITE_BLOOM", "LENS_CLEAN", "LENS_ARCHIVE" };
        public static readonly float[] HELPER_PRIORITY = { 100f, 99f, 96f, 96f, 199f, 200f };
        /// <summary>全屏遮罩（占位：旧的 White / Black volume）要压在所有调色之上。</summary>
        public const float MASK_PRIORITY = 150f;

        public static string PathOf(string key) { return PROFILE_DIR + "/Lanbai_" + key + ".asset"; }
        public static PostProcessProfile Load(string key) { return AssetDatabase.LoadAssetAtPath<PostProcessProfile>(PathOf(key)); }

        /// <summary>15 套场景调色是不是都在了。</summary>
        public static bool Ready()
        {
            foreach (var k in KEYS) if (Load(k) == null) return false;
            return true;
        }

        /// <summary>每套的 postExposure：profile 在就读 profile，不在就用圣经的数。</summary>
        public static float[] PostExposures()
        {
            var a = (float[])PE.Clone();
            for (int i = 0; i < KEYS.Length; i++)
            {
                var p = Load(KEYS[i]);
                var cg = p != null ? p.GetSetting<ColorGrading>() : null;
                if (cg != null && cg.postExposure.overrideState) a[i] = cg.postExposure.value;
            }
            return a;
        }

        /// <summary>在 PostProcess 下面建 Grades / Helpers 两组槽。返回（场景 15 个，助手 6 个）。</summary>
        public static void Build(Transform ppRoot, int layer, out PostProcessVolume[] grades, out PostProcessVolume[] helpers)
        {
            var g = new GameObject("Grades"); g.transform.SetParent(ppRoot, false); g.layer = layer;
            grades = new PostProcessVolume[KEYS.Length];
            for (int i = 0; i < KEYS.Length; i++) grades[i] = Slot(g.transform, KEYS[i], i + 1f, layer);
            var h = new GameObject("Helpers"); h.transform.SetParent(ppRoot, false); h.layer = layer;
            helpers = new PostProcessVolume[HELPERS.Length];
            for (int i = 0; i < HELPERS.Length; i++) helpers[i] = Slot(h.transform, HELPERS[i], HELPER_PRIORITY[i], layer);
        }

        static PostProcessVolume Slot(Transform parent, string key, float priority, int layer)
        {
            var go = new GameObject(key); go.transform.SetParent(parent, false); go.layer = layer;
            var v = go.AddComponent<PostProcessVolume>();
            v.isGlobal = true; v.priority = priority; v.weight = 0f; v.sharedProfile = Load(key);
            return v;
        }

        /// <summary>项目设置（§1.4、§1.6）：查一遍，不对的改掉，返回报告。不和 VRChat SDK 的 EnvConfig 打架。</summary>
        public static string ApplyProjectSettings()
        {
            var sb = new StringBuilder();
            // 线性色彩空间（VRChat 要求）
            if (PlayerSettings.colorSpace != ColorSpace.Linear) { sb.Append("色彩空间 ").Append(PlayerSettings.colorSpace).Append(" → Linear；"); PlayerSettings.colorSpace = ColorSpace.Linear; }
            // HDR = FP16：只查不改——VRChat SDK 的 EnvConfig 会清空 Tier Settings（客户端用自己的，桌面默认就是 HDR FP16）
            foreach (GraphicsTier tier in System.Enum.GetValues(typeof(GraphicsTier)))
            {
                var ts = EditorGraphicsSettings.GetTierSettings(BuildTargetGroup.Standalone, tier);
                if (!ts.hdr || ts.hdrMode != CameraHDRMode.FP16) sb.Append("（注意：").Append(tier).Append(" HDR ").Append(ts.hdr ? ts.hdrMode.ToString() : "关").Append("，不是 FP16）");
            }
            // 灯光强度：VRChat SDK 的 EnvConfig 强制 lightsUseLinearIntensity = true（和客户端一致）。
            // 圣经 §1.5 写的"false，VRChat 客户端如此"不对——这里跟 SDK 走，9/30 那次误改成 false 的也改回来
            if (!GraphicsSettings.lightsUseLinearIntensity) { sb.Append("lightsUseLinearIntensity false → true（跟 VRChat SDK / 客户端一致）；"); GraphicsSettings.lightsUseLinearIntensity = true; }
            // 雾：Shader Stripping 只留 Exponential
            var gs = new SerializedObject(GraphicsSettings.GetGraphicsSettings());
            var strip = gs.FindProperty("m_FogStripping"); var lin = gs.FindProperty("m_FogKeepLinear"); var exp = gs.FindProperty("m_FogKeepExp"); var exp2 = gs.FindProperty("m_FogKeepExp2");
            if (strip != null && lin != null && exp != null && exp2 != null)
            {
                if (strip.intValue != 1 || lin.boolValue || !exp.boolValue || exp2.boolValue)
                {
                    sb.Append("雾的 shader 变体 ").Append(strip.intValue == 1 ? "自定义" : "自动").Append("(线性 ").Append(lin.boolValue).Append(" 指数 ").Append(exp.boolValue).Append(" 指数平方 ").Append(exp2.boolValue).Append(") → 只留指数；");
                    strip.intValue = 1; lin.boolValue = false; exp.boolValue = true; exp2.boolValue = false;
                    gs.ApplyModifiedPropertiesWithoutUndo();
                }
            }
            else sb.Append("（没找到雾的 stripping 设置）");
            if (sb.Length > 0) AssetDatabase.SaveAssets();
            return sb.Length > 0 ? "改了：" + sb : "项目设置已经对了（线性色彩空间、HDR FP16、灯光强度线性（跟 VRChat SDK）、只留指数雾）";
        }

        /// <summary>小助手用：报告 15 + 6 个槽各自有没有 profile。</summary>
        public static string Status(string arg)
        {
            var sb = new StringBuilder();
            int n = 0;
            foreach (var k in KEYS) { bool ok = Load(k) != null; if (ok) n++; sb.Append(k).Append(ok ? "✓ " : "· "); }
            sb.Append("| ");
            foreach (var k in HELPERS) sb.Append(k).Append(Load(k) != null ? "✓ " : "· ");
            return "场景调色 " + n + "/15：" + sb + (n == KEYS.Length ? "\n→ 时间轴用圣经的 15 套" : "\n→ 还用旧的 8 套（等 LanbaiGradeBuilder 把 profile 生成到 " + PROFILE_DIR + "）");
        }
    }
}
