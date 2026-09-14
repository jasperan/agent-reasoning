package views

import (
	"image/color"
	"math"
	"regexp"
	"strings"
	"testing"

	"agent-reasoning-tui/internal/ui"
	"charm.land/lipgloss/v2"
)

var ansiSGR = regexp.MustCompile("\x1b\\[[0-9;]*m")

func visible(s string) string { return ansiSGR.ReplaceAllString(s, "") }

// sgrBefore returns the SGR sequence immediately preceding the first occurrence of
// glyph in s. Asserting on this rather than on the whole string matters: progress
// emits a trailing escape for the empty track even when there are no empty cells, so
// a caller's colour can appear in the output while the FILLED cells are still the
// library default. A whole-string check cannot tell those apart; this one can.
func sgrBefore(s, glyph string) string {
	i := strings.Index(s, glyph)
	if i < 0 {
		return ""
	}
	prefix := s[:i]
	j := strings.LastIndex(prefix, "\x1b[")
	if j < 0 {
		return ""
	}
	return prefix[j:]
}

// sgrFor is the escape lipgloss emits for c, so expectations are derived from the
// colour value rather than hardcoded.
func sgrFor(c color.Color) string {
	r := lipgloss.NewStyle().Foreground(c).Render("X")
	return sgrBefore(r, "X")
}

// oldBar is the pre-migration implementation, kept here verbatim so the adoption
// of bubbles/progress can be checked against what it replaced rather than against
// a description of it.
func oldBar(pct float64, barWidth int, c color.Color) string {
	filled := int(math.Round(pct / 100 * float64(barWidth)))
	if filled > barWidth {
		filled = barWidth
	}
	bar := strings.Repeat("█", filled) + strings.Repeat("░", barWidth-filled)
	return lipgloss.NewStyle().Foreground(c).Render(bar)
}

// TestRenderBarMatchesHandRolledAppearance pins that adopting bubbles/progress did
// not change what the user sees. It compares the VISIBLE text, not the raw bytes:
// progress emits one SGR per filled cell where the hand-rolled bar emitted one for
// the whole run, so the raw strings differ while the rendered bar is identical.
// Comparing raw bytes here would fail for a reason that is not a defect; comparing
// stripped bytes is the assertion that actually describes the requirement.
func TestRenderBarMatchesHandRolledAppearance(t *testing.T) {
	colors := map[string]color.Color{
		"error": ui.ColorError, "success": ui.ColorSuccess,
		"warning": ui.ColorWarning, "primary": ui.ColorPrimary,
	}
	checked := 0
	for name, c := range colors {
		for total := 1; total <= 12; total++ {
			for correct := 0; correct <= total; correct++ {
				pct := float64(correct) / float64(total) * 100
				for _, w := range []int{10, 20, 37} {
					want := visible(oldBar(pct, w, c))
					got := visible(renderBar(pct/100, w, func() color.Color { return c }))
					checked++
					if got != want {
						t.Errorf("%s correct=%d/%d width=%d\n got %q\nwant %q", name, correct, total, w, got, want)
					}
					// The bar must also occupy exactly the requested width, so the
					// label/percentage columns around it do not shift.
					if lipgloss.Width(got) != w {
						t.Errorf("%s width=%d rendered %d cells", name, w, lipgloss.Width(got))
					}
				}
			}
		}
	}
	if checked == 0 {
		t.Fatal("no combinations were checked; the test would pass vacuously")
	}
	t.Logf("compared %d renderings against the hand-rolled implementation", checked)
}

