# NVIDIA Llama-Nemotron 后训练数据集完整梳理

> 来源: https://developer.nvidia.cn/blog/build-custom-reasoning-models-with-advanced-open-post-training-datasets/
> 数据集: https://huggingface.co/datasets/nvidia/Llama-Nemotron-Post-Training-Dataset
> 论文: https://arxiv.org/abs/2505.00949
> 日期: 2026-03-14

---

## 一、概览

NVIDIA 开源了 **Llama-Nemotron Post-Training Dataset v1.1**，包含约 **3300万** 合成训练样本，用于后训练（SFT + RL），提升数学、代码、推理、指令遵循等能力。

- **许可证:** CC-BY-4.0（主体），少量 ODC-BY（WildChat）/ CC-BY-SA（StackOverflow）
- **版本:** v1.1（2025-04-08 更新，新增 220万数学 + 50万代码推理数据）
- **上下文长度:** 128K

用此数据集训练的三个模型：

| 模型 | 参数量 | 基座模型 |
|------|--------|----------|
| Llama-Nemotron-Ultra | 253B | Llama-3.1-405B-Instruct（NAS 压缩） |
| Llama-Nemotron-Super | 49B | Llama-3.3-70B-Instruct（NAS 压缩） |
| Llama-Nemotron-Nano | 8B | Llama-3.1-8B-Instruct |

每个模型在各自参数量级的推理和代理式任务中均达到领先准确率。

---

## 二、数据分布

### 2.1 按类别

| 类别 | 样本数 | 子集类型 | 说明 |
|------|--------|----------|------|
| 数学 (math) | 22,066,397 | SFT | 最大部分，含 CoT 推理链 |
| 代码 (code) | 10,108,883 | SFT | 编程竞赛题 + 推理解题 |
| 科学 (science) | 708,920 | SFT | 科学推理 |
| 指令遵循 (instruction_following) | 56,339 | RL | 强化学习数据 |
| 聊天 (chat) | 39,792 | SFT | 开放对话、创意写作等 |
| 安全 (safety) | 31,426 | SFT | 安全对齐 |

### 2.2 按响应生成模型（教师模型）

| 模型 | 样本数 | 主要角色 |
|------|--------|----------|
| Qwen-2.5-Math-7B-Instruct | 19,840,970 | 数学解题主力 |
| Qwen-2.5-Coder-32B-Instruct | 8,917,167 | 代码生成主力 |
| DeepSeek-R1 | 3,934,627 | 长推理链（代码 + 数学） |
| Qwen-2.5-32B-Instruct | 2,297,175 | 数学数据管护/处理 |
| Qwen-2.5-72B-Instruct | 464,658 | 通用推理 |
| Llama-3.3-70B-Instruct | 420,021 | 聊天数据响应 |
| Mixtral-8x22B-Instruct-v0.1 | 31,426 | 安全数据 |
| Llama-3.1-Nemotron-70B-Instruct | 31,218 | 反馈/编辑 |
| Llama-3.3-Nemotron-70B-Feedback/Edit/Select | 22,644 | 反馈/选择/编辑 |

**关键设计：** 部分 prompt 包含推理开/关两种模式的响应，训练模型学会区分何时需要深度推理。

---

## 三、数据管护流水线

### 3.1 数学数据 (Math)

**Prompt 来源:** Art of Problem Solving (AoPS) 社区论坛

