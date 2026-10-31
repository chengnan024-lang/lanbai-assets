#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
namespace Lanbai.Tests {
 [InitializeOnLoad] public static class LB_DiagnosticMaterials {
  const string Key="Lanbai.DiagnosticMaterials.Snapshot";
  const string Armed="Lanbai.DiagnosticMaterials.Armed";
  [Serializable] public class Item { public string path,json,hash; public bool dirty; }
  [Serializable] public class State { public Item[] items; }
  static string Hash(string p){using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(p))).Replace("-","");}
  static LB_DiagnosticMaterials(){EditorApplication.playModeStateChanged+=Changed;}
  public static void Arm(){if(EditorApplication.isPlaying)throw new Exception("Arm before diagnostic Play");SessionState.SetBool(Armed,true);}
  static void Changed(PlayModeStateChange mode){
   if(mode==PlayModeStateChange.ExitingEditMode && SessionState.GetBool(Armed,false)){
    var paths=AssetDatabase.FindAssets("t:Material",new[]{"Assets/Lanbai/Act04c_Inside/Materials","Assets/Lanbai/Generated/Materials"}).Select(AssetDatabase.GUIDToAssetPath).Distinct();
    var state=new State{items=paths.Select(p=>{var m=AssetDatabase.LoadAssetAtPath<Material>(p);return new Item{path=p,json=EditorJsonUtility.ToJson(m),hash=Hash(p),dirty=EditorUtility.IsDirty(m)};}).ToArray()};
    string file="E:/IDMdownload/VRCC/Backups/continuation_20261026/delivery_0058/material_guard_"+DateTime.Now.ToString("HHmmssfff")+".json";
    File.WriteAllText(file,JsonUtility.ToJson(state,true));SessionState.SetString(Key,file);SessionState.SetBool(Armed,false);
   }
   if(mode==PlayModeStateChange.EnteredEditMode){
    string file=SessionState.GetString(Key,"");if(file=="")return;
    var state=JsonUtility.FromJson<State>(File.ReadAllText(file));int restored=0;string report="";
    foreach(var row in state.items){
     if(!File.Exists(row.path)||Hash(row.path)!=row.hash){report+="DISK CHANGED, not restored: "+row.path+"\n";continue;}
     var m=AssetDatabase.LoadAssetAtPath<Material>(row.path);
     if(EditorJsonUtility.ToJson(m)!=row.json){EditorJsonUtility.FromJsonOverwrite(row.json,m);if(row.dirty)EditorUtility.SetDirty(m);else EditorUtility.ClearDirty(m);restored++;}
    }
    File.WriteAllText(file+".result.txt","Restored in-memory diagnostic material state="+restored+"; no asset files written\n"+report);
    SessionState.EraseString(Key);
    if(report!="")Debug.LogError("[Lanbai DiagnosticMaterials] "+report);
   }
  }
 }
}
#endif
