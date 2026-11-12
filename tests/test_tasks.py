from __future__ import annotations

import re
from datetime import date, timedelta

from studytask import create_app
from studytask.db import get_db

BASE_TASK = {
    "name": "完成线性代数习题",
    "course": "线性代数",
    "description": "第三章课后习题",
    "due_date": (date.today() + timedelta(days=5)).isoformat(),
    "priority": "高",
    "status": "待完成",
}


def post_create(client, **overrides):
    data = dict(BASE_TASK)
    data.update(overrides)
    return client.post("/tasks/new", data=data, follow_redirects=False)


def create_task(client, **overrides) -> int:
    response = post_create(client, **overrides)
    assert response.status_code == 302
    match = re.search(r"/tasks/(\d+)$", response.headers["Location"])
    assert match is not None
    return int(match.group(1))


def fetch_task(app, task_id: int):
    with app.app_context():
        row = get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row is not None else None


def task_count(app) -> int:
    with app.app_context():
        return int(get_db().execute("SELECT COUNT(*) FROM tasks").fetchone()[0])


def task_row(html: str, task_id: int) -> str:
    match = re.search(rf'<tr data-task-id="{task_id}">(.*?)</tr>', html, re.S)
    assert match is not None, f"未找到任务 {task_id} 的列表行"
    return match.group(1)


# T1：创建任务及服务端校验
def test_t1_create_task_with_defaults(client, app):
    response = client.post(
        "/tasks/new",
        data={
            "name": "  高数作业  ",
            "course": " 高等数学 ",
            "due_date": "2026-12-31",
        },
    )

    assert response.status_code == 302
    task_id = int(response.headers["Location"].rstrip("/").split("/")[-1])
    task = fetch_task(app, task_id)
    assert task is not None
    assert task["name"] == "高数作业"
    assert task["course"] == "高等数学"
    assert task["description"] == ""
    assert task["due_date"] == "2026-12-31"
    assert task["priority"] == "中"
    assert task["status"] == "待完成"
    assert task["created_at"]
    assert task["updated_at"]

    detail = client.get(f"/tasks/{task_id}").get_data(as_text=True)
    assert "任务创建成功。" in detail
    assert "高数作业" in detail
    assert "高等数学" in detail


def test_t1_invalid_input_is_rejected_without_writes(client, app):
    cases = [
        ({"name": ""}, "请输入任务名称。"),
        ({"name": "名" * 101}, "任务名称不能超过 100 个字符。"),
        ({"course": " "}, "请输入所属课程。"),
        ({"course": "课" * 61}, "所属课程不能超过 60 个字符。"),
        ({"due_date": ""}, "请选择截止日期。"),
        ({"due_date": "2026/12/01"}, "截止日期格式必须为 YYYY-MM-DD。"),
        ({"due_date": "2026-02-30"}, "截止日期不是有效日期。"),
        ({"description": "描" * 1001}, "任务描述不能超过 1000 个字符。"),
        ({"priority": "紧急"}, "优先级必须为“高”“中”或“低”。"),
        ({"status": "延期"}, "状态必须为“待完成”“进行中”或“已完成”。"),
    ]

    for overrides, message in cases:
        response = post_create(client, **overrides)
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert message in html
        assert task_count(app) == 0


def test_boundary_values_are_accepted(client, app):
    task_id = create_task(
        client,
        name="名" * 100,
        course="课" * 60,
        description="描" * 1000,
        due_date="2028-02-29",
        priority="低",
        status="已完成",
    )

    task = fetch_task(app, task_id)
    assert task is not None
    assert task["name"] == "名" * 100
    assert task["course"] == "课" * 60
    assert task["description"] == "描" * 1000
    assert task["due_date"] == "2028-02-29"


# T2：列表展示与详情入口
def test_t2_list_and_detail_show_required_fields(client):
    task_id = create_task(
        client,
        name="概率论复习",
        course="概率论",
        description="复习第一章\n整理错题",
        priority="中",
        status="进行中",
    )

    html = client.get("/").get_data(as_text=True)
    assert "任务名称" in html
    assert "所属课程" in html
    assert "截止日期" in html
    assert "状态" in html
    assert "优先级" in html
    assert "概率论复习" in html
    assert "概率论" in html
    assert f"/tasks/{task_id}" in html

    detail = client.get(f"/tasks/{task_id}").get_data(as_text=True)
    assert "复习第一章" in detail
    assert "整理错题" in detail
    assert "进行中" in detail
    assert "中优先级" in detail


