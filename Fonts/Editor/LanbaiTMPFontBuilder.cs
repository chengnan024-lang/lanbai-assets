// Lanbai / 蓝白 — builds the TextMeshPro font assets for every string the world shows (art bible v2.1 §7.2).
//
// ⚠ UNCOMPILED IN UNITY. Written against TextMeshPro 3.0.x (com.unity.textmeshpro, the version Unity 2022.3 ships)
//   and type-checked outside Unity with Roslyn against UnityEngine/UnityEditor reference assemblies plus a stub of
//   the TMP API it uses (Tools~/compile_check). Members we are less sure of are reached through reflection.
//
// What it does (same recipe TMP's own "Create > TextMeshPro > Font Asset" menu uses, then frozen to Static):
//   for each font: Subset/<font>  +  Charsets/<charset>.txt
//     -> TMP_FontAsset.CreateFontAsset(font, 90 pt, padding 10, SDF32 (or SDFAA), atlas W×H, Dynamic, single atlas)
//     -> AssetDatabase.CreateAsset + atlas texture and material as sub-assets
//     -> TryAddCharacters(charset)  -> material shader = "TextMeshPro/Distance Field"  -> atlasPopulationMode = Static
//   Output: <kit>/FontAssets/Lanbai_*.asset. Existing assets are rebuilt IN PLACE (GUID kept, references survive).
//
// Every entry point is a public static method that returns a report string (for the remote helper's `call` step);
// the menu items under 蓝白/Fonts/ just log that string.
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;

namespace Lanbai.Fonts.EditorTools
{
    public static class LanbaiTMPFontBuilder
    {
        public const int SamplingPointSize = 90;   // bible §7.2
        public const int AtlasPadding = 10;        // bible §7.2 (gives room for _OutlineSoftness 0.9 and Face Dilate +0.10)
        public const float DefaultFaceDilate = 0.05f; // desktop value (§7.2); Udon raises it to 0.10 in VR at runtime

        struct Spec
        {
            public string Key, FontFile, CharsetFile, AssetName;
            public int Width, Height;
            public bool Optional;
            public Spec(string key, string fontFile, string charsetFile, string assetName, int w, int h, bool optional)
            {
                Key = key; FontFile = fontFile; CharsetFile = charsetFile; AssetName = assetName;
                Width = w; Height = h; Optional = optional;
            }
        }

        // Latin assets use the "+ascii" charsets (cheap insurance for names typed later); CJK assets are exact.
        static readonly Spec[] Specs =
        {
            new Spec("SourceHanSerifSC-Regular", "LanbaiSerifSC-Regular.otf", "charset_SourceHanSerifSC-Regular.txt", "Lanbai_SerifSC_Regular SDF", 2048, 2048, false),
            new Spec("SourceHanSerifTW-Regular", "LanbaiSerifTC-Regular.otf", "charset_SourceHanSerifTW-Regular.txt", "Lanbai_SerifTC_Regular SDF", 2048, 2048, false),   // v4: Traditional (zh-HK, D-31)
            new Spec("SourceHanSerifSC-Medium", "LanbaiSerifSC-Medium.otf", "charset_SourceHanSerifSC-Medium.txt", "Lanbai_SerifSC_Medium SDF", 2048, 2048, false),
            new Spec("SourceHanSerifJP-Regular", "LanbaiSerifJP-Regular.otf", "charset_SourceHanSerifJP-Regular.txt", "Lanbai_SerifJP_Regular SDF", 2048, 2048, false),   // v4: every Japanese poem line (D-30)
            new Spec("SourceHanSerifJP-Medium", "LanbaiSerifJP-Medium.otf", "charset_SourceHanSerifJP-Medium.txt", "Lanbai_SerifJP_Medium SDF", 2048, 2048, false),     // v4: only the Tianwen sub-line
            new Spec("EBGaramond-Regular", "EBGaramond-Regular.Lanbai.ttf", "charset_EBGaramond-Regular+ascii.txt", "Lanbai_Garamond_Regular SDF", 1024, 1024, false),
            new Spec("EBGaramond-Italic", "EBGaramond-Italic.Lanbai.ttf", "charset_EBGaramond-Italic+ascii.txt", "Lanbai_Garamond_Italic SDF", 1024, 1024, false),
            new Spec("BarlowSemiCondensed-SemiBold", "BarlowSemiCondensed-SemiBold.Lanbai.ttf", "charset_BarlowSemiCondensed-SemiBold+ascii.txt", "Lanbai_Barlow_SemiBold SDF", 1024, 1024, false),
            // optional: the Sign kit already bakes the credits / Coleridge slip
            new Spec("IMFellEnglish-Roman", "LanbaiSlip-Regular.ttf", "charset_IMFellEnglish-Roman+ascii.txt", "Lanbai_Slip_Roman SDF", 1024, 1024, true),
            new Spec("IMFellEnglishSC", "LanbaiSlipSC-Regular.ttf", "charset_IMFellEnglishSC+ascii.txt", "Lanbai_Slip_SC SDF", 1024, 1024, true),
        };

