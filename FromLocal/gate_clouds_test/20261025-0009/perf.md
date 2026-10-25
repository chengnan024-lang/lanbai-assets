# 性能记录

| 机位 × 状态 | 类型 | 分辨率/视角 | 时间 | draw / batches / SetPass / 三角 | Udon ms |
|---|---|---|---|---|---|
| U7 附近，全开 | Play + ClientSim，未戴头显 | 1461×720，H90°/V52.47° | GPU/CPU 未测 | 181 / 181 / 175 / 571251，一帧 | 门/云分别未测 |
| U7，全开 | 编辑器估算 | 1920×1080；双眼估算1832×1920×2 | 桌面5.56ms；双眼10.99ms，CPU2.69ms | Recorder为0，不采信 | 未测 |
| U8fwd，全开 | 编辑器估算 | 同上 | 桌面5.18ms；双眼11.35ms，CPU2.54ms | Recorder为0，不采信 | 未测 |

完整八种机位×状态、采样范围见 ../20261025-001346/perf.json。Quality VRC High、LOD Bias 2、MSAA4、Linear、HDR FP16、Forward。估算不作为真实 VR 的预算判定。真实头显、GPU分项和Udon分项仍未测。
