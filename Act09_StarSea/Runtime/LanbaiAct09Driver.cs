// 蓝白 · 第 9 幕（星海）的天：驱动（UdonSharp）。
// !!! NOT COMPILED IN UNITY / UdonSharp: Roslyn type-check against UnityEngine 2021.1 + a U# stub only. !!!
//
// Interface (CONTROL_总控.md §5): the Director's dispatcher calls LanbaiTick(t) every frame inside LanbaiWindow(),
// LanbaiActivate(on) only under occlusion. Every number comes from Act09_StarSea/Act09_StarSea.json; the build menu
// 蓝白/Build/Act09 fills these fields (do not hand-edit). This behaviour sits on its own always-active object
// (Lanbai_Act09Driver); `root` (R_StarSea) holds only the two star renderers.
// It writes, from the act's start (1001.21; before that the 8b driver owns them):
//   _Udon_SkyBlend = (0, 1, night, 1)   night 0 -> 1 over 1001.21 -> 1009.21 (directional in the shader)
//   _Udon_SkyFx    = (0, band1, 0, 1)   the blue-hour band stays, the night layer covers it
//   _Udon_GalaxyGain = (g(s), gCore(s), 1, 1) x (1 + 0.8 x^2.5) on x and y: the arms and the galactic core
//                      (LanbaiGalaxyGainAt; gCore = the same breath a little ahead, so the light spreads along the
//                      band), s = t - F13
//   _Udon_StarGain   = (F13 ? 1 : 0, 4 + 4 x^2.5, 50 + 150 x^2.5, 1)
//   _Udon_Fog = (0, 0, 0, 1)
// and from 1009.21 the star floor (night + g x floorAdd, 1) into _Udon_ZenithColor (the mirrors read it),
// _Udon_HorizonColor, _Udon_FogBandColor and _Udon_NadirColor (as the star_sea preset: LanbaiHorizon is the floor too);
// plus the first stars' MaterialPropertyBlock (no globals). Per frame: 5 SetGlobalVector (9 from 1009.21), 1 MPB,
// no loops, no allocation.
// Taking over (Engineering/README_集成.md §9.5, D-33 #6): the first tick at t >= 1001.21 after an activation (or after the
// timeline went back before 1001.21) applies the whole blue_hour preset once (handoffPreset.Apply(): all the sky's
// globals, the same values act 8b leaves), then writes its own on top in the same frame: a late joiner or a seek
// lands on the same sky as watching from the start. Not before 1001.21 (the sky is still act 8b's then).
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

namespace Lanbai.Act09
{
    [UdonBehaviourSyncMode(BehaviourSyncMode.None)]
    public class LanbaiAct09Driver : UdonSharpBehaviour
    {
        [Header("Roots and renderers (filled by 蓝白/Build/Act09)")]
        public GameObject root;
        public Lanbai.Sky.LanbaiSkyPreset handoffPreset;  // Lanbai_SkyPresets/SkyPreset_blue_hour
        public Renderer firstStars;
        public Renderer questionStars;

        [Header("Labels (timeline seconds, from Act09_StarSea.json)")]
        public float tBlueHour = 993.06f;
        public float tActStart = 1001.21f;
        public float tDarkEnd = 1009.21f;
        public float tF13 = 1018.21f;
        public float tF16 = 1149.31f;

        [Header("Ignition tables from F13, step 0.05 s: the arms (g) and the galactic core")]
        public float[] gTable;
        public float[] gCoreTable;                        // empty = the core runs gTable (no lead)
        public float gStep = 0.05f;

        [Header("Sky")]
        public float band1Gain = 0.85f;
        public Vector3 nightColor = new Vector3(0.0015f, 0f, 0f);
        public Vector3 floorAdd = new Vector3(0.0025f, 0.0048f, 0.017f);

        [Header("First stars of the blue hour")]
        public float firstAppear0 = 994.06f;
        public float firstAppear1 = 997.06f;
        public float firstPeak = 0.55f;
        public float firstOutSeconds = 0.8f;

        private int idSkyBlend, idSkyFx, idGalaxy, idStar, idZenith, idFog, idHorizon, idFogBand, idNadir;
        private int idGain, idOrderFade;
        private MaterialPropertyBlock mpb;
        private bool ready;
        private bool _full;                               // blue_hour applied since the activation / the last seek back

        void Start()
        {
            Init();
        }

