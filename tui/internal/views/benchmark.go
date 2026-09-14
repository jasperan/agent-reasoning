package views

import (
	"encoding/json"
	"fmt"
	"image/color"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/ui"

	"charm.land/bubbles/v2/key"
	"charm.land/bubbles/v2/progress"
	"charm.land/bubbles/v2/table"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
)

// BenchmarkTab identifies which tab is active.
type BenchmarkTab int

const (
	TabReasoning BenchmarkTab = iota
	TabAccuracy
	TabSpeed
	TabCompare
)

// SpeedResult maps one row from ollama_results.json.
type SpeedResult struct {
	Model      string  `json:"model"`
	TTFT_MS    float64 `json:"ttft_ms"`
	LatencyMS  float64 `json:"latency_ms"`
	OutputToks int     `json:"output_tokens"`
	TPS        float64 `json:"tps"`
}

// AccuracyEntry maps one row from accuracy_full_*.json.
type AccuracyEntry struct {
	Dataset  string `json:"dataset"`
	Strategy string `json:"strategy"`
	Correct  bool   `json:"correct"`
}

// AccuracyFile is the top-level wrapper of the accuracy JSON files.
type AccuracyFile struct {
	Results []AccuracyEntry `json:"results"`
}

// OCIResult maps one row from oci_results.json / oci_benchmark_results.json.
type OCIResult struct {
	Model       string  `json:"model"`
	DisplayName string  `json:"display_name"`
	TTFT_MS     float64 `json:"ttft_ms"`
	LatencyMS   float64 `json:"latency_ms"`
	OutputToks  int     `json:"output_tokens"`
	TPS         float64 `json:"tps"`
	CostEst     float64 `json:"cost_estimate"`
	Error       *string `json:"error"`
}

// OCIFile is the top-level wrapper of oci_results.json.
type OCIFile struct {
	Results []OCIResult `json:"results"`
}

// BenchmarkView is a 4-tab dashboard reading JSON files directly.
type BenchmarkView struct {
	ctx    *app.Context
	tab    BenchmarkTab
	width  int
	height int
	keys   KeyMap

	speedData    []SpeedResult
	accuracyData []AccuracyEntry
	ociData      []OCIResult

	loadError string
}

func NewBenchmarkView(appCtx *app.Context) *BenchmarkView {
	return &BenchmarkView{
		ctx:  appCtx,
		tab:  TabReasoning,
		keys: defaultKeyMap(),
	}
}

func (v *BenchmarkView) ID() app.ViewID { return app.ViewBenchmark }

func (v *BenchmarkView) Init() tea.Cmd {
	v.loadData()
	return nil
}

func (v *BenchmarkView) SetSize(width, height int) {
	v.width = width
	v.height = height
}

func (v *BenchmarkView) Update(msg tea.Msg) (app.View, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyPressMsg:
		return v.handleKey(msg)
	}
	return v, nil
}

func (v *BenchmarkView) handleKey(msg tea.KeyPressMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Escape):
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }

	case msg.String() == "1":
		v.tab = TabReasoning
	case msg.String() == "2":
		v.tab = TabAccuracy
	case msg.String() == "3":
		v.tab = TabSpeed
	case msg.String() == "4":
		v.tab = TabCompare

	case msg.String() == "h":
		if v.tab > TabReasoning {
			v.tab--
		}
	case msg.String() == "l":
		if v.tab < TabCompare {
			v.tab++
		}

	case msg.String() == "r":
		// future: run benchmarks
	}
	return v, nil
}

func (v *BenchmarkView) View() string {
	header := v.renderHeader()
	tabs := v.renderTabs()
	content := v.renderContent()
	help := lipgloss.NewStyle().Foreground(ui.ColorMuted).Render(
		"  [1-4/h/l] switch tabs  [r] run (coming soon)  [Esc] back",
	)
	return lipgloss.JoinVertical(lipgloss.Left, header, tabs, content, help)
}

func (v *BenchmarkView) renderHeader() string {
	return lipgloss.NewStyle().
		Bold(true).
		Foreground(ui.ColorPrimary).
		Width(v.width).
		Padding(0, 1).
		Render("Benchmark Dashboard")
}

