"""
Langfuse 核心概念测试：Session、Trace、Span 的区别与联系

概念说明：
1. Session（会话）：一个用户的多次交互，包含多个 Trace
   - 例如：用户今天上午的所有操作

2. Trace（追踪）：一次完整的请求/任务，包含多个 Span/Observation
   - 例如：用户问了一个问题，系统完整的处理过程
   - 在 Langfuse UI 中是「一行记录」

3. Span/Observation（观察）：Trace 中的一个具体步骤
   - 例如：调用数据库、调用 LLM、执行某个函数
   - 可以嵌套（父子关系）或并列（兄弟关系）
"""

import os
import time
import uuid
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============================================
# 方式 1: 使用 Langfuse SDK（推荐用于理解概念）
# ============================================

def test_langfuse_sdk():
    """使用 Langfuse SDK 手动创建 Session、Trace、Span"""
    from langfuse import get_client, propagate_attributes

    print("\n" + "="*70)
    print("方式 1: Langfuse SDK 手动创建 (SDK v3)")
    print("="*70)

    # 初始化 Langfuse 客户端 (SDK v3 使用 get_client)
    langfuse = get_client()

    # 注意：需要配置环境变量
    # LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

    # 模拟一个用户的会话 ID（通常由前端生成或后端分配）
    session_id = f"session-{uuid.uuid4()}"
    user_id = "test-user-001"

    print(f"\n📱 创建 Session: {session_id}")
    print(f"👤 用户: {user_id}")

    # ========================================
    # Trace 1: 用户问了一个问题
    # ========================================
    print(f"\n🔍 Trace 1: 用户提问 - '如何使用 Langfuse？'")

    # 使用 propagate_attributes 设置 trace 级别的属性
    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        metadata={"X-Ai-Feature": "s-core-plg-mcp"}
    ):
        # 创建根 span (代表整个 Trace)
        with langfuse.start_as_current_observation(
            as_type="span",
            name="question-answering",
            input={"question": "如何使用 Langfuse？"},
            metadata={"question_type": "how-to"}
        ) as trace1:
            trace1_id = langfuse.get_current_trace_id()

            # Span 1.1: 检索相关文档
            print("  └─ Span 1.1: 检索相关文档")
            with langfuse.start_as_current_observation(
                as_type="span",
                name="retrieve-docs",
                metadata={"retrieval_method": "vector-search"}
            ) as span1_1:
                time.sleep(0.1)  # 模拟检索耗时
                span1_1.update(output={
                    "docs_found": 5,
                    "top_doc": "Langfuse 快速入门指南"
                })

            # Span 1.2: 调用 LLM 生成答案
            print("  └─ Span 1.2: 调用 Claude 生成答案")
            with langfuse.start_as_current_observation(
                as_type="generation",  # 注意：LLM 调用用 "generation" 类型
                name="llm-generation",
                model="claude-sonnet-4-20250514",  # ✅ 指定模型名称（必须匹配 Langfuse 的模型定义）
                metadata={"engine": "anthropic"}
            ) as span1_2:
                # Span 1.2.1: 嵌套 - Prompt 构建（子 Span）
                print("      └─ Span 1.2.1: 构建 Prompt")
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name="build-prompt",
                    metadata={"prompt_template": "qa-template"}
                ) as span1_2_1:
                    time.sleep(0.05)
                    span1_2_1.update(output={"prompt_length": 256},)

                # 模拟 LLM 调用
                time.sleep(0.2)
                # 🎯 方式 1: 只提供 usage_details，让 Langfuse 自动计算成本
                # Langfuse 会根据模型定义自动计算成本
                span1_2.update(
                    output={"answer": "Langfuse 是一个 LLM 可观测平台..."},
                    # usage_details={
                    #     "input": 100,   # 只需要提供 token 数量
                    #     "output": 150,  # Langfuse 会自动计算成本
                    #     # "total": 250  # total 可选，会自动计算
                    # }
                    usage = {
                        "input": 1000,
                        "output": 5000,
                        "total": 6000
                    }
                )

                # 🎯 方式 2: 手动指定成本（如果需要覆盖自动计算）
                # span1_2.update(
                #     output={"answer": "Langfuse 是一个 LLM 可观测平台..."},
                #     usage_details={
                #         "input": 100,
                #         "output": 150,
                #     },
                #     cost_details={
                #         "input": 0.0003,
                #         "output": 0.00225,
                #         "total": 0.00075
                #     }
                # )

            # 完成 Trace 1
            trace1.update(
                output={"answer": "Langfuse 是一个 LLM 可观测平台..."},
                metadata={"total_cost": 0.003, "response_time_ms": 350},
                usage_details={
                    "input": 1000,
                    "output": 5000,
                    "total": 6000
                }
            )

            print(f"✅ Trace 1 完成: {trace1_id}")

    # ========================================
    # Trace 2: 用户继续追问
    # ========================================
    print(f"\n🔍 Trace 2: 用户追问 - '能举个例子吗？'")

    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,  # 同一个 Session
        metadata={"X-Ai-Feature": "s-core-plg-mcp"}
    ):
        with langfuse.start_as_current_observation(
            as_type="span",
            name="follow-up-question",
            input={"question": "能举个例子吗？"}
        ) as trace2:
            trace2_id = langfuse.get_current_trace_id()

            # Span 2.1: 调用 LLM
            print("  └─ Span 2.1: 调用 Claude 生成示例")
            with langfuse.start_as_current_observation(
                as_type="generation",
                name="llm-generation",
                model="claude-sonnet-4-20250514",
                metadata={"engine": "anthropic"}
            ) as span2_1:
                time.sleep(0.15)
                # 自动计费：只提供 tokens，Langfuse 自动计算成本
                span2_1.update(
                    output={"answer": "当然！这是一个使用 Langfuse 的示例代码..."},
                    usage_details={
                        "input": 80,
                        "output": 200
                    }
                )

            trace2.update(output={"answer": "当然！这是一个使用 Langfuse 的示例代码..."})
            print(f"✅ Trace 2 完成: {trace2_id}")

    # ========================================
    # Trace 3: 模拟错误情况
    # ========================================
    print(f"\n🔍 Trace 3: 用户提问 - 但遇到了错误")

    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        metadata={"X-Ai-Feature": "s-core-plg-mcp"}
    ):
        with langfuse.start_as_current_observation(
            as_type="span",
            name="error-case",
            input={"question": "这是一个会失败的问题"}
        ) as trace3:
            trace3_id = langfuse.get_current_trace_id()

            try:
                with langfuse.start_as_current_observation(
                    as_type="generation",
                    name="llm-generation",
                    model="claude-sonnet-4-5-20250929"
                ) as span3_1:
                    # 模拟错误
                    raise Exception("API 调用失败: Rate limit exceeded")
            except Exception as e:
                if 'span3_1' in locals():
                    span3_1.update(
                        level="ERROR",
                        status_message=str(e),
                        output={"error": str(e)}
                    )
                trace3.update(
                    output={"error": str(e)},
                    metadata={"status": "failed"}
                )
                print(f"❌ Trace 3 失败: {str(e)}")

    # 强制发送数据到 Langfuse
    langfuse.flush()

    print(f"\n📊 总结:")
    print(f"  - Session: {session_id}")
    print(f"  - User: {user_id}")
    print(f"  - 包含 3 个 Traces:")
    print(f"    1. {trace1_id} (包含 3 个 Spans/Generations)")
    print(f"    2. {trace2_id} (包含 1 个 Generation)")
    print(f"    3. {trace3_id} (包含 1 个 Generation - 失败)")

    # 读取环境变量（优先 LANGFUSE_HOST，其次 LANGFUSE_BASE_URL）
    langfuse_host = os.getenv('LANGFUSE_HOST') or os.getenv('LANGFUSE_BASE_URL')
    print(f"\n🌐 查看结果: {langfuse_host}/project/default/traces")


