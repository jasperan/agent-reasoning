package views

import (
	"strings"
	"testing"
	"time"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/client"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
)

// The screenshot harness drives every TUI at this size, so layout regressions
// are asserted here instead of being caught by eye in a PNG.
const (
	harnessWidth  = 120
	harnessHeight = 36
)

// runBounded runs one command with a deadline. huh batches every field
// transition together with a text-cursor blink tick that sleeps about half a
// second, and these tests must not depend on the clock, so a slow command is
// abandoned rather than awaited.
func runBounded(cmd tea.Cmd, d time.Duration) (tea.Msg, bool) {
	done := make(chan tea.Msg, 1)
	go func() { done <- cmd() }()
	select {
	case msg := <-done:
		return msg, true
	case <-time.After(d):
		return nil, false
	}
}

// settle does what the bubbletea runtime does: run the command the view
// returned, feed the resulting message back to the view, and repeat until the
// view stops asking for work.
//
// This is not optional scaffolding. A huh field reports "advance to the next
// field" as a message produced by a command the field returns, so a view that
// only forwards key presses to its form never leaves the first field.
func settle(v app.View, cmd tea.Cmd) app.View {
	for cmd != nil {
		msg, ok := runBounded(cmd, 50*time.Millisecond)
		if !ok {
			return v
		}
		if batch, isBatch := msg.(tea.BatchMsg); isBatch {
			for _, sub := range batch {
				v = settle(v, sub)
			}
			return v
		}
		v, cmd = v.Update(msg)
	}
	return v
}

// sendKey delivers a key press and settles whatever the view returned.
func sendKey(v app.View, msg tea.KeyPressMsg) app.View {
	next, cmd := v.Update(msg)
	return settle(next, cmd)
}

// typeText types into the focused field without settling. The text field applies
// each keystroke synchronously, so only the submit needs its command drained.
func typeText(v app.View, s string) app.View {
	for _, r := range s {
		next, _ := v.Update(tea.KeyPressMsg{Code: r, Text: string(r)})
		v = next
	}
	return v
}

func maxLineWidth(s string) int {
	widest := 0
	for _, line := range strings.Split(s, "\n") {
		if w := lipgloss.Width(line); w > widest {
			widest = w
		}
	}
	return widest
}

func enter() tea.KeyPressMsg { return tea.KeyPressMsg{Code: tea.KeyEnter} }

// testContext wires a server client pointed at the documented loopback default,
// so any operation a view starts fails on a refused connection instead of a nil
// dereference. Nothing listens there during a test run.
func testContext() *app.Context {
	return &app.Context{
		ServerClient: client.NewServerClient(),
		CurrentModel: "test-model",
		Connected:    false,
	}
}

// --- duel: two-agent picker -------------------------------------------------

func TestDuelSelectionStartsDuelWithChosenAgents(t *testing.T) {
	v := NewDuelView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*DuelView)

	want := v.agents
	// First enter confirms the left select, second confirms the right select;
	// the defaults are the first two agents.
	v = sendKey(v, enter()).(*DuelView)
	v = sendKey(v, enter()).(*DuelView)

	if v.phase != DuelInput {
		t.Fatalf("phase = %v, want DuelInput after confirming both agents", v.phase)
	}
	if v.left.agentName != want[0].Name {
		t.Errorf("left agent = %q, want %q", v.left.agentName, want[0].Name)
	}
	if v.right.agentName != want[1].Name {
		t.Errorf("right agent = %q, want %q", v.right.agentName, want[1].Name)
	}
}

// TestDuelSelectionRejectsTheSameAgentTwice pins the rule the hand-rolled
// cursor used to enforce silently by ignoring the key: both sides of a duel must
// be different strategies.
func TestDuelSelectionRejectsTheSameAgentTwice(t *testing.T) {
	v := NewDuelView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*DuelView)

	// Confirm the left agent, step onto the right select, then walk its cursor
	// back onto the same agent the left side already holds.
	v = sendKey(v, enter()).(*DuelView)
	v = sendKey(v, tea.KeyPressMsg{Code: tea.KeyUp}).(*DuelView)
	v = sendKey(v, enter()).(*DuelView)

	if v.phase != DuelSelection {
		t.Fatalf("phase = %v, want DuelSelection: an identical pair must not start a duel", v.phase)
	}
	if got := v.View(); !strings.Contains(got, "different agent") {
		t.Errorf("expected an inline validation message about picking a different agent, view:\n%s", got)
	}
}

func TestDuelSelectionLayoutAtHarnessSize(t *testing.T) {
	v := NewDuelView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*DuelView)

	got := v.View()
	if w := maxLineWidth(got); w > harnessWidth {
		t.Errorf("selection screen renders %d columns wide, harness is %d:\n%s", w, harnessWidth, got)
	}
	for _, a := range v.agents[:2] {
		if !strings.Contains(got, a.Name) {
			t.Errorf("selection screen is missing agent %q:\n%s", a.Name, got)
		}
	}
}

