// 蓝白 · 触手之门 · 云的运行时（UdonSharp）  gate clouds kit v1, 2026-10-22, cloud art team.
// !!! NOT COMPILED IN UNITY: compile with UdonSharp and check. !!!
//
// Filled by LanbaiGateCloudsBuilder (蓝白/Gate Clouds/Build). The act interface of CONTROL_总控.md §5:
//     LanbaiTick(t)        every frame inside LanbaiWindow() (t = timeline seconds)
//     LanbaiActivate(on)   `root` (GateRoot/GateClouds) on / off, only under an occluder; the driver itself sits on an
//                          always-active object (Director v1 rule: never switch off the object you live on)
//     LanbaiWindow()       {U6 - 20, U9 + 2} = {113.80, 181.55} (GateRoot's own window)
// (Apply() with the public `t` does the same as LanbaiTick, for a caller that sets t itself.)
// Start() / _Init(): every card gets its MaterialPropertyBlock (_Mirror, _Gain, _Alpha = opacity): property blocks are not
// saved with the scene, so they are written at runtime.
// Apply(): the towers SAG (localScale.y x sag, pivot on the base), SINK (localPosition.y + sink) and fade out in their
// last 2 s (alpha); a renderer turns off at alpha 0 (GateLayout_v2.json towers, unchanged).
// Keys are flattened (t0, v0, t1, v1, ...) per card, smoothstep between keys, held outside them.
// D-44 #3 (2026-10-25): the arms' roots in 阿白's volume cloud. Every frame inside the window: _Udon_CloudVolume /
// _Udon_CloudVolumeWind / _Udon_CloudVolumeTex (copied by the builder from the volume deck's material, so the arms and
// the deck read one density) and the SKIRTS: every arm's baked root centreline (GateClouds_Skirts.json) is transformed,
// the point where it crosses the cloud top - skirtLevel is found (a root above that level: the root itself, the shader
// stretches it down), and the 8 nearest to the bus go to _Udon_GateSkirt0..7 (x, z, strength = the arm's reveal, r) +
// _Udon_GateSkirtK (count, width, climb, strength). LanbaiCloudVolume.cginc reads them (the deck and TentacleSway v2.8).
using UdonSharp;
using VRC.SDKBase;
using UnityEngine;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiGateClouds : UdonSharpBehaviour
{
    [Header("Timeline seconds (set by the Director before Apply)")]
    public float t;

    [Header("The clouds' root (GateRoot/GateClouds), switched by LanbaiActivate")]
    public GameObject root;

    [Header("All cards (builder)")]
    public Renderer[] cardRenderers;
    public float[] cardMirror;
    public float[] cardGain;
    public float[] cardOpacity;

    [Header("Towers (builder)")]
    public Transform[] towers;
    public Renderer[] towerRenderers;
    public float[] towerOpacity;
    public float[] towerMirror;
    public float[] towerGain;
    public float[] towerBaseY;
    public float[] towerBaseScaleY;
    public float[] sagKeys;
    public int[] sagStart;
    public int[] sagCount;
    public float[] sinkKeys;
    public int[] sinkStart;
    public int[] sinkCount;
    public float[] alphaKeys;
    public int[] alphaStart;
    public int[] alphaCount;

    [Header("D-44 #3: the volume cloud and the arms' skirts (builder)")]
    public Texture3D cloudVolumeTex;                                  // the volume deck material's _NoiseVolume (null = no volume)
    public Vector4 cloudVolume = new Vector4(1f, 0.036f, 520f, 260f); // x 1, y extinction / m (_Density), z / w periods m
    public Vector4 cloudWind = new Vector4(8f, 3f, 0f, 0f);           // xy the deck's _CloudWind.xy
    public Transform gateRoot;                                        // GateRoot: the cloud top = GateRoot.y - 150 (= -h_bus)
    public Transform[] skirtArms;
    public float[] skirtPts;                                          // object-space centreline points (xyz) of every arm
    public int[] skirtPtStart;                                        // first point (index / 3) per arm
    public int[] skirtPtCount;
    public float[] skirtR;                                            // radius per point (m)
    public float[] skirtRevKeys;                                      // the arm's reveal keys (t, v), from the gate bake
    public int[] skirtRevStart;
    public int[] skirtRevCount;
    public float skirtLevel = 40f;                                    // the crossing: cloud top - this (m)
    public Vector4 skirtK = new Vector4(0f, 1.3f, 26f, 2.2f);          // x count (runtime), y width x r, z climb m, w strength

    private MaterialPropertyBlock _mpb;
    private int _idVol, _idWind, _idVolTex, _idSkK;
    private int[] _idSk;
    private float[] _cd, _cx, _cz, _cr, _ck;
    private bool[] _cUsed;
    private int _idAlpha, _idMirror, _idGain;
    // act 4's haze band for every LanbaiFog user (Common/UdonGlobals.md: act 4 = the gate's driver): LANBAI_GATE_NEAR
    private float[] _window;
    private bool _warnedMissing;
    // the fog band (_Udon_FogBand*) is NOT written here any more: D-22 gives the whole fog / moon / star family on
    // [U6, U9) to LanbaiGateDriver (one writer per global)

    public void LanbaiTick(float time)
    {
        if (_mpb == null) _Init();             // activated and ticked in the same frame: Start has not run yet (tech r1 #9)
        t = time;
        Apply();
    }

    public void LanbaiActivate(bool on)
    {
        if (root != null) root.SetActive(on);
        if (_mpb == null) _Init();
        if (!on)
        {
            // the arms are off: no volume mode, no skirts (one writer: this driver, inside the gate's window)
            VRCShader.SetGlobalVector(_idVol, Vector4.zero);
            skirtK.x = 0f;
            VRCShader.SetGlobalVector(_idSkK, skirtK);
        }
        else if (cloudVolumeTex != null) VRCShader.SetGlobalTexture(_idVolTex, cloudVolumeTex);
    }

    // written by the builder from GateClouds_Layout.json "window" = {U6 - 20, U9 + 2} (FromLocal/cues.json labels)
    public float windowStart = 113.80f;
    public float windowEnd = 181.55f;

    public float[] LanbaiWindow()
    {
        if (_window == null) _window = new float[] { windowStart, windowEnd };   // no garbage per call
        return _window;
    }

    void Start()
    {
        if (_mpb == null) _Init();
    }

    // the set-up, callable before Start (tech r2 #7: an event method is not called as a plain method)
    public void _Init()
    {
        _mpb = new MaterialPropertyBlock();
        _idAlpha = VRCShader.PropertyToID("_Alpha");
        _idMirror = VRCShader.PropertyToID("_Mirror");
        _idGain = VRCShader.PropertyToID("_Gain");
        _idVol = VRCShader.PropertyToID("_Udon_CloudVolume");
        _idWind = VRCShader.PropertyToID("_Udon_CloudVolumeWind");
        _idVolTex = VRCShader.PropertyToID("_Udon_CloudVolumeTex");
        _idSkK = VRCShader.PropertyToID("_Udon_GateSkirtK");
        _idSk = new int[8];
        for (int k = 0; k < 8; k++) _idSk[k] = VRCShader.PropertyToID("_Udon_GateSkirt" + k);
        int na = skirtArms != null ? skirtArms.Length : 0;
        _cd = new float[na]; _cx = new float[na]; _cz = new float[na]; _cr = new float[na]; _ck = new float[na];
        _cUsed = new bool[na];
        if (cloudVolumeTex != null) VRCShader.SetGlobalTexture(_idVolTex, cloudVolumeTex);
        for (int i = 0; i < cardRenderers.Length; i++)
        {
            if (cardRenderers[i] == null) continue;
            _mpb.Clear();
            _mpb.SetFloat(_idMirror, cardMirror[i]);
            _mpb.SetFloat(_idGain, cardGain[i]);
            _mpb.SetFloat(_idAlpha, cardOpacity[i]);
            cardRenderers[i].SetPropertyBlock(_mpb);
        }
    }

    float Smooth(float x)
    {
        x = Mathf.Clamp01(x);
        return x * x * (3f - 2f * x);
    }

    float Key(float[] keys, int start, int count, float time, float dflt)
    {
        if (count <= 0) return dflt;
        if (time <= keys[start]) return keys[start + 1];
        int last = start + 2 * (count - 1);
        if (time >= keys[last]) return keys[last + 1];
        for (int k = start; k < last; k += 2)
        {
            float t0 = keys[k], t1 = keys[k + 2];
            if (time >= t0 && time <= t1)
                return Mathf.Lerp(keys[k + 1], keys[k + 3], Smooth((time - t0) / Mathf.Max(t1 - t0, 1e-4f)));
        }
        return keys[last + 1];
    }

    // D-44 #3: the volume globals and the 8 nearest skirts (see the header)
    void Skirts()
    {
        if (cloudVolumeTex == null || gateRoot == null || skirtArms == null)
        {
            VRCShader.SetGlobalVector(_idVol, Vector4.zero);              // no volume deck: TentacleSway v2.7d behaviour
            return;
        }
        VRCShader.SetGlobalVector(_idVol, cloudVolume);
        VRCShader.SetGlobalVector(_idWind, cloudWind);
        float yl = gateRoot.position.y - 150f - skirtLevel;
        int n = 0;
        for (int i = 0; i < skirtArms.Length; i++)
        {
            _cUsed[i] = true;
            Transform tr = skirtArms[i];
            if (tr == null || !tr.gameObject.activeInHierarchy) continue;
            float k = Key(skirtRevKeys, skirtRevStart[i], skirtRevCount[i], t, 1f);
            if (k <= 0f) continue;
            int p0 = skirtPtStart[i], pc = skirtPtCount[i];
            if (pc < 1) continue;
            Vector3 a = tr.TransformPoint(new Vector3(skirtPts[3 * p0], skirtPts[3 * p0 + 1], skirtPts[3 * p0 + 2]));
            bool hit = false;
            float hx = 0f, hz = 0f, hr = 0f;
            if (a.y >= yl) { hit = true; hx = a.x; hz = a.z; hr = skirtR[p0]; }   // the root stands above: its stem
            else
            {
                for (int j = 1; j < pc; j++)
                {
                    int q = p0 + j;
                    Vector3 b = tr.TransformPoint(new Vector3(skirtPts[3 * q], skirtPts[3 * q + 1], skirtPts[3 * q + 2]));
                    if (b.y >= yl)
                    {
                        float f = (yl - a.y) / Mathf.Max(b.y - a.y, 1e-4f);
                        hx = a.x + (b.x - a.x) * f; hz = a.z + (b.z - a.z) * f;
                        hr = skirtR[q - 1] + (skirtR[q] - skirtR[q - 1]) * f;
                        hit = true;
                        break;
                    }
                    a = b;
                }
            }
            if (!hit) continue;                                          // still under the level (rising)
            _cd[i] = hx * hx + hz * hz;                                   // from the bus (world origin)
            _cx[i] = hx; _cz[i] = hz; _cr[i] = hr; _ck[i] = Mathf.Clamp01(k);
            _cUsed[i] = false;
            n++;
        }
        int slots = Mathf.Min(n, 8);
        for (int s = 0; s < 8; s++)
        {
            int best = -1;
            if (s < slots)
                for (int i = 0; i < _cd.Length; i++)
                    if (!_cUsed[i] && (best < 0 || _cd[i] < _cd[best])) best = i;
            if (best < 0) { VRCShader.SetGlobalVector(_idSk[s], Vector4.zero); continue; }
            _cUsed[best] = true;
            VRCShader.SetGlobalVector(_idSk[s], new Vector4(_cx[best], _ck[best], _cz[best], _cr[best]));
        }
        skirtK.x = slots;
        VRCShader.SetGlobalVector(_idSkK, skirtK);
    }

    public void Apply()
    {
        if (_mpb == null) _Init();
        Skirts();
        for (int i = 0; i < towers.Length; i++)
        {
            Transform tr = towers[i];
            if (tr == null) continue;
            float sag = Key(sagKeys, sagStart[i], sagCount[i], t, 1f);
            float sink = Key(sinkKeys, sinkStart[i], sinkCount[i], t, 0f);
            float a = Key(alphaKeys, alphaStart[i], alphaCount[i], t, 1f);
            Vector3 s = tr.localScale;
            s.y = towerBaseScaleY[i] * sag;
            tr.localScale = s;
            Vector3 p = tr.localPosition;
            p.y = towerBaseY[i] + sink;
            tr.localPosition = p;
            Renderer r = towerRenderers[i];
            if (r == null)
            {
                // the gate was rebuilt after the clouds: skip, warn once (v1.5, 总导演 A4)
                if (!_warnedMissing) Debug.LogWarning("[GateClouds] a tower renderer is missing: please re-run 蓝白/Gate Clouds/Build");
                _warnedMissing = true;
                continue;
            }
            bool on = a > 0.001f;
            if (r.enabled != on) r.enabled = on;
            if (!on) continue;
            _mpb.Clear();
            _mpb.SetFloat(_idMirror, towerMirror[i]);
            _mpb.SetFloat(_idGain, towerGain[i]);
            _mpb.SetFloat(_idAlpha, towerOpacity[i] * a);
            r.SetPropertyBlock(_mpb);
        }
    }
}
