// Compile-check stub of com.unity.postprocessing 3.x public API (signatures copied from the real source,
// Unity-Technologies/Graphics master com.unity.postprocessing/PostProcessing/Runtime). Bodies are fake.
using System;
using System.Collections.Generic;
namespace UnityEngine.Rendering.PostProcessing
{
    public abstract class ParameterOverride
    {
        public bool overrideState;
        public abstract int GetHash();
        public T GetValue<T>() { return default(T); }
    }
    [Serializable]
    public class ParameterOverride<T> : ParameterOverride
    {
        public T value;
        public ParameterOverride() : this(default(T), false) { }
        public ParameterOverride(T value) : this(value, false) { }
        public ParameterOverride(T value, bool overrideState) { this.value = value; this.overrideState = overrideState; }
        public virtual void Interp(T from, T to, float t) { value = t > 0f ? to : from; }
        public void Override(T x) { overrideState = true; value = x; }
        public override int GetHash() { return 0; }
        public static implicit operator T(ParameterOverride<T> prop) { return prop.value; }
    }
    [Serializable] public sealed class FloatParameter : ParameterOverride<float> { }
    [Serializable] public sealed class IntParameter : ParameterOverride<int> { }
    [Serializable] public sealed class BoolParameter : ParameterOverride<bool> { }
    [Serializable] public sealed class ColorParameter : ParameterOverride<Color> { }
    [Serializable] public sealed class Vector2Parameter : ParameterOverride<Vector2> { }
    [Serializable] public sealed class Vector3Parameter : ParameterOverride<Vector3> { }
    [Serializable] public sealed class Vector4Parameter : ParameterOverride<Vector4> { }
    public enum TextureParameterDefault { None, Black, White, Transparent, Lut2D }
    [Serializable] public sealed class TextureParameter : ParameterOverride<Texture> { public TextureParameterDefault defaultState = TextureParameterDefault.Black; }

    [Serializable]
    public class PostProcessEffectSettings : ScriptableObject
    {
        public bool active = true;
        public BoolParameter enabled = new BoolParameter { overrideState = true, value = false };
        public void SetAllOverridesTo(bool state, bool excludeEnabled = true) { }
        public int GetHash() { return 0; }
    }

