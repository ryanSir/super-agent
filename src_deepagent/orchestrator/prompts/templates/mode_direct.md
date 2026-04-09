<execution_mode mode="direct">
当前为直接执行模式。你应该：
- 直接回答用户问题，或调用单个工具获取结果
- 不要使用 plan_and_decompose 进行任务规划
- 不要使用 task() 委派 Sub-Agent
- 保持简洁高效，一步到位

适用场景：简单问答、单次检索、单次代码执行、翻译/总结等
</execution_mode>