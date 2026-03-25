# AutoResearch 生态调研：AI 自主研究/优化循环

> 日期: 2026-03-26
> 来源: GitHub 搜索 + 各项目 README

---

## 一、概览

**AutoResearch** 不是一个单一项目，而是围绕 Karpathy 2026 年 3 月发起的同名项目衍生出的一整个生态。核心理念极其简洁：

> **给 AI Agent 一个目标指标 + 一个固定时间预算 → Agent 自主修改代码 → 跑实验 → 保留改进 / 回滚退化 → 循环。你去睡觉，醒来看结果。**

当前生态按方向可分为三类：

| 方向 | 代表项目 | 星标 | 做什么 |
|------|---------|------|--------|
| **ML 训练优化** | karpathy/autoresearch | 55.8k | 自主优化单 GPU 上的 LLM 训练代码 |
| **论文自动生成** | aiming-lab/AutoResearchClaw | 8.7k | 从 idea 到完整学术论文的 23 阶段全自动 pipeline |
| **通用优化循环** | davebcn87/pi-autoresearch | 2.9k | 把 autoresearch 循环做成 pi 编辑器的通用扩展 |
| **通用优化循环** | uditgoenka/autoresearch | 2.3k | 把 autoresearch 循环做成 Claude Code 的通用 Skill |

---

## 二、Karpathy/autoresearch — 起源项目

### 2.1 定位

让 AI Agent 在**单 GPU 上自主做 LLM 训练研究**。Agent 修改训练代码 → 训练 5 分钟 → 看 val_bpb 是否降低 → 保留或丢弃 → 循环。

### 2.2 核心设计

```
只有三个文件：

prepare.py  — 固定不变：数据下载、BPE 分词器训练、数据加载、评估工具
train.py    — Agent 唯一可修改的文件：GPT 模型 + 优化器 (Muon+AdamW) + 训练循环
program.md  — 人类编写的 Agent 指令：你来编程这个 Markdown

核心约束：
- 固定 5 分钟训练时间预算（wall clock）
- 唯一指标：val_bpb（validation bits per byte，越低越好）
- 与词表大小无关，架构变更可公平比较
```

### 2.3 运行方式

```bash
# 1. 安装
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# 2. 准备数据
uv run prepare.py

# 3. 手动验证一次
uv run train.py

# 4. 自主模式：启动 Claude/Codex，指向 program.md
# Agent 自动循环：修改 train.py → 训练 → 评估 → 保留/回滚
```

### 2.4 关键设计哲学

| 设计 | 说明 |
|------|------|
| **单文件可改** | Agent 只改 train.py，scope 可控，diff 可审 |
| **固定时间预算** | 5 分钟 = 实验可比较 = 12 次/小时 = 100 次/一夜 |
| **平台自适应** | 同一时间预算，不同 GPU 自动找到该平台的最优配置 |
| **人编 program.md** | "你不写 Python，你写给 Agent 的 Markdown"——元编程 |
| **自包含** | 无外部依赖，无分布式，无复杂配置，一个 GPU 一个文件一个指标 |

### 2.5 社区 Fork

| Fork | 平台 | 说明 |
|------|------|------|
| autoresearch-mlx | Apple Silicon (MLX) | 无 PyTorch，原生 MLX |
| autoresearch-macos | macOS | Mac 适配 |
| autoresearch-win-rtx | Windows | Windows RTX 适配 |
| autoresearch (andyluo7) | AMD | AMD GPU 支持 |

### 2.6 小机器调优建议

Karpathy 给出了在小 GPU / Mac 上的调优方向：

- 用低熵数据集（TinyStories）
- 降低 vocab_size（从 8192 → 1024 甚至 256 字节级）
- 降低 MAX_SEQ_LEN（→ 256）
- 降低 DEPTH（8 → 4）
- 只用 "L" 注意力模式（不用 "SSSL" 交替带状注意力）
- 降低 TOTAL_BATCH_SIZE（→ 2^14）

---

## 三、AutoResearchClaw — 论文自动生成

### 3.1 定位

**从一个 idea 到完整学术论文的全自动 23 阶段 Pipeline。** 不是辅助写作，而是完全自主：文献检索（真实引用）→ 假设生成 → 实验设计 → 代码编写 → 沙箱执行 → 结果分析 → 论文撰写 → 同行评审 → LaTeX 输出。

### 3.2 安装与运行

```bash
pip install -e . && researchclaw setup && researchclaw init
researchclaw run --topic "Your research idea here" --auto-approve
```

或通过 OpenClaw 直接对话："Research [topic]"。

### 3.3 产出物

| 文件 | 内容 |
|------|------|
| paper_draft.md | 完整论文（Introduction → Related Work → Method → Experiments → Results → Conclusion） |
| paper.tex | NeurIPS/ICML/ICLR 模板的 LaTeX |
| references.bib | 真实 BibTeX（OpenAlex + Semantic Scholar + arXiv） |
| verification_report.json | 4 层引用验证（arXiv / CrossRef / DataCite / LLM） |
| experiment runs/ | 实验代码 + 沙箱结果 + JSON 指标 |
| charts/ | 自动生成的对比图（含 error bars 和置信区间） |
| reviews.md | 多 Agent 同行评审 |
| evolution/ | 自学习经验提取 |

