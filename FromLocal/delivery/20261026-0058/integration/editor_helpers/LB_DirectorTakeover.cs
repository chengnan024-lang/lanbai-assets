#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Globalization;
using System.Text;
using UnityEngine;
using UnityEditor;
using UnityEngine.SceneManagement;
using UnityEditor.SceneManagement;
using UdonSharpEditor;
using VRC.Udon;

namespace Lanbai.Tests
{
    // Runtime-only spawn diagnostics, plus a guarded save of the authorized wire operation.
    public static class LB_DirectorTakeover
    {
        const string Out = "E:/IDMdownload/VRCC/Backups/continuation_20261026/delivery_0058/director";
        static bool frozen;
        static float frozenT;
        static void HoldTimeline()
        {
            if(!EditorApplication.isPlaying || !frozen) { EditorApplication.update-=HoldTimeline; return; }
            Journey().SetProgramVariable("departureMs",VRC.SDKBase.Networking.GetServerTimeInMilliseconds()-Mathf.RoundToInt(frozenT*1000f));
        }
        public static string FreezeTimeline(string seconds)
        {
            Journey(); frozenT=float.Parse(seconds,CultureInfo.InvariantCulture); frozen=true;
            EditorApplication.update-=HoldTimeline; EditorApplication.update+=HoldTimeline;
            return "Runtime timeline paused at "+frozenT+"; wall clock continues";
        }
        public static string UnfreezeTimeline()
        {
            frozen=false; EditorApplication.update-=HoldTimeline;
            return "Runtime timeline released";
        }
        static UdonBehaviour Journey()
        {
            if (!EditorApplication.isPlaying) throw new Exception("Play required");
            return UdonSharpEditorUtility.GetBackingUdonBehaviour(UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>());
        }
        public static string Wire()
        {
            var s=SceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode || s.path!=LB_FullAssembly.Preview || s.isDirty) throw new Exception("Clean preview required");
            Lanbai.Director.Editor.LanbaiDirectorGen.WireMenu();
            return "Authorized preview wire requested; await readiness before saving";
        }
        public static string SaveWire()
        {
            var s=SceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode || s.path!=LB_FullAssembly.Preview) throw new Exception("Preview edit mode required");
            var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
            if(j.deliveredDispatcher==null || j.deliveredOverlay==null || j.ppWhite.priority!=150f) throw new Exception("Protected bindings missing");
            Undo.FlushUndoRecordObjects();
            Directory.CreateDirectory(Out);
            string snapshot=Out+"/wired_preview.unity";
            if(File.Exists(snapshot)) throw new Exception("Do not overwrite previous snapshot");
            if(!EditorSceneManager.SaveScene(s,snapshot,true)) throw new Exception("Snapshot failed");
            if(!EditorSceneManager.SaveScene(s)) throw new Exception("Save failed");
            return "Saved authorized wire only, with independent preview snapshot";
        }
        public static string ConfigureSpawnDefaults()
        {
            var s=SceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode || s.path!=LB_FullAssembly.Preview || s.isDirty) throw new Exception("Clean preview required");
            var d=UnityEngine.Object.FindObjectOfType<LanbaiActDispatcher>(true);
            string before="timeout="+d.spawnFadeTimeout+" max="+d.spawnFadeMax+" rate="+d.spawnFadeRate;
            Undo.RecordObject(d,"Migrate documented Director v1.3 spawn defaults");
            d.spawnFadeTimeout=25f; d.spawnFadeMax=9.4f; d.spawnFadeRate=0.85f;
            UdonSharpEditorUtility.CopyProxyToUdon(d);
            EditorUtility.SetDirty(d); Undo.FlushUndoRecordObjects();
            if(!EditorSceneManager.SaveScene(s)) throw new Exception("Preview save failed");
            return "Migrated v1.3 defaults from "+before;
        }
        public static string ResetSpawn(string seconds)
        {
            var u=Journey();
            LB_FullAssembly.Seek(seconds);
            u.SetProgramVariable("_deliveredStarted",false);
            u.SetProgramVariable("_sp",0);
            u.SetProgramVariable("_spawnFadeEnded",false);
            return "Runtime spawn re-entry at "+seconds;
        }
        public static string ReturnToStation()
        {
            Journey().SetProgramVariable("departureMs",0);
            return "Runtime timeline returned to stationary platform without resetting spawn state";
        }
        public static string Snapshot(string label)
        {
            var u=Journey(); var sb=new StringBuilder();
            sb.AppendLine("label="+label+" time="+Time.time+" batch="+Application.isBatchMode+" audio="+AudioListener.volume);
            foreach(string key in new[]{"dbgT","dbgSeg","dbgDEV","dbgB","_sp","_spHandAt","_spBlackEnd","_spFade0","_spawnFadeEnded","_journeyReady"})
                sb.AppendLine(key+"="+u.GetProgramVariable(key));
            var d=UdonSharpEditorUtility.GetBackingUdonBehaviour(UnityEngine.Object.FindObjectOfType<LanbaiActDispatcher>());
            foreach(string key in new[]{"lastT","activeCount","gradeDEV","spawnFadeTimeout","spawnFadeMax","_fadeEndT","_fadeEnded","_handState","_fadeBegin"}) sb.AppendLine("dispatcher."+key+"="+d.GetProgramVariable(key));
            sb.AppendLine("overlay="+Shader.GetGlobalVector("_Udon_OverlayColor"));
            Directory.CreateDirectory(Out); File.WriteAllText(Out+"/"+label+".txt",sb.ToString());
            return sb.ToString();
        }
    }
}
#endif