// --- arena: query prompt ----------------------------------------------------

func TestArenaInputPhaseRendersPromptAtHarnessSize(t *testing.T) {
	v := NewArenaView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*ArenaView)

	got := v.View()
	if !strings.Contains(got, "Query") {
		t.Errorf("arena input phase should render the huh prompt:\n%s", got)
	}
	if w := maxLineWidth(got); w > harnessWidth {
		t.Errorf("arena input phase renders %d columns wide, harness is %d:\n%s", w, harnessWidth, got)
	}
}

func TestArenaInputPhaseRejectsBlankQuery(t *testing.T) {
	v := NewArenaView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*ArenaView)

	v = sendKey(v, enter()).(*ArenaView)

	if v.phase != ArenaInput {
		t.Fatalf("phase = %v, want ArenaInput: a blank query must not start a race", v.phase)
	}
}

func TestArenaInputPhaseStartsRaceWithTypedQuery(t *testing.T) {
	v := NewArenaView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*ArenaView)

	v = typeText(v, "compare sorting algorithms").(*ArenaView)
	v = sendKey(v, enter()).(*ArenaView)

	if got, want := v.query, "compare sorting algorithms"; got != want {
		t.Errorf("query = %q, want %q", got, want)
	}
	// Nothing listens on the loopback server during a test, so every cell fails
	// at once and the phase may already have collapsed from ArenaRacing to
	// ArenaSummary. What must hold is that the race was actually dispatched: no
	// cell may still be waiting for a query.
	if v.phase == ArenaInput {
		t.Fatal("a submitted query must leave the input phase")
	}
	for i, c := range v.cells {
		if c.Status == CellWaiting {
			t.Errorf("cell %d (%s) is still waiting, so startRace never ran", i, c.AgentName)
		}
	}
}

// --- debug: query prompt ----------------------------------------------------

func TestDebugInputPhaseRendersPromptAtHarnessSize(t *testing.T) {
	v := NewDebugView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*DebugView)

	got := v.View()
	if !strings.Contains(got, "Query") {
		t.Errorf("debug input phase should render the huh prompt:\n%s", got)
	}
	// renderInputPhase wraps its content in a (2,4) padding, so this also catches
	// a form sized without leaving room for that padding.
	if w := maxLineWidth(got); w > harnessWidth {
		t.Errorf("debug input phase renders %d columns wide, harness is %d:\n%s", w, harnessWidth, got)
	}
}

// TestDebugInputPhaseValidationBlocksTheSession pins that an empty query never
// reaches startDebugSession: agentID is only assigned on the submit path.
func TestDebugInputPhaseValidationBlocksTheSession(t *testing.T) {
	v := NewDebugView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*DebugView)

	v = sendKey(v, enter()).(*DebugView)

	if v.agentID != "" {
		t.Errorf("agentID = %q, want empty: a blank query must not start a session", v.agentID)
	}
	if v.statusMsg != "" {
		t.Errorf("statusMsg = %q, want empty", v.statusMsg)
	}
}

func TestDebugInputPhaseAcceptsQueryWithQFromChatOnlyByEscape(t *testing.T) {
	v := NewDebugView(testContext())
	v.SetSize(harnessWidth, harnessHeight)
	v = settle(v, v.Init()).(*DebugView)

	// "q" used to quit the input phase, which made it impossible to type a query
	// containing a q. The huh field now owns the character.
	v = typeText(v, "q").(*DebugView)

	if !strings.Contains(v.View(), "q") {
		t.Errorf("the letter q should be typed into the prompt, not treated as quit:\n%s", v.View())
	}

	// Esc still leaves for chat.
	next, _ := v.Update(tea.KeyPressMsg{Code: tea.KeyEscape})
	if _, ok := next.(*DebugView); !ok {
		t.Fatalf("expected the debug view back, got %T", next)
	}
}

// TestChatKeepsItsOwnInput records the deliberate decision not to convert the
// chat input: it is a single line inside a composite header/sidebar/log/footer
// layout, it is read mid-typing by the strategy advisor, and it takes part in a
// Tab focus handshake with the sidebar. A bordered huh card there would add
// three rows to the layout and fight the focus model.
func TestChatKeepsItsOwnInput(t *testing.T) {
	v := NewChatView(testContext())
	v.SetSize(harnessWidth, harnessHeight)

	got := v.input.View()
	if strings.Contains(got, "╭") {
		t.Errorf("chat input should stay a plain one-line field, got a bordered card:\n%s", got)
	}
}
