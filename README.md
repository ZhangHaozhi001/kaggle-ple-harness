# PLE Agent Harness — Kaggle「Physical-Engineering's Last Exam」

An agent harness for the Kaggle competition **Google – Agent Harness on
Physical-Engineering's Last Exam** ($400,000, top 3 only). The event's scoring
is unforgiving: **if any required output of a problem is missing, or carries a
missing/wrong unit, that problem scores zero.** This harness is built around
that rule — strict spec loading, a unit-aware validator, a validate-and-repair
agent loop, and a local scorer that mirrors the zero-rule exactly.

中文说明见下方「中文」一节。

## Architecture

```
harness/
  units.py        unit registry: dimensions, SI conversion, degC/degF offsets
  task_loader.py  strict task-spec loading (rejects ambiguous specs loudly)
  validator.py    answer validation + scoring (missing spec/unit => 0)
  model.py        ModelClient interface | MockModelClient (local, $0)
                  | VertexModelClient stub for google-cloud/claude-opus-5-5
  agent.py        solve -> validate -> repair-with-feedback loop (bounded)
  scorer.py       local scorer + pre-submission self-check + checkpoint gate
  run.py          CLI: `score` and `check`
sample_tasks/     7 SELF-MADE practice tasks (NOT official problems)
tests/            negative-path checks for the zero-score rules
```

Data flow: `task JSON -> loader (spec gate) -> agent loop (model + validator)
-> scorer (0/1 per task, mean) `. The mean over a dev subset is the number the
project's stop-loss gate is judged on.

## Run it (mock model, zero cost, stdlib only)

```bash
python3 -m harness.run score --tasks sample_tasks --out results-mock.json
python3 tests/run_checks.py
```

Expected: 7 tasks, mean score 1.0 under the mock (the mock solves the
self-made samples with small rule-based physics solvers and answers in SI
base units; the validator converts into the required units — the same
discipline the real model must follow).

Pre-submission self-check (every answer structurally complete, or it would
score zero):

```bash
python3 -m harness.run check --tasks <task_dir> --answers <answers_dir>
```

## How this maps to the official two-stage flow

| Official stage | This repo |
|---|---|
| Stage 1: ≤2,000-word writeup + repo → Top 100 | This repository + the writeup (drafted in a later segment); the prompt contract in `model.build_prompt` and the zero-rule design are the writeup's core claims |
| Stage 2: 56 hidden tasks, strict spec/unit scoring | `agent.py` loop + `validator.py` zero-rule; target model `google-cloud/claude-opus-5-5` plugs into `model.py` without touching the loop |
| Dev subset for iteration | `sample_tasks/` now (self-made); official dev set drops into the same JSON format via an adapter once access is granted |

## Project gates (from PLAN.md)

- **2026-12-06 checkpoint:** dev-subset mean score **< 0.20 → stop the project**.
- Total effort cap ≈ 30 h; local budget target $0 (cap $100).
- Final deadline **2027-01-06 07:59 CST**; internal submission target 2027-01-04.

## User-only steps (seams — everything else is automated)

1. **Kaggle**: open the competition page and click **Join / accept the rules**.
2. **Hugging Face**: register, request access to the gated dev dataset, and
   hand `HF_TOKEN` over via the Secure Vault.
3. **Final submission**: the user personally clicks **Submit** by 2027-01-04.

The real-model client refuses to run until these are done and it is
explicitly enabled (`PLE_MODEL_ENABLED=1`), so this skeleton cannot incur
API cost.

---

## 中文

这是 Kaggle「Physical-Engineering's Last Exam」（奖金 $40 万、仅前 3 名）的
agent harness 骨架。该赛计分极严：**任一题漏掉任一要求的输出项、或单位缺失/
错误，该题直接 0 分**——整套设计都围着这条规则转：

- **任务加载**（`task_loader.py`）：题面规格严格校验，规格写得含糊的题在加载期
  就报错，绝不让它蒙混进 agent。
- **单位引擎**（`units.py`）：量纲 + SI 换算 + 摄氏/华氏偏移（卡诺效率题的经典坑）。
- **校验器**（`validator.py`）：逐项核对输出是否齐全、单位量纲是否对、数值是否
  在容差内；提交前自检就靠它。
- **Agent 循环**（`agent.py`）：模型作答 → 校验 → 不合格带着具体问题反馈重试
  （有上限），不合格绝不静默放行。
- **本地评分器**（`scorer.py`）：与官方同口径的 0/1 计分和平均分；**2026-12-06
  检查点：开发子集平均分 < 0.20 就停掉整个项目**（止损线）。
- **模型层**（`model.py`）：接口抽象 + 本地替身（零费用）；真模型
  `google-cloud/claude-opus-5-5` 是桩，未显式启用前拒绝运行，不可能误花钱。

`sample_tasks/` 里是 **7 道自备样例题（非官方题目）**，仅供本地调试，替身模型下
端到端跑通、平均分 1.0；负向用例（缺项/缺单位/量纲错/超容差/摄氏坑）在
`tests/run_checks.py`，全过。

运行（纯标准库、零依赖）：

```bash
python3 -m harness.run score --tasks sample_tasks
python3 tests/run_checks.py
```

**需要用户本人的三步**（其余全自动）：① Kaggle 点 Join 接受规则；② 注册
Hugging Face、申请 gated 开发集权限、经保险柜交 HF_TOKEN；③ 2027-01-04 前
本人点最终 Submit。计划与止损线见 `PLAN.md`，复检记录见 `BUILD-REPORT.md`。