# ============================================
# 方式 2: 使用 OpenTelemetry（当前项目使用）
# ============================================

def test_opentelemetry():
    """使用 OpenTelemetry 创建 Session、Trace、Span"""
    import base64
    from opentelemetry import trace, baggage, context
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.processor.baggage import BaggageSpanProcessor, ALLOW_ALL_BAGGAGE_KEYS

    print("\n" + "="*70)
    print("方式 2: OpenTelemetry (当前项目使用)")
    print("="*70)

    # 配置 OpenTelemetry
    langfuse_public = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret = os.getenv("LANGFUSE_SECRET_KEY")
    langfuse_host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")

    langfuse_auth = base64.b64encode(
        f"{langfuse_public}:{langfuse_secret}".encode()
    ).decode()

    otlp_endpoint = f"{langfuse_host}/api/public/otel"

    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otlp_endpoint
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {langfuse_auth}"

    resource = Resource.create({
        "service.name": "test-service",
        "service.version": "1.0.0"
    })

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS))
    tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    tracer = trace.get_tracer(__name__)

    # 模拟一个 Session
    session_id = f"otel-session-{uuid.uuid4()}"
    user_id = "test-user-002"

    print(f"\n📱 创建 Session: {session_id}")
    print(f"👤 用户: {user_id}")

    # ========================================
    # Trace 1: 使用 baggage 传播 Session 属性
    # ========================================
    print(f"\n🔍 Trace 1: OpenTelemetry Trace")

    # 设置 Trace 级别的属性（会传播到所有 child spans）
    ctx = baggage.set_baggage("langfuse.session.id", session_id)
    ctx = baggage.set_baggage("langfuse.user.id", user_id, context=ctx)
    ctx = baggage.set_baggage("langfuse.trace.name", "otel-test-trace", context=ctx)
    ctx = baggage.set_baggage("langfuse.trace.metadata.X-Ai-Feature", "s-core-plg-mcp", context=ctx)

    token = context.attach(ctx)

    try:
        # 创建根 Span（代表整个 Trace）
        with tracer.start_as_current_span("process-request") as root_span:
            root_span.set_attribute("request.type", "question-answering")

            print("  └─ Span 1: process-request (根 Span)")

            # 子 Span 1: 数据库查询
            with tracer.start_as_current_span("database-query") as db_span:
                print("      └─ Span 1.1: database-query")
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.query", "SELECT * FROM docs WHERE ...")
                time.sleep(0.1)
                db_span.set_attribute("db.rows_returned", 5)

            # 子 Span 2: LLM 调用
            with tracer.start_as_current_span("llm-call") as llm_span:
                print("      └─ Span 1.2: llm-call")
                # Observation 级别的 metadata（不应该用 baggage）
                llm_span.set_attribute("langfuse.observation.metadata.engine", "anthropic")
                llm_span.set_attribute("langfuse.observation.metadata.model", "claude-sonnet-4-5-20250929")
                llm_span.set_attribute("gen_ai.request.model", "claude-sonnet-4-5-20250929")
                llm_span.set_attribute("gen_ai.usage.prompt_tokens", 100)
                llm_span.set_attribute("gen_ai.usage.completion_tokens", 150)
                time.sleep(0.2)

            root_span.set_attribute("response.status", "success")

    finally:
        context.detach(token)

    print(f"✅ Trace 1 完成")

    # 强制发送
    tracer_provider.force_flush()

    print(f"\n📊 总结:")
    print(f"  - Session: {session_id} (通过 baggage 传播)")
    print(f"  - User: {user_id} (通过 baggage 传播)")
    print(f"  - Trace: otel-test-trace")
    print(f"  - 包含 3 个 Spans (嵌套关系)")
    print(f"\n🌐 查看结果: {langfuse_host}/project/default/traces")


