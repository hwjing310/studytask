"""SQLite 连接与初始化。"""

from __future__ import annotations

import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db() -> sqlite3.Connection:
    """取得当前请求（或应用上下文）共用的数据库连接。"""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None) -> None:
    """请求结束时关闭连接。"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """按 schema.sql 创建表与索引，不清空已有数据。"""
    db = get_db()
    with current_app.open_resource("schema.sql") as schema_file:
        db.executescript(schema_file.read().decode("utf-8"))
    db.commit()


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """初始化 SQLite 数据库（可重复执行）。"""
    init_db()
    click.echo(f"数据库已初始化：{current_app.config['DATABASE']}")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
