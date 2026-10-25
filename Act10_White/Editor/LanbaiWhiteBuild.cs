// 蓝白 · 菜单 蓝白/Build/Act10 White：搭第 10 幕（白）的驱动（可重复运行：先删上一次搭的 Lanbai_WhiteDriver）。
// 做的事：（D-41 共用工具）建 LanbaiWhiteDriver 的 U# 程序资产、等 SDK 初始化 → 建常开的根物体 Lanbai_WhiteDriver → 挂组件 → 连场景里的 Lanbai_Overlay。
// 找不到遮罩球就报错（先跑 蓝白/Build/Overlay）。搭完跑 蓝白/Director/1 Generate Dispatcher 与 2 Wire Scene。
// 第 10 幕没有几何：白就是遮罩球 + 曝光事件（LanbaiGrade），所以根物体只有驱动本身，常开（窗口由分发层管）。
// !!! NOT COMPILED IN UNITY: Roslyn type-check only (Common/Tools~/compile_check/check_cs.sh). !!!
using System;
using UnityEditor;
using UnityEngine;
using Lanbai.Act10;

namespace Lanbai.Act10.EditorTools
{
    public static class LanbaiWhiteBuild
    {
        const string DriverName = "Lanbai_WhiteDriver", OverlayName = "Lanbai_Overlay";

        // D-41：菜单先建 U# 程序资产（脚本旁边）、等 SDK 初始化完，再搭（Common/Editor/LanbaiUdonPrograms）
        [MenuItem("蓝白/Build/Act10 White")]
        public static void BuildMenu()
        {
            Lanbai.Udon.LanbaiUdonPrograms.RunWhenReady("蓝白/Build/Act10 White", new[] { typeof(LanbaiWhiteDriver) }, Build, Lanbai.Udon.LanbaiUdonPrograms.NextToScript);
        }

        public static void Build()
        {
            Lanbai.Udon.LanbaiUdonPrograms.RequireReady("蓝白/Build/Act10 White", typeof(LanbaiWhiteDriver));
            LanbaiOverlay overlay = null;
            foreach (LanbaiOverlay o in UnityEngine.Object.FindObjectsOfType<LanbaiOverlay>(true))
                if (o != null && o.gameObject.name == OverlayName) { overlay = o; break; }
            if (overlay == null)
            {
                Debug.LogError("[Act10] no " + OverlayName + " (LanbaiOverlay) in the scene: run 蓝白/Build/Overlay first. Nothing built.");
                return;
            }

            foreach (LanbaiWhiteDriver od in UnityEngine.Object.FindObjectsOfType<LanbaiWhiteDriver>(true))
                if (od != null) Undo.DestroyObjectImmediate(od.gameObject);
            foreach (GameObject g in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
                if (g.name == DriverName) Undo.DestroyObjectImmediate(g);

            GameObject drv = new GameObject(DriverName);
            Undo.RegisterCreatedObjectUndo(drv, "蓝白 Act10 White build");
            LanbaiWhiteDriver c = AddUdon(drv);
            if (c == null)
            {
                Debug.LogError("[Act10] could not add LanbaiWhiteDriver (UdonSharp missing, or the program asset failed to compile).");
                return;
            }
            c.overlay = overlay;
            EditorUtility.SetDirty(c);
            drv.SetActive(true);                        // always on: it draws nothing outside its window
            AssetDatabase.SaveAssets();
            Debug.Log("[Act10] " + DriverName + " built, overlay = " + overlay.gameObject.name + ". Now run 蓝白/Director/1 Generate Dispatcher and 2 Wire Scene.");
        }

        static LanbaiWhiteDriver AddUdon(GameObject go)
        {
            return (LanbaiWhiteDriver)Lanbai.Udon.LanbaiUdonPrograms.AddComponent(go, typeof(LanbaiWhiteDriver));
        }
    }
}
