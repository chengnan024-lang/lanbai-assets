#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering.PostProcessing;
using UdonSharpEditor;
using VRC.Udon;
namespace Lanbai.Tests {
 [InitializeOnLoad] public static class LB_FlickerDiagnostic {
  const string Root=@"E:\IDMdownload\VRCC\Backups\continuation_20261025\flicker_0315\captures";
  static GameObject go; static Camera camera; static RenderTexture hdr,ldr; static Texture2D tex;
  static PostProcessLayer pp; static Lanbai.LB_Journey journey; static UdonBehaviour udon;
  static readonly List<string> rows=new List<string>(); static readonly List<string> errors=new List<string>();
  static Renderer[] bus; static Behaviour[] mirrors; static MaterialPropertyBlock[] blocks;
  static string label,mode,folder,last; static double started,next; static float length,startT; static int count,initialFrame;
  static bool move; static bool[] intervalMirrorOn;
  static LB_FlickerDiagnostic(){EditorApplication.update+=Tick;EditorApplication.playModeStateChanged+=s=>{if(s==PlayModeStateChange.ExitingPlayMode&&go!=null)Finish("play stopped");};}
  static string PathOf(Transform t){string p=t.name;while(t.parent!=null){t=t.parent;p=t.name+"/"+p;}return p;}
  public static string Inspect(){
   var sb=new StringBuilder();var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>(true);
   foreach(var c in UnityEngine.Object.FindObjectsOfType<Camera>(true))sb.AppendLine("camera "+PathOf(c.transform)+" active="+c.isActiveAndEnabled+" near="+c.nearClipPlane+" far="+c.farClipPlane+" mask="+c.cullingMask+" path="+c.actualRenderingPath);
   foreach(var m in UnityEngine.Object.FindObjectsOfType<MonoBehaviour>(true).Where(m=>m!=null&&m.GetType().Name.Contains("MirrorReflection")))sb.AppendLine("mirror "+m.GetType().FullName+" "+PathOf(m.transform)+" active="+m.isActiveAndEnabled);
   if(j!=null){
    sb.AppendLine("cross="+string.Join(",",j.starCross.Select(x=>x.ToString("F3"))));
    sb.AppendLine("segments="+string.Join(",",j.segStart.Select(x=>x.ToString("F3"))));
    foreach(var r in new[]{j.seaARenderer,j.seaBRenderer}.Where(x=>x!=null))sb.AppendLine("sea "+PathOf(r.transform)+" shader="+AssetDatabase.GetAssetPath(r.sharedMaterial.shader));
    if(EditorApplication.isPlaying){var u=UdonSharpEditorUtility.GetBackingUdonBehaviour(j);foreach(var key in new[]{"seaARenderer","seaBRenderer","skyTop","skyHorizon","skyTex"}){var v=u.GetProgramVariable(key);sb.AppendLine("runtime "+key+"="+v+(v is Array?" length="+((Array)v).Length:""));}}
    var mats=j.busRoot.GetComponentsInChildren<Renderer>(true).SelectMany(r=>r.sharedMaterials).Where(m=>m!=null).Distinct();
    foreach(var m in mats)sb.AppendLine("bus material "+m.name+" shader="+AssetDatabase.GetAssetPath(m.shader));
   }
   sb.AppendLine("Shader.Find Lanbai/Sea="+AssetDatabase.GetAssetPath(Shader.Find("Lanbai/Sea")));
   return sb.ToString();
  }
  // label|mode|start seconds|duration|motion(0/1); per-render isolation never changes shared materials.
  public static string Begin(string spec){
   if(!EditorApplication.isPlaying)throw new Exception("Play required");
   if(go!=null)throw new Exception("Another capture is active");
   var s=spec.Split('|');if(s.Length!=5)throw new Exception("label|mode|start|duration|motion");
   label=s[0];mode=s[1];startT=float.Parse(s[2],System.Globalization.CultureInfo.InvariantCulture);length=float.Parse(s[3],System.Globalization.CultureInfo.InvariantCulture);move=s[4]=="1";
   if(!new[]{"baseline","opaque_bus","no_bus","no_sea","no_mirrors","no_pp","no_refl","no_mirrors_interval"}.Contains(mode))throw new Exception("Unknown mode");
   folder=Path.Combine(Root,label);if(Directory.Exists(folder))throw new Exception("Capture label already exists");
   Directory.CreateDirectory(folder);rows.Clear();errors.Clear();count=0;
   journey=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();
   udon=UdonSharpEditorUtility.GetBackingUdonBehaviour(journey);
   bus=journey.busRoot.GetComponentsInChildren<Renderer>(true);
   blocks=bus.Select(r=>{var b=new MaterialPropertyBlock();r.GetPropertyBlock(b);return b;}).ToArray();
   mirrors=UnityEngine.Object.FindObjectsOfType<MonoBehaviour>(true).Where(m=>m!=null&&m.GetType().Name.Contains("MirrorReflection")).Cast<Behaviour>().ToArray();
   intervalMirrorOn=mirrors.Select(m=>m.enabled).ToArray();
   if(mode=="no_mirrors_interval")foreach(var m in mirrors)m.enabled=false;
   var desc=UnityEngine.Object.FindObjectOfType<VRC.SDK3.Components.VRCSceneDescriptor>();
   var src=desc.ReferenceCamera.GetComponent<Camera>();
   go=new GameObject("LB_FlickerDiagnostic_Camera");go.hideFlags=HideFlags.HideAndDontSave;
   camera=go.AddComponent<Camera>();camera.CopyFrom(src);camera.enabled=false;camera.allowHDR=true;camera.farClipPlane=45000;camera.fieldOfView=58.7155f;camera.aspect=16f/9f;
   camera.cullingMask&=~((1<<5)|(1<<9)|(1<<10)|(1<<12)|(1<<18)|(1<<19)|(1<<20));
   camera.transform.position=journey.busRoot.TransformPoint(new Vector3(.55f,1.7f,2.05f));camera.transform.rotation=journey.busRoot.rotation;
   pp=go.AddComponent<PostProcessLayer>();pp.volumeLayer=1<<LayerMask.NameToLayer("PostProcessing");pp.volumeTrigger=camera.transform;pp.stopNaNPropagation=true;
   var sourcePP=src.GetComponent<PostProcessLayer>();
   if(sourcePP!=null){
    var f=typeof(PostProcessLayer).GetField("m_Resources",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
    var r=f.GetValue(sourcePP) as PostProcessResources;if(r!=null)pp.Init(r);
    pp.antialiasingMode=sourcePP.antialiasingMode;
   }
   hdr=new RenderTexture(960,540,24,RenderTextureFormat.ARGBHalf,RenderTextureReadWrite.Linear);hdr.Create();
   ldr=new RenderTexture(960,540,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);ldr.Create();
   tex=new Texture2D(960,540,TextureFormat.RGB24,false,false);camera.targetTexture=hdr;
   rows.Add("frame,t,elapsed,busAlpha,seaA_y,seaB_y,seaA_active,seaB_active,star_x,star_y,galaxy_x,skyBlend_z,mean,mirrorBefore,mirrorAfter,topBefore,topAfter");
   File.WriteAllText(Path.Combine(folder,"scene_info.txt"),Inspect()+"\nmode="+mode+" motion="+move+" ppAA="+pp.antialiasingMode);
   LB_FullAssembly.Seek(startT.ToString(System.Globalization.CultureInfo.InvariantCulture));started=EditorApplication.timeSinceStartup;next=started+.1;initialFrame=Time.frameCount;
   Application.logMessageReceived+=Log;last="running "+label;return last;
  }
  static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)errors.Add(message+"\n"+stack);}
  static void Tick(){
   if(go==null)return;
   if(!EditorApplication.isPlaying){Finish("not playing");return;}
   double now=EditorApplication.timeSinceStartup;if(now<next||Time.frameCount<initialFrame+3)return;
   if(now-started>length){Finish("done");return;}
   next=now+.1;
   try{Capture(now-started);}catch(Exception e){errors.Add(e.ToString());Finish("exception");}
  }
  static void Capture(double elapsed){
   float t=Convert.ToSingle(udon.GetProgramVariable("dbgT"));
   float alpha=Convert.ToSingle(udon.GetProgramVariable("_alpha"));
   if(move)camera.transform.position=journey.busRoot.TransformPoint(new Vector3(.55f+Mathf.Sin((float)elapsed*.7f)*.012f,1.7f,2.05f));
   var old=RenderTexture.active;var off=bus.Select(r=>r.forceRenderingOff).ToArray();
   var seas=new[]{journey.seaARenderer,journey.seaBRenderer};var seaOff=seas.Select(r=>r!=null&&r.forceRenderingOff).ToArray();
   var mirrorOn=mirrors.Select(m=>m.enabled).ToArray();bool ppOn=pp.enabled;
   var seaBlocks=seas.Select(r=>{var b=new MaterialPropertyBlock();if(r!=null)r.GetPropertyBlock(b);return b;}).ToArray();
   var beforeBlock=new MaterialPropertyBlock();journey.seaBRenderer.GetPropertyBlock(beforeBlock);
   try{
    if(mode=="opaque_bus")for(int i=0;i<bus.Length;i++){bus[i].GetPropertyBlock(blocks[i]);var b=new MaterialPropertyBlock();bus[i].GetPropertyBlock(b);b.SetFloat("_Alpha",1f);bus[i].SetPropertyBlock(b);}
    if(mode=="no_bus")foreach(var r in bus)r.forceRenderingOff=true;
    if(mode=="no_sea")foreach(var r in seas)if(r!=null)r.forceRenderingOff=true;
    if(mode=="no_mirrors")foreach(var m in mirrors)m.enabled=false;
    if(mode=="no_pp")pp.enabled=false;
    if(mode=="no_refl")foreach(var r in seas)if(r!=null){var b=new MaterialPropertyBlock();r.GetPropertyBlock(b);b.SetFloat("_ReflAmount",0);r.SetPropertyBlock(b);}
    camera.Render();Graphics.Blit(hdr,ldr);RenderTexture.active=ldr;tex.ReadPixels(new Rect(0,0,960,540),0,0);tex.Apply();
    var afterBlock=new MaterialPropertyBlock();journey.seaBRenderer.GetPropertyBlock(afterBlock);
    File.WriteAllBytes(Path.Combine(folder,count.ToString("D4")+".png"),tex.EncodeToPNG());
    var px=tex.GetPixels32();double sum=0;for(int i=0;i<px.Length;i+=8)sum+=(px[i].r+px[i].g+px[i].b)/3.0;
    var stars=Shader.GetGlobalVector("_Udon_StarGain");var galaxy=Shader.GetGlobalVector("_Udon_GalaxyGain");var blend=Shader.GetGlobalVector("_Udon_SkyBlend");
    rows.Add(string.Join(",",new[]{(double)count,t,elapsed,alpha,journey.seaA.position.y,journey.seaB.position.y,journey.seaA.gameObject.activeInHierarchy?1:0,journey.seaB.gameObject.activeInHierarchy?1:0,stars.x,stars.y,galaxy.x,blend.z,sum/((px.Length+7)/8),beforeBlock.GetFloat("_Mirror"),afterBlock.GetFloat("_Mirror"),beforeBlock.GetColor("_SkyTop").r,afterBlock.GetColor("_SkyTop").r}.Select(v=>v.ToString("F6",System.Globalization.CultureInfo.InvariantCulture))));
    count++;
   }finally{
    RenderTexture.active=old;pp.enabled=ppOn;
    for(int i=0;i<bus.Length;i++){bus[i].forceRenderingOff=off[i];if(mode=="opaque_bus")bus[i].SetPropertyBlock(blocks[i]);}
    for(int i=0;i<seas.Length;i++)if(seas[i]!=null){seas[i].forceRenderingOff=seaOff[i];if(mode=="no_refl")seas[i].SetPropertyBlock(seaBlocks[i]);}
    for(int i=0;i<mirrors.Length;i++)mirrors[i].enabled=mirrorOn[i];
   }
  }
  static void Finish(string why){
   Application.logMessageReceived-=Log;
   if(mode=="no_mirrors_interval"&&mirrors!=null)for(int i=0;i<mirrors.Length;i++)if(mirrors[i]!=null)mirrors[i].enabled=intervalMirrorOn[i];
   if(folder!=null){File.WriteAllLines(Path.Combine(folder,"frames.csv"),rows);File.WriteAllLines(Path.Combine(folder,"errors.txt"),errors);}
   last=why+" "+label+" frames="+count+" errors="+errors.Count+" folder="+folder;
   if(camera!=null)camera.targetTexture=null;
   if(go!=null)UnityEngine.Object.DestroyImmediate(go);go=null;
   if(hdr!=null){hdr.Release();UnityEngine.Object.DestroyImmediate(hdr);}if(ldr!=null){ldr.Release();UnityEngine.Object.DestroyImmediate(ldr);}if(tex!=null)UnityEngine.Object.DestroyImmediate(tex);
  }
  public static string Status(){return go==null?last:"running "+label+" frames="+count;}
 }
}
#endif