# T3：编辑全部字段并保持列表/详情一致
def test_t3_edit_updates_list_and_detail(client, app):
    task_id = create_task(client, name="旧任务", course="旧课程")

    new_due_date = (date.today() + timedelta(days=10)).isoformat()
    response = client.post(
        f"/tasks/{task_id}/edit",
        data={
            "name": "新任务",
            "course": "新课程",
            "description": "更新后的描述",
            "due_date": new_due_date,
            "priority": "低",
            "status": "进行中",
        },
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "任务已更新。" in html
    assert "新任务" in html
    assert "新课程" in html
    assert "更新后的描述" in html
    assert "低优先级" in html
    assert "进行中" in html

    task = fetch_task(app, task_id)
    assert task is not None
    assert task["name"] == "新任务"
    assert task["course"] == "新课程"
    assert task["description"] == "更新后的描述"
    assert task["due_date"] == new_due_date
    assert task["priority"] == "低"
    assert task["status"] == "进行中"

    list_html = client.get("/").get_data(as_text=True)
    assert "新任务" in list_html
    assert "新课程" in list_html


# T4：删除前必须确认，确认后从数据库删除
def test_t4_delete_requires_confirmation_and_removes_task(client, app):
    task_id = create_task(client, name="待删除任务")

    confirm = client.get(f"/tasks/{task_id}/delete")
    confirm_html = confirm.get_data(as_text=True)
    assert confirm.status_code == 200
    assert "确认删除" in confirm_html
    assert "待删除任务" in confirm_html
    assert task_count(app) == 1

    response = client.post(f"/tasks/{task_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert "已删除。" in response.get_data(as_text=True)
    assert task_count(app) == 0
    assert client.get(f"/tasks/{task_id}").status_code == 404


# T5：状态在三种状态之间调整
def test_t5_status_can_change_between_all_states(client, app):
    task_id = create_task(client, status="待完成")

    for status in ("进行中", "已完成", "待完成"):
        response = client.post(
            f"/tasks/{task_id}/status",
            data={"status": status},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert f"任务状态已更新为“{status}”。" in response.get_data(as_text=True)
        assert fetch_task(app, task_id)["status"] == status


# T6：课程、状态、优先级组合筛选
def test_t6_combined_filters(client):
    math_todo_high = create_task(
        client, name="数学待办高", course="数学", priority="高", status="待完成"
    )
    math_done_low = create_task(
        client, name="数学完成低", course="数学", priority="低", status="已完成"
    )
    english_todo_high = create_task(
        client, name="英语待办高", course="英语", priority="高", status="待完成"
    )
    math_todo_low = create_task(
        client, name="数学待办低", course="数学", priority="低", status="待完成"
    )

    html = client.get(
        "/",
        query_string={"course": "数学", "status": "待完成", "priority": "高"},
    ).get_data(as_text=True)
    assert html.count("<tr data-task-id=") == 1
    assert "数学待办高" in html
    for name in ("数学完成低", "英语待办高", "数学待办低"):
        assert name not in html
    assert f'data-task-id="{math_todo_high}"' in html
    assert f'data-task-id="{math_done_low}"' not in html
    assert f'data-task-id="{english_todo_high}"' not in html
    assert f'data-task-id="{math_todo_low}"' not in html

    status_html = client.get("/", query_string={"status": "已完成"}).get_data(as_text=True)
    assert "数学完成低" in status_html
    assert "数学待办高" not in status_html

    priority_html = client.get("/", query_string={"priority": "低"}).get_data(as_text=True)
    assert "数学完成低" in priority_html
    assert "数学待办低" in priority_html
    assert "数学待办高" not in priority_html


# T7：逾期、即将到期与已完成不提醒
def test_t7_overdue_and_upcoming_rules(client):
    today = date.today()
    overdue_id = create_task(
        client,
        name="昨天到期任务",
        due_date=(today - timedelta(days=1)).isoformat(),
        status="待完成",
    )
    due_today_id = create_task(
        client,
        name="今天到期任务",
        due_date=today.isoformat(),
        status="进行中",
    )
    upcoming_id = create_task(
        client,
        name="三天后到期任务",
        due_date=(today + timedelta(days=3)).isoformat(),
        status="待完成",
    )
    future_id = create_task(
        client,
        name="四天后到期任务",
        due_date=(today + timedelta(days=4)).isoformat(),
        status="待完成",
    )
    completed_overdue_id = create_task(
        client,
        name="已完成过期任务",
        due_date=(today - timedelta(days=2)).isoformat(),
        status="已完成",
    )

    html = client.get("/").get_data(as_text=True)
    assert "逾期" in task_row(html, overdue_id)
    assert "即将到期（今天）" in task_row(html, due_today_id)
    assert "即将到期（3天后）" in task_row(html, upcoming_id)
    assert "即将到期" not in task_row(html, future_id)
    assert "逾期" not in task_row(html, future_id)
    assert "逾期" not in task_row(html, completed_overdue_id)

    assert "逾期" in client.get(f"/tasks/{overdue_id}").get_data(as_text=True)
    assert "逾期" not in client.get(f"/tasks/{completed_overdue_id}").get_data(as_text=True)


# T8：首页统计与 0 条数据时的完成率
def test_t8_dashboard_statistics(client):
    empty_html = client.get("/").get_data(as_text=True)
    assert '<strong id="stat-total">0</strong>' in empty_html
    assert '<strong id="stat-completed">0</strong>' in empty_html
    assert '<strong id="stat-rate">0%</strong>' in empty_html

    create_task(client, name="已完成任务", status="已完成")
    create_task(client, name="待办任务一", status="待完成")
    create_task(client, name="待办任务二", status="进行中")

    html = client.get("/").get_data(as_text=True)
    assert '<strong id="stat-total">3</strong>' in html
    assert '<strong id="stat-completed">1</strong>' in html
    assert '<strong id="stat-rate">33%</strong>' in html


# T9：应用重启后数据仍存在
def test_t9_data_survives_restart(tmp_path):
    database = str(tmp_path / "persistent.db")
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": database,
    }

    first_app = create_app(config)
    first_client = first_app.test_client()
    task_id = create_task(first_client, name="持久化任务")

    second_app = create_app(config)
    second_client = second_app.test_client()
    html = second_client.get("/").get_data(as_text=True)
    assert "持久化任务" in html
    assert f'data-task-id="{task_id}"' in html

    with second_app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 1


# T10：中文界面与 404 错误处理
def test_t10_chinese_pages_and_404(client):
    home = client.get("/").get_data(as_text=True)
    assert '<html lang="zh-CN">' in home
    assert "我的学习任务" in home
    assert "任务总数" in home
    assert "完成率" in home
    assert "新建任务" in home

    unknown_task = client.get("/tasks/999999")
    assert unknown_task.status_code == 404
    assert "页面不存在" in unknown_task.get_data(as_text=True)

    unknown_page = client.get("/no-such-page")
    assert unknown_page.status_code == 404
    assert "页面不存在" in unknown_page.get_data(as_text=True)


def test_invalid_status_update_is_rejected(client, app):
    task_id = create_task(client, status="待完成")

    response = client.post(
        f"/tasks/{task_id}/status",
        data={"status": "延期"},
        follow_redirects=True,
    )
    assert "状态无效，未做修改。" in response.get_data(as_text=True)
    assert fetch_task(app, task_id)["status"] == "待完成"


def test_filter_with_no_matches_shows_clear_empty_state(client):
    create_task(client, course="数学")
    html = client.get("/", query_string={"course": "不存在的课程"}).get_data(
        as_text=True
    )
    assert "没有符合筛选条件的任务" in html
    assert "清除筛选" in html


def test_homepage_handles_200_tasks(app, client):
    now = "2026-01-01 09:00:00"
    due = (date.today() + timedelta(days=10)).isoformat()
    rows = [
        (f"任务 {index:03d}", "批量课程", "", due, "中", "待完成", now, now)
        for index in range(200)
    ]
    with app.app_context():
        connection = get_db()
        connection.executemany(
            """
            INSERT INTO tasks
                (name, course, description, due_date, priority, status,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

    response = client.get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '<strong id="stat-total">200</strong>' in html
    assert html.count("<tr data-task-id=") == 200


def test_init_db_command_is_idempotent(app, runner):
    result = runner.invoke(args=["init-db"])
    assert result.exit_code == 0
    assert "数据库已初始化" in result.output

    result_again = runner.invoke(args=["init-db"])
    assert result_again.exit_code == 0

    with app.app_context():
        tables = {
            row[0]
            for row in get_db()
            .execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            .fetchall()
        }
    assert "tasks" in tables
