"""StudyTask 个人学习任务管理系统。"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, render_template


def create_app(test_config: dict | None = None) -> Flask:
    """创建并配置 Flask 应用。"""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get(
            "STUDYTASK_SECRET_KEY", "studytask-local-single-user-key"
        ),
        DATABASE=str(Path(app.instance_path) / "studytask.db"),
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    database = str(app.config["DATABASE"])
    if database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)

    from . import db

    db.init_app(app)

    # 首次启动时自动建表；重复执行 init-db 也不会破坏已有数据。
    with app.app_context():
        db.init_db()

    from . import tasks

    app.register_blueprint(tasks.bp)

    @app.errorhandler(404)
    def page_not_found(error):  # pragma: no cover - 由路由测试覆盖
        return render_template("404.html"), 404

    return app
