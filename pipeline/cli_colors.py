import os

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

if os.name == "nt":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RED = "\033[91m"
WHITE = "\033[97m"

CATEGORY_COLORS = {
    "language_feature": BLUE,
    "framework": GREEN,
    "tool": YELLOW,
    "pattern": MAGENTA,
    "concept": CYAN,
}

CATEGORY_ICONS = {
    "language_feature": "{ }",
    "framework": "< />",
    "tool": "[ ]",
    "pattern": "* *",
    "concept": "(i)",
}

EXERCISE_TYPE_COLORS = {
    "predict_output": GREEN,
    "fix_bug": RED,
    "build_from_spec": BLUE,
}


def category_badge(category: str) -> str:
    color = CATEGORY_COLORS.get(category, WHITE)
    icon = CATEGORY_ICONS.get(category, "?")
    return f"{color}{icon} {category}{RESET}"


def status_ok(msg: str) -> str:
    return f"{GREEN}✓{RESET} {msg}"


def status_fail(msg: str) -> str:
    return f"{RED}✗{RESET} {msg}"


def status_skip(msg: str) -> str:
    return f"{YELLOW}⊘{RESET} {msg}"


def progress(counter: int, total: int, name: str, extra: str = "") -> str:
    pct = counter / total * 100 if total > 0 else 0
    bar_len = 20
    filled = int(bar_len * counter / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    extra_str = f" {extra}" if extra else ""
    return f"{DIM}[{bar}]{RESET} {counter}/{total} ({pct:.0f}%){extra_str} {BOLD}{name}{RESET}"
