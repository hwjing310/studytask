# 测试结果

## 测试环境

- 日期：2026-11-11
- 系统：Windows（本地）
- Python：3.12.14
- Flask：3.1.3
- pytest：9.2.0
- 数据库：SQLite（测试使用 pytest 临时数据库，不影响正式数据库）

## 执行命令

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

## 汇总结果

```text
collected 16 items
16 passed in 1.00s
```

原始详细输出见 `test-results.txt`。

## 用例清单

| 序号 | 测试用例 | 覆盖点 | 结果 |
|---|---|---|---|
| 1 | `test_t1_create_task_with_defaults` | 创建任务、默认优先级/状态、自动时间戳、跳转详情 | PASSED |
| 2 | `test_t1_invalid_input_is_rejected_without_writes` | 必填、长度、日期格式/真实性、优先级/状态合法性，非法输入不落库 | PASSED |
| 3 | `test_boundary_values_are_accepted` | 100/60/1000 字符边界、闰年日期 | PASSED |
| 4 | `test_t2_list_and_detail_show_required_fields` | 列表五要素、详情链接、描述和状态显示 | PASSED |
| 5 | `test_t3_edit_updates_list_and_detail` | 全部字段修改、列表与详情一致 | PASSED |
| 6 | `test_t4_delete_requires_confirmation_and_removes_task` | 删除确认页不直接删除、POST 后数据库删除、详情 404 | PASSED |
| 7 | `test_t5_status_can_change_between_all_states` | 待完成 → 进行中 → 已完成 → 待完成 | PASSED |
| 8 | `test_t6_combined_filters` | 课程 + 状态 + 优先级组合筛选，单独筛选 | PASSED |
| 9 | `test_t7_overdue_and_upcoming_rules` | 逾期、今天到期、3 天内、第 4 天、已完成不提醒 | PASSED |
| 10 | `test_t8_dashboard_statistics` | 0 条任务 0%、3 条任务 1 条完成显示 33% | PASSED |
| 11 | `test_t9_data_survives_restart` | 重新创建应用后同一 SQLite 文件仍可读取 | PASSED |
| 12 | `test_t10_chinese_pages_and_404` | 中文页面、`lang="zh-CN"`、任务/页面 404 | PASSED |
| 13 | `test_invalid_status_update_is_rejected` | 非法状态调整被拒绝且原状态不变 | PASSED |
| 14 | `test_filter_with_no_matches_shows_clear_empty_state` | 无匹配筛选结果提示与清除入口 | PASSED |
| 15 | `test_homepage_handles_200_tasks` | 200 条任务规模下首页及统计正常 | PASSED |
| 16 | `test_init_db_command_is_idempotent` | `init-db` 可重复执行、`tasks` 表存在 | PASSED |

## 启动冒烟验证

在 `http://127.0.0.1:5000` 启动真实服务后，通过 HTTP 完成以下验证：

- 首页返回 200，中文标题正常。
- 本地 CSS 返回 200。
- 提交中文任务返回详情页 200，详情与列表均出现新任务。
- 删除确认页可访问；确认删除后列表不再包含该任务，详情页返回 404。

结果：`SMOKE_OK`。

## 验收结论

A.3 的 FR-01—FR-10 对应功能均通过自动化测试；A.6 中 T1—T10 的等价映射全部通过。正式数据库在交付时为空库，可直接使用。
