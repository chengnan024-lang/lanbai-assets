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
        public float[] extraV = new float[] { 0f, 3f };
        public float rimSoftStart = 1139.31f;       // F16 - 10: the far soft rim sharpens over 4 s
        public float rimSoftSeconds = 4f;
        public float rimSoftFrom = 0.8f;            // MirrorSchedule.json mirrors[12].rim_soft.inner_frac

        [Header("Constants (spec_conventions.md)")]
        public Vector3 eye = new Vector3(0.55f, 1.70f, 2.05f);
        public float appearSeconds = 3f;
        public float pulseIn = 0.08f;
        public float pulseOut = 0.35f;
        public float rimLightE = 0.3f;

        private const float FaceR = 0.48f;
        private const float Sag = 0.015f;
        private const float Rho = 7.6875f;

        private MaterialPropertyBlock mpb;
        private int idRadius, idK, idEmK, idVis, idExtra, idAppear, idDissolve, idRimSoft, idRimSoftFrom;
        private int idSphere, idAxis, idFaceK;
        private int idDustNow, idDustT0, idDustC, idDustCar, idDustOn;
        private int idPlane, idRimLight;
        private bool ready;
        private float[] grade = new float[4];

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
            ready = true;
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
            if (!on)
                ClearGlobals();
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
            if (t < windowStart || t >= windowEnd || t >= tCross[tCross.Length - 1])
            {
                for (int k = 0; k < mirrors.Length; k++)
                    if (mirrors[k] != null && mirrors[k].gameObject.activeSelf && (t < activeStart[k] || t > activeEnd[k]))
                        mirrors[k].gameObject.SetActive(false);
                ClearGlobals();
                return;
            }
            int n = tCross.Length;
            float planeY = 0f, planeLine = 0f, planeIdx = 0f, planePhase = 0f, bestAbs = 1e9f;
            Vector3 rim = Vector3.zero;
            float rimE = 0f;
            for (int k = 0; k < n; k++)
            {
                bool on = t >= activeStart[k] && t <= activeEnd[k];
                GameObject go = mirrors[k].gameObject;
                if (go.activeSelf != on)
                    go.SetActive(on);
                if (!on)
                    continue;
                float D = diameter[k];
                float yCar = Hermite(knotStart[k], knotCount[k], t);
                float rCar = Mathf.Min(Mathf.Sqrt((eye.x - centreX[k]) * (eye.x - centreX[k]) + (eye.z - centreZ[k]) * (eye.z - centreZ[k])) / D, FaceR);
                float yEdge = yCar - (Mathf.Sqrt(Rho * Rho - rCar * rCar) - (Rho - Sag)) * D;
                mirrors[k].localPosition = new Vector3(centreX[k], yEdge, centreZ[k]);
                mirrors[k].localScale = new Vector3(D, D, D);

                float vis = Linear(visT, visV, visStart[k], visCount[k], t);
                float appear = Mathf.Clamp01((t - visT[visStart[k]]) / appearSeconds);
                float dis = dissolveEnd[k] > 0f ? Mathf.Clamp01((t - tCross[k]) / (dissolveEnd[k] - tCross[k])) : 0f;
                float extra = (k == n - 1) ? Linear(extraT, extraV, 0, extraT.Length, t) : 0f;
                float rimSoft = (k == n - 1) ? 1f - Mathf.Clamp01((t - rimSoftStart) / rimSoftSeconds) : 0f;

                mpb.Clear();
                mpb.SetFloat(idRadius, 0.5f * D);
                mpb.SetFloat(idK, k + 1);
                mpb.SetFloat(idEmK, emissionK[k]);
                mpb.SetFloat(idVis, vis);
                mpb.SetFloat(idExtra, extra);
                mpb.SetFloat(idAppear, appear);
                mpb.SetFloat(idDissolve, dis);
                mpb.SetFloat(idRimSoft, rimSoft);
                mpb.SetFloat(idRimSoftFrom, rimSoftFrom);
                for (int l = 0; l < 3; l++)
                {
                    Renderer r = lodRenderers[3 * k + l];
                    if (r != null)
                        r.SetPropertyBlock(mpb);
                }

                // the reflected stars of this mirror (its stencil slot)
                int slot = (k == n - 1) ? 6 : (k % 6);
                Renderer sc = starCopies[slot];
                if (sc != null)
                {
                    mpb.Clear();
                    mpb.SetVector(idSphere, new Vector4(centreX[k], yEdge + (Sag - Rho) * D, centreZ[k], Rho * D));
                    mpb.SetVector(idAxis, new Vector4(0f, 1f, 0f, FaceR * D));
                    mpb.SetVector(idFaceK, new Vector4(0f, emissionK[k] * vis * Mathf.Pow(2f, extra), 0f, 0f));
                    sc.SetPropertyBlock(mpb);
                }

                // the nearest crossing drives the cabin line and the rim light
                float dt = t - tCross[k];
                if (dt > -2f && dt < 2f && Mathf.Abs(dt) < bestAbs)
                {
                    bestAbs = Mathf.Abs(dt);
                    planeY = yCar;
                    planeIdx = k + 1;
                    planePhase = Mathf.Clamp(dt * 0.5f, -1f, 1f);
                    planeLine = dt < 0f ? Mathf.Clamp01(1f + dt / 0.3f) : Mathf.Clamp01(1f - (dt - 0.6f) / 0.3f);
                    float dx = eye.x - centreX[k], dz = eye.z - centreZ[k];
                    float l2 = Mathf.Max(Mathf.Sqrt(dx * dx + dz * dz), 1e-3f);
                    rim = new Vector3(centreX[k] + dx / l2 * 0.5f * D, yEdge, centreZ[k] + dz / l2 * 0.5f * D);
                    rimE = rimLightE * (dt < 0f ? Mathf.SmoothStep(0f, 1f, 1f + dt / 2f) : Mathf.SmoothStep(0f, 1f, 1f - dt));
                }
            }
            // star copies of slots with no active mirror: collapse (gain 0)
            for (int s = 0; s < starCopies.Length; s++)
            {
                if (starCopies[s] == null)
                    continue;
                bool used = false;
                for (int k = 0; k < n; k++)
                    if (t >= activeStart[k] && t <= activeEnd[k] && ((k == n - 1) ? 6 : (k % 6)) == s)
                        used = true;
                if (starCopies[s].enabled != used)
                    starCopies[s].enabled = used;
            }
            // dust: the latest mirror per slot that is dissolving or fading (t_cross .. dissolveEnd + 4 s)
            for (int s = 0; s < dustSlots.Length; s++)
            {
                Renderer dr = dustSlots[s];
                if (dr == null)
                    continue;
                int kk = -1;
                for (int k = 0; k < n - 1; k++)
                    if (k % 3 == s && t >= tCross[k] && t <= dissolveEnd[k] + 4f)
                        kk = k;
                mpb.Clear();
                mpb.SetFloat(idDustNow, t);
                mpb.SetFloat(idDustOn, kk >= 0 ? 1f : 0f);
                if (kk >= 0)
                {
                    float D = diameter[kk];
                    float rCar = Mathf.Min(Mathf.Sqrt((eye.x - centreX[kk]) * (eye.x - centreX[kk]) + (eye.z - centreZ[kk]) * (eye.z - centreZ[kk])) / D, FaceR);
                    float yEdge0 = eye.y - (Mathf.Sqrt(Rho * Rho - rCar * rCar) - (Rho - Sag)) * D;
                    mpb.SetFloat(idDustT0, tCross[kk]);
                    mpb.SetVector(idDustC, new Vector4(centreX[kk], yEdge0, centreZ[kk], 0.5f * D));
                    mpb.SetVector(idDustCar, new Vector4(eye.x - centreX[kk], eye.z - centreZ[kk], crossSpeed[kk], D));
                }
                dr.SetPropertyBlock(mpb);
                if (dr.enabled != (kk >= 0))
                    dr.enabled = kk >= 0;
            }
            VRCShader.SetGlobalVector(idPlane, new Vector4(planeY, planeLine, planeIdx, planePhase));
            VRCShader.SetGlobalVector(idRimLight, new Vector4(rim.x, rim.y, rim.z, rimE));
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
