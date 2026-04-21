# 多模型架构改造方案

## 1. 当前现状与主要问题

当前项目已经有基础的模型切换能力，但实现仍然偏“单网关 + 少量别名”的形态，扩展到多个 provider / 多种国产 thinking 模型时会快速失控。

### 1.1 当前实现位置

- 模型配置集中在 [src_deepagent/config/settings.py](/Users/zhangyang/Desktop/temp/super-agent/src_deepagent/config/settings.py:13)
- 模型创建逻辑集中在 [src_deepagent/llm/config.py](/Users/zhangyang/Desktop/temp/super-agent/src_deepagent/llm/config.py:1)
- 主 Agent 固定使用 `get_model("orchestrator")`，见 [src_deepagent/orchestrator/agent_factory.py](/Users/zhangyang/Desktop/temp/super-agent/src_deepagent/orchestrator/agent_factory.py:84)
- Sub-Agent 固定使用 `get_model("subagent")`，见 [src_deepagent/agents/factory.py](/Users/zhangyang/Desktop/temp/super-agent/src_deepagent/agents/factory.py:68)
- Planner 也复用 `orchestrator` 模型，见 [src_deepagent/capabilities/base_tools.py](/Users/zhangyang/Desktop/temp/super-agent/src_deepagent/capabilities/base_tools.py:224)
- Claude thinking 特判写在 [src_deepagent/gateway/rest_api.py](/Users/zhangyang/Desktop/temp/super-agent/src_deepagent/gateway/rest_api.py:267)

### 1.2 主要问题

1. `settings.py` 只支持少量固定字段
   - 当前只有 `orchestrator_model` / `subagent_model` / `classifier_model`
   - 每新增一个角色或路由档位，都要改配置类和环境变量

2. `llm/config.py` 通过模型名猜测 provider
   - 现在通过 `"claude" in model_name.lower()` 判断是否走 Anthropic 原生路径
   - 这种方式无法稳定支持 Qwen、Kimi、Doubao、DeepSeek、GLM、Gemini 等不同供应商和网关入口

3. 运行时能力差异没有建模
   - 哪些模型支持 reasoning
   - 哪些模型支持原生 tool calling
   - 哪些模型在 tool call 时要求 `reasoning_content`
   - 哪些模型只支持 OpenAI 兼容协议但字段要求不同
   - 这些差异现在散落在业务逻辑里，没有统一能力层

4. thinking 策略写死在 API 层
   - `rest_api.py` 直接构造 `AnthropicModelSettings`
   - 这意味着接入其他 thinking 模型时，还要继续在网关层堆 if/else

5. 角色与模型绑定过死
   - `orchestrator` / `subagent` / `classifier` 只是少量别名
   - 无法优雅支持 `planner`、`fast_router`、`tool_reasoner`、`sandbox_pi` 等更细颗粒度角色

6. 新模型接入成本高
   - 要同时改 settings、模型工厂、调用链特判
   - 缺少统一注册表和能力描述，代码可维护性会越来越差


## 2. 改造目标

这次改造建议明确 5 个目标：

1. 支持多个 provider
   - OpenAI
   - Anthropic
   - OpenAI-compatible gateway
   - Gemini
   - Ollama
   - 国产网关模型

2. 支持多个“逻辑角色”
   - orchestrator
   - planner
   - subagent
   - classifier
   - fast_router
   - sandbox_pi

3. 支持模型能力声明
   - 是否支持 streaming
   - 是否支持 tool calling
   - 是否支持 reasoning
   - 是否要求 tool call assistant message 带 `reasoning_content`
   - 是否需要 provider-native settings

4. 支持动态增加新模型
   - 新增配置即可生效
   - 尽量不改业务代码
   - 最多只补一个 provider 适配器

5. 让业务代码只依赖“逻辑模型角色”
   - 业务层不直接关心 provider
   - 业务层不直接构造 provider-specific settings
   - 业务层只说“我要 planner 模型”或“我要 orchestrator 模型”


## 3. 目标架构

建议把当前 `src_deepagent/llm/` 重构为 4 层：

