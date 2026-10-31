#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEditor.SceneManagement;
namespace Lanbai.Tests {
 public static class LB_ApprovedTests {
  const string Root="E:/IDMdownload/VRCC/Backups/continuation_20261026/delivery_0058";
  [Serializable] class Completion { public int exit; public string output,finished; }
  public static string Run(string name) {
   var scene=SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=LB_FullAssembly.Preview||scene.isDirty)throw new Exception("Clean FullPreview required");
   string path=Root+"/"+name+".json";
   if(!File.Exists(path))throw new Exception("Prepared test variant missing");
   string id=name.StartsWith("bus_")?"bus_slice":name.StartsWith("gate_")?"gate_clouds_test":(name.StartsWith("transitions")?"transitions_sweep":"flicker_probe");
   LB_WhiteHandoffAudit.QuietNextPlay();
   Lanbai.Test.Runner.Start(id,path,false,"bridge",(code,dir)=>File.WriteAllText(Root+"/"+name+"_completion.json",JsonUtility.ToJson(new Completion{exit=code,output=dir,finished=DateTimeOffset.Now.ToString("o")},true)));
   return "Started authorized test "+id+" using prepared variant "+name+"; completion determines outcome";
  }
  public static string RestorePreview() {
   var scene=SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||!scene.path.StartsWith("Assets/_LanbaiTest/"))throw new Exception("Only own stopped test sandbox may be closed");
   string path=Root+"/sandbox_"+DateTime.Now.ToString("HHmmssfff")+".unity";
   if(File.Exists(path)||!EditorSceneManager.SaveScene(scene,path,true))throw new Exception("Sandbox preservation failed");
   EditorSceneManager.OpenScene(LB_FullAssembly.Preview,OpenSceneMode.Single);
   return "Preserved own sandbox; restored saved FullPreview";
  }
  public static string RunOfficial(string id) {
   var scene=SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=LB_FullAssembly.Preview||scene.isDirty)throw new Exception("Clean FullPreview required");
   if(Array.IndexOf(new[]{"gate_clouds_test","tree_sample","flicker_probe","transitions_sweep","bus_slice","bus_dropin"},id)<0)throw new Exception("Test outside approved scope");
   string path="Assets/Lanbai/Engineering/UnityTest/tests/"+id+".json";
   if(!File.Exists(path))throw new Exception("Official definition missing");
   LB_WhiteHandoffAudit.QuietNextPlay();
   Lanbai.Test.Runner.Start(id,path,false,"bridge",(code,dir)=>File.WriteAllText(Root+"/"+id+"_official_completion.json",JsonUtility.ToJson(new Completion{exit=code,output=dir,finished=DateTimeOffset.Now.ToString("o")},true)));
   return "Started approved official "+id+"; inspect terminal result, not this acknowledgement";
  }
 }
}
#endif