        // ------------------------------------------------------------------------------------------ menus
        [MenuItem("蓝白/Fonts/Build TMP Font Assets (SDF32, bible)")]
        static void MenuBuild() { Debug.Log(BuildAll()); }

        [MenuItem("蓝白/Fonts/Build TMP Font Assets (SDFAA, fast fallback)")]
        static void MenuBuildFast() { Debug.Log(BuildAllFast()); }

        [MenuItem("蓝白/Fonts/Build Optional Font Assets (Slip = IM FELL subsets)")]
        static void MenuBuildOptional() { Debug.Log(BuildOptional()); }

        [MenuItem("蓝白/Fonts/Verify TMP Font Assets")]
        static void MenuVerify() { Debug.Log(VerifyAll()); }

        // --------------------------------------------------------------------------------- public API
        /// <summary>Required assets, SDF32 (bible §7.2). Returns a report.</summary>
        public static string BuildAll() { return Build(GlyphRenderMode.SDF32, false); }

        /// <summary>Required assets, SDFAA (fast; use if SDF32 is too slow or fails on this machine).</summary>
        public static string BuildAllFast() { return Build(GlyphRenderMode.SDFAA, false); }

        /// <summary>Only the optional assets (IM FELL for a TMP credits slip), SDF32.</summary>
        public static string BuildOptional() { return Build(GlyphRenderMode.SDF32, true); }

        /// <summary>Build one asset by key, e.g. "SourceHanSerifSC-Regular"; mode "SDF32" or "SDFAA".</summary>
        public static string BuildOne(string key, string mode)
        {
            GlyphRenderMode m = mode == "SDFAA" ? GlyphRenderMode.SDFAA : GlyphRenderMode.SDF32;
            string kit = KitRoot();
            if (kit == null) return "LanbaiTMPFontBuilder: kit folder not found (the script must stay at <kit>/Editor/LanbaiTMPFontBuilder.cs).";
            foreach (Spec s in Specs)
                if (s.Key == key) return BuildSpec(kit, s, m);
            return "LanbaiTMPFontBuilder: unknown key " + key;
        }

