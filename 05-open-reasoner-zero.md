# Open-Reasoner-Zero: Scaling Up RL on the Base Model

> **论文链接**：https://arxiv.org/abs/2503.24290
> **会议**：NeurIPS 2025
> **代码**：https://github.com/Open-Reasoner-Zero/Open-Reasoner-Zero
> **定位**：极简路线——用 vanilla PPO 在 base model 上做 RL，1/10 训练步数达到 R1-Zero 效果

---

## 1. 概述

Open-Reasoner-Zero 证明了一个极简方案就能复现 DeepSeek-R1-Zero 的 scaling 现象：

> **Vanilla PPO + GAE（λ=1, γ=1）+ rule-based reward，无 KL 正则化**

| 对比 | DeepSeek-R1-Zero | Open-Reasoner-Zero |
|:---:|:---------------:|:------------------:|
| 算法 | GRPO | Vanilla PPO + GAE |
| 基座 | V3-Base (671B) | Qwen2.5-32B-Base |
| KL 正则 | 有 | 无 |
| 训练步数 | ~数千步 | ~数百步（1/10） |
| AIME24 | 71.0 | 更优 |
| MATH500 | ✓ | 更优 |
| GPQA Diamond | ✓ | 更优 |

---

## 2. 核心方法

### 极简配置
- **算法**：Vanilla PPO（不是 GRPO）
- **Advantage 估计**：GAE with λ=1, γ=1（等价于 Monte Carlo return）
- **Reward**：纯 rule-based（准确性验证）
- **无 KL 正则化**：不需要 reference model
- **无 entropy bonus**：不需要额外的熵管理

### 为什么 PPO 而不是 GRPO？
- PPO 使用 learned critic（价值函数）
- Critic 能有效**识别和降低重复响应模式的 advantage**
- 带来更鲁棒的 advantage 估计 → 训练更稳定
- GRPO 的 group-level 标准化可能没有这个优势

---

## 3. 关键发现

### 3.1 Scaling 现象可复现
- 随训练步数增加，benchmark 性能持续提升
- 响应长度自然增长（模型自发分配更多 thinking time）
- 与 R1-Zero 观察到的 scaling 现象一致

### 3.2 效率惊人
- 使用同一个 base model（Qwen2.5-32B），仅需 1/10 训练步数
- 性能反而更优（AIME24, MATH500, GPQA Diamond）

### 3.3 Learned Critic 的价值
- Critic 能量化识别重复模式
- 降低重复响应的 advantage → 避免模型陷入重复
- 这是 PPO 相比 GRPO 的潜在优势

---

## 4. 与 R1-Zero 路线的对比

| 维度 | R1-Zero | Open-Reasoner-Zero |
|:---:|:------:|:-----------------:|
| 算法 | GRPO（无 critic） | PPO + GAE（有 critic） |
| KL 正则 | 有 | 无 |
| 训练步数 | ~数千步 | ~数百步 |
| 基座 | V3-671B | Qwen2.5-32B |
| 关键发现 | Aha Moment | Critic 抑制重复 |
| 开源 | 权重 | 代码+数据+权重 |

---

## 5. 实战 Takeaway

1. **PPO 可能比 GRPO 更好**：learned critic 带来更稳定的训练
2. **极简配置就够了**：不需要 KL、不需要 entropy bonus、不需要 fancy tricks
3. **GAE(λ=1, γ=1) = Monte Carlo**：最简单的 advantage 估计
4. **训练效率很高**：1/10 步数达到相同效果
5. **从 base model 直接 RL 是可行的**：不需要 SFT 冷启动
6. **全开源**：代码 + 数据 + 权重，最容易复现

---

## 6. 相关资源

- 代码: https://github.com/Open-Reasoner-Zero/Open-Reasoner-Zero
- 论文: https://arxiv.org/abs/2503.24290
- NeurIPS 2025: https://neurips.cc/virtual/2025/poster/118391
