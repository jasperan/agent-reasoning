package ui

import (
	"github.com/charmbracelet/lipgloss"
)

// Splash screen styles
var (
	splashTitleStyle = lipgloss.NewStyle().
			Foreground(ColorPrimary).
			Bold(true)

	splashAccentStyle = lipgloss.NewStyle().
				Foreground(ColorSecondary).
				Bold(true)

	splashSubtitleStyle = lipgloss.NewStyle().
				Foreground(ColorMuted).
				Italic(true)

	splashBrainStyle = lipgloss.NewStyle().
				Foreground(ColorPrimary)

	splashHintStyle = lipgloss.NewStyle().
			Foreground(ColorMuted)
)

// RenderSplash generates the ASCII art splash screen centered in the given dimensions.
func RenderSplash(width, height int) string {
	title := splashTitleStyle.Render("AGENT REASONING")
	subtitle := splashSubtitleStyle.Render("From tokens to thoughts")

	// Fallback for very small terminals
	if width < 30 || height < 12 {
		small := lipgloss.JoinVertical(lipgloss.Center, title, subtitle)
		return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, small)
	}

	art := buildSplashArt()
	hint := splashHintStyle.Render("Tab focus  |  Enter send  |  q quit")

	content := lipgloss.JoinVertical(lipgloss.Center,
		art,
		"",
		title,
		subtitle,
		"",
		hint,
	)

	return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, content)
}

func buildSplashArt() string {
	c := func(t string) string { return splashBrainStyle.Render(t) }
	a := func(t string) string { return splashAccentStyle.Render(t) }

	lines := []string{
		c("            .---.            "),
		c("        .--'     `--.       "),
		c("      .'    ") + a("_   _") + c("    `.     "),
		c("     /     ") + a("| ) | )") + c("     \\    "),
		c("    |      ") + a("|/  |/") + c("      |   "),
		c("    |     ") + a(".--------.") + c("   |   "),
		c("    |    ") + a("( thinking )") + c("   |   "),
		c("    |     ") + a("`--------'") + c("   |   "),
		c("     \\                /    "),
		c("      `._          _.'     "),
		c("         `--.__--'         "),
	}

	return lipgloss.JoinVertical(lipgloss.Left, lines...)
}
