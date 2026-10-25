// 蓝白 · 十三面白铜镜：驱动（UdonSharp）。第 9 幕 9c（1032.41 → F16）。
// !!! NOT COMPILED IN UNITY / UdonSharp: Roslyn type-check (Common/Tools~/compile_check/check_cs.sh) + U# stubs only. !!!
//
// Interface (CONTROL_总控.md §5 + 总工程师意见 第 1 轮): the Director's dispatcher calls LanbaiTick(t) every frame inside
// LanbaiWindow(), LanbaiActivate(on) only under occlusion, and LanbaiGrade(t) after the tick.  This driver NEVER touches
// PPv2 volumes: LanbaiGrade returns {dEV, WHITE_SAT, WHITE_BLOOM, lens multiplier} (the mirror pulses, +0.35 EV on
// crossings 1-11) and LB_Journey.ApplyGrades is the one writer of exposure (bible §1.4, ruling of 10-23).
// Every number comes from Mirrors/MirrorSchedule.json; the build menu 蓝白/Build/Mirrors bakes it into these arrays
// (Udon cannot read JSON).  Same maths as Mirrors/Tools~/port/mirror_port.py (mirror_state, pulse_ev).
// Writes per frame: one transform + one MaterialPropertyBlock per active mirror (x3 LOD renderers), one MPB per
// reflected-star copy and per dust slot, two globals (_Udon_MirrorPlane, _Udon_MirrorRimLight).  No allocation in Tick.
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

namespace Lanbai.Mirrors
{
    [UdonBehaviourSyncMode(BehaviourSyncMode.None)]
    public class LanbaiMirrorsDriver : UdonSharpBehaviour
    {
        [Header("Objects (filled by 蓝白/Build/Mirrors)")]
        public GameObject root;                     // R_Mirrors: switched by LanbaiActivate
        public Transform[] mirrors;                 // 13, each with a LODGroup and 3 renderers
        public Renderer[] lodRenderers;             // 13 x 3 (LOD0, LOD1, LOD2 of mirror k at 3k .. 3k+2)
        public Renderer[] starCopies;               // 7 slots: mirror k (1-12) -> slot (k-1) % 6, mirror 13 -> slot 6
        public Renderer[] dustSlots;                // 3 slots: mirror k (1-12) -> slot (k-1) % 3

        [Header("Window (timeline s)")]
        public float windowStart = 1010.0f;         // in act 9's black (天问), before any mirror is lit
        public float windowEnd = 1150.31f;          // F16 + 1 s, under the full white: the ticks after F16 switch mirror 13 off and zero the globals

        [Header("Per mirror (13), from MirrorSchedule.json")]
        public float[] tCross;
        public float[] diameter;
        public float[] centreX;
        public float[] centreZ;
        public float[] emissionK;
        public float[] pulseEV;
        public float[] activeStart;
        public float[] activeEnd;
        public float[] dissolveEnd;                 // 0 = never dissolves (mirror 13)
        public float[] crossSpeed;                  // face rise speed after the crossing (dust birth height)
        public int[] knotStart;                     // motion knots of mirror k: knotT/Y/V[knotStart[k] .. + knotCount[k]]
        public int[] knotCount;
        public float[] knotT;
        public float[] knotY;
        public float[] knotV;
        public int[] visStart;                      // visibility knots (linear)
        public int[] visCount;
        public float[] visT;
        public float[] visV;

        [Header("Mirror 13: extra face emission EV (WhiteSchedule.json mirror13_face_extra, linear)")]
        public float[] extraT = new float[] { 1138.78f, 1146.31f };
        public float[] extraV = new float[] { 0f, 2.7f };     // r3 C3: +2.7 EV (looking down with WHITE_BLOOM <= 220)
        [Header("Mirror 13 far (终审 M-4): the bible's blurred giant disc until F16 - 10, one stop under the column")]
        public float farUntil = 1135.31f;           // far = 1 before this ...
        public float farSeconds = 4f;               // ... -> 0 at F16 - 10 (1139.31): sharp and full from then on (D-38)
        public float farDim = 0.5f;                 // face x 0.5 while far (one stop)
        public float farRimFrom = 0.35f;            // the soft rim starts at this fraction of the radius

