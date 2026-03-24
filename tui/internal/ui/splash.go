package ui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Splash screen styles
var (
	splashStaffStyle = lipgloss.NewStyle().
				Foreground(ColorPrimary).
				Bold(true)

	splashSnakeMagenta = lipgloss.NewStyle().
				Foreground(ColorSecondary)

	splashSnakeGreen = lipgloss.NewStyle().
				Foreground(ColorSuccess)

	splashWingStyle = lipgloss.NewStyle().
			Foreground(ColorWarning)

	splashOrnamentStyle = lipgloss.NewStyle().
				Foreground(ColorWhite).
				Bold(true)

	splashCrossStyle = lipgloss.NewStyle().
				Foreground(ColorMuted)

	splashBaseStyle = lipgloss.NewStyle().
			Foreground(ColorPrimary)

	splashTitleStyle = lipgloss.NewStyle().
				Foreground(ColorPrimary).
				Bold(true)

	splashSubtitleStyle = lipgloss.NewStyle().
				Foreground(ColorMuted).
				Italic(true)
)

// RenderSplash generates the caduceus splash screen centered in the given dimensions.
func RenderSplash(width, height int) string {
	title := splashTitleStyle.Render("A G E N T   R E A S O N I N G")
	subtitle := splashSubtitleStyle.Render("From tokens to thoughts")

	// Fallback for very small terminals
	if width < 25 || height < 10 {
		small := lipgloss.JoinVertical(lipgloss.Center, title, subtitle)
		return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, small)
	}

	art := buildCaduceus()

	content := lipgloss.JoinVertical(lipgloss.Center,
		art,
		"",
		title,
		subtitle,
	)

	return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, content)
}

// buildCaduceus constructs the color-coded caduceus ASCII art.
//
// Layout: staff at visual column 9, art ~19 chars wide.
// Colors: staff=cyan, left-snake=magenta, right-snake=green,
// wings=yellow, ornament=white, crossings=gray, base=cyan.
//
// The snakes swap sides at each crossing, creating the classic
// caduceus double-helix pattern.
func buildCaduceus() string {
	// Style shortcuts
	st := func(t string) string { return splashStaffStyle.Render(t) }
	m := func(t string) string { return splashSnakeMagenta.Render(t) }
	g := func(t string) string { return splashSnakeGreen.Render(t) }
	w := func(t string) string { return splashWingStyle.Render(t) }
	o := func(t string) string { return splashOrnamentStyle.Render(t) }
	x := func(t string) string { return splashCrossStyle.Render(t) }
	b := func(t string) string { return splashBaseStyle.Render(t) }
	p := func(n int) string { return strings.Repeat(" ", n) }

	lines := []string{
		// ──── Ornament ────
		p(9) + o("◆"),

		// ──── Wings ────
		p(6) + w("╱") + p(5) + w("╲"),
		p(2) + w("━━╱") + p(4) + st("│") + p(4) + w("╲━━"),
		p(1) + w("╱") + p(3) + w("╲") + p(3) + st("│") + p(3) + w("╱") + p(3) + w("╲"),
		w("╱") + p(5) + w("╲") + p(2) + st("│") + p(2) + w("╱") + p(5) + w("╲"),

		// ──── Staff gap ────
		p(9) + st("│"),

		// ──── Coil 1 descent (magenta left, green right) ────
		p(2) + m("╲") + p(6) + st("│") + p(6) + g("╱"),
		p(3) + m("╲") + p(5) + st("│") + p(5) + g("╱"),

		// ──── Cross 1 ────
		p(4) + m("╲") + x("────") + st("┼") + x("────") + g("╱"),
		p(4) + g("╱") + x("────") + st("┼") + x("────") + m("╲"),

		// ──── Coil 1 ascent (green left, magenta right) ────
		p(3) + g("╱") + p(5) + st("│") + p(5) + m("╲"),
		p(2) + g("╱") + p(6) + st("│") + p(6) + m("╲"),

		// ──── Coil 2 descent (green left, magenta right) ────
		p(2) + g("╲") + p(6) + st("│") + p(6) + m("╱"),
		p(3) + g("╲") + p(5) + st("│") + p(5) + m("╱"),

		// ──── Cross 2 ────
		p(4) + g("╲") + x("────") + st("┼") + x("────") + m("╱"),
		p(4) + m("╱") + x("────") + st("┼") + x("────") + g("╲"),

		// ──── Coil 2 ascent (magenta left, green right) ────
		p(3) + m("╱") + p(5) + st("│") + p(5) + g("╲"),
		p(2) + m("╱") + p(6) + st("│") + p(6) + g("╲"),

		// ──── Staff gap ────
		p(9) + st("│"),

		// ──── Base ────
		p(6) + b("═══") + st("╪") + b("═══"),
		p(9) + st("│"),
	}

	return lipgloss.JoinVertical(lipgloss.Left, lines...)
}
