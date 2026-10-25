#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering.PostProcessing;
using UdonSharpEditor;
using VRC.Udon;
namespace Lanbai.Tests {
 [InitializeOnLoad] public static class LB_SeaViewAudit {
  const string Root=@"E:\IDMdownload\VRCC\Backups\continuation_20261025\act07a_view_0336";
  static readonly float[] Times={363.3f,367.2f,387f,446f,462.4f,474.4f,506.4f,532.4f,556.4f,559f,630f,645f};
  static bool running,stateOnly;static int idx,phase,frame;static double began;static string last,folder;
  static Lanbai.LB_Journey journey;static LanbaiAct07Driver sea;static UdonBehaviour udon;
  static LB_SeaViewAudit(){EditorApplication.update+=Tick;}
  public static string Begin(){return Start(false);}
  public static string BeginStateOnly(){return Start(true);}
  static string Start(bool only){
   if(!EditorApplication.isPlaying||running)throw new Exception("Play required; no other sea audit");
   stateOnly=only;folder=only?Root+"_state_corrected":Root;
   if(Directory.Exists(folder))throw new Exception("Existing audit: no overwrite");
   Directory.CreateDirectory(folder);journey=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();sea=UnityEngine.Object.FindObjectOfType<LanbaiAct07Driver>(true);udon=UdonSharpEditorUtility.GetBackingUdonBehaviour(journey);
   idx=0;phase=0;running=true;began=EditorApplication.timeSinceStartup;return last="running sea view audit";
  }
  static void Tick(){
   if(!running)return;
   if(!EditorApplication.isPlaying||EditorApplication.timeSinceStartup-began>90){running=false;last="stopped/timeout at "+idx;return;}
   try{
    if(phase==0){LB_FullAssembly.Seek((Times[idx]-.025f).ToString(System.Globalization.CultureInfo.InvariantCulture));frame=Time.frameCount;phase=1;return;}
    if(Time.frameCount<frame+2)return;
    float t=Convert.ToSingle(udon.GetProgramVariable("dbgT"));if(t<Times[idx])return;
    Capture(Times[idx],t);idx++;phase=0;
    if(idx==Times.Length){running=false;last="done 12 times / "+(stateOnly?"state only: ":"24 views: ")+folder;}
   }catch(Exception e){running=false;last=e.ToString();File.WriteAllText(Path.Combine(folder,"failure.txt"),last);Debug.LogException(e);}
  }
  static string PathOf(Transform t){string p=t.name;while(t.parent!=null){t=t.parent;p=t.name+"/"+p;}return p;}
  static void Capture(float target,float actual){
   var name=target.ToString("F1",System.Globalization.CultureInfo.InvariantCulture);var sb=new StringBuilder();
   sb.AppendLine("target="+target+" actual="+actual+" eyeLocal=(0.70,1.77,0.20) source=LB_Udon.HERO_EYE; front=0deg up=60deg; both views use same rendered runtime state");
   sb.AppendLine("seaLevel="+Shader.GetGlobalFloat("_Udon_SeaLevel")+" underwater="+Shader.GetGlobalFloat("_Udon_Underwater")+" seaMode="+Shader.GetGlobalFloat("_Udon_SeaMode"));
   foreach(var r in new[]{sea.seaRenderer,sea.shafts,sea.lastShaft,sea.snow,sea.seeds,sea.trails,sea.ridge,sea.warmPoint,sea.dome,sea.mirrorRenderer}.Where(r=>r!=null)){
    var b=new MaterialPropertyBlock();r.GetPropertyBlock(b);
    sb.AppendLine(PathOf(r.transform)+" active="+r.gameObject.activeInHierarchy+" enabled="+r.enabled+" forcedOff="+r.forceRenderingOff+" material="+r.sharedMaterial.name+" _Gain(block)="+b.GetFloat("_Gain")+" _WindowGain(block)="+b.GetFloat("_WindowGain")+" position="+r.transform.position);
   }
   sb.AppendLine("beam="+(sea.beam!=null?(sea.beam.gameObject.activeInHierarchy+"/"+sea.beam.enabled+" E="+sea.beam.intensity):"null"));
   if(stateOnly){File.WriteAllText(Path.Combine(folder,name+"_state.txt"),sb.ToString());return;}
   var desc=UnityEngine.Object.FindObjectOfType<VRC.SDK3.Components.VRCSceneDescriptor>();var src=desc.ReferenceCamera.GetComponent<Camera>();
   var go=new GameObject("LB_SeaViewAudit_Camera");go.hideFlags=HideFlags.HideAndDontSave;var cam=go.AddComponent<Camera>();cam.CopyFrom(src);cam.enabled=false;cam.allowHDR=true;cam.farClipPlane=45000;cam.fieldOfView=58.7155f;cam.aspect=16f/9f;
   cam.cullingMask&=~((1<<5)|(1<<9)|(1<<10)|(1<<12)|(1<<18)|(1<<19)|(1<<20));cam.transform.position=journey.busRoot.TransformPoint(new Vector3(.70f,1.77f,.20f));
   var pp=go.AddComponent<PostProcessLayer>();pp.volumeLayer=1<<LayerMask.NameToLayer("PostProcessing");pp.volumeTrigger=cam.transform;pp.stopNaNPropagation=true;
   var sourcePP=src.GetComponent<PostProcessLayer>();if(sourcePP!=null){var f=typeof(PostProcessLayer).GetField("m_Resources",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);var resources=f.GetValue(sourcePP) as PostProcessResources;if(resources!=null)pp.Init(resources);pp.antialiasingMode=sourcePP.antialiasingMode;}
   var prev=RenderTexture.active;var hdr=new RenderTexture(1600,900,24,RenderTextureFormat.ARGBHalf,RenderTextureReadWrite.Linear);var ldr=new RenderTexture(1600,900,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);var tex=new Texture2D(1600,900,TextureFormat.RGB24,false,false);
   try{
    hdr.Create();ldr.Create();cam.targetTexture=hdr;
    foreach(var up in new[]{false,true}){
     cam.transform.rotation=journey.busRoot.rotation*Quaternion.Euler(up?-60:0,0,0);for(int k=0;k<3;k++)cam.Render();Graphics.Blit(hdr,ldr);RenderTexture.active=ldr;tex.ReadPixels(new Rect(0,0,1600,900),0,0);tex.Apply();File.WriteAllBytes(Path.Combine(Root,name+(up?"_up60.png":"_front.png")),tex.EncodeToPNG());
    }
    File.WriteAllText(Path.Combine(Root,name+"_state.txt"),sb.ToString());
   }finally{RenderTexture.active=prev;cam.targetTexture=null;UnityEngine.Object.DestroyImmediate(go);hdr.Release();ldr.Release();UnityEngine.Object.DestroyImmediate(hdr);UnityEngine.Object.DestroyImmediate(ldr);UnityEngine.Object.DestroyImmediate(tex);}
  }
  public static string Status(){return running?"running "+idx+"/12":last;}
 }
}
#endif
