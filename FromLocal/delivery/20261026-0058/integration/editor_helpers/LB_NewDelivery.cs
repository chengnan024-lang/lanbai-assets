#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEditor;
using UnityEngine.SceneManagement;
using UnityEditor.SceneManagement;
using UdonSharp;

namespace Lanbai.Tests {
 public static class LB_NewDelivery {
  const string Out="E:/IDMdownload/VRCC/Backups/continuation_20261026/delivery_0058";
  static void Guard() {
   if(EditorApplication.isPlayingOrWillChangePlaymode || SceneManager.GetActiveScene().path!=LB_FullAssembly.Preview)
    throw new Exception("Preview edit mode required");
  }
  static void Sync(UdonSharpBehaviour b) { EditorUtility.SetDirty(b); Lanbai.Udon.LanbaiUdonPrograms.CopyProxyToUdon(b); }
  public static string Save(string label) {
   Guard(); if(!System.Text.RegularExpressions.Regex.IsMatch(label,"^[a-z0-9_]+$")) throw new Exception("Invalid snapshot label");
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
   if(j.deliveredDispatcher==null || j.deliveredOverlay==null || j.ppWhite.priority!=150f) throw new Exception("Protected bindings missing");
   string snapshot=Out+"/"+label+".unity"; if(File.Exists(snapshot)) throw new Exception("No snapshot overwrite");
   Undo.FlushUndoRecordObjects(); var s=SceneManager.GetActiveScene();
   if(!EditorSceneManager.SaveScene(s,snapshot,true) || !EditorSceneManager.SaveScene(s)) throw new Exception("Save failed");
   return "Saved authorized preview stage with independent snapshot "+label;
  }
  public static string PreserveDirty() {
   Guard();var s=SceneManager.GetActiveScene();if(!s.isDirty)return "Already clean";
   string path=Out+"/dirty_"+DateTime.Now.ToString("HHmmssfff")+".unity";
   Undo.FlushUndoRecordObjects();if(!EditorSceneManager.SaveScene(s,path,true))throw new Exception("Snapshot failed");
   if(!File.ReadAllBytes(path).SequenceEqual(File.ReadAllBytes(s.path)))return "Preserved differing snapshot; inspect before saving: "+path;
   if(!EditorSceneManager.SaveScene(s))throw new Exception("Identical save failed");
   return "Byte-identical snapshot; cleared deferred dirty: "+path;
  }
  public static string CheckBus() {
   Guard(); string r=LanbaiBusCabinDropIn.Check();
   if(!r.StartsWith("OK")) throw new Exception(r);
   return r;
  }
  public static string BuildBus() {
   Guard(); string r=LanbaiBusCabinDropIn.BuildAll();
   if(!r.StartsWith("OK")) throw new Exception(r);
   return r;
  }
  public static string ConfigureDusk() {
   Guard(); var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
   var d=UnityEngine.Object.FindObjectOfType<LanbaiAct08Driver>(true);
   if(d==null || d.ceilingInner==null || d.ceilingEdge==null || d.cards==null || d.cards.Length==0) throw new Exception("Dusk incomplete");
   d.worldSun=j.sun; d.writeRenderSettings=true; d.writeMainLight=true; Sync(d);
   j.useDeliveredDusk=true; Sync(j);
   var sea=UnityEngine.Object.FindObjectOfType<LanbaiAct07Driver>(true);
   sea.worldSun=j.sun;sea.writeRenderSettings=true;sea.writeMainLight=true;
   int busLayer=LayerMask.NameToLayer("Bus");
   if(sea.beam!=null)sea.beam.cullingMask=1<<busLayer;
   if(sea.roseLights!=null)foreach(var l in sea.roseLights)if(l!=null)l.cullingMask=1<<busLayer;
   Sync(sea); string bus=LanbaiBusCabinDropIn.UseNew();
   if(!bus.StartsWith("OK"))throw new Exception(bus);
   EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
   return "Dusk owns atmosphere/sun and legacy sky/sea/exposure fallback disabled; Act07 wired to new bus. "+bus;
  }
  public static string FixBusGlassImports() {
   Guard(); string dir=Application.dataPath+"/Lanbai/Rain/Textures/Glass";
   string bk=Out+"/before_glass_meta";Directory.CreateDirectory(bk);int count=0;
   foreach(string file in Directory.GetFiles(dir,"*.png")) {
    string path="Assets"+file.Substring(Application.dataPath.Length).Replace('\\','/');
    var ti=AssetImporter.GetAtPath(path) as TextureImporter;
    if(ti==null || (!ti.sRGBTexture && ti.textureType==TextureImporterType.Default))continue;
    string dst=bk+"/"+Path.GetFileName(file)+".meta"; if(File.Exists(dst))throw new Exception("No meta backup overwrite");
    File.Copy(file+".meta",dst);
    ti.textureType=TextureImporterType.Default;ti.sRGBTexture=false;ti.SaveAndReimport();count++;
   }
   return "Corrected "+count+" raw glass data texture imports, originals preserved";
  }
  public static string BindPoems() {
   Guard(); var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
   var p=UnityEngine.Object.FindObjectOfType<LanbaiPoemDriver>(true);
   if(p==null || p.subRig==null || p.pgT==null || p.pgT.Length==0 || p.depthTable.Length!=23*24*9)throw new Exception("v5 subtitle bake incomplete");
   j.deliveredPoems=p;p.busRoot=j.busRoot;p.useLocalAppliedExposure=true;
   var data=JsonUtility.FromJson<SeatNames>(File.ReadAllText("Assets/Lanbai/Fonts/subtitle_depth.json"));int count=0;
   foreach(var seat in j.busRoot.GetComponentsInChildren<Lanbai.LB_Seat>(true)) {
    if(seat.transform.parent.name!="Seats" || !seat.name.StartsWith("Station_"))continue;
    string name=seat.name.Substring(8).Replace("_HERO","");int k=Array.IndexOf(data.seats,name);
    if(k<0)throw new Exception("Unknown v5 seat "+name);
    seat.poemDriver=p;seat.poemSeatIndex=k;Sync(seat);count++;
   }
   if(count!=23)throw new Exception("Expected 23 v5 seats, got "+count);
   // Reserve an unused user-layer number inside this preview only; no ProjectSettings change.
   const int layer=24;
   if(LayerMask.LayerToName(layer)!="" && LayerMask.LayerToName(layer)!="LanbaiSubtitles")throw new Exception("Layer 24 already named");
   foreach(var root in SceneManager.GetActiveScene().GetRootGameObjects())foreach(var t in root.GetComponentsInChildren<Transform>(true))
    if(t.gameObject.layer==layer && !t.IsChildOf(p.subRig) && t!=p.lbQuad)throw new Exception("Layer 24 already occupied");
   foreach(var t in p.subRig.GetComponentsInChildren<Transform>(true))t.gameObject.layer=layer;
   foreach(var c in UnityEngine.Object.FindObjectsOfType<Camera>(true)) {
    if(c.name.IndexOf("reflect",StringComparison.OrdinalIgnoreCase)>=0 || c.name.IndexOf("mirror",StringComparison.OrdinalIgnoreCase)>=0)c.cullingMask &= ~(1<<layer);
    else c.cullingMask |= 1<<layer;
   }
   foreach(var r in UnityEngine.Object.FindObjectsOfType<ReflectionProbe>(true))r.cullingMask &= ~(1<<layer);
   Sync(p);Sync(j);EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
   return "v5 pages="+p.pgT.Length+", depth cells="+p.depthTable.Length+", 23 seats rewired, subtitles on unused preview layer 24";
  }
  [Serializable] public class SeatNames { public string[] seats; }
  public static string ConfigureWhite() {
   Guard(); var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
   var m=UnityEngine.Object.FindObjectOfType<Lanbai.Mirrors.LanbaiMirrorsDriver>(true);
   var w=UnityEngine.Object.FindObjectOfType<Lanbai.Act10.LanbaiWhiteDriver>(true);
   if(m==null || m.mirrors==null || m.mirrors.Length!=13 || w==null || w.overlay==null)throw new Exception("Mirror/white build incomplete");
   j.useDeliveredMirrors=true;j.useDeliveredWhite=true;w.writeRenderSettings=true;Sync(w);Sync(j);
   return "13 mirrors + white wired; legacy mirrors and first-white events disabled; F16 unchanged at 1149.31";
  }
  public static string Capture(string spec) {
   if(!EditorApplication.isPlaying)throw new Exception("Play required");
   var a=spec.Split('|');if(a.Length!=3)throw new Exception("label|yaw|pitch required");
   if(!System.Text.RegularExpressions.Regex.IsMatch(a[0],"^[a-z0-9_]+$"))throw new Exception("Invalid label");
   var ci=System.Globalization.CultureInfo.InvariantCulture;float yaw=float.Parse(a[1],ci),pitch=float.Parse(a[2],ci);
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();
   Directory.CreateDirectory(Out+"/views");string path=Out+"/views/"+a[0]+".png";
   var shot=typeof(LB_DeliveryChecks).GetMethod("Shot",System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.NonPublic);
   shot.Invoke(null,new object[]{path,j.busRoot.TransformPoint(new Vector3(.55f,1.70f,2.05f)),j.busRoot.rotation*Quaternion.Euler(-pitch,yaw,0),58.7155f,1600,900});
   var ju=UdonSharpEditor.UdonSharpEditorUtility.GetBackingUdonBehaviour(j);
   var p=UnityEngine.Object.FindObjectOfType<LanbaiPoemDriver>();
   var pu=UdonSharpEditor.UdonSharpEditorUtility.GetBackingUdonBehaviour(p);
   string text="Timeline="+ju.GetProgramVariable("dbgT")+" actualDEV="+ju.GetProgramVariable("dbgDEV")+" base="+ju.GetProgramVariable("dbgB")+"\n";
   foreach(var n in new[]{"_Udon_OverlayColor","_Udon_OverlayCurve","_Udon_ZenithColor","_Udon_HorizonColor"})text+=n+"="+Shader.GetGlobalVector(n)+"\n";
   text+="seaA="+j.seaA.gameObject.activeSelf+" seaB="+j.seaB.gameObject.activeSelf+" whiteWeight="+j.ppWhite.weight+"\n";
   text+="subtitleSeat="+pu.GetProgramVariable("seat")+" subtitleEV="+pu.GetProgramVariable("localAppliedDeltaEV")+" pages="+p.pgT.Length+"\n";
   File.WriteAllText(Out+"/views/"+a[0]+".txt",text);return path;
  }
  public static string SitHero() {
   if(!EditorApplication.isPlaying)throw new Exception("Play required");
   var seat=UnityEngine.Object.FindObjectsOfType<Lanbai.LB_Seat>().Single(s=>s.name=="Station_SeatR0_HERO");
   UdonSharpEditor.UdonSharpEditorUtility.GetBackingUdonBehaviour(seat).Interact();
   return "Invoked actual local hero-seat interaction";
  }
  public static string Depart() {
   if(!EditorApplication.isPlaying)throw new Exception("Play required");
   var button=UnityEngine.Object.FindObjectOfType<Lanbai.LB_DepartButton>();
   UdonSharpEditor.UdonSharpEditorUtility.GetBackingUdonBehaviour(button).Interact();
   return "Invoked actual active departure-button interaction";
  }
  public static string FixImportedBusLod() {
   Guard(); var model=UnityEngine.Object.FindObjectsOfType<Transform>(true).Single(t=>t.name=="Model_PAZ672");
   int count=0;foreach(var lod in model.GetComponents<LODGroup>()){UnityEngine.Object.DestroyImmediate(lod);count++;}
   var seen=new System.Collections.Generic.HashSet<Renderer>();
   foreach(var lod in model.parent.GetComponentsInChildren<LODGroup>(true))foreach(var level in lod.GetLODs())foreach(var r in level.renderers)
    if(r!=null && !seen.Add(r))throw new Exception("Renderer still belongs to duplicate LOD levels/groups: "+r.name);
   EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
   return "Removed "+count+" imported aggregate bus LODGroup; explicit exterior/seat groups retained; no duplicate renderer ownership";
  }
  public static string ConfigureInside() {
   Guard();var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
   var d=UnityEngine.Object.FindObjectOfType<LanbaiInsideDriver>(true);
   if(d==null || j.deliveredOverlay==null || j.sun==null)throw new Exception("Inside dependencies missing");
   d.overlay=j.deliveredOverlay;d.worldMainLight=j.sun;d.writeRenderSettings=true;d.writeMainLight=true;d.writeExposure=false;Sync(d);
   j.useDeliveredInside=true;j.useDeliveredGate=true;Sync(j);
   return "Inside light/atmosphere and overlay rebound; single PPv2 exposure writer retained";
  }
  public static string BakeGateDimensions() {
   Guard();var container=UnityEngine.Object.FindObjectsOfType<Transform>(true).Single(t=>t.name=="DeliveredGate");
   var children=new[]{"GateRoot","NearRoot_bus","Gate_Lights"}.Select(n=>container.Find(n)).ToArray();
   if(children.Any(t=>t==null))throw new Exception("Delivered gate structure incomplete");
   foreach(var t in children)t.SetParent(null,true);
   LanbaiGateDriver d=null;
   try {
    string r=LB_GateTest.Apply("155.1");if(r.StartsWith("ERROR"))throw new Exception(r);
    d=LanbaiGateDriverBuilder.Build(false);
   } finally { foreach(var t in children)if(t!=null)t.SetParent(container,true); }
   if(d==null || d.rHasDims.Count(x=>x)<108)throw new Exception("Gate multitude dimension bake incomplete");
   EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
   return "Gate dimensions baked for "+d.rHasDims.Count(x=>x)+" renderers, original DeliveredGate hierarchy retained";
  }
 }
}
#endif
