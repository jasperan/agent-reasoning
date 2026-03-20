package viz

import (
	"strings"

	"agent-reasoning-tui/internal/client"

	"github.com/charmbracelet/lipgloss"
)

var (
	analogyHeaderStyle  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#FFFF00"))
	analogyContentStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#CCCCCC"))
	analogySepStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("#444444"))
)

type analogyData struct {
	sourceDomain string
	mapping      string
	application  string
}

// AnalogyViz renders analogical reasoning events in 3 sequential panels.
type AnalogyViz struct {
	data          analogyData
	phase         string
	width, height int
}

func NewAnalogyViz(width, height int) Visualizer {
	return &AnalogyViz{width: width, height: height}
}

func (v *AnalogyViz) Reset() {
	v.data = analogyData{}
	v.phase = ""
}

func (v *AnalogyViz) SetSize(width, height int) {
	v.width = width
	v.height = height
}

func (v *AnalogyViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "analogy":
		phase := getString(event.Data, "phase")
		v.phase = phase

		src := getString(event.Data, "source_domain")
		if src != "" {
			v.data.sourceDomain = src
		}
		mapping := getString(event.Data, "mapping")
		if mapping != "" {
			v.data.mapping = mapping
		}
		application := getString(event.Data, "application")
		if application != "" {
			v.data.application = application
		}

	case "final":
		content := getString(event.Data, "content")
		if content != "" {
			v.data.application = content
		}
	}
}

func (v *AnalogyViz) View() string {
	if v.data.sourceDomain == "" && v.data.mapping == "" && v.data.application == "" {
		return analogySepStyle.Render("Waiting for analogy events...")
	}

	innerWidth := v.width - 4
	if innerWidth < 10 {
		innerWidth = 10
	}

	var lines []string

	panels := []struct {
		label   string
		content string
		active  bool
	}{
		{"Source Domain", v.data.sourceDomain, v.data.sourceDomain != ""},
		{"Mapping", v.data.mapping, v.data.mapping != ""},
		{"Application", v.data.application, v.data.application != ""},
	}

	for _, p := range panels {
		header := analogyHeaderStyle.Render("▸ " + p.label)
		lines = append(lines, header)
		lines = append(lines, analogySepStyle.Render(strings.Repeat("─", innerWidth)))
		if p.active {
			lines = append(lines, analogyContentStyle.Render(wrapText(p.content, innerWidth)))
		} else {
			lines = append(lines, analogySepStyle.Render("(pending...)"))
		}
		lines = append(lines, "")
	}

	return strings.Join(lines, "\n")
}