### 3.1 模型目录层 `catalog`

负责描述“系统里有哪些 provider / model profile / role binding”。

建议新增：

- `src_deepagent/llm/catalog.py`
- `src_deepagent/llm/schemas.py`

核心对象：

- `ProviderConfig`
- `ModelProfile`
- `RoleBinding`
- `ModelCapabilities`

建议结构：

```python
class ModelCapabilities(BaseModel):
    streaming: bool = True
    tool_calling: bool = True
    reasoning: bool = False
    requires_reasoning_content_on_tool_call: bool = False
    supports_native_thinking: bool = False
    supports_openai_compat: bool = True
    supports_anthropic_native: bool = False


class ProviderConfig(BaseModel):
    name: str
    kind: Literal["openai", "anthropic", "openai_compat", "gemini", "ollama"]
    api_key_env: str | None = None
    base_url_env: str | None = None
    default_headers: dict[str, str] = {}
    timeout: int = 60


class ModelProfile(BaseModel):
    name: str
    provider: str
    model: str
    transport: Literal["openai_compat", "anthropic_native"]
    capabilities: ModelCapabilities
    default_params: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class RoleBinding(BaseModel):
    role: str
    model_profile: str
```

### 3.2 Provider 适配层 `providers`

负责把 `ModelProfile` 转成真正可执行的模型实例与运行时参数。

建议新增：

- `src_deepagent/llm/providers/base.py`
- `src_deepagent/llm/providers/openai_compat.py`
- `src_deepagent/llm/providers/anthropic_native.py`

职责：

- 创建 `PydanticAI` 模型对象
- 返回 provider-specific `model_settings`
- 处理默认 header / auth / base_url
- 隔离 provider 差异

### 3.3 运行时策略层 `runtime`

负责根据“当前角色 + 当前模式 + 当前模型能力”计算本次调用策略。

建议新增：

- `src_deepagent/llm/runtime.py`

职责：

- 根据 role 获取 `ModelProfile`
- 根据执行模式产出 `RunModelPolicy`
- 统一生成 `iter_kwargs["model_settings"]`
- 处理 thinking 预算
- 处理 tool call / reasoning 兼容策略

### 3.4 Facade 层 `registry`

保留一个业务友好的入口，替代当前 `get_model()`。

建议新增：

- `src_deepagent/llm/registry.py`

对外暴露：

- `get_model_for_role(role: str)`
- `get_runtime_policy(role: str, execution_mode: str)`
- `get_model_bundle(role: str, execution_mode: str)`

其中 `bundle` 统一返回：

```python
class ModelBundle(NamedTuple):
    model: Any
    profile: ModelProfile
    provider: ProviderConfig
    runtime_settings: Any | None
```


## 4. 配置设计

### 4.1 不建议继续只靠零散环境变量

当前这类配置：

```bash
OPENAI_API_KEY=...
OPENAI_API_BASE=...
ORCHESTRATOR_MODEL=...
SUBAGENT_MODEL=...
CLASSIFIER_MODEL=...
```

只适合单 provider 或非常少的角色，不适合多模型系统。

### 4.2 建议采用“一个主配置 + 少量环境变量注入 secret”

推荐方案：

1. provider / model / role 关系写入 `yaml`
2. api_key / secret 继续从环境变量读取
3. 配置文件支持热加载或启动时加载

建议新增：

- `config/models.yaml`

示例：

```yaml
providers:
  rd_gateway:
    kind: openai_compat
    api_key_env: OPENAI_API_KEY
    base_url_env: OPENAI_API_BASE
    timeout: 60

  anthropic_gateway:
    kind: anthropic
    api_key_env: OPENAI_API_KEY
    base_url_env: OPENAI_API_BASE
    timeout: 60

models:
  claude_orchestrator:
    provider: anthropic_gateway
    model: claude-4.6-sonnet
    transport: anthropic_native
    capabilities:
      streaming: true
      tool_calling: true
      reasoning: true
      supports_native_thinking: true

  kimi_k25_reasoner:
    provider: rd_gateway
    model: kimi-k2.5
    transport: openai_compat
    capabilities:
      streaming: true
      tool_calling: true
      reasoning: true
      requires_reasoning_content_on_tool_call: true

  qwen_fast:
    provider: rd_gateway
    model: qwen3.5-plus
    transport: openai_compat
    capabilities:
      streaming: true
      tool_calling: true
      reasoning: false

roles:
  orchestrator: claude_orchestrator
  planner: kimi_k25_reasoner
  subagent: qwen_fast
  classifier: qwen_fast
  sandbox_pi: qwen_fast
```