### 3.4 核心能力

| 能力 | 机制 |
|------|------|
| **PIVOT / REFINE 循环** | Stage 15 自主决定：PROCEED / REFINE（调参）/ PIVOT（换方向），产物自动版本管理 |
| **多 Agent 辩论** | 假设生成、结果分析、同行评审都用多视角结构化辩论 |
| **自学习** | 每次运行提取经验（决策理由、运行时警告、指标异常），30 天衰减，未来运行复用 |
| **知识库** | 每次运行构建 6 类结构化 KB（决策、实验、发现、文献、问题、评审） |
| **Sentinel 看门狗** | 后台质量监控：NaN/Inf 检测、论文-证据一致性、引用相关性评分、反捏造防护 |
| **反捏造系统** | VerifiedRegistry + 实验诊断修复循环 |
| **质量审计** | 4 轮论文质量审计：AI-slop 检测、7 维评审评分、NeurIPS checklist |

### 3.5 集成生态

**LLM 后端（ACP 兼容）：**

| Agent | 命令 |
|-------|------|
| Claude Code | `claude` |
| Codex CLI | `codex` |
| Copilot CLI | `gh` |
| Gemini CLI | `gemini` |
| OpenCode | `opencode` |
| Kimi CLI | `kimi` |

**消息平台（通过 OpenClaw Bridge）：** Discord / Telegram / 飞书 / WeChat

**OpenClaw Bridge 可选能力：**
- `use_cron` — 定时研究任务
- `use_message` — 进度通知
- `use_memory` — 跨 session 知识持久化
- `use_sessions_spawn` — 并发子 session
- `use_web_fetch` — 文献综述时在线搜索
- `use_browser` — 基于浏览器的论文采集

### 3.6 版本历史

| 版本 | 日期 | 关键更新 |
|------|------|---------|
| v0.1.0 | 2026-03-15 | 首发：23 阶段全自动研究 pipeline |
| v0.2.0 | 2026-03-16 | 多 Agent 子系统、Docker 沙箱、4 轮论文审计 |
| v0.3.0 | 2026-03-17 | MetaClaw 集成：跨运行学习，+18.3% 鲁棒性 |
| v0.3.1 | 2026-03-18 | OpenCode Beast Mode + 社区贡献 |
| v0.3.2 | 2026-03-22 | 跨平台 ACP 支持 + 消息平台桥接 + 100+ 修复 |

---

## 四、pi-autoresearch — 通用优化循环（pi 编辑器）

### 4.1 定位

将 autoresearch 的"修改 → 验证 → 保留/回滚 → 循环"做成 pi 编辑器的**通用扩展**，不限于 ML——测试速度、bundle 大小、Lighthouse 分数、构建时间都行。

### 4.2 核心设计

```
扩展提供 3 个工具：
  init_experiment  — 配置：名称、指标、单位、方向
  run_experiment   — 执行命令、计时、捕获输出
  log_experiment   — 记录结果、自动 git commit、更新仪表板

两个持久化文件：
  autoresearch.md    — 会话文档：目标、已尝试方案、死胡同、关键成果
  autoresearch.jsonl — 每次实验的追加日志（指标、状态、commit、描述）
```

### 4.3 适用场景示例

| 场景 | 指标 | 命令 |
|------|------|------|
| 测试速度 | seconds ↓ | `pnpm test` |
| Bundle 大小 | KB ↓ | `pnpm build && du -sb dist` |
| LLM 训练 | val_bpb ↓ | `uv run train.py` |
| 构建速度 | seconds ↓ | `pnpm build` |
| Lighthouse | perf score ↑ | `lighthouse http://localhost:3000 --output=json` |

### 4.4 置信度评分

3+ 实验后自动计算置信度 = |best_improvement| / MAD（中位绝对偏差）。区分真实增益 vs 噪声：

| 置信度 | 含义 |
|--------|------|
| ≥ 2.0× 🟢 | 改进大概率是真实的 |
| 1.0–2.0× 🟡 | 高于噪声但不确定 |
| < 1.0× 🔴 | 在噪声范围内，需要重跑确认 |

---

## 五、Claude Autoresearch Skill — 通用优化循环（Claude Code）

### 5.1 定位

将 autoresearch 理念封装成 **Claude Code 的 Skill**，适用于任何有可测量指标的领域——不仅 ML，还包括代码优化、内容、营销、安全审计等。

### 5.2 核心循环

```
LOOP (FOREVER or N times):
  1. Review 当前状态 + git 历史 + 结果日志
  2. 选择下一个修改（基于过去成功/失败/未尝试）
  3. 做一个聚焦修改
  4. Git commit（验证前）
  5. 跑机械验证（测试/benchmark/分数）
  6. 改进 → 保留；退化 → git revert；崩溃 → 修复或跳过
  7. 记录结果
  8. 重复。永不停止直到中断
```

### 5.3 可用命令