        private void Init()
        {
            if (ready)
                return;
            idSkyBlend = VRCShader.PropertyToID("_Udon_SkyBlend");
            idSkyFx = VRCShader.PropertyToID("_Udon_SkyFx");
            idGalaxy = VRCShader.PropertyToID("_Udon_GalaxyGain");
            idStar = VRCShader.PropertyToID("_Udon_StarGain");
            idZenith = VRCShader.PropertyToID("_Udon_ZenithColor");
            idFog = VRCShader.PropertyToID("_Udon_Fog");
            idHorizon = VRCShader.PropertyToID("_Udon_HorizonColor");
            idFogBand = VRCShader.PropertyToID("_Udon_FogBandColor");
            idNadir = VRCShader.PropertyToID("_Udon_NadirColor");
            idGain = VRCShader.PropertyToID("_Gain");
            idOrderFade = VRCShader.PropertyToID("_OrderFade");
            mpb = new MaterialPropertyBlock();
            ready = true;
        }

        public float[] LanbaiWindow()
        {
            return new float[] { tBlueHour - 1f, tF16 };
        }

        public void LanbaiActivate(bool on)
        {
            _full = false;
            if (root != null)
                root.SetActive(on);
        }

        // a table at s = seconds after F13 (linear interpolation; 0 before F13, 1 after its end)
        public float TableAt(float[] tab, float s)
        {
            if (s <= 0f || tab == null || tab.Length == 0)
                return 0f;
            float f = s / gStep;
            int i = (int)Mathf.Floor(f);
            if (i >= tab.Length - 1)
                return 1f;
            return Mathf.Lerp(tab[i], tab[i + 1], f - i);
        }

        public float IgnitionGain(float s)
        {
            return TableAt(gTable, s);
        }

        public void LanbaiTick(float t)
        {
            Init();
            float x = Mathf.Clamp01((t - tF13) / (tF16 - tF13));
            float x25 = Mathf.Pow(x, 2.5f);

            // first stars: appear in the blue hour, go out one by one in the darkening (order 0 first, order 1 =
            // the zenith star at tDarkEnd): order threshold sweeps 0 -> 1 + soft over [tActStart + 2, tDarkEnd]
            if (firstStars != null)
            {
                float a = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(firstAppear0, firstAppear1, t));
                float sweep = Mathf.InverseLerp(tActStart + 0.25f * (tDarkEnd - tActStart), tDarkEnd, t);
                float soft = 0.5f * firstOutSeconds / Mathf.Max(0.75f * (tDarkEnd - tActStart), 0.01f);
                firstStars.GetPropertyBlock(mpb);
                mpb.SetFloat(idGain, (t < tDarkEnd + firstOutSeconds) ? a * firstPeak : 0f);
                // stars whose order is below the threshold are OFF (z = 1): threshold runs from -soft to 1 + soft
                mpb.SetVector(idOrderFade, new Vector4(Mathf.Lerp(-soft, 1f + soft, sweep), soft, 1f, 0f));
                firstStars.SetPropertyBlock(mpb);
                firstStars.enabled = t >= firstAppear0 && t < tDarkEnd + firstOutSeconds;   // built disabled
            }

            if (questionStars != null)
                questionStars.enabled = t >= tF13;        // built disabled; also off again when the timeline seeks back

            if (t < tActStart)
            {
                _full = false;                            // a seek back before the takeover: write it all again later
                return;                                   // the 8b driver still owns the sky globals
            }
            if (!_full)
            {
                if (handoffPreset != null)
                    handoffPreset.Apply();                // all of blue_hour once; ours are written on top below
                _full = true;
            }

            float night = Mathf.Clamp01((t - tActStart) / (tDarkEnd - tActStart));
            VRCShader.SetGlobalVector(idSkyBlend, new Vector4(0f, 1f, night, 1f));
            VRCShader.SetGlobalVector(idSkyFx, new Vector4(0f, band1Gain, 0f, 1f));
            VRCShader.SetGlobalVector(idFog, new Vector4(0f, 0f, 0f, 1f));

            float s = t - tF13;
            float climax = 1f + 0.8f * x25;
            float g = TableAt(gTable, s) * climax;
            float gc = (gCoreTable != null && gCoreTable.Length > 0) ? TableAt(gCoreTable, s) * climax : g;
            VRCShader.SetGlobalVector(idGalaxy, new Vector4(g, gc, 1f, 1f));
            bool lit = t >= tF13;
            VRCShader.SetGlobalVector(idStar, new Vector4(lit ? 1f : 0f, 4f + 4f * x25, 50f + 150f * x25, 1f));

            if (t >= tDarkEnd)
            {
                Vector3 z = nightColor + floorAdd * g;
                Vector4 floor = new Vector4(z.x, z.y, z.z, 1f);
                VRCShader.SetGlobalVector(idZenith, floor);
                VRCShader.SetGlobalVector(idHorizon, floor);
                VRCShader.SetGlobalVector(idFogBand, floor);
                VRCShader.SetGlobalVector(idNadir, floor);
            }
        }
    }
}
