# CoPaw + AgentScope 生态：Python Agent 框架全景梳理

> 来源: https://github.com/agentscope-ai/CoPaw
> 生态: https://github.com/agentscope-ai/agentscope
> 参考: https://github.com/yuanzhoulvpi2017/zero_agent
> 日期: 2026-03-17

---

## 一、概览

**CoPaw** 是阿里 AgentScope 团队开源的**个人 AI 助手**，可以理解为 Python 版的 OpenClaw。它基于 AgentScope 框架构建，支持多渠道（钉钉/飞书/QQ/Discord/iMessage）接入、技能扩展、定时任务、长期记忆，并可本地或云端部署。

- **许可证:** Apache 2.0
- **语言:** Python
- **最新版本:** v0.0.7（2026-03-12）
- **安装:** `pip install copaw`

CoPaw 的底层生态由四个核心项目组成：

| 项目 | 定位 | 仓库 |
|------|------|------|
| **CoPaw** | 个人 AI 助手（终端产品） | https://github.com/agentscope-ai/CoPaw |
| **AgentScope** | Agent 开发框架（核心引擎） | https://github.com/agentscope-ai/agentscope |
| **AgentScope Runtime** | Agent 调度/部署/沙箱（运行时） | https://github.com/agentscope-ai/agentscope-runtime |
| **ReMe** | 记忆管理框架 | https://github.com/agentscope-ai/ReMe |

---

## 二、CoPaw vs OpenClaw 对比

