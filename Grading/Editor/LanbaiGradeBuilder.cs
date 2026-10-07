// Lanbai / 蓝白 -- PPv2 grade builder (ART BIBLE v2.1, 1.4 + 1.7 + appendix B).
// Menu: 蓝白/Grades/Build Profiles & Volumes
//
// UNCOMPILED IN UNITY. Type-checked on the art side with Roslyn against Unity 2021.1 UnityEngine/UnityEditor
// reference DLLs, both against a stub of the PPv2 3.x public API and against the real PPv2 3.0.2 runtime source.
// Behaviour has not run.
//
// The numbers it writes are the ENGINE numbers (LanbaiGradeData, generated from grades_engine.json): solved so that
// PPv2's real Neutral path shows the bible's screen targets. The bible's appendix B1 numbers are the look definition
// for the art simulator; they are kept per entry in LanbaiGradeData.lookDefinition and must NOT be typed into Unity.
//
// What it does (idempotent: re-running updates everything in place, never duplicates):
//   1. ensures the layer "PostProcessing" exists (creates it in the first empty user slot >= 22 if missing);
//   2. one PostProcessProfile asset per LanbaiGradeData entry in <kit>/Profiles/Lanbai_PP_<id>.asset,
//      holding EXACTLY the effects and overridden parameters the bible requires (every other override is
//      switched off, every foreign effect removed); ColorGrading in HDR + Neutral for every scene profile;
//      scene profiles override bible 1.4's 22 parameters + the 9 Channel Mixer entries of the engine solve;
//   3. one global PostProcessVolume per profile under the scene root "Lanbai_Grades"
//      (Scenes / Helpers / Lens_DesktopOnly), on layer PostProcessing, priority from the json,
//      weight 0 except S1 (first scene) and LENS_CLEAN (bible 1.4: desktop lens layer is always 1);
//   4. validates: identical 31-parameter override set on every scene profile, values read back from
//      the saved assets, foreign volumes in the scene, the reference camera's PostProcessLayer, project HDR;
//   5. writes a report to <project>/LanbaiReports/GradeBuild_Report.md and returns a one-line summary.
//      Values it REPLACED in existing profile assets (e.g. a hand trim of postExposure) are listed there:
//      trims belong in grades_final.json on the art side (bible 1.5), never in the profile assets.
// Undo: the volumes in the scene are undoable; the profile ASSETS are not (sub-assets added / removed by
// AddSettings / RemoveObjectFromAsset cannot be undone cleanly). To get back to the data, just re-run the build.
// Route C (bible 1.7, fallback only): 蓝白/Grades/Route C/... builds External-LUT profiles from the
// art/luts/hdr_external/*_HDRext33.cube Texture3Ds and points the scene volumes at them; Route A switches back.
// Every public static method returns a string so a remote helper can call it by reflection (no dialogs).

