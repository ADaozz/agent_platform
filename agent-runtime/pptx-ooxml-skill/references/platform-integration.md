# 独立 CLI 与可选平台适配

## 独立运行

按本 SKILL.md 的实际位置设置 PPTX_SKILL_DIR，安装 requirements.txt 后调用 scripts/office_pptx.py。工作目录约定为 files/ 和 tmp/；不依赖 Thread、特定 Agent、固定挂载路径或平台 API key。scripts/artifact_runtime.py 随包提供原子保存、文件锁、版本数据库和恢复。它使用 POSIX 文件锁；Windows 原生运行需要适配，WSL/Linux 可用。

Python 脚本可直接使用 native_charts、native_math、style_library 等模块。脚本覆盖已有 PPT 后，CLI 的修改冲突校验会要求先同步当前文件：独立调用者可用 PresentationStore.track_external(presentation_id) 登记完整保存，再调用检查接口；平台会自动执行此同步。

本地检查调用 PATH 中的 libreoffice，并用 PyMuPDF 生成图片。check-deck 通过后的 visual pending 表示等待 Agent 审查：用 review-images 取得渲染图，看图后 submit-review。独立与平台模式的审查流程相同，都不调用其他模型或外部 API；未完成审查时照常交付，只报告未执行视觉审查，不将 pending 当作通过。

## 平台增强

feature.json 用于发现扩展，platform_adapter.py 对接当前平台的文件索引、事件、HTTP 预览接口和后台队列。该适配器可替换，不是 CLI 的运行依赖。

- 平台在工具结束和文件列表刷新时发现完整脚本保存，校验、去重并登记版本；未改页面保留检查结果。
- 后台合并连续保存的预览任务，渲染最新版本，通过事件通知前端。
- 平台保留当前和前一版快照及预览；独立 CLI 不会自动执行这个裁剪策略。
- 视觉审查由主 Agent 用 read_file 查看正式渲染图后通过 submit-review 提交，宿主不调用任何模型；宿主从事件日志把每条提交的审查记入私有台账，定稿时只信任台账中存在的结论。不可用不阻塞交付。
- 原始文件、版本哈希、截图和审查结果绑定；修改后旧整稿结果标记过期，不能当作新版本审查。

平台快照排除 tests 和 platform_adapter.py，保留技能自带运行时。旧快照不会因源目录更新自动改变；需要使用新快照才能读取新版技能说明和脚本。
