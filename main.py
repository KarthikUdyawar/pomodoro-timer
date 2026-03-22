"""
🍅 Pomodoro Timer
=================
A simple, distraction-free Pomodoro timer built with Streamlit.
"""

import base64
import streamlit as st
import time

st.set_page_config(page_title="Pomodoro Timer", page_icon="🍅", layout="centered")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LONG_EVERY: int = 4

ALARM_PATH: str = "alarm.mp3"


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------


@st.cache_resource
def load_alarm() -> str:
    """Load the alarm MP3 and return it as a base64-encoded string.

    Uses ``@st.cache_resource`` so the file is read from disk only once
    per server process, regardless of how many times the page reruns.

    Returns
    -------
    str
        Base64-encoded contents of ``alarm.mp3``.

    Raises
    ------
    FileNotFoundError
        If ``alarm.mp3`` is not found in the working directory.
    """
    with open(ALARM_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


alarm_b64 = load_alarm()


def play_alarm() -> None:
    """Inject a hidden, auto-playing ``<audio>`` element into the page.

    The MP3 is embedded as a base64 data URI so no static file server is
    required. The element is invisible and plays exactly once per call.
    Browsers that block auto-play will silently skip it.
    """
    st.markdown(
        f"""
        <audio autoplay style="display:none">
          <source src="data:audio/mp3;base64,{alarm_b64}" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


def _init_state() -> None:
    """Initialise all session-state keys with their default values.

    Only sets a key if it does not already exist, so existing state is
    never overwritten on rerun.
    """
    defaults = dict(
        mode="Focus",  # Current mode: "Focus" | "Short Break" | "Long Break"
        running=False,  # Whether the timer is actively counting down
        remaining=25.0 * 60,  # Seconds left in the current session
        sessions=0,  # Total completed Focus sessions (all-time)
        sessions_in_cycle=0,  # Completed Focus sessions in the current cycle (0-3)
        total_focus=0.0,  # Cumulative seconds spent in Focus mode
        last_tick=None,  # Wall-clock time of the previous rerun (float | None)
        dur_focus=25,  # User-configured Focus duration in minutes
        dur_short=5,  # User-configured Short Break duration in minutes
        dur_long=15,  # User-configured Long Break duration in minutes
        auto_start=True,  # Whether the next session starts automatically
        play_sound=False,  # True for one rerun after a session completes
    )
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_state()
ss = st.session_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def durations() -> dict[str, float]:
    """Return current session durations in seconds, reflecting user settings.

    Returns
    -------
    dict[str, float]
        Keys: ``"Focus"``, ``"Short Break"``, ``"Long Break"``.
    """
    return {
        "Focus": ss.dur_focus * 60,
        "Short Break": ss.dur_short * 60,
        "Long Break": ss.dur_long * 60,
    }


def next_label() -> str:
    """Return a human-readable label for the mode that follows the current one.

    For Focus, predicts whether the *next* transition will be a Short Break
    or Long Break based on how many sessions are left in the cycle.

    Returns
    -------
    str
        One of ``"Focus"``, ``"Short Break"``, or ``"Long Break"``.
    """
    if ss.mode != "Focus":
        return "Focus"
    return "Long Break" if (ss.sessions_in_cycle + 1) >= LONG_EVERY else "Short Break"


def next_mode_after_focus() -> str:
    """Determine which mode follows a completed Focus session.

    Must be called *after* ``sessions_in_cycle`` has already been
    incremented.  When ``sessions_in_cycle`` wraps back to 0 (i.e.
    ``% LONG_EVERY == 0``) the user has earned a Long Break.

    Returns
    -------
    str
        ``"Long Break"`` or ``"Short Break"``.
    """
    return "Long Break" if ss.sessions_in_cycle % LONG_EVERY == 0 else "Short Break"


def switch_mode(mode: str) -> None:
    """Switch to a different mode and reset the timer without starting it.

    Parameters
    ----------
    mode : str
        Target mode — one of ``"Focus"``, ``"Short Break"``, ``"Long Break"``.
    """
    ss.mode = mode
    ss.remaining = float(durations()[mode])
    ss.running = False
    ss.last_tick = None


def fmt(seconds: float) -> str:
    """Format a duration in seconds as ``MM:SS``.

    Parameters
    ----------
    seconds : float
        Non-negative duration in seconds.

    Returns
    -------
    str
        Zero-padded string, e.g. ``"04:07"``.
    """
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


# ---------------------------------------------------------------------------
# Timing logic  (runs at the top of every rerun)
# ---------------------------------------------------------------------------

ss.play_sound = False  # reset each rerun; set to True below when session ends

if ss.running:
    now = time.time()

    if ss.last_tick is not None:
        dt = now - ss.last_tick

        # Accumulate focus time only while there is time on the clock
        if ss.mode == "Focus" and ss.remaining > 0:
            ss.total_focus += dt

        ss.remaining = max(0.0, ss.remaining - dt)

    ss.last_tick = now

    # Session complete
    if ss.remaining <= 0:
        ss.running = False
        ss.last_tick = None
        ss.play_sound = True

        if ss.mode == "Focus":
            ss.sessions += 1
            ss.sessions_in_cycle = (ss.sessions_in_cycle + 1) % LONG_EVERY
            next_mode = next_mode_after_focus()
        else:
            next_mode = "Focus"

        ss.remaining = float(durations()[next_mode])
        ss.mode = next_mode

        if ss.auto_start:
            ss.running = True
            ss.last_tick = time.time()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🍅 Pomodoro Timer")

# Play alarm sound for one rerun after a session completes
if ss.play_sound:
    play_alarm()

# ── Mode selector ──────────────────────────────────────────────────────────
t1, t2, t3 = st.columns(3)
with t1:
    if st.button("🍅 Focus", use_container_width=True):
        switch_mode("Focus")
with t2:
    if st.button("☕ Short Break", use_container_width=True):
        switch_mode("Short Break")
with t3:
    if st.button("🌿 Long Break", use_container_width=True):
        switch_mode("Long Break")

st.divider()

# ── Timer display ──────────────────────────────────────────────────────────
st.subheader(f"Mode: {ss.mode}")

total = durations()[ss.mode]
remaining = max(0.0, min(ss.remaining, float(total)))
progress = max(0.0, min(1.0, 1.0 - (remaining / total))) if total > 0 else 0.0

st.metric("Time Remaining", fmt(remaining))
st.progress(float(progress))

# ── Cycle indicator ────────────────────────────────────────────────────────
sic = ss.sessions_in_cycle
dots = ""
for i in range(LONG_EVERY):
    if i < sic:
        dots += "🔴 "  # completed this cycle
    elif i == sic and ss.mode == "Focus":
        dots += "🟠 "  # in progress
    else:
        dots += "⚪ "  # upcoming

pomo_num = sic + 1 if ss.mode == "Focus" else sic
st.write(
    f"Cycle: {dots.strip()}  |  "
    f"Pomodoro {pomo_num}/{LONG_EVERY}  |  "
    f"Next: **{next_label()}**"
)

st.divider()

# ── Controls ───────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("↺ Reset", use_container_width=True):
        ss.remaining = float(durations()[ss.mode])
        ss.running = False
        ss.last_tick = None
with c2:
    label = "⏸ Pause" if ss.running else "▶ Start"
    if st.button(label, use_container_width=True, type="primary"):
        ss.running = not ss.running
        ss.last_tick = time.time() if ss.running else None
with c3:
    if st.button("⏭ Skip", use_container_width=True):
        if ss.mode == "Focus":
            ss.sessions += 1
            ss.sessions_in_cycle = (ss.sessions_in_cycle + 1) % LONG_EVERY
            next_mode = next_mode_after_focus()
        else:
            next_mode = "Focus"
        switch_mode(next_mode)

st.divider()

# ── Stats ──────────────────────────────────────────────────────────────────
s1, s2, s3 = st.columns(3)
s1.metric("Sessions", ss.sessions)
s2.metric("Focus min", int(ss.total_focus // 60))
s3.metric("Sets done", ss.sessions // LONG_EVERY)

# ── Settings ───────────────────────────────────────────────────────────────
with st.expander("⚙️ Settings"):
    ss.dur_focus = st.slider("🍅 Focus (min)", 1, 90, ss.dur_focus)
    ss.dur_short = st.slider("☕ Short break (min)", 1, 30, ss.dur_short)
    ss.dur_long = st.slider("🌿 Long break (min)", 1, 60, ss.dur_long)
    ss.auto_start = st.toggle("Auto-start next session", value=ss.auto_start)

    if st.button("✅ Apply & reset timer"):
        ss.remaining = float(durations()[ss.mode])
        ss.running = False
        ss.last_tick = None
        st.rerun()

# ── Auto-rerun every second while the timer is running ─────────────────────
if ss.running:
    time.sleep(1)
    st.rerun()
