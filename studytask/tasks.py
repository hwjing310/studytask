"""任务管理路由与校验逻辑。"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .db import get_db

bp = Blueprint("tasks", __name__)

PRIORITIES = ("高", "中", "低")
STATUSES = ("待完成", "进行中", "已完成")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _empty_values() -> dict:
    return {
        "name": "",
        "course": "",
        "description": "",
        "due_date": "",
        "priority": "中",
        "status": "待完成",
    }


def _validate_task_form(form) -> tuple[dict, dict]:
    """校验并清洗表单，返回表单值和字段错误。"""
    values = {
        "name": (form.get("name") or "").strip(),
        "course": (form.get("course") or "").strip(),
        "description": (form.get("description") or "").strip(),
        "due_date": (form.get("due_date") or "").strip(),
        "priority": (form.get("priority") or "中").strip(),
        "status": (form.get("status") or "待完成").strip(),
    }
    errors: dict[str, str] = {}

    if not values["name"]:
        errors["name"] = "请输入任务名称。"
    elif len(values["name"]) > 100:
        errors["name"] = "任务名称不能超过 100 个字符。"

    if not values["course"]:
        errors["course"] = "请输入所属课程。"
    elif len(values["course"]) > 60:
        errors["course"] = "所属课程不能超过 60 个字符。"

    if len(values["description"]) > 1000:
        errors["description"] = "任务描述不能超过 1000 个字符。"

    if not values["due_date"]:
        errors["due_date"] = "请选择截止日期。"
    elif not DATE_PATTERN.fullmatch(values["due_date"]):
        errors["due_date"] = "截止日期格式必须为 YYYY-MM-DD。"
    else:
        try:
            date.fromisoformat(values["due_date"])
        except ValueError:
            errors["due_date"] = "截止日期不是有效日期。"

    if values["priority"] not in PRIORITIES:
        errors["priority"] = "优先级必须为“高”“中”或“低”。"

    if values["status"] not in STATUSES:
        errors["status"] = "状态必须为“待完成”“进行中”或“已完成”。"

    return values, errors


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _task_alert(task) -> dict | None:
    """计算未完成任务的逾期/即将到期提示。"""
    if task["status"] == "已完成":
        return None

    try:
        due_date = date.fromisoformat(task["due_date"])
    except (TypeError, ValueError):
        return None

    today = date.today()
    if due_date < today:
        return {"kind": "overdue", "label": "逾期"}

    if due_date <= today + timedelta(days=3):
        days = (due_date - today).days
        label = "即将到期（今天）" if days == 0 else f"即将到期（{days}天后）"
        return {"kind": "upcoming", "label": label}

    return None


def _get_task(task_id: int):
    task = get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        abort(404)
    return task


def _dashboard_stats() -> tuple[int, int, int]:
    row = get_db().execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status = '已完成' THEN 1 ELSE 0 END), 0)
                AS completed
        FROM tasks
        """
    ).fetchone()
    total = int(row["total"])
    completed = int(row["completed"])
    completion_rate = round(completed * 100 / total) if total else 0
    return total, completed, completion_rate


@bp.get("/")
def index():
    db = get_db()
    filters = {
        "course": (request.args.get("course") or "").strip(),
        "status": (request.args.get("status") or "").strip(),
        "priority": (request.args.get("priority") or "").strip(),
    }
    if filters["status"] not in STATUSES:
        filters["status"] = ""
    if filters["priority"] not in PRIORITIES:
        filters["priority"] = ""

    conditions: list[str] = []
    params: list[str] = []
    if filters["course"]:
        conditions.append("course = ?")
        params.append(filters["course"])
    if filters["status"]:
        conditions.append("status = ?")
        params.append(filters["status"])
    if filters["priority"]:
        conditions.append("priority = ?")
        params.append(filters["priority"])

    query = "SELECT * FROM tasks"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY due_date ASC, id ASC"

    tasks = []
    for row in db.execute(query, params).fetchall():
        task = dict(row)
        task["alert"] = _task_alert(task)
        tasks.append(task)

    courses = [
        row["course"]
        for row in db.execute(
            "SELECT DISTINCT course FROM tasks ORDER BY course ASC"
        ).fetchall()
    ]
    total, completed, completion_rate = _dashboard_stats()

    return render_template(
        "index.html",
        tasks=tasks,
        courses=courses,
        filters=filters,
        priorities=PRIORITIES,
        statuses=STATUSES,
        total=total,
        completed=completed,
        completion_rate=completion_rate,
    )


@bp.route("/tasks/new", methods=("GET", "POST"))
def create():
    values = _empty_values()
    errors: dict[str, str] = {}

    if request.method == "POST":
        values, errors = _validate_task_form(request.form)
        if not errors:
            db = get_db()
            now = _now()
            cursor = db.execute(
                """
                INSERT INTO tasks
                    (name, course, description, due_date, priority, status,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values["name"],
                    values["course"],
                    values["description"],
                    values["due_date"],
                    values["priority"],
                    values["status"],
                    now,
                    now,
                ),
            )
            db.commit()
            flash("任务创建成功。", "success")
            return redirect(url_for("tasks.detail", task_id=cursor.lastrowid))

    return render_template(
        "task_form.html",
        mode="create",
        values=values,
        errors=errors,
        task=None,
        priorities=PRIORITIES,
        statuses=STATUSES,
    )


@bp.get("/tasks/<int:task_id>")
def detail(task_id: int):
    task = _get_task(task_id)
    return render_template(
        "task_detail.html",
        task=task,
        alert=_task_alert(task),
        statuses=STATUSES,
    )


@bp.route("/tasks/<int:task_id>/edit", methods=("GET", "POST"))
def edit(task_id: int):
    task = _get_task(task_id)
    values = {
        "name": task["name"],
        "course": task["course"],
        "description": task["description"],
        "due_date": task["due_date"],
        "priority": task["priority"],
        "status": task["status"],
    }
    errors: dict[str, str] = {}

    if request.method == "POST":
        values, errors = _validate_task_form(request.form)
        if not errors:
            db = get_db()
            db.execute(
                """
                UPDATE tasks
                SET name = ?, course = ?, description = ?, due_date = ?,
                    priority = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    values["name"],
                    values["course"],
                    values["description"],
                    values["due_date"],
                    values["priority"],
                    values["status"],
                    _now(),
                    task_id,
                ),
            )
            db.commit()
            flash("任务已更新。", "success")
            return redirect(url_for("tasks.detail", task_id=task_id))

    return render_template(
        "task_form.html",
        mode="edit",
        values=values,
        errors=errors,
        task=task,
        priorities=PRIORITIES,
        statuses=STATUSES,
    )


@bp.post("/tasks/<int:task_id>/status")
def update_status(task_id: int):
    _get_task(task_id)
    status = (request.form.get("status") or "").strip()
    if status not in STATUSES:
        flash("状态无效，未做修改。", "error")
        return redirect(url_for("tasks.detail", task_id=task_id))

    db = get_db()
    db.execute(
        "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
        (status, _now(), task_id),
    )
    db.commit()
    flash(f"任务状态已更新为“{status}”。", "success")
    return redirect(url_for("tasks.detail", task_id=task_id))


@bp.route("/tasks/<int:task_id>/delete", methods=("GET", "POST"))
def delete(task_id: int):
    task = _get_task(task_id)

    if request.method == "POST":
        db = get_db()
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        db.commit()
        flash(f"任务“{task['name']}”已删除。", "success")
        return redirect(url_for("tasks.index"))

    return render_template("delete_confirm.html", task=task)
