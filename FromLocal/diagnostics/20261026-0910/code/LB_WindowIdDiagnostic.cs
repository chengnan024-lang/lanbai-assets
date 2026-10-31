#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.Rendering.PostProcessing;
using Object=UnityEngine.Object;
namespace Lanbai.Tests {
public static class LB_WindowIdDiagnostic {
 const string Base="E:/IDMdownload/VRCC/Backups/continuation_20261026/window_id_0910";
 static GameObject Make(string name,Scene scene){var g=new GameObject(name){hideFlags=HideFlags.HideAndDontSave};SceneManager.MoveGameObjectToScene(g,scene);return g;}
 static Dictionary<string,object> D(params object[] pairs){var d=new Dictionary<string,object>();for(int i=0;i<pairs.Length;i+=2)d[(string)pairs[i]]=pairs[i+1];return d;}
 static object V(Vector3 v){return new[]{v.x,v.y,v.z};}
 static double L(Color32 c){return .2126*c.r+.7152*c.g+.0722*c.b;}
 static void Save(Color32[] px,int w,int h,string path){var t=new Texture2D(w,h,TextureFormat.RGB24,false,true);try{t.SetPixels32(px);t.Apply();File.WriteAllBytes(path,t.EncodeToPNG());}finally{Object.DestroyImmediate(t);}}
 static Color32[] Shot(Camera c,PostProcessLayer pp,int ss,bool id){
  int w=834,h=614;var prev=RenderTexture.active;RenderTexture big=null,small=null;Texture2D tex=null;
  try {pp.enabled=!id;c.allowHDR=!id;c.allowMSAA=false;big=new RenderTexture(w*ss,h*ss,24,id?RenderTextureFormat.ARGB32:RenderTextureFormat.ARGBHalf,RenderTextureReadWrite.Linear){antiAliasing=1,filterMode=FilterMode.Bilinear};big.Create();small=new RenderTexture(w,h,0,RenderTextureFormat.ARGB32,id?RenderTextureReadWrite.Linear:RenderTextureReadWrite.sRGB);small.Create();c.targetTexture=big;for(int i=0;i<(id?1:3);i++)c.Render();
   if(id&&ss>2){RenderTexture.active=big;tex=new Texture2D(w*ss,h*ss,TextureFormat.RGB24,false,true);tex.ReadPixels(new Rect(0,0,w*ss,h*ss),0,0);tex.Apply();var high=tex.GetPixels32();var avg=new Color32[w*h];for(int y=0;y<h;y++)for(int x=0;x<w;x++){int total=0;for(int dy=0;dy<ss;dy++)for(int dx=0;dx<ss;dx++)total+=high[(y*ss+dy)*w*ss+x*ss+dx].r;byte v=(byte)Math.Round(total/(double)(ss*ss));avg[y*w+x]=new Color32(v,v,v,255);}return avg;}
   Graphics.Blit(big,small);RenderTexture.active=small;tex=new Texture2D(w,h,TextureFormat.RGB24,false,id);tex.ReadPixels(new Rect(0,0,w,h),0,0);tex.Apply();return tex.GetPixels32();}
  finally{c.targetTexture=null;RenderTexture.active=prev;if(tex!=null)Object.DestroyImmediate(tex);if(big!=null){big.Release();Object.DestroyImmediate(big);}if(small!=null){small.Release();Object.DestroyImmediate(small);}}
 }
 public static string Run(string label){return RunCore(label,2,true);}
 public static string Convergence(string label){return RunCore(label,8,false);}
 static string RunCore(string label,int idSS,bool beauty){
  var active=SceneManager.GetActiveScene();if(EditorApplication.isPlayingOrWillChangePlaymode||active.isDirty||active.path!=LB_FullAssembly.Preview)throw new Exception("Clean stopped FullPreview required");
  if(label.Any(x=>!char.IsLetterOrDigit(x)&&x!='_'))throw new Exception("Simple label only");string output=Base+"/"+label;if(Directory.Exists(output))throw new Exception("No overwrite/replay");Directory.CreateDirectory(output);
  var root=Object.FindObjectsOfType<Transform>(true).Single(x=>x.name=="Model_PAZ672");var bus=Object.FindObjectOfType<Lanbai.LB_Journey>(true).busRoot;
  string[] names={"Seat_SeatR0","Window_R1","Glass_WinR1","Pole_R0"};var sources=names.Select(n=>root.GetComponentsInChildren<MeshRenderer>(true).Single(x=>x.name==n)).ToArray();
  var rows=new List<object>();var shots=new List<object>();var owned=new List<Object>();Scene sc=default(Scene);
  string[] globals={"_Udon_CabinAmbient","_Udon_CabinBleach","_Udon_CabinFade","_Udon_CabinSlice","_Udon_CabinSliceColor"};var old=globals.Select(Shader.GetGlobalVector).ToArray();float oldLM=Shader.GetGlobalFloat("_Udon_CabinLightmap");
  try {
   sc=EditorSceneManager.NewPreviewScene();var clones=new List<MeshRenderer>();var mats=new List<Material[]>();
   foreach(var s in sources){
    var g=Make(s.name,sc);g.transform.position=bus.InverseTransformPoint(s.transform.position);g.transform.rotation=Quaternion.Inverse(bus.rotation)*s.transform.rotation;
    var z=s.transform.lossyScale;var b=bus.lossyScale;g.transform.localScale=new Vector3(z.x/b.x,z.y/b.y,z.z/b.z);
    var mf=g.AddComponent<MeshFilter>();mf.sharedMesh=s.GetComponent<MeshFilter>().sharedMesh;var r=g.AddComponent<MeshRenderer>();
    r.sharedMaterials=s.sharedMaterials.Select(m=>{var v=new Material(m){hideFlags=HideFlags.HideAndDontSave};owned.Add(v);return v;}).ToArray();r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;r.receiveShadows=false;
    clones.Add(r);mats.Add(r.sharedMaterials);
    rows.Add(D("name",s.name,"mesh",AssetDatabase.GetAssetPath(mf.sharedMesh),"mesh_name",mf.sharedMesh.name,"vertices",mf.sharedMesh.vertexCount,"submeshes",mf.sharedMesh.subMeshCount,"materials",s.sharedMaterials.Select(AssetDatabase.GetAssetPath).ToArray(),"position",V(g.transform.position),"euler",V(g.transform.eulerAngles),"scale",V(g.transform.localScale),"bounds_min",V(r.bounds.min),"bounds_max",V(r.bounds.max)));
   }
   Shader.SetGlobalFloat("_Udon_CabinLightmap",1);Shader.SetGlobalVector(globals[0],new Vector4(0,0,0,1));Shader.SetGlobalVector(globals[1],new Vector4(0,0,0,1));Shader.SetGlobalVector(globals[2],new Vector4(0,0,0,1));Shader.SetGlobalVector(globals[3],new Vector4(0,1.5f,3,0));Shader.SetGlobalVector(globals[4],Vector4.zero);
   var cam=Make("WindowDiagnosticCamera",sc).AddComponent<Camera>();cam.enabled=false;cam.scene=sc;cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=Color.black;cam.nearClipPlane=.02f;cam.farClipPlane=1000;cam.fieldOfView=30;cam.aspect=834f/614;cam.useOcclusionCulling=false;
   var pp=cam.gameObject.AddComponent<PostProcessLayer>();pp.volumeLayer=1<<31;pp.volumeTrigger=cam.transform;pp.stopNaNPropagation=true;pp.antialiasingMode=PostProcessLayer.Antialiasing.None;pp.finalBlitToCameraTarget=false;
   var resources=AssetDatabase.LoadAssetAtPath<PostProcessResources>(AssetDatabase.GUIDToAssetPath("d82512f9c8e5d4a4d938b575d47f88d4"));if(resources==null)throw new Exception("PP resources missing");pp.Init(resources);
   var paths=AssetDatabase.FindAssets("Lanbai_PP_S2 t:PostProcessProfile").Select(AssetDatabase.GUIDToAssetPath).Where(p=>Path.GetFileNameWithoutExtension(p)=="Lanbai_PP_S2").ToArray();if(paths.Length!=1)throw new Exception("Ambiguous S2 profile");
   var vol=Make("DiagnosticS2",sc).AddComponent<PostProcessVolume>();vol.gameObject.layer=31;vol.isGlobal=true;vol.weight=1;vol.priority=2;vol.sharedProfile=AssetDatabase.LoadAssetAtPath<PostProcessProfile>(paths[0]);
   var shader=Shader.Find("Hidden/Lanbai/DiagnosticObjectId");if(shader==null||!shader.isSupported||ShaderUtil.ShaderHasError(shader))throw new Exception("ID shader unavailable");
   var white=new Material(shader){hideFlags=HideFlags.HideAndDontSave};white.SetColor("_Color",Color.white);owned.Add(white);var black=new Material(shader){hideFlags=HideFlags.HideAndDontSave};black.SetColor("_Color",Color.black);owned.Add(black);
   var eyes=new[]{new Vector3(.5941508412361145f,1.733657717704773f,2.0382795333862305f),new Vector3(.2601340413093567f,1.4790256023406982f,1.8831098079681396f)};
   var eulers=new[]{new Vector3(323.61669921875f,104.86687469482422f,0),new Vector3(326.5489501953125f,60.0688362121582f,.000002046542249445338f)};
   for(int v=0;v<2;v++){
    string id=v==0?"window_05m":"window_10m";cam.transform.position=eyes[v];cam.transform.rotation=Quaternion.Euler(eulers[v]);for(int i=0;i<clones.Count;i++){clones[i].enabled=true;clones[i].sharedMaterials=mats[i];}
    Color32[] on=null,off=null,diff=null;int hit=0;if(beauty){on=Shot(cam,pp,2,false);clones[1].enabled=false;off=Shot(cam,pp,2,false);clones[1].enabled=true;diff=new Color32[on.Length];for(int i=0;i<on.Length;i++){bool yes=Math.Abs(L(on[i])-L(off[i]))>2;diff[i]=yes?new Color32(255,255,255,255):new Color32(0,0,0,255);if(yes)hit++;}
    Save(on,834,614,output+"/"+id+"_on.png");Save(off,834,614,output+"/"+id+"_off.png");Save(diff,834,614,output+"/"+id+"_diff_mask.png");}
    for(int i=0;i<clones.Count;i++){clones[i].sharedMaterials=Enumerable.Repeat(i==1?white:black,mats[i].Length).ToArray();clones[i].enabled=i!=2;}
    var mask=Shot(cam,pp,idSS,true);Save(mask,834,614,output+"/"+id+"_id_occluded.png");double area=mask.Sum(p=>(double)p.r)/(255*mask.Length);int binary=mask.Count(p=>p.r>=128);
    clones[0].enabled=false;clones[3].enabled=false;var bare=Shot(cam,pp,idSS,true);Save(bare,834,614,output+"/"+id+"_id_unoccluded.png");double bareArea=bare.Sum(p=>(double)p.r)/(255*bare.Length);
    shots.Add(D("id",id,"eye",V(cam.transform.position),"euler",V(cam.transform.eulerAngles),"width",834,"height",614,"id_ss",idSS,"vfov",30,"diff_coverage",beauty?(object)(hit/(double)on.Length):null,"id_fractional_area",area,"id_binary_area",binary/(double)mask.Length,"id_unoccluded_fractional_area",bareArea,"original_diff_coverage",v==0?.238521235129:.086424671338,"threshold_unchanged",.3));
   }
   File.WriteAllText(output+"/measurements.json",Lanbai.Test.TJson.Write(D("status","diagnostic_only","source_scene",active.path,"geometry",rows,"shots",shots,"profile",paths[0],"glass_policy","Glass_WinR1 is transparent ZWrite Off; omitted from geometric ownership/depth, never counted as frame. On/off beauty retains original glass. Opaque seat and pillar remain depth-tested black occluders, target Window_R1 white; backface culling and near plane retained.","limitations","Read-only mesh/material copies from current FullPreview; original unsaved test scene no longer exists. Original FAIL retained; paired re-render checks reconstruction. No builders, SaveAssets, scene save, Play or global resets.")));
  } finally {for(int i=0;i<globals.Length;i++)Shader.SetGlobalVector(globals[i],old[i]);Shader.SetGlobalFloat("_Udon_CabinLightmap",oldLM);if(sc.IsValid())EditorSceneManager.ClosePreviewScene(sc);foreach(var x in owned)if(x!=null)Object.DestroyImmediate(x);}
  if(SceneManager.GetActiveScene()!=active||active.isDirty)throw new Exception("Unexpected scene state changed; preserve for inspection");return "Diagnostic captured two original cameras, no world edits: "+output;
 }
}
}
#endif