### 4.3 `settings.py` 的改造方向

将当前 `LLMSettings` 从“具体模型字段集合”改成“配置入口 + 默认值”：

建议保留：

- `LLM_CONFIG_PATH`
- `LLM_REQUEST_TIMEOUT`
- `LLM_ENABLE_LITELLM`
- 可选的 fallback 环境变量

不再在 `settings.py` 里硬编码：

- `orchestrator_model`
- `subagent_model`
- `classifier_model`


## 5. 动态增加新模型的机制

### 5.1 新增同类模型

如果新模型仍然走已有 provider 适配器，例如：

- 新增 `deepseek-r1`
- 新增 `glm-5`
- 新增 `doubao`
- 新增 `gemini` 的 OpenAI-compatible 网关入口

则只需要：

1. 在 `models.yaml` 增加一个 `models.xxx`
2. 给出 capabilities
3. 在 `roles` 中把某个角色切到它

业务代码不需要改。

### 5.2 新增新 provider

如果新模型需要新的协议或新的 SDK：

1. 新增一个 provider adapter
2. 在 `providers/` 里实现
3. 注册到 provider factory
4. `models.yaml` 中引用该 provider

此时仍然不需要改 orchestrator / gateway / agents 业务代码。

### 5.3 动态加载与热更新

建议提供一个简单的 registry reload 能力：

- `load_model_catalog(path)`
- `reload_model_catalog()`

触发方式：

- 启动时加载
- 运维接口手动 reload
- 配置文件变更时 reload（可选）

可复用现有的 `/admin/reload-mcp` 风格，再增加：

- `/admin/reload-models`


## 6. 业务调用链如何改

### 6.1 `llm/config.py` 的职责收缩

当前文件同时负责：

- 读 settings
- alias 映射
- provider 判断
- 模型实例化

建议将其拆掉，变成兼容层或直接废弃。

### 6.2 `agent_factory.py`

当前：

```python
model=get_model("orchestrator")
```

改成：

```python
bundle = get_model_bundle(role="orchestrator", execution_mode=plan.mode.value)
model=bundle.model
model_settings=bundle.runtime_settings
```

如果 `create_deep_agent()` 初始化阶段不接收 `model_settings`，那就在运行阶段传入。

### 6.3 `agents/factory.py`

当前 sub-agent 固定拿 `get_model("subagent")`。

建议改成按角色或 profile 获取：

```python
subagent_bundle = get_model_bundle(role="subagent", execution_mode="sub_agent")
```

后续若要支持不同 sub-agent 角色用不同模型，也能继续扩展：

- `researcher -> research_model`
- `analyst -> analysis_model`
- `writer -> writing_model`

### 6.4 `base_tools.py`

Planner 不应复用 orchestrator 模型。

当前：

```python
model=get_model("orchestrator")
```

建议改成：

```python
model=get_model_bundle(role="planner", execution_mode="plan_and_execute").model
```

### 6.5 `rest_api.py`

当前最需要收口的点是 Claude thinking 特判。

现在是：

- API 层自己知道 AnthropicModelSettings
- API 层自己计算 budget_tokens

改造后应该由 `runtime policy` 统一产出：

```python
bundle = get_model_bundle(role="orchestrator", execution_mode=decision.mode.value)
iter_kwargs["model_settings"] = bundle.runtime_settings
```

这样 `rest_api.py` 不再知道 Claude、Kimi、Qwen 的细节。


## 7. thinking / tool calling 兼容策略

这是这次改造里最关键的部分，必须单独建模。

### 7.1 需要抽象的能力字段

