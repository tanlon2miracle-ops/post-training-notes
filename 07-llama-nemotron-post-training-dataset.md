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

### 5.3 其他工具

| 工具 | 用途 | 地址 |
|------|------|------|
| lmsys decontaminator | 基准去污（防止评测数据泄露） | https://github.com/lm-sys/llm-decontaminator |
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