func (v *BenchmarkView) renderTabs() string {
	labels := []string{"Agent Reasoning", "Accuracy", "Inference Speed", "OCI vs Ollama"}
	var parts []string
	for i, label := range labels {
		if BenchmarkTab(i) == v.tab {
			parts = append(parts, lipgloss.NewStyle().
				Bold(true).
				Foreground(ui.ColorBlack).
				Background(ui.ColorPrimary).
				Padding(0, 1).
				Render(label))
		} else {
			parts = append(parts, lipgloss.NewStyle().
				Foreground(ui.ColorMuted).
				Padding(0, 1).
				Render(label))
		}
	}
	return lipgloss.NewStyle().
		BorderStyle(lipgloss.NormalBorder()).
		BorderBottom(true).
		BorderForeground(ui.ColorMuted).
		Width(v.width).
		Render(strings.Join(parts, "  "))
}

func (v *BenchmarkView) renderContent() string {
	availH := v.height - 6
	if availH < 5 {
		availH = 5
	}
	switch v.tab {
	case TabReasoning:
		return v.renderReasoning(availH)
	case TabAccuracy:
		return v.renderAccuracy(availH)
	case TabSpeed:
		return v.renderSpeed(availH)
	case TabCompare:
		return v.renderCompare(availH)
	}
	return ""
}

// --- Tab 1: Agent Reasoning ---

func (v *BenchmarkView) renderReasoning(height int) string {
	if len(v.accuracyData) == 0 {
		return v.noDataMsg("No benchmark results found. Run benchmarks from CLI:\n  python agent_cli.py --benchmark")
	}

	// Build strategy → dataset → (correct, total) map
	type stat struct{ correct, total int }
	type key2 struct{ strategy, dataset string }
	counts := map[key2]stat{}
	datasets := map[string]bool{}
	strategies := map[string]bool{}

	for _, e := range v.accuracyData {
		k := key2{e.Strategy, e.Dataset}
		s := counts[k]
		s.total++
		if e.Correct {
			s.correct++
		}
		counts[k] = s
		datasets[e.Dataset] = true
		strategies[e.Strategy] = true
	}

	sortedDS := sortedKeys(datasets)
	sortedStrats := sortedKeys(strategies)

	colW := 10
	labelW := 18

	bold := lipgloss.NewStyle().Bold(true).Foreground(ui.ColorPrimary)
	muted := lipgloss.NewStyle().Foreground(ui.ColorMuted)

	// Header row
	hdr := fmt.Sprintf("%-*s", labelW, "Strategy")
	for _, ds := range sortedDS {
		ds2 := ds
		if len(ds2) > colW-1 {
			ds2 = ds2[:colW-1]
		}
		hdr += fmt.Sprintf("  %-*s", colW, ds2)
	}
	var rows []string
	rows = append(rows, bold.Render(hdr))
	rows = append(rows, muted.Render(strings.Repeat("─", labelW+len(sortedDS)*(colW+2))))

	for _, strat := range sortedStrats {
		line := fmt.Sprintf("%-*s", labelW, strat)
		for _, ds := range sortedDS {
			s := counts[key2{strat, ds}]
			if s.total == 0 {
				line += fmt.Sprintf("  %-*s", colW, "-")
			} else {
				pct := float64(s.correct) / float64(s.total) * 100
				cell := fmt.Sprintf("%.0f%%(%d/%d)", pct, s.correct, s.total)
				color := ui.ColorError
				if pct >= 70 {
					color = ui.ColorSuccess
				} else if pct >= 40 {
					color = ui.ColorWarning
				}
				cell = lipgloss.NewStyle().Foreground(color).Render(fmt.Sprintf("%-*s", colW, cell))
				line += "  " + cell
			}
		}
		rows = append(rows, line)
	}

	return lipgloss.NewStyle().Padding(1, 2).Render(strings.Join(rows, "\n"))
}

// --- Tab 2: Accuracy ---

