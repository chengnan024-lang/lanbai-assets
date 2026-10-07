// Lanbai / 蓝白 — import settings for the poem scrim sprites (art bible v2.1 §7.2), applied automatically.
//
// ⚠ UNCOMPILED IN UNITY (type-checked offline with Roslyn only, see Tools~/compile_check). Editor-only.
//
// Applies to every texture whose path contains "/Fonts/Textures/Lanbai_Scrim_": Sprite (single, Full Rect mesh),
// 100 pixels per unit (strings_all.json 'sprite_scale' assumes this), mip maps on, Clamp, Bilinear, uncompressed,
// alpha is transparency. The RGB is white. The scrim COLOUR is the solved fill on the material's _Color
// (Lanbai_Scrim_Dark_S8 / Lanbai_Scrim_Light_S6, made by LanbaiPoemMaterials.cs); SpriteRenderer.color stays
// (1, 1, 1, alpha) and carries only the alpha and its fade (README §4.5).
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

namespace Lanbai.Fonts.EditorTools
{
    public class LanbaiScrimTextureImport : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            string p = assetPath.Replace('\\', '/');
            if (!p.Contains("/Fonts/Textures/Lanbai_Scrim_")) return;
            var ti = (TextureImporter)assetImporter;
            ti.textureType = TextureImporterType.Sprite;
            ti.spriteImportMode = SpriteImportMode.Single;
            ti.spritePixelsPerUnit = 100f;
            var settings = new TextureImporterSettings();
            ti.ReadTextureSettings(settings);
            settings.spriteMeshType = SpriteMeshType.FullRect;
            settings.spriteAlignment = (int)SpriteAlignment.Center;
            ti.SetTextureSettings(settings);
            ti.mipmapEnabled = true;
            ti.wrapMode = TextureWrapMode.Clamp;
            ti.filterMode = FilterMode.Bilinear;
            ti.alphaIsTransparency = true;
            ti.sRGBTexture = true;
            ti.textureCompression = TextureImporterCompression.Uncompressed;
            ti.maxTextureSize = 512;
        }
    }
}
#endif
