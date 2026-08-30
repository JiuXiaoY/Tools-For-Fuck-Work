# antelope 待补充 / 待确认清单

> 背景：fr_dress 全流程 ①~⑥ 已跑通（`outputs/fr_dress_filled.xlsm`，1540 格 / 61 行）。
> 已解决项不再列出，包括：M 数据生成（dataTemp）、批次命名配置、**未使用列忽略**、**空单元格读取空并写入空**、产出模板 Eva、多余行删除、col_scope 守门、**Sheet1 忽略（不在映射列文件范围内）**、价格 AT/AU 忽略、**.xlsx 只读第一个工作表 Sheet0（其余忽略）**。
> 以下仅剩**需要你补充 / 确认**的项。**你补齐后告诉我编号，我重跑修复。**

| # | 待补充 / 待确认 | 当前状态 | 需要你提供 | 你填完后的修复动作 |
|---|----------------|----------|-----------|-------------------|
| 1 | **13 个未覆盖列**：其中 **4 列有可选值**（17/126 领型、141 袖型、143 闭合），**9 列无可选值**（19/20/40/41-45/46） | ⚠️ 当前全部 `dataTemp` 占位 | 有可选值列：**AI 选值**（程序已写好待运行）；无可选值列：保持占位或另想办法 | 运行 `ai_pick_attributes.py`（见下）→ ⑤⑥ |

---

## 解决方案（你补充，2026-08-30）

针对上述占位列：模板解析 json（`fr_dress_completed.json`）里有**可选值(choices)**的列，构造提示词询问 AI 选值；没有可选值的列暂时依旧填占位。每列每组只存 1 个值，采用**循环填充模式**。类似 `tools/title_optimize` 的方式：提示词写到配置文件 → 读取 → 替换相关可选项。**先写好，你说运行再运行。**

### ✅ 已写好（待运行）：`antelope/ai_pick_attributes.py`

1. 找出未覆盖列中有 choices 的列：**17/126 领型（31 值）、141 袖型（22 值）、143 闭合（11 值）**
2. 从数据源 A(Sheet0) 提取产品列表（每组锚点行 `标题 | 卖点`，共 4 组 → 产品A~D）
3. 每列生成提示词文件：`intermediate/fr_dress/ai_prompt/col{N}_{字段}.txt`（产品列表 + 可选值，要求 AI 按 `编号: 值` 输出）
4. 取值：
   - **手动模式（默认）**：把提示词喂给 AI，回答存为同目录 `col{N}_result.txt`，再运行本程序读取
   - **`--api` 模式**：直接调 AIClient（config.py 的 ai_provider / ai_api_key / ai_model）
5. 校验值在可选值内 → 更新 M JSON（每组 1 个值 → **cycle 循环填充**）
6. 无可选值列保持 `dataTemp` 占位

### 运行示例（等你说"运行"）

```bash
python antelope/ai_pick_attributes.py            # 手动模式：生成提示词文件
#   → 喂给 AI → 回答存为 intermediate/fr_dress/ai_prompt/col17_*.txt_result.txt 等
#   → 再运行一次（不带 --api）读取并写回
python antelope/ai_pick_attributes.py --api      # 或 API 模式：直接调 AI 并写回
python antelope/build_fill_framework.py          # ⑤ 重新生成 plan（M 合并）
python antelope/fill_from_plan.py antelope/fill_plan/fr_dress_fill_framework.json -o outputs/fr_dress_filled.xlsm
```

*你补齐任意一项后告诉我编号，我按表内"修复动作"执行。*