// renderBar renders a progress bar using bubbles/progress.
//
// progress.WithColorFunc is used rather than progress.WithColors: WithColors
// interpolates between the supplied colours by fill fraction, which would draw a
// gradient these bars have never had. Every hand-rolled bar here picks ONE colour
// from a threshold, so the colour function ignores its arguments and returns it.
//
// WithoutPercentage is required because every caller already renders its own
// percentage on the same row; progress would otherwise append a second one.
// The fill characters are set explicitly because progress defaults to a half
// block for blending resolution, whereas these bars have always been █/░.
//
// The fraction is clamped at the top. progress does not clamp upward, and it
// reports only total/current, which are already sanitised. It DOES handle a
// negative or NaN fraction (both render as an empty bar), so no guard is needed
// there. It does NOT handle over-full correctly: measured, a fraction of +Inf
// renders an EMPTY bar, which is the wrong direction for a value above 1.
func renderBar(fraction float64, width int, colorFn func() color.Color) string {
	if fraction > 1 {
		fraction = 1
	}
	p := progress.New(
		progress.WithWidth(width),
		progress.WithFillCharacters(progress.DefaultFullCharFullBlock, progress.DefaultEmptyCharBlock),
		progress.WithoutPercentage(),
		progress.WithColorFunc(func(_, _ float64) color.Color { return colorFn() }),
	)
	// The empty track keeps the bar's own colour. progress defaults it to a fixed
	// grey, but the bars this replaces drew the FILLED and EMPTY characters in ONE
	// colour (lipgloss.NewStyle().Foreground(color).Render(full+empty)), so leaving
	// the default would silently change the appearance of every bar in this view.
	// There is no option for this field, so it is set directly.
	p.EmptyColor = colorFn()
	return p.ViewAs(fraction)
}

func (v *BenchmarkView) renderAccuracy(height int) string {
	if len(v.accuracyData) == 0 {
		return v.noDataMsg("No accuracy data found.\n\nExpected: benchmarks/accuracy_full_*.json")
	}

	type stat struct{ correct, total int }
	byStat := map[string]stat{}
	for _, e := range v.accuracyData {
		s := byStat[e.Strategy]
		s.total++
		if e.Correct {
			s.correct++
		}
		byStat[e.Strategy] = s
	}

	strats := sortedKeys(byStat)
	barWidth := v.width - 40
	if barWidth < 10 {
		barWidth = 10
	}

	title := lipgloss.NewStyle().Bold(true).Foreground(ui.ColorPrimary).Render(" Accuracy by Strategy")
	var rows []string
	rows = append(rows, title, "")

	for _, strat := range strats {
		s := byStat[strat]
		pct := 0.0
		if s.total > 0 {
			pct = float64(s.correct) / float64(s.total) * 100
		}
		barColor := ui.ColorError
		if pct >= 70 {
			barColor = ui.ColorSuccess
		} else if pct >= 40 {
			barColor = ui.ColorWarning
		}
		barRendered := renderBar(pct/100, barWidth, func() color.Color { return barColor })
		label := fmt.Sprintf(" %-16s", strat)
		pctStr := fmt.Sprintf("  %.0f%%", pct)
		rows = append(rows, label+barRendered+pctStr)
	}

	return lipgloss.NewStyle().Padding(1, 1).Render(strings.Join(rows, "\n"))
}

// --- Tab 3: Inference Speed ---

