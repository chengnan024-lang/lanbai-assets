# R2 可穿越云：候选与技术边界

只读研究，未下载代码/资源、未导入工程、未购买、未登录VRChat。核对2026-10-25。

|候选|主来源与许可|适用结论|
|---|---|---|
|Sebastian Lague Clouds|[仓库](https://github.com/SebLague/Clouds)、[MIT](https://github.com/SebLague/Clouds/blob/master/LICENSE)，©2019 Sebastian Lague|真密度场raymarching，可参考形态/散射；源码CloudMaster用OnRenderImage + Graphics.Blit +噪声/天气生成。是相机后处理研究工程，不是可直接放入VRC的普通世界材质。未实测双眼、镜面、穿越帧率。|
|AlexStrook UnlitClouds|[仓库](https://github.com/AlexStrook/UnlitClouds)、[CC0](https://github.com/AlexStrook/UnlitClouds/blob/master/LICENSE)|作者说明顶点色+tessellation造型云；适合观察轮廓手法，**不能等同可进入的体积密度**。核心shader确有tessellate；不是本项目自动替换方案。|
|Xiexe XSVolumetrics|[仓库](https://github.com/Xiexe/XSVolumetrics)、[MIT](https://github.com/Xiexe/XSVolumetrics/blob/master/LICENSE)，©2018 Xiexe|作者的VR体积光效果，需深度缓冲避免交界硬切；可参考近场雾/过渡，不是天气云系统。作者性能描述没有当前4060实测，不能抄成预算。|
|TowelCloud|[作者说明](https://hackmd.io/@towel/cloud)|作者明确非体积渲染、不能靠近云。排除“穿云主体”候选，避免把移动天空盒当可穿越云。|

VRChat世界线索：[A Little Slice](https://vrchat.com/home/world/wrld_16887192-8200-45a4-b62c-349b2a61c501)，索引称Kyris制作、可飞行并引用UnlitClouds；官方页面本轮无法读取，**尚未核实穿越内部体积和实机效果，不列为已验证案例**。未靠第三方介绍推断性能或许可。

工程判断：蓝白需要车穿入云时的体内衰减、轮廓消失、双眼一致、镜面相机一致，以及离开云时的连续恢复。可把密度raymarching方法作为云端重做的技术参考，但没有批准改渲染管线/导入第三方包；目前云端负责人继续制作，不另开本地制作线。R2尚缺实际VRChat穿越录像可核实的案例与性能，不标完成。
