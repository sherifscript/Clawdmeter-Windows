"""Entry point for Clawdmeter-Windows."""

from __future__ import annotations

import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import app_settings
from dashboard import Dashboard
from sprite_player import assets_root


def main() -> int:
    mock = "--mock" in sys.argv
    app = QApplication(sys.argv)
    app.setApplicationName("Clawdmeter")
    app.setOrganizationName(app_settings.ORG)
    app.setQuitOnLastWindowClosed(False)  # tray keeps app alive

    # Apply persisted credentials override before the poller starts.
    cred = app_settings.get_credentials_override()
    if cred:
        os.environ["CLAUDE_CREDENTIALS_PATH"] = cred

    icon_path = assets_root() / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    win = Dashboard(mock=mock)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
