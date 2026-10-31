#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEditor;
using VRC.SDK3.Rendering;
using UdonSharpEditor;
namespace Lanbai.Tests {
 public static class LB_CurrentViews {
  const string Out="E:/IDMdownload/VRCC/Backups/continuation_20261026/delivery_0058/views";
  static LanbaiPoemDriver Poems(){if(!EditorApplication.isPlaying)throw new Exception("Own diagnostic Play required");return UnityEngine.Object.FindObjectOfType<LanbaiPoemDriver>();}
  public static string BusAxes(){
   if(EditorApplication.isPlayingOrWillChangePlaymode)throw new Exception("Edit mode audit only");
   var asset=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Lanbai/Bus/Models/Bus.fbx");
   var model=UnityEngine.Object.FindObjectsOfType<Transform>(true).Single(x=>x.name=="Model_PAZ672");
   string text="FBX root position="+asset.transform.localPosition+" rotation="+asset.transform.localEulerAngles+" scale="+asset.transform.localScale+"\nscene model position="+model.localPosition+" rotation="+model.localEulerAngles+" scale="+model.localScale+"\n";
   foreach(string name in new[]{"Seat_SeatR0","Window_R1","Pole_R0","Bus_Door0","Station_SeatR0_HERO"}){
    var t=model.parent.GetComponentsInChildren<Transform>(true).FirstOrDefault(x=>x.name==name);
    if(t==null){text+=name+" missing\n";continue;}
    text+=name+" world="+t.position+" rotation="+t.eulerAngles;
    var r=t.GetComponent<Renderer>();if(r!=null)text+=" bounds="+r.bounds.min.ToString("F4")+" .. "+r.bounds.max.ToString("F4");text+="\n";
   }
   Directory.CreateDirectory(Out);File.WriteAllText(Out+"/bus_axes_"+DateTime.Now.ToString("HHmmss")+".txt",text);return text;
  }
  public static string FixLetterboxLayer(){
   var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=LB_FullAssembly.Preview||scene.isDirty)throw new Exception("Clean FullPreview required");
   var p=UnityEngine.Object.FindObjectOfType<LanbaiPoemDriver>(true);if(p.lbQuad==null||p.subRig.gameObject.layer!=24)throw new Exception("Subtitle layer setup missing");
   p.lbQuad.gameObject.layer=24;EditorUtility.SetDirty(p.lbQuad.gameObject);UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
   return "Desktop letterbox shares subtitle-only layer 24; reflection probes already exclude it";
  }
  public static string ExitHero(){
   Poems();var lp=VRC.SDKBase.Networking.LocalPlayer;
   var hero=UnityEngine.Object.FindObjectsOfType<VRC.SDK3.Components.VRCStation>().Single(x=>x.name=="Station_SeatR0_HERO");
   hero.ExitStation(lp);return "Exited own test seat before Play teardown";
  }
  public static string D28(string spec){
   Poems();var a=spec.Split('|');var ci=System.Globalization.CultureInfo.InvariantCulture;float yaw=float.Parse(a[1],ci),pitch=float.Parse(a[2],ci);
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();Directory.CreateDirectory(Out);
   var shot=typeof(LB_DeliveryChecks).GetMethod("Shot",BindingFlags.Static|BindingFlags.NonPublic);
   shot.Invoke(null,new object[]{Out+"/"+a[0]+".png",j.busRoot.TransformPoint(new Vector3(.55f,1.70f,2.05f)),j.busRoot.rotation*Quaternion.Euler(-pitch,yaw,0),58.7155f,960,540});
   var u=UdonSharpEditorUtility.GetBackingUdonBehaviour(j);
   string text="Fixed D28 eye (.55,1.70,2.05), 960x540 HDR PPv2 MSAA4; yaw="+yaw+" pitch="+pitch+" timeline="+u.GetProgramVariable("dbgT")+" actualDEV="+u.GetProgramVariable("dbgDEV");
   File.WriteAllText(Out+"/"+a[0]+".txt",text);return text;
  }
  public static string Language(string language){
   string ev=language=="zh"?"_LangZhs":language=="en"?"_LangEn":null;
   if(ev==null)throw new Exception("Unsupported diagnostic language");
   var u=UdonSharpEditorUtility.GetBackingUdonBehaviour(Poems());u.SendCustomEvent(ev);u.SendCustomEvent("_SubFollow");return "Runtime language "+language;
  }
  public static string Look(string spec){
   var a=spec.Split('|');var ci=System.Globalization.CultureInfo.InvariantCulture;float yaw=float.Parse(a[0],ci),pitch=float.Parse(a[1],ci);
   var cam=VRCCameraSettings.ScreenCamera;if(cam==null)throw new Exception("ScreenCamera unavailable");
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();
   var t=AppDomain.CurrentDomain.GetAssemblies().Select(x=>x.GetType("VRC.SDK3.ClientSim.ClientSimDesktopTrackingProvider")).FirstOrDefault(x=>x!=null);
   if(t==null)throw new Exception("Desktop tracking provider unavailable");
   var obj=Resources.FindObjectsOfTypeAll(t).Cast<Component>().Single(x=>x.gameObject.scene.IsValid() && x.gameObject.activeInHierarchy);
   t.GetMethod("LookTowardsPoint").Invoke(obj,new object[]{cam.Position+j.busRoot.rotation*Quaternion.Euler(-pitch,yaw,0)*Vector3.forward*100f});
   return "Simulated desktop view yaw="+yaw+" pitch="+pitch+" via simulator test API";
  }
  public static string BindHaloTexture(){
   var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=LB_FullAssembly.Preview||scene.isDirty)throw new Exception("Clean FullPreview required");
   var p=UnityEngine.Object.FindObjectOfType<LanbaiPoemDriver>(true);var a=p.haloTop as SpriteRenderer;var b=p.haloBot as SpriteRenderer;
   if(a.sprite.texture!=b.sprite.texture||a.sharedMaterial!=b.sharedMaterial)throw new Exception("Unexpected halo material setup");
   var mat=a.sharedMaterial;if(AssetDatabase.GetAssetPath(mat)!="Assets/Lanbai/Fonts/FontAssets/SubtitleMaterials/Lanbai_SubtitleHalo.mat")throw new Exception("Not dedicated subtitle material");
   mat.SetTexture("_MainTex",a.sprite.texture);EditorUtility.SetDirty(mat);AssetDatabase.SaveAssetIfDirty(mat);return "Saved dedicated halo alpha texture; runtime colour MPB unchanged";
  }
  public static string RestoreGateTest(){
   var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!="Assets/Lanbai/Tests/GateTest.unity")throw new Exception("Only own stopped GateTest may be preserved");
   var path="E:/IDMdownload/VRCC/Backups/continuation_20261026/delivery_0058/gate_test_"+DateTime.Now.ToString("HHmmssfff")+".unity";
   if(!UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene,path,true))throw new Exception("GateTest snapshot failed");
   UnityEditor.SceneManagement.EditorSceneManager.OpenScene(LB_FullAssembly.Preview);return "Preserved GateTest; restored saved FullPreview";
  }
  public static string HaloTextureCheck(){
   var p=Poems();Desktop("halo_before_explicit_texture");string text="";
   foreach(var r in new[]{p.haloTop,p.haloBot}){
    var sr=r as SpriteRenderer;var block=new MaterialPropertyBlock();r.GetPropertyBlock(block);
    text+=r.name+" active="+r.enabled+" blockTexture="+block.GetTexture("_MainTex")+" materialTexture="+r.sharedMaterial.GetTexture("_MainTex")+" spriteTexture="+sr.sprite.texture+"\n";
    block.SetTexture("_MainTex",sr.sprite.texture);r.SetPropertyBlock(block);
   }
   Desktop("halo_after_explicit_texture");File.WriteAllText(Out+"/halo_texture_check.txt",text);return text;
  }
  public static string Desktop(string label){
   var p=Poems();var cam=VRCCameraSettings.ScreenCamera;if(cam==null)throw new Exception("ScreenCamera unavailable");
   if(!System.Text.RegularExpressions.Regex.IsMatch(label,"^[a-z0-9_]+$"))throw new Exception("Invalid label");
   float aspect=cam.PixelHeight>0?(float)cam.PixelWidth/cam.PixelHeight:16f/9f;
   int h=900,w=Mathf.RoundToInt(h*aspect);Directory.CreateDirectory(Out);string path=Out+"/"+label+".png";
   var shot=typeof(LB_DeliveryChecks).GetMethod("Shot",BindingFlags.Static|BindingFlags.NonPublic);
   shot.Invoke(null,new object[]{path,cam.Position,cam.Rotation,cam.FieldOfView,w,h});
   var u=UdonSharpEditorUtility.GetBackingUdonBehaviour(p);var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();var ju=UdonSharpEditorUtility.GetBackingUdonBehaviour(j);
   string text="Desktop ScreenCamera position="+cam.Position+" rotation="+cam.Rotation+" fov="+cam.FieldOfView+" native="+cam.PixelWidth+"x"+cam.PixelHeight+" capture="+w+"x"+h+"\nTimeline="+ju.GetProgramVariable("dbgT")+" actualDEV="+ju.GetProgramVariable("dbgDEV")+" audio="+AudioListener.volume+"\n";
   foreach(string k in new[]{"key","seat","_vr","_pg","_sCur","_aTop","_aBot","_lbE","_lbBar","localAppliedDeltaEV"})text+=k+"="+u.GetProgramVariable(k)+"\n";
   text+="letterboxActive="+(p.lbQuad!=null&&p.lbQuad.gameObject.activeSelf)+" subtitleLayer="+p.subRig.gameObject.layer+"\n";
   File.WriteAllText(Out+"/"+label+".txt",text);return text;
  }
 }
}
#endif
