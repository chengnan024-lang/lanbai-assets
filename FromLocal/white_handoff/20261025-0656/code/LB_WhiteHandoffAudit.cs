#if UNITY_EDITOR
using System;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering.PostProcessing;
using UdonSharpEditor;

namespace Lanbai.Tests
{
    // Editor-only, read-only diagnostics; quiet play does not change assets or scene data.
    [InitializeOnLoad]
    public static class LB_WhiteHandoffAudit
    {
        const string QuietKey = "Lanbai.WhiteHandoff.Quiet";
        const string VolumeKey = "Lanbai.WhiteHandoff.AudioVolume";
        static LB_WhiteHandoffAudit()
        {
            EditorApplication.playModeStateChanged += state =>
            {
                if (!SessionState.GetBool(QuietKey, false)) return;
                if (state == PlayModeStateChange.EnteredPlayMode) AudioListener.volume = 0f;
                if (state == PlayModeStateChange.EnteredEditMode)
                {
                    AudioListener.volume = SessionState.GetFloat(VolumeKey, 1f);
                    SessionState.SetBool(QuietKey, false);
                }
            };
        }
        public static string QuietNextPlay()
        {
            if (EditorApplication.isPlaying) throw new Exception("Arm quiet mode before Play");
            SessionState.SetFloat(VolumeKey, AudioListener.volume);
            SessionState.SetBool(QuietKey, true);
            return "Next diagnostic Play muted; volume restored on return to edit mode";
        }
        static string PathOf(Transform t) { return t.parent == null ? t.name : PathOf(t.parent) + "/" + t.name; }
        public static string TrialMaskPriority()
        {
            if (!EditorApplication.isPlaying) throw new Exception("Runtime-only trial requires Play");
            var j = UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();
            if (j == null || j.ppWhite == null || j.ppBlack == null) throw new Exception("Mask reference missing");
            j.ppWhite.priority = Lanbai.EditorTools.LB_Grades.MASK_PRIORITY;
            j.ppBlack.priority = Lanbai.EditorTools.LB_Grades.MASK_PRIORITY + 1f;
            return "Runtime trial: white/black mask priorities 150/151; scene assets untouched";
        }
        public static string ApplyPreviewWhitePriority()
        {
            var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || scene.path != LB_FullAssembly.Preview || scene.isDirty)
                throw new Exception("Clean FullPreview edit mode required; no unknown scene edits may be saved");
            var j = UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
            if (j == null || j.ppWhite == null || !j.useGrades || j.ppGrade.Length != 15)
                throw new Exception("Expected delivered-grade binding missing");
            if (j.ppWhite.priority != 2f) throw new Exception("White mask priority changed since audit; inspect before writing");
            Undo.RecordObject(j.ppWhite, "Fix FullPreview white mask priority");
            j.ppWhite.priority = Lanbai.EditorTools.LB_Grades.MASK_PRIORITY;
            EditorUtility.SetDirty(j.ppWhite);
            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
            Undo.FlushUndoRecordObjects();
            if (!UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene)) throw new Exception("Preview scene save failed");
            return "Saved only FullPreview: PP_White priority 2 -> 150; PP_Black unchanged";
        }
        public static string PreserveDirtyPreview()
        {
            var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || scene.path != LB_FullAssembly.Preview)
                throw new Exception("FullPreview edit mode required");
            if (!scene.isDirty) return "Preview already clean";
            const string copy = "E:/IDMdownload/VRCC/Backups/continuation_20261025/takeover_0650/unsaved_preview_after_test.unity";
            if (System.IO.File.Exists(copy)) throw new Exception("Snapshot exists; inspect it rather than overwrite");
            Undo.FlushUndoRecordObjects();
            if (!UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene, copy, true)) throw new Exception("Snapshot failed; original scene left untouched");
            using (var sha = System.Security.Cryptography.SHA256.Create())
            {
                string saved = Convert.ToBase64String(sha.ComputeHash(System.IO.File.ReadAllBytes(scene.path)));
                string captured = Convert.ToBase64String(sha.ComputeHash(System.IO.File.ReadAllBytes(copy)));
                if (saved != captured) return "Preserved unsaved snapshot; differs from disk, left scene dirty: " + copy;
            }
            if (!UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene)) throw new Exception("Identical scene save failed");
            return "Unsaved snapshot byte-identical to disk; flushed deferred Undo dirtiness and saved FullPreview only";
        }
        public static string Inspect()
        {
            var j = UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
            if (j == null) throw new Exception("Journey missing");
            var sb = new StringBuilder();
            sb.AppendLine("playing=" + EditorApplication.isPlaying + " audio=" + AudioListener.volume);
            sb.AppendLine("segStart=" + string.Join(",", j.segStart.Select(x => x.ToString("F3"))));
            sb.AppendLine("cueF=" + string.Join(",", j.cueF.Select(x => x.ToString("F3"))));
            sb.AppendLine("starCross=" + string.Join(",", j.starCross.Select(x => x.ToString("F3"))));
            if (EditorApplication.isPlaying)
            {
                var u = UdonSharpEditorUtility.GetBackingUdonBehaviour(j);
                foreach (var key in new[] { "dbgT", "dbgSeg", "dbgDEV", "dbgB", "_alpha", "useGrades", "ppWhite", "ppBlack" })
                    sb.AppendLine("runtime " + key + "=" + u.GetProgramVariable(key));
                sb.AppendLine(LB_FullAssembly.RuntimeState());
            }
            foreach (var v in UnityEngine.Object.FindObjectsOfType<PostProcessVolume>(true))
            {
                if (v.weight <= 0f && v != j.ppWhite && v != j.ppBlack) continue;
                sb.AppendLine("volume " + PathOf(v.transform) + " layer=" + v.gameObject.layer + " enabled=" + v.enabled + " active=" + v.gameObject.activeInHierarchy + " weight=" + v.weight + " priority=" + v.priority + " profile=" + (v.sharedProfile == null ? "null" : AssetDatabase.GetAssetPath(v.sharedProfile)) + " WHITE=" + (v == j.ppWhite) + " BLACK=" + (v == j.ppBlack));
                var profile = v.profile;
                if (profile == null) continue;
                foreach (var s in profile.settings)
                {
                    sb.AppendLine("  " + s.GetType().Name + " active=" + s.active + " enabled=" + s.enabled.value);
                    if (s is ColorGrading cg) sb.AppendLine("    postExposure=" + cg.postExposure.value + " override=" + cg.postExposure.overrideState);
                }
            }
            return sb.ToString();
        }
    }
}
#endif
