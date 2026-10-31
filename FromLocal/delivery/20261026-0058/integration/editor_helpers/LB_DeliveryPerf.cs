#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEditor;
using UnityEngine.Profiling;
using UnityEngine.Rendering.PostProcessing;
using Unity.Profiling;
using Unity.Profiling.LowLevel.Unsafe;
namespace Lanbai.Tests {
 [InitializeOnLoad] public static class LB_DeliveryPerf {
  const string Root=@"E:\IDMdownload\VRCC\Backups\continuation_20261026\delivery_0058";
  static readonly float[] AllPoints={30,90,135,154.5f,175,180,185,200,215,300,367.2f,532.4f,630,700,870,950,990,1050,1105,1116,1160,1200,1250};
  static float[] Points=AllPoints; static double sampleStart;
  static bool running; static int index,frame; static double phaseStart; static string last,folder;
  static StreamWriter csv; static GameObject viewer; static Camera cam;
  static List<ProfilerRecorder> records=new List<ProfilerRecorder>(); static List<string> names=new List<string>();
  static FrameTiming[] timing=new FrameTiming[1];
  static LB_DeliveryPerf(){EditorApplication.update+=Tick;}
  public static string Begin(string label) {
   if(!EditorApplication.isPlaying||running) throw new Exception("Play required; perf must be idle");
   if(label.Any(c=>!char.IsLetterOrDigit(c)&&c!='_'))throw new Exception("Invalid label");
   Points=label.EndsWith("_only700")?new float[]{700}:AllPoints;
   folder=Path.Combine(Root,"perf_"+label);if(Directory.Exists(folder))throw new Exception("No overwrite");Directory.CreateDirectory(folder);
   var handles=new List<ProfilerRecorderHandle>();ProfilerRecorderHandle.GetAvailable(handles);
   var descs=handles.Select(ProfilerRecorderHandle.GetDescription).Where(d=>d.Name.IndexOf("udon",StringComparison.OrdinalIgnoreCase)>=0).ToArray();
   foreach(var d in descs.Take(24)) { var r=ProfilerRecorder.StartNew(d.Category,d.Name,1);records.Add(r);names.Add(d.Name.Replace(",",";")); }
   File.WriteAllText(Path.Combine(folder,"method.txt"),"Background Editor/ClientSim; D28 camera (.55,1.70,2.05), 58.7155deg, no quality changes. 2s settle +4s samples per point. Contains placeholders, not final/VR. Column cpuFrameMs is frame interval, NOT pure CPU time, from Time.unscaledDeltaTime; GPU timing remains UNVERIFIED in this background setup, including nonzero values. DrawCalls from UnityStats (Editor aggregate); graphicsDriverBytes is Unity graphics allocation estimate, NOT physical VRAM usage. Udon markers individually reported, not summed (nesting possible). GPU="+SystemInfo.graphicsDeviceName+" Screen="+Screen.width+"x"+Screen.height+" MSAA="+QualitySettings.antiAliasing+"\nUdon markers="+string.Join(" | ",names));
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();var desc=UnityEngine.Object.FindObjectOfType<VRC.SDK3.Components.VRCSceneDescriptor>();var src=desc.ReferenceCamera.GetComponent<Camera>();
   viewer=new GameObject("LB_DeliveryPerf_Camera"); viewer.hideFlags=HideFlags.HideAndDontSave;cam=viewer.AddComponent<Camera>();cam.CopyFrom(src);cam.enabled=true;cam.depth=99;cam.allowHDR=true;cam.farClipPlane=45000;cam.fieldOfView=58.7155f;
   cam.cullingMask&=~((1<<5)|(1<<9)|(1<<10)|(1<<12)|(1<<18)|(1<<19)|(1<<20));cam.transform.position=j.busRoot.TransformPoint(new Vector3(.55f,1.70f,2.05f));cam.transform.rotation=j.busRoot.rotation;
   var pp=viewer.AddComponent<PostProcessLayer>();pp.volumeLayer=1<<LayerMask.NameToLayer("PostProcessing");pp.volumeTrigger=cam.transform;pp.stopNaNPropagation=true;
   var sourcePP=src.GetComponent<PostProcessLayer>();if(sourcePP!=null){var f=typeof(PostProcessLayer).GetField("m_Resources",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);var resources=f.GetValue(sourcePP) as PostProcessResources;if(resources!=null)pp.Init(resources);pp.antialiasingMode=sourcePP.antialiasingMode;}
   csv=new StreamWriter(Path.Combine(folder,"frames.csv"));csv.WriteLine("target,frame,cpuFrameMs,gpuMs,drawCalls,batches,triangles,graphicsDriverBytes,"+string.Join(",",names));
   index=0;frame=-1;running=true;Seek();return last="running background performance baseline";
  }
  static void Seek(){LB_FullAssembly.Seek(Points[index].ToString(CultureInfo.InvariantCulture));phaseStart=EditorApplication.timeSinceStartup;sampleStart=0;}
  static void Finish(string reason){running=false;last=reason;csv?.Dispose();csv=null;foreach(var r in records)r.Dispose();records.Clear();names.Clear();if(viewer!=null)UnityEngine.Object.DestroyImmediate(viewer);File.WriteAllText(Path.Combine(folder,"status.txt"),reason);}
  static void Tick(){if(!running)return;try{
   if(!EditorApplication.isPlaying){Finish("interrupted: Play stopped");return;}
   if(Time.frameCount==frame)return;frame=Time.frameCount;
   var j=UnityEngine.Object.FindObjectOfType<Lanbai.LB_Journey>();cam.transform.position=j.busRoot.TransformPoint(new Vector3(.55f,1.70f,2.05f));cam.transform.rotation=j.busRoot.rotation;
   double age=EditorApplication.timeSinceStartup-phaseStart;
   if(sampleStart>0 && EditorApplication.timeSinceStartup-sampleStart>=4){index++;if(index==Points.Length){Finish("done "+Points.Length+" timeline points");return;}Seek();return;}
   FrameTimingManager.CaptureFrameTimings();if(age<2)return;if(sampleStart==0)sampleStart=EditorApplication.timeSinceStartup;
   uint n=FrameTimingManager.GetLatestTimings(1,timing);double gpu=n>0?timing[0].gpuFrameTime:0;
   csv.WriteLine(string.Join(",",new[]{Points[index].ToString(CultureInfo.InvariantCulture),frame.ToString(),(Time.unscaledDeltaTime*1000).ToString("F4",CultureInfo.InvariantCulture),gpu.ToString("F4",CultureInfo.InvariantCulture),UnityStats.drawCalls.ToString(),UnityStats.batches.ToString(),UnityStats.triangles.ToString(),Profiler.GetAllocatedMemoryForGraphicsDriver().ToString()}.Concat(records.Select(r=>r.Valid?r.LastValue.ToString():"NA"))));
  }catch(Exception e){Finish("ERROR "+e);Debug.LogException(e);}}
  public static string Status(){return running?"running "+index+"/"+Points.Length:last;}
 }
}
#endif