// TestRenderBarAppliesTheGivenColour guards the point of the adoption: the colour of
// the FILLED cells must come from the caller.
//
// The assertion targets the escape immediately before the first filled glyph, not the
// output as a whole. That detail is load-bearing twice over: at a partial fraction the
// empty track also carries the caller's colour, and progress emits a trailing escape
// for the empty track even at a full fraction - so a whole-string check sees the
// caller's colour even when WithColorFunc has been removed and the filled cells are
// the library default. Verified by removing WithColorFunc: this test fails.
func TestRenderBarAppliesTheGivenColour(t *testing.T) {
	cases := map[string]color.Color{
		"error": ui.ColorError, "warning": ui.ColorWarning, "success": ui.ColorSuccess,
	}
	seen := map[string]string{}
	for name, c := range cases {
		got := renderBar(1.0, 20, func() color.Color { return c })

		want := sgrFor(c)
		if want == "" {
			t.Fatalf("%s: could not derive an SGR for the colour; the test cannot judge", name)
		}
		if fill := sgrBefore(got, "█"); fill != want {
			t.Errorf("%s: filled cells are %q, want %q (the caller's colour, not the library default)",
				name, fill, want)
		}
		if strings.Contains(visible(got), "%") {
			t.Errorf("%s: bar renders its own percentage; callers already print one: %q", name, got)
		}
		seen[name] = got
	}
	if seen["error"] == seen["success"] || seen["warning"] == seen["success"] || seen["error"] == seen["warning"] {
		t.Error("threshold colours are not distinct, so the bar cannot communicate a threshold")
	}
}

// TestRenderBarKeepsOneColourAcrossTheTrack pins the deliberate choice to keep the
// empty track in the bar's own colour. The bars this replaces drew the filled AND
// empty characters with a single Foreground, so leaving progress's default grey track
// would change the appearance of every bar in this view - an unintended visual delta
// in a migration. The stripped-text comparison cannot see this (the glyphs are the
// same), which is exactly why it is asserted separately.
// Verified by removing the EmptyColor assignment: this test fails.
func TestRenderBarKeepsOneColourAcrossTheTrack(t *testing.T) {
	for name, c := range map[string]color.Color{
		"error": ui.ColorError, "primary": ui.ColorPrimary,
	} {
		got := renderBar(0.5, 20, func() color.Color { return c })
		want := sgrFor(c)
		for _, glyph := range []string{"█", "░"} {
			if s := sgrBefore(got, glyph); s != want {
				t.Errorf("%s: %q cells are %q, want %q (the pre-migration bar used one colour for both)",
					name, glyph, s, want)
			}
		}
	}
}

// TestRenderBarFillsWhenOverFull pins the one out-of-range case progress does not
// handle. progress renders NaN and negative fractions as an EMPTY bar, which is
// acceptable, but it renders an over-full value the same way - measured, +Inf gives
// 10 of 10 cells unfilled. That is the wrong direction, so renderBar clamps. +Inf is
// the discriminating input: removing the clamp leaves this test passing for 1.5 but
// failing here. Verified by removing the clamp.
func TestRenderBarFillsWhenOverFull(t *testing.T) {
	for _, frac := range []float64{1, 1.5, 2, math.Inf(1)} {
		got := visible(renderBar(frac, 10, func() color.Color { return ui.ColorPrimary }))
		if n := strings.Count(got, "█"); n != 10 {
			t.Errorf("fraction %v should be fully filled, got %d/10 filled: %q", frac, n, got)
		}
		if w := lipgloss.Width(got); w != 10 {
			t.Errorf("fraction %v rendered %d cells, want 10", frac, w)
		}
	}

	// Degenerate inputs must not panic and must keep the width. Their appearance is
	// progress's choice; this only pins that the bar stays a bar.
	for _, frac := range []float64{-1, -0.001, math.NaN(), math.Inf(-1), 0} {
		got := visible(renderBar(frac, 10, func() color.Color { return ui.ColorPrimary }))
		if w := lipgloss.Width(got); w != 10 {
			t.Errorf("fraction %v rendered %d cells, want 10", frac, w)
		}
		if strings.Count(got, "█") != 0 {
			t.Errorf("fraction %v should have no filled cells, got %q", frac, got)
		}
	}
}
