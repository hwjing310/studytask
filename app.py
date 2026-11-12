"""StudyTask 应用入口。

运行：python app.py
"""

from __future__ import annotations

import os

from studytask import create_app

app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("STUDYTASK_PORT", "5000")),
        debug=False,
    )
