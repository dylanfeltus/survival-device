#!/usr/bin/env python3
"""Pip-Boy style terminal UI for survival AI device.

Green phosphor aesthetic, optimized for 320x240 TFT framebuffer display.
Works in standard terminals with curses or falls back to simple print mode.
"""

from __future__ import annotations

import curses
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try importing chat functionality
try:
    from chat import main as chat_main
    import subprocess
    CHAT_AVAILABLE = True
except ImportError:
    CHAT_AVAILABLE = False


# ============================================================================
# Configuration
# ============================================================================

def load_ui_config() -> Dict[str, Any]:
    """Load UI configuration from ui_config.json."""
    config_path = Path(__file__).parent / "ui_config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    # Defaults
    return {
        "refresh_rate_ms": 500,
        "history_max": 10,
        "scroll_lines": 3,
        "tab_names": ["SURVIVE", "NAV", "MED", "TECH", "INDEX"],
        "color_primary": "green",
        "color_dim": "dark_green",
        "color_warn": "yellow",
        "splash_duration_s": 2,
    }


def load_runtime_state() -> Dict[str, Any]:
    """Load runtime state (battery, power mode) if available."""
    state_path = Path(__file__).parent.parent / "data" / "runtime" / "state.json"
    if state_path.exists():
        try:
            with open(state_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ============================================================================
# Data Models
# ============================================================================

class QAPair:
    """Question-answer pair with citations."""
    def __init__(self, query: str, answer: str, citations: List[Dict], confidence: float):
        self.query = query
        self.answer = answer
        self.citations = citations
        self.confidence = confidence
        self.timestamp = datetime.now()


class AppState:
    """Application state."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tab_names = config["tab_names"]
        self.current_tab = 0
        self.query_text = ""
        self.history: List[QAPair] = []
        self.history_index = -1  # -1 = current, 0+ = viewing history
        self.current_qa: Optional[QAPair] = None
        self.scroll_offset = 0
        self.input_mode = True  # True = query input, False = answer scroll
        self.thinking = False
        self.error_message = ""
        
    def add_to_history(self, qa: QAPair):
        """Add Q&A pair to history, respecting max limit."""
        self.history.append(qa)
        max_history = self.config.get("history_max", 10)
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]
        self.history_index = -1  # Reset to current
        
    def get_display_qa(self) -> Optional[QAPair]:
        """Get the Q&A pair to display (current or from history)."""
        if self.history_index >= 0 and self.history_index < len(self.history):
            return self.history[self.history_index]
        return self.current_qa
    
    def navigate_history(self, direction: int):
        """Navigate history: -1 = newer, +1 = older."""
        if not self.history:
            return
        
        if self.history_index == -1:
            # Currently viewing current, go to most recent history
            if direction > 0:
                self.history_index = len(self.history) - 1
        else:
            new_index = self.history_index - direction
            if new_index < 0:
                self.history_index = -1  # Back to current
            elif new_index < len(self.history):
                self.history_index = new_index
        
        self.scroll_offset = 0  # Reset scroll when changing history item


# ============================================================================
# Chat Integration
# ============================================================================

def query_chat(query: str, tab_name: str) -> Dict[str, Any]:
    """Query the chat backend and return JSON response."""
    if not CHAT_AVAILABLE:
        return {
            "answer": "Chat backend not available. Install dependencies and configure model.",
            "citations": [],
            "confidence": 0.0,
            "error": True,
        }
    
    try:
        # Shell out to chat.py with --json flag
        import subprocess
        cmd = [sys.executable, str(Path(__file__).parent / "chat.py"), "--json", query]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            return {
                "answer": f"Chat error (code {result.returncode}): {result.stderr or result.stdout}",
                "citations": [],
                "confidence": 0.0,
                "error": True,
            }
        
        # Parse JSON output
        response = json.loads(result.stdout)
        return response
        
    except subprocess.TimeoutExpired:
        return {
            "answer": "Query timed out. Model may be too slow or not responding.",
            "citations": [],
            "confidence": 0.0,
            "error": True,
        }
    except json.JSONDecodeError as e:
        return {
            "answer": f"Failed to parse chat response: {e}",
            "citations": [],
            "confidence": 0.0,
            "error": True,
        }
    except Exception as e:
        return {
            "answer": f"Chat error: {e}",
            "citations": [],
            "confidence": 0.0,
            "error": True,
        }


# ============================================================================
# Rendering - Curses Mode
# ============================================================================

class CursesUI:
    """Curses-based UI renderer."""
    
    def __init__(self, stdscr, state: AppState):
        self.stdscr = stdscr
        self.state = state
        self.setup_colors()
        curses.curs_set(0)  # Hide cursor
        self.stdscr.nodelay(1)  # Non-blocking input
        self.stdscr.timeout(100)  # 100ms timeout for getch()
        
    def setup_colors(self):
        """Initialize color pairs for green phosphor theme."""
        curses.start_color()
        curses.use_default_colors()
        
        # Color pairs
        self.COLOR_PRIMARY = 1
        self.COLOR_DIM = 2
        self.COLOR_WARN = 3
        self.COLOR_STATUS = 4
        self.COLOR_HIGHLIGHT = 5
        
        curses.init_pair(self.COLOR_PRIMARY, curses.COLOR_GREEN, -1)
        curses.init_pair(self.COLOR_DIM, curses.COLOR_GREEN, -1)
        curses.init_pair(self.COLOR_WARN, curses.COLOR_YELLOW, -1)
        curses.init_pair(self.COLOR_STATUS, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(self.COLOR_HIGHLIGHT, curses.COLOR_GREEN, -1)
        
    def get_dimensions(self) -> tuple[int, int]:
        """Get terminal dimensions (height, width)."""
        height, width = self.stdscr.getmaxyx()
        return height, width
    
    def draw_splash(self):
        """Draw startup splash screen."""
        self.stdscr.clear()
        height, width = self.get_dimensions()
        
        splash_lines = [
            "╔═══════════════════════════╗",
            "║      S U R V - A I        ║",
            "║      v0.1 OFFLINE         ║",
            "║                           ║",
            "║   Loading knowledge base  ║",
            "║   ████████░░  80%         ║",
            "╚═══════════════════════════╝",
        ]
        
        start_y = (height - len(splash_lines)) // 2
        for i, line in enumerate(splash_lines):
            x = (width - len(line)) // 2
            if x >= 0 and start_y + i < height:
                try:
                    self.stdscr.addstr(
                        start_y + i, x, line,
                        curses.color_pair(self.COLOR_HIGHLIGHT) | curses.A_BOLD
                    )
                except curses.error:
                    pass
        
        self.stdscr.refresh()
        time.sleep(self.state.config.get("splash_duration_s", 2))
    
    def draw_tabs(self, y: int, width: int):
        """Draw tab bar at given y position."""
        tab_names = self.state.tab_names
        current_tab = self.state.current_tab
        
        # Calculate tab widths
        tab_width = max(len(name) + 2 for name in tab_names)
        
        # Draw top border
        try:
            self.stdscr.addstr(y, 0, "┌", curses.color_pair(self.COLOR_PRIMARY))
        except curses.error:
            pass
            
        x = 1
        for i, name in enumerate(tab_names):
            is_current = (i == current_tab)
            
            # Draw tab separator and name
            try:
                if is_current:
                    tab_str = f"[{name}]"
                    self.stdscr.addstr(
                        y, x, tab_str,
                        curses.color_pair(self.COLOR_HIGHLIGHT) | curses.A_BOLD
                    )
                else:
                    tab_str = f"─{name}─"
                    self.stdscr.addstr(y, x, tab_str, curses.color_pair(self.COLOR_DIM))
                x += len(tab_str)
            except curses.error:
                pass
        
        # Fill rest of line
        remaining = width - x - 1
        if remaining > 0:
            try:
                self.stdscr.addstr(y, x, "─" * remaining, curses.color_pair(self.COLOR_PRIMARY))
            except curses.error:
                pass
        
        try:
            self.stdscr.addstr(y, width - 1, "┐", curses.color_pair(self.COLOR_PRIMARY))
        except curses.error:
            pass
    
    def draw_query_input(self, y: int, width: int):
        """Draw query input area."""
        try:
            self.stdscr.addstr(y, 0, "│", curses.color_pair(self.COLOR_PRIMARY))
            
            if self.state.thinking:
                prompt = " > thinking..."
                self.stdscr.addstr(
                    y, 1, prompt[:width-2],
                    curses.color_pair(self.COLOR_WARN) | curses.A_BOLD
                )
            else:
                prompt = " > " + self.state.query_text
                attr = curses.color_pair(self.COLOR_HIGHLIGHT) if self.state.input_mode else curses.color_pair(self.COLOR_DIM)
                if self.state.input_mode:
                    attr |= curses.A_BOLD
                self.stdscr.addstr(y, 1, prompt[:width-2], attr)
            
            self.stdscr.addstr(y, width - 1, "│", curses.color_pair(self.COLOR_PRIMARY))
        except curses.error:
            pass
    
    def draw_answer_area(self, start_y: int, end_y: int, width: int):
        """Draw answer and citations area."""
        qa = self.state.get_display_qa()
        
        if not qa and not self.state.error_message:
            # Show welcome message
            welcome_lines = [
                "",
                "  SURVIVAL AI READY",
                "",
                "  Type your question and press Enter.",
                "  Use arrow keys to navigate.",
                "",
            ]
            for i, line in enumerate(welcome_lines):
                y = start_y + i
                if y >= end_y:
                    break
                try:
                    self.stdscr.addstr(y, 0, "│", curses.color_pair(self.COLOR_PRIMARY))
                    self.stdscr.addstr(y, 1, line[:width-2], curses.color_pair(self.COLOR_DIM))
                    self.stdscr.addstr(y, width - 1, "│", curses.color_pair(self.COLOR_PRIMARY))
                except curses.error:
                    pass
            return
        
        if self.state.error_message:
            # Show error
            try:
                self.stdscr.addstr(start_y, 0, "│", curses.color_pair(self.COLOR_PRIMARY))
                self.stdscr.addstr(
                    start_y, 1, f" ERROR: {self.state.error_message}"[:width-2],
                    curses.color_pair(self.COLOR_WARN)
                )
                self.stdscr.addstr(start_y, width - 1, "│", curses.color_pair(self.COLOR_PRIMARY))
            except curses.error:
                pass
            return
        
        if qa:
            # Prepare text lines
            lines = []
            
            # Answer text
            answer_lines = qa.answer.split("\n")
            for line in answer_lines:
                # Word wrap
                while len(line) > width - 4:
                    lines.append(line[:width-4])
                    line = line[width-4:]
                lines.append(line)
            
            # Add spacing
            lines.append("")
            
            # Citations
            if qa.citations:
                for i, citation in enumerate(qa.citations, 1):
                    title = citation.get("title", "Unknown")
                    source = citation.get("source", "Unknown")
                    lines.append(f"[{i}] {title} - {source}")
            
            # Add confidence info
            lines.append("")
            conf_pct = int(qa.confidence * 100)
            lines.append(f"Confidence: {conf_pct}%")
            
            # Show history indicator if viewing history
            if self.state.history_index >= 0:
                lines.insert(0, f"[HISTORY {len(self.state.history) - self.state.history_index}/{len(self.state.history)}]")
                lines.insert(1, "")
            
            # Render visible lines with scroll
            visible_lines = lines[self.state.scroll_offset:]
            for i, line in enumerate(visible_lines):
                y = start_y + i
                if y >= end_y:
                    break
                try:
                    self.stdscr.addstr(y, 0, "│", curses.color_pair(self.COLOR_PRIMARY))
                    self.stdscr.addstr(y, 1, f" {line}"[:width-2], curses.color_pair(self.COLOR_PRIMARY))
                    self.stdscr.addstr(y, width - 1, "│", curses.color_pair(self.COLOR_PRIMARY))
                except curses.error:
                    pass
    
    def draw_status_bar(self, y: int, width: int):
        """Draw status bar at bottom."""
        # Get runtime state
        runtime_state = load_runtime_state()
        battery_pct = runtime_state.get("battery_pct", runtime_state.get("percent"))
        power_mode = runtime_state.get("power_mode", runtime_state.get("recommended_mode", "NORMAL")).upper()
        
        # If no state file, try to get from last query result
        if battery_pct is None and self.state.current_qa:
            # This would come from the chat response
            battery_pct = 0  # Default fallback
        
        # Build status line
        current_time = datetime.now().strftime("%H:%M")
        model_status = "OFFLINE"  # Could be enhanced to check actual model status
        
        if battery_pct is not None:
            status_text = f" ■ BATT {battery_pct}%  ■ {power_mode}  ■ {current_time}  ■ {model_status} "
        else:
            status_text = f" ■ {power_mode}  ■ {current_time}  ■ {model_status} "
        
        # Center status text
        padding = (width - len(status_text)) // 2
        status_text = " " * padding + status_text
        
        # Draw status bar
        try:
            self.stdscr.addstr(y, 0, "├", curses.color_pair(self.COLOR_PRIMARY))
            self.stdscr.addstr(y, 1, "─" * (width - 2), curses.color_pair(self.COLOR_PRIMARY))
            self.stdscr.addstr(y, width - 1, "┤", curses.color_pair(self.COLOR_PRIMARY))
            
            self.stdscr.addstr(y + 1, 0, "│", curses.color_pair(self.COLOR_PRIMARY))
            self.stdscr.addstr(
                y + 1, 1, status_text[:width-2],
                curses.color_pair(self.COLOR_STATUS) | curses.A_BOLD
            )
            self.stdscr.addstr(y + 1, width - 1, "│", curses.color_pair(self.COLOR_PRIMARY))
            
            self.stdscr.addstr(y + 2, 0, "└", curses.color_pair(self.COLOR_PRIMARY))
            self.stdscr.addstr(y + 2, 1, "─" * (width - 2), curses.color_pair(self.COLOR_PRIMARY))
            self.stdscr.addstr(y + 2, width - 1, "┘", curses.color_pair(self.COLOR_PRIMARY))
        except curses.error:
            pass
    
    def draw(self):
        """Main draw routine."""
        self.stdscr.clear()
        height, width = self.get_dimensions()
        
        # Layout:
        # 0: tabs
        # 1: blank
        # 2: query input
        # 3: blank
        # 4 to height-4: answer area
        # height-3 to height-1: status bar (3 lines)
        
        self.draw_tabs(0, width)
        self.draw_query_input(2, width)
        
        answer_start = 4
        answer_end = height - 4
        self.draw_answer_area(answer_start, answer_end, width)
        
        self.draw_status_bar(height - 3, width)
        
        self.stdscr.refresh()
    
    def handle_input(self) -> bool:
        """Handle keyboard input. Returns False if should quit."""
        try:
            key = self.stdscr.getch()
        except curses.error:
            return True
        
        if key == -1:
            return True
        
        # Quit keys
        if key == ord('q') or key == ord('Q'):
            return False
        if key == 3:  # Ctrl+C
            return False
        
        # Tab key - toggle input/scroll mode
        if key == ord('\t') or key == 9:
            self.state.input_mode = not self.state.input_mode
            return True
        
        # Left/Right arrow - switch tabs
        if key == curses.KEY_LEFT:
            self.state.current_tab = (self.state.current_tab - 1) % len(self.state.tab_names)
            return True
        if key == curses.KEY_RIGHT:
            self.state.current_tab = (self.state.current_tab + 1) % len(self.state.tab_names)
            return True
        
        # Page Up/Down - navigate history
        if key == curses.KEY_PPAGE:  # Page Up
            self.state.navigate_history(1)  # Go back in history
            return True
        if key == curses.KEY_NPAGE:  # Page Down
            self.state.navigate_history(-1)  # Go forward in history
            return True
        
        # Up/Down arrow - context dependent
        if key == curses.KEY_UP:
            if self.state.input_mode:
                # Could implement command history here
                pass
            else:
                # Scroll answer up
                self.state.scroll_offset = max(0, self.state.scroll_offset - self.state.config.get("scroll_lines", 3))
            return True
        
        if key == curses.KEY_DOWN:
            if self.state.input_mode:
                # Could implement command history here
                pass
            else:
                # Scroll answer down
                self.state.scroll_offset += self.state.config.get("scroll_lines", 3)
            return True
        
        # Enter - submit query
        if key == ord('\n') or key == curses.KEY_ENTER or key == 10:
            if self.state.query_text and not self.state.thinking:
                self.submit_query()
            return True
        
        # Text input (only in input mode)
        if self.state.input_mode and not self.state.thinking:
            if key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                self.state.query_text = self.state.query_text[:-1]
            elif 32 <= key <= 126:  # Printable ASCII
                self.state.query_text += chr(key)
        
        return True
    
    def submit_query(self):
        """Submit current query to chat backend."""
        query = self.state.query_text
        tab_name = self.state.tab_names[self.state.current_tab]
        
        # Set thinking state
        self.state.thinking = True
        self.state.error_message = ""
        self.draw()
        
        # Query chat backend
        try:
            response = query_chat(query, tab_name)
            
            if response.get("error"):
                self.state.error_message = response.get("answer", "Unknown error")
            else:
                # Create Q&A pair
                qa = QAPair(
                    query=query,
                    answer=response.get("answer", "No answer received"),
                    citations=response.get("citations", []),
                    confidence=response.get("confidence", 0.0)
                )
                self.state.current_qa = qa
                self.state.add_to_history(qa)
                self.state.scroll_offset = 0
        except Exception as e:
            self.state.error_message = f"Query failed: {e}"
        
        # Reset state
        self.state.thinking = False
        self.state.query_text = ""
        self.state.input_mode = False  # Switch to scroll mode to view answer
    
    def run(self):
        """Main UI loop."""
        self.draw_splash()
        
        while True:
            self.draw()
            if not self.handle_input():
                break
            time.sleep(0.01)  # Small delay to prevent CPU spinning


# ============================================================================
# Fallback Mode (No Curses)
# ============================================================================

def run_fallback_mode(state: AppState):
    """Simple print-based UI when curses is not available."""
    print("=" * 40)
    print("  SURVIVAL AI - FALLBACK MODE")
    print("  (curses not available)")
    print("=" * 40)
    print()
    print("Commands:")
    print("  Type question and press Enter")
    print("  'quit' or 'exit' to quit")
    print()
    
    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if not query:
            continue
        
        if query.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        
        # Query chat
        print("\nThinking...")
        tab_name = state.tab_names[state.current_tab]
        response = query_chat(query, tab_name)
        
        print("\n" + "=" * 40)
        print("ANSWER:")
        print("-" * 40)
        print(response.get("answer", "No answer"))
        print()
        
        if response.get("citations"):
            print("CITATIONS:")
            for i, citation in enumerate(response["citations"], 1):
                title = citation.get("title", "Unknown")
                source = citation.get("source", "Unknown")
                print(f"[{i}] {title} - {source}")
            print()
        
        conf = response.get("confidence", 0.0)
        print(f"Confidence: {int(conf * 100)}%")
        print("=" * 40)
        print()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    config = load_ui_config()
    state = AppState(config)
    
    # Try curses mode first
    try:
        curses.wrapper(lambda stdscr: CursesUI(stdscr, state).run())
    except Exception as e:
        # Fall back to simple mode
        print(f"Curses mode failed ({e}), using fallback mode...")
        run_fallback_mode(state)


if __name__ == "__main__":
    main()
