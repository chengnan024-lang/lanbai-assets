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
}