# ============================================
# 方式 3: 实际业务场景模拟
# ============================================

def test_business_scenario():
    """模拟实际业务场景：一个用户使用多个 Skills"""
    from langfuse import get_client, propagate_attributes

    print("\n" + "="*70)
    print("方式 3: 实际业务场景 - 用户使用多个 Skills (SDK v3)")
    print("="*70)

    langfuse = get_client()

    # 一个用户开始使用系统
    session_id = f"business-session-{uuid.uuid4()}"
    user_id = "product-manager-zhang"

    print(f"\n📱 用户登录，开始一个工作会话")
    print(f"  Session: {session_id}")
    print(f"  User: {user_id}")

    # ========================================
    # Trace 1: 使用 code-reviewer skill
    # ========================================
    print(f"\n🔍 Trace 1: 用户使用 'code-reviewer' skill 审查代码")

    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        metadata={
            "X-Ai-Feature": "s-core-plg-mcp",
            "skill_name": "code-reviewer"
        }
    ):
        with langfuse.start_as_current_observation(
            as_type="span",
            name="skill-code-reviewer",
            input={
                "file_path": "src/auth.py",
                "task": "Review this authentication code"
            }
        ) as trace1:
            trace1_id = langfuse.get_current_trace_id()

            # Skill 内部的多个步骤
            with langfuse.start_as_current_observation(
                as_type="span",
                name="read-file"
            ) as span:
                print("  └─ 步骤 1: 读取文件")
                time.sleep(0.05)
                span.update(output={"file_size": 1024})

            with langfuse.start_as_current_observation(
                as_type="generation",
                name="claude-analysis",
                model="claude-sonnet-4-5-20250929",
                metadata={"engine": "anthropic"}
            ) as span:
                print("  └─ 步骤 2: Claude 分析代码")
                time.sleep(0.2)
                # 自动计费：只提供 tokens
                span.update(
                    output={
                        "issues_found": 3,
                        "suggestions": ["使用参数化查询", "添加输入验证", "改进错误处理"]
                    },
                    usage_details={
                        "input": 500,   # 代码文件较大
                        "output": 300
                    }
                )

            trace1.update(output={"review_complete": True, "issues_count": 3})
            print(f"✅ Trace 1 完成: {trace1_id}")

    # ========================================
    # Trace 2: 使用 bug-finder skill
    # ========================================
    print(f"\n🔍 Trace 2: 用户继续使用 'bug-finder' skill 查找 bug")

    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,  # 同一个 Session
        metadata={
            "X-Ai-Feature": "s-core-plg-mcp",
            "skill_name": "bug-finder"
        }
    ):
        with langfuse.start_as_current_observation(
            as_type="span",
            name="skill-bug-finder",
            input={
                "file_path": "src/auth.py",
                "task": "Find potential bugs"
            }
        ) as trace2:
            trace2_id = langfuse.get_current_trace_id()

            with langfuse.start_as_current_observation(
                as_type="span",
                name="static-analysis"
            ) as span:
                print("  └─ 步骤 1: 静态代码分析")
                time.sleep(0.1)
                span.update(output={"warnings": 5})

            with langfuse.start_as_current_observation(
                as_type="generation",
                name="claude-deep-analysis",
                model="claude-sonnet-4-5-20250929",
                metadata={"engine": "anthropic"}
            ) as span:
                print("  └─ 步骤 2: Claude 深度分析")
                time.sleep(0.25)
                # 自动计费
                span.update(
                    output={
                        "bugs_found": 2,
                        "severity": ["high", "medium"]
                    },
                    usage_details={
                        "input": 600,
                        "output": 400
                    }
                )

            trace2.update(output={"bugs_found": 2})
            print(f"✅ Trace 2 完成: {trace2_id}")

    # ========================================
    # Trace 3: 使用 refactoring-assistant skill
    # ========================================
    print(f"\n🔍 Trace 3: 用户使用 'refactoring-assistant' skill 重构代码")

    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,  # 仍然是同一个 Session
        metadata={
            "X-Ai-Feature": "s-core-plg-mcp",
            "skill_name": "refactoring-assistant"
        }
    ):
        with langfuse.start_as_current_observation(
            as_type="span",
            name="skill-refactoring-assistant",
            input={
                "file_path": "src/auth.py",
                "task": "Refactor based on review findings"
            }
        ) as trace3:
            trace3_id = langfuse.get_current_trace_id()

            with langfuse.start_as_current_observation(
                as_type="generation",
                name="claude-refactoring",
                model="claude-sonnet-4-5-20250929",
                metadata={"engine": "anthropic"}
            ) as span:
                print("  └─ 步骤 1: Claude 生成重构建议")
                time.sleep(0.3)
                # 自动计费
                span.update(
                    output={
                        "refactoring_plan": "Extract method, improve error handling..."
                    },
                    usage_details={
                        "input": 700,
                        "output": 500
                    }
                )

            with langfuse.start_as_current_observation(
                as_type="span",
                name="write-file"
            ) as span:
                print("  └─ 步骤 2: 写入重构后的代码")
                time.sleep(0.05)
                span.update(output={"file_updated": True})

            trace3.update(output={"refactoring_complete": True})
            print(f"✅ Trace 3 完成: {trace3_id}")

    langfuse.flush()

    langfuse_host = os.getenv('LANGFUSE_HOST') or os.getenv('LANGFUSE_BASE_URL')
    print(f"\n📊 会话总结:")
    print(f"  - Session: {session_id}")
    print(f"  - User: {user_id} (产品经理张)")
    print(f"  - 工作流程: code-reviewer → bug-finder → refactoring-assistant")
    print(f"  - 总共 3 个 Traces，每个 Trace 包含多个 Spans/Generations")
    print(f"  - 所有操作都在同一个 Session 下，可以在 Langfuse 中按 Session 聚合查看")
    print(f"\n🌐 在 Langfuse 中查看:")
    print(f"  - 所有 Traces: {langfuse_host}/project/default/traces")
    print(f"  - 按 Session 过滤: 在 UI 中搜索 session_id={session_id}")
    print(f"  - 按 User 过滤: 在 UI 中搜索 user_id={user_id}")


