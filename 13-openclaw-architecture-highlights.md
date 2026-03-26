# OpenClaw 架构深度解析：自托管 AI Agent 操作系统

> **来源**：[Paolo Perazzo - OpenClaw Architecture, Explained](https://ppaolo.substack.com/p/openclaw-system-architecture-overview)（2026-02-12）
>
> **定位**：面向开发者和技术决策者，理解 OpenClaw 如何将 AI Agent 从"聊天机器人"变成"能行动的智能助手"

---

## 一、OpenClaw 是什么

**一句话**：OpenClaw 是运行在你自己硬件上的 AI Agent 操作系统。LLM 提供智能，OpenClaw 提供执行环境。

它不是 API 套壳的聊天机器人，而是一个完整的基础设施：会话管理、记忆系统、工具沙箱、消息路由、安全隔离——全部运行在你的笔记本、VPS 或 Mac Mini 上。

**增长**：2026 年 1 月到 2 月，从周末 WhatsApp 转发脚本到 GitHub 180K+ Stars，成为开源历史上增长最快的项目之一。Andrej Karpathy 称之为"最不可思议的科幻级起飞"。

---

## 二、高层架构：Hub-and-Spoke

![高层架构图](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff5354755-5809-446a-844a-498454484cfd_1205x1094.png)

```
用户界面层                     核心层                      能力层
┌─────────────┐          ┌──────────────┐          ┌─────────────┐
│  WhatsApp   │          │              │          │   工具执行   │
│  Telegram   │◄────────►│   Gateway    │◄────────►│  (bash/浏览器│
│  Discord    │  消息适配  │  (WS 控制面) │  Agent    │   /文件系统) │
│  iMessage   │          │              │  Runtime  │             │
│  Slack/...  │          │              │          │  记忆+会话   │
│  CLI / Web  │          └──────────────┘          └─────────────┘
│  macOS App  │
│  iOS/Android│
└─────────────┘
```

**关键洞察**：Gateway 是单一控制面板。所有消息 App 接入它，它调度给 Agent Runtime 执行。接口层和智能层完全解耦——一个 Agent 可以同时通过所有你已有的消息 App 访问。

---

## 三、核心组件详解

### 3.1 Channel Adapters（消息适配器）

每个平台一个适配器，实现统一接口：

| 职责 | 说明 |
|------|------|
| **认证** | WhatsApp 用 QR 码配对(Baileys)；Telegram/Discord 用 Bot Token |
| **入站解析** | 提取文本、媒体、表情、回复上下文，统一格式 |
| **访问控制** | 允许名单、DM 配对审批、群组 @mention 要求 |
| **出站格式化** | 适配各平台的 Markdown 方言、消息长度限制、媒体上传 |

**支持的平台**：WhatsApp(Baileys)、Telegram(grammY)、Discord(discord.js)、iMessage(macOS 原生)、Slack、Signal、Matrix、Teams 等 20+ 个，还可通过插件扩展。

### 3.2 Control Interfaces（控制界面）

| 界面 | 说明 |
|------|------|
| **Web UI** | Lit 组件，Gateway 内置服务，`http://127.0.0.1:18789/` |
| **CLI** | Commander.js 实现，`openclaw gateway` / `openclaw agent` / `openclaw channels login` |
| **macOS App** | Swift 菜单栏应用，集成 Voice Wake、WebChat、远程 Gateway 管理 |
| **Mobile** | iOS/Android 作为 Node 连接，暴露摄像头、屏幕录制、定位等设备能力 |

### 3.3 Gateway Control Plane（网关控制面）

- **位置**：`src/gateway/server.ts`，Node.js 22+，基于 `ws` WebSocket 库
- **默认绑定**：`127.0.0.1:18789`（仅本地，安全第一）
- **单实例设计**：每台主机一个 Gateway（避免 WhatsApp 多设备冲突）
- **类型安全**：所有 WebSocket 帧经 JSON Schema 校验（TypeBox 生成）
- **事件驱动**：客户端订阅 `agent`/`presence`/`health`/`tick` 事件，非轮询
- **幂等操作**：所有副作用操作需幂等键，安全重试

### 3.4 Agent Runtime（Agent 运行时）

实现在 `src/agents/piembeddedrunner.ts`，基于 Pi Agent Core 库。每轮执行 4 步：

```
① 会话解析 → ② 上下文组装 → ③ 模型调用+工具执行 → ④ 状态持久化
```

#### 会话解析（Session Resolution）

| 消息来源 | Session Key | 信任级别 |
|---------|------------|---------|
| 你自己的消息 | `main` | 完全访问 |
| 某渠道的 DM | `dm:<channel>:<id>` | 沙箱化 |
| 群聊消息 | `group:<channel>:<id>` | 沙箱化 |

Session 不只是 ID，更是**安全边界**——不同类型携带不同权限和沙箱规则。

#### 上下文组装（Context Assembly）

每次调用模型前组装：
1. **会话历史**：从磁盘 JSON 加载
2. **系统提示词**：动态组合多个来源（见下文）
3. **语义记忆**：搜索相关历史对话注入上下文

#### 执行循环（Execution Loop）

模型响应时实时拦截工具调用 → 执行（可能在 Docker 沙箱内）→ 结果流回模型 → 模型继续生成 → 循环直到完成 → 持久化整个会话状态。

---

## 四、系统提示词架构

![系统提示词组成](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7a977528-1f60-44b6-963c-9248b7b9dd0a_1966x558.png)

提示词由多层组合而成，不是单一大 prompt：

| 层级 | 来源 | 说明 |
|------|------|------|
| **工作区配置** | `AGENTS.md` | 核心指令：Agent 能做什么、全局约束、安全规则 |
| | `SOUL.md` | 人格与语气：Agent 怎么说话（可选） |
| | `TOOLS.md` | 用户的工具使用笔记（可选，非工具注册表） |
| **动态上下文** | 会话历史 | 当前对话的最近消息 |
| | Skills | `skills/<name>/SKILL.md`——按需注入，不是全部塞进去 |
| | 记忆搜索 | 语义相似的历史对话 |
| **工具定义** | 内置工具 | bash、浏览器、文件操作、Canvas 等 |
| | 插件工具 | 通过扩展系统注册的自定义工具 |
| **基础系统** | Pi Agent Core | 底层运行时指令 |

**关键细节**：Skill 是**按需注入**的，不会把所有 Skill 塞进每个 prompt。运行时根据当前对话内容选择性加载相关 Skill，避免 prompt 膨胀。

---

## 五、端到端消息流（以 WhatsApp 为例）

![消息流全图](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdc2a349c-91c9-402f-8356-16dbb2583952_1724x1327.png)

| 阶段 | 做什么 | 延迟 |
|------|--------|------|
| **① 接收** | Baileys 收到 WhatsApp WebSocket 事件，适配器解析消息/媒体/元数据 | — |
| **② 访问控制+路由** | 检查允许名单/配对状态 → 解析 session（main/dm/group） | <10ms |
| **③ 上下文组装** | 加载 session 历史 + 组合系统 prompt + 语义记忆搜索 | <100ms |
| **④ 模型调用** | 流式发送到 Claude/GPT/Gemini 等 | 200-500ms |
| **⑤ 工具执行** | 拦截工具调用，执行（可能在 Docker 内），结果流回模型 | 视工具而定 |
| **⑥ 响应交付** | 格式化 → 通过 Baileys 发回 WhatsApp → 持久化会话状态 | — |

---

## 六、交互与协调能力

### 6.1 Canvas 和 A2UI（Agent-to-UI）

![Canvas 架构](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F99d80f71-7a18-4854-9617-58e142334f6f_980x915.png)

Canvas 是 Agent 驱动的可视化工作区（独立端口 18793）。A2UI 是声明式框架——Agent 生成带特殊属性的 HTML，无需写 JavaScript：

```html
<button a2ui-action="complete" a2ui-param-id="123">Mark Complete</button>
```

用户点击 → Canvas 服务器转发为工具调用 → Agent 处理 → 推送更新 → UI 刷新。

### 6.2 Voice Wake & Talk Mode

- **平台**：macOS、iOS、Android
- **唤醒词**："Hey OpenClaw" 或自定义
- **流程**：语音 → ElevenLabs 转写 → Agent 处理 → TTS 回复
- **Talk Mode**：连续对话，支持打断检测

### 6.3 多 Agent 路由

![多Agent路由](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fff9c8af5-2816-479d-9bf7-b7004909bd99_1223x497.png)

不同频道/群组可以路由到**完全隔离的 Agent 实例**，各自有独立的 workspace、模型、行为：

```json5
{
  "agents": {
    "mapping": {
      "group:discord:123": {
        "workspace": "~/.openclaw/workspaces/discord-bot",
        "model": "anthropic/claude-sonnet-4-5"
      },
      "dm:telegram:*": {
        "workspace": "~/.openclaw/workspaces/support",
        "model": "openai/gpt-4o",
        "sandbox": { "mode": "always" }
      }
    }
  }
}
```

### 6.4 Session Tools（Agent 间通信）

- `sessions_list`：发现活跃 session
- `sessions_send`：向另一个 session 发消息
- `sessions_history`：读取另一个 session 的对话记录
- `sessions_spawn`：创建新 session 委派工作

### 6.5 Cron Jobs & Webhooks

- **Cron**：定时触发 Agent 动作（如每天 9 点生成日报）
- **Webhooks**：外部事件触发（如 Gmail 推送到 webhook → 触发 Agent 处理邮件）

---

## 七、数据存储与状态管理

![存储布局](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd3387882-3f4d-4d40-9ad3-f09ae4802852_1798x690.png)

### 配置

- 主文件：`~/.openclaw/openclaw.json`（JSON5 格式，支持注释）
- 分层覆盖：环境变量 > 配置文件 > 内置默认值

### 会话状态

- 位置：`~/.openclaw/sessions/`
- 格式：追加式事件日志，支持分支
- **自动压缩**：超出模型上下文限制时，旧对话被摘要化。压缩前会执行"记忆刷新"，把重要信息提升到记忆文件中

### 记忆系统

- 存储：`~/.openclaw/memory/<agentId>.sqlite`（SQLite + 向量嵌入）
- 搜索：**混合检索**——向量相似度（语义匹配）+ BM25（关键词匹配）
- 工作区记忆文件：
  - `MEMORY.md`——长期记忆，仅在私有/main session 中加载
  - `memory/YYYY-MM-DD.md`——每日笔记
- Embedding 选择：本地模型 > OpenAI > Gemini（按可用性自动选择）
- 文件监控：修改后 1.5 秒自动重建索引

### 凭证

- 位置：`~/.openclaw/credentials/`
- 权限：0600（仅所有者可读写）
- 自动排除版本控制

---

## 八、安全架构：六层纵深防御

| 层 | 机制 | 细节 |
|----|------|------|
| **1. 网络** | 仅绑定 127.0.0.1 | 远程访问需 SSH 隧道或 Tailscale |
| **2. 认证** | Token + 设备配对 | 新设备需挑战-响应签名 + 人工审批 |
| **3. 渠道访问** | 允许名单 + DM 配对 | 未知发送者必须经审批流程；群组可要求 @mention |
| **4. 工具沙箱** | Docker 隔离 | main=完全访问；DM/group=Docker 容器（隔离文件系统、可选网络） |
| **5. 工具策略** | 分层策略链 | `Tool Profile → Provider → Global → Agent → Group → Sandbox`，越后越严 |
| **6. Prompt 注入防御** | 上下文隔离 | 用户消息/系统指令/工具结果严格分离；推荐用最强模型 |

**核心原则**：信任链逐层收紧。main session 有完全权限，DM 默认沙箱化，group 更严格。即使 prompt 被注入，爆炸半径被容器限制。

---

## 九、部署模式

| 模式 | 适用场景 | 特点 |
|------|---------|------|
| **本地开发** | 开发调试 | `pnpm dev` 热重载，绑定 localhost，无需认证 |
| **macOS 菜单栏** | 个人日常 | LaunchAgent 后台运行，Voice Wake，iMessage 支持 |
| **Linux/VPS** | 7×24 在线 | systemd 服务 + SSH 隧道或 Tailscale Serve |
| **Fly.io 容器** | 云原生 | Docker + 持久卷 + 托管 HTTPS（需强认证） |

---

## 十、插件扩展体系

![插件体系](https://substackcdn.com/image/fetch/f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc7a60780-5817-4a4d-b518-0440ce283ed9_1181x988.png)

四类插件，不改核心代码：

| 类型 | 说明 | 例子 |
|------|------|------|
| **Channel 插件** | 新消息平台 | Teams、Matrix、Mattermost |
| **Memory 插件** | 替代存储后端 | 向量数据库、知识图谱 |
| **Tool 插件** | 自定义能力 | 超越内置 bash/browser/file |
| **Provider 插件** | 自定义 LLM | 自托管模型 |

发现机制：插件加载器扫描 `extensions/` 中 `package.json` 的 `openclaw.extensions` 字段，校验 schema 后热加载。

---

## 十一、与其他方案对比

| 维度 | OpenClaw | ChatGPT/Claude 官方 | AutoGPT/AgentGPT |
|------|---------|-------------------|------------------|
| 运行位置 | 自托管 | SaaS | 自托管 |
| 数据控制 | 完全本地 | 云端第三方 | 本地（有限） |
| 消息渠道 | 20+ 平台适配 | 仅官方 App | 无 |
| 记忆系统 | Markdown + 语义搜索 | 黑盒 | 简单 |
| 工具沙箱 | Docker 隔离 | N/A | 有限 |
| 多 Agent | 原生路由 | 无 | 有限 |
| 设备集成 | 摄像头/录屏/定位 | 无 | 无 |

---

## 十二、核心总结

OpenClaw 解决了四个关键问题：

1. **解决"入口碎片化"**：一个 Agent 通过所有你已有的消息 App 访问
2. **解决"记忆断裂"**：会话持久化 + 语义搜索 + 结构化记忆文件
3. **解决"安全裸奔"**：纵深防御——网络 + 认证 + 访问控制 + Docker 沙箱 + 策略链 + 上下文隔离
4. **解决"能力封闭"**：插件体系 + Skills 市场 + 多 Agent 路由 + 设备能力扩展

> "Not a chatbot wrapper. An operating system for AI agents."

---

## 参考链接

- [OpenClaw 官网](https://openclaw.ai/)
- [GitHub 仓库](https://github.com/openclaw/openclaw)
- [官方文档](https://docs.openclaw.ai)
- [Paolo Perazzo 原文](https://ppaolo.substack.com/p/openclaw-system-architecture-overview)
- [ClawHub 技能市场](https://clawhub.com)
- [Discord 社区](https://discord.com/invite/clawd)
