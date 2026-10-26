# OPC UA NodeSet2 to Standard JSON

English version: [README.md](README.md)

这是一个用于 OPC UA NodeSet2 XML 的离线转换流水线。该项目会解析源节点事实，建立规范化的 canonical model，并将节点映射到已验证的标准 bundle 中；同时保留结构化的映射证据和审查结果。语义审核被明确地与转换器分离：调用 agent 或人工审阅者需要基于生成的证据判断节点是否合理，再决定是否接受该标准语义。

这个项目强调可追溯性和可解释性，而不是盲目自动化。它不会调用外部大模型 API，也不依赖在线服务；相反，它生成的是便于审查的结构化输出，供后续语义审核使用。

## 目录

- [项目存在的意义](#项目存在的意义)
- [核心能力](#核心能力)
- [为 Agent 安装 Skill](#为-agent-安装-skill)
- [Agent 如何使用本 Skill](#agent-如何使用本-skill)
- [架构与实现方法](#架构与实现方法)
- [业务流程与执行标准](#业务流程与执行标准)
- [手动运行 CLI](#手动运行-cli)
- [输入与输出契约](#输入与输出契约)
- [生成的产物](#生成的产物)
- [定制与二次开发](#定制与二次开发)
- [测试](#测试)
- [安全与限制](#安全与限制)
- [许可证](#许可证)

## 项目存在的意义

大多数 OPC UA XML 导出都具有以下特点：噪声大、结构不统一、语义模糊。节点名、描述、层级、单位和数据类型往往不能一一对应到目标工业模型。该项目的作用是构建一个清晰、可控、可审计的处理流程：

- 解析 XML 中的 OPC UA 事实
- 规范化原始结构，生成 canonical model
- 将映射约束在已知 bundle 的允许集合之内
- 使用确定性规则为候选语义评分
- 对模糊或冲突节点触发 review
- 明确区分转换阶段和语义审核阶段

因此它适合用于模型驱动工程、工业数据标准化，以及人工参与的语义审阅场景。

## 核心能力

- 离线 NodeSet2 解析与规范化
- 基于 bundle 的实体和变量语义映射
- 基于规则的候选评分与冲突识别
- 层级回退与 synthetic container 标记
- 单位与数据类型冲突报告
- 对模糊节点生成 review queue
- 面向 agent 的语义审核工作流
- 生成可用于后续审计的输出包

## 项目结构

- `layer1/`：解析 XML、解析引用关系、生成 canonical 路径和原始事实
- `layer2/`：特征抽取、候选评分、候选选择、review 生成、语义对齐适配器钩子
- `models/`：校验后的 bundle 和模型契约
- `exporters/`：JSON 输出、清单生成、结果打包
- `config/`：bundle 和运行时配置
- `examples/`：样例 XML 与调用配置
- `tests/`：回归测试与行为验证
- `utils/`：共享归一化和路径工具
- `runner.py`：命令行入口
- `SKILL.md`：调用契约与责任边界定义

## 为 Agent 安装 Skill

本仓库是一个**包含 Python 实现的 Agent Skill 包**，不是可通过 `pip install` 安装的 Python 发行包。安装 Skill 是为了让兼容的 Agent 能发现并加载其指令；Agent 在需要执行转换时，才单独准备 Python 运行环境。

### VS Code / GitHub Copilot

VS Code 会从工作区的 `.github/skills/`、`.claude/skills/` 或 `.agents/skills/`，以及用户目录的 `~/.copilot/skills/`、`~/.claude/skills/` 或 `~/.agents/skills/` 发现 Skill。每个 Skill 目录中都必须直接包含 `SKILL.md`。本仓库将 `SKILL.md`、`runner.py`、`layer1/`、`layer2/`、`models/` 等运行文件放在仓库根目录，因此应将**整个仓库作为 Skill 目录**安装；不要在 Skill 目录和 `SKILL.md` 之间多套一层项目子目录。发现规则详见 [VS Code Agent Skills 文档](https://code.visualstudio.com/docs/agent-customization/agent-skills)。

例如，在宿主工作区根目录进行工作区级安装：

```powershell
git clone https://github.com/happy-momo/OPCUA2graph.git .github/skills/opcua-nodeset-to-standard-json
```

也可以在 VS Code 中运行 **Chat: Open Customizations**，打开 **Skills** 并创建或管理工作区级/用户级 Skill。若通过界面手动安装本仓库，请将仓库内容复制到 Skill 目录，并确保 `SKILL.md` 位于该目录根部。

其他兼容 Agent 使用各自文档规定的 Skill 目录和发现规则。Skill 格式具有可移植性，但安装路径和支持的功能由宿主 Agent 决定。安装后，如宿主要求，请刷新或重新加载 Skill 列表，并确认 `opcua-nodeset-to-standard-json` 已被发现。

### Agent 使用的 Python 运行环境

Agent 应先检查已有 Python 环境，并在依赖已具备时复用工作区配置的解释器。如果缺少依赖，应在 Skill 目录创建隔离环境并安装声明的依赖，避免修改用户全局 Python 环境：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS/Linux 可使用 `python3 -m venv .venv` 和 `.venv/bin/python -m pip install -r requirements.txt`。运行环境需要 Python 3.11+ 及 [requirements.txt](requirements.txt) 中的依赖。安装依赖后，转换本身可离线运行；不需要模型 API key 或 OPC UA 服务。

## Agent 如何使用本 Skill

用户提供或指定 NodeSet2 XML，并要求转换、映射或审核时，**Agent 负责完成仓库、运行环境和命令行操作**：

1. **识别并确定任务范围**：对 NodeSet2 转换或映射审核请求加载本 Skill。不要将它用于通用 XML 转换、实时服务器浏览或无关的 OPC UA 问题。
2. **查找输入并确定目标**：定位 XML、已有运行配置和目标标准 bundle。优先使用用户提供的文件，而不是仓库示例。如果目标 profile 或必需输出不明确，应先询问。
3. **准备运行环境**：检查 Python 3.11+ 和所需依赖。复用合适的现有解释器，否则按上文准备隔离环境。除非用户希望亲自操作，否则不要要求用户手动运行安装命令。
4. **安全配置和运行**：复用匹配的配置，或创建本次专用的配置和输出目录。不得覆盖源 XML、用户配置或 bundle。常规 Skill 流程关闭语义对齐，由 Agent 在转换完成后单独审核。
5. **验证产物后再解释**：检查命令执行结果及 `result_package.json` 中的运行标识、bundle ID/版本、模式、计数和所有输出路径。若解析、校验或导出失败，应停止并报告错误。
6. **审核映射**：读取映射证据、审核队列、未映射结果、标准模型，以及存在时的 canonical model。根据源 NodeId、名称、数据类型、单位、父/同级上下文、层级和 bundle 约束核对候选代码。
7. **交付可追溯结果**：报告产物路径、bundle/运行标识、状态汇总、主要发现、未解决问题，并将 Agent 审核结论与转换器状态分开。如果用户要求或工作流需要持久化审核，则在本次结果包旁写入 `agent_review.json`。不得静默修改转换器输出。

完整且权威的操作指令见 [SKILL.md](SKILL.md)。若本概览与 Skill 指令不一致，以 `SKILL.md` 为准。

## 架构与实现方法

项目使用分阶段 Python 流水线，并通过明确的数据契约衔接各阶段：

1. **加载并校验输入**：`runner.py` 读取运行配置，通过 `StandardBundle` 加载并校验目标 bundle，同时检查配置中的 bundle ID 是否匹配。
2. **解析 NodeSet2**：`layer1/` 读取 XML `UANodeSet`，提取受支持节点的事实（ID、类别、名称、描述、数据类型、工程单位和引用关系），解析父子关系并生成规范路径。项目不宣称完成完整的 OPC UA NodeSet schema 校验。
3. **生成证据与候选项**：`layer2/` 生成节点、父节点及同级节点特征；仅从 bundle 允许列表中生成实体或变量候选，并根据别名、模式、数据类型、单位和上下文规则确定性评分。
4. **分类并保留审核证据**：映射器记录候选分数、选中代码、冲突、规范化单位、审核触发器和转换器状态。即使分数达到自动接受阈值，强制审核触发器仍可要求复核。
5. **构建并打包结果**：标准模型构建器根据运行模式筛选结果，`exporters/` 写出 JSON 产物和包含自身路径的结果清单。
6. **独立执行语义审核**：调用 agent 或人工审核者根据源上下文和 bundle 核验映射，并单独报告审核结论。审核不得静默改写转换器输出。

`config/default_bundle.json` 明确标记为**演示 profile**（`conformance_claim: none`），不是权威工业词汇表。生产环境应使用经过审核、版本化的 bundle。

## 设计哲学

这个项目严格区分三个职责：

1. 确定性转换器
   - 读取 NodeSet
   - 提取源事实
   - 对候选映射评分
   - 在结构化输出中保留证据

2. 调用 agent 或审核人
   - 基于源上下文检查所选语义
   - 校验层级、单位、数据类型和父对象兼容性
   - 决定映射是 confirmed、ambiguous，还是 unsupported

3. Bundle 作为允许清单
   - 只有已知的标准概念才可作为候选
   - 不允许静默创造新的目标代码
   - 对不支持的概念保留未映射状态，或要求补充 bundle

这一设计已在 `SKILL.md` 中说明。Python 实现本身不会在转换阶段调用 LLM 或外部模型服务；真正的语义审核发生在转换之后，由 agent 或用户基于生成结果进行再判定。

## 运行流程

日常操作由 Agent 负责：

1. 定位用户的 NodeSet 和目标 bundle；只有必要决策不明确时才向用户澄清。
2. 准备或复用合适的 Python 环境和运行配置，且不修改用户输入。
3. 使用唯一输出目录运行 `runner.py` 并验证结果清单。
4. 检查生成证据，并根据源文件和 bundle 审核映射。
5. 返回产物路径和发现，将 Agent 结论与转换器状态分开。

这是“审查优先”的工作流，不是盲目的自动接受流程。

## 业务流程与执行标准

Agent 应在每次运行中遵循以下关卡：

### 运行前

- 确认源文件是 NodeSet2 XML，并确定目标 profile。优先使用用户提供的 bundle；仓库默认 bundle 是演示 profile，不是权威工业标准。
- 阅读 bundle 的标准注册表、结构 schema、实体和变量概念、单位字典、评分规则、审核策略和输出契约。如果标准或输出要求存在实质歧义，应先提出聚焦的问题。
- 使用唯一的运行目录。保护所有用户输入，不要将完整 NodeSet XML 发送给外部模型或服务。

### 转换与验证

- 使用选定的工作区 Python 环境和匹配的配置运行确定性转换器。
- 在将运行视为成功前，验证 `result_package.json` 中的每个路径，包括清单对自身的引用。
- 转换器状态（`auto_accepted`、`needs_review`、`unmapped`、`rejected`）代表机器决策，不是 Agent 的语义审核结论。
- 审核所有已映射或要求复核的节点。优先检查低分、候选并列、单位/类型冲突、未解析父级、synthetic hierarchy 和 bundle-gap；同时检查自动接受映射是否存在系统性错误。

### 审核与交付

- 核对源 NodeId、名称和描述、NodeClass、数据类型、ValueRank、访问级别、单位、引用关系、父路径、同级上下文、候选替代项、硬约束以及实际加载的 bundle 代码。
- 仅推荐 bundle 中已声明的代码。概念缺失时应报告 bundle-gap，不得自行创造代码。
- 审核结论使用 `confirmed`、`incorrect`、`ambiguous`、`insufficient_evidence` 或 `bundle_gap`。结论必须与转换器状态分开，不得静默改写其输出。
- 报告运行 ID、源文件、bundle/版本、运行模式、产物位置、汇总计数、重要发现和限制。用户要求或工作流需要时持久化 `agent_review.json`。
- 解析、bundle 校验或导出失败时，应停止并报告可操作的错误；不得将部分文件描述为成功结果。

完整审核清单和 `agent_review.json` 结构见 [SKILL.md](SKILL.md)。

## 手动运行 CLI

Agent 通常会在 Skill 工作流中运行转换器。本节面向维护者、问题诊断，或明确希望手动调用确定性转换器的用户。请先按上文安装运行依赖。

运行示例转换：

```powershell
.\.venv\Scripts\python.exe runner.py --input examples/input.json --output-dir outputs/example-run
```

或者使用自定义 NodeSet：

```powershell
.\.venv\Scripts\python.exe runner.py --input examples/factory_multiline_input.json --output-dir outputs/factory_multiline_run
```

若已激活虚拟环境，也可以使用 `python runner.py ...`。macOS/Linux 请使用 `.venv/bin/python runner.py ...`。

`--input` 指向 JSON 运行配置。配置中的 `input_file.path` 和 `target_standard.bundle_path` 相对于项目根目录解析；相对的 `--output-dir` 也相对于项目根目录。运行配置本身相对于当前工作目录解析，因此从其他目录调用时应传入配置文件绝对路径。

## 输入与输出契约

### 运行配置

配置文件会指定：

- 源 XML 文件
- 目标 bundle 路径
- bundle ID
- 运行模式
- 可选的语义模式
- 可选产物的开关

示例见 [examples/input.json](examples/input.json)。必需产物不能关闭；`include_canonical_model` 默认值为 `true`。

### 支持的运行模式

- `fast`：确定性转换，并强制关闭语义对齐。
- `review`：使用 bundle 阈值的审查型转换。默认 bundle 的自动接受、审核和拒绝阈值分别为 `0.90`、`0.65` 和 `0.40`；强制审核触发器仍优先。
- `strict`：使用自动接受阈值作为接受边界。只有状态为 `auto_accepted` 的记录可以进入标准模型，其余记录仍保留在审核产物中。

### 语义模式

- `off`：不开启 adapter 语义增强
- `assist` 和 `enhanced`：仅供通过 Python API 显式注入 adapter 的调用方使用。

命令行入口不会注入 adapter，也不会调用外部模型。常规 Skill 流程应保持语义对齐关闭，由调用 agent 在转换后独立完成语义审核。

## 生成的产物

每次运行都会在输出目录中写入一组产物，包括：

- `standard_model.json`
- `mapping_results.json`
- `review_queue.json`
- `unmapped_nodes.json`
- `result_package.json`
- 可选的 `canonical_model.json`

结果包会记录输出文件、run ID、源文件、bundle 版本、模式和汇总状态等元数据。

## 定制与二次开发

应选择满足需求的最小扩展点：

### 添加或调整目标 profile（无需修改 Python）

创建符合 [SKILL.md](SKILL.md) 契约且通过 [standard_bundle.py](models/standard_bundle.py) 校验的版本化 bundle JSON。定义来源信息、层级、实体和变量代码、别名、数据类型和单位约束、评分规则、审核阈值及必需输出。所有可选代码必须在 bundle 中声明；演示概念需清晰标注。在运行配置中将 `target_standard.bundle_path` 和 `bundle_id` 指向新 bundle，并补充 bundle 校验与端到端测试样例。

### 修改确定性转换行为

遵循现有流水线分层，不要将所有逻辑都塞入 `runner.py`：

- XML 事实和支持的 NodeSet 节点：`layer1/parser.py` 及 `models/canonical_model.py` 中的 canonical 契约。
- 名称规范化、引用关系和层级路径：对应的 `layer1/` 模块与 `utils/`。
- 特征和候选评分：`layer2/feature_builder.py`、`layer2/entity_mapper.py`、`layer2/variable_mapper.py` 和 `layer2/scorer.py`。
- 状态和审核触发器：`layer2/review_splitter.py`、`layer2/mapper.py` 及 bundle 的 `review_policy`。
- 输出结构和清单：`layer2/standard_model_builder.py` 与 `exporters/`。

在 `tests/` 下新增或更新针对性测试；保持源证据和输出契约稳定。若 Agent 行为变化，更新 `SKILL.md`；若公开行为或安装方法变化，则同步维护中英文 README。

### 添加可选语义 adapter

Python API 支持通过 `run(..., semantic_adapter=...)` 显式注入 adapter。它接收 prompt 字符串，并必须返回能通过 `layer2/semantic_response_parser.py` 校验的 JSON 字符串或对象。CLI 不配置 adapter，标准 Skill 流程默认关闭此功能；不得在转换器中引入隐式网络调用或凭证。

### 验证与贡献

在项目根目录运行 `python -m pytest`。测试使用本地 fixture 和确定性的模拟 adapter，不需要 OPC UA 服务或模型 API。保持改动范围清晰，避免提交运行输出和本地环境，并记录任何有意的输出契约变化。

## 审核模型与审计行为

转换器记录的是证据，而不是单纯结论。每个节点的输出中都保留了：

- 源节点元数据
- 提取后的特征与 token
- 候选映射
- 选中的映射与分数
- review 触发器
- 结构和单位冲突
- 归一化后的单位
- 最终 review 状态

这使得 agent 可以回答以下问题：

- 为什么这个节点被映射到这个标准概念，而不是邻近候选？
- 父对象和同级信号是否支持这个选择？
- 是否出现单位或数据类型冲突？
- 当前层级是显式的，还是 synthetic fallback？

## 标准与来源要求

bundle 被视为显式、版本化的语义契约。它可能引用：

- OPC UA Core 规范
- IEC 62264 / ISA-95 概念
- UCUM 单位参考（如适用）
- OPC UA companion 规范（如适用）

但该项目始终保持离线和可追溯的特点。它不宣称超出实际加载的 bundle 和源证据之外的规范合规性。

## 安全与限制

这个项目是保守型设计：

- 不会静默创造新的 bundle code
- 会保留歧义，而不是强行猜测
- 会明确记录 synthetic hierarchy 容器
- 对模糊或冲突映射要求进行 review
- 不会把不完整结果伪装为有效输出

如果 bundle 中不存在可辩护的概念，那么该节点应保持未映射状态，或者被标记为 bundle-gap，需要人工复核。

## 测试

```powershell
python -m pytest
```

测试使用本地 fixture 和确定性的模拟 adapter，不需要联网、OPC UA 服务或远程模型 API。

## 复用与贡献

这个项目适合于以下场景：

- 工厂层级规范化
- OPC UA 语义映射审查
- 基于 bundle 的工业数据标准化
- 证据驱动、可追溯的映射输出

如果能够改进确定性、证据质量、bundle 覆盖范围或 review 清晰度，欢迎贡献代码和改进建议。

## 许可证

仓库当前没有 `LICENSE` 文件。在补充许可证前，不应假定仓库已授予开源许可或再分发权。

## 总结

这个项目最合理的定位是：一个带有显式 agent 审核层的确定性 OPC UA 映射流水线。它提供了机器可读的证据、面向 review 的输出和严格的语义工作流，适合工业数据标准化和人工审核场景。
