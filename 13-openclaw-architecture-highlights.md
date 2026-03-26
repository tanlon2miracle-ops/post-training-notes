# OpenClaw 架构深度解析：自托管 AI Agent 操作系统

> **来源**：[Paolo Perazzo - OpenClaw Architecture, Explained](https://ppaolo.substack.com/p/openclaw-system-architecture-overview)（2026-02-12）+ 实际运行经验总结
>
> **定位**：面向开发者，深入理解 OpenClaw 的 Agent Loop、Skills、Tools、记忆、插件、Sub-Agents 等核心机制

---

## 一、OpenClaw 是什么

**一句话**：OpenClaw 是运行在你自己硬件上的 AI Agent 操作系统。LLM 提供智能，OpenClaw 提供执行环境。

它不是 API 套壳的聊天机器人，而是一个完整的基础设施：会话管理、记忆系统、工具沙箱、消息路由、安全隔离——全部运行在你的笔记本、VPS 或 Mac Mini 上。

---

## 二、高层架构

```
用户界面层                     核心层                      能力层
┌─────────────┐          ┌──────────────┐          ┌─────────────┐
│  WhatsApp   │          │              │          │   工具执行   │
│  Telegram   │◄────────►│   Gateway    │◄────────►│  (exec/浏览器│
│  Discord    │  Channel  │  (WS 控制面) │  Agent    │   /文件系统) │
│  iMessage   │  Adapters │              │  Runtime  │             │
│  Slack/CLI  │          │              │          │  记忆+会话   │
│  飞书/Web   │          └──────────────┘          └─────────────┘
└─────────────┘
```

**Gateway** 是单一控制面板（`src/gateway/server.ts`，Node.js 22+，WebSocket）。所有 Channel Adapter 接入它，它调度给 Agent Runtime 执行。绑定 `127.0.0.1:18789`，远程访问走 SSH 隧道或 Tailscale。

**Channel Adapters** 每平台一个，实现统一接口：认证（QR/Token/OAuth）→ 入站解析 → 访问控制（允许名单、DM 配对、@mention 要求）→ 出站格式化。支持 20+ 平台，可通过插件扩展。

---

## 三、Agent Loop（执行循环）⭐

这是 OpenClaw 的核心引擎，实现在 `src/agents/piembeddedrunner.ts`。每条消息到达后经历完整的 4 步流程：

```
① 会话解析（Session Resolution）
      │
      ▼
② 上下文组装（Context Assembly）
      │
      ▼
③ 模型调用 + 工具执行（LLM Call + Tool Execution Loop）
      │
      ▼
④ 状态持久化（State Persistence）
```

### 3.1 会话解析（Session Resolution）

每条入站消息首先被解析为一个 **Session**。Session 不只是 ID，更是**安全边界**——不同类型携带不同权限和工具策略。

| 消息来源 | Session Key 格式 | 信任级别 | 默认权限 |
|---------|-----------------|---------|---------|
| 你自己的消息 | `agent:main` | `owner` | 完全访问所有工具 |
| 私聊 DM | `agent:main:dm:<channel>:<userId>` | `trusted` | 沙箱化，受限工具集 |
| 群聊消息 | `agent:main:group:<channel>:<groupId>` | `sandboxed` | 更严格，需 @mention |
| 子 Agent | `agent:main:subagent:<uuid>` | 继承父级 | 按深度递减 |

**解析规则细节**：

```typescript
// Session 解析的核心逻辑（简化）
function resolveSession(inbound: InboundMessage): SessionDescriptor {
  const { channel, senderId, groupId, isOwner } = inbound;

  if (isOwner) {
    return { key: 'agent:main', trust: 'owner', tools: 'full' };
  }

  if (groupId) {
    return {
      key: `agent:main:group:${channel}:${groupId}`,
      trust: 'sandboxed',
      tools: resolveGroupToolPolicy(channel, groupId),
      requireMention: config.groups?.requireMention ?? true,
    };
  }

  return {
    key: `agent:main:dm:${channel}:${senderId}`,
    trust: 'trusted',
    tools: resolveDmToolPolicy(channel, senderId),
  };
}
```

**信任级别如何影响行为**：
- `owner`：可读写工作区文件、执行任意命令、访问 MEMORY.md
- `trusted`：可执行沙箱内命令、不能读 MEMORY.md
- `sandboxed`：Docker 隔离、受限网络、工具白名单

### 3.2 上下文组装（Context Assembly）

每次调用模型前，系统从多个来源**动态组合**完整的上下文。这不是一个静态 prompt，而是根据 session 类型、对话内容、可用 Skills 实时构建的。

```
系统 Prompt 构建顺序（从上到下）：

┌─────────────────────────────────────────────────┐
│  ① Pi Agent Core 基础指令（内置，不可改）          │
├─────────────────────────────────────────────────┤
│  ② AGENTS.md —— 工作区核心指令                    │
│  ③ SOUL.md —— 人格、语气、行为准则                │
│  ④ TOOLS.md —— 用户的工具使用笔记                 │
│  ⑤ IDENTITY.md —— Agent 身份信息                  │
│  ⑥ USER.md —— 用户信息                           │
├─────────────────────────────────────────────────┤
│  ⑦ 其他工作区文件（*.md，自动注入 Project Context）│
├─────────────────────────────────────────────────┤
│  ⑧ Skills —— 按需注入（见 Skills 系统章节）        │
├─────────────────────────────────────────────────┤
│  ⑨ 语义记忆搜索结果                               │
├─────────────────────────────────────────────────┤
│  ⑩ 运行时元数据（时间、主机名、模型、channel 等）   │
├─────────────────────────────────────────────────┤
│  ⑪ 工具定义（JSON Schema，见 Tools 章节）          │
└─────────────────────────────────────────────────┘
         +
   会话历史（从磁盘 JSON 加载）
```

**关键机制**：
- 工作区的 `*.md` 文件会被作为 "Project Context" 自动注入系统 prompt，但只限浅层目录
- 记忆搜索使用混合检索（BM25 + 向量语义），仅在 main session 中搜索 MEMORY.md
- Skills 不是全量注入，而是根据 `<available_skills>` 的 `<description>` 匹配当前对话主题后按需加载
- 不同 session 类型看到不同的上下文（如 group session 看不到 MEMORY.md）

### 3.3 执行循环（LLM Call + Tool Execution）

这是最核心的循环——模型生成响应时，工具调用被实时拦截和执行：

```
                    ┌──────────────┐
                    │  发送到 LLM   │
                    │ （流式请求）   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌─────│  解析响应流    │
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐     ┌──────────────┐
              │  是  │  检测到工具   │ 否  │  纯文本响应    │
              │ ┌───│  调用？       │────►│  发回 channel  │
              │ │   └──────────────┘     └──────────────┘
              │ │
              │ │   ┌──────────────┐
              │ └──►│  执行工具     │
              │     │  (exec/browser│
              │     │  /read/write) │
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │  工具结果     │
              │     │  流回模型     │
              └─────┤  继续生成     │
                    └──────────────┘
                    （循环直到没有更多工具调用）
```

**流式拦截机制**：模型响应以 SSE（Server-Sent Events）流式到达。当检测到 `tool_use` block 时，运行时暂停流、执行工具、将结果作为 `tool_result` 追加到对话历史，然后发起新一轮模型调用。这个循环持续直到模型产生纯文本响应。

**工具执行的安全检查**：

```typescript
// 每次工具调用前的检查链（简化）
async function executeToolCall(call: ToolCall, session: Session) {
  // 1. 工具是否在 allow list 中
  if (!isToolAllowed(call.name, session.toolPolicy)) {
    return { error: `Tool ${call.name} is not allowed in this session` };
  }

  // 2. 循环检测
  if (loopDetector.check(call, session.recentCalls)) {
    return { error: 'Loop detected, breaking execution' };
  }

  // 3. 沙箱检查（DM/group session 可能需要 Docker）
  const executor = session.sandbox
    ? sandboxedExecutor(call, session.sandbox)
    : directExecutor(call);

  // 4. 执行并记录
  const result = await executor.run();
  session.recentCalls.push({ call, result, timestamp: Date.now() });
  return result;
}
```

### 3.4 队列化与并发控制

OpenClaw 使用 **per-session lane + global lane** 的双层队列，确保：

1. **Per-session 串行**：同一 session 的消息严格按序执行，避免状态竞争
2. **Cross-session 并行**：不同 session 的请求可以并发处理
3. **Global 限流**：全局最大并发数防止资源耗尽

```
入站消息队列：

Session A: [msg1] → [msg2] → [msg3]    ──→ 串行执行
Session B: [msg1] → [msg2]              ──→ 串行执行
Session C: [msg1]                       ──→ 串行执行
                                            ↑
                                        三个 session 之间并行
                                        但受 global concurrency 限制
```

配置示例：

```json5
// openclaw.json
{
  "agents": {
    "concurrency": {
      "maxConcurrentSessions": 3,    // 最多同时处理 3 个 session
      "queueTimeout": 120000         // 排队超时 2 分钟
    }
  }
}
```

### 3.5 自动压缩（Compaction）与预压缩记忆刷新

当会话历史超过模型的上下文窗口时，OpenClaw 自动触发 **compaction**：

```
压缩前：
[sys_prompt] [msg1] [msg2] ... [msg50] [msg51] ... [msg100]
              ─────── 旧消息 ────────   ──── 新消息 ────

压缩过程：
1. 【记忆刷新】把即将被压缩的旧消息中的关键信息
   提取并写入 memory/YYYY-MM-DD.md（预压缩 memory flush）
2. 【摘要生成】用模型对旧消息生成结构化摘要
3. 【替换】用摘要替换原始旧消息

压缩后：
[sys_prompt] [summary_of_msg1-50] [msg51] ... [msg100]
              ── 一条摘要消息 ──   ──── 新消息保留 ────
```

**预压缩记忆刷新（Memory Flush）** 是关键设计——在压缩丢弃旧消息之前，先把重要信息持久化到记忆文件，避免信息丢失。这保证了即使对话很长，关键上下文也不会被"遗忘"。

### 3.6 状态持久化

每轮执行完成后，完整的会话状态（包括所有工具调用和结果）被持久化到磁盘：

```
~/.openclaw/sessions/
├── agent_main/
│   ├── history.json          # 完整对话历史（追加式事件日志）
│   └── state.json            # session 元数据
├── agent_main_dm_discord_xxx/
│   ├── history.json
│   └── state.json
└── ...
```

---

## 四、Skills 系统 ⭐

Skills 是 OpenClaw 的能力扩展单元——可复用的指令包，告诉 Agent 如何完成特定类型的任务。

### 4.1 三层加载优先级

```
优先级从高到低：

① workspace skills     ~/.openclaw/workspace/skills/
   └── 用户自定义，最高优先级，可覆盖同名 skill

② managed/local skills ~/.openclaw/extensions/<plugin>/skills/
   └── 插件附带的 skills（如 feishu 插件带 feishu-doc skill）

③ bundled skills       <install_dir>/node_modules/openclaw/skills/
   └── OpenClaw 自带的内置 skills
```

**覆盖规则**：如果 workspace 中存在与 bundled 同名的 skill，workspace 版本优先。这让用户可以定制内置行为。

### 4.2 SKILL.md 格式（AgentSkills 兼容）

每个 Skill 是一个目录，核心文件是 `SKILL.md`：

```
skills/
└── my-skill/
    ├── SKILL.md          # 必须，核心指令文件
    ├── metadata.json     # 可选，元数据和门控条件
    ├── scripts/          # 可选，辅助脚本
    │   └── helper.py
    └── references/       # 可选，参考资料
        └── api-docs.md
```

**SKILL.md 示例**：

```markdown
# My Custom Skill

## When to Use
当用户要求 xxx 时使用此 skill。

## Instructions
1. 首先执行 `scripts/helper.py` 获取数据
2. 然后根据结果生成报告
3. 输出到 workspace 目录

## References
参考 references/api-docs.md 了解 API 格式。
```

**metadata.json 示例**：

```json
{
  "name": "my-skill",
  "description": "用一句话描述此 skill 的功能，用于匹配对话内容",
  "version": "1.0.0",
  "openclaw": {
    "requires": {
      "bins": ["python3", "git"],
      "env": ["OPENAI_API_KEY"],
      "config": ["channels.discord"]
    }
  }
}
```

### 4.3 门控机制（Gating）

`metadata.openclaw.requires` 定义了 Skill 的运行前提条件：

| 门控类型 | 说明 | 示例 |
|---------|------|------|
| `bins` | 系统中必须存在的可执行文件 | `["python3", "ffmpeg"]` |
| `env` | 必须设置的环境变量 | `["OPENAI_API_KEY"]` |
| `config` | openclaw.json 中必须存在的配置路径 | `["channels.discord"]` |

**不满足条件的 Skill 不会出现在 `<available_skills>` 列表中**，从根本上避免 Agent 尝试调用不可用的能力。

### 4.4 按需注入（On-Demand Injection）

**关键设计**：Skills 不是全部塞进系统 prompt。OpenClaw 的做法是：

```
Step 1: 系统 prompt 中注入所有可用 Skill 的摘要清单：

<available_skills>
  <skill>
    <name>weather</name>
    <description>Get weather forecasts...</description>
    <location>~/.openclaw/skills/weather/SKILL.md</location>
  </skill>
  <skill>
    <name>github</name>
    <description>GitHub operations via gh CLI...</description>
    <location>~/.openclaw/skills/github/SKILL.md</location>
  </skill>
  ... 每个 skill 仅 ~100 tokens
</available_skills>

Step 2: 模型根据对话内容判断需要哪个 Skill

Step 3: 模型调用 read 工具读取对应 SKILL.md

Step 4: SKILL.md 内容进入对话历史，指导后续行为
```

**为什么不直接全注入？** Token 开销计算：

```
假设有 30 个 Skills，每个 SKILL.md 平均 800 tokens：
- 全量注入：30 × 800 = 24,000 tokens（每次请求都浪费）
- 按需注入：30 × 100（摘要）+ 1 × 800（按需加载）= 3,800 tokens

节省约 84% 的 prompt token 开销
```

### 4.5 ClawHub 技能市场

ClawHub（clawhub.com）是 OpenClaw 的官方 Skill 市场，类似 npm：

```bash
# 搜索 skill
clawhub search "weather"

# 安装 skill（安装到 ~/.openclaw/workspace/skills/）
clawhub install weather

# 更新到最新版本
clawhub update weather

# 同步所有已安装 skill
clawhub sync

# 发布自己的 skill
clawhub publish ./skills/my-skill
```

### 4.6 创建自定义 Skill

```bash
# 1. 创建目录
mkdir -p ~/.openclaw/workspace/skills/my-tool

# 2. 写 SKILL.md（必须）
cat > ~/.openclaw/workspace/skills/my-tool/SKILL.md << 'EOF'
# My Tool Skill

## When to Use
当用户需要 xxx 时触发。

## Steps
1. ...
2. ...
EOF

# 3. 可选：添加 metadata.json（门控条件、版本信息）
# 4. 可选：添加 scripts/ 和 references/ 目录
# 5. 重启 gateway 或等待自动热加载
```

---

## 五、Tools 工具体系 ⭐

### 5.1 内置工具清单

| 工具 | 功能 | 典型用途 |
|------|------|---------|
| `exec` | 执行 shell 命令 | 运行脚本、安装包、Git 操作 |
| `process` | 管理后台进程 | 轮询长任务、发送输入、PTY 交互 |
| `read` / `write` / `edit` | 文件操作 | 读写代码、配置、文档 |
| `browser` | Chromium 浏览器自动化 | 网页操作、截图、数据提取 |
| `canvas` | Agent 驱动的可视化工作区 | 展示 UI、A2UI 交互 |
| `nodes` | 设备控制（手机/IoT） | 摄像头、屏幕录制、定位 |
| `message` | 跨平台消息发送 | Discord/Telegram/飞书等 |
| `web_search` | 网络搜索（Brave API） | 实时信息检索 |
| `web_fetch` | 网页内容抓取 | 读取文章、API 文档 |
| `tts` | 文本转语音 | 语音回复 |
| `subagents` | 子 Agent 管理 | 多 Agent 协作 |
| `feishu_*` | 飞书文档/表格/Wiki | 飞书生态集成 |

### 5.2 工具策略（Tool Policies）

工具可用性通过 **策略链** 控制，从粗到细：

```json5
// openclaw.json
{
  "tools": {
    // 全局允许/拒绝列表
    "allow": ["exec", "read", "write", "web_search"],
    "deny": ["browser"],

    // 预定义 profile（快捷方式）
    "profile": "coding",  // minimal | coding | messaging | full

    // 按 provider 覆盖
    "byProvider": {
      "openai/*": {
        "deny": ["exec"]  // OpenAI 模型禁用 exec
      },
      "anthropic/claude-*": {
        "profile": "full"  // Claude 全量工具
      }
    }
  }
}
```

**Profile 预设**：

| Profile | 包含工具 |
|---------|---------|
| `minimal` | read, write, edit, web_search, web_fetch |
| `coding` | minimal + exec, process |
| `messaging` | minimal + message, tts |
| `full` | 所有可用工具 |

### 5.3 Tool Groups

工具按功能分组，便于策略配置中批量引用：

```json5
{
  "tools": {
    "allow": [
      "group:runtime",     // exec, process
      "group:fs",          // read, write, edit
      "group:web",         // web_search, web_fetch
      "group:ui",          // browser, canvas
      "group:messaging",   // message, tts
      "group:sessions",    // subagents, sessions_*
      "group:memory",      // 记忆相关
      "group:nodes",       // 设备控制
      "group:automation",  // cron, webhooks
      "group:openclaw"     // gateway 管理
    ]
  }
}
```

### 5.4 循环检测（Loop Detection）

Agent 有时会陷入无效循环（重复执行相同工具调用）。OpenClaw 内置三种检测器：

| 检测器 | 触发条件 | 示例 |
|--------|---------|------|
| `genericRepeat` | 连续 N 次相同工具+相同参数 | 反复 `exec("git status")` |
| `knownPollNoProgress` | 轮询类操作无进展 | `process(poll)` 反复无新输出 |
| `pingPong` | 两个工具调用交替循环 | `read → write → read → write` |

触发后 Agent 会收到循环警告，强制跳出。

### 5.5 工具如何呈现给模型

工具通过**双通道**传递给模型：

1. **Tool Schema 通道**：每个工具的 JSON Schema（函数名、参数、描述）通过 API 的 `tools` 参数传递
2. **System Prompt 通道**：工具的使用指南、限制、最佳实践写在系统 prompt 中

```
模型看到的：

System Prompt:
  "... 你可以使用 exec 工具执行 shell 命令。
   使用 pty=true 处理需要 TTY 的交互式命令 ..."

Tools (JSON Schema):
  {
    "name": "exec",
    "description": "Execute shell commands...",
    "parameters": {
      "command": { "type": "string" },
      "pty": { "type": "boolean" },
      "timeout": { "type": "number" },
      ...
    }
  }
```

---

## 六、记忆系统 ⭐

### 6.1 工作区记忆文件

```
~/.openclaw/workspace/
├── MEMORY.md                    # 长期记忆（仅 main session 可见）
└── memory/
    ├── 2026-03-25.md            # 昨天的日志
    ├── 2026-03-26.md            # 今天的日志
    └── heartbeat-state.json     # 心跳检查状态
```

- **MEMORY.md**：Agent 的"长期记忆"，手动或自动维护的精炼信息。**安全限制**：仅在 main session 中加载，group/dm session 看不到，防止泄露私人上下文
- **memory/YYYY-MM-DD.md**：每日原始笔记，记录当天发生的事件和决策
- Agent 可以在心跳（heartbeat）时定期整理日志 → 提炼到 MEMORY.md

### 6.2 向量记忆搜索

底层存储在 `~/.openclaw/memory/<agentId>.sqlite`（SQLite + 向量嵌入），支持**混合检索**：

```
查询："上次处理飞书文档的经验"
          │
          ├──→ BM25 关键词匹配（精确命中 "飞书文档"）
          │         权重: 0.3
          │
          └──→ 向量语义匹配（语义相近的 "Lark doc"/"云文档" 也能召回）
                    权重: 0.7
          │
          ▼
    合并 + MMR 多样性重排
          │
          ▼
    时间衰减加权（近期记忆权重更高）
          │
          ▼
    Top-K 结果注入上下文
```

**MMR（Maximal Marginal Relevance）多样性重排**：避免返回语义高度重复的结果。在相关性和多样性之间取平衡。

**时间衰减**：最近的记忆得分更高，避免远古记忆淹没当前相关信息。

### 6.3 预压缩记忆刷新（Memory Flush）

见 Agent Loop 章节的 compaction 部分。核心思想：**在压缩（丢弃旧消息）之前，先把关键信息写入记忆文件**，确保重要上下文不随 compaction 丢失。

### 6.4 QMD 后端（实验性）

QMD（Query-based Memory with Documents）是实验性的高级记忆后端，支持更复杂的检索策略和文档级别的记忆管理。

### 6.5 Embedding 选择

OpenClaw 按可用性自动选择 Embedding 模型，优先级：

```
local（本地模型）> openai > gemini > voyage > mistral > ollama
```

配置示例：

```json5
{
  "memory": {
    "embedding": {
      "provider": "openai",          // 强制指定
      "model": "text-embedding-3-small"
    }
  }
}
```

文件监控：工作区 `.md` 文件修改后 **1.5 秒自动重建索引**，保证搜索时效性。

---

## 七、插件（Plugins）和 MCP ⭐

### 7.1 四类插件

| 类型 | 说明 | 例子 |
|------|------|------|
| **Channel** | 新消息平台接入 | Teams、Matrix、飞书 |
| **Memory** | 替代记忆存储后端 | 向量数据库、知识图谱 |
| **Tool** | 自定义 Agent 工具 | 自定义 API 调用、硬件控制 |
| **Provider** | 自定义 LLM 提供商 | 自托管模型、私有 API |

### 7.2 插件能力注册

一个插件可以同时注册多种能力：

```typescript
// 插件入口示例
export default class MyPlugin implements OpenClawPlugin {
  register(host: PluginHost) {
    // 注册 Agent 工具（模型可调用）
    host.registerTool('my_tool', {
      description: 'Do something useful',
      parameters: { /* JSON Schema */ },
      handler: async (params) => { /* ... */ }
    });

    // 注册 RPC 方法（Gateway 可调用）
    host.registerRPC('my_rpc', async (req) => { /* ... */ });

    // 注册 HTTP handler
    host.registerHTTP('GET', '/my-endpoint', async (req, res) => { /* ... */ });

    // 注册 CLI 命令
    host.registerCLI('my-command', async (args) => { /* ... */ });

    // 注册后台服务（随 Gateway 启动）
    host.registerService('my-bg-task', async () => { /* ... */ });

    // 注册 Skills
    host.registerSkills(__dirname + '/skills');

    // 注册自动回复命令（如 /help 触发特定回复）
    host.registerAutoReply('/my-cmd', async (msg) => { /* ... */ });
  }
}
```

### 7.3 Plugin Hooks（生命周期钩子）

插件可以挂载到 Agent 执行的各个阶段：

| Hook | 触发时机 | 典型用途 |
|------|---------|---------|
| `before_model_resolve` | 模型选择之前 | 动态路由到不同模型 |
| `before_prompt_build` | 系统 prompt 组装之前 | 注入自定义上下文 |
| `before_tool_call` | 工具执行之前 | 审计日志、参数改写 |
| `after_tool_call` | 工具执行之后 | 结果后处理、监控 |
| `before_response` | 响应发回用户之前 | 内容过滤、格式调整 |
| `on_session_start` | 新 session 创建时 | 初始化自定义状态 |
| `on_compaction` | 会话压缩时 | 自定义摘要逻辑 |

### 7.4 Plugin Slots（独占类别）

某些插件类别是**独占**的——同一时间只能有一个插件占据该 slot：

- **Memory Slot**：只能有一个记忆后端（默认 SQLite，可被向量数据库插件替换）
- **这避免了多个记忆插件同时写入导致冲突**

### 7.5 MCP（Model Context Protocol）

OpenClaw 也支持 MCP 协议，可以作为 MCP server 对外暴露能力，或作为 MCP client 调用外部 MCP 工具。

---

## 八、Sub-Agents（多 Agent 协作）⭐

### 8.1 sessions_spawn 生成子 Agent

主 Agent 可以通过 `subagents` 工具生成子 Agent 来委派工作：

```
主 Agent（收到复杂任务）
    │
    ├─ spawn subagent A: "重写文档"
    │     ├─ 独立 session
    │     ├─ 独立上下文
    │     └─ 完成后自动汇报结果
    │
    └─ spawn subagent B: "搜索相关资料"
          ├─ 独立 session
          └─ 并行执行
```

### 8.2 一次性（run）vs 持久线程绑定（session + thread）

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **run** | 一次性执行，完成后 session 归档 | 文件处理、数据分析、Git 操作 |
| **session + thread** | 绑定到特定 channel 线程，持续响应 | Discord thread、长期协作 |

### 8.3 嵌套 Sub-Agent（Orchestrator Pattern）

Sub-Agent 可以再生成 Sub-Agent，形成层级结构：

```
主 Agent (depth 0)
  └─ 子 Agent A (depth 1)
       └─ 孙 Agent A1 (depth 2)   ← 受 maxSpawnDepth 限制
  └─ 子 Agent B (depth 1)
```

**maxSpawnDepth**（配置项）限制最大嵌套深度，防止无限递归。

### 8.4 工具策略按深度分配

子 Agent 的工具权限随深度递减：

```json5
{
  "agents": {
    "subagents": {
      "maxSpawnDepth": 3,
      "toolsByDepth": {
        "1": { "profile": "coding" },     // depth 1: 可执行代码
        "2": { "profile": "minimal" },     // depth 2: 仅读写
        "3": { "deny": ["exec"] }          // depth 3: 禁止执行
      }
    }
  }
}
```

### 8.5 级联停止与自动归档

- **级联停止**：当父 Agent session 结束时，所有子 Agent 自动停止
- **自动归档**：一次性 sub-agent 完成后，session 自动归档，释放资源
- **结果推送**：子 Agent 完成后，结果自动推送回父 Agent（push-based，无需轮询）

### 8.6 ACP 协议（Agent Client Protocol）

ACP 允许 OpenClaw 运行外部 Agent harness 作为子进程：

```json5
// 支持的外部 Agent
{
  "acp": {
    "harnesses": {
      "codex": { "command": "codex", "args": ["--model", "o3"] },
      "claude-code": { "command": "claude", "args": [] },
      "gemini-cli": { "command": "gemini", "args": [] }
    }
  }
}
```

工作流：主 Agent 通过 ACP 启动外部 coding agent（如 Codex、Claude Code）→ 外部 agent 在 PTY 中运行 → 通过 ACP 协议交换消息 → 结果流回主 Agent。

---

## 九、真实案例——从 Discord 消息到 Git Push

### 场景

用户在 Discord #笔记 频道发了一条消息：

> "你直接按照这个文档来吧"（附带一个 Substack 文章链接）
> "本地 markdown 然后上传到 https://github.com/xxx/post-training-notes"

### 实际执行流程

```
Discord 群聊消息
      │
      ▼
┌─ ① 接收 ──────────────────────────────────────────────┐
│  discord.js 收到消息事件                                │
│  适配器解析：sender, channel=#笔记                      │
│  提取：消息文本 + 引用的 Substack URL                   │
└───────────────────────────────────────────────────────┘
      │
      ▼
┌─ ② 访问控制 + Session 解析 ───────────────────────────┐
│  检查 group policy → 该频道已在允许名单                 │
│  Session → group:discord:1481255435108356269            │
│  信任级别：群聊（但该频道配置了扩展工具集）               │
└───────────────────────────────────────────────────────┘
      │
      ▼
┌─ ③ 上下文组装 ────────────────────────────────────────┐
│  加载 session 历史（含之前对话上下文）                   │
│  组合系统 prompt：AGENTS.md + SOUL.md + IDENTITY.md    │
│  匹配 Skills：检测到 tech-note-writer 可能相关         │
│  记忆搜索：查找相关的历史笔记操作经验                    │
└───────────────────────────────────────────────────────┘
      │
      ▼
┌─ ④ 模型调用 + 工具执行（多轮循环）─────────────────────┐
│                                                        │
│  Turn 1: 模型决定先读网页                               │
│  ├─ 调用 web_fetch → 403（Cloudflare 拦截）            │
│  ├─ 模型自动降级：browser.open → browser.snapshot      │
│  └─ 获取文章完整内容（~15000 字）                       │
│                                                        │
│  Turn 2: 写本地文件                                     │
│  ├─ 分析文章结构，用中文重写为技术笔记                   │
│  └─ write → openclaw-architecture-notes.md             │
│                                                        │
│  Turn 3: 推送 GitHub                                    │
│  ├─ exec: git clone → 复制文件 → git add + commit      │
│  └─ exec: git push origin main                         │
│                                                        │
└───────────────────────────────────────────────────────┘
      │
      ▼
┌─ ⑥ 响应交付 + 持久化 ────────────────────────────────┐
│  生成简短状态回复 → Discord 格式化 → 发回 #笔记         │
│  持久化完整会话状态（含所有工具调用和结果）               │
└───────────────────────────────────────────────────────┘
```

### 关键观察

- **工具降级**：`web_fetch` 被 Cloudflare 拦截后，Agent 自主切换到 `browser`，无需人工干预
- **多工具链式调用**：一条消息触发 browser → write → exec(git) 等 8+ 次工具调用，全部自动编排
- **上下文连续性**：Agent 记住前几条消息中提到的 URL 和目标仓库，跨消息理解意图

---

## 十、安全架构：六层纵深防御

| 层 | 机制 | 要点 |
|----|------|------|
| **1. 网络** | 仅 `127.0.0.1` | 远程需 SSH 隧道 / Tailscale |
| **2. 认证** | Token + 设备配对 | 新设备需挑战-响应 + 人工审批 |
| **3. 渠道访问** | 允许名单 + DM 配对 | 未知发送者须审批；群组可要求 @mention |
| **4. 工具沙箱** | Docker 隔离 | main=完全访问；DM/group=容器隔离 |
| **5. 工具策略** | 分层策略链 | Profile → Provider → Global → Agent → Group → Sandbox |
| **6. Prompt 注入防御** | 上下文隔离 | 用户消息/系统指令/工具结果严格分离 |

**核心原则**：信任链逐层收紧。main session 有完全权限，DM 默认沙箱化，group 更严格。即使 prompt 被注入，爆炸半径被容器限制。

---

## 十一、部署模式

| 模式 | 适用场景 | 特点 |
|------|---------|------|
| **本地开发** | 调试 | `pnpm dev` 热重载 |
| **macOS 菜单栏** | 个人日常 | LaunchAgent + Voice Wake |
| **Linux/VPS** | 7×24 | systemd + SSH 隧道 |
| **容器化** | 云原生 | Docker + 持久卷 |

---

## 十二、与其他方案对比

| 维度 | OpenClaw | ChatGPT/Claude 官方 | AutoGPT |
|------|---------|-------------------|---------|
| 运行位置 | 自托管 | SaaS | 自托管 |
| 数据控制 | 完全本地 | 云端 | 本地（有限） |
| 消息渠道 | 20+ 平台 | 仅官方 App | 无 |
| 记忆系统 | MD + 向量混合检索 | 黑盒 | 简单 |
| 工具沙箱 | Docker + 策略链 | N/A | 有限 |
| 多 Agent | 原生 Sub-Agent + ACP | 无 | 有限 |
| 设备集成 | 摄像头/录屏/定位 | 无 | 无 |
| 插件体系 | 四类 + 生命周期钩子 | 有限 | 有限 |

---

## 参考链接

- [OpenClaw 官网](https://openclaw.ai/)
- [GitHub 仓库](https://github.com/openclaw/openclaw)
- [官方文档](https://docs.openclaw.ai)
- [Paolo Perazzo 原文](https://ppaolo.substack.com/p/openclaw-system-architecture-overview)
- [ClawHub 技能市场](https://clawhub.com)
- [Discord 社区](https://discord.com/invite/clawd)