# ============================================
# 概念图解
# ============================================

def print_concept_diagram():
    """打印概念关系图"""
    print("\n" + "="*70)
    print("概念关系图")
    print("="*70)

    print("""
┌─────────────────────────────────────────────────────────────────┐
│  Session (会话): session-12345                                   │
│  User: user-zhang                                               │
│  时间跨度: 2024-01-13 09:00 ~ 11:30                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Trace 1 (一次完整请求) ─────────────────────────┐          │
│  │  名称: question-answering                         │          │
│  │  输入: "如何使用 Langfuse？"                      │          │
│  │  输出: "Langfuse 是一个..."                       │          │
│  │                                                   │          │
│  │  ├─ Span 1.1: retrieve-docs                      │          │
│  │  │   └─ 检索相关文档 (100ms)                     │          │
│  │  │                                                │          │
│  │  ├─ Span 1.2: llm-generation                     │          │
│  │  │   ├─ Span 1.2.1: build-prompt                 │          │
│  │  │   │   └─ 构建提示词 (50ms)                    │          │
│  │  │   └─ Claude API 调用 (200ms)                  │          │
│  │  │                                                │          │
│  │  └─ 总耗时: 350ms                                 │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                 │
│  ┌─ Trace 2 (另一次请求) ───────────────────────────┐          │
│  │  名称: follow-up-question                         │          │
│  │  输入: "能举个例子吗？"                           │          │
│  │                                                   │          │
│  │  └─ Span 2.1: llm-generation                     │          │
│  │      └─ Claude API 调用 (150ms)                  │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                 │
│  ┌─ Trace 3 (又一次请求) ───────────────────────────┐          │
│  │  名称: error-case                                 │          │
│  │  状态: ❌ 失败                                    │          │
│  │                                                   │          │
│  │  └─ Span 3.1: llm-generation                     │          │
│  │      └─ 错误: Rate limit exceeded                │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

核心理解:
1. Session = 一个用户的多次交互（通常按时间段或业务会话分组）
2. Trace = 一次完整的请求处理（在 UI 中是一行记录）
3. Span = Trace 中的一个步骤（可以嵌套，形成树状结构）

类比:
- Session ≈ 一次咖啡店的点单会话
- Trace ≈ 一杯咖啡的制作过程
- Span ≈ 磨豆、冲泡、打奶泡等具体步骤
    """)