至少需要这些：

- `reasoning`
- `supports_native_thinking`
- `requires_reasoning_content_on_tool_call`
- `tool_calling`
- `streaming`

### 7.2 统一策略

建议定义：

```python
class ToolCallCompatibilityPolicy(BaseModel):
    inject_reasoning_content: bool = False
    reasoning_content_template: str = "需要调用工具以获取必要信息。"
```

对于类似 Kimi / Qwen 的 thinking 模型，如果通过 OpenAI-compatible 链路并且它要求：

- assistant tool call message 必须带 `reasoning_content`

则在协议转换层统一补齐，不要让上层业务代码知道这个要求。

### 7.3 不要把兼容逻辑写进业务路由

错误示范：

- 在 `rest_api.py` 判断“如果是 kimi 就补 reasoning_content”
- 在 `agent_factory.py` 判断“如果是 qwen 就换另一条调用路径”

正确做法：

- provider adapter 或 protocol transformer 负责处理协议差异
- 上层只拿标准的 model bundle


## 8. 推荐的目录结构

建议把 `src_deepagent/llm/` 调整成：

```text
src_deepagent/llm/
  __init__.py
  schemas.py
  catalog.py
  registry.py
  runtime.py
  compatibility.py
  providers/
    __init__.py
    base.py
    openai_compat.py
    anthropic_native.py
```

职责划分：

- `schemas.py`: 数据结构
- `catalog.py`: 从 yaml/env 读取配置
- `registry.py`: role -> profile -> provider 的解析入口
- `runtime.py`: execution_mode -> model_settings
- `compatibility.py`: tool_call / reasoning_content / transport 兼容处理
- `providers/*`: provider 适配器


## 9. 分阶段迁移建议

建议分 4 个阶段，不要一次性重构到底。

### Phase 1: 建立配置中心和注册表

目标：

- 引入 `models.yaml`
- 引入 `catalog.py` / `schemas.py` / `registry.py`
- 保留旧的 `get_model()` 作为兼容层

收益：

- 不改业务行为
- 先把“模型定义”从代码里抽出来

### Phase 2: 收口运行时设置

目标：

- 把 `rest_api.py` 中 Claude thinking 特判迁移到 `runtime.py`
- 让 orchestrator / planner / subagent 都通过 `bundle` 获取模型与 settings

收益：

- 业务层不再关心 provider-specific settings

### Phase 3: 引入能力声明与兼容策略

目标：

- 支持 `requires_reasoning_content_on_tool_call`
- 支持不同 transport
- 支持按模型能力调整调用策略

收益：

- thinking 模型兼容问题集中治理
- 新增国产模型成本显著下降

### Phase 4: 细化角色与路由策略

目标：

- planner / classifier / researcher / analyst / writer 可独立绑定模型
- 支持 fallback chain、熔断、降级

收益：

- 成本、延迟、效果可精细优化


## 10. 推荐的最小落地改造

如果本轮只做“最值回票价”的部分，建议优先做这 5 件事：

1. 引入 `models.yaml`
   - 先把 provider、model、role 关系从代码中拿出来

2. 新建 `ModelProfile` 和 `ProviderConfig`
   - 先别追求全功能，先把配置模型规范起来

3. 新建 `get_model_bundle(role, execution_mode)`
   - 替代单纯的 `get_model(alias)`

4. 把 `rest_api.py` 中 thinking 特判迁移到 `runtime.py`
   - 这是当前最明显的坏味道

5. 让 planner 使用独立角色
   - 不再复用 orchestrator 模型


## 11. 结论

当前项目的问题不在于“能不能切模型”，而在于“模型能力、provider 差异、业务角色、运行时策略”混在了一起。

建议本次重构遵循两个原则：

1. 业务代码只面向角色，不面向 provider
2. 协议差异和模型能力差异统一沉到 LLM 层

按这个方向改造后，后面新增一个国产 thinking 模型的成本应当收敛到：

- 已有 provider 路径：只改 `models.yaml`
- 新 provider 路径：新增一个 adapter，再改 `models.yaml`

这才是后续可维护的多模型架构。