        [Header("Constants (spec_conventions.md)")]
        public Vector3 eye = new Vector3(0.55f, 1.70f, 2.05f);
        public float appearSeconds = 3f;
        public float pulseIn = 0.08f;
        public float pulseOut = 0.35f;
        public float rimLightE = 0.3f;
        [Header("Rim light (总导演 F7, 10-24: one point light, no shadows, Not Important, culling Player + PlayerLocal)")]
        public Light rimLight;                      // built by 蓝白/Build/Mirrors; driven by the envelope, off at 0
        public float rimLightIntensity = 1.2f;      // intensity at the envelope peak (rimLightE)

        private const float FaceR = 0.48f;
        private const float Sag = 0.015f;
        private const float Rho = 7.6875f;

        private MaterialPropertyBlock mpb;
        private int idRadius, idK, idEmK, idVis, idExtra, idAppear, idDissolve, idRimSoft, idRimSoftFrom, idFaceSoft, idFarDim;
        private int idSphere, idAxis, idFaceK;
        private int idDustNow, idDustT0, idDustC, idDustCar, idDustOn;
        private int idPlane, idRimLight;
        private bool ready;
        private bool valid;                         // M2: all arrays present and of matching length
        private float[] grade = new float[4];

        // M1: precomputed per mirror (the eye and the centres never move) and per-frame caches, so a frame only touches the
        // few mirrors that are on and only writes what changed (every Udon operation is an extern call)
        private int n;
        private int[] slotOf;                       // star-copy slot
        private float[] yOff;                       // face point under the eye -> face edge (object y = 0), metres
        private Vector3[] rimPos;                   // nearest rim point, xz (y filled per frame)
        private float[] rimDistM;
        private Vector4[] dustC, dustCar;
        private bool[] onCache;
        private int[] activeList;
        private int activeCount;
        private float segA = 1e9f, segB = -1e9f;   // [segA, segB): the active set does not change inside
        private float[] events;                     // every activeStart / activeEnd / tCross / dissolveEnd + 4, sorted
        private int[] dustK;                        // per dust slot: the mirror it shows (-1 none)
        private bool[] starOn, dustOn;
        private bool rimLit;
        private float[] lastVis, lastAppear, lastDis, lastExtra;
        private float lastFar = -1f;

        void Start()
        {
            Init();
            ClearGlobals();                         // CONTROL §5: globals written in Start (editor values are lost on Play)
        }

        // review r1 #3: outside the window nothing may keep an eye-height mirror line or a rim light alive
        private void ClearGlobals()
        {
            VRCShader.SetGlobalVector(idPlane, Vector4.zero);
            VRCShader.SetGlobalVector(idRimLight, Vector4.zero);
        }