#pragma warning disable 0618 // PPv2 3.5+ marks its types [Obsolete] (a warning only)
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.PostProcessing;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace Lanbai.Grading
{
    public static class LanbaiGradeBuilder
    {
        public const string Menu = "蓝白/Grades/";
        public const string VolumeLayerName = "PostProcessing";
        public const string RootName = "Lanbai_Grades";
        public const string ProfilePrefix = "Lanbai_PP_";
        public const string RouteCProfilePrefix = "Lanbai_PPC_";
        public const string VolumePrefix = "PPV_";
        const string UndoName = "蓝白 Build Grades";

        /// <summary>
        /// The full override set every scene profile must carry (ordinal order). Bible 1.4's 22 parameters plus the 9
        /// Channel Mixer entries of the engine realisation (all 15 scene profiles override them, S10 at identity), so no
        /// crossfade ever passes through a default.
        /// </summary>
        public static readonly string[] SceneOverrideSet = new string[]
        {
            "Bloom.anamorphicRatio", "Bloom.clamp", "Bloom.color", "Bloom.diffusion", "Bloom.fastMode",
            "Bloom.intensity", "Bloom.softKnee", "Bloom.threshold",
            "ColorGrading.colorFilter", "ColorGrading.contrast", "ColorGrading.gain", "ColorGrading.gamma",
            "ColorGrading.gradingMode", "ColorGrading.hueShift", "ColorGrading.lift",
            "ColorGrading.mixerBlueOutBlueIn", "ColorGrading.mixerBlueOutGreenIn", "ColorGrading.mixerBlueOutRedIn",
            "ColorGrading.mixerGreenOutBlueIn", "ColorGrading.mixerGreenOutGreenIn", "ColorGrading.mixerGreenOutRedIn",
            "ColorGrading.mixerRedOutBlueIn", "ColorGrading.mixerRedOutGreenIn", "ColorGrading.mixerRedOutRedIn",
            "ColorGrading.postExposure",
            "ColorGrading.saturation", "ColorGrading.temperature", "ColorGrading.tint", "ColorGrading.tonemapper",
            "Grain.intensity", "Vignette.intensity",
        };

        // =========================================================================================
        // Menu
        // =========================================================================================
        [MenuItem(Menu + "Build Profiles & Volumes", false, 1)]
        static void MenuBuild() { Debug.Log("[蓝白 Grades] " + BuildAll()); }

        [MenuItem(Menu + "Validate Scene & Camera", false, 2)]
        static void MenuValidate() { Debug.Log("[蓝白 Grades] " + ValidateScene()); }

        [MenuItem(Menu + "Configure Reference Camera (PostProcessLayer)", false, 3)]
        static void MenuCamera() { Debug.Log("[蓝白 Grades] " + ConfigureReferenceCamera()); }

        [MenuItem(Menu + "Restore Initial Weights", false, 4)]
        static void MenuRestore() { Debug.Log("[蓝白 Grades] " + RestoreInitialWeights()); }

        [MenuItem(Menu + "Route C (External LUT fallback)/Build Route C Profiles and Switch to Route C", false, 60)]
        static void MenuRouteC() { Debug.Log("[蓝白 Grades] " + UseRouteC()); }

        [MenuItem(Menu + "Route C (External LUT fallback)/Switch Back to Route A (parametric, default)", false, 61)]
        static void MenuRouteA() { Debug.Log("[蓝白 Grades] " + UseRouteA()); }

        [MenuItem(Menu + "Bloom Colour/Compensate PPv2 double sRGB decode (default)", false, 70)]
        static void MenuBloomComp() { Debug.Log("[蓝白 Grades] " + SetBloomColourCompensation(true)); }

        [MenuItem(Menu + "Bloom Colour/Write the bible hex unchanged", false, 71)]
        static void MenuBloomRaw() { Debug.Log("[蓝白 Grades] " + SetBloomColourCompensation(false)); }

        [MenuItem(Menu + "Fallback/Add Animator Weight Drivers (only if Udon cannot set weight)", false, 100)]
        static void MenuFallbackAdd() { Debug.Log("[蓝白 Grades] " + AddAnimatorFallback()); }

        [MenuItem(Menu + "Fallback/Remove Animator Weight Drivers", false, 101)]
        static void MenuFallbackRemove() { Debug.Log("[蓝白 Grades] " + RemoveAnimatorFallback()); }

        // =========================================================================================
        // Build
        // =========================================================================================
        public static string BuildAll()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                return "ERROR: leave Play mode first (the builder edits assets and the scene).";

            var log = new StringBuilder();
            int errors = 0, warnings = 0;
            bool routeC = CurrentRouteIsC();                     // keep the route the scene is on
            Undo.IncrementCurrentGroup();
            Undo.SetCurrentGroupName(UndoName);
            int undoGroup = Undo.GetCurrentGroup();

            int ppLayer = LanbaiGradeUtil.EnsureLayer(VolumeLayerName, log);
            if (ppLayer < 0) return "ERROR: could not find or create the layer '" + VolumeLayerName + "' (all user layers 22-31 are taken).";

            string kit = LanbaiGradeUtil.KitFolder();
            string folder = kit + "/Profiles";
            LanbaiGradeUtil.EnsureFolder(folder);

            // ---- 1. profile assets
            var profiles = new Dictionary<string, PostProcessProfile>();
            var replaced = new List<string>();
            foreach (var e in LanbaiGradeData.Entries)
            {
                string err;
                var p = BuildProfile(e, folder, replaced, out err);
                if (p == null) { errors++; log.AppendLine("- ERROR " + e.id + ": " + err); continue; }
                profiles[e.id] = p;
            }
            AssetDatabase.SaveAssets();
            if (replaced.Count > 0)
            {
                log.AppendLine("- this build REPLACED " + replaced.Count + " value(s) that differed from LanbaiGradeData in the existing profile assets "
                               + "(an older kit, or a hand edit). A postExposure trim (bible 1.5) is lost here: send it back to the art side as a "
                               + "grades_final.json change and regenerate; never edit the profile assets by hand:");
                foreach (var r in replaced) log.AppendLine("  - " + r);
            }
            Dictionary<string, PostProcessProfile> routeCProfiles = null;
            if (routeC)
            {
                string rcErr;
                routeCProfiles = BuildRouteCProfiles(folder, log, out rcErr);
                if (routeCProfiles == null) { errors++; log.AppendLine("- ERROR Route C was active but its profiles could not be rebuilt: " + rcErr + " -> scene volumes go back to Route A"); routeC = false; }
            }

            // ---- 2. volumes in the active scene
            Scene scene = SceneManager.GetActiveScene();
            if (!scene.IsValid() || !scene.isLoaded) return "ERROR: no active scene.";
            GameObject root = LanbaiGradeUtil.FindOrCreateRoot(scene, RootName, UndoName);
            root.layer = ppLayer;
            var keep = new HashSet<string>();
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessProfile p;
                if (!profiles.TryGetValue(e.id, out p)) continue;
                PostProcessProfile pc;
                if (routeC && e.kind == LanbaiGradeKind.Scene && routeCProfiles.TryGetValue(e.id, out pc)) p = pc;
                Transform group = LanbaiGradeUtil.FindOrCreateChild(root.transform, e.group, UndoName);
                group.gameObject.layer = ppLayer;
                BuildVolume(group, e, p, ppLayer);
                keep.Add(e.group + "/" + VolumePrefix + e.id);
            }
            // remove stale PPV_ children under our own root (entries that left the json)
            foreach (Transform group in LanbaiGradeUtil.Children(root.transform))
            {
                foreach (Transform c in LanbaiGradeUtil.Children(group))
                {
                    if (!c.name.StartsWith(VolumePrefix, StringComparison.Ordinal)) continue;
                    if (keep.Contains(group.name + "/" + c.name)) continue;
                    log.AppendLine("- removed stale volume " + group.name + "/" + c.name);
                    Undo.DestroyObjectImmediate(c.gameObject);
                }
            }
            EditorSceneManager.MarkSceneDirty(scene);
            Undo.CollapseUndoOperations(undoGroup);
            LanbaiGradeUtil.ResortVolumes(FindVolumes().Values);

            // ---- 3. validation + report
            string validation = ValidateInternal(profiles, ref errors, ref warnings);
            var md = new StringBuilder();
            md.AppendLine("# 蓝白 Grades · build report");
            md.AppendLine();
            md.AppendLine("- time: " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture));
            md.AppendLine("- Unity " + Application.unityVersion + ", scene `" + scene.path + "`");
            md.AppendLine("- data: grades_engine.json sha256 `" + LanbaiGradeData.GradesSha256 + "` (engine numbers; look definition grades_final.json `"
                          + LanbaiGradeData.LookDefSha256.Substring(0, 12) + "…`)");
            md.AppendLine("- route: " + (routeC ? "**C** (External LUT fallback, bible 1.7): tick `routeC` on LanbaiExposure (b = 0)" : "A (parametric, default)")
                          + "; bloom colour: " + (LanbaiGradeUtil.BloomColourCompensation ? "compensated for PPv2's double sRGB decode" : "bible hex written unchanged"));
            md.AppendLine("- profiles folder: `" + folder + "`; volume layer `" + VolumeLayerName + "` = " + ppLayer);
            md.AppendLine("- errors " + errors + ", warnings " + warnings);
            md.AppendLine();
            if (log.Length > 0) { md.AppendLine("## Build log"); md.AppendLine(); md.Append(log); md.AppendLine(); }
            md.Append(validation);
            string path = LanbaiGradeUtil.WriteReport("GradeBuild_Report.md", md.ToString());
            InternalRepaint();
            return (errors == 0 ? "OK" : "ERRORS " + errors) + ": " + profiles.Count + " profiles, "
                   + LanbaiGradeData.Entries.Length + " volumes under '" + RootName + "' (route " + (routeC ? "C" : "A") + "), warnings " + warnings
                   + (replaced.Count > 0 ? ", replaced " + replaced.Count + " differing value(s) (listed in the report)" : "") + ". Report: " + path;
        }

        // -----------------------------------------------------------------------------------------
        static PostProcessProfile BuildProfile(LanbaiGradeEntry e, string folder, List<string> replaced, out string error)
        {
            error = null;
            string path = folder + "/" + ProfilePrefix + e.id + ".asset";
            var profile = AssetDatabase.LoadAssetAtPath<PostProcessProfile>(path);
            if (profile == null)
            {
                if (AssetDatabase.LoadMainAssetAtPath(path) != null)
                {
                    error = "an asset that is not a PostProcessProfile already sits at " + path;
                    return null;
                }
                profile = ScriptableObject.CreateInstance<PostProcessProfile>();
                AssetDatabase.CreateAsset(profile, path);
            }
            else if (replaced != null)
            {
                // bible 1.5 trims and other hand edits are about to be overwritten: say so in the report
                var before = new List<string>();
                CompareValues(e, profile, before);
                foreach (var b in before) replaced.Add(e.id + ": " + b);
            }
            // no Undo.RecordObject on the asset: see the header (re-run the build instead of Ctrl+Z)

            var need = new List<Type>();
            if (e.HasColorGrading) need.Add(typeof(ColorGrading));
            if (e.HasBloom) need.Add(typeof(Bloom));
            if (e.HasVignette) need.Add(typeof(Vignette));
            if (e.HasGrain) need.Add(typeof(Grain));
            PruneSettings(profile, need);

            if (e.HasColorGrading)
            {
                var cg = GetOrAdd<ColorGrading>(profile);
                if (e.hdrNeutral.HasValue && e.hdrNeutral.Value)
                {
                    cg.gradingMode.Override(GradingMode.HighDefinitionRange);
                    cg.tonemapper.Override(Tonemapper.Neutral);
                }
                if (e.postExposure.HasValue) cg.postExposure.Override(e.postExposure.Value);
                if (e.temperature.HasValue) cg.temperature.Override(e.temperature.Value);
                if (e.tint.HasValue) cg.tint.Override(e.tint.Value);
                if (e.colorFilter != null) cg.colorFilter.Override(LanbaiGradeUtil.Hex(e.colorFilter));
                if (e.hueShift.HasValue) cg.hueShift.Override(e.hueShift.Value);
                if (e.saturation.HasValue) cg.saturation.Override(e.saturation.Value);
                if (e.contrast.HasValue) cg.contrast.Override(e.contrast.Value);
                if (e.lift != null) cg.lift.Override(LanbaiGradeUtil.V4(e.lift));
                if (e.gamma != null) cg.gamma.Override(LanbaiGradeUtil.V4(e.gamma));
                if (e.gain != null) cg.gain.Override(LanbaiGradeUtil.V4(e.gain));
                if (e.channelMixer != null)
                {
                    float[] m = e.channelMixer;
                    cg.mixerRedOutRedIn.Override(m[0]); cg.mixerRedOutGreenIn.Override(m[1]); cg.mixerRedOutBlueIn.Override(m[2]);
                    cg.mixerGreenOutRedIn.Override(m[3]); cg.mixerGreenOutGreenIn.Override(m[4]); cg.mixerGreenOutBlueIn.Override(m[5]);
                    cg.mixerBlueOutRedIn.Override(m[6]); cg.mixerBlueOutGreenIn.Override(m[7]); cg.mixerBlueOutBlueIn.Override(m[8]);
                }
                EditorUtility.SetDirty(cg);
            }
            if (e.HasBloom)
            {
                var b = GetOrAdd<Bloom>(profile);
                if (e.bloomIntensity.HasValue) b.intensity.Override(e.bloomIntensity.Value);
                if (e.bloomThreshold.HasValue) b.threshold.Override(e.bloomThreshold.Value);
                if (e.bloomSoftKnee.HasValue) b.softKnee.Override(e.bloomSoftKnee.Value);
                if (e.bloomClamp.HasValue) b.clamp.Override(e.bloomClamp.Value);
                if (e.bloomDiffusion.HasValue) b.diffusion.Override(e.bloomDiffusion.Value);
                if (e.bloomAnamorphicRatio.HasValue) b.anamorphicRatio.Override(e.bloomAnamorphicRatio.Value);
                if (e.bloomColor != null) b.color.Override(LanbaiGradeUtil.BloomColourFor(e));
                if (e.bloomFastMode.HasValue) b.fastMode.Override(e.bloomFastMode.Value);
                EditorUtility.SetDirty(b);
            }
            if (e.HasVignette)
            {
                var v = GetOrAdd<Vignette>(profile);
                if (e.vignetteMode != null)
                {
                    if (e.vignetteMode != "Classic") { error = "vignette mode " + e.vignetteMode + " unsupported"; return null; }
                    v.mode.Override(VignetteMode.Classic);
                }
                if (e.vignetteColor != null) v.color.Override(LanbaiGradeUtil.Hex(e.vignetteColor));
                if (e.vignetteCenter != null) v.center.Override(new Vector2(e.vignetteCenter[0], e.vignetteCenter[1]));
                if (e.vignetteIntensity.HasValue) v.intensity.Override(e.vignetteIntensity.Value);
                if (e.vignetteSmoothness.HasValue) v.smoothness.Override(e.vignetteSmoothness.Value);
                if (e.vignetteRoundness.HasValue) v.roundness.Override(e.vignetteRoundness.Value);
                if (e.vignetteRounded.HasValue) v.rounded.Override(e.vignetteRounded.Value);
                EditorUtility.SetDirty(v);
            }
            if (e.HasGrain)
            {
                var g = GetOrAdd<Grain>(profile);
                if (e.grainColored.HasValue) g.colored.Override(e.grainColored.Value);
                if (e.grainIntensity.HasValue) g.intensity.Override(e.grainIntensity.Value);
                if (e.grainSize.HasValue) g.size.Override(e.grainSize.Value);
                if (e.grainLumContrib.HasValue) g.lumContrib.Override(e.grainLumContrib.Value);
                EditorUtility.SetDirty(g);
            }
            profile.isDirty = true;
            EditorUtility.SetDirty(profile);
            return profile;
        }

        /// <summary>Removes null entries, duplicates and every effect type not in 'need' (sub-assets destroyed too).</summary>
        internal static void PruneSettings(PostProcessProfile profile, List<Type> need)
        {
            var seen = new HashSet<Type>();
            var remove = new List<PostProcessEffectSettings>();
            var keep = new List<PostProcessEffectSettings>();
            foreach (var s in profile.settings)
            {
                if (s == null) continue;
                Type t = s.GetType();
                if (!need.Contains(t) || seen.Contains(t)) { remove.Add(s); continue; }
                seen.Add(t);
                keep.Add(s);
            }
            if (remove.Count == 0 && keep.Count == profile.settings.Count) return;
            profile.settings.Clear();
            profile.settings.AddRange(keep);
            profile.isDirty = true;
            EditorUtility.SetDirty(profile);
            foreach (var s in remove)
            {
                if (AssetDatabase.IsSubAsset(s)) AssetDatabase.RemoveObjectFromAsset(s);
                Object.DestroyImmediate(s, true);
            }
        }

        /// <summary>Existing effect (all overrides reset to off) or a new one stored as a sub-asset of the profile.</summary>
        internal static T GetOrAdd<T>(PostProcessProfile profile) where T : PostProcessEffectSettings
        {
            T s = profile.GetSetting<T>();
            if (s == null)
            {
                s = profile.AddSettings<T>();                  // CreateInstance, hide flags, enabled = true
                if (EditorUtility.IsPersistent(profile)) AssetDatabase.AddObjectToAsset(s, profile);
            }
            s.active = true;
            s.enabled.overrideState = true;
            s.enabled.value = true;
            s.SetAllOverridesTo(false, true);                  // only what we write below stays overridden
            return s;
        }

        // -----------------------------------------------------------------------------------------
        static PostProcessVolume BuildVolume(Transform group, LanbaiGradeEntry e, PostProcessProfile profile, int layer)
        {
            string name = VolumePrefix + e.id;
            Transform t = group.Find(name);
            GameObject go;
            if (t == null)
            {
                go = new GameObject(name);
                go.layer = layer;                                // before the volume registers itself
                Undo.RegisterCreatedObjectUndo(go, UndoName);
                Undo.SetTransformParent(go.transform, group, UndoName);
                go.transform.localPosition = Vector3.zero;
                go.transform.localRotation = Quaternion.identity;
                go.transform.localScale = Vector3.one;
            }
            else
            {
                go = t.gameObject;
                Undo.RecordObject(go, UndoName);
                go.layer = layer;
            }
            if (!go.activeSelf) go.SetActive(true);
            var vol = go.GetComponent<PostProcessVolume>();
            if (vol == null) vol = Undo.AddComponent<PostProcessVolume>(go);
            else Undo.RecordObject(vol, UndoName);
            vol.enabled = true;
            vol.isGlobal = true;
            vol.blendDistance = 0f;
            vol.priority = e.priority;
            vol.weight = e.initialWeight;
            vol.sharedProfile = profile;                          // never touch vol.profile (it clones)
            EditorUtility.SetDirty(vol);
            return vol;
        }

        // =========================================================================================
        // Weights
        // =========================================================================================
        /// <summary>All volumes under Lanbai_Grades, by entry id.</summary>
        public static Dictionary<string, PostProcessVolume> FindVolumes()
        {
            var map = new Dictionary<string, PostProcessVolume>();
            GameObject root = LanbaiGradeUtil.FindRoot(SceneManager.GetActiveScene(), RootName);
            if (root == null) return map;
            foreach (var e in LanbaiGradeData.Entries)
            {
                Transform t = root.transform.Find(e.group + "/" + VolumePrefix + e.id);
                if (t == null) continue;
                var v = t.GetComponent<PostProcessVolume>();
                if (v != null) map[e.id] = v;
            }
            return map;
        }

        public static string RestoreInitialWeights()
        {
            var map = FindVolumes();
            if (map.Count == 0) return "no volumes: run Build Profiles & Volumes first";
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (map.TryGetValue(e.id, out v)) SetWeight(v, e.initialWeight);
            }
            InternalRepaint();
            return "weights restored (S1 = 1, LENS_CLEAN = 1, everything else 0)";
        }

        /// <summary>Scene profile 'id' alone at weight 1 (other scenes and helpers 0; lens layers untouched).</summary>
        public static string Solo(string id)
        {
            var e0 = LanbaiGradeData.Find(id);
            if (e0 == null || e0.kind != LanbaiGradeKind.Scene) return "unknown scene profile '" + id + "'";
            var map = FindVolumes();
            if (map.Count == 0) return "no volumes: run Build Profiles & Volumes first";
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (!map.TryGetValue(e.id, out v)) continue;
                if (e.kind == LanbaiGradeKind.Scene) SetWeight(v, e.id == id ? 1f : 0f);
                else if (e.kind == LanbaiGradeKind.Helper) SetWeight(v, 0f);
            }
            InternalRepaint();
            return "solo " + id + " " + e0.shortName;
        }

        internal static void SetWeight(PostProcessVolume v, float w)
        {
            if (Mathf.Approximately(v.weight, w)) return;
            if (!EditorApplication.isPlaying) Undo.RecordObject(v, "蓝白 grade weight");
            v.weight = Mathf.Clamp01(w);
            if (!EditorApplication.isPlaying) EditorUtility.SetDirty(v);
        }

        internal static void InternalRepaint()
        {
            SceneView.RepaintAll();
            UnityEditorInternal.InternalEditorUtility.RepaintAllViews();
        }

        // =========================================================================================
        // Validation
        // =========================================================================================
        public static string ValidateScene()
        {
            var profiles = new Dictionary<string, PostProcessProfile>();
            string folder = LanbaiGradeUtil.KitFolder() + "/Profiles";
            foreach (var e in LanbaiGradeData.Entries)
            {
                var p = AssetDatabase.LoadAssetAtPath<PostProcessProfile>(folder + "/" + ProfilePrefix + e.id + ".asset");
                if (p != null) profiles[e.id] = p;
            }
            int errors = 0, warnings = 0;
            string md = ValidateInternal(profiles, ref errors, ref warnings);
            string path = LanbaiGradeUtil.WriteReport("GradeValidate_Report.md", "# 蓝白 Grades · validation\n\n" + md);
            return (errors == 0 ? "OK" : "ERRORS " + errors) + ", warnings " + warnings + ". Report: " + path;
        }

        static string ValidateInternal(Dictionary<string, PostProcessProfile> profiles, ref int errors, ref int warnings)
        {
            var md = new StringBuilder();

            // ---- (a) every profile: effect list + override list, compared with the data table
            md.AppendLine("## Profiles (values read from the profile assets after saving)");
            md.AppendLine();
            md.AppendLine("| id | effects | overridden parameters | value check |");
            md.AppendLine("|---|---|---|---|");
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessProfile p;
                if (!profiles.TryGetValue(e.id, out p)) { errors++; md.AppendLine("| " + e.id + " | MISSING | | |"); continue; }
                var effects = new List<string>();
                foreach (var s in p.settings) if (s != null) effects.Add(s.GetType().Name);
                var ov = OverriddenParams(p);
                var bad = new List<string>();
                CompareValues(e, p, bad);
                foreach (var s in p.settings)
                    if (s != null && Array.IndexOf(LanbaiGradeData.ForbiddenEffects, s.GetType().Name) >= 0)
                        bad.Add("forbidden effect " + s.GetType().Name);
                if (e.kind == LanbaiGradeKind.Scene)
                {
                    string want = string.Join(",", SceneOverrideSet), got = string.Join(",", ov.ToArray());
                    if (want != got) bad.Add("scene override set differs from bible 1.4: " + got);
                }
                if (bad.Count > 0) errors++;
                md.AppendLine("| " + e.id + " | " + string.Join(", ", effects.ToArray()) + " | " + ov.Count + ": "
                              + string.Join(" ", ov.ToArray()) + " | " + (bad.Count == 0 ? "OK" : string.Join("; ", bad.ToArray())) + " |");
            }
            md.AppendLine();

            // ---- (b) scene volumes
            md.AppendLine("## Scene");
            md.AppendLine();
            var map = FindVolumes();
            int ppLayer = LayerMask.NameToLayer(VolumeLayerName);
            bool routeC = CurrentRouteIsC();
            md.AppendLine("- route: " + (routeC ? "**C** (External LUT fallback). LanbaiExposure needs `routeC` ticked (b = 0); exposure-changing crossfades use RouteCCrossfadeWeight"
                                                : "A (parametric profiles, default)"));
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (!map.TryGetValue(e.id, out v)) { errors++; md.AppendLine("- ERROR volume " + VolumePrefix + e.id + " missing"); continue; }
                string want = (routeC && e.kind == LanbaiGradeKind.Scene ? RouteCProfilePrefix : ProfilePrefix) + e.id;
                if (!v.isGlobal || v.gameObject.layer != ppLayer || !Mathf.Approximately(v.priority, e.priority)
                    || v.sharedProfile == null || v.sharedProfile.name != want)
                { errors++; md.AppendLine("- ERROR volume " + v.name + " misconfigured (global/layer/priority/profile; expected profile " + want + ")"); }
                if (!v.enabled || !v.gameObject.activeInHierarchy)
                {
                    if (e.kind == LanbaiGradeKind.Lens) md.AppendLine("- note: " + v.name + " is disabled (fine in VR tests: LanbaiExposure switches the lens group off in VR)");
                    else { warnings++; md.AppendLine("- WARNING " + v.name + " is disabled or inactive: PPv2 skips it. Drive scene / helper volumes by weight only, never by SetActive / enabled"); }
                }
                if (routeC && e.kind == LanbaiGradeKind.Scene && v.sharedProfile != null)
                {
                    ColorGrading cg;
                    if (!v.sharedProfile.TryGetSettings(out cg) || cg.gradingMode.value != GradingMode.External || cg.externalLut.value == null
                        || Mathf.Abs(cg.postExposure.value) > 1e-6f)
                    { errors++; md.AppendLine("- ERROR Route C profile " + v.sharedProfile.name + ": needs gradingMode External, an external LUT and postExposure 0"); }
                }
            }
            var foreign = new List<string>();
            foreach (var v in Object.FindObjectsOfType<PostProcessVolume>(true))
            {
                if (map.ContainsValue(v)) continue;
                if (LanbaiGradeUtil.IsUnder(v.transform, "Lanbai_TestCard")) continue;   // our debug volumes
                foreign.Add(LanbaiGradeUtil.PathOf(v.transform) + " (priority " + v.priority + ", weight " + v.weight
                            + (v.isGlobal ? ", GLOBAL" : "") + ")");
            }
            if (foreign.Count > 0)
            {
                warnings++;
                md.AppendLine("- WARNING " + foreign.Count + " PostProcessVolume(s) that are not ours: they blend into the Lanbai grade "
                              + "(PPv2 lerps every volume in priority order). Disable or delete the old build's volumes:");
                foreach (var f in foreign) md.AppendLine("  - `" + f + "`");
            }
            else md.AppendLine("- no foreign PostProcessVolumes in the scene");

            // ---- (c) camera + project
            md.AppendLine();
            md.AppendLine("## Camera & project (bible 1.4)");
            md.AppendLine();
            foreach (var line in CheckCameraAndProject(ref errors, ref warnings)) md.AppendLine("- " + line);
            md.AppendLine();
            return md.ToString();
        }

        /// <summary>Sorted "Effect.param" list of every parameter with overrideState == true (the 'enabled' flag excluded).</summary>
        public static List<string> OverriddenParams(PostProcessProfile p)
        {
            var list = new List<string>();
            foreach (var s in p.settings)
            {
                if (s == null) continue;
                foreach (var f in s.GetType().GetFields(BindingFlags.Public | BindingFlags.Instance))
                {
                    if (f.Name == "enabled" || !typeof(ParameterOverride).IsAssignableFrom(f.FieldType)) continue;
                    var po = f.GetValue(s) as ParameterOverride;
                    if (po != null && po.overrideState) list.Add(s.GetType().Name + "." + f.Name);
                }
            }
            list.Sort(StringComparer.Ordinal);
            return list;
        }

        static void CompareValues(LanbaiGradeEntry e, PostProcessProfile p, List<string> bad)
        {
            ColorGrading cg; Bloom b; Vignette v; Grain g;
            if (p.TryGetSettings(out cg))
            {
                if (e.hdrNeutral == true && (cg.gradingMode.value != GradingMode.HighDefinitionRange || cg.tonemapper.value != Tonemapper.Neutral))
                    bad.Add("gradingMode/tonemapper");
                F(bad, "postExposure", e.postExposure, cg.postExposure.value);
                F(bad, "temperature", e.temperature, cg.temperature.value);
                F(bad, "tint", e.tint, cg.tint.value);
                F(bad, "hueShift", e.hueShift, cg.hueShift.value);
                F(bad, "saturation", e.saturation, cg.saturation.value);
                F(bad, "contrast", e.contrast, cg.contrast.value);
                C(bad, "colorFilter", e.colorFilter, cg.colorFilter.value);
                V(bad, "lift", e.lift, cg.lift.value);
                V(bad, "gamma", e.gamma, cg.gamma.value);
                V(bad, "gain", e.gain, cg.gain.value);
                if (e.channelMixer != null)
                {
                    float[] m = e.channelMixer;
                    float[] got = { cg.mixerRedOutRedIn.value, cg.mixerRedOutGreenIn.value, cg.mixerRedOutBlueIn.value,
                                    cg.mixerGreenOutRedIn.value, cg.mixerGreenOutGreenIn.value, cg.mixerGreenOutBlueIn.value,
                                    cg.mixerBlueOutRedIn.value, cg.mixerBlueOutGreenIn.value, cg.mixerBlueOutBlueIn.value };
                    for (int i = 0; i < 9; i++)
                        if (Mathf.Abs(m[i] - got[i]) > 1e-4f) { bad.Add("channel mixer[" + i + "] " + got[i].ToString("R", CultureInfo.InvariantCulture) + " != " + m[i].ToString("R", CultureInfo.InvariantCulture)); break; }
                }
            }
            else if (e.HasColorGrading) bad.Add("ColorGrading missing");
            if (p.TryGetSettings(out b))
            {
                F(bad, "bloom.intensity", e.bloomIntensity, b.intensity.value);
                F(bad, "bloom.threshold", e.bloomThreshold, b.threshold.value);
                F(bad, "bloom.softKnee", e.bloomSoftKnee, b.softKnee.value);
                F(bad, "bloom.clamp", e.bloomClamp, b.clamp.value);
                F(bad, "bloom.diffusion", e.bloomDiffusion, b.diffusion.value);
                F(bad, "bloom.anamorphicRatio", e.bloomAnamorphicRatio, b.anamorphicRatio.value);
                if (e.bloomColor != null) CC(bad, "bloom.color", LanbaiGradeUtil.BloomColourFor(e), b.color.value,
                                             e.bloomColor + (LanbaiGradeUtil.BloomColourCompensation ? " (compensated)" : ""));
                if (e.bloomFastMode.HasValue && b.fastMode.value != e.bloomFastMode.Value) bad.Add("bloom.fastMode");
            }
            else if (e.HasBloom) bad.Add("Bloom missing");
            if (p.TryGetSettings(out v))
            {
                F(bad, "vignette.intensity", e.vignetteIntensity, v.intensity.value);
                F(bad, "vignette.smoothness", e.vignetteSmoothness, v.smoothness.value);
                F(bad, "vignette.roundness", e.vignetteRoundness, v.roundness.value);
                C(bad, "vignette.color", e.vignetteColor, v.color.value);
            }
            else if (e.HasVignette) bad.Add("Vignette missing");
            if (p.TryGetSettings(out g))
            {
                F(bad, "grain.intensity", e.grainIntensity, g.intensity.value);
                F(bad, "grain.size", e.grainSize, g.size.value);
                F(bad, "grain.lumContrib", e.grainLumContrib, g.lumContrib.value);
                if (e.grainColored.HasValue && g.colored.value != e.grainColored.Value) bad.Add("grain.colored");
            }
            else if (e.HasGrain) bad.Add("Grain missing");
        }

        static void F(List<string> bad, string n, float? want, float got)
        {
            if (want.HasValue && Mathf.Abs(want.Value - got) > 1e-5f) bad.Add(n + " " + got.ToString("R", CultureInfo.InvariantCulture) + " != " + want.Value.ToString("R", CultureInfo.InvariantCulture));
        }
        static void C(List<string> bad, string n, string want, Color got)
        {
            if (want == null) return;
            Color w = LanbaiGradeUtil.Hex(want);
            if (Mathf.Abs(w.r - got.r) > 1e-4f || Mathf.Abs(w.g - got.g) > 1e-4f || Mathf.Abs(w.b - got.b) > 1e-4f) bad.Add(n + " != " + want);
        }
        static void CC(List<string> bad, string n, Color w, Color got, string label)
        {
            if (Mathf.Abs(w.r - got.r) > 1e-4f || Mathf.Abs(w.g - got.g) > 1e-4f || Mathf.Abs(w.b - got.b) > 1e-4f) bad.Add(n + " != " + label);
        }
        static void V(List<string> bad, string n, float[] want, Vector4 got)
        {
            if (want == null) return;
            for (int i = 0; i < 4; i++) if (Mathf.Abs(want[i] - got[i]) > 1e-5f) { bad.Add(n + " != (" + string.Join(", ", Array.ConvertAll(want, x => x.ToString("R", CultureInfo.InvariantCulture))) + ")"); return; }
        }

        static List<string> CheckCameraAndProject(ref int errors, ref int warnings)
        {
            var o = new List<string>();
            if (PlayerSettings.colorSpace != ColorSpace.Linear) { errors++; o.Add("ERROR Player Settings colour space is " + PlayerSettings.colorSpace + " (must be Linear)"); }
            else o.Add("colour space Linear");
            // Tier settings read by reflection: the API moved between Unity versions (BuildTargetGroup / NamedBuildTarget).
            try
            {
                Type egs = typeof(Editor).Assembly.GetType("UnityEditor.Rendering.EditorGraphicsSettings");
                MethodInfo get = egs == null ? null : egs.GetMethod("GetTierSettings", BindingFlags.Public | BindingFlags.Static, null,
                                                                   new Type[] { typeof(BuildTargetGroup), typeof(GraphicsTier) }, null);
                if (get == null) o.Add("(tier settings API not found: check Graphics > Tier Settings HDR on / FP16 by hand)");
                else
                {
                    foreach (GraphicsTier tier in new[] { GraphicsTier.Tier1, GraphicsTier.Tier2, GraphicsTier.Tier3 })
                    {
                        object ts = get.Invoke(null, new object[] { BuildTargetGroup.Standalone, tier });
                        FieldInfo fHdr = ts.GetType().GetField("hdr"), fMode = ts.GetType().GetField("hdrMode");
                        bool hdr = fHdr != null && (bool)fHdr.GetValue(ts);
                        object mode = fMode != null ? fMode.GetValue(ts) : null;
                        if (!hdr || mode == null || mode.ToString() != "FP16")
                        { warnings++; o.Add("WARNING Graphics > Tier Settings (Standalone " + tier + "): HDR " + hdr + ", mode " + mode + " (bible: HDR on, FP16)"); }
                    }
                }
            }
            catch (Exception ex) { o.Add("(could not read tier settings: " + ex.Message + ")"); }

            Camera cam = LanbaiGradeUtil.FindReferenceCamera();
            if (cam == null) { warnings++; o.Add("WARNING no VRC scene descriptor ReferenceCamera found (checked by reflection)"); return o; }
            o.Add("reference camera `" + LanbaiGradeUtil.PathOf(cam.transform) + "`");
            if (!cam.allowHDR) { errors++; o.Add("ERROR reference camera Allow HDR is off"); }
            if (cam.nearClipPlane > 0.0501f || cam.farClipPlane < 44999f) { warnings++; o.Add("WARNING near/far = " + cam.nearClipPlane + " / " + cam.farClipPlane + " (bible: 0.05 / 45000)"); }
            var ppl = cam.GetComponent<PostProcessLayer>();
            int ppLayer = LayerMask.NameToLayer(VolumeLayerName);
            if (ppl == null) { errors++; o.Add("ERROR reference camera has no PostProcessLayer"); return o; }
            if (ppLayer < 0 || (ppl.volumeLayer.value & (1 << ppLayer)) == 0) { errors++; o.Add("ERROR PostProcessLayer.volumeLayer does not include '" + VolumeLayerName + "'"); }
            if (ppl.volumeLayer.value != (ppLayer >= 0 ? 1 << ppLayer : 0)) { warnings++; o.Add("WARNING volumeLayer mask " + ppl.volumeLayer.value + " includes more than '" + VolumeLayerName + "'"); }
            if (ppl.antialiasingMode != PostProcessLayer.Antialiasing.None) { warnings++; o.Add("WARNING anti-aliasing " + ppl.antialiasingMode + " (bible: None)"); }
            if (!ppl.stopNaNPropagation) { warnings++; o.Add("WARNING Stop NaN Propagation off (bible: on)"); }
            if (ppl.finalBlitToCameraTarget) { warnings++; o.Add("WARNING Directly to Camera Target on (bible: off)"); }
            o.Add("PPv2 dithering has no switch in 3.x: it is always applied in the final pass (= the bible's 'Dithering on')");
            return o;
        }

        /// <summary>Applies bible 1.4 to the VRC ReferenceCamera (or the selected camera): HDR, near/far, PostProcessLayer.</summary>
        public static string ConfigureReferenceCamera()
        {
            if (EditorApplication.isPlaying) return "leave Play mode first";
            Camera cam = LanbaiGradeUtil.FindReferenceCamera();
            if (cam == null && Selection.activeGameObject != null) cam = Selection.activeGameObject.GetComponent<Camera>();
            if (cam == null) return "no ReferenceCamera on the VRC scene descriptor and no camera selected";
            var sb = new StringBuilder();
            int ppLayer = LanbaiGradeUtil.EnsureLayer(VolumeLayerName, sb);
            if (ppLayer < 0) return "no free layer for " + VolumeLayerName;
            Undo.RecordObject(cam, "蓝白 camera");
            cam.allowHDR = true;
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 45000f;
            cam.clearFlags = CameraClearFlags.Skybox;
            var ppl = cam.GetComponent<PostProcessLayer>();
            if (ppl == null) ppl = Undo.AddComponent<PostProcessLayer>(cam.gameObject);
            else Undo.RecordObject(ppl, "蓝白 camera");
            LanbaiGradeUtil.EnsureLayerResources(ppl);
            ppl.volumeTrigger = cam.transform;
            ppl.volumeLayer = 1 << ppLayer;
            ppl.antialiasingMode = PostProcessLayer.Antialiasing.None;
            ppl.stopNaNPropagation = true;
            ppl.finalBlitToCameraTarget = false;
            EditorUtility.SetDirty(cam);
            EditorUtility.SetDirty(ppl);
            EditorSceneManager.MarkSceneDirty(cam.gameObject.scene);
            return "configured " + LanbaiGradeUtil.PathOf(cam.transform) + ": HDR on, near 0.05, far 45000, Skybox, PostProcessLayer "
                   + "(volume layer '" + VolumeLayerName + "', trigger = camera, AA None, Stop NaN on, direct-to-target off). "
                   + "Also set Graphics > Tier Settings HDR on / FP16 by hand (bible 1.4). " + sb;
        }

        // =========================================================================================
        // Bloom colour (PPv2 decodes the bloom tint twice in a Linear project; see LanbaiGradeData header)
        // =========================================================================================
        /// <summary>true = write bloomColorCompensated (default); false = write the bible hex unchanged. Rebuilds the profiles.</summary>
        public static string SetBloomColourCompensation(bool on)
        {
            LanbaiGradeUtil.BloomColourCompensation = on;
            return "bloom colour " + (on ? "compensated for PPv2's double sRGB decode" : "written as the bible hex") + "; rebuild: " + BuildAll();
        }

        // =========================================================================================
        // Route C (bible 1.7.2): External-LUT profiles, a fallback only. The LUTs are the look itself, baked
        // (art/luts/hdr_external/*_HDRext33.cube, LogC in, display-linear out, postExposure baked in).
        // =========================================================================================
        /// <summary>true when every scene volume points at a Route C profile.</summary>
        public static bool CurrentRouteIsC()
        {
            var map = FindVolumes();
            int n = 0, c = 0;
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (e.kind != LanbaiGradeKind.Scene || !map.TryGetValue(e.id, out v)) continue;
                n++;
                if (v.sharedProfile != null && v.sharedProfile.name == RouteCProfilePrefix + e.id) c++;
            }
            return n > 0 && c == n;
        }

        /// <summary>The Texture3D PPv2's CubeLutAssetImporter made from &lt;name&gt;.cube (anywhere under Assets/), or null.</summary>
        public static Texture3D FindRouteCLut(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            foreach (string guid in AssetDatabase.FindAssets(name + " t:Texture3D"))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(p) != name) continue;
                var t = AssetDatabase.LoadAssetAtPath<Texture3D>(p);
                if (t != null) return t;
            }
            return null;
        }

        static Dictionary<string, PostProcessProfile> BuildRouteCProfiles(string folder, StringBuilder log, out string error)
        {
            error = null;
            var missing = new List<string>();
            var luts = new Dictionary<string, Texture3D>();
            foreach (var e in LanbaiGradeData.Entries)
            {
                if (e.kind != LanbaiGradeKind.Scene) continue;
                var t = FindRouteCLut(e.routeCLut);
                if (t == null) missing.Add(e.routeCLut ?? e.id);
                else if (t.width != t.height || t.width != t.depth) missing.Add(e.routeCLut + " (not a cube LUT: " + t.width + "x" + t.height + "x" + t.depth + ")");
                else luts[e.id] = t;
            }
            if (missing.Count > 0)
            {
                error = "Route C needs the 15 Texture3D LUTs that PPv2 imports from art/luts/hdr_external/*_HDRext33.cube. Copy those .cube files "
                        + "(only those: bible 1.7) anywhere under Assets/, wait for the import, then run this again. Missing: " + string.Join(", ", missing.ToArray());
                return null;
            }
            string dir = folder + "/RouteC";
            LanbaiGradeUtil.EnsureFolder(dir);
            var map = new Dictionary<string, PostProcessProfile>();
            foreach (var e in LanbaiGradeData.Entries)
            {
                if (e.kind != LanbaiGradeKind.Scene) continue;
                string path = dir + "/" + RouteCProfilePrefix + e.id + ".asset";
                var profile = AssetDatabase.LoadAssetAtPath<PostProcessProfile>(path);
                if (profile == null)
                {
                    if (AssetDatabase.LoadMainAssetAtPath(path) != null) { error = "an asset that is not a PostProcessProfile sits at " + path; return null; }
                    profile = ScriptableObject.CreateInstance<PostProcessProfile>();
                    AssetDatabase.CreateAsset(profile, path);
                }
                PruneSettings(profile, new List<Type> { typeof(ColorGrading), typeof(Bloom), typeof(Vignette), typeof(Grain) });
                var cg = GetOrAdd<ColorGrading>(profile);
                cg.gradingMode.Override(GradingMode.External);
                cg.externalLut.Override(luts[e.id]);
                cg.postExposure.Override(0f);                 // baked into the LUT; EXPO helpers still work (b = 0)
                EditorUtility.SetDirty(cg);
                var b = GetOrAdd<Bloom>(profile);             // bloom happens before the LUT: identical to Route A
                if (e.bloomIntensity.HasValue) b.intensity.Override(e.bloomIntensity.Value);
                if (e.bloomThreshold.HasValue) b.threshold.Override(e.bloomThreshold.Value);
                if (e.bloomSoftKnee.HasValue) b.softKnee.Override(e.bloomSoftKnee.Value);
                if (e.bloomClamp.HasValue) b.clamp.Override(e.bloomClamp.Value);
                if (e.bloomDiffusion.HasValue) b.diffusion.Override(e.bloomDiffusion.Value);
                if (e.bloomAnamorphicRatio.HasValue) b.anamorphicRatio.Override(e.bloomAnamorphicRatio.Value);
                if (e.bloomColor != null) b.color.Override(LanbaiGradeUtil.BloomColourFor(e));
                if (e.bloomFastMode.HasValue) b.fastMode.Override(e.bloomFastMode.Value);
                EditorUtility.SetDirty(b);
                var vg = GetOrAdd<Vignette>(profile); vg.intensity.Override(0f); EditorUtility.SetDirty(vg);
                var gr = GetOrAdd<Grain>(profile); gr.intensity.Override(0f); EditorUtility.SetDirty(gr);
                profile.isDirty = true;
                EditorUtility.SetDirty(profile);
                map[e.id] = profile;
            }
            AssetDatabase.SaveAssets();
            if (log != null) log.AppendLine("- Route C profiles (re)built in " + dir);
            return map;
        }

        /// <summary>Builds the Route C profiles and points the 15 scene volumes at them (helpers and lens layers unchanged).</summary>
        public static string UseRouteC()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) return "leave Play mode first";
            var map = FindVolumes();
            if (map.Count == 0) return "no volumes: run Build Profiles & Volumes first";
            var log = new StringBuilder();
            string err;
            var pcs = BuildRouteCProfiles(LanbaiGradeUtil.KitFolder() + "/Profiles", log, out err);
            if (pcs == null) return "ERROR: " + err;
            int n = 0;
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v; PostProcessProfile pc;
                if (e.kind != LanbaiGradeKind.Scene || !map.TryGetValue(e.id, out v) || !pcs.TryGetValue(e.id, out pc)) continue;
                Undo.RecordObject(v, "蓝白 Route C");
                v.sharedProfile = pc;
                EditorUtility.SetDirty(v);
                n++;
            }
            LanbaiGradeUtil.ResortVolumes(map.Values);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            InternalRepaint();
            return "Route C: " + n + " scene volumes now use External-LUT profiles (postExposure 0 baked in). Tick 'routeC' on LanbaiExposure "
                   + "(b = 0) and use LanbaiExposure.RouteCCrossfadeWeight for the exposure-changing crossfades (2->3, 7b->8, 11->12). "
                   + "Measure Test Card checks it the same way. " + log.ToString().Replace("\n", " ");
        }

        /// <summary>Points the scene volumes back at the parametric profiles (Route A, the default).</summary>
        public static string UseRouteA()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) return "leave Play mode first";
            var map = FindVolumes();
            if (map.Count == 0) return "no volumes: run Build Profiles & Volumes first";
            string folder = LanbaiGradeUtil.KitFolder() + "/Profiles";
            int n = 0;
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (e.kind != LanbaiGradeKind.Scene || !map.TryGetValue(e.id, out v)) continue;
                var p = AssetDatabase.LoadAssetAtPath<PostProcessProfile>(folder + "/" + ProfilePrefix + e.id + ".asset");
                if (p == null) return "ERROR: " + ProfilePrefix + e.id + " missing: run Build Profiles & Volumes";
                Undo.RecordObject(v, "蓝白 Route A");
                v.sharedProfile = p;
                EditorUtility.SetDirty(v);
                n++;
            }
            LanbaiGradeUtil.ResortVolumes(map.Values);
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            InternalRepaint();
            return "Route A: " + n + " scene volumes use the parametric profiles again (untick 'routeC' on LanbaiExposure).";
        }

        // =========================================================================================
        // Animator fallback (bible 1.4: "若 SDK 未暴露，给每个 volume 一个 Animator 驱动 weight")
        // =========================================================================================
        public static string AddAnimatorFallback()
        {
            if (EditorApplication.isPlaying) return "leave Play mode first";
            var map = FindVolumes();
            if (map.Count == 0) return "no volumes: run Build Profiles & Volumes first";
            string folder = LanbaiGradeUtil.KitFolder() + "/Fallback";
            LanbaiGradeUtil.EnsureFolder(folder);

            string clipPath = folder + "/PPV_Weight_0to1.anim";
            var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
            if (clip == null) { clip = new AnimationClip(); AssetDatabase.CreateAsset(clip, clipPath); }
            clip.ClearCurves();
            var binding = EditorCurveBinding.FloatCurve("", typeof(PostProcessVolume), "weight");
            AnimationUtility.SetEditorCurve(clip, binding, AnimationCurve.Linear(0f, 0f, 1f, 1f));
            var cs = AnimationUtility.GetAnimationClipSettings(clip);
            cs.loopTime = false;
            AnimationUtility.SetAnimationClipSettings(clip, cs);
            EditorUtility.SetDirty(clip);

            var c0 = FallbackController(folder + "/PPV_Weight_default0.controller", clip, 0f);
            var c1 = FallbackController(folder + "/PPV_Weight_default1.controller", clip, 1f);
            AssetDatabase.SaveAssets();

            int n = 0;
            foreach (var e in LanbaiGradeData.Entries)
            {
                PostProcessVolume v;
                if (!map.TryGetValue(e.id, out v)) continue;
                var a = v.GetComponent<Animator>();
                if (a == null) a = Undo.AddComponent<Animator>(v.gameObject);
                else Undo.RecordObject(a, "蓝白 fallback");
                a.runtimeAnimatorController = e.initialWeight > 0.5f ? c1 : c0;
                a.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                a.applyRootMotion = false;
                EditorUtility.SetDirty(a);
                n++;
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return "Animator weight drivers on " + n + " volumes (float parameter \"w\" = weight). Now add the scripting define "
                   + "LANBAI_PPV_ANIMATOR_FALLBACK so LanbaiExposure drives the Animators. Remove both if Udon can set weight.";
        }

        static AnimatorController FallbackController(string path, AnimationClip clip, float defaultWeight)
        {
            var old = AssetDatabase.LoadAssetAtPath<AnimatorController>(path);
            if (old != null) AssetDatabase.DeleteAsset(path);                 // rebuild: simplest idempotent form
            var ctrl = AnimatorController.CreateAnimatorControllerAtPath(path);
            ctrl.AddParameter(new AnimatorControllerParameter { name = "w", type = AnimatorControllerParameterType.Float, defaultFloat = defaultWeight });
            var sm = ctrl.layers[0].stateMachine;
            var st = sm.AddState("weight");
            st.motion = clip;
            st.timeParameterActive = true;                                    // normalized time = w
            st.timeParameter = "w";
            st.writeDefaultValues = true;
            sm.defaultState = st;
            EditorUtility.SetDirty(ctrl);
            return ctrl;
        }

        public static string RemoveAnimatorFallback()
        {
            if (EditorApplication.isPlaying) return "leave Play mode first";
            int n = 0;
            foreach (var v in FindVolumes().Values)
            {
                var a = v.GetComponent<Animator>();
                if (a == null) continue;
                Undo.DestroyObjectImmediate(a);
                n++;
            }
            EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
            return "removed " + n + " Animator weight drivers (remove the LANBAI_PPV_ANIMATOR_FALLBACK define too)";
        }
    }

    // =============================================================================================
    // shared editor helpers
    // =============================================================================================
    public static class LanbaiGradeUtil
    {
        /// <summary>Folder of this kit (the folder holding Editor/LanbaiGradeBuilder.cs), e.g. "Assets/Lanbai/Grading".</summary>
        public static string KitFolder()
        {
            const string tail = "/Editor/LanbaiGradeBuilder.cs";
            foreach (string guid in AssetDatabase.FindAssets("LanbaiGradeBuilder t:MonoScript"))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid).Replace('\\', '/');
                if (p.EndsWith(tail, StringComparison.Ordinal)) return p.Substring(0, p.Length - tail.Length);
            }
            return "Assets/Lanbai/Grading";
        }

        public static void EnsureFolder(string path)
        {
            path = path.Replace('\\', '/').TrimEnd('/');
            if (AssetDatabase.IsValidFolder(path)) return;
            int i = path.LastIndexOf('/');
            if (i <= 0) return;
            string parent = path.Substring(0, i);
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, path.Substring(i + 1));
        }

        /// <summary>Layer index by name; creates it in the first empty user slot 22..31 when missing (no dialog). -1 on failure.</summary>
        public static int EnsureLayer(string name, StringBuilder log)
        {
            int l = LayerMask.NameToLayer(name);
            if (l >= 0) return l;
            Object[] assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset");
            if (assets == null || assets.Length == 0) return -1;
            var so = new SerializedObject(assets[0]);
            SerializedProperty layers = so.FindProperty("layers");
            if (layers == null || !layers.isArray) return -1;
            for (int i = 22; i < 32 && i < layers.arraySize; i++)
            {
                SerializedProperty sp = layers.GetArrayElementAtIndex(i);
                if (!string.IsNullOrEmpty(sp.stringValue)) continue;
                sp.stringValue = name;
                so.ApplyModifiedPropertiesWithoutUndo();
                AssetDatabase.SaveAssets();
                if (log != null) log.AppendLine("- created layer '" + name + "' at index " + i + " (Project Settings > Tags and Layers)");
                return i;
            }
            return -1;
        }

        /// <summary>
        /// PPv2 re-sorts a layer's volumes by priority only when the layer is marked dirty (internal API). Toggling
        /// enabled re-registers the volume (OnDisable/OnEnable -> Register -> SetLayerDirty), so the next render
        /// blends in the current priority order even if PostProcessVolume.Update has not ticked yet in edit mode.
        /// </summary>
        public static void ResortVolumes(IEnumerable<PostProcessVolume> volumes)
        {
            foreach (var v in volumes)
            {
                if (v == null || !v.enabled || !v.gameObject.activeInHierarchy) continue;
                v.enabled = false;
                v.enabled = true;
            }
        }

        public static Color Hex(string hex)
        {
            string h = hex.TrimStart('#');
            if (h.Length != 6) throw new ArgumentException("hex colour must be #RRGGBB: " + hex);
            int r = int.Parse(h.Substring(0, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
            int g = int.Parse(h.Substring(2, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
            int b = int.Parse(h.Substring(4, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
            return new Color(r / 255f, g / 255f, b / 255f, 1f);             // sRGB-coded, like the colour picker
        }

        public static Vector4 V4(float[] a) { return new Vector4(a[0], a[1], a[2], a[3]); }

        /// <summary>
        /// Project-scoped switch (EditorPrefs keyed by the project's GUID). Default true: PPv2's Bloom passes
        /// settings.color.value.linear to MaterialPropertyBlock.SetColor, which decodes sRGB again in a Linear project,
        /// so the builder writes bloomColorCompensated. 蓝白/Grades/Probe Bloom Colour measures it and sets this.
        /// </summary>
        public static bool BloomColourCompensation
        {
            get { return EditorPrefs.GetBool(BloomPrefKey(), true); }
            set { EditorPrefs.SetBool(BloomPrefKey(), value); }
        }

        static string BloomPrefKey() { return "Lanbai.Grades.BloomColourCompensation." + PlayerSettings.productGUID.ToString("N"); }

        /// <summary>The Color the builder writes into Bloom.color for this entry (see BloomColourCompensation).</summary>
        public static Color BloomColourFor(LanbaiGradeEntry e)
        {
            if (e.bloomColor == null) return Color.white;
            float[] c = e.bloomColorCompensated;
            if (BloomColourCompensation && c != null && c.Length == 3) return new Color(c[0], c[1], c[2], 1f);
            return Hex(e.bloomColor);
        }

        public static GameObject FindRoot(Scene scene, string name)
        {
            if (!scene.IsValid()) return null;
            foreach (GameObject g in scene.GetRootGameObjects()) if (g.name == name) return g;
            return null;
        }

        public static GameObject FindOrCreateRoot(Scene scene, string name, string undo)
        {
            GameObject g = FindRoot(scene, name);
            if (g != null) return g;
            g = new GameObject(name);
            SceneManager.MoveGameObjectToScene(g, scene);
            Undo.RegisterCreatedObjectUndo(g, undo);
            return g;
        }

        public static Transform FindOrCreateChild(Transform parent, string name, string undo)
        {
            Transform t = parent.Find(name);
            if (t != null) return t;
            var g = new GameObject(name);
            Undo.RegisterCreatedObjectUndo(g, undo);
            Undo.SetTransformParent(g.transform, parent, undo);
            g.transform.localPosition = Vector3.zero;
            g.transform.localRotation = Quaternion.identity;
            g.transform.localScale = Vector3.one;
            return g.transform;
        }

        public static List<Transform> Children(Transform t)
        {
            var l = new List<Transform>();
            for (int i = 0; i < t.childCount; i++) l.Add(t.GetChild(i));
            return l;
        }

        public static string PathOf(Transform t)
        {
            string p = t.name;
            while (t.parent != null) { t = t.parent; p = t.name + "/" + p; }
            return p;
        }

        public static bool IsUnder(Transform t, string rootName)
        {
            while (t != null) { if (t.parent == null && t.name == rootName) return true; t = t.parent; }
            return false;
        }

        /// <summary>VRC scene descriptor's ReferenceCamera, found by reflection (no SDK assembly reference).</summary>
        public static Camera FindReferenceCamera()
        {
            foreach (var mb in Object.FindObjectsOfType<MonoBehaviour>(true))
            {
                if (mb == null) continue;
                for (Type t = mb.GetType(); t != null; t = t.BaseType)
                {
                    if (t.Name != "VRC_SceneDescriptor" && t.Name != "VRCSceneDescriptor") continue;
                    FieldInfo f = t.GetField("ReferenceCamera", BindingFlags.Public | BindingFlags.Instance);
                    if (f == null) continue;
                    var go = f.GetValue(mb) as GameObject;
                    if (go != null) return go.GetComponent<Camera>();
                }
            }
            return null;
        }

        /// <summary>PPv2 resources for a PostProcessLayer created from script (the package's default reference, by GUID then by type).</summary>
        public static PostProcessResources FindResources()
        {
            string p = AssetDatabase.GUIDToAssetPath("d82512f9c8e5d4a4d938b575d47f88d4");   // PostProcessResources.asset in the package
            PostProcessResources r = string.IsNullOrEmpty(p) ? null : AssetDatabase.LoadAssetAtPath<PostProcessResources>(p);
            if (r != null) return r;
            foreach (string guid in AssetDatabase.FindAssets("t:PostProcessResources"))
            {
                r = AssetDatabase.LoadAssetAtPath<PostProcessResources>(AssetDatabase.GUIDToAssetPath(guid));
                if (r != null) return r;
            }
            return null;
        }

        public static void EnsureLayerResources(PostProcessLayer ppl)
        {
            var so = new SerializedObject(ppl);
            SerializedProperty sp = so.FindProperty("m_Resources");
            PostProcessResources r = FindResources();
            if (sp != null && sp.objectReferenceValue == null && r != null)
            {
                sp.objectReferenceValue = r;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            if (r != null) ppl.Init(r);
        }

        /// <summary>Reports go to &lt;project&gt;/LanbaiReports (outside Assets: nothing gets imported). Push them to FromLocal/.</summary>
        public static string ReportFolder()
        {
            string dir = Path.Combine(Directory.GetCurrentDirectory(), "LanbaiReports");
            Directory.CreateDirectory(dir);
            return dir;
        }

        public static string WriteReport(string fileName, string text)
        {
            string path = Path.Combine(ReportFolder(), fileName);
            File.WriteAllText(path, text, new UTF8Encoding(false));
            return path.Replace('\\', '/');
        }
    }
}