## 12. Claude 原生流式兼容问题记录

### 12.1 问题现象

在接入 `Claude + Anthropic 原生协议 + true streaming` 后，运行时出现如下错误：

```text
TypeError: 'AnthropicAsyncStream' object does not support the asynchronous context manager protocol
```

错误栈定位到：

- `.venv/lib/python3.12/site-packages/pydantic_ai/models/anthropic.py`
- `request_stream()` 内部的 `async with response:`

### 12.2 根因判断

这不是业务层模型路由、YAML 配置或流式开关的错误，而是 `pydantic_ai` 对 Anthropic SDK streaming 返回对象的适配不兼容。

当前调用链为：

1. 业务层调用 `agent.run(..., event_stream_handler=...)`
2. `pydantic_ai` 进入 `AnthropicModel.request_stream()`
3. `pydantic_ai` 底层继续调用 `anthropic.AsyncAnthropic`
4. Anthropic SDK 返回 `AnthropicAsyncStream`
5. `pydantic_ai` 假设该对象支持 `async with`
6. 实际不支持，导致流式入口直接报错

结论：

- `pydantic_ai` 并不是自研完整 Claude 协议栈，而是封装在 Anthropic SDK 之上
- 问题本质是 `pydantic_ai` 的 Anthropic 原生流式适配缺陷

### 12.3 版本排查结论

已做过两轮验证：

1. 升级到最新版
   - `anthropic 0.96.0`
   - `pydantic-ai 1.84.1`
   - 仍然报同样错误

2. 降级 Anthropic SDK
   - `anthropic 0.86.0`
   - `pydantic-ai 1.84.1`
   - 仍然报同样错误

结论：

- 该问题不能简单归因为 Anthropic SDK 新旧版本变化
- 更可能是 `pydantic_ai` 当前 Anthropic streaming 适配实现本身存在兼容问题

### 12.4 当前解决方案

项目内在 [src_deepagent/llm/providers/anthropic_native.py](/Users/zhangyang/Desktop/temp/super-agent/src_deepagent/llm/providers/anthropic_native.py:1) 增加了 `CompatibleAnthropicModel`，替代标准 `AnthropicModel` 用于 Claude 原生流式场景。

修复思路：

- 不再走 `async with response`
- 直接消费 Anthropic SDK 返回的 stream 对象
- 在 `finally` 中显式 `close()`

这样可以继续保留：

- Claude 原生协议
- true streaming 能力
- 现有 `pydantic_ai` 上层 Agent 抽象

### 12.5 当前推荐配置

针对产品交互体验，推荐使用以下开关组合：

```bash
LLM_TRUE_STREAMING_ENABLED=true
LLM_STREAM_THINKING_ENABLED=true
LLM_STREAM_TEXT_ENABLED=false
```

这样行为为：

- thinking 流式输出
- 正文不逐字流式
- 最终答案整段返回

### 12.6 后续建议

1. 将 `CompatibleAnthropicModel` 视为项目内兼容补丁，短期保留
2. 如后续 `pydantic_ai` 官方修复 Anthropic streaming 适配，再评估移除补丁
3. 若要向外部反馈问题，可基于当前报错栈向 `pydantic_ai` 提 issue


## 13. Claude 模型测试结论

### 13.1 本轮覆盖范围

本轮已覆盖 Claude 的三个典型档位：

1. Sonnet
   - `claude-4.6-sonnet`
2. Opus
   - `claude-4.7-opus`
3. Haiku
   - `claude-4.5-haiku`

三者都通过 `anthropic_native` 路径接入，底层仍然走公司网关的 Anthropic 原生协议入口。

### 13.2 Sonnet 4.6 结论

`claude-4.6-sonnet` 当前是 Claude 家族里最稳定的测试样本。

结论：

- 原生 Anthropic 协议调用可用
- thinking 参数使用 `enabled + budget_tokens`
- 在手工调网关原始接口时，明确可以看到 `content[].type == "thinking"` 的返回块
- 在项目集成链路里，适合作为“稳定展示 thinking”的 Claude 默认模型

当前传参方式：