        private void Init()
        {
            if (ready)
                return;
            ready = true;
            mpb = new MaterialPropertyBlock();
            idRadius = VRCShader.PropertyToID("_RadiusM");
            idK = VRCShader.PropertyToID("_MirrorK");
            idEmK = VRCShader.PropertyToID("_EmissionK");
            idVis = VRCShader.PropertyToID("_Visibility");
            idExtra = VRCShader.PropertyToID("_EmitExtraEV");
            idAppear = VRCShader.PropertyToID("_Appear");
            idDissolve = VRCShader.PropertyToID("_Dissolve");
            idRimSoft = VRCShader.PropertyToID("_RimSoft");
            idRimSoftFrom = VRCShader.PropertyToID("_RimSoftFrom");
            idFaceSoft = VRCShader.PropertyToID("_FaceSoft");
            idFarDim = VRCShader.PropertyToID("_FarDim");
            idSphere = VRCShader.PropertyToID("_SphereC");
            idAxis = VRCShader.PropertyToID("_Axis");
            idFaceK = VRCShader.PropertyToID("_FaceK");
            idDustNow = VRCShader.PropertyToID("_DustNow");
            idDustT0 = VRCShader.PropertyToID("_DustT0");
            idDustC = VRCShader.PropertyToID("_DustC");
            idDustCar = VRCShader.PropertyToID("_DustCar");
            idDustOn = VRCShader.PropertyToID("_DustOn");
            idPlane = VRCShader.PropertyToID("_Udon_MirrorPlane");
            idRimLight = VRCShader.PropertyToID("_Udon_MirrorRimLight");

            // M2: a half-wired driver must not index out of range every frame: check, and stay idle if anything is off
            valid = tCross != null && mirrors != null && lodRenderers != null && starCopies != null && dustSlots != null;
            if (valid)
            {
                n = tCross.Length;
                valid = n > 0 && mirrors.Length == n && lodRenderers.Length == 3 * n && starCopies.Length >= 7 && dustSlots.Length >= 3
                    && diameter != null && diameter.Length == n && centreX != null && centreX.Length == n && centreZ != null && centreZ.Length == n
                    && emissionK != null && emissionK.Length == n && pulseEV != null && pulseEV.Length == n
                    && activeStart != null && activeStart.Length == n && activeEnd != null && activeEnd.Length == n
                    && dissolveEnd != null && dissolveEnd.Length == n && crossSpeed != null && crossSpeed.Length == n
                    && knotStart != null && knotStart.Length == n && knotCount != null && knotCount.Length == n
                    && visStart != null && visStart.Length == n && visCount != null && visCount.Length == n
                    && knotT != null && knotY != null && knotV != null && visT != null && visV != null
                    && extraT != null && extraV != null && extraT.Length == extraV.Length && extraT.Length > 0;
            }
            if (valid)
                for (int k = 0; k < n && valid; k++)
                    valid = mirrors[k] != null && knotCount[k] > 0 && knotStart[k] + knotCount[k] <= knotT.Length
                        && knotT.Length == knotY.Length && knotT.Length == knotV.Length
                        && visCount[k] > 0 && visStart[k] + visCount[k] <= visT.Length && visT.Length == visV.Length;
            if (!valid)
            {
                Debug.LogError("[Mirrors] LanbaiMirrorsDriver: arrays missing or of different lengths: run 蓝白/Build/Mirrors again. The driver stays idle.");
                return;
            }
            slotOf = new int[n]; yOff = new float[n]; rimPos = new Vector3[n]; rimDistM = new float[n];
            dustC = new Vector4[n]; dustCar = new Vector4[n]; onCache = new bool[n]; activeList = new int[n];
            lastVis = new float[n]; lastAppear = new float[n]; lastDis = new float[n]; lastExtra = new float[n];
            for (int k = 0; k < n; k++)
            {
                float D = diameter[k];
                slotOf[k] = (k == n - 1) ? 6 : (k % 6);
                float dx = eye.x - centreX[k], dz = eye.z - centreZ[k];
                float l2 = Mathf.Max(Mathf.Sqrt(dx * dx + dz * dz), 1e-3f);
                float rCar = Mathf.Min(l2 / D, FaceR);
                yOff[k] = (Mathf.Sqrt(Rho * Rho - rCar * rCar) - (Rho - Sag)) * D;
                rimPos[k] = new Vector3(centreX[k] + dx / l2 * 0.5f * D, 0f, centreZ[k] + dz / l2 * 0.5f * D);
                rimDistM[k] = Mathf.Abs(0.5f * D - l2);
                dustC[k] = new Vector4(centreX[k], eye.y - yOff[k], centreZ[k], 0.5f * D);
                dustCar[k] = new Vector4(dx, dz, crossSpeed[k], D);
                lastVis[k] = -1f;
                onCache[k] = mirrors[k].gameObject.activeSelf;
            }
            events = new float[4 * n];
            for (int k = 0; k < n; k++)
            {
                events[4 * k] = activeStart[k]; events[4 * k + 1] = activeEnd[k];
                events[4 * k + 2] = tCross[k]; events[4 * k + 3] = dissolveEnd[k] > 0f ? dissolveEnd[k] + 4f : activeEnd[k];
            }
            for (int i = 1; i < events.Length; i++)    // insertion sort, once (52 values; no System.Array in Udon)
            {
                float v = events[i];
                int j = i - 1;
                while (j >= 0 && events[j] > v) { events[j + 1] = events[j]; j--; }
                events[j + 1] = v;
            }
            dustK = new int[dustSlots.Length]; dustOn = new bool[dustSlots.Length];
            for (int s = 0; s < dustSlots.Length; s++) { dustK[s] = -1; dustOn[s] = dustSlots[s] != null && dustSlots[s].enabled; }
            starOn = new bool[starCopies.Length];
            for (int s = 0; s < starCopies.Length; s++) starOn[s] = starCopies[s] != null && starCopies[s].enabled;
            rimLit = rimLight != null && rimLight.enabled;
        }

        // ---------------------------------------------------------------------------------------- dispatcher API
        public float[] LanbaiWindow()
        {
            return new float[] { windowStart, windowEnd };
        }

        public void LanbaiActivate(bool on)
        {
            Init();
            if (root != null)
                root.SetActive(on);
            if (on)
                PrewarmPose();                      // F8: the spawn prewarm only activates; draw all three shaders once
            else
            {
                ClearGlobals();
                AllOff();
            }
        }

