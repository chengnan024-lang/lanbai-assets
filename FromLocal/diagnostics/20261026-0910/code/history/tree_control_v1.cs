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
using UnityEngine.Rendering.PostProcessing;
using Object=UnityEngine.Object;
namespace Lanbai.Tests {
public static class LB_TreeControlledDiagnostic {
 const int W=834,H=614,N=W*H,Frames=30;
 const string Output="E:/IDMdownload/VRCC/Backups/continuation_20261026/tree_control_0930";
 static Dictionary<string,object> D(params object[] p){var d=new Dictionary<string,object>();for(int i=0;i<p.Length;i+=2)d[(string)p[i]]=p[i+1];return d;}
 static GameObject Make(string n,Scene s){var g=new GameObject(n){hideFlags=HideFlags.HideAndDontSave};SceneManager.MoveGameObjectToScene(g,s);return g;}
 static RenderTexture RT(int w,int h,int depth,int aa,RenderTextureFormat fmt,RenderTextureReadWrite rw){var r=new RenderTexture(w,h,depth,fmt,rw){antiAliasing=aa,filterMode=FilterMode.Bilinear};r.Create();return r;}
 static Color32[] Read8(RenderTexture r){var p=RenderTexture.active;var t=new Texture2D(r.width,r.height,TextureFormat.RGB24,false,false);try{RenderTexture.active=r;t.ReadPixels(new Rect(0,0,r.width,r.height),0,0);t.Apply();return t.GetPixels32();}finally{RenderTexture.active=p;Object.DestroyImmediate(t);}}
 static Color ReadFloat(RenderTexture r){var p=RenderTexture.active;var t=new Texture2D(1,1,TextureFormat.RGBAFloat,false,true);try{RenderTexture.active=r;t.ReadPixels(new Rect(0,0,1,1),0,0);t.Apply();return t.GetPixels()[0];}finally{RenderTexture.active=p;Object.DestroyImmediate(t);}}
 static double L(Color32 c){return .2126*c.r+.7152*c.g+.0722*c.b;}
 static float Wave(float t,float a,float p,float b,float q){return .6f*Mathf.Sin(2*Mathf.PI*a*t+p)+.4f*Mathf.Sin(2*Mathf.PI*b*t+q);}
 static object Stats(double[] s,double[] s2,bool[] roi){var a=new List<double>();for(int k=0;k<N;k++)if(roi[k])a.Add(Math.Sqrt(Math.Max(0,s2[k]/Frames-Math.Pow(s[k]/Frames,2))));a.Sort();return D("mean",a.Average(),"p99",a[(int)Math.Floor((a.Count-1)*.99)],"fraction_gt4",a.Count(x=>x>4)/(double)a.Count,"roi_pixels",a.Count);}
 public static string Run(string label){
  var active=SceneManager.GetActiveScene();if(EditorApplication.isPlayingOrWillChangePlaymode||active.isDirty||active.path!=LB_FullAssembly.Preview)throw new Exception("Clean stopped FullPreview required");if(label.Any(c=>!char.IsLetterOrDigit(c)&&c!='_'))throw new Exception("Simple label required");string dir=Output+"/"+label;if(Directory.Exists(dir))throw new Exception("No replay");Directory.CreateDirectory(dir);
  var sceneLights=Object.FindObjectsOfType<Light>().Where(x=>x.enabled&&x.gameObject.activeInHierarchy).ToArray();var sc=EditorSceneManager.NewPreviewScene();var owned=new List<Object>();var rts=new List<RenderTexture>();var renderers=new List<MeshRenderer>();var materials=new List<object>();var lightRows=new List<object>();Camera cam=null;CommandBuffer cb=null;var records=new List<object>();
  try {
   float[] xs={9,12.5f,8.5f,15,-8.5f,-11,-9},zs={16,24,33,40,14,26,38},ys={20,140,260,0,70,200,310};string[] names={"Tree_A1","Tree_A2","Tree_A3","Tree_B1","Tree_A3","Tree_A1","Tree_A2"};
   for(int i=0;i<names.Length;i++){
    var pf=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Lanbai/Lamps/Tree/Prefabs/"+names[i]+".prefab");if(pf==null)throw new Exception("Prefab missing");var group=pf.GetComponentInChildren<LODGroup>();if(group==null)throw new Exception("LODGroup missing");var lod=group.GetLODs()[0];var row=Make(names[i]+"_"+i,sc);row.transform.position=new Vector3(xs[i],0,zs[i]);row.transform.rotation=Quaternion.Euler(0,ys[i],0);
    foreach(var src in lod.renderers){var mf=src.GetComponent<MeshFilter>();if(mf==null)throw new Exception("Non mesh tree");var g=Make(src.name,sc);g.layer=src.gameObject.layer;g.transform.SetParent(row.transform,false);g.transform.localPosition=pf.transform.InverseTransformPoint(src.transform.position);g.transform.localRotation=Quaternion.Inverse(pf.transform.rotation)*src.transform.rotation;g.transform.localScale=src.transform.lossyScale;g.AddComponent<MeshFilter>().sharedMesh=mf.sharedMesh;var r=g.AddComponent<MeshRenderer>();r.lightProbeUsage=LightProbeUsage.Off;r.reflectionProbeUsage=ReflectionProbeUsage.Off;r.shadowCastingMode=src.shadowCastingMode;r.receiveShadows=src.receiveShadows;
     r.sharedMaterials=src.sharedMaterials.Select(m=>{var v=new Material(m){hideFlags=HideFlags.HideAndDontSave};owned.Add(v);materials.Add(D("source",AssetDatabase.GetAssetPath(m),"shader",m.shader.name,"wind_freq_before",m.GetFloat("_WindFreq"),"flutter_freq_before",m.GetFloat("_FlutterFreq"),"wind_strength",m.GetFloat("_WindStrength"),"flutter",m.GetFloat("_Flutter")));v.SetFloat("_WindFreq",0);v.SetFloat("_FlutterFreq",0);return v;}).ToArray();renderers.Add(r);
    }
   }
   foreach(var src in sceneLights){var g=Make(src.name,sc);g.transform.position=src.transform.position;g.transform.rotation=src.transform.rotation;var light=g.AddComponent<Light>();EditorUtility.CopySerialized(src,light);lightRows.Add(D("name",src.name,"type",src.type.ToString(),"intensity",src.intensity,"range",src.range,"mask",src.cullingMask));}
   cam=Make("ControlledTreeCamera",sc).AddComponent<Camera>();cam.enabled=false;cam.scene=sc;cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=Color.black;cam.fieldOfView=30;cam.aspect=W/(float)H;cam.nearClipPlane=.05f;cam.farClipPlane=1000;cam.allowHDR=true;cam.allowMSAA=true;cam.useOcclusionCulling=false;
   var pp=cam.gameObject.AddComponent<PostProcessLayer>();pp.volumeLayer=1<<31;pp.volumeTrigger=cam.transform;pp.stopNaNPropagation=true;pp.antialiasingMode=PostProcessLayer.Antialiasing.None;pp.finalBlitToCameraTarget=false;pp.Init(AssetDatabase.LoadAssetAtPath<PostProcessResources>(AssetDatabase.GUIDToAssetPath("d82512f9c8e5d4a4d938b575d47f88d4")));
   var vol=Make("ControlledS1",sc).AddComponent<PostProcessVolume>();vol.gameObject.layer=31;vol.isGlobal=true;vol.weight=1;vol.sharedProfile=AssetDatabase.LoadAssetAtPath<PostProcessProfile>("Assets/Lanbai/Grading/Profiles/Lanbai_PP_S1.asset");if(vol.sharedProfile==null)throw new Exception("S1 missing");
   var low=RT(W,H,24,4,RenderTextureFormat.ARGBHalf,RenderTextureReadWrite.Linear);var high=RT(W*4,H*4,24,4,RenderTextureFormat.ARGBHalf,RenderTextureReadWrite.Linear);var half=RT(W*2,H*2,0,1,RenderTextureFormat.ARGBHalf,RenderTextureReadWrite.Linear);var small=RT(W,H,0,1,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);var probe=RT(1,1,0,1,RenderTextureFormat.ARGBFloat,RenderTextureReadWrite.Linear);rts.AddRange(new[]{low,high,half,small,probe});
   var tm=new Material(Shader.Find("Hidden/Lanbai/SamplingTimeDiagnostic")){hideFlags=HideFlags.HideAndDontSave};owned.Add(tm);cb=new CommandBuffer{name="Record tree capture GPU time"};cb.Blit(BuiltinRenderTextureType.CameraTarget,probe,tm);cam.AddCommandBuffer(CameraEvent.AfterEverything,cb);
   var eye=new Vector3(.55f,1.7f,2.05f);var rot=Quaternion.LookRotation(new Vector3(9,6,16)-eye,Vector3.up);cam.transform.SetPositionAndRotation(eye,rot);cam.targetTexture=low;for(int z=0;z<3;z++)cam.Render();Graphics.Blit(low,small);var with=Read8(small);foreach(var r in renderers)r.enabled=false;cam.Render();Graphics.Blit(low,small);var without=Read8(small);foreach(var r in renderers)r.enabled=true;var roi0=new bool[N];for(int k=0;k<N;k++)roi0[k]=Math.Abs(L(with[k])-L(without[k]))>2;var roi=Lanbai.Test.Img.Dilate(roi0,W,H,4);if(roi.Count(x=>x)<1000)throw new Exception("Tree ROI empty/small; inspect lighting before further testing");
   var sumLegacy=new double[N];var sqLegacy=new double[N];var sumBox=new double[N];var sqBox=new double[N];var refDifference=new double[Frames];
   for(int i=0;i<Frames;i++){
    float t=i*(89f/90f)/(Frames-1);var off=new Vector3(Wave(t,.83f,.3f,2.1f,1.7f),Wave(t,.61f,2.2f,1.7f,.4f),Wave(t,.47f,1.1f,1.3f,2.9f))*.02f;var q=Quaternion.Euler(Wave(t,.53f,.2f,1.6f,2),Wave(t,.71f,.9f,1.9f,2.4f),Wave(t,.37f,1.4f,1.1f,.6f)*.5f);cam.transform.SetPositionAndRotation(eye+rot*off,rot*q);
    cam.targetTexture=low;cam.Render();var tl=ReadFloat(probe).r;Graphics.Blit(low,small);var a=Read8(small);
    cam.targetTexture=high;cam.Render();var th=ReadFloat(probe).r;Graphics.Blit(high,small);var legacy=Read8(small);Graphics.Blit(high,half);Graphics.Blit(half,small);var box=Read8(small);
    double differences=0;for(int k=0;k<N;k++){double dl=L(a[k])-L(legacy[k]),db=L(a[k])-L(box[k]);sumLegacy[k]+=dl;sqLegacy[k]+=dl*dl;sumBox[k]+=db;sqBox[k]+=db*db;if(roi[k])differences+=Math.Abs(L(legacy[k])-L(box[k]));}refDifference[i]=differences/roi.Count(x=>x);
    records.Add(D("sample",i,"synthetic_motion_t",t,"editor_time",EditorApplication.timeSinceStartup,"frame_count",Time.frameCount,"low_gpu_Time",tl,"ref_gpu_Time",th,"fixed_wind_phase_time",0,"fixed_lod",0,"eye",new[]{cam.transform.position.x,cam.transform.position.y,cam.transform.position.z},"rotation",new[]{cam.transform.rotation.x,cam.transform.rotation.y,cam.transform.rotation.z,cam.transform.rotation.w}));
    if(i==0||i==Frames/2||i==Frames-1){Lanbai.Test.Img.SavePng(a,W,H,dir+"/"+i.ToString("00")+"_low.png");Lanbai.Test.Img.SavePng(legacy,W,H,dir+"/"+i.ToString("00")+"_legacy_ref.png");Lanbai.Test.Img.SavePng(box,W,H,dir+"/"+i.ToString("00")+"_box_ref.png");}
   }
   var mask=roi.Select(x=>x?new Color32(255,255,255,255):new Color32(0,0,0,255)).ToArray();Lanbai.Test.Img.SavePng(mask,W,H,dir+"/roi.png");
   File.WriteAllText(dir+"/measurements.json",Lanbai.Test.TJson.Write(D("status","diagnostic_not_acceptance","frames",Frames,"dimensions",new[]{W,H},"low_ss",1,"reference_ss",4,"msaa",4,"fixed_LOD",0,"fixed_wind_method","Clone materials set WindFreq=FlutterFreq=0; amplitude and vertex/root phase retained. Original material assets untouched.","legacy_reference_error",Stats(sumLegacy,sqLegacy,roi),"box_reference_error",Stats(sumBox,sqBox,roi),"reference_method_difference_mean_srgb",refDifference.Average(),"samples",records,"materials",materials,"lights",lightRows,"wetness_global",Shader.GetGlobalFloat("_Udon_Wetness"),"limits","Offscreen preview scene, mesh/material copies, seven original row transforms, S1 profile, copied enabled lights. Fixed LOD0/wind and controlled environment differ from historical mixed LOD scene; cannot replace old FAIL or compare absolute values as before/after. Both references derive from the SAME high-res render. No geometry, lighting asset, threshold or official test changes.")));
  } finally {if(cam!=null){if(cb!=null){cam.RemoveCommandBuffer(CameraEvent.AfterEverything,cb);cb.Release();}cam.targetTexture=null;}EditorSceneManager.ClosePreviewScene(sc);foreach(var r in rts){if(RenderTexture.active==r)RenderTexture.active=null;r.Release();Object.DestroyImmediate(r);}foreach(var o in owned)if(o!=null)Object.DestroyImmediate(o);}
  if(active.isDirty||SceneManager.GetActiveScene()!=active)throw new Exception("Unexpected scene state changed; preserve");return dir;
 }
}
}
#endif
