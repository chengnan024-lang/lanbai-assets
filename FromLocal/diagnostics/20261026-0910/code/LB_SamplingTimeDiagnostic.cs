#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.Rendering;
using Object=UnityEngine.Object;
namespace Lanbai.Tests {
public static class LB_SamplingTimeDiagnostic {
 const string Dir="E:/IDMdownload/VRCC/Backups/continuation_20261026/sampling_time_0920";
 static Dictionary<string,object> D(params object[] p){var d=new Dictionary<string,object>();for(int i=0;i<p.Length;i+=2)d[(string)p[i]]=p[i+1];return d;}
 static Color[] Read(RenderTexture r){var old=RenderTexture.active;var t=new Texture2D(r.width,r.height,TextureFormat.RGBAFloat,false,true);try{RenderTexture.active=r;t.ReadPixels(new Rect(0,0,r.width,r.height),0,0);t.Apply();return t.GetPixels();}finally{RenderTexture.active=old;Object.DestroyImmediate(t);}}
 static RenderTexture RT(int w,int h,int depth=0){var r=new RenderTexture(w,h,depth,RenderTextureFormat.ARGBFloat,RenderTextureReadWrite.Linear){filterMode=FilterMode.Bilinear,antiAliasing=1};r.Create();return r;}
 public static string Run(string label){
  var active=SceneManager.GetActiveScene();if(EditorApplication.isPlayingOrWillChangePlaymode||active.isDirty||active.path!=LB_FullAssembly.Preview)throw new Exception("Clean stopped FullPreview only");
  if(label.Any(c=>!char.IsLetterOrDigit(c)&&c!='_'))throw new Exception("Simple label required");Directory.CreateDirectory(Dir);string path=Dir+"/"+label+".json";if(File.Exists(path))throw new Exception("No replay");
  var shader=Shader.Find("Hidden/Lanbai/SamplingTimeDiagnostic");if(shader==null||ShaderUtil.ShaderHasError(shader))throw new Exception("Probe shader missing");var mat=new Material(shader){hideFlags=HideFlags.HideAndDontSave};var sc=EditorSceneManager.NewPreviewScene();var rts=new List<RenderTexture>();CommandBuffer cb=null;Camera cam=null;var rows=new List<object>();var sampling=new List<object>();
  try {
   var go=new GameObject("DiagnosticTimeCamera"){hideFlags=HideFlags.HideAndDontSave};SceneManager.MoveGameObjectToScene(go,sc);cam=go.AddComponent<Camera>();cam.enabled=false;cam.scene=sc;cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=Color.black;cam.cullingMask=0;cam.allowHDR=true;cam.allowMSAA=false;
   var low=RT(32,32,24);var high=RT(128,128,24);var probe=RT(1,1);rts.AddRange(new[]{low,high,probe});cb=new CommandBuffer{name="Read actual GPU camera time"};cb.Blit(BuiltinRenderTextureType.CameraTarget,probe,mat);cam.AddCommandBuffer(CameraEvent.AfterEverything,cb);
   for(int i=0;i<12;i++){
    cam.targetTexture=i%2==0?low:high;double start=EditorApplication.timeSinceStartup;cam.Render();var p=Read(probe)[0];rows.Add(D("index",i,"label",i%2==0?"low":"high_reference","editor_before",start,"editor_after",EditorApplication.timeSinceStartup,"cpu_time",Time.time,"cpu_realtime",Time.realtimeSinceStartup,"cpu_frame",Time.frameCount,"rendered_frame",Time.renderedFrameCount,"gpu_Time_y",p.r,"gpu_SinTime_w",p.g,"gpu_CosTime_w",p.b,"gpu_DeltaTime_x",p.a));
   }
   cam.RemoveCommandBuffer(CameraEvent.AfterEverything,cb);cb.Release();cb=null;cam.targetTexture=null;
   mat.SetFloat("_Mode",1);
   foreach(int ss in new[]{2,4}){
    var big=RT(32*ss,32*ss);var small=RT(32,32);rts.Add(big);rts.Add(small);mat.SetFloat("_Period",ss);Graphics.Blit(null,big,mat);Graphics.Blit(big,small);var a=Read(big);var b=Read(small);double[] box=new double[32*32];for(int y=0;y<32;y++)for(int x=0;x<32;x++){double total=0;for(int dy=0;dy<ss;dy++)for(int dx=0;dx<ss;dx++)total+=a[(y*ss+dy)*32*ss+x*ss+dx].r;box[y*32+x]=total/(ss*ss);}
    sampling.Add(D("ss",ss,"source_white_fraction",a.Average(p=>(double)p.r),"legacy_bilinear_mean",b.Average(p=>(double)p.r),"box_mean",box.Average(),"max_abs_difference",box.Select((v,i)=>Math.Abs(v-b[i].r)).Max(),"expected_box",1.0/(ss*ss),"linear_float_targets",true));
   }
   File.WriteAllText(path,Lanbai.Test.TJson.Write(D("label",label,"utc",DateTime.UtcNow.ToString("o"),"unity",Application.unityVersion,"playing",false,"gpu_time",rows,"downsample_calibration",sampling,"purpose","Diagnostic camera uses same Camera.Render primitive as tree harness. Not a tree re-test, cannot retroactively establish old shader time or prove the tree root cause. No changes to official metrics/thresholds.","sources",new[]{"Assets/Lanbai/Engineering/UnityTest/Editor/LanbaiTestCapture.cs: Renderer2.Frame uses one bilinear Graphics.Blit; Sequence loops synchronously without editor/player yield."})));
  } finally {if(cam!=null){if(cb!=null){cam.RemoveCommandBuffer(CameraEvent.AfterEverything,cb);cb.Release();}cam.targetTexture=null;}EditorSceneManager.ClosePreviewScene(sc);foreach(var r in rts){if(RenderTexture.active==r)RenderTexture.active=null;r.Release();Object.DestroyImmediate(r);}Object.DestroyImmediate(mat);}
  if(active.isDirty||SceneManager.GetActiveScene()!=active)throw new Exception("Unexpected scene state; preserve");return path;
 }
}
}
#endif
