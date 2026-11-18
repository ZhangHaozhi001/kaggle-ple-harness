# BUILD-REPORT — 第一段（骨架）复检记录

日期：2026-11-18（CST）。范围：harness 骨架 + 自备样例题 + 本地评分，零 API 费用、未注册、未 Join、未提交。

## 完成范围

- `harness/units.py`：单位注册表（量纲、SI 换算、°C/°F 偏移、复合量纲如 W/m²、m³/s、m⁴）。
- `harness/task_loader.py`：题面规格严格加载——缺字段、输出缺单位、单位不可解析、参考答案对不上要求输出，一律在加载期报错。
- `harness/validator.py`：逐项核对（缺输出 / 缺单位 / 量纲错 → 该题 0 分）+ 容差评分（先换算到要求单位再比）。
- `harness/model.py`：`ModelClient` 接口 + `MockModelClient`（7 个规则求解器，零费用）+ `VertexModelClient` 桩（目标模型 `google-cloud/claude-opus-5-5`；未显式启用 `PLE_MODEL_ENABLED=1` 前拒绝运行）+ 正式 prompt 契约与回复解析。
- `harness/agent.py`：作答 → 校验 → 带问题反馈重试（上限 3 次）的执行循环。
- `harness/scorer.py`：本地评分（0/1 + 平均分 + 0.20 检查点闸门）与提交前自检 `check`。
- `sample_tasks/`：7 道自备样例题（`source: "self-made"`，非官方）：梁挠度、管道压降、导热、卡诺效率（摄氏坑）、抛体、RC 电路（毫秒坑）、静水压力。
- `tests/run_checks.py`：10 项负向/正向检查。

## 复检结果（干净 venv、纯标准库重跑）

| 检查项 | 结果 |
|---|---|
| 端到端评分（mock，7 题） | ✅ mean = 1.0，7/7 全过，`passes_checkpoint_gate = true` |
| 负向用例（缺输出→0、缺单位→0、量纲错→0、超容差→0、摄氏坑→0、坏规格被拒、跨量纲换算抛错等 10 项） | ✅ 0 failure |
| 提交前自检 CLI（`check`） | ✅ 全 ok（答案文件由 mock 现场生成） |
| 真模型桩拒绝运行 | ✅ 退出码 2 + 明确提示，不抛堆栈、不产生任何 API 调用 |
| 依赖 | ✅ 仅 Python 标准库，venv 无任何第三方包可跑通 |

复检中发现并修复的问题：① 热流密度单位最初误用 W（量纲错），已新增 `power_flux` 量纲与 `W/m^2`；② 管道流量单位 `m^3` 应为流量量纲，已新增 `volume_flow` 与 `m^3/s`；③ 二阶矩 `m^4` 未注册导致梁题输入换算会抛错，已补注册；④ 真模型拒绝时原本抛堆栈，已改为干净报错。

## 未做（按计划属下一段，不在本轮）

- 官方 dev 数据集适配器（等用户 Join + HF gated 权限）。
- 真模型接通冒烟（等用户步 + 显式启用）。
- Stage 1 writeup 初稿。

## 12-06 检查点前的剩余工作

1. 用户三步：Kaggle Join、HF 注册+申请开发集权限+交 HF_TOKEN、（2027-01-04 前）最终 Submit——前两步需在下一段开工前完成。
2. 官方 dev 集到位后写格式适配器，用官方子集跑第一次真实评分，对照 0.20 止损线出结论。
3. 真模型冒烟一次，核对成本/限额。
4. Writeup 框架（≤2,000 词）。