    public enum GradingMode { LowDefinitionRange, HighDefinitionRange, External }
    public enum Tonemapper { None, Neutral, ACES, Custom }
    [Serializable] public sealed class GradingModeParameter : ParameterOverride<GradingMode> { }
    [Serializable] public sealed class TonemapperParameter : ParameterOverride<Tonemapper> { }
    [Serializable]
    public sealed class ColorGrading : PostProcessEffectSettings
    {
        public GradingModeParameter gradingMode = new GradingModeParameter { value = GradingMode.HighDefinitionRange };
        public TextureParameter externalLut = new TextureParameter { value = null };
        public TonemapperParameter tonemapper = new TonemapperParameter { value = Tonemapper.None };
        public TextureParameter ldrLut = new TextureParameter { value = null, defaultState = TextureParameterDefault.Lut2D };
        public FloatParameter ldrLutContribution = new FloatParameter { value = 1f };
        public FloatParameter temperature = new FloatParameter { value = 0f };
        public FloatParameter tint = new FloatParameter { value = 0f };
        public ColorParameter colorFilter = new ColorParameter { value = Color.white };
        public FloatParameter hueShift = new FloatParameter { value = 0f };
        public FloatParameter saturation = new FloatParameter { value = 0f };
        public FloatParameter brightness = new FloatParameter { value = 0f };
        public FloatParameter postExposure = new FloatParameter { value = 0f };
        public FloatParameter contrast = new FloatParameter { value = 0f };
        public Vector4Parameter lift = new Vector4Parameter { value = new Vector4(1f, 1f, 1f, 0f) };
        public Vector4Parameter gamma = new Vector4Parameter { value = new Vector4(1f, 1f, 1f, 0f) };
        public Vector4Parameter gain = new Vector4Parameter { value = new Vector4(1f, 1f, 1f, 0f) };
        public FloatParameter mixerRedOutRedIn = new FloatParameter { value = 100f };
        public FloatParameter mixerRedOutGreenIn = new FloatParameter { value = 0f };
        public FloatParameter mixerRedOutBlueIn = new FloatParameter { value = 0f };
        public FloatParameter mixerGreenOutRedIn = new FloatParameter { value = 0f };
        public FloatParameter mixerGreenOutGreenIn = new FloatParameter { value = 100f };
        public FloatParameter mixerGreenOutBlueIn = new FloatParameter { value = 0f };
        public FloatParameter mixerBlueOutRedIn = new FloatParameter { value = 0f };
        public FloatParameter mixerBlueOutGreenIn = new FloatParameter { value = 0f };
        public FloatParameter mixerBlueOutBlueIn = new FloatParameter { value = 100f };
    }
    [Serializable]
    public sealed class Bloom : PostProcessEffectSettings
    {
        public FloatParameter intensity = new FloatParameter { value = 0f };
        public FloatParameter threshold = new FloatParameter { value = 1f };
        public FloatParameter softKnee = new FloatParameter { value = 0.5f };
        public FloatParameter clamp = new FloatParameter { value = 65472f };
        public FloatParameter diffusion = new FloatParameter { value = 7f };
        public FloatParameter anamorphicRatio = new FloatParameter { value = 0f };
        public ColorParameter color = new ColorParameter { value = Color.white };
        public BoolParameter fastMode = new BoolParameter { value = false };
        public TextureParameter dirtTexture = new TextureParameter { value = null };
        public FloatParameter dirtIntensity = new FloatParameter { value = 0f };
    }
    public enum VignetteMode { Classic, Masked }
    [Serializable] public sealed class VignetteModeParameter : ParameterOverride<VignetteMode> { }
    [Serializable]
    public sealed class Vignette : PostProcessEffectSettings
    {
        public VignetteModeParameter mode = new VignetteModeParameter { value = VignetteMode.Classic };
        public ColorParameter color = new ColorParameter { value = new Color(0f, 0f, 0f, 1f) };
        public Vector2Parameter center = new Vector2Parameter { value = new Vector2(0.5f, 0.5f) };
        public FloatParameter intensity = new FloatParameter { value = 0f };
        public FloatParameter smoothness = new FloatParameter { value = 0.2f };
        public FloatParameter roundness = new FloatParameter { value = 1f };
        public BoolParameter rounded = new BoolParameter { value = false };
        public TextureParameter mask = new TextureParameter { value = null };
        public FloatParameter opacity = new FloatParameter { value = 1f };
    }
    [Serializable]
    public sealed class Grain : PostProcessEffectSettings
    {
        public BoolParameter colored = new BoolParameter { value = true };
        public FloatParameter intensity = new FloatParameter { value = 0f };
        public FloatParameter size = new FloatParameter { value = 1f };
        public FloatParameter lumContrib = new FloatParameter { value = 0.8f };
    }
    [Serializable] public sealed class AutoExposure : PostProcessEffectSettings { }
    [Serializable] public sealed class MotionBlur : PostProcessEffectSettings { }
    [Serializable] public sealed class DepthOfField : PostProcessEffectSettings { }
    [Serializable] public sealed class ChromaticAberration : PostProcessEffectSettings { }
    [Serializable] public sealed class LensDistortion : PostProcessEffectSettings { }
    [Serializable] public sealed class AmbientOcclusion : PostProcessEffectSettings { }
    [Serializable] public sealed class ScreenSpaceReflections : PostProcessEffectSettings { }

    public sealed class PostProcessProfile : ScriptableObject
    {
        public List<PostProcessEffectSettings> settings = new List<PostProcessEffectSettings>();
        [NonSerialized] public bool isDirty = true;
        public T AddSettings<T>() where T : PostProcessEffectSettings { return (T)AddSettings(typeof(T)); }
        public PostProcessEffectSettings AddSettings(Type type) { return null; }
        public PostProcessEffectSettings AddSettings(PostProcessEffectSettings effect) { return effect; }
        public void RemoveSettings<T>() where T : PostProcessEffectSettings { }
        public void RemoveSettings(Type type) { }
        public bool HasSettings<T>() where T : PostProcessEffectSettings { return false; }
        public bool HasSettings(Type type) { return false; }
        public T GetSetting<T>() where T : PostProcessEffectSettings { return null; }
        public bool TryGetSettings<T>(out T outSetting) where T : PostProcessEffectSettings { outSetting = null; return false; }
    }

    public sealed class PostProcessVolume : MonoBehaviour
    {
        public PostProcessProfile sharedProfile;
        public bool isGlobal = false;
        public float blendDistance = 0f;
        public float weight = 1f;
        public float priority = 0f;
        public PostProcessProfile profile { get { return null; } set { } }
        public bool HasInstantiatedProfile() { return false; }
    }

    public sealed class PostProcessResources : ScriptableObject { }

    public sealed class PostProcessLayer : MonoBehaviour
    {
        public enum Antialiasing { None, FastApproximateAntialiasing, SubpixelMorphologicalAntialiasing, TemporalAntialiasing }
        public Transform volumeTrigger;
        public LayerMask volumeLayer;
        public bool stopNaNPropagation = true;
        public bool finalBlitToCameraTarget = false;
        public Antialiasing antialiasingMode = Antialiasing.None;
        public bool breakBeforeColorGrading = false;
        public void Init(PostProcessResources resources) { }
        public void InitBundles() { }
        public void ResetHistory() { }
    }
}