| 命令 | 功能 |
|------|------|
| `/autoresearch` | 启动自主优化循环（无限制） |
| `/autoresearch:plan` | 交互向导：设定目标/范围/指标/验证 |
| `/autoresearch:security` | 自主 STRIDE + OWASP + 红队安全审计 |
| `/autoresearch:ship` | 通用交付工作流 |
| `/autoresearch:debug` | 自主 bug 狩猎循环 |
| `/autoresearch:fix` | 自主修复循环 |
| `/autoresearch:learn` | 自主文档生成引擎 |
| `/autoresearch:predict` | 多角色预测 |

### 5.4 八条核心规则

1. **循环直到完成** — 无界：永远。有界：N 次后总结
2. **先读后写** — 修改前理解完整上下文
3. **每次一个修改** — 原子操作，坏了知道是谁
4. **只做机械验证** — 不靠主观"看起来不错"，用数字说话
5. **自动回滚** — 失败改动立即 revert
6. **简洁为王** — 同等结果 + 更少代码 = 保留
7. **Git 即记忆** — `experiment:` 前缀 commit，revert 保留历史
8. **卡住时更努力想** — 重读、组合近似成功、尝试激进方案

---

## 六、横向对比

| 维度 | karpathy/autoresearch | AutoResearchClaw | pi-autoresearch | Claude Autoresearch |
|------|----------------------|-----------------|----------------|-------------------|
| **目标** | ML 训练优化 | 学术论文生成 | 通用指标优化 | 通用指标优化 |
| **Agent** | 任意（Claude/Codex/…） | 内置 + ACP 兼容 | pi 编辑器内 | Claude Code |
| **自主程度** | 高（修改 → 训练 → 评估） | 极高（23 阶段端到端） | 高（修改 → 验证 → 保留/回滚） | 高（修改 → 验证 → 保留/回滚） |
| **适用领域** | 仅 ML 训练 | 学术研究（任何领域） | 任何可量化目标 | 任何可量化目标 |
| **验证方式** | val_bpb | 多轮审计 + 同行评审 | 用户自定义命令 | 用户自定义命令 |
| **持久化** | Git commits | 知识库 + 经验提取 | jsonl + md | Git + TSV |
| **平台** | 单 GPU (NVIDIA) | Docker 沙箱 / 本地 | pi 编辑器 | Claude Code |
| **语言** | Python | Python | TypeScript | Shell (Skill) |
| **星标** | 55.8k | 8.7k | 2.9k | 2.3k |

---

## 七、核心洞察

### 7.1 Karpathy 的范式创新

Karpathy 的原始 autoresearch 提出了一个极其简洁但深刻的范式：

> **你不写代码，你写给 Agent 的 Markdown。Agent 写代码。**

`program.md` 是真正的"研究组织代码"——人类编程的对象从 Python 变成了 Agent 的指令文件。这是一种**元编程范式转换**。

### 7.2 通用化方向

从 Karpathy 的 ML 专用到 pi-autoresearch / Claude Autoresearch 的通用化，核心抽象是：

```
任何问题 = 一个指标 + 一个约束 + 一个循环

指标：你要优化什么数字（val_bpb / 测试时间 / bundle 大小 / Lighthouse 分数）
约束：Agent 能改什么文件，不能改什么
循环：修改 → 验证 → 保留或回滚 → 重复
```

### 7.3 AutoResearchClaw 的野心

AutoResearchClaw 走的是完全不同的方向——不是优化一个指标，而是**自动完成整个研究过程**。从 idea 到论文的 23 个阶段，包括文献检索（用真实 API，不是捏造）、实验设计、代码编写、沙箱执行、结果分析、论文撰写、同行评审。

这比优化循环激进得多，但也更脆弱——依赖大量 LLM 调用的可靠性。

### 7.4 与现有工具的关系

| 现有工具 | autoresearch 生态的关系 |
|---------|---------------------|
| GitHub Copilot | autoresearch 可以用 Copilot CLI 作为 Agent 后端 |
| Claude Code | Claude Autoresearch Skill 直接运行在 Claude Code 中 |
| OpenClaw | AutoResearchClaw 是 OpenClaw 兼容服务 |
| Codex CLI | 可作为 ACP 后端 |
| vLLM / SGLang | 不相关（autoresearch 是研究流程层，不是推理引擎） |

---

## 八、总结

1. **Karpathy 的 autoresearch 是 2026 年 3 月最热的 AI 开源项目之一**（55.8k 星标），核心创新不是代码而是范式——人类写 Markdown 给 Agent，Agent 写代码做研究
2. **生态迅速分化为三个方向**：ML 训练优化（原版）、通用优化循环（pi/Claude 版）、论文自动生成（AutoResearchClaw）
3. **通用化的核心抽象**：任何问题 = 一个指标 + 一个约束 + 一个循环，这个抽象足够简洁且强大
4. **AutoResearchClaw 最激进**：23 阶段端到端论文生成，集成反捏造、多 Agent 评审、自学习，但可靠性仍是挑战
5. **program.md 是元编程的新形态**："编程程序员的程序"——Agent 指令文件成为人类真正编写和迭代的对象
