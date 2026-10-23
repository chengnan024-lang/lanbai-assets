// Type-check stub: the UnityEngine / UnityEditor / UdonSharp / VRC API surface the GateClouds C# touches, with the
// real signatures. NOT Unity: it proves the kit's C# parses and type-checks against these declarations only.
using System;
using System.Collections.Generic;
namespace UnityEngine
{
    public struct Vector2 { public float x, y; public Vector2(float x, float y) { this.x = x; this.y = y; }
        public static Vector2 zero => new Vector2(0, 0); public static Vector2 one => new Vector2(1, 1);
        public static Vector2 right => new Vector2(1, 0); public static Vector2 up => new Vector2(0, 1); }
    public struct Vector3 { public float x, y, z; public Vector3(float x, float y, float z) { this.x = x; this.y = y; this.z = z; }
        public static Vector3 zero => default; public static Vector3 one => new Vector3(1, 1, 1);
        public static Vector3 up => new Vector3(0, 1, 0); public static Vector3 back => new Vector3(0, 0, -1);
        public Vector3 normalized => this; public static Vector3 operator +(Vector3 a, Vector3 b) => a; public static Vector3 operator *(Vector3 a, float b) => a; }
    public struct Vector4 { public float x, y, z, w; public Vector4(float x, float y, float z, float w) { this.x = x; this.y = y; this.z = z; this.w = w; } }
    public struct Quaternion { public static Quaternion LookRotation(Vector3 f, Vector3 u) => default; public static Quaternion identity => default; }
    public struct Bounds { public Bounds(Vector3 c, Vector3 s) { } }
    public struct Color { }
    public static class Mathf { public static float Clamp01(float v) => v; public static float Lerp(float a, float b, float t) => a;
        public static float Max(float a, float b) => a; public static float Min(float a, float b) => a; }
    public class Object { public string name; public static void DestroyImmediate(Object o) { } }
    public class Component : Object { public GameObject gameObject; public Transform transform; public T GetComponent<T>() => default; }
    public class Behaviour : Component { public bool enabled; }
    public class MonoBehaviour : Behaviour { }
    public class Transform : Component, System.Collections.IEnumerable
    { public Vector3 localPosition, localScale; public Quaternion localRotation; public Transform parent; public int childCount;
      public Transform Find(string n) => null; public Transform GetChild(int i) => null; public void SetParent(Transform p, bool w) { }
      public System.Collections.IEnumerator GetEnumerator() => null; }
    public class GameObject : Object { public GameObject(string n) { } public Transform transform; public void SetActive(bool b) { } public static GameObject Find(string n) => null;
        public T AddComponent<T>() where T : Component => default; public T GetComponent<T>() => default;
        public SceneManagement.Scene scene; }
    public class Renderer : Component { public bool enabled; public Material sharedMaterial;
        public Rendering.ShadowCastingMode shadowCastingMode; public bool receiveShadows;
        public void SetPropertyBlock(MaterialPropertyBlock p) { } public void GetPropertyBlock(MaterialPropertyBlock p) { } }
    public class MeshRenderer : Renderer { }
    public class MeshFilter : Component { public Mesh sharedMesh; }
    public class Mesh : Object { public Vector3[] vertices; public Vector2[] uv; public Vector3[] normals; public int[] triangles; public Bounds bounds;
        public void SetVertices(List<Vector3> v) { } public void SetUVs(int ch, List<Vector2> uv) { } public void SetTriangles(List<int> t, int sub) { } }
    public class Shader : Object { public static Shader Find(string n) => null; public static int PropertyToID(string n) => 0; }
    public class Texture : Object { } public class Texture2D : Texture { }
    public class Material : Object { public Material(Shader s) { } public Shader shader; public int renderQueue; public bool enableInstancing;
        public void SetTexture(string n, Texture t) { } public void SetVector(string n, Vector4 v) { } public void SetFloat(string n, float v) { } }
    public sealed class MaterialPropertyBlock { public void Clear() { } public void SetFloat(int id, float v) { } public void SetFloat(string n, float v) { } }
    public enum FilterMode { Point, Bilinear, Trilinear } public enum TextureWrapMode { Repeat, Clamp }
    public static class Debug { public static void Log(object o) { } public static void LogWarning(object o) { } public static void LogError(object o) { } }
    public static class JsonUtility { public static T FromJson<T>(string s) => default; }
    [AttributeUsage(AttributeTargets.Field)] public class HeaderAttribute : Attribute { public HeaderAttribute(string h) { } }
    namespace Rendering { public enum ShadowCastingMode { Off, On } public enum BlendMode { Zero = 0, One = 1, OneMinusSrcAlpha = 10 } }
    namespace SceneManagement { public struct Scene { public GameObject[] GetRootGameObjects() => null; }
        public static class SceneManager { public static Scene GetActiveScene() => default; } }
}
namespace UnityEditor
{
    using UnityEngine;
    [AttributeUsage(AttributeTargets.Method)] public class MenuItem : Attribute { public MenuItem(string p) { } }
    public static class AssetDatabase { public static string[] FindAssets(string f) => null; public static string GUIDToAssetPath(string g) => null;
        public static T LoadAssetAtPath<T>(string p) where T : Object => null; public static Object LoadAssetAtPath(string p, System.Type t) => null; public static void CreateAsset(Object o, string p) { }
        public static bool IsValidFolder(string p) => true; public static string CreateFolder(string a, string b) => null; public static void SaveAssets() { } }
    public static class EditorUtility { public static void CopySerialized(Object a, Object b) { } public static void SetDirty(Object o) { } }
    public class AssetImporter : Object { public static AssetImporter GetAtPath(string p) => null; public void SaveAndReimport() { } }
    public enum TextureImporterType { Default } public enum TextureImporterAlphaSource { FromInput }
    public enum TextureImporterMipFilter { BoxFilter } public enum TextureImporterNPOTScale { None }
    public enum TextureImporterFormat { RGBA32, BC7 } public enum TextureImporterCompression { Uncompressed, CompressedHQ }
    public class TextureImporterPlatformSettings { public int maxTextureSize; public TextureImporterFormat format; public TextureImporterCompression textureCompression; public bool overridden; }
    public class TextureImporter : AssetImporter { public TextureImporterCompression textureCompression; public TextureImporterType textureType; public bool sRGBTexture; public TextureImporterAlphaSource alphaSource;
        public bool alphaIsTransparency; public TextureWrapMode wrapMode; public bool mipmapEnabled; public TextureImporterMipFilter mipmapFilter;
        public FilterMode filterMode; public int anisoLevel; public int maxTextureSize; public TextureImporterNPOTScale npotScale;
        public TextureImporterPlatformSettings GetDefaultPlatformTextureSettings() => null; public TextureImporterPlatformSettings GetPlatformTextureSettings(string p) => null;
        public void SetPlatformTextureSettings(TextureImporterPlatformSettings s) { } }
    namespace SceneManagement { public static class EditorSceneManager { public static bool MarkSceneDirty(UnityEngine.SceneManagement.Scene s) => true; } }
}
namespace UdonSharp
{
    public abstract class UdonSharpBehaviour : UnityEngine.MonoBehaviour { }
    public enum BehaviourSyncMode { Any, None, Continuous, Manual, NoVariableSync }
    [AttributeUsage(AttributeTargets.Class)] public sealed class UdonBehaviourSyncModeAttribute : Attribute { public UdonBehaviourSyncModeAttribute(BehaviourSyncMode m) { } }
}
namespace VRC.SDKBase { public static class VRCShader { public static int PropertyToID(string name) => 0; public static void SetGlobalVector(int id, UnityEngine.Vector4 v) { } } }
namespace UnityEditor
{
    public class MonoScript : UnityEngine.Object { public static MonoScript FromMonoBehaviour(UnityEngine.MonoBehaviour b) => null; }
}
namespace UnityEngine
{
    public class ScriptableObject : Object { public static ScriptableObject CreateInstance(System.Type t) => null; }
}
