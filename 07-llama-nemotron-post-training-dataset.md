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
- **用途:** 数学/代码数据管护、解答生成与验证、模型评测
- **核心能力:**
  - 灵活 LLM 推理：支持 TensorRT-LLM / vLLM / sglang / Megatron
  - 从单 GPU 到上万 GPU Slurm 集群无缝扩展
  - 评测覆盖广泛：
    - 数学（自然语言）：AIME24/25, HMMT
    - 数学（形式化）：MiniF2F, ProofNet, Putnam-Bench
    - 代码：SWE-bench, LiveCodeBench, BIRD
    - 科学：HLE, SciCode, GPQA
    - 指令遵循：IFBench, IFEval
    - 长上下文：RULER, MRCR
    - 工具调用：BFCL v3
    - 多语言：MMLU-ProX, FLORES-200
    - 语音/音频、视觉-语言模型
  - 训练集成：NeMo-RL / verl

### 5.2 NeMo-Curator

- **仓库:** https://github.com/NVIDIA-NeMo/Curator
- **用途:** 通用数据管护（文本/图像/视频/音频多模态）
- **核心能力:**
  - **文本:** 去重（精确/模糊MinHash/语义GPU加速）、30+启发式过滤器、fastText分类、语言检测
  - **图像:** 美学评分、NSFW检测、CLIP嵌入、去重
  - **视频:** 场景检测、片段提取、运动过滤、Cosmos-Embed1 嵌入
  - **音频:** ASR转写、WER过滤、质量评估
- **性能:**
  - 16x 加速（8TB RedPajama v2 模糊去重）
  - 40% TCO 降低（vs CPU 方案）
  - 近线性扩展（1→4 H100 节点：2.05h → 0.50h）
- **安装:** `uv pip install "nemo-curator[text_cuda12]"`

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
| NeMo Framework | 模型训练 | NVIDIA NeMo |
| NeMo Customizer | 微调微服务 | NVIDIA NeMo |
| NeMo-RL / verl | 强化学习训练 | GitHub |

---

## 六、快速使用

```python
from datasets import load_dataset

# 加载代码和数学 SFT 数据
ds = load_dataset("nvidia/Llama-Nemotron-Post-Training-Dataset", "SFT", split=["code", "math"])

# 加载 RL 数据
ds_rl = load_dataset("nvidia/Llama-Nemotron-Post-Training-Dataset", "RL", split="instruction_following")

# 加载特定类别
ds_chat = load_dataset("nvidia/Llama-Nemotron-Post-Training-Dataset", "SFT", split="chat")
ds_safety = load_dataset("nvidia/Llama-Nemotron-Post-Training-Dataset", "SFT", split="safety")
ds_science = load_dataset("nvidia/Llama-Nemotron-Post-Training-Dataset", "SFT", split="science")
```

---

## 七、总结

这是目前开源社区最完整的后训练数据集之一。核心价值：

1. **规模大:** 3300万样本，覆盖数学/代码/科学/聊天/安全/指令遵循
2. **全流程开放:** 不只给数据，还公开了 prompt 采集→管护→生成→验证→去污的完整方法论
3. **工具链完整:** NeMo-Skills + NeMo-Curator 可直接复用整套流水线
4. **教师模型多样:** 9个不同模型生成响应，增加数据多样性
5. **推理模式训练:** 包含开/关推理的响应对，教模型何时该深度思考
6. **严格去污:** 针对所有主流基准做了去污处理，确保评测公平性