**处理流程：**
1. **问题提取** — LLM（Qwen2.5-32B-Instruct）从论坛帖子中识别并提取所有问题
2. **问题分类** — 分为：证明题/非证明题，多选/非多选
3. **问题转换** — 证明题→答案型题目；多选题→去掉选项变直答
4. **答案提取** — 从论坛讨论中提取最终答案（如有）
5. **基准去污** — 用 [lmsys decontaminator](https://github.com/lm-sys/llm-decontaminator) 删除与热门数学基准相似的题目
6. **解答生成** — 多模型混合生成：
   - Qwen2.5-7B-Math-Instruct
   - QwQ-32B
   - DeepSeek-R1
7. **解答验证** — 只保留：
   - 答案正确的解法（与提取答案匹配）
   - 或多数投票一致的解法（答案未知时）
   - 使用 LLM-as-judge 验证

**工具:** [NeMo-Skills](https://github.com/NVIDIA-NeMo/Skills)

### 3.2 代码数据 (Code)

**Prompt 来源:** [CodeContests](https://huggingface.co/datasets/deepmind/code_contests)（DeepMind 编程竞赛数据集）

**处理流程：**
1. **基准去污** — 删除与 HumanEval、MBPP、LiveCodeBench、BigCodeBench 相似的题目
2. **响应生成** — DeepSeek-R1 为每题生成 32-40 个响应（最大输出 16K token）
3. **验证** — 保留含完整推理链 + 语法正确代码的响应，解析代码验证语法

**工具:** [NeMo-Skills](https://github.com/NVIDIA-NeMo/Skills)

### 3.3 聊天数据 (Chat)

**Prompt 来源:**
- [WildChat](https://huggingface.co/datasets/allenai/WildChat)（真实用户交互）
- 合成生成（覆盖开放式 QA、封闭式 QA、创意写作等任务）

**处理流程：**
1. 合成提示生成时，LLM 为每个任务类型生成多样化主题/关键字
2. 多代生成响应
3. 使用 [Llama-3.1-Nemotron-70B-Reward](https://huggingface.co/nvidia/Llama-3.1-Nemotron-70B-Reward-HF) 奖励模型做拒绝采样
4. 响应生成模型：Llama-3.3-70B-Instruct + DeepSeek-R1

**工具:** [NeMo-Curator](https://github.com/NVIDIA-NeMo/Curator)（参考 [tutorial notebook](https://github.com/NVIDIA/NeMo-Curator/blob/main/tutorials/nemotron_340B_synthetic_datagen/synthetic_preference_data_generation_nemotron_4_340B.ipynb)）

---

## 四、开源 Prompt 数据来源汇总

| 来源 | 类型 | 许可证 | 用途 |
|------|------|--------|------|
| [AoPS 社区论坛](https://artofproblemsolving.com/community) | 数学竞赛题 | 公开 | 数学 SFT |
| [CodeContests (DeepMind)](https://huggingface.co/datasets/deepmind/code_contests) | 编程竞赛题 | 开源 | 代码 SFT |
| [WildChat](https://huggingface.co/datasets/allenai/WildChat) | 真实用户对话 | ODC-BY | 聊天 SFT |
| StackOverflow | 技术问答 | CC-BY-SA | 部分 prompt |
| 合成生成 | LLM 生成的 prompt | CC-BY-4.0 | 聊天/数学/代码 |

---

## 五、工具链详解

### 5.1 NeMo-Skills

- **仓库:** https://github.com/NVIDIA-NeMo/Skills
- **文档:** https://nvidia-nemo.github.io/Skills/
- **论文/模型:** OpenMathReasoning, OpenReasoning 等多个 NVIDIA 开源项目基于此构建
- **用途:** LLM 技能提升的端到端工具包——合成数据生成、数学/代码数据管护、模型训练、评测

#### 5.1.1 为什么需要它？

训练推理模型需要大量高质量合成数据，但数据生成→验证→去污→训练→评测的完整流程非常复杂。NeMo-Skills 将这些步骤封装为统一管道，**一行命令切换本地单 GPU 和万卡 Slurm 集群**。

#### 5.1.2 核心架构：三大管道

```
NeMo-Skills 架构：

┌─────────────────────────────────────────────┐
│  Generation Pipeline（合成数据生成）          │
│  · 输入 JSONL + Prompt 模板 → LLM 批量推理    │
│  · 支持多采样（num_random_seeds=32）          │
│  · 自动断点续跑 + 分块并行                    │
├─────────────────────────────────────────────┤
│  Evaluation Pipeline（模型评测）              │
│  · 30+ 基准覆盖数学/代码/科学/多语言等        │
│  · 支持符号验证 + LLM-as-judge 双重判定       │
│  · 可并行调度多个 Slurm 评测任务              │
├─────────────────────────────────────────────┤
│  Training Pipeline（模型训练）                │
│  · 集成 NeMo-RL / verl 框架                  │
│  · 支持 SFT + RL 训练                        │
└─────────────────────────────────────────────┘
```

#### 5.1.3 Generation Pipeline（合成数据生成）

这是 Nemotron 数据集构建的核心管道。

**推理后端（可无缝切换）：**

| 后端 | 说明 | 适用场景 |
|------|------|----------|
| TensorRT-LLM | NVIDIA 优化推理引擎 | 大规模生产、最高吞吐 |
| vLLM | 开源高性能推理 | 通用本地/集群 |
| sglang | 结构化生成优化 | 复杂 prompt 场景 |
| Megatron | 多节点大模型推理 | 超大参数模型 |
| OpenAI API | 外部 API 调用 | 快速原型验证 |

**关键功能：**
- **多采样生成：** `--num_random_seeds=32` 为每道题生成 32 个不同解法（高温采样）
- **自动续跑：** 中断后重新提交相同命令，自动跳过已完成部分
- **分块并行：** `--num_chunks=N` 将数据拆分到 N 个 Slurm 任务并行，完成后自动合并
- **软失败模式：** `++server.enable_soft_fail=True`，上下文超限时自动裁剪而非崩溃
- **Prompt 模板化：** YAML 格式定义 prompt，支持 few-shot、system/user 角色、变量替换

**在 Nemotron 数据集中的应用：**
```bash
# 示例：为 MATH 训练集生成 32 个合成解法
ns generate \
    --cluster=slurm \
    --server_type=trtllm \
    --model=/hf_models/Llama-3.1-405B-Instruct \
    --server_gpus=8 --server_nodes=2 \
    --num_random_seeds=32 \
    --output_dir=/workspace/synthetic-math-solutions \
    --input_file=/nemo_run/code/nemo_skills/dataset/math/train.jsonl \
    ++eval_type=hendrycks_math \
    ++prompt_config=generic/math-base
```

#### 5.1.4 数学数据管护流程（NeMo-Skills 实现）

NeMo-Skills 内置了完整的数学数据生产流水线：

```
AoPS 论坛原始帖子
    │
    ▼
问题提取（LLM 从帖子中提取题目）
    │
    ▼
问题分类（证明/非证明、多选/非多选）
    │
    ▼
问题转换（证明题→答案型，多选→直答）
    │
    ▼
答案提取（从论坛讨论中提取标准答案）
    │
    ▼
基准去污（lmsys decontaminator 排除评测集相似题）
    │
    ▼
多模型解答生成（Qwen-Math / QwQ / DeepSeek-R1）
    │
    ▼
解答验证
  ├── 符号验证：答案提取 → 与标准答案对比（精确匹配）
  └── LLM-as-judge：当标准答案不确定时，多数投票 + LLM 裁判
    │
    ▼
过滤输出（只保留正确解法）
```

**解答验证细节：**
- 从 `\boxed{}` 中提取预测答案
- 使用 [math_grader.py](https://github.com/NVIDIA-NeMo/Skills/blob/main/nemo_skills/evaluation/math_grader.py) 做符号比较
- 可选 LLM-as-judge 做更鲁棒的判定

#### 5.1.5 Evaluation Pipeline（模型评测）

支持 30+ 主流基准，覆盖 10 个领域：

| 领域 | 代表性基准 |
|------|-----------|
| 数学（自然语言） | AIME24, AIME25, HMMT Feb25 |
| 数学（形式化） | MiniF2F, ProofNet, Putnam-Bench |
| 代码 | SWE-bench, LiveCodeBench, BIRD |
| 科学 | HLE, SciCode, GPQA |
| 指令遵循 | IFBench, IFEval |
| 长上下文 | RULER, MRCR, AALCR |
| 工具调用 | BFCL v3 |
| 多语言 | MMLU-ProX, FLORES-200, WMT24PP |
| 语音/音频 | ASR-Leaderboard, MMAU-Pro |
| 视觉-语言 | MMMU-Pro |

**评测特色：**
- 每个基准都可并行到多个 Slurm 任务
- 支持自托管 LLM judge
- 可自定义 prompt 和基准配置

#### 5.1.6 已发布的数据集和模型（基于 NeMo-Skills 构建）

| 时间 | 项目 | 说明 |
|------|------|------|
| 2025-07 | OpenReasoning | 数学/代码/科学 SOTA 开源推理模型 |
| 2025-04 | OpenMathReasoning | 306K 题目 + 320万 CoT + 170万 TIR 解法 |
| 2025-04 | Llama-Nemotron 数据集 | 3300万样本后训练数据集（本文档） |
| 2024-10 | OpenMathInstruct-2 | 1400万数学指令调优数据 |
| 2025-12 | Nemotron-Math-v2 / Math-Proofs-v1 | 形式化证明数据 |

### 5.2 NeMo-Curator

- **仓库:** https://github.com/NVIDIA-NeMo/Curator
- **文档:** https://docs.nvidia.com/nemo/curator/latest/
- **用途:** GPU 加速的多模态数据管护工具包，覆盖文本/图像/视频/音频

#### 5.2.1 为什么需要它？

训练数据的质量直接决定模型性能。但原始数据（Common Crawl、用户对话等）充满噪声、重复和低质内容。传统 CPU 方案处理 TB 级数据需要数天，NeMo-Curator 用 **NVIDIA RAPIDS（cuDF/cuML/cuGraph）+ Ray** 实现 GPU 加速，在相同硬件上快 16 倍。

在 Nemotron 数据集中，NeMo-Curator 主要用于**聊天数据管护**——从 WildChat 和合成数据中筛选高质量 prompt。

#### 5.2.2 核心架构

```
NeMo-Curator 架构：

              ┌──────────────────────┐
              │     Data Loading     │
              │  Common Crawl / Wiki │
              │  ArXiv / Custom / S3 │
              └──────────┬───────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │   Text   │   │  Image   │   │  Video   │   + Audio
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │               │               │
   ┌────▼─────┐   ┌────▼─────┐   ┌────▼─────┐
   │ Cleaning  │   │  CLIP    │   │TransNetV2│
   │ LangID    │   │ Embedding│   │ Scene    │
   │ Heuristic │   │ Aesthetic│   │ Detection│
   │ Filtering │   │ NSFW     │   │ Motion   │
   │ Classifier│   │ Filter   │   │ Filter   │
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │               │               │
   ┌────▼─────────────────────────────────▼────┐
   │          Deduplication Layer               │
   │  Exact / Fuzzy(MinHash LSH) / Semantic    │
   │  K-means Clustering / Pairwise Similarity │
   └───────────────────────────────────────────┘
        │
        ▼
   Curated Dataset
```

#### 5.2.3 四大模态能力详解

**📝 文本管护**

| 功能 | 实现方式 | 说明 |
|------|----------|------|
| 数据加载 | Common Crawl / Wikipedia / ArXiv / 自定义 | 支持多种公开语料 |
| 文本清洗 | 正则 + 启发式规则 | 去除 HTML、特殊字符、乱码 |
| 语言检测 | fastText 模型 | 多语言识别 |
| 质量过滤 | 30+ 启发式过滤器 + fastText 分类 + GPU 分类器 | 过滤低质、色情、有害内容 |
| 精确去重 | 哈希匹配 | 完全相同的文档 |
| 模糊去重 | MinHash LSH | 近似重复文档（最常用） |
| 语义去重 | GPU 加速嵌入 + 余弦相似度 | 意义相近但表述不同的文档 |

**🖼️ 图像管护**

| 功能 | 实现方式 |
|------|----------|
| 数据加载 | WebDataset 格式，支持大规模图文对 |
| 嵌入生成 | CLIP embedding 用于语义分析 |
| 美学评分 | 自动评估图像质量 |
| NSFW 检测 | 过滤不安全内容 |
| 去重 | 基于嵌入的相似度去重 |

**🎬 视频管护**

| 功能 | 实现方式 |
|------|----------|
| 数据加载 | 本地路径 / S3 / HTTP(S) |
| 片段切割 | 固定步长 + TransNetV2 场景检测 |
| GPU 编码 | H.264 硬件加速 |
| 运动过滤 | 过滤静态/低运动片段 |
| 美学过滤 | 视觉质量评估 |
| 嵌入 | Cosmos-Embed1 片段级嵌入 |
| 去重 | K-means 聚类 + 成对相似度 |

**🔊 音频管护**

| 功能 | 实现方式 |
|------|----------|
| 数据加载 | 本地文件 / 自定义 manifest / FLEURS 等公开数据集 |
| ASR 转写 | NeMo 预训练 ASR 模型自动转写 |
| 质量评估 | WER 计算 + 时长分析 + 质量过滤 |
| 多模态集成 | 与文本管护流程无缝衔接 |

#### 5.2.4 性能基准

| 指标 | 数据 |
|------|------|
| 模糊去重加速 | **16x**（8TB RedPajama v2 / 1.78 万亿 token） |
| TCO 降低 | **40%**（vs CPU 方案） |
| 扩展性 | 近线性（1→4 H100 80GB 节点：2.05h → 0.50h） |

**消融实验验证：** 使用 357M 参数 GPT 模型在 curated Common Crawl 上训练，经过文本清洗→去重→质量过滤各阶段，零样本下游任务性能逐步提升。

#### 5.2.5 在 Nemotron 数据集中的应用

NeMo-Curator 在 Llama-Nemotron 数据集构建中主要负责**聊天数据管护**：

1. **Prompt 管护** — 从 WildChat 和合成数据中筛选高质量 prompt
2. **偏好数据生成** — 参考 [synthetic preference data generation tutorial](https://github.com/NVIDIA/NeMo-Curator/blob/main/tutorials/nemotron_340B_synthetic_datagen/synthetic_preference_data_generation_nemotron_4_340B.ipynb)
3. **拒绝采样配合** — 为 Llama-3.1-Nemotron-70B-Reward 奖励模型提供候选响应的筛选框架

#### 5.2.6 底层技术栈

| 组件 | 用途 |
|------|------|
| NVIDIA RAPIDS cuDF | GPU 加速数据帧操作 |
| NVIDIA RAPIDS cuML | GPU 加速机器学习（聚类、降维） |
| NVIDIA RAPIDS cuGraph | GPU 加速图分析（去重中的连通分量） |
| Ray | 分布式计算调度（多节点扩展） |
| fastText | 语言检测 + 质量分类 |
| CLIP | 图像嵌入 + 语义分析 |
| TransNetV2 | 视频场景检测 |
| Cosmos-Embed1 | 视频片段嵌入 |

### 5.3 lmsys LLM Decontaminator（基准去污工具）

- **仓库:** https://github.com/lm-sys/llm-decontaminator
- **论文:** [Rethinking Benchmark and Contamination for Language Models with Rephrased Samples](https://arxiv.org/abs/2311.04850) (LMSYS, 2023)
- **用途:** 检测训练数据中与评测基准语义相似的"改写污染"样本，并从训练集中移除

#### 5.3.1 为什么需要它？

传统去污方法用 **n-gram 字符串匹配**（如 GPT-4 技术报告中的做法），但这种方法无法检测：
- 改写/释义（paraphrasing）
- 翻译后的等价题目
- 变量名/数字替换后的同题

论文证明：**一个 13B 模型只要训练了改写后的基准数据，就能在 MMLU 上达到接近 GPT-4 的分数**——这说明 n-gram 去污完全不够。

#### 5.3.2 核心原理：两阶段检测

```
Stage 1: Embedding 召回（粗筛）
  训练集 ──→ SentenceTransformer 编码 ──→ 向量
  测试集 ──→ SentenceTransformer 编码 ──→ 向量
  ──→ 余弦相似度 Top-K 匹配 ──→ 候选对

Stage 2: LLM 判定（精筛）
  候选对 ──→ GPT-4 判断 "这两道题是否是同一个问题？" ──→ True/False
```

**Stage 1 — 向量召回**
- 使用 `multi-qa-MiniLM-L6-cos-v1`（轻量 SentenceTransformer）
- 对训练集和测试集分别做 embedding
- 计算余弦相似度矩阵，取每个测试样本的 Top-K 最相似训练样本
- 目的：从百万级训练集中快速筛出小量候选对（降低 LLM 调用量）

**Stage 2 — LLM 精确判定**
- 将候选对送给 GPT-4（默认），用专门的 prompt 判断两个样本是否为同一问题
- 针对不同数据类型有定制化 prompt：

| 数据类型 | Prompt 策略 |
|----------|-------------|
| `code` | 判断两段程序是否解决同一个问题（忽略实现方式，只看目标/输入/输出） |
| `math` | 判断两道数学题是否相同（忽略姓名和语序变化，如果 prompt 相似且答案相同则视为同题） |
| `number_substitution` | 更严格的数学比对（额外忽略数字差异） |
| `knowledge` | 判断两道知识题是否相同（忽略姓名和语序） |

- LLM 只回答 "True" 或 "False"，temperature=0.3，最多重试 30 次

#### 5.3.3 实际检出率（论文数据）

| 训练集 | 基准 | 训练集大小 | 改写污染数 | 污染率 |
|--------|------|-----------|-----------|--------|
| The Stack (4G) | HumanEval | 500K | 31 | **18.9%** |
| StarCoder-Data (2.4G) | HumanEval | 500K | 26 | **15.9%** |
| CodeExercise-Python | HumanEval | 27K | 26 | **15.9%** |
| CodeAlpaca | HumanEval | 20K | 21 | **12.8%** |
| RedPajama-1T (16G) | HumanEval | 1.6M | 14 | **8.5%** |
| MATHInstruct | MATH Test | 262K | 769 | **15.4%** |
| MATH Train | MATH Test | 7.5K | 79 | **1.6%** |
| FLAN CoT | MMLU | 184K | 76 | 0.5% |
| WizardLM-Evol-Instruct | MMLU | 143K | 75 | 0.5% |

**关键发现：** 即使是 GPT-3.5/4 合成的数据集也存在无意的基准污染风险。

#### 5.3.4 在 Nemotron 数据集中的应用

NVIDIA 在构建 Llama-Nemotron 数据集时，对以下基准做了去污：
- **数学:** 热门数学基准（MATH 等）
- **代码:** HumanEval、MBPP、LiveCodeBench、BigCodeBench

去污流程集成在 NeMo-Skills 管道中，确保训练数据不包含评测集的改写版本。

#### 5.3.5 使用方式

```bash
# 安装
git clone https://github.com/lm-sys/llm-decontaminator.git
cd llm-decontaminator
pip install -r requirement.txt

# 运行（需要 OPENAI_API_KEY）
export OPENAI_API_KEY=sk-xxx
python3 main.py \
    --train_path ./data/train/your_data.jsonl \
    --test_path ./data/test/HumanEval.jsonl \
    --output_path ./data/database/output.jsonl \
    --data-type code \
    --top_k 1
```

输入格式：每行一个 `{"text": "..."}` 的 JSONL 文件。

### 5.4 其他工具

| 工具 | 用途 | 地址 |
|------|------|------|
| Llama-3.1-Nemotron-70B-Reward | 奖励模型，用于聊天数据拒绝采样 | https://huggingface.co/nvidia/Llama-3.1-Nemotron-70B-Reward-HF |
| NeMo Framework | 端到端模型训练框架 | https://github.com/NVIDIA/NeMo |
| NeMo Customizer | 模型微调微服务 | https://developer.nvidia.com/nemo-microservices |
| NeMo-RL | NVIDIA 强化学习训练库 | https://github.com/NVIDIA-NeMo/RL |
| verl | 字节跳动开源 RL 训练框架 | https://github.com/volcengine/verl |

---

## 六、总结

这是目前开源社区最完整的后训练数据集之一。核心价值：

1. **规模大:** 3300万样本，覆盖数学/代码/科学/聊天/安全/指令遵循
2. **全流程开放:** 不只给数据，还公开了 prompt 采集→管护→生成→验证→去污的完整方法论
3. **工具链完整:** NeMo-Skills + NeMo-Curator 可直接复用整套流水线
4. **教师模型多样:** 9个不同模型生成响应，增加数据多样性
5. **推理模式训练:** 包含开/关推理的响应对，教模型何时该深度思考
6. **严格去污:** 针对所有主流基准做了去污处理，确保评测公平性
