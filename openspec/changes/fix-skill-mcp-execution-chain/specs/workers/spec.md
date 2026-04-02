## MODIFIED Requirements

### Requirement: SandboxManager 通过公共接口暴露运行模式
`SandboxManager` SHALL 通过公共属性 `is_local: bool` 暴露当前运行模式，外部调用方 SHALL 使用该公共属性，不得直接访问 `_is_local` 私有属性。

#### Scenario: SandboxWorker 判断本地模式
- **WHEN** `SandboxWorker` 需要判断当前是否为本地模式
- **THEN** 系统 SHALL 通过 `self._manager.is_local` 访问，不使用 `self._manager._is_local`

#### Scenario: 本地模式 token 获取
- **WHEN** `is_local` 为 `True`
- **THEN** `SandboxWorker` SHALL 直接使用 `settings.llm.openai_api_key` 作为 temp_token，不调用 `issue_sandbox_token`

#### Scenario: E2B 模式 token 获取
- **WHEN** `is_local` 为 `False`
- **THEN** `SandboxWorker` SHALL 调用 `issue_sandbox_token` 签发临时 token
