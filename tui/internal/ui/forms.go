package ui

import (
	"errors"
	"strings"

	"agent-reasoning-tui/internal/huhstyle"

	tea "charm.land/bubbletea/v2"
	"charm.land/huh/v2"
)

// QueryForm is the single-field prompt shared by the views that begin an
// operation from a free-text query (arena, duel, debugger).
//
// huh owns the text field while the form is active, so a view must forward key
// messages to Update and may only read Value once Done or Aborted reports that
// the form has stopped.
type QueryForm struct {
	form   *huh.Form
	value  string
	width  int
	title  string
	desc   string
	holder string
}

// NewQueryForm builds a query prompt. It must be Activated before it accepts
// input.
func NewQueryForm(title, description, placeholder string) *QueryForm {
	q := &QueryForm{
		width:  80,
		title:  title,
		desc:   description,
		holder: placeholder,
	}
	q.Reset()
	return q
}

// Reset discards the previous answer, focus and validation error, leaving a
// prompt ready to be shown again. The views re-enter their input phase to start
// a fresh operation, so the form must not carry the old query forward.
func (q *QueryForm) Reset() {
	q.value = ""
	q.form = q.build()
}

func (q *QueryForm) build() *huh.Form {
	return huh.NewForm(
		huh.NewGroup(
			huh.NewInput().
				Key("query").
				Title(q.title).
				Description(q.desc).
				Placeholder(q.holder).
				Value(&q.value).
				Validate(validateQuery),
		),
	).
		WithTheme(huh.ThemeFunc(huhstyle.Theme)).
		// Accessible mode is inert for an embedded form: huh only consults the
		// flag in Form.Run (huh form.go, runAccessible), never in Update. It is
		// wired anyway so the intent survives, and the token palette is the only
		// contrast guarantee this TUI actually gets.
		WithAccessible(huhstyle.Accessible()).
		WithWidth(q.width)
}

// validateQuery rejects a blank query so the form reports the problem inline
// instead of swallowing the submit key the way a bare Enter used to be dropped.
func validateQuery(s string) error {
	if strings.TrimSpace(s) == "" {
		return errors.New("enter a query")
	}
	return nil
}

// Activate prepares the prompt to receive keys. Call it once each time the
// owning view enters its input phase.
func (q *QueryForm) Activate() tea.Cmd { return q.form.Init() }

// SetWidth resizes the prompt without discarding what has been typed.
func (q *QueryForm) SetWidth(width int) {
	if width < 20 {
		width = 20
	}
	q.width = width
	q.form.WithWidth(width)
}

// Update forwards a message to the form and returns its command.
func (q *QueryForm) Update(msg tea.Msg) tea.Cmd {
	model, cmd := q.form.Update(msg)
	if form, ok := model.(*huh.Form); ok {
		q.form = form
	}
	return cmd
}

// Done reports whether the user submitted an answer.
func (q *QueryForm) Done() bool { return q.form.State == huh.StateCompleted }

// Aborted reports whether the user dismissed the prompt (ctrl+c).
func (q *QueryForm) Aborted() bool { return q.form.State == huh.StateAborted }

// Value returns the submitted query with surrounding space removed.
func (q *QueryForm) Value() string { return strings.TrimSpace(q.value) }

// View renders the prompt.
func (q *QueryForm) View() string { return q.form.View() }