        // every mirror whole, just below the eye, star copies and dust on: whatever frames run before the next Tick
        // (the dispatcher's spawn prewarm, under the black) upload and draw Lanbai/BronzeMirror, MirrorStars and
        // MirrorDust once. The next Tick rebuilds the real state from t (D-33 #6).
        private void PrewarmPose()
        {
            for (int k = 0; k < mirrors.Length; k++)
            {
                if (mirrors[k] == null)
                    continue;
                mirrors[k].gameObject.SetActive(true);
                mirrors[k].localPosition = new Vector3(eye.x, eye.y - 2f - 0.05f * k, eye.z + 10f);
                mirrors[k].localScale = new Vector3(40f, 40f, 40f);
                mpb.Clear();
                mpb.SetFloat(idRadius, 20f);
                mpb.SetFloat(idK, k + 1);
                mpb.SetFloat(idEmK, emissionK[k]);
                mpb.SetFloat(idVis, 1f);
                mpb.SetFloat(idExtra, 0f);
                mpb.SetFloat(idAppear, 1f);
                mpb.SetFloat(idDissolve, 0.5f);   // the noise / clip path too
                for (int l = 0; l < 3; l++)
                {
                    Renderer r = lodRenderers[3 * k + l];
                    if (r != null)
                        r.SetPropertyBlock(mpb);
                }
            }
            for (int s = 0; s < starCopies.Length; s++)
                if (starCopies[s] != null)
                    starCopies[s].enabled = true;
            for (int s = 0; s < dustSlots.Length; s++)
            {
                if (dustSlots[s] == null)
                    continue;
                mpb.Clear();
                mpb.SetFloat(idDustOn, 1f);
                mpb.SetFloat(idDustNow, 1f);
                mpb.SetFloat(idDustT0, 0f);
                mpb.SetVector(idDustC, new Vector4(eye.x, eye.y - 2f, eye.z + 10f, 20f));
                mpb.SetVector(idDustCar, new Vector4(0f, -10f, 1f, 40f));
                dustSlots[s].SetPropertyBlock(mpb);
                dustSlots[s].enabled = true;
            }
        }

        // F6: outside the window nothing of ours draws or lights
        private void AllOff()
        {
            for (int k = 0; k < mirrors.Length; k++)
                if (mirrors[k] != null && mirrors[k].gameObject.activeSelf)
                    mirrors[k].gameObject.SetActive(false);
            for (int s = 0; s < starCopies.Length; s++)
                if (starCopies[s] != null && starCopies[s].enabled)
                    starCopies[s].enabled = false;
            for (int s = 0; s < dustSlots.Length; s++)
                if (dustSlots[s] != null && dustSlots[s].enabled)
                    dustSlots[s].enabled = false;
            if (rimLight != null && rimLight.enabled)
                rimLight.enabled = false;
        }

        public float[] LanbaiGrade(float t)
        {
            float ev = PulseEV(t);
            if (ev <= 0f)
                return null;
            grade[0] = ev; grade[1] = 0f; grade[2] = 0f; grade[3] = 1f;
            return grade;
        }