# ============================================
# 主函数
# ============================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Langfuse 核心概念测试")
    print("="*70)

    # 检查环境变量
    required_env = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
    missing = [key for key in required_env if not os.getenv(key)]

    # 检查 LANGFUSE_HOST 或 LANGFUSE_BASE_URL 至少有一个
    if not os.getenv("LANGFUSE_HOST") and not os.getenv("LANGFUSE_BASE_URL"):
        missing.append("LANGFUSE_HOST or LANGFUSE_BASE_URL")

    if missing:
        print(f"\n❌ 错误: 缺少环境变量: {', '.join(missing)}")
        print("请确保 .env 文件中配置了:")
        print("  LANGFUSE_PUBLIC_KEY=pk-lf-xxx")
        print("  LANGFUSE_SECRET_KEY=sk-lf-xxx")
        print("  LANGFUSE_HOST=https://xxx  (或 LANGFUSE_BASE_URL)")
        exit(1)

    # 打印概念图
    print_concept_diagram()

    # 交互式选择
    print("\n请选择要运行的测试:")
    print("  1. Langfuse SDK 手动创建（推荐先看这个）")
    print("  2. OpenTelemetry 方式（当前项目使用）")
    print("  3. 实际业务场景模拟")
    print("  4. 运行所有测试")

    choice = input("\n请输入选项 (1-4): ").strip()

    if choice == "1":
        test_langfuse_sdk()
    elif choice == "2":
        test_opentelemetry()
    elif choice == "3":
        test_business_scenario()
    elif choice == "4":
        test_langfuse_sdk()
        test_opentelemetry()
        test_business_scenario()
    else:
        print("无效选项")

    print("\n" + "="*70)
    print("测试完成！请在 Langfuse UI 中查看结果")
    print("="*70)

    langfuse_host = os.getenv('LANGFUSE_HOST') or os.getenv('LANGFUSE_BASE_URL')
    print(f"\n🌐 访问: {langfuse_host}/project/default/traces")
    print("\n提示:")
    print("  - 使用 session_id 过滤可以看到一个会话的所有 traces")
    print("  - 使用 user_id 过滤可以看到一个用户的所有 traces")
    print("  - 点击某个 trace 可以看到内部的所有 spans")
    print("  - metadata 字段可以用于自定义过滤和分析")