func (v *BenchmarkView) renderSpeed(height int) string {
	if len(v.speedData) == 0 {
		return v.noDataMsg("No speed data found.\n\nExpected: benchmarks/ollama_results.json")
	}

	// Aggregate by model: average TPS and latency
	type agg struct {
		tpsSum     float64
		latSum     float64
		ttftSum    float64
		n          int
		tpsSamples []float64
	}
	byModel := map[string]*agg{}
	for _, r := range v.speedData {
		if byModel[r.Model] == nil {
			byModel[r.Model] = &agg{}
		}
		a := byModel[r.Model]
		a.tpsSum += r.TPS
		a.latSum += r.LatencyMS
		a.ttftSum += r.TTFT_MS
		a.n++
		a.tpsSamples = append(a.tpsSamples, r.TPS)
	}

	models := sortedKeys(byModel)

	// Find max TPS for bar scaling
	maxTPS := 1.0
	for _, a := range byModel {
		avg := a.tpsSum / float64(a.n)
		if avg > maxTPS {
			maxTPS = avg
		}
	}

	barWidth := v.width - 50
	if barWidth < 10 {
		barWidth = 10
	}

	title := lipgloss.NewStyle().Bold(true).Foreground(ui.ColorPrimary).Render(" Inference Speed (tokens/sec)")
	hdr := lipgloss.NewStyle().Foreground(ui.ColorMuted).Render(
		fmt.Sprintf(" %-24s  %-*s  %8s  %8s  %8s", "Model", barWidth, "TPS", "Avg TPS", "Lat ms", "TTFT ms"))
	var rows []string
	rows = append(rows, title, "", hdr)

	for _, model := range models {
		a := byModel[model]
		avgTPS := a.tpsSum / float64(a.n)
		avgLat := a.latSum / float64(a.n)
		avgTTFT := a.ttftSum / float64(a.n)

		frac := 0.0
		if maxTPS > 0 {
			frac = avgTPS / maxTPS
		}
		barRendered := renderBar(frac, barWidth, func() color.Color { return ui.ColorPrimary })

		mLabel := model
		if len(mLabel) > 22 {
			mLabel = mLabel[:19] + "..."
		}
		rows = append(rows, fmt.Sprintf(" %-24s  %s  %7.1f  %7.0f  %7.0f",
			mLabel, barRendered, avgTPS, avgLat, avgTTFT))
	}

	return lipgloss.NewStyle().Padding(1, 1).Render(strings.Join(rows, "\n"))
}

// --- Tab 4: OCI vs Ollama ---

func (v *BenchmarkView) renderCompare(height int) string {
	if len(v.ociData) == 0 || len(v.speedData) == 0 {
		if len(v.ociData) == 0 && len(v.speedData) == 0 {
			return v.noDataMsg("No OCI or Ollama data found.\n\nExpected: benchmarks/oci_results.json and benchmarks/ollama_results.json")
		}
		if len(v.ociData) == 0 {
			return v.noDataMsg("No OCI data found.\n\nExpected: benchmarks/oci_results.json or benchmarks/oci_benchmark_results.json")
		}
		return v.noDataMsg("No Ollama data found.\n\nExpected: benchmarks/ollama_results.json")
	}

	// Aggregate Ollama by model
	type modelStat struct {
		tpsSum float64
		latSum float64
		n      int
		source string
	}
	allStats := map[string]*modelStat{}

	for _, r := range v.speedData {
		if allStats[r.Model] == nil {
			allStats[r.Model] = &modelStat{source: "Ollama"}
		}
		allStats[r.Model].tpsSum += r.TPS
		allStats[r.Model].latSum += r.LatencyMS
		allStats[r.Model].n++
	}

	for _, r := range v.ociData {
		if r.Error != nil {
			continue
		}
		name := r.DisplayName
		if name == "" {
			name = r.Model
		}
		if allStats[name] == nil {
			allStats[name] = &modelStat{source: "OCI"}
		}
		allStats[name].tpsSum += r.TPS
		allStats[name].latSum += r.LatencyMS
		allStats[name].n++
		allStats[name].source = "OCI"
	}

	sortedModels := sortedKeys(allStats)

	title := lipgloss.NewStyle().Bold(true).Foreground(ui.ColorPrimary).Render(" OCI vs Ollama Comparison")

	// table never clips its HEADER to the viewport, so the column widths are kept
	// within the same budget as the rows rather than assumed to fit.
	cols := []table.Column{
		{Title: "Model", Width: 28},
		{Title: "Source", Width: 8},
		{Title: "Avg TPS", Width: 10},
		{Title: "Avg Lat ms", Width: 11},
	}
	rows := make([]table.Row, 0, len(sortedModels))
	for _, name := range sortedModels {
		s := allStats[name]
		avgTPS := s.tpsSum / float64(s.n)
		avgLat := s.latSum / float64(s.n)

		srcColor := ui.ColorPrimary
		if s.source == "OCI" {
			srcColor = ui.ColorSecondary
		}
		tpsColor := ui.ColorSuccess
		if avgTPS < 30 {
			tpsColor = ui.ColorWarning
		}
		latColor := ui.ColorSuccess
		if avgLat > 5000 {
			latColor = ui.ColorWarning
		}

		mName := name
		if len(mName) > 26 {
			mName = mName[:23] + "..."
		}
		// Colour is applied to the cell VALUE. table exposes no per-cell style
		// hook, but renderRow renders the value it is handed and ansi.Truncate
		// preserves SGR, so a styled value keeps its colour and still truncates
		// with an ellipsis instead of dropping the escape.
		rows = append(rows, table.Row{
			mName,
			lipgloss.NewStyle().Foreground(srcColor).Render(s.source),
			lipgloss.NewStyle().Foreground(tpsColor).Render(fmt.Sprintf("%.1f", avgTPS)),
			lipgloss.NewStyle().Foreground(latColor).Render(fmt.Sprintf("%.0f", avgLat)),
		})
	}

	// The width must be set BEFORE the first View: the table's internal viewport
	// returns "" when its width is 0, so an unsized table silently renders a header
	// and zero rows. WithWidth covers construction; SetWidth covers later resizes.
	tw := v.width - 2 // the frame below pads one cell on each side
	if tw < 20 {
		tw = 20
	}
	tbl := table.New(
		table.WithColumns(cols),
		table.WithRows(rows),
		table.WithWidth(tw),
		table.WithStyles(table.DefaultStyles()),
	)
	// SetHeight already includes the header (View is header + viewport), so the
	// budget is what is left after the title and its blank line. Without this the
	// table rendered every row regardless of the space available.
	if h := height - 2; h > 3 {
		tbl.SetHeight(h)
	}
	return lipgloss.NewStyle().Padding(1, 1).Render(title + "\n\n" + tbl.View())
}