| 维度 | CoPaw | OpenClaw |
|------|-------|----------|
| **语言** | Python | TypeScript |
| **Agent 框架** | AgentScope（自研） | Pi-mono |
| **渠道** | 钉钉/飞书/QQ/Discord/iMessage/Mattermost/Matrix/Telegram | Signal/Telegram/WhatsApp/Discord/iMessage/IRC/Slack/Feishu |
| **记忆** | ReMe（文件+向量，自动压缩） | MEMORY.md + memory/*.md（手动/心跳维护） |
| **技能系统** | Skills（Python 脚本） | Skills（SKILL.md + 脚本） |
| **定时任务** | 内置 cron | 心跳 + cron |
| **本地模型** | llama.cpp / MLX / Ollama | 需自行配置 |
| **MCP 支持** | ✅ 内置 | ❌ |
| **A2A 协议** | ✅（通过 AgentScope） | ❌ |
| **沙箱** | AgentScope Runtime（Docker/K8s/gVisor） | exec 工具（受限） |
| **Web UI** | ✅ Console（http://127.0.0.1:8088） | ❌（CLI 为主） |
| **桌面应用** | ✅ Beta（Windows/macOS） | ❌ |
| **部署** | 本地 / Docker / ModelScope / 阿里云 | 本地 |

---

## 三、AgentScope 框架详解

### 3.1 定位与设计哲学

AgentScope 是一个**面向生产的、易用的 Agent 开发框架**，核心设计理念是「随着模型能力提升而设计」——利用模型的推理和工具使用能力，而非用严格的 prompt 和固定编排去约束它。

**三大设计原则：**
- **Simple（简洁）：** 5 分钟上手，内置 ReActAgent + 工具 + 记忆 + 评估 + 微调
- **Extensible（可扩展）：** 大量生态集成（工具/记忆/可观测性），内置 MCP 和 A2A 支持
- **Production-ready（生产就绪）：** 本地/Serverless/K8s 部署，内置 OTel 可观测性

**论文：**
- [AgentScope 1.0: A Developer-Centric Framework for Building Agentic Applications](https://arxiv.org/abs/2508.16279)
- [AgentScope: A Flexible yet Robust Multi-Agent Platform](https://arxiv.org/abs/2402.14034)

### 3.2 核心架构

```
AgentScope 生态架构：

┌─────────────────────────────────────────────────────┐
│  AgentScope Runtime（调度/部署层）                     │
│  · AgentApp（FastAPI）— Agent as API                 │
│  · 沙箱（Base/GUI/Browser/Filesystem/Mobile）        │
│  · 状态管理 + 会话持久化                               │
│  · OTel 可观测性                                      │
│  · 多框架适配（AgentScope/LangGraph/AutoGen/Agno）    │
├─────────────────────────────────────────────────────┤
│  AgentScope（核心框架层）                              │
│  · ReActAgent — 内置推理 + 工具调用                    │
│  · MsgHub — 多 Agent 消息路由                         │
│  · Toolkit — 工具注册 + MCP                           │
│  · Memory — 短期（InMemory）+ 长期（ReMe）            │
│  · Formatter — 多模型格式适配                          │
│  · Pipeline — 顺序/并发/条件编排                       │
├─────────────────────────────────────────────────────┤
│  模型层                                               │
│  · 云端：DashScope / OpenAI / Anthropic              │
│  · 本地：llama.cpp / MLX / Ollama / LM Studio        │
├─────────────────────────────────────────────────────┤
│  ReMe（记忆层）                                       │
│  · 文件记忆（MEMORY.md + daily journal）              │
│  · 向量记忆（embedding + BM25 混合检索）              │
│  · 上下文管理（自动压缩 + token 计数）                 │
└─────────────────────────────────────────────────────┘
```

### 3.3 核心能力一览

| 能力 | 说明 |
|------|------|
| ReAct Agent | 内置推理 + 工具调用循环，5 分钟上手 |
| 工具系统 | Toolkit 注册 + MCP 集成 + Anthropic Agent Skill |
| 多 Agent 协作 | MsgHub 消息广播 + Pipeline 编排（顺序/并发/条件） |
| 实时语音 | Voice Agent + Realtime Voice Agent（支持中断恢复） |
| Human-in-the-loop | 实时干预和引导 |
| Agentic RL | Trinity-RFT 集成，用 RL 训练 Agent 策略 |
| A2A 协议 | Agent-to-Agent 互操作标准 |
| 结构化输出 | 支持约束解码 |
| RAG | 内置检索增强生成 |

### 3.4 ReActAgent —— 核心 Agent 类

**ReActAgent 是 AgentScope 最核心的 Agent 实现**，采用经典的 Reasoning + Acting 循环：

```
用户输入
    │
    ▼
ReActAgent 推理循环
    │
    ├─→ Reasoning（思考）：分析当前状态，决定下一步
    │
    ├─→ Acting（行动）：调用工具执行操作
    │       │
    │       ├─→ Toolkit 注册的本地函数
    │       ├─→ MCP 工具（通过 HttpStatelessClient）
    │       └─→ Anthropic Agent Skill
    │
    ├─→ Observation（观察）：获取工具执行结果
    │
    └─→ 循环直到任务完成或达到最大轮次
         │
         ▼
      最终输出
```

**代码示例（最小可运行）：**

```python
from agentscope.agent import ReActAgent, UserAgent
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit, execute_python_code, execute_shell_command
import os, asyncio

async def main():
    toolkit = Toolkit()
    toolkit.register_tool_function(execute_python_code)
    toolkit.register_tool_function(execute_shell_command)

    agent = ReActAgent(
        name="Friday",
        sys_prompt="You're a helpful assistant named Friday.",
        model=DashScopeChatModel(
            model_name="qwen-max",
            api_key=os.environ["DASHSCOPE_API_KEY"],
            stream=True,
        ),
        memory=InMemoryMemory(),
        formatter=DashScopeChatFormatter(),
        toolkit=toolkit,
    )

    user = UserAgent(name="user")
    msg = None
    while True:
        msg = await agent(msg)
        msg = await user(msg)
        if msg.get_text_content() == "exit":
            break

asyncio.run(main())
```

**关键设计特点：**
- **全异步架构**：所有 Agent/工具/记忆操作都是 async/await
- **流式输出**：通过 `stream_printing_messages` 实现 SSE 流式响应
- **记忆可插拔**：支持 `InMemoryMemory`、`AsyncSQLAlchemyMemory`（SQLite/PostgreSQL/MySQL）、`RedisMemory`
- **中断恢复**：实时语音场景下对话可被中断，通过 robust memory preservation 无缝恢复

### 3.5 MCP 工具集成

AgentScope 的 MCP 集成不止是简单调用，还支持**细粒度控制**：

```python
from agentscope.mcp import HttpStatelessClient
from agentscope.tool import Toolkit

async def fine_grained_mcp_control():
    client = HttpStatelessClient(
        name="gaode_mcp",
        transport="streamable_http",
        url=f"https://mcp.amap.com/mcp?key={os.environ['GAODE_API_KEY']}",
    )

    # 获取 MCP 工具作为本地可调用函数
    func = await client.get_callable_function(func_name="maps_geo")

    # 方式 1：直接调用
    await func(address="Tiananmen Square", city="Beijing")

    # 方式 2：作为工具传给 Agent
    toolkit = Toolkit()
    toolkit.register_tool_function(func)

    # 方式 3：包装成更复杂的工具
    # ...
```

**核心能力：**
- MCP 工具可以作为**本地可调用函数**使用（不仅仅是 Agent 工具）
- 支持 `streamable_http` 传输协议
- 可以与本地 Toolkit 函数混合使用

### 3.6 MsgHub —— 多 Agent 消息路由

MsgHub 管理多 Agent 对话的消息广播和参与者动态管理：

```python
from agentscope.pipeline import MsgHub, sequential_pipeline
from agentscope.message import Msg

async def multi_agent_conversation():
    agent1, agent2, agent3, agent4 = ...

    async with MsgHub(
        participants=[agent1, agent2, agent3],
        announcement=Msg("Host", "Introduce yourselves.", "assistant")
    ) as hub:
        # 顺序发言
        await sequential_pipeline([agent1, agent2, agent3])
        # 动态管理参与者
        hub.add(agent4)
        hub.delete(agent3)
        await hub.broadcast(Msg("Host", "Goodbye!", "assistant"))
```

**Pipeline 编排方式：**

| 方式 | 函数 | 说明 |
|------|------|------|
| 顺序执行 | `sequential_pipeline` | Agent 按序发言 |
| 并发执行 | `concurrent_pipeline` | Agent 同时执行 |
| 条件执行 | `conditional_pipeline` | 基于条件路由 |
| 自定义 | `Pipeline` 基类 | 自定义编排逻辑 |

### 3.7 Memory 模块

AgentScope 的 Memory 模块负责**消息存储 + 标记管理**，与压缩等算法逻辑解耦：

| 存储实现 | 说明 | 适用场景 |
|---------|------|---------|
| `InMemoryMemory` | 内存存储，配合 Session 可持久化 | 开发/测试 |
| `AsyncSQLAlchemyMemory` | 异步 SQLAlchemy，支持 SQLite/PostgreSQL/MySQL | 生产环境 |
| `RedisMemory` | Redis 存储 | 高并发场景 |

**标记系统（Mark）：** 每条消息可打标签（如 "hint"），支持按标签过滤和删除。ReActAgent 的 hint 消息就用 mark="hint" 管理。

```python
memory = InMemoryMemory()
# 添加普通消息
await memory.add(Msg("Alice", "Generate a report", "user"))
# 添加带标记的消息
await memory.add(
    [Msg("system", "<system-hint>...</system-hint>", "system")],
    marks="hint",
)
# 按标记检索
msgs = await memory.get_memory(mark="hint")
# 按标记删除
await memory.delete_by_mark("hint")
# 状态序列化（用于 Session 持久化）
state = memory.state_dict()
```

**Memory 压缩架构：**
- 压缩算法在 **Agent 层**实现（不在 Memory 层）
- Memory 模块通过 `_compressed_summary` 字段存储压缩后的摘要
- 支持 `state_dict()` / `load_state_dict()` 做跨 Session 状态恢复

### 3.8 Formatter —— 多模型格式适配

不同 LLM 提供商的消息格式各不相同。Formatter 层负责将 AgentScope 内部的统一消息格式（`Msg` 对象）转换为各模型 API 所需的格式：

| Formatter | 适配模型 |
|-----------|---------|
| `DashScopeChatFormatter` | 通义千问系列 (DashScope API) |
| `OpenAIChatFormatter` | GPT 系列 / OpenAI 兼容 API |
| `AnthropicChatFormatter` | Claude 系列 |

**为什么需要 Formatter？**
- 工具调用的请求/响应格式不同（如 OpenAI 的 `function_call` vs Anthropic 的 `tool_use`）
- 多模态消息的编码方式不同
- 系统消息的处理方式不同

### 3.9 Agentic RL 训练

通过 [Trinity-RFT](https://github.com/agentscope-ai/Trinity-RFT) 库集成，用强化学习直接训练 Agent 策略：

| 场景 | 模型 | 训练前 → 训练后 | 说明 |
|------|------|----------------|------|
| 数学推理 | Qwen3-0.6B | 75% → 85% | 多步推理 Agent |
| Frozen Lake 导航 | Qwen2.5-3B-Instruct | 15% → 86% | 环境导航 |
| 学会提问 | Qwen2.5-7B-Instruct | 47% → 92% | LLM-as-a-judge 自动反馈 |
| 邮件搜索 | Qwen3-4B-Instruct-2507 | — → 60% | 无标注数据的工具使用提升 |
| 狼人杀博弈 | Qwen2.5-7B-Instruct | 50% → 80% | 多 Agent 策略博弈 |
| 数据增强 (AIME-24) | Qwen3-0.6B | 20% → 60% | 合成数据增强训练 |

**训练流程：**
1. 定义 Agent 环境和奖励函数
2. Agent 在环境中执行任务（推理 + 工具调用）
3. 基于结果计算奖励（任务完成度/准确率等）
4. 用 RL 优化模型参数（PPO / GRPO 等算法）
5. 迭代直到策略收敛

### 3.10 实时语音 Agent

AgentScope 支持两种语音 Agent：

**Voice Agent（基础版）：**
- 语音输入 → STT → Agent 推理 → TTS → 语音输出
- 适合非实时场景

**Realtime Voice Agent（实时版）：**
- Web 界面实时语音交互
- 支持**中断恢复**：对话可被打断，中断后通过 robust memory preservation 无缝恢复
- 支持多 Agent 实时对话
- 基于 WebSocket 的实时通信

---

## 四、AgentScope Runtime 详解

### 4.1 定位

Agent 应用的**生产级运行时框架**——安全沙箱执行、Agent-as-a-Service API、可扩展部署、全栈可观测性。

**关键定位：框架无关（Framework-Agnostic）**——不绑定特定 Agent 框架，可以跑 AgentScope、LangGraph、Microsoft Agent Framework、Agno、AutoGen 等。

### 4.2 核心架构

```
AgentScope Runtime 架构：

┌─────────────────────────────────────────────────────────┐
│  客户端层                                                │
│  · curl / HTTP 客户端                                    │
│  · OpenAI SDK（兼容模式）                                │
│  · A2A 协议客户端                                        │
│  · Response API 客户端                                   │
├─────────────────────────────────────────────────────────┤
│  AgentApp（继承 FastAPI）                                │
│  · @agent_app.query() — 核心请求处理装饰器               │
│  · SSE 流式输出 — stream_printing_messages               │
│  · Distributed Interrupt Service — 运行时任务抢占        │
│  · Web Chat UI（可选）                                   │
├─────────────────────────────────────────────────────────┤
│  状态管理层                                              │
│  · RedisSession — 会话状态持久化                         │
│  · load_session_state / save_session_state               │
│  · 支持 FakeRedis（开发） / Redis（生产）                │
├─────────────────────────────────────────────────────────┤
│  沙箱层                                                  │
│  · BaseSandbox — Python/Shell 代码执行                   │
│  · GuiSandbox — 虚拟桌面（VNC）                          │
│  · BrowserSandbox — 浏览器操作（VNC）                    │
│  · FilesystemSandbox — 文件系统操作                      │
│  · MobileSandbox — 移动端操作                            │
│  · TrainingSandbox — 模型训练环境                        │
│  · AgentbaySandbox — Agentbay 集成                      │
├─────────────────────────────────────────────────────────┤
│  部署层                                                  │
│  · LocalDeployManager — 本地部署                         │
│  · Docker / K8s — 容器化部署                             │
│  · 阿里云 FC / ACK — Serverless/托管部署                 │
│  · gVisor / BoxLite — 轻量级沙箱后端                     │
├─────────────────────────────────────────────────────────┤
│  可观测性                                                │
│  · OpenTelemetry — 分布式追踪 + 指标                     │
└─────────────────────────────────────────────────────────┘
```

### 4.3 AgentApp —— Agent as API

AgentApp 是 Runtime 的核心，**直接继承 FastAPI**（v1.1.0 重构），可以使用完整的 FastAPI 生态：

```python
from agentscope_runtime.engine import AgentApp

# 1. 创建 AgentApp（继承 FastAPI）
agent_app = AgentApp(
    app_name="Friday",
    app_description="A helpful assistant",
    lifespan=lifespan,  # 生命周期管理
)

# 2. 注册查询处理函数
@agent_app.query(framework="agentscope")
async def query_func(self, msgs, request: AgentRequest = None, **kwargs):
    session_id = request.session_id
    user_id = request.user_id

    # 加载会话状态
    await agent_app.state.session.load_session_state(
        session_id=session_id, user_id=user_id, agent=agent,
    )

    # 流式输出
    async for msg, last in stream_printing_messages(
        agents=[agent], coroutine_task=agent(msgs),
    ):
        yield msg, last

    # 保存会话状态
    await agent_app.state.session.save_session_state(
        session_id=session_id, user_id=user_id, agent=agent,
    )

# 3. 启动服务
agent_app.run(host="0.0.0.0", port=8090)
# 可选：启用 Web Chat UI
# agent_app.run(host="0.0.0.0", port=8090, web_ui=True)
```

**SSE 流式响应格式：**
```
data: {"sequence_number":0,"object":"response","status":"created", ...}
data: {"sequence_number":1,"object":"response","status":"in_progress", ...}
data: {"sequence_number":2,"object":"message","status":"in_progress", ...}
data: {"sequence_number":3,"object":"content","status":"in_progress","text":"The"}
data: {"sequence_number":4,"object":"content","status":"in_progress","text":" capital..."}
data: {"sequence_number":5,"object":"message","status":"completed","text":"The capital..."}
data: {"sequence_number":6,"object":"response","status":"completed", ...}
```

**多种访问方式：**
- HTTP API：`curl -N -X POST "http://localhost:8090/process"`
- OpenAI SDK 兼容模式：`OpenAI(base_url="http://0.0.0.0:8091/compatible-mode/v1")`
- A2A 协议
- Response API

### 4.4 Distributed Interrupt Service（分布式中断服务）

v1.1.0 新增特性，支持在 Agent 执行过程中**手动抢占任务**：

- **场景：** 用户发送新消息时中断正在执行的 Agent 任务
- **机制：** 开发者可自定义状态持久化和恢复逻辑
- **实时语音中特别有用：** 用户打断对话时无缝恢复

### 4.5 沙箱系统详解

每种沙箱都有**同步 + 异步**两个实现版本：

| 沙箱 | 同步类 | 异步类 | 功能 | Docker 镜像 |
|------|--------|--------|------|------------|
| 基础 | BaseSandbox | BaseSandboxAsync | Python/Shell 执行 | `agentscope/runtime-sandbox-base:latest` |
| 桌面 | GuiSandbox | GuiSandboxAsync | 虚拟桌面（VNC） | `agentscope/runtime-sandbox-gui:latest` |
| 浏览器 | BrowserSandbox | BrowserSandboxAsync | 浏览器操作（VNC） | `agentscope/runtime-sandbox-browser:latest` |
| 文件 | FilesystemSandbox | FilesystemSandboxAsync | 文件读写删 | `agentscope/runtime-sandbox-filesystem:latest` |
| 移动 | MobileSandbox | MobileSandboxAsync | 移动端操作 | - |
| 训练 | TrainingSandbox | - | 模型训练 | - |
| Agentbay | AgentbaySandbox | - | Agentbay 集成 | - |

**BaseSandbox 使用示例：**

```python
# 同步版
from agentscope_runtime.sandbox import BaseSandbox
with BaseSandbox() as box:
    print(box.list_tools())
    print(box.run_ipython_cell(code="print('hello')"))
    print(box.run_shell_command(command="echo world"))

# 异步版
from agentscope_runtime.sandbox import BaseSandboxAsync
async with BaseSandboxAsync() as box:
    print(await box.list_tools_async())
    print(await box.run_ipython_cell(code="print('hello')"))
    print(await box.run_shell_command(command="echo world"))
```

**GuiSandbox（虚拟桌面）能力：**

| 操作 | 方法 | 说明 |
|------|------|------|
| 获取鼠标位置 | `computer_use(action="get_cursor_position")` | 返回坐标 |
| 截屏 | `computer_use(action="get_screenshot")` | 返回截图 |
| 点击 | `computer_use(action="click", x=100, y=200)` | 鼠标点击 |
| 输入 | `computer_use(action="type", text="hello")` | 键盘输入 |
| VNC 访问 | `box.desktop_url` | 返回 Web 桌面 URL |

**沙箱后端选择：**

| 后端 | 环境变量 `CONTAINER_DEPLOYMENT` | 适用场景 |
|------|-------------------------------|---------|
| Docker | `docker`（默认） | 本地开发 |
| gVisor | `gvisor` | 更强隔离 |
| BoxLite | `boxlite` | 轻量级 |
| K8s | - | 生产集群 |
| 阿里云 FC | - | Serverless |
| 阿里云 ACK | - | 托管 K8s |

### 4.6 多框架适配

| 框架 | 消息/事件 | 工具 | 文档 |
|------|----------|------|------|
| AgentScope | ✅ | ✅ | [指南](https://runtime.agentscope.io/en/quickstart.html) |
| LangGraph | ✅ | 🚧 | [指南](https://runtime.agentscope.io/en/langgraph_guidelines.html) |
| MS Agent Framework | ✅ | ✅ | [指南](https://runtime.agentscope.io/en/ms_agent_framework_guidelines.html) |
| Agno | ✅ | ✅ | [指南](https://runtime.agentscope.io/en/agno_guidelines.html) |
| AutoGen | 🚧 | ✅ | 开发中 |

### 4.7 部署流程

```
开发三阶段模式：

1. init  ──→  lifespan 函数（资源初始化/清理）
                │
2. query ──→  @agent_app.query() 装饰器（核心逻辑）
                │
3. deploy ──→  DeployManager（部署方式选择）
                │
                ├─→ LocalDeployManager（本地）
                ├─→ Docker Compose
                ├─→ K8s Deployment
                └─→ 阿里云 FC / ACK（Serverless/托管）
```

```python
# 本地部署
from agentscope_runtime.engine.deployers import LocalDeployManager

async def main():
    await agent_app.deploy(LocalDeployManager(host="0.0.0.0", port=8091))
```

---

## 五、ReMe 记忆框架详解

### 5.1 定位

**"Remember Me, Refine Me"** —— 解决 Agent 记忆的两个核心痛点：
1. **上下文窗口有限** — 长对话中早期信息被截断或丢失
2. **会话无状态** — 新会话无法继承历史，每次从零开始

**核心理念：Memory as Files, Files as Memory** —— 把记忆当文件，可读、可编辑、可复制迁移。

### 5.2 双系统架构

#### 5.2.1 文件记忆系统（ReMeLight）

ReMeLight 是核心类，提供完整的 Agent 记忆管理能力：

```
working_dir/
├── MEMORY.md              # 长期记忆（用户偏好等持久信息）
├── memory/
│   └── YYYY-MM-DD.md      # 每日日志（对话后自动写入）
├── dialog/
│   └── YYYY-MM-DD.jsonl   # 原始对话记录（压缩前完整保存）
└── tool_result/
    └── <uuid>.txt         # 工具输出缓存（自动过期清理）
```

**vs 传统记忆系统：**

| 维度 | 传统方案 | ReMe |
|------|---------|------|
| 存储 | 🗄️ 数据库 | 📝 Markdown 文件 |
| 透明度 | 🔒 不透明 | 👀 随时可读 |
| 修改 | ❌ 难以修改 | ✏️ 直接编辑 |
| 迁移 | 🚫 难以迁移 | 📦 复制即迁移 |
| 调试 | 需要专用工具 | 任何文本编辑器 |

#### 5.2.2 向量记忆系统

基于 embedding + BM25 的混合检索系统：
- **向量检索** — embedding 语义匹配（理解意图）
- **BM25** — 关键词精确匹配（精确召回）
- **混合检索** — 两者融合，兼顾语义理解和精确匹配
- **FileWatcher** — 文件变更自动更新索引（实时同步）

### 5.3 ReMeLight API 详解

| 类别 | 方法 | 功能 | 核心组件 |
|------|------|------|---------|
| **上下文管理** | `check_context` | 📊 检查上下文大小 | ContextChecker — token 计数 + 消息分割 |
| | `compact_memory` | 📦 压缩历史为摘要 | Compactor — ReActAgent 生成结构化摘要 |
| | `compact_tool_result` | ✂️ 压缩过长工具输出 | ToolResultCompactor — 截断 + 存文件 + 保留引用 |
| | `pre_reasoning_hook` | 🔄 推理前钩子 | 串联上述三步 + 异步持久化 |
| **长期记忆** | `summary_memory` | 📝 持久化重要记忆 | Summarizer — ReActAgent + 文件工具 |
| | `memory_search` | 🔍 语义记忆搜索 | MemorySearch — 向量 + BM25 混合检索 |
| **会话记忆** | `get_in_memory_memory` | 💾 创建会话内记忆 | ReMeInMemoryMemory + dialog_path |
| | `await_summary_tasks` | ⏳ 等待异步摘要任务 | 阻塞直到后台任务完成 |
| **生命周期** | `start` | 🚀 启动记忆系统 | 初始化文件存储/FileWatcher/embedding 缓存 |
| | `close` | 📕 关闭并清理 | 清理 tool_result + 停止 FileWatcher + 持久化缓存 |

### 5.4 核心流程图

```
Agent 推理前
    │
    ▼
pre_reasoning_hook（自动执行）
    │
    ├─→ compact_tool_result（压缩过长的工具输出）
    │       │
    │       ├─→ 工具输出 > 阈值？
    │       │       │
    │       │       ├─→ 是：截断内容 → 存入 tool_result/<uuid>.txt
    │       │       │         └─→ 原消息替换为文件引用
    │       │       └─→ 否：保持不变
    │       │
    │       └─→ 可配置保留最近 N 个工具结果不压缩
    │
    ├─→ check_context（token 计数）
    │       │
    │       ├─→ AsMsgHandler 计算所有消息 token 数
    │       │
    │       ├─→ total_tokens > memory_compact_threshold ?
    │       │       │
    │       │       ├─→ 否 → 返回所有消息（无需压缩）
    │       │       │
    │       │       └─→ 是 → 从尾部保留 memory_compact_reserve tokens
    │       │              │
    │       │              ├─→ messages_to_compact（较早的消息）
    │       │              ├─→ messages_to_keep（较新的消息）
    │       │              └─→ is_valid（工具调用对是否完整）
    │       │
    │       └─→ 完整性保证：不拆分 user-assistant 对和 tool_use/tool_result 对
    │
    ├─→ compact_memory（生成结构化摘要）
    │       │
    │       ├─→ AsMsgHandler.format_msgs_to_str（格式化消息为字符串）
    │       │
    │       ├─→ ReActAgent（reme_compactor）生成摘要
    │       │       │
    │       │       ├─→ 首次压缩：initial_user_message 提示
    │       │       └─→ 增量压缩：previous_summary + update 提示
    │       │
    │       └─→ 输出结构化摘要（见 5.5 节）
    │
    └─→ summary_memory（异步持久化）
            │
            ├─→ ReActAgent（reme_summarizer）+ 文件工具
            │       │
            │       ├─→ read：读取 memory/YYYY-MM-DD.md
            │       ├─→ 推理：如何合并新旧内容
            │       ├─→ write：覆盖写入
            │       └─→ edit：find-and-replace 精确编辑
            │
            └─→ mark_messages_compressed
                    └─→ 原始对话存入 dialog/YYYY-MM-DD.jsonl
```

### 5.5 上下文压缩结构（Context Checkpoints）

Compactor 生成的**结构化摘要**格式：

| 字段 | 内容 | 说明 |
|------|------|------|
| `## Goal` | 用户目标 | 当前对话的核心目标 |
| `## Constraints` | 约束和偏好 | 用户限制条件和偏好设置 |
| `## Progress` | 任务进度 | 已完成的步骤和当前状态 |
| `## Key Decisions` | 关键决策 | 重要的选择和原因 |
| `## Next Steps` | 下一步计划 | 待执行的操作 |
| `## Critical Context` | 关键数据 | 文件路径、函数名、错误信息等不能丢失的数据 |

**增量更新机制：**
- 首次压缩：从对话中提取上述六个维度
- 后续压缩：将新对话内容**合并**到已有摘要中（而非替换）
- Compactor 内部使用 ReActAgent 做推理，确保摘要质量

**压缩效果实测：** 223,838 tokens → 1,105 tokens（**99.5% 压缩率**）

### 5.6 核心组件源码解析

#### ContextChecker（上下文检查器）

```
源码路径：reme/memory/file_based/components/context_checker.py

输入：messages（对话消息列表）
参数：
  - memory_compact_threshold：触发压缩的 token 阈值
  - memory_compact_reserve：为最近消息保留的 token 数
  
断言：threshold > reserve（保证逻辑正确）

流程：
  messages → AsMsgHandler.context_check()
          → 计算总 token 数
          → 如果超过阈值：从尾部保留 reserve tokens
          → 返回 (messages_to_compact, messages_to_keep, is_valid)

is_valid = False 表示拆分会破坏 tool_use/tool_result 配对
```

#### Compactor（压缩器）

```
源码路径：reme/memory/file_based/components/compactor.py

输入：messages + previous_summary（可选）
参数：memory_compact_threshold

流程：
  1. AsMsgHandler.format_msgs_to_str() 格式化消息
  2. 记录 token 变化：before_token_count → after_token_count
  3. 构建 ReActAgent（reme_compactor）
  4. 根据是否有 previous_summary 选择提示模板：
     - 有：update_user_message_prefix/suffix 模板
     - 无：initial_user_message 模板
  5. Agent 推理生成结构化摘要
  6. 返回压缩后的文本
```

#### Summarizer（持久化器）

```
源码路径：reme/memory/file_based/components/summarizer.py

输入：messages（需要持久化的对话）
工具：FileIO（read/write/edit）

流程：
  1. ReActAgent（reme_summarizer）接收消息
  2. Agent 自主决定：
     - read → 读取 memory/YYYY-MM-DD.md 了解已有内容
     - 推理 → 决定如何合并（覆盖 vs 追加 vs 精确编辑）
     - write → 覆盖写入新内容
     - edit → find-and-replace 精确修改
  3. 结果：memory/YYYY-MM-DD.md 更新完成
```

#### ToolResultCompactor（工具输出压缩器）

```
源码路径：reme/memory/file_based/components/tool_result_compactor.py

输入：messages（含工具输出的消息列表）
参数：tool_result_compact_keep_n（保留最近 N 个不压缩）

流程：
  1. 扫描消息中的工具输出
  2. 如果工具输出超过阈值：
     - 将完整输出存入 tool_result/<uuid>.txt
     - 原消息中替换为文件引用
  3. 最近 N 个工具输出保持不变（通常最新的还有用）
  4. 过期的 tool_result 文件在 start()/close() 时自动清理
```

### 5.7 使用示例

```python
import asyncio
from reme.reme_light import ReMeLight

async def main():
    # 初始化 ReMeLight
    reme = ReMeLight(
        default_as_llm_config={"model_name": "qwen3.5-35b-a3b"},
        default_file_store_config={
            "fts_enabled": True,      # 全文搜索
            "vector_enabled": False,  # 向量搜索（需要 embedding key）
        },
    )
    await reme.start()

    messages = [...]  # 对话消息列表

    # 1. 检查上下文（是否需要压缩）
    msgs_to_compact, msgs_to_keep, is_valid = await reme.check_context(
        messages=messages,
        memory_compact_threshold=90000,   # 超过 90k tokens 触发压缩
        memory_compact_reserve=10000,     # 保留最近 10k tokens
    )

    # 2. 压缩对话历史
    summary = await reme.compact_memory(
        messages=messages,
        previous_summary="",              # 首次压缩无前置摘要
        max_input_length=128000,          # 模型上下文窗口
        compact_ratio=0.7,                # 使用 70% 窗口时触发
        language="zh",                    # 摘要语言
    )

    # 3. 压缩过长工具输出
    messages = await reme.compact_tool_result(messages)

    # 4. 一键式推理前处理（串联 1-3 步）
    processed_msgs, compressed_summary = await reme.pre_reasoning_hook(
        messages=messages,
        system_prompt="You are a helpful AI assistant.",
        compressed_summary="",
        max_input_length=128000,
        compact_ratio=0.7,
        memory_compact_reserve=10000,
        enable_tool_result_compact=True,
        tool_result_compact_keep_n=3,     # 保留最近 3 个工具输出
    )

    # 5. 持久化重要记忆到文件
    await reme.summary_memory(messages=messages, language="zh")

    # 6. 语义搜索历史记忆
    result = await reme.memory_search(
        query="Python version preference",
        max_results=5,
    )

    # 7. 会话内记忆管理
    memory = reme.get_in_memory_memory()
    for msg in messages:
        await memory.add(msg)
    token_stats = await memory.estimate_tokens(max_input_length=128000)
    print(f"上下文使用率: {token_stats['context_usage_ratio']:.1f}%")
    print(f"消息 token 数: {token_stats['messages_tokens']}")
    print(f"预估总 token: {token_stats['estimated_tokens']}")

    await reme.close()

asyncio.run(main())
```

### 5.8 CoPaw 中的集成

CoPaw 的 `MemoryManager` 继承 `ReMeLight`，将记忆能力集成到 Agent 推理循环中：

```
CoPaw MemoryManager（继承 ReMeLight）

每次推理前自动执行：
    pre_reasoning_hook
        │
        ├─→ compact_tool_result（压缩工具输出）
        ├─→ check_context（token 计数）
        ├─→ compact_memory（超限时生成摘要）
        ├─→ summary_memory（异步写入 memory/*.md）
        └─→ mark_messages_compressed（原始对话存入 dialog/*.jsonl）

Agent 主动调用：
    memory_search（向量 + BM25 混合检索）

会话内管理：
    ReMeInMemoryMemory（token 感知的消息管理）
        └─→ 压缩/清理时自动持久化到 dialog/*.jsonl

后台索引：
    FileWatcher 监控 memory/*.md 文件变更
        └─→ 自动更新 FileStore（向量 + 全文搜索索引）
```

### 5.9 环境配置

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `LLM_API_KEY` | LLM API Key | sk-xxx |
| `LLM_BASE_URL` | LLM Base URL | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| `EMBEDDING_API_KEY` | Embedding API Key（可选） | sk-xxx |
| `EMBEDDING_BASE_URL` | Embedding Base URL（可选） | https://dashscope.aliyuncs.com/compatible-mode/v1 |

---

## 六、CoPaw 功能详解

### 6.1 渠道支持

| 渠道 | 状态 | 特色功能 |
|------|------|----------|
| 钉钉 | ✅ | @mention 过滤 |
| 飞书 | ✅ | emoji 回复 + 富文本 |
| QQ | ✅ | 图片发送 |
| Discord | ✅ | @mention + 2000 字分割 |
| iMessage | ✅ | - |
| Telegram | ✅ | Markdown 渲染 |
| Mattermost | ✅ | v0.0.7 新增 |
| Matrix | ✅ | v0.0.7 新增 |
| MQTT | ✅ | IoT 场景 |

### 6.2 特色功能

| 功能 | 说明 |
|------|------|
| Skills | 工作空间中的自定义技能，自动加载 |
| Cron | 内置定时任务 |
| MCP | 管理 MCP 客户端 |
| Magic Commands | 控制对话状态（不等 AI 响应） |
| Heartbeat | 定时心跳检查 |
| Tool Guard | 安全层——拦截高风险工具调用等用户审批 |
| 本地模型 | llama.cpp / MLX / Ollama / LM Studio |
| Token 追踪 | 用量仪表盘 |
| Web Console | http://127.0.0.1:8088 可视化配置 |

### 6.3 部署方式

| 方式 | 命令/说明 |
|------|----------|
| pip 安装 | `pip install copaw && copaw init --defaults && copaw app` |
| 脚本安装 | `curl -fsSL https://copaw.agentscope.io/install.sh \| bash` |
| Docker | `docker pull agentscope/copaw:latest` |
| 桌面应用 | Windows (.exe) / macOS (.zip) — Beta |
| ModelScope | 一键云端部署 |
| 阿里云 ECS | 一键部署 |

---

## 七、Roadmap 关键方向

| 方向 | 状态 |
|------|------|
| 更多渠道/模型/技能/MCP | 社区共建中 |
| Console Web UI 增强 | 进行中 |
| 自愈能力（DaemonAgent） | 计划中 |
| 多 Agent 后台任务 | 进行中 |
| 多 Agent 隔离 + 通信 | 计划中 |
| 实时语音/视频交互 | 进行中 |
| 大小模型协作路由 | 计划中 |
| 经验蒸馏 + 技能提取 | 进行中 |
| AgentScope Runtime 沙箱深度集成 | 长期计划 |

---

## 八、总结

1. **Python 生态的 OpenClaw 替代** — CoPaw 提供了几乎对等的功能集（多渠道/技能/心跳/记忆），且有更好的 Web UI 和桌面应用
2. **框架分层清晰** — AgentScope（核心）+ Runtime（部署）+ ReMe（记忆）+ CoPaw（产品），各层职责明确
3. **AgentScope 设计哲学独特** — "随模型能力提升而设计"，不用严格 prompt 约束模型，而是利用模型的推理和工具能力
4. **Runtime 架构成熟** — 继承 FastAPI、支持 SSE 流式、分布式中断、7 种沙箱、5 种框架适配、多种部署方式
5. **ReMe 记忆系统创新** — "文件即记忆"设计比传统数据库方案更透明可控，99.5% 压缩率实用性强，源码级模块化清晰
6. **沙箱能力强大** — 7 种沙箱类型覆盖代码/桌面/浏览器/文件/移动端/训练/Agentbay，支持 Docker/K8s/gVisor/BoxLite
7. **Agentic RL 集成** — 直接用 RL 训练 Agent 策略，6 个场景有实际效果数据支撑
8. **阿里生态加持** — DashScope、ModelScope、阿里云一键部署，中国开发者友好