        static string Build(GlyphRenderMode mode, bool optionalOnly)
        {
            string kit = KitRoot();
            if (kit == null) return "LanbaiTMPFontBuilder: kit folder not found (the script must stay at <kit>/Editor/LanbaiTMPFontBuilder.cs).";
            var sb = new StringBuilder();
            sb.AppendLine("Lanbai TMP font assets — " + mode + ", sampling " + SamplingPointSize + ", padding " + AtlasPadding + ", kit " + kit);
            foreach (Spec s in Specs)
            {
                if (s.Optional != optionalOnly) continue;
                try { sb.AppendLine(BuildSpec(kit, s, mode)); }
                catch (Exception e) { sb.AppendLine("  FAIL " + s.AssetName + ": " + e.GetType().Name + " " + e.Message); }
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            sb.AppendLine(VerifyAll());
            return sb.ToString();
        }

        static string BuildSpec(string kit, Spec s, GlyphRenderMode mode)
        {
            string fontPath = kit + "/Subset/" + s.FontFile;
            Font font = AssetDatabase.LoadAssetAtPath<Font>(fontPath);
            if (font == null) return "  FAIL " + s.AssetName + ": font not found at " + fontPath;
            string chars = ReadCharset(kit, s.CharsetFile);
            if (chars == null) return "  FAIL " + s.AssetName + ": charset not found " + s.CharsetFile;

            string outDir = kit + "/FontAssets";
            if (!AssetDatabase.IsValidFolder(outDir)) AssetDatabase.CreateFolder(kit, "FontAssets");
            string assetPath = outDir + "/" + s.AssetName + ".asset";

            TMP_FontAsset fa = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(assetPath);
            bool inPlace = fa != null;
            if (inPlace)
            {
                // keep the GUID: switch back to dynamic, clear, re-add (TMP's inspector does the same for "Clear Dynamic Data")
                SetSourceFont(fa, font);
                fa.atlasPopulationMode = AtlasPopulationMode.Dynamic;
                // set size / mode / padding BEFORE clearing: ClearFontAssetData rebuilds the packer's free-rect list
                // from m_AtlasWidth / m_AtlasHeight, so a changed atlas size must already be in place (verify r1 m9)
                SetRenderSettings(fa, mode, s.Width, s.Height);
                if (!InvokeClear(fa))
                    return "  FAIL " + s.AssetName + ": exists, and ClearFontAssetData is not available in this TMP version — delete the asset and run again.";
            }
            else
            {
                fa = TMP_FontAsset.CreateFontAsset(font, SamplingPointSize, AtlasPadding, mode, s.Width, s.Height, AtlasPopulationMode.Dynamic, false);
                if (fa == null) return "  FAIL " + s.AssetName + ": CreateFontAsset returned null (font import?)";
                fa.name = s.AssetName;
                AssetDatabase.CreateAsset(fa, assetPath);
                Texture2D tex0 = fa.atlasTexture;
                tex0.name = s.AssetName + " Atlas";
                AssetDatabase.AddObjectToAsset(tex0, fa);
                fa.material.name = s.AssetName + " Material";
                AssetDatabase.AddObjectToAsset(fa.material, fa);
            }

            string missing;
            bool all = AddCharacters(fa, chars, out missing);
            if (KerningCount(fa) <= 0) TryFetchKerning(fa);       // Latin: the subsets carry a legacy 'kern' table for this
            ApplyDistanceFieldMaterial(fa);
            fa.atlasPopulationMode = AtlasPopulationMode.Static;   // editor: also drops the source-font reference from builds

            EditorUtility.SetDirty(fa.atlasTexture);
            EditorUtility.SetDirty(fa.material);
            EditorUtility.SetDirty(fa);
            AssetDatabase.SaveAssets();

            int glyphs = fa.glyphTable != null ? fa.glyphTable.Count : -1;
            return string.Format("  {0} {1}: {2} chars requested, {3} glyphs, atlas {4}x{5}, kerning pairs {6}{7}",
                all ? "OK  " : "MISS", s.AssetName, CountChars(chars), glyphs, fa.atlasWidth, fa.atlasHeight, KerningCount(fa),
                (all ? "" : "  missing: " + missing) + (inPlace ? "  (rebuilt in place)" : "  (new)"));
        }

        /// <summary>Checks every asset: all charset characters present, static, Distance Field shader.</summary>
        public static string VerifyAll()
        {
            string kit = KitRoot();
            if (kit == null) return "LanbaiTMPFontBuilder: kit folder not found.";
            var sb = new StringBuilder();
            sb.AppendLine("Verify (" + kit + "/FontAssets):");
            bool pass = true;
            foreach (Spec s in Specs)
            {
                string assetPath = kit + "/FontAssets/" + s.AssetName + ".asset";
                TMP_FontAsset fa = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(assetPath);
                if (fa == null)
                {
                    if (!s.Optional) pass = false;
                    sb.AppendLine("  " + (s.Optional ? "--   " : "MISSING ") + s.AssetName + (s.Optional ? " (optional, not built)" : ""));
                    continue;
                }
                string chars = ReadCharset(kit, s.CharsetFile) ?? "";
                List<char> missing;
                bool all = fa.HasCharacters(chars, out missing);
                string shader = fa.material != null && fa.material.shader != null ? fa.material.shader.name : "(none)";
                bool ok = all && fa.atlasPopulationMode == AtlasPopulationMode.Static && shader == "TextMeshPro/Distance Field";
                if (!ok && !s.Optional) pass = false;
                sb.AppendLine(string.Format("  {0} {1}: {2}, {3}, atlas {4}x{5}, glyphs {6}, kerning {7}{8}",
                    ok ? "PASS" : "FAIL", s.AssetName, fa.atlasPopulationMode, shader, fa.atlasWidth, fa.atlasHeight,
                    fa.glyphTable != null ? fa.glyphTable.Count : -1, KerningCount(fa),
                    all ? "" : "  missing: " + new string(missing.ToArray())));
            }
            sb.AppendLine(pass ? "VERIFY PASS" : "VERIFY FAIL");
            return sb.ToString();
        }

        // ----------------------------------------------------------------------------------- helpers
        static void ApplyDistanceFieldMaterial(TMP_FontAsset fa)
        {
            Material mat = fa.material;
            if (mat == null) return;
            Shader sh = Shader.Find("TextMeshPro/Distance Field");       // bible §7.2 (CreateFontAsset defaults to the Mobile SDF shader)
            if (sh != null && mat.shader != sh) mat.shader = sh;
            mat.SetTexture("_MainTex", fa.atlasTexture);
            mat.SetFloat("_TextureWidth", fa.atlasWidth);
            mat.SetFloat("_TextureHeight", fa.atlasHeight);
            mat.SetFloat("_GradientScale", AtlasPadding + 1);
            mat.SetFloat("_WeightNormal", fa.normalStyle);
            mat.SetFloat("_WeightBold", fa.boldStyle);
            mat.SetFloat("_FaceDilate", DefaultFaceDilate);
            // no glow, no outline, no underlay: §7.2 "永不描边、永不投影、没有辉光"
            if (mat.HasProperty("_OutlineWidth")) mat.SetFloat("_OutlineWidth", 0f);
            if (mat.HasProperty("_OutlineSoftness")) mat.SetFloat("_OutlineSoftness", 0f);
            mat.DisableKeyword("GLOW_ON");
            mat.DisableKeyword("UNDERLAY_ON");
            mat.DisableKeyword("UNDERLAY_INNER");
            mat.DisableKeyword("BEVEL_ON");
        }

        static string ReadCharset(string kit, string file)
        {
            string abs = ToAbsolute(kit + "/Charsets/" + file);
            if (!File.Exists(abs)) return null;
            string t = File.ReadAllText(abs, new UTF8Encoding(false));
            if (t.Length > 0 && t[0] == '﻿') t = t.Substring(1);
            return t.Replace("\r", "").Replace("\n", "");
        }

        static int CountChars(string s)
        {
            int n = 0;
            for (int i = 0; i < s.Length; i++) if (!char.IsLowSurrogate(s[i])) n++;
            return n;
        }

        static string ToAbsolute(string assetPath)
        {
            string root = Directory.GetParent(Application.dataPath).FullName;
            return Path.Combine(root, assetPath);
        }

        static string KitRoot()
        {
            const string tail = "/Editor/LanbaiTMPFontBuilder.cs";
            foreach (string g in AssetDatabase.FindAssets("LanbaiTMPFontBuilder t:MonoScript"))
            {
                string p = AssetDatabase.GUIDToAssetPath(g);
                if (p.EndsWith(tail, StringComparison.Ordinal)) return p.Substring(0, p.Length - tail.Length);
            }
            return null;
        }

        // Reflection for members whose exact shape differs between TMP versions.
        const BindingFlags Any = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

        static bool InvokeClear(TMP_FontAsset fa)
        {
            MethodInfo m = null;
            foreach (MethodInfo mi in typeof(TMP_FontAsset).GetMethods(Any))
                if (mi.Name == "ClearFontAssetData") { m = mi; break; }
            if (m == null) return false;
            ParameterInfo[] ps = m.GetParameters();
            var args = new object[ps.Length];
            for (int i = 0; i < ps.Length; i++)
                args[i] = ps[i].ParameterType == typeof(bool) ? (object)true : (ps[i].HasDefaultValue ? ps[i].DefaultValue : null);   // setAtlasSizeToZero: re-made at W×H on the next add
            m.Invoke(fa, args);
            return true;
        }

        static void SetRenderSettings(TMP_FontAsset fa, GlyphRenderMode mode, int w, int h)
        {
            SetField(fa, "m_AtlasRenderMode", mode);
            SetField(fa, "m_AtlasWidth", w);
            SetField(fa, "m_AtlasHeight", h);
            SetField(fa, "m_AtlasPadding", AtlasPadding);
        }

        static void SetSourceFont(TMP_FontAsset fa, Font font)
        {
            SetField(fa, "m_SourceFontFile_EditorRef", font);
            SetField(fa, "m_SourceFontFile", font);
        }

        static void SetField(object o, string name, object value)
        {
            FieldInfo f = o.GetType().GetField(name, Any);
            if (f != null && (value == null || f.FieldType.IsAssignableFrom(value.GetType()))) f.SetValue(o, value);
        }

        /// <summary>TryAddCharacters, preferring the overload with includeFontFeatures (newer TMP) so kerning comes too.</summary>
        static bool AddCharacters(TMP_FontAsset fa, string chars, out string missing)
        {
            try
            {
                foreach (MethodInfo mi in typeof(TMP_FontAsset).GetMethods(BindingFlags.Instance | BindingFlags.Public))
                {
                    if (mi.Name != "TryAddCharacters") continue;
                    ParameterInfo[] ps = mi.GetParameters();
                    if (ps.Length == 3 && ps[0].ParameterType == typeof(string) && ps[1].ParameterType == typeof(string).MakeByRefType()
                        && ps[2].ParameterType == typeof(bool))
                    {
                        object[] args = { chars, null, true };
                        bool ok = (bool)mi.Invoke(fa, args);
                        missing = args[1] as string;
                        return ok;
                    }
                }
            }
            catch (Exception e) { Debug.LogWarning("LanbaiTMPFontBuilder: TryAddCharacters(string, out string, bool) failed on " + fa.name + ", using the 2-argument form: " + e.Message); }
            return fa.TryAddCharacters(chars, out missing);
        }

        static void TryFetchKerning(TMP_FontAsset fa)
        {
            try
            {
                MethodInfo withList = null;
                foreach (MethodInfo mi in typeof(TMP_FontAsset).GetMethods(Any))
                {
                    if (mi.Name != "UpdateGlyphAdjustmentRecords") continue;
                    ParameterInfo[] ps = mi.GetParameters();
                    if (ps.Length == 0) { mi.Invoke(fa, null); Debug.Log("LanbaiTMPFontBuilder: " + fa.name + ": UpdateGlyphAdjustmentRecords() -> kerning pairs " + KerningCount(fa)); return; }
                    if (ps.Length == 1 && ps[0].ParameterType == typeof(List<uint>)) withList = mi;
                }
                if (withList != null && fa.glyphTable != null)
                {
                    var idx = new List<uint>();
                    foreach (var g in fa.glyphTable) idx.Add(g.index);
                    withList.Invoke(fa, new object[] { idx });
                    Debug.Log("LanbaiTMPFontBuilder: " + fa.name + ": UpdateGlyphAdjustmentRecords(List<uint>) -> kerning pairs " + KerningCount(fa));
                    return;
                }
                Debug.LogWarning("LanbaiTMPFontBuilder: " + fa.name + ": this TMP version has no UpdateGlyphAdjustmentRecords we can call; "
                                 + "kerning pairs = " + KerningCount(fa) + ". If 0 on a Latin asset, make it once by hand in Font Asset Creator with Get Kerning Pairs on (README §3.3).");
            }
            catch (Exception e) { Debug.LogWarning("LanbaiTMPFontBuilder: kerning fetch failed on " + fa.name + ": " + e.Message); }
        }

        static int KerningCount(TMP_FontAsset fa)
        {
            try
            {
                object table = typeof(TMP_FontAsset).GetProperty("fontFeatureTable", Any)?.GetValue(fa, null);
                if (table == null) return -1;
                object recs = table.GetType().GetProperty("glyphPairAdjustmentRecords", Any)?.GetValue(table, null)
                              ?? table.GetType().GetField("m_GlyphPairAdjustmentRecords", Any)?.GetValue(table);
                var coll = recs as System.Collections.ICollection;
                return coll != null ? coll.Count : -1;
            }
            catch (Exception) { return -1; }
        }
    }
}
#endif
