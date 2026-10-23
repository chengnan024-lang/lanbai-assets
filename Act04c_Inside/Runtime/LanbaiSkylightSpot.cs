// Lanbai / 蓝白 -- LanbaiSkylightSpot: the brightness envelope of the skylight spot, beam and dust (act 4, U8 -> U9).
// UdonSharp 1.x. UNCOMPILED (cloud side; Roslyn type-check only). The geometry is projected in the shader
// (Lanbai/SkylightSpot) from the gate's _Udon_TearPos / _Udon_TearH, so this only writes one global and switches renderers.
//   U8 -> U8b + 1.3 (~169.2): EV-linear from -5 EV to full (the wound reaches the middle of the skylight)
//   ~169.2 -> U9: smoothstep down to 0.6 (the wound outgrows the skylight; the gate's light keeps falling in)
//   U9 -> U9 + 0.25: to 0 with the tear light (the tubes die in the same quarter second)
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiSkylightSpot : UdonSharpBehaviour
{
    public float tU8 = 166.15f;
    public float tPeak = 169.20f;
    public float tU9 = 179.55f;
    public float evFrom = -5f;
    public float holdTo = 0.6f;
    public Renderer[] renderers;

    private int _id;
    private bool _ready;
    private bool _on;

    void Start()
    {
        Init();
        SetOn(false);
    }

    private void Init()
    {
        if (_ready) return;
        _id = VRCShader.PropertyToID("_Udon_SkySpot");
        _ready = true;
    }

    public float[] LanbaiWindow()
    {
        return new float[] { tU8 - 0.5f, tU9 + 0.5f };
    }

    public void LanbaiActivate(bool on)
    {
        SetOn(on);
    }

    public float Envelope(float t)
    {
        if (t <= tU8) return 0f;
        if (t < tPeak) return Mathf.Pow(2f, evFrom * (1f - (t - tU8) / (tPeak - tU8)));
        if (t < tU9)
        {
            float x = Mathf.Clamp01((t - tPeak) / (tU9 - tPeak));
            return Mathf.Lerp(1f, holdTo, x * x * (3f - 2f * x));
        }
        if (t < tU9 + 0.25f) return holdTo * (1f - (t - tU9) / 0.25f);
        return 0f;
    }

    public void LanbaiTick(float t)
    {
        Init();
        float e = Envelope(t);
        VRCShader.SetGlobalVector(_id, new Vector4(e, 0f, 0f, 0f));
        SetOn(e > 0f);
    }

    private void SetOn(bool on)
    {
        if (on == _on || renderers == null) { _on = on; return; }
        _on = on;
        for (int i = 0; i < renderers.Length; i++)
            if (renderers[i] != null) renderers[i].enabled = on;
    }
}
