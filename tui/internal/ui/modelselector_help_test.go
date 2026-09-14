package ui

import (
	"strings"
	"testing"

	"charm.land/lipgloss/v2"
)

func stripANSI(s string) string {
	var b strings.Builder
	inEsc := false
	for _, r := range s {
		if r == 0x1b {
			inEsc = true
			continue
		}
		if inEsc {
			if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') {
				inEsc = false
			}
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

// TestSelectorHintListsEveryBinding pins that the hint is generated from the binding
// list. Before this, the line was a hand-written string, so a key could be added to
// the UI without appearing in the hint - or removed from the UI while still being
// advertised, which is the more dangerous direction.
func TestSelectorHintListsEveryBinding(t *testing.T) {
	got := stripANSI(selectorHint(80))
	for _, want := range []string{"↑/↓", "navigate", "Enter", "select", "Esc", "cancel"} {
		if !strings.Contains(got, want) {
			t.Errorf("hint is missing %q, so it is not driven by the bindings: %q", want, got)
		}
	}
	// Cross-check against the bindings themselves rather than a second literal list,
	// so adding a binding without it appearing here fails.
	//
	// Note key.Binding.Help() returns a key.Help struct in v2; in v1 it returned
	// two strings.
	for _, b := range selectorHelpBindings() {
		h := b.Help()
		if !strings.Contains(got, h.Key) || !strings.Contains(got, h.Desc) {
			t.Errorf("binding %q/%q is not represented in the hint %q", h.Key, h.Desc, got)
		}
	}
}

// TestSelectorHintNeverExceedsItsWidth is the HZ-7 guard. bubbles/help's truncation
// is non-monotonic - it appends an item that does not fit when the ellipsis would not
// fit either - so SetWidth alone is not a guarantee and the result is also bounded
// with MaxWidth. Measured, the visible content is genuinely non-monotonic here (width
// 10 renders just an ellipsis while width 1 renders a key), so this asserts the bound
// rather than any particular amount of content.
func TestSelectorHintNeverExceedsItsWidth(t *testing.T) {
	for _, w := range []int{0, 1, 4, 6, 10, 20, 30, 40, 80} {
		got := selectorHint(w)
		vis := stripANSI(got)
		limit := w
		if limit < 1 {
			limit = 1
		}
		if n := lipgloss.Width(vis); n > limit {
			t.Errorf("width %d rendered %d cells (%q); help does not bound itself", w, n, vis)
		}
	}
}

// TestSelectorHintElidesRatherThanHardCutting pins that narrow terminals degrade by
// dropping whole bindings and showing an ellipsis. Without the width being set on the
// help model, help never truncates at all and the line is cut mid-word by MaxWidth
// instead, which reads as a rendering fault rather than an intentional elision.
func TestSelectorHintElidesRatherThanHardCutting(t *testing.T) {
	got := stripANSI(selectorHint(30))
	if !strings.HasSuffix(got, "…") {
		t.Errorf("narrow hint should elide with an ellipsis, got %q", got)
	}
	if strings.Contains(got, "cance") {
		t.Errorf("hint was cut mid-word rather than at a binding boundary: %q", got)
	}
}
