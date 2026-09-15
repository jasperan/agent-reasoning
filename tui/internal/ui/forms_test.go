package ui

import (
	"strings"
	"testing"
	"time"

	"agent-reasoning-tui/internal/huhstyle"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
)

// runBounded runs one command with a deadline. huh batches every field
// transition together with a text-cursor blink tick that sleeps for roughly
// half a second, and a validation test must not depend on the clock, so a slow
// command is abandoned rather than awaited. The goroutine finishes on its own.
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

// settle does what the bubbletea runtime would: run the command the form
// returned, feed the resulting message back in, and repeat until the form stops
// asking for work. Without this a submitted field only emits its transition
// message and the form never reaches StateCompleted.
func settle(q *QueryForm, cmd tea.Cmd) {
	if cmd == nil {
		return
	}
	msg, ok := runBounded(cmd, 50*time.Millisecond)
	if !ok {
		return
	}
	if batch, isBatch := msg.(tea.BatchMsg); isBatch {
		for _, sub := range batch {
			settle(q, sub)
		}
		return
	}
	settle(q, q.Update(msg))
}

// send delivers one key press and then settles the form.
func send(q *QueryForm, msg tea.KeyPressMsg) {
	settle(q, q.Update(msg))
}

// typeRunes types a query without settling. The text field applies each
// keystroke synchronously, so only the submit needs its command drained; this
// keeps the test off the blink clock.
func typeRunes(q *QueryForm, s string) {
	for _, r := range s {
		q.Update(tea.KeyPressMsg{Code: r, Text: string(r)})
	}
}

func newActiveQueryForm() *QueryForm {
	q := NewQueryForm("Query", "test prompt", "placeholder")
	q.Activate()
	return q
}

func enter() tea.KeyPressMsg { return tea.KeyPressMsg{Code: tea.KeyEnter} }

func TestQueryFormRejectsBlankQuery(t *testing.T) {
	q := newActiveQueryForm()

	send(q, enter())

	if q.Done() {
		t.Fatal("a blank query must not complete the form")
	}
	if q.Aborted() {
		t.Fatal("a blank query must not abort the form")
	}
}

func TestQueryFormRejectsWhitespaceOnlyQuery(t *testing.T) {
	q := newActiveQueryForm()

	typeRunes(q, "   ")
	send(q, enter())

	if q.Done() {
		t.Fatalf("a whitespace-only query must not complete the form, value=%q", q.Value())
	}
}

func TestQueryFormCompletesWithTypedQuery(t *testing.T) {
	q := newActiveQueryForm()

	typeRunes(q, "why is the sky blue")
	send(q, enter())

	if !q.Done() {
		t.Fatalf("expected the typed query to complete the form, value=%q", q.Value())
	}
	if got, want := q.Value(), "why is the sky blue"; got != want {
		t.Errorf("Value() = %q, want %q", got, want)
	}
}

func TestQueryFormAbortsOnCtrlC(t *testing.T) {
	q := newActiveQueryForm()

	send(q, tea.KeyPressMsg{Code: 'c', Mod: tea.ModCtrl})

	if !q.Aborted() {
		t.Fatal("ctrl+c must abort the prompt so the view can forward the quit")
	}
	if q.Done() {
		t.Fatal("an aborted prompt must not also read as completed")
	}
}

// TestQueryFormResetReopensThePrompt guards the re-run path: the views call
// Reset and re-activate when the user repeats an operation, and a form left in
// StateCompleted renders an empty view because huh marks it as quitting.
func TestQueryFormResetReopensThePrompt(t *testing.T) {
	q := newActiveQueryForm()
	typeRunes(q, "first query")
	send(q, enter())
	if !q.Done() {
		t.Fatal("precondition: the first query should complete the form")
	}

	q.Reset()
	q.Activate()

	if q.Done() || q.Aborted() {
		t.Fatalf("after Reset the prompt must be active again, got done=%v aborted=%v", q.Done(), q.Aborted())
	}
	if q.Value() != "" {
		t.Errorf("after Reset Value() = %q, want empty", q.Value())
	}
	if !strings.Contains(q.View(), "Query") {
		t.Error("after Reset the prompt should render its title again")
	}

	typeRunes(q, "second")
	send(q, enter())
	if got, want := q.Value(), "second"; !q.Done() || got != want {
		t.Errorf("second submission: done=%v value=%q, want done=true value=%q", q.Done(), got, want)
	}
}

// TestQueryFormSetWidthAppliesFloor asserts the clamp is real rather than
// asserting a magic column count: a width below the floor must render no wider
// than the floor itself, because the views pass narrow pane widths through.
func TestQueryFormSetWidthAppliesFloor(t *testing.T) {
	q := newActiveQueryForm()

	q.SetWidth(5)
	tiny := lipgloss.Width(q.View())
	q.SetWidth(20)
	floor := lipgloss.Width(q.View())

	if tiny > floor {
		t.Errorf("width below the floor rendered %d columns, wider than the floor's %d", tiny, floor)
	}
}

func TestAccessibleFollowsEnv(t *testing.T) {
	t.Setenv("ACCESSIBLE", "")
	if huhstyle.Accessible() {
		t.Error("Accessible() must be false when ACCESSIBLE is unset")
	}
	t.Setenv("ACCESSIBLE", "1")
	if !huhstyle.Accessible() {
		t.Error("Accessible() must be true when ACCESSIBLE is set")
	}
}

// TestQueryFormCompletesWithAccessibleEnvSet proves the screen-reader flag does
// not break the embedded prompt.
//
// It does not prove huh renders plain prompts for a screen reader: huh only
// consults the flag inside Form.Run (huh form.go, runAccessible), and these
// forms are embedded in a Bubble Tea program rather than run standalone, so the
// flag is inert here. A real screen-reader path would have to come from the
// surrounding application, not from these three views.
func TestQueryFormCompletesWithAccessibleEnvSet(t *testing.T) {
	t.Setenv("ACCESSIBLE", "1")
	q := newActiveQueryForm()

	typeRunes(q, "hello")
	send(q, enter())

	if !q.Done() {
		t.Fatalf("with ACCESSIBLE set the prompt should still complete, value=%q", q.Value())
	}
	if got, want := q.Value(), "hello"; got != want {
		t.Errorf("Value() = %q, want %q", got, want)
	}
}
