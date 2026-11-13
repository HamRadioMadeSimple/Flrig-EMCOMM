"""Start the app:  python -m flrig_emcomm   (or double-click run.py).

Options:  --debug    write extra detail to the log file
          --console  (Windows) keep the black command window open
"""

import logging
import logging.handlers
import sys

from . import APP_NAME
from .desktop import hide_console_window
from .paths import LOG_FILE, make_data_dir

log = logging.getLogger("flrig_emcomm")


def setup_logging():
    """Problems go to flrig_emcomm.log next to the program (kept small), so a
    tester can send it in. Nothing is logged about normal use."""
    level = logging.DEBUG if "--debug" in sys.argv else logging.INFO
    make_data_dir()
    try:
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=200_000, backupCount=1, encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)

    def unhandled(exc_type, exc, tb):
        log.critical("Unexpected error", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = unhandled
    log.info("%s starting (Python %s, %s)", APP_NAME, sys.version.split()[0], sys.platform)


def main():
    setup_logging()
    hide_console_window()
    from .app import App
    app = App()

    def tk_error(exc_type, exc, tb):  # errors inside button clicks etc.
        log.error("Error in the window", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)
    app.report_callback_exception = tk_error
    app.mainloop()
    log.info("Closed normally")


if __name__ == "__main__":
    main()
