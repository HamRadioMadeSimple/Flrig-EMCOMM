"""The keyboard shortcut list shown in the Hotkeys box and Help > Keyboard shortcuts."""


SHORTCUTS = [  # (keys, what it does, shown in the Hotkeys legend)
    ("Double-click / Enter", "Tune the rig to the station", True),
    ("F", "Favorite on / off", True),
    ("R", "✔ Reliable (go-to station) on / off", True),
    ("Ctrl+F", "Search (Esc clears, Down goes to the list)", True),
    ("Ctrl+G", "Show the station on the rig now", True),
    ("Click frequency", "Switch kHz / MHz / Rig style", True),
    ("Ctrl+T", "ATU Tune", True),
    ("Ctrl+N", "Add station (starts from the rig)", True),
    ("F2", "Edit station", True),
    ("Ctrl+Tab", "Next tab (Ctrl+Shift+Tab: previous)", True),
    ("Ctrl+1 … 9", "Go to tab (1 = Favorites, 2 = All Stations)", True),
    ("F1", "All keyboard shortcuts", True),
    ("Delete", "Delete station(s)", False),
    ("Ctrl+A", "Highlight all stations on the tab", False),
    ("Ctrl+D", "Clone station (same details, new frequency)", False),
    ("Ctrl+Up / Down", "Move station up / down", False),
    ("Ctrl+Shift+Left / Right", "Move tab left / right", False),
    ("Ctrl+I", "Import stations", False),
    ("Ctrl+L", "Switch Light / Dark", False),
    ("Esc", "Close a window, or clear Search", False),
]
