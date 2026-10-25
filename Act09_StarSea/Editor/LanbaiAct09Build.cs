// 蓝白 · 菜单 蓝白/Build/Act09：按 Act09_StarSea.json 搭第 9 幕的天（可重复运行：先删上一次搭的 R_StarSea 和 Lanbai_Act09Driver，含未激活的）。
// 搭完要跑 蓝白/Director/1 Generate Dispatcher 和 2 Wire Scene（README_Act09 §0）。
// !!! NOT COMPILED IN UNITY: Roslyn type-check against UnityEditor 2021.1 only (Sky/Tools~/compile_check/check_cs.sh). !!!
// Needs: 蓝白/Sky/Build Star Mesh + Build Sky run first (they make the main star mesh, the one sky material and M_Sky_StarPoints.mat).
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using Lanbai.Sky.EditorTools;

namespace Lanbai.Act09.EditorTools
{
    [Serializable] public class A9Labels { public float F12, F13, F14, F15, F16, blue_hour_start, act9_start, dark_end, ignition_full; }
    [Serializable] public class A9Ignition { public float t0; public float seconds; public float table_step_s; public float[] g; public float[] g_core; public float core_lead_s; }
    [Serializable] public class A9First { public int hr; public float[] dir; public float mag; public float order; public float out_t; }
    [Serializable] public class A9FirstStars { public A9First[] stars; public float[] appear; public float peak; public float out_s; }
    [Serializable] public class A9Q { public string @char; public int strokes; public float[] dir; public float peak; }
    [Serializable] public class A9QStars { public A9Q[] stars; }
    [Serializable] public class A9Zenith { public float[] night; public float[] floor_add; }
    [Serializable] public class A9Sky { public float band1_gain; public A9Zenith zenith_floor; }
    [Serializable] public class A9File { public A9Labels labels; public A9Ignition ignition; public A9FirstStars first_stars; public A9QStars question_stars; public A9Sky sky; }

    public static class LanbaiAct09Build
    {
        const float MagSlope = 0.5f;     // = Lanbai/StarPoints _MagSlope (its default; Sky's material keeps it)
        const string RootName = "R_StarSea", DriverName = "Lanbai_Act09Driver";

        static string ActRoot()
        {
            foreach (string id in AssetDatabase.FindAssets("Act09_StarSea"))
            {
                string p = AssetDatabase.GUIDToAssetPath(id);
                if (p.EndsWith("/Act09_StarSea/Act09_StarSea.json")) return p.Substring(0, p.Length - "/Act09_StarSea.json".Length);
            }
            return "Assets/Lanbai/Act09_StarSea";
        }

        // magnitude that gives a linear peak 'peak' with _StarScale 1.6, _MagRef 0, _MagSlope 0.5 (no rank boost)
        static float MagForPeak(float peak) { return -Mathf.Log(Mathf.Max(peak, 1e-6f) / 1.6f, 2f) / (1.3287712f * MagSlope); }   // _StarScale 1.6

        // D-41：菜单先等 U# 程序资产初始化完再搭（Common/Editor/LanbaiUdonPrograms）
        [MenuItem("蓝白/Build/Act09")]
        public static void BuildMenu()
        {
            Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("蓝白/Build/Act09", new[] { typeof(LanbaiAct09Driver) }, Build, Lanbai.Udon.LanbaiUdonPrograms.NextToScript);
        }

