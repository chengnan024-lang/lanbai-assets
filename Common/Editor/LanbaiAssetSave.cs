// ═══════════════════════════════════════════════════════════════════
//  蓝白 · 只存自己写的资产（D-50 #9，总工程师）
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check only. !!!
//
//  为什么：AssetDatabase.SaveAssets() 会把整个工程里所有“脏”的资产一起写盘。运行时 / 编辑模式的驱动改过的共享材质
//  （门内的光唇、云、触手……）在内存里是脏的，谁一调 SaveAssets 就被写进仓库同步过来的文件——本地 10-26 的
//  bus_slice（12 个材质）和 transitions_sweep（1 个）就是这样被测试工具报成“没声明的写入”。
//  规矩：搭建脚本只存自己建的、改的资产：LanbaiAssetSave.Only(obj, ...)。Unity 2021.2+ 用 AssetDatabase.SaveAssetIfDirty
//  （反射调：compile_check 的 UnityEditor 是 2021.1）；没有这个方法就只 SetDirty、不存（宁可没存，不要写别人的东西），
//  返回 false 让调用方在报告里说一声。
// ═══════════════════════════════════════════════════════════════════
#if UNITY_EDITOR
using System.Reflection;
using UnityEditor;
using Object = UnityEngine.Object;

namespace Lanbai.Udon
{
    public static class LanbaiAssetSave
    {
        static readonly MethodInfo SaveIfDirty = typeof(AssetDatabase).GetMethod("SaveAssetIfDirty", BindingFlags.Public | BindingFlags.Static,
                                                                                 null, new[] { typeof(Object) }, null);

        /// <summary>true: SaveAssetIfDirty 在（Unity 2021.2+），Only 真的存了。</summary>
        public static bool Available { get { return SaveIfDirty != null; } }

        /// <summary>标脏并只存这几个资产。返回 false = 这个 Unity 没有 SaveAssetIfDirty，只标了脏、没存。</summary>
        public static bool Only(params Object[] assets)
        {
            if (assets == null) return true;
            foreach (var a in assets)
            {
                if (a == null) continue;
                EditorUtility.SetDirty(a);
                if (SaveIfDirty != null) SaveIfDirty.Invoke(null, new object[] { a });
            }
            return SaveIfDirty != null;
        }
    }
}
#endif
