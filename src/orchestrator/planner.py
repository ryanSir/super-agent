"""Plan-and-Execute DAG 规划器

接收用户 query，通过 PydanticAI 调用 LLM 生成结构化的 ExecutionDAG。
"""

# 标准库
import uuid
from typing import Any, Dict, Optional

# 第三方库
from pydantic_ai import Agent
from pydantic_ai.models.instrumented import InstrumentationSettings

# 本地模块
from src.core.exceptions import PlanningError
from src.core.logging import get_logger
from src.llm.config import get_model
from src.orchestrator.prompts.planning import PLANNING_PROMPT_TEMPLATE
from src.schemas.agent import ExecutionDAG, TaskNode

logger = get_logger(__name__)

# 规划专用 Agent — 结构化输出 DAG
planner_agent = Agent(
    model=get_model("planning"),
    output_type=list[TaskNode],
    instructions=(
        "你是一个任务规划专家。根据用户请求，输出结构化的子任务列表。"
        "每个子任务必须包含 task_id, task_type, risk_level, description, input_data, depends_on。"
        "代码生成和脚本执行类任务的 risk_level 必须为 dangerous。"
    ),
    retries=3,
    instrument=True,
)


async def plan_tasks(
    query: str,
    context: Optional[Dict[str, Any]] = None,
) -> ExecutionDAG:
    """规划任务执行 DAG

    Args:
        query: 用户自然语言请求
        context: 附加上下文

    Returns:
        ExecutionDAG: 任务执行拓扑

    Raises:
        PlanningError: 规划失败
    """
    dag_id = f"dag-{uuid.uuid4().hex[:8]}"
    context_str = str(context) if context else "无"

    prompt = PLANNING_PROMPT_TEMPLATE.format(query=query, context=context_str)

    logger.info(f"[Planner] 开始规划 | dag_id={dag_id} query_len={len(query)}")

    try:
        result = await planner_agent.run(prompt)
        tasks = result.output

        dag = ExecutionDAG(
            dag_id=dag_id,
            query=query,
            tasks=tasks,
        )

        logger.info(
            f"[Planner] 规划完成 | "
            f"dag_id={dag_id} task_count={len(tasks)} "
            f"root_tasks={[t.task_id for t in dag.root_tasks]}"
        )
        return dag

    except Exception as e:
        logger.error(
            f"[Planner] 规划失败 | dag_id={dag_id} error={e}",
            exc_info=True,
        )
        raise PlanningError(
            f"任务规划失败: {e}",
            context={"dag_id": dag_id, "query": query[:200]},
        ) from e
