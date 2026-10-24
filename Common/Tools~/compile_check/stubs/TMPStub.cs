// Copied from Fonts/Tools~/compile_check/TMPStub.cs (2026-10-22) for the shared check: assembly Unity.TextMeshPro.
// Minimal stub of the TextMeshPro 3.0.x API used by LanbaiTMPFontBuilder (signatures as in com.unity.textmeshpro 3.0.6).
// Only for the offline Roslyn type-check; never goes into Unity.
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.TextCore;
using UnityEngine.TextCore.LowLevel;
namespace TMPro
{
    public enum AtlasPopulationMode { Static = 0x0, Dynamic = 0x1 }
    public abstract class TMP_Asset : ScriptableObject { public int hashCode; public Material material; public int materialHashCode; }
    public class TMP_FontFeatureTable { public List<object> glyphPairAdjustmentRecords { get { return null; } set { } } }
    public class TMP_FontAsset : TMP_Asset
    {
        public float normalStyle = 0; public float boldStyle = 0.75f;
        public AtlasPopulationMode atlasPopulationMode { get { return default; } set { } }
        public Texture2D atlasTexture { get { return null; } }
        public Texture2D[] atlasTextures { get { return null; } set { } }
        public int atlasWidth { get { return 0; } }
        public int atlasHeight { get { return 0; } }
        public int atlasPadding { get { return 0; } }
        public List<Glyph> glyphTable { get { return null; } }
        public TMP_FontFeatureTable fontFeatureTable { get { return null; } }
        public static TMP_FontAsset CreateFontAsset(Font font, int samplingPointSize, int atlasPadding, GlyphRenderMode renderMode, int atlasWidth, int atlasHeight, AtlasPopulationMode atlasPopulationMode = AtlasPopulationMode.Dynamic, bool enableMultiAtlasSupport = true) { return null; }
        public bool TryAddCharacters(string characters, out string missingCharacters) { missingCharacters = null; return false; }
        public bool TryAddCharacters(uint[] unicodes, out uint[] missingUnicodes) { missingUnicodes = null; return false; }
        public bool HasCharacters(string text, out List<char> missingCharacters) { missingCharacters = null; return false; }
        public bool HasCharacters(string text, out uint[] missingCharacters, bool searchFallbacks = false, bool tryAddCharacter = false) { missingCharacters = null; return false; }
        public bool HasCharacters(string text) { return false; }
        public void ClearFontAssetData(bool setAtlasSizeToZero = false) { }
    }
    // runtime text components (added for the shared check; the player pass uses the real Unity.TextMeshPro.dll)
    public abstract class TMP_Text : UnityEngine.UI.MaskableGraphicStub
    {
        public virtual string text { get { return null; } set { } }
        public TMP_FontAsset font { get { return null; } set { } }
        public virtual Material fontSharedMaterial { get { return null; } set { } }
        public virtual Material fontMaterial { get { return null; } set { } }
        public float fontSize { get { return 0f; } set { } }
        public float alpha { get { return 1f; } set { } }
        public float characterSpacing { get { return 0f; } set { } }
        public float lineSpacing { get { return 0f; } set { } }
        public bool enableWordWrapping { get { return true; } set { } }
        public void ForceMeshUpdate(bool ignoreActiveState = false, bool forceTextReparsing = false) { }
        public void SetText(string sourceText) { }
    }
    public class TextMeshPro : TMP_Text { }
    public class TextMeshProUGUI : TMP_Text { }
}
namespace UnityEngine.UI
{
    // stands in for uGUI's MaskableGraphic (not in UnityEngine.dll): only what TMP_Text inherits and Lanbai code uses
    public abstract class MaskableGraphicStub : UnityEngine.MonoBehaviour
    {
        public virtual UnityEngine.Color color { get { return UnityEngine.Color.white; } set { } }
    }
}