        public void LanbaiTick(float t)
        {
            Init();
            if (!valid)
                return;
            if (t < windowStart || t >= windowEnd || t >= tCross[n - 1])
            {
                if (t < windowStart || t >= windowEnd)
                    AllOff();
                else
                {
                    // mirror 13 alone from F16: its stars and dust are not ours to keep (F6)
                    for (int k = 0; k < n; k++)
                        if (onCache[k] && (t < activeStart[k] || t > activeEnd[k])) { mirrors[k].gameObject.SetActive(false); onCache[k] = false; }
                    for (int s = 0; s < dustSlots.Length; s++)
                        if (dustOn[s]) { dustSlots[s].enabled = false; dustOn[s] = false; }
                    if (rimLit) { rimLight.enabled = false; rimLit = false; }
                }
                segA = 1e9f; segB = -1e9f;
                ClearGlobals();
                return;
            }
            if (t < segA || t >= segB)
                RebuildActive(t);

            float planeY = 0f, planeLine = 0f, planeIdx = 0f, planePhase = 0f, bestAbs = 1e9f;
            float rimE = 0f, rimY = 0f;
            int rimK = -1;
            for (int a = 0; a < activeCount; a++)
            {
                int k = activeList[a];
                float D = diameter[k];
                float yCar = Hermite(knotStart[k], knotCount[k], t);
                float yEdge = yCar - yOff[k];
                mirrors[k].localPosition = new Vector3(centreX[k], yEdge, centreZ[k]);

                float vis = Linear(visT, visV, visStart[k], visCount[k], t);
                float appear = Mathf.Clamp01((t - visT[visStart[k]]) / appearSeconds);
                float dis = dissolveEnd[k] > 0f ? Mathf.Clamp01((t - tCross[k]) / (dissolveEnd[k] - tCross[k])) : 0f;
                float extra = (k == n - 1) ? Linear(extraT, extraV, 0, extraT.Length, t) : 0f;
                float far = (k == n - 1) ? 1f - Mathf.Clamp01((t - farUntil) / farSeconds) : 0f;
                bool farChanged = k == n - 1 && far != lastFar;
                if (vis != lastVis[k] || appear != lastAppear[k] || dis != lastDis[k] || extra != lastExtra[k] || farChanged)
                {
                    lastVis[k] = vis; lastAppear[k] = appear; lastDis[k] = dis; lastExtra[k] = extra;
                    if (k == n - 1) lastFar = far;
                    mpb.Clear();
                    mpb.SetFloat(idRadius, 0.5f * D);
                    mpb.SetFloat(idK, k + 1);
                    mpb.SetFloat(idEmK, emissionK[k]);
                    mpb.SetFloat(idVis, vis);
                    mpb.SetFloat(idExtra, extra);
                    mpb.SetFloat(idAppear, appear);
                    mpb.SetFloat(idDissolve, dis);
                    mpb.SetFloat(idRimSoft, far);
                    mpb.SetFloat(idRimSoftFrom, farRimFrom);
                    mpb.SetFloat(idFaceSoft, far);
                    mpb.SetFloat(idFarDim, 1f - (1f - farDim) * far);
                    int b = 3 * k;
                    if (lodRenderers[b] != null) lodRenderers[b].SetPropertyBlock(mpb);
                    if (lodRenderers[b + 1] != null) lodRenderers[b + 1].SetPropertyBlock(mpb);
                    if (lodRenderers[b + 2] != null) lodRenderers[b + 2].SetPropertyBlock(mpb);
                }
                // the reflected stars of this mirror (its stencil slot): the sphere moves with the mirror every frame
                Renderer sc = starCopies[slotOf[k]];
                if (sc != null)
                {
                    mpb.Clear();
                    mpb.SetVector(idSphere, new Vector4(centreX[k], yEdge + (Sag - Rho) * D, centreZ[k], Rho * D));
                    mpb.SetVector(idAxis, new Vector4(0f, 1f, 0f, FaceR * D));
                    mpb.SetVector(idFaceK, new Vector4(0f, emissionK[k] * vis * Mathf.Pow(2f, extra), 0f, 0f));
                    sc.SetPropertyBlock(mpb);
                }
                float dt = t - tCross[k];
                if (dt > -2f && dt < 2f)
                {
                    float ad = dt < 0f ? -dt : dt;
                    if (ad < bestAbs)                   // the nearest crossing drives the cabin line
                    {
                        bestAbs = ad;
                        planeY = yCar;
                        planeIdx = k + 1;
                        planePhase = Mathf.Clamp(dt * 0.5f, -1f, 1f);
                        planeLine = dt < 0f ? Mathf.Clamp01(1f + dt / 0.3f) : Mathf.Clamp01(1f - (dt - 0.6f) / 0.3f);
                    }
                    // the rim light: the LARGEST envelope (C8); mirror 13 is not lit (its rim is kilometres away)
                    if (k < n - 1 && dt < 1f)
                    {
                        float e = rimLightE * (dt < 0f ? Mathf.SmoothStep(0f, 1f, 1f + dt / 2f) : Mathf.SmoothStep(0f, 1f, 1f - dt));
                        if (e > rimE) { rimE = e; rimK = k; rimY = yEdge; }
                    }
                }
            }
            // dust: only the slots that show a mirror tick (the rest were written when the set changed)
            for (int s = 0; s < dustSlots.Length; s++)
            {
                int kk = dustK[s];
                if (kk < 0)
                    continue;
                mpb.Clear();
                mpb.SetFloat(idDustNow, t);
                mpb.SetFloat(idDustOn, 1f);
                mpb.SetFloat(idDustT0, tCross[kk]);
                mpb.SetVector(idDustC, dustC[kk]);
                mpb.SetVector(idDustCar, dustCar[kk]);
                dustSlots[s].SetPropertyBlock(mpb);
            }
            Vector3 rim = rimK >= 0 ? new Vector3(rimPos[rimK].x, rimY, rimPos[rimK].z) : Vector3.zero;
            VRCShader.SetGlobalVector(idPlane, new Vector4(planeY, planeLine, planeIdx, planePhase));
            VRCShader.SetGlobalVector(idRimLight, new Vector4(rim.x, rim.y, rim.z, rimE));
            if (rimLight != null)
            {
                bool lit = rimE > 1e-4f;
                if (rimLit != lit) { rimLight.enabled = lit; rimLit = lit; }
                if (lit)
                {
                    rimLight.transform.localPosition = rim;     // a child of R_Mirrors, same frame as the mirrors
                    rimLight.intensity = rimLightIntensity * rimE / Mathf.Max(rimLightE, 1e-4f);
                    rimLight.range = Mathf.Max(rimDistM[rimK] + 8f, 12f);
                }
            }
        }