        public static void Build()
        {
            Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Build/Act09", typeof(LanbaiAct09Driver));
            A9File d = JsonUtility.FromJson<A9File>(File.ReadAllText(ActRoot() + "/Act09_StarSea.json"));
            string gen = LanbaiSkyBuild.GeneratedFolder();
            Mesh main = AssetDatabase.LoadAssetAtPath<Mesh>(gen + "/StarPoints_BSC5.asset");
            Material starMat = AssetDatabase.LoadAssetAtPath<Material>(gen + "/M_Sky_StarPoints.mat");
            if (main == null || starMat == null) { Debug.LogError("[Act09] run 蓝白/Sky/Build Star Mesh and 蓝白/Sky/Build Sky first"); return; }

            // first stars (real stars around the zenith, their real magnitudes; order = the order they go out)
            int nf = d.first_stars.stars.Length;
            Vector3[] fd = new Vector3[nf]; float[] fm = new float[nf]; float[] fr = new float[nf]; float[] fo = new float[nf]; Color[] fc = new Color[nf];
            for (int i = 0; i < nf; i++)
            {
                A9First s = d.first_stars.stars[i];
                fd[i] = new Vector3(s.dir[0], s.dir[1], s.dir[2]); fm[i] = s.mag; fr[i] = 9999f; fo[i] = s.order; fc[i] = Color.white;
            }
            Mesh firstMesh = LanbaiSkyBuild.SaveStarMesh(ActRoot() + "/Generated_FirstStars.asset", "Act09_FirstStars", fd, fm, fr, fo, fc);
            // question stars (one per character; the peak is encoded as a magnitude)
            int nq = d.question_stars.stars.Length;
            Vector3[] qd = new Vector3[nq]; float[] qm = new float[nq]; float[] qr = new float[nq]; float[] qo = new float[nq]; Color[] qc = new Color[nq];
            for (int i = 0; i < nq; i++)
            {
                A9Q s = d.question_stars.stars[i];
                qd[i] = new Vector3(s.dir[0], s.dir[1], s.dir[2]); qm[i] = MagForPeak(s.peak); qr[i] = 9999f; qo[i] = 1f; qc[i] = Color.white;
            }
            Mesh qMesh = LanbaiSkyBuild.SaveStarMesh(ActRoot() + "/Generated_QuestionStars.asset", "Act09_QuestionStars", qd, qm, qr, qo, qc);

            Material firstMat = MatCopy(starMat, ActRoot() + "/M_Act09_FirstStars.mat");
            firstMat.SetVector("_Tint", new Vector4(0.807f, 0.855f, 0.939f, 1f) / 0.855f);      // #E8EEF8, luminance ~1
            firstMat.SetFloat("_BrightCount", 0f);
            firstMat.SetFloat("_UseGlobalGain", 0f);          // the driver's MPB _Gain, not the act's global star gain
            Material qMat = MatCopy(starMat, ActRoot() + "/M_Act09_QuestionStars.mat");
            qMat.SetFloat("_BrightCount", 0f); qMat.SetFloat("_MagFloor", 99f);
            qMat.SetVector("_Tint", new Vector4(0.8879f, 0.9216f, 1.0f, 1f) / 0.9201f);      // #F2F6FF linear, luminance 1

            // earlier builds: by name at the scene root (active or not: the reflection baker leaves R_StarSea off, and
            // GameObject.Find does not see inactive objects) and any driver left anywhere (old builds put it inside R_StarSea)
            foreach (GameObject g in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
                if (g.name == RootName || g.name == DriverName) Undo.DestroyObjectImmediate(g);
            foreach (LanbaiAct09Driver od in UnityEngine.Object.FindObjectsOfType<LanbaiAct09Driver>(true))
                if (od != null) Undo.DestroyObjectImmediate(od.gameObject);
            GameObject root = new GameObject(RootName);
            Undo.RegisterCreatedObjectUndo(root, "蓝白 Act09 build");
            // the main stars are the film's ONE star object (Sky's Lanbai_Stars_BSC5, 蓝白/Sky/Build Sky): a second copy here drew
            // every star twice from F13 (+1 EV, tech review r2 #4). The driver does not switch it (gain 0 = culled in the
            // vertex shader), so seeking back to acts 3-4 never finds it disabled.
            if (LanbaiSkyBuild.FindRoot("Lanbai_Stars_BSC5", false) == null) Debug.LogWarning("[Act09] no Lanbai_Stars_BSC5 in the scene: run 蓝白/Sky/Build Sky");
            Renderer rFirst = MakeStarObject(root, "Stars_First", firstMesh, firstMat);
            Renderer rQ = MakeStarObject(root, "Stars_Question", qMesh, qMat);
            rFirst.enabled = false; rQ.enabled = false;      // the driver's Tick switches them on (never visible at activation)

            // the driver on its OWN always-active object (Director README §3.1): LanbaiActivate switches R_StarSea, which
            // holds only the two renderers, so the driver never switches itself off
            GameObject drv = new GameObject(DriverName);
            Undo.RegisterCreatedObjectUndo(drv, "蓝白 Act09 build");
            LanbaiAct09Driver c = AddUdon(drv);
            c.root = root; c.firstStars = rFirst; c.questionStars = rQ;
            c.tBlueHour = d.labels.blue_hour_start; c.tActStart = d.labels.act9_start; c.tDarkEnd = d.labels.dark_end;
            c.tF13 = d.labels.F13; c.tF16 = d.labels.F16;
            c.gTable = d.ignition.g; c.gCoreTable = d.ignition.g_core; c.gStep = d.ignition.table_step_s;
            c.band1Gain = d.sky.band1_gain;
            c.nightColor = new Vector3(d.sky.zenith_floor.night[0], d.sky.zenith_floor.night[1], d.sky.zenith_floor.night[2]);
            c.floorAdd = new Vector3(d.sky.zenith_floor.floor_add[0], d.sky.zenith_floor.floor_add[1], d.sky.zenith_floor.floor_add[2]);
            c.firstAppear0 = d.first_stars.appear[0]; c.firstAppear1 = d.first_stars.appear[1];
            c.firstPeak = d.first_stars.peak; c.firstOutSeconds = d.first_stars.out_s;
            EditorUtility.SetDirty(c);
            root.SetActive(false);                            // off until the dispatcher's LanbaiActivate(true) at 992.06
            Debug.Log("[Act09] R_StarSea + " + DriverName + " built: " + nf + " first stars, " + nq + " question stars, ignition " + d.ignition.seconds + " s (" + d.ignition.g.Length + " samples, core lead " + d.ignition.core_lead_s + " s). Now run 蓝白/Director/1 Generate Dispatcher and 2 Wire Scene. Mirrors: add the kit from Mirrors/ when it arrives.");
        }

        static Material MatCopy(Material src, string path)
        {
            Material m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(src); AssetDatabase.CreateAsset(m, path); }
            else m.CopyPropertiesFromMaterial(src);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Renderer MakeStarObject(GameObject root, string name, Mesh mesh, Material mat)
        {
            GameObject go = new GameObject(name);
            Undo.RegisterCreatedObjectUndo(go, "蓝白 Act09 build");
            go.transform.SetParent(root.transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            MeshRenderer r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off;
            r.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
            r.allowOcclusionWhenDynamic = false;
            return r;
        }

        static LanbaiAct09Driver AddUdon(GameObject go)
        {
            return (LanbaiAct09Driver)Lanbai.Udon.LanbaiUdonPrograms.AddComponent(go, typeof(LanbaiAct09Driver));
        }
    }
}