```python
AnthropicModelSettings(
    anthropic_thinking={
        "type": "enabled",
        "budget_tokens": ...
    },
    max_tokens=...
)
```

### 13.3 Opus 4.7 结论

`claude-4.7-opus` 能调用成功，但和 `4.6-sonnet` 在 thinking 参数上存在重要差异。

已确认差异：

- 不支持 `thinking.type = enabled`
- 不支持 `budget_tokens`
- 需要使用：
  - `anthropic_thinking={"type": "adaptive"}`
  - `anthropic_effort="medium" | "high" | ...`

本轮排查中遇到的问题：

1. 按 `4.6` 参数调用时报 400
   - 错误明确提示：
     - `thinking.type.enabled` 不被支持
     - 需要 `adaptive + effort`

2. 初版适配时误用了 `anthropic_output_config`
   - 该字段不是 `pydantic_ai` 识别的 Anthropic thinking 配置入口
   - 正确字段是 `anthropic_effort`

3. 调整为 `adaptive + anthropic_effort` 后
   - 正文能正常返回
   - 但当前仍**没有稳定拿到可见的思考过程**

当前判断：

- `claude-4.7-opus` 并非不可用
- 但其 thinking 机制比 `4.6-sonnet` 更依赖模型自身判断
- 同时不排除网关 / Bedrock / `pydantic_ai` 在 `adaptive` thinking summarization 透传上存在兼容问题

当前状态结论：

- `4.7-opus` 已可正常调用
- `4.7-opus` 当前**未稳定返回思考过程**
- 若产品需要稳定展示 thinking，不建议当前默认使用 `4.7-opus`

当前传参方式：

```python
AnthropicModelSettings(
    anthropic_thinking={"type": "adaptive"},
    anthropic_effort="medium",
    max_tokens=...
)
```

### 13.4 Haiku 4.5 结论

`claude-4.5-haiku` 当前已确认可以调用成功。

当前项目里由于 provider 分支逻辑是：

- `4.7` 单独走 `adaptive + effort`
- 其他 Claude 默认走 `enabled + budget_tokens`

因此 `claude-4.5-haiku` 目前走的是和 `4.6-sonnet` 相同的参数路径：

```python
AnthropicModelSettings(
    anthropic_thinking={
        "type": "enabled",
        "budget_tokens": ...
    },
    max_tokens=...
)
```

当前结论：

- `haiku` 已经可调用
- 当前暂未单独深挖其 thinking 返回特性
- 现阶段可视为轻量、低成本的 Claude 可用模型

### 13.5 流式问题结论

Claude 原生流式本轮还确认了一个重要问题：

- `pydantic_ai` 默认 Anthropic streaming 实现和 Anthropic SDK 返回对象存在兼容问题
- 具体表现为：

```text
TypeError: 'AnthropicAsyncStream' object does not support the asynchronous context manager protocol
```

当前项目已通过 `CompatibleAnthropicModel` 在 provider 层做兼容修复。

结论：

- 这不是业务层问题
- 也不是单纯 SDK 升降级问题
- 更像是 `pydantic_ai` Anthropic streaming 适配缺陷

### 13.6 当前推荐

如果当前目标是“稳定展示 Claude 思考过程”，推荐优先使用：

- `claude-4.6-sonnet`

如果当前目标是“验证高阶模型正文效果”，可以继续使用：

- `claude-4.7-opus`

但需要接受当前事实：

- `claude-4.7-opus` 目前还**没有稳定返回思考过程**

### 13.7 Claude 阶段性结论

可以认为 Claude 模型这一轮核心测试已基本完成，已覆盖：

- Sonnet
- Opus
- Haiku

并且已经沉淀出以下工程结论：

1. Claude 模型必须支持 Anthropic 原生协议路径
2. `pydantic_ai` 的 Anthropic streaming 需要项目内兼容补丁
3. Sonnet / Opus 不能复用同一套 thinking 参数
4. `claude-4.6-sonnet` 当前更适合作为默认 Claude thinking 模型
5. `claude-4.7-opus` 当前可用，但思考过程返回不稳定
