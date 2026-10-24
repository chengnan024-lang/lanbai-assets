// 蓝白 · 公告板的语言开关（UdonSharp，D-31 #1）。一个按钮一个组件：Interact 时让 LanbaiPoemDriver 换语言，只对本人生效。
// !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check only. !!!
// eventName = "_LangZh" | "_LangJa" | "_LangEn"（蓝白/Fonts/Build Poem Objects 建按钮时填好）。
using UdonSharp;
using UnityEngine;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiLangButton : UdonSharpBehaviour
{
    public LanbaiPoemDriver driver;
    public string eventName = "_LangEn";

    public override void Interact()
    {
        if (driver != null) driver.SendCustomEvent(eventName);
    }
}
