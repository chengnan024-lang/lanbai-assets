#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering;
using UdonSharpEditor;
using UnityEngine.Rendering.PostProcessing;
namespace Lanbai.Tests {
 public static class LB_FinalDeliveryChecks {
  const string Out="E:/IDMdownload/VRCC/Backups/continuation_20261026/delivery_0058";
  public static string FinalAudit(){
   var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
   if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=LB_FullAssembly.Preview||scene.isDirty)throw new Exception("Clean FullPreview required");
   ColorGrading cg;j.ppWhite.sharedProfile.TryGetSettings(out cg);
   string s="scene="+scene.path+" dirty="+scene.isDirty+" playing="+EditorApplication.isPlaying+" audio="+AudioListener.volume+" compileFailed="+EditorUtility.scriptCompilationFailed+"\nwhitePriority="+j.ppWhite.priority+" profile="+AssetDatabase.GetAssetPath(j.ppWhite.sharedProfile)+" tonemapperOverride="+cg.tonemapper.overrideState+"\n";
   foreach(var f in j.GetType().GetFields().Where(f=>f.Name.StartsWith("useDelivered")))s+=f.Name+"="+f.GetValue(j)+"\n";
   foreach(var c in UnityEngine.Object.FindObjectsOfType<Component>(true).Where(c=>c!=null && (c.GetType().Name=="LanbaiGateDriver"||c.GetType().Name=="LanbaiGateClouds"))){
    foreach(var f in c.GetType().GetFields().Where(f=>f.FieldType.IsArray && typeof(UnityEngine.Object).IsAssignableFrom(f.FieldType.GetElementType()))){var a=f.GetValue(c) as Array;s+=c.GetType().Name+"."+f.Name+" count="+(a==null?-1:a.Length)+" null="+(a==null?-1:a.Cast<UnityEngine.Object>().Count(x=>x==null))+"\n";}
   }
   s+=LB_NewDelivery.CheckBus()+"\n"+LB_FullAssembly.CheckAllPrograms();File.WriteAllText(Out+"/final_editor_audit.txt",s);return s;
  }
  public static string WhiteState(string label){
   if(!EditorApplication.isPlaying)throw new Exception("Own Play required");var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();var u=UdonSharpEditorUtility.GetBackingUdonBehaviour(j);ColorGrading cg;j.ppWhite.profile.TryGetSettings(out cg);
   string s="t="+u.GetProgramVariable("dbgT")+" dEV="+u.GetProgramVariable("dbgDEV")+" white="+j.ppWhite.weight+" whiteTonemapper="+cg.tonemapper.value+" override="+cg.tonemapper.overrideState+"\n";
   Directory.CreateDirectory(Out+"/white_tail");File.WriteAllText(Out+"/white_tail/"+label+".txt",s);LB_CurrentViews.D28(label+"|0|0");return s;
  }
  public static string WhiteTonemapTrial(){
   if(!EditorApplication.isPlaying)throw new Exception("Runtime-only trial");var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();ColorGrading cg;j.ppWhite.profile.TryGetSettings(out cg);cg.tonemapper.overrideState=false;return "Runtime instance only: white now inherits underlying tonemapper";
  }
  public static string ApplyPreviewWhiteTonemap(){
   var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=LB_FullAssembly.Preview||scene.isDirty)throw new Exception("Clean FullPreview required");
   const string path="Assets/Lanbai/Generated/PostProcess/LB_PP_White_FullPreview.asset";
   if(File.Exists(path))throw new Exception("No profile overwrite");
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();var original=j.ppWhite.sharedProfile;
   var profile=ScriptableObject.CreateInstance<PostProcessProfile>();profile.name="LB_PP_White_FullPreview";AssetDatabase.CreateAsset(profile,path);
   foreach(var setting in original.settings){var copy=UnityEngine.Object.Instantiate(setting);copy.name=setting.name;profile.settings.Add(copy);AssetDatabase.AddObjectToAsset(copy,profile);}
   ColorGrading cg;if(!profile.TryGetSettings(out cg))throw new Exception("White grade missing");cg.tonemapper.overrideState=false;
   foreach(var setting in profile.settings){EditorUtility.SetDirty(setting);AssetDatabase.SaveAssetIfDirty(setting);}EditorUtility.SetDirty(profile);AssetDatabase.SaveAssetIfDirty(profile);
   j.ppWhite.sharedProfile=profile;EditorUtility.SetDirty(j.ppWhite);EditorSceneManager.MarkSceneDirty(scene);
   return "Preview-only profile inherits underlying tone mapping; original white profile unchanged, priority="+j.ppWhite.priority;
  }
  public static string BakeCabinCube(){
   var main=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||main.path!=LB_FullAssembly.Preview||main.isDirty)throw new Exception("Clean FullPreview edit mode required");
   const string path="Assets/Lanbai/Bus/Generated/Local_CabinTubeCube_20261026_hdr.asset";
   if(File.Exists(path))throw new Exception("No cube overwrite");
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();
   var model=j.busRoot.GetComponentsInChildren<Transform>(true).Single(x=>x.name=="Model_PAZ672");
   var all=model.GetComponentsInChildren<MeshRenderer>(true);var excluded=new HashSet<Renderer>();var lod0=new HashSet<Renderer>();
   foreach(var group in j.busRoot.GetComponentsInChildren<LODGroup>(true)){
    var ls=group.GetLODs();if(ls.Length>0)foreach(var r in ls[0].renderers)lod0.Add(r);
    foreach(var l in ls.Skip(1))foreach(var r in l.renderers)excluded.Add(r);
   }
   var src=all.Where(r=>!r.name.StartsWith("Glass_")&&(!excluded.Contains(r)||lod0.Contains(r))).ToArray();
   var preview=EditorSceneManager.NewPreviewScene();var objs=new List<GameObject>();var mats=new Dictionary<Material,Material>();
   var globals=new[]{"_Udon_CabinAmbient","_Udon_CabinBleach","_Udon_CabinFade","_Udon_CabinSlice","_Udon_CabinSliceColor","_Udon_MirrorPlane","_Udon_MirrorRimLight","_Udon_RadioDial"};
   var prev=globals.Select(Shader.GetGlobalVector).ToArray();float lm=Shader.GetGlobalFloat("_Udon_CabinLightmap");Cubemap cube=null;bool saved=false;
   try {
    for(int i=0;i<globals.Length;i++)Shader.SetGlobalVector(globals[i],Vector4.zero);
    Shader.SetGlobalFloat("_Udon_CabinLightmap",1f);
    foreach(var r in src){
     var mf=r.GetComponent<MeshFilter>();if(mf==null||mf.sharedMesh==null)continue;
     var go=new GameObject(r.name);objs.Add(go);UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(go,preview);
     go.transform.position=j.busRoot.InverseTransformPoint(r.transform.position);go.transform.rotation=Quaternion.Inverse(j.busRoot.rotation)*r.transform.rotation;go.transform.localScale=r.transform.lossyScale;
     go.AddComponent<MeshFilter>().sharedMesh=mf.sharedMesh;var rr=go.AddComponent<MeshRenderer>();rr.shadowCastingMode=ShadowCastingMode.Off;rr.lightProbeUsage=LightProbeUsage.Off;rr.reflectionProbeUsage=ReflectionProbeUsage.Off;
     rr.sharedMaterials=r.sharedMaterials.Select(m=>{if(!mats.ContainsKey(m)){var n=new Material(m);if(n.HasProperty("_EmitMode") && n.GetFloat("_EmitMode")!=1)n.SetFloat("_EmitMode",0);mats[m]=n;}return mats[m];}).ToArray();
    }
    var cgo=new GameObject("TubeCubeCamera");objs.Add(cgo);UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(cgo,preview);var cam=cgo.AddComponent<Camera>();cam.scene=preview;cam.enabled=false;cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=Color.black;cam.nearClipPlane=.02f;cam.farClipPlane=20;cam.allowHDR=true;cam.allowMSAA=false;cam.transform.position=new Vector3(.55f,1.70f,2.05f);cam.transform.rotation=Quaternion.identity;
    cube=new Cubemap(256,TextureFormat.RGBAHalf,true){name="Local_CabinTubeCube_20261026_hdr",wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Trilinear};
    var target=new RenderTexture(256,256,24,RenderTextureFormat.ARGBHalf,RenderTextureReadWrite.Linear){dimension=TextureDimension.Cube,useMipMap=false};target.Create();var previous=RenderTexture.active;
    try {
     if(!cam.RenderToCubemap(target,63))throw new Exception("HDR cubemap render failed");
     for(int face=0;face<6;face++){Graphics.SetRenderTarget(target,0,(CubemapFace)face);var read=new Texture2D(256,256,TextureFormat.RGBAHalf,false,true);read.ReadPixels(new Rect(0,0,256,256),0,0);read.Apply(false,false);cube.SetPixels(read.GetPixels(),(CubemapFace)face);UnityEngine.Object.DestroyImmediate(read);}
     cube.Apply(true,false);
    } finally {RenderTexture.active=previous;target.Release();UnityEngine.Object.DestroyImmediate(target);}
    string dir=Out+"/cabin_cube_hdr";Directory.CreateDirectory(dir);string report="256 RGBAHalf cube; hero (.55,1.70,2.05); isolated preview scene; LOD0 bus meshes; no glass, world, PP or scene lights; tube lightmap=1; other emission disabled; display PNG clamps linear HDR.\nmeshRenderers="+src.Length+"\n";
    foreach(CubemapFace face in new[]{CubemapFace.PositiveX,CubemapFace.NegativeX,CubemapFace.PositiveY,CubemapFace.NegativeY,CubemapFace.PositiveZ,CubemapFace.NegativeZ}){
     var pixels=cube.GetPixels(face);report+=face+" max="+pixels.Max(x=>Mathf.Max(x.r,Mathf.Max(x.g,x.b)))+" mean="+pixels.Average(x=>(double)(x.r+x.g+x.b)/3)+"\n";
     var tex=new Texture2D(256,256,TextureFormat.RGBA32,false,true);tex.SetPixels(pixels);tex.Apply();File.WriteAllBytes(dir+"/"+face+".png",tex.EncodeToPNG());UnityEngine.Object.DestroyImmediate(tex);
    }
    AssetDatabase.CreateAsset(cube,path);AssetDatabase.SaveAssetIfDirty(cube);saved=true;
    foreach(var name in new[]{"Side","Skylight","Windscreen"}){var m=AssetDatabase.LoadAssetAtPath<Material>("Assets/Lanbai/Bus/Generated/Materials/M_Bus_Glass_"+name+".mat");if(m==null||(m.GetTexture("_CabinCube")!=null && AssetDatabase.GetAssetPath(m.GetTexture("_CabinCube"))!="Assets/Lanbai/Bus/Generated/Local_CabinTubeCube_20261026.asset"))throw new Exception("Missing or preassigned glass material "+name);m.SetTexture("_CabinCube",cube);EditorUtility.SetDirty(m);AssetDatabase.SaveAssetIfDirty(m);report+="bound "+m.name+"\n";}
    File.WriteAllText(dir+"/method.txt",report);return report;
   } finally {
    Shader.SetGlobalFloat("_Udon_CabinLightmap",lm);for(int i=0;i<globals.Length;i++)Shader.SetGlobalVector(globals[i],prev[i]);
    foreach(var go in objs)if(go!=null)UnityEngine.Object.DestroyImmediate(go);foreach(var m in mats.Values)UnityEngine.Object.DestroyImmediate(m);EditorSceneManager.ClosePreviewScene(preview);if(cube!=null&&!saved)UnityEngine.Object.DestroyImmediate(cube);
   }
  }
  public static string SkyState(string label){
   if(!EditorApplication.isPlaying)throw new Exception("Own Play required");
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();var ju=UdonSharpEditorUtility.GetBackingUdonBehaviour(j);
   string s="t="+ju.GetProgramVariable("dbgT")+"\n";
   foreach(var sky in UnityEngine.Object.FindObjectsOfType<Lanbai.Sky.LanbaiSkyDriver>(true)){var u=UdonSharpEditorUtility.GetBackingUdonBehaviour(sky);s+=sky.name+" lastIndex="+u.GetProgramVariable("lastIndex")+" fade="+u.GetProgramVariable("lastWasFade")+" active="+sky.gameObject.activeInHierarchy+"\n";}
   foreach(var n in new[]{"_Udon_SkyBlend","_Udon_Sky_NightColor","_Udon_Sky_NightMaskDir","_Udon_Sky_NightMaskShape"})s+=n+"="+Shader.GetGlobalVector(n).ToString("F6")+"\n";
   s+="fog="+RenderSettings.fogColor+" density="+RenderSettings.fogDensity+" skybox="+RenderSettings.skybox;
   Directory.CreateDirectory(Out+"/sky");File.WriteAllText(Out+"/sky/"+label+".txt",s);return s;
  }
 }
}
#endif