        // the active set, star slots and dust slots only change at the event times: rebuild them there (or on a backward jump)
        private void RebuildActive(float t)
        {
            segA = -1e9f; segB = 1e9f;
            for (int i = 0; i < events.Length; i++)
            {
                if (events[i] <= t) segA = events[i];
                else { segB = events[i]; break; }
            }
            activeCount = 0;
            for (int s = 0; s < starCopies.Length; s++)
            {
                bool used = false;
                for (int k = 0; k < n; k++)
                    if (slotOf[k] == s && t >= activeStart[k] && t <= activeEnd[k]) { used = true; break; }
                if (starCopies[s] != null && starOn[s] != used) { starCopies[s].enabled = used; starOn[s] = used; }
            }
            for (int k = 0; k < n; k++)
            {
                bool on = t >= activeStart[k] && t <= activeEnd[k];
                if (onCache[k] != on)
                {
                    mirrors[k].gameObject.SetActive(on);
                    onCache[k] = on;
                    lastVis[k] = -1f;               // force the MPB on the next write
                    if (on) mirrors[k].localScale = new Vector3(diameter[k], diameter[k], diameter[k]);
                }
                if (on)
                    activeList[activeCount++] = k;
            }
            for (int s = 0; s < dustSlots.Length; s++)
            {
                int kk = -1;
                for (int k = 0; k < n - 1; k++)
                    if (k % 3 == s && t >= tCross[k] && t <= dissolveEnd[k] + 4f)
                        kk = k;
                dustK[s] = kk;
                bool want = kk >= 0;
                if (dustSlots[s] != null && dustOn[s] != want)
                {
                    if (!want)
                    {
                        mpb.Clear();
                        mpb.SetFloat(idDustOn, 0f);
                        dustSlots[s].SetPropertyBlock(mpb);
                    }
                    dustSlots[s].enabled = want;
                    dustOn[s] = want;
                }
            }
        }

        // ---------------------------------------------------------------------------------------- maths
        public float PulseEV(float t)
        {
            float ev = 0f;
            for (int k = 0; k < tCross.Length; k++)
            {
                if (pulseEV[k] <= 0f)
                    continue;
                float x = t - tCross[k];
                if (x > -pulseIn && x <= 0f)
                    ev = Mathf.Max(ev, pulseEV[k] * (x + pulseIn) / pulseIn);
                else if (x > 0f && x < pulseOut)
                    ev = Mathf.Max(ev, pulseEV[k] * (1f - x / pulseOut));
            }
            return ev;
        }

        private float Hermite(int s, int c, float t)
        {
            if (t <= knotT[s])
                return knotY[s];
            if (t >= knotT[s + c - 1])
                return knotY[s + c - 1];
            int lo = s, hi = s + c - 1;
            while (hi - lo > 1)
            {
                int mid = (lo + hi) / 2;
                if (knotT[mid] <= t) lo = mid; else hi = mid;
            }
            float h = knotT[hi] - knotT[lo];
            float u = (t - knotT[lo]) / h;
            float u2 = u * u, u3 = u2 * u;
            return (2f * u3 - 3f * u2 + 1f) * knotY[lo] + (u3 - 2f * u2 + u) * h * knotV[lo]
                 + (-2f * u3 + 3f * u2) * knotY[hi] + (u3 - u2) * h * knotV[hi];
        }

        private float Linear(float[] xs, float[] ys, int s, int c, float t)
        {
            if (c <= 0)
                return 0f;
            if (t <= xs[s])
                return ys[s];
            for (int i = s; i < s + c - 1; i++)
                if (t <= xs[i + 1])
                    return Mathf.Lerp(ys[i], ys[i + 1], (t - xs[i]) / Mathf.Max(xs[i + 1] - xs[i], 1e-6f));
            return ys[s + c - 1];
        }
    }
}