// --- Data loading ---

func (v *BenchmarkView) loadData() {
	dir := filepath.Join(v.ctx.ProjectDir, "benchmarks")

	// Speed data
	speedPath := filepath.Join(dir, "ollama_results.json")
	if data, err := os.ReadFile(speedPath); err == nil {
		var results []SpeedResult
		if json.Unmarshal(data, &results) == nil {
			v.speedData = results
		}
	}

	// Accuracy data — glob for latest
	pattern := filepath.Join(dir, "accuracy_full_*.json")
	if matches, err := filepath.Glob(pattern); err == nil && len(matches) > 0 {
		sort.Strings(matches)
		latest := matches[len(matches)-1]
		if data, err := os.ReadFile(latest); err == nil {
			// Try wrapped format first
			var wrapped AccuracyFile
			if json.Unmarshal(data, &wrapped) == nil && len(wrapped.Results) > 0 {
				v.accuracyData = wrapped.Results
			} else {
				// Try flat array
				var flat []AccuracyEntry
				if json.Unmarshal(data, &flat) == nil {
					v.accuracyData = flat
				}
			}
		}
	}

	// OCI data — try both filenames
	for _, name := range []string{"oci_results.json", "oci_benchmark_results.json"} {
		path := filepath.Join(dir, name)
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		// Try wrapped format
		var wrapped OCIFile
		if json.Unmarshal(data, &wrapped) == nil && len(wrapped.Results) > 0 {
			v.ociData = wrapped.Results
			break
		}
		// Try flat array
		var flat []OCIResult
		if json.Unmarshal(data, &flat) == nil && len(flat) > 0 {
			v.ociData = flat
			break
		}
	}
}

func (v *BenchmarkView) noDataMsg(msg string) string {
	return lipgloss.NewStyle().
		Foreground(ui.ColorMuted).
		Padding(2, 3).
		Render(msg)
}

// sortedKeys returns sorted keys from any map with string keys.
func sortedKeys[V any](m map[string]V) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}
