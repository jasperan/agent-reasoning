package views

import (
	"strings"
	"testing"

	"agent-reasoning-tui/internal/ui"
	"charm.land/lipgloss/v2"
)

// compareView builds a BenchmarkView with real rows for the comparison tab.
func compareView(width, height int) *BenchmarkView {
	v := &BenchmarkView{
		tab:    TabCompare,
		width:  width,
		height: height,
		keys:   defaultKeyMap(),
		speedData: []SpeedResult{
			{Model: "llama3.1:8b", TPS: 41.5, LatencyMS: 900},
			{Model: "qwen2.5:14b", TPS: 22.0, LatencyMS: 6100},
			{Model: "mistral:7b", TPS: 55.0, LatencyMS: 700},
		},
		ociData: []OCIResult{
			{Model: "meta.llama-3.1-70b", DisplayName: "llama-3.1-70b-instruct", TPS: 78.0, LatencyMS: 15000},
		},
	}
	return v
}

// TestRenderCompareShowsEveryRow is the HZ-1 guard. A bubbles table whose width is
// never set renders a header and ZERO rows with no error and no panic, so a test
// that only asserts "the header is present" would pass on a completely empty table.
// This asserts the row CONTENT the input implies.
func TestRenderCompareShowsEveryRow(t *testing.T) {
	v := compareView(120, 40)
	got := visible(v.renderCompare(30))

	wantModels := []string{"llama-3.1-70b-instruct", "llama3.1:8b", "mistral:7b", "qwen2.5:14b"}
	for _, m := range wantModels {
		if !strings.Contains(got, m) {
			t.Errorf("table is missing row %q; a table with no width renders no rows at all:\n%s", m, got)
		}
	}
	// Sources are derived per row, so both must appear.
	for _, src := range []string{"OCI", "Ollama"} {
		if !strings.Contains(got, src) {
			t.Errorf("table is missing source %q:\n%s", src, got)
		}
	}
	// The header must be present too, or the assertions above could be satisfied by
	// a hand-rolled list rather than a table.
	if !strings.Contains(got, "Avg TPS") || !strings.Contains(got, "Avg Lat ms") {
		t.Errorf("table header is missing:\n%s", got)
	}
}

// TestRenderCompareColumnArityFits guards HZ-3: the library indexes cols by the row
// index with no bound check, so a row longer than the column set PANICS rather than
// erroring. Every row must therefore have exactly len(cols) cells at every width,
// because this view rebuilds its rows per render.
func TestRenderCompareColumnArityFits(t *testing.T) {
	for _, w := range []int{150, 120, 100, 96, 80, 60, 40, 20, 0} {
		v := compareView(w, 40)
		func() {
			defer func() {
				if r := recover(); r != nil {
					t.Errorf("width %d panicked: %v", w, r)
				}
			}()
			_ = v.renderCompare(30)
		}()
	}
}

// TestRenderCompareRespectsHeight pins that the table is bounded by the space it is
// given. Before this conversion renderCompare ignored its height argument entirely
// and rendered every row, so it could overflow the frame.
func TestRenderCompareRespectsHeight(t *testing.T) {
	// Both series are required: renderCompare short-circuits to its no-data message
	// when either is empty, which would make this test measure the wrong string.
	many := &BenchmarkView{tab: TabCompare, width: 120, height: 40, keys: defaultKeyMap()}
	many.ociData = []OCIResult{{Model: "oci-model", DisplayName: "oci-model", TPS: 50, LatencyMS: 1000}}
	for i := 0; i < 40; i++ {
		many.speedData = append(many.speedData, SpeedResult{
			Model: strings.Repeat("m", 3) + string(rune('a'+i%26)) + string(rune('0'+i/26)),
			TPS:   10 + float64(i), LatencyMS: float64(500 + i*100),
		})
	}
	short := lipgloss.Height(many.renderCompare(6))
	tall := lipgloss.Height(many.renderCompare(30))
	if short >= tall {
		t.Errorf("a 6-row budget (%d lines) should render fewer lines than a 30-row budget (%d)", short, tall)
	}
	if tall < 10 {
		t.Errorf("a 30-row budget rendered only %d lines; the rows are not being shown", tall)
	}
}

// TestRenderCompareKeepsPerCellColour pins the colouring, which is the part of this
// conversion that is easy to lose: table has no per-cell style hook, so colour is
// carried inside the cell VALUE. If that stops working the table renders correctly
// in one colour, which the text assertions above cannot see.
func TestRenderCompareKeepsPerCellColour(t *testing.T) {
	// Shape the data so the two thresholds fire in opposite directions: slow models
	// below 30 TPS must be warning-coloured while fast ones are success-coloured.
	v := &BenchmarkView{
		tab: TabCompare, width: 120, height: 40, keys: defaultKeyMap(),
		speedData: []SpeedResult{
			{Model: "fast-model", TPS: 90, LatencyMS: 100},
			{Model: "slow-model", TPS: 5, LatencyMS: 9000},
		},
		// Required: renderCompare short-circuits to its no-data message when either
		// series is empty, so without this the test would measure that message
		// instead of a table and report a colour failure that is not real.
		ociData: []OCIResult{{Model: "oci-fast", DisplayName: "oci-fast", TPS: 90, LatencyMS: 200}},
	}
	got := v.renderCompare(30)
	warn := sgrFor(ui.ColorWarning)
	good := sgrFor(ui.ColorSuccess)
	if !strings.Contains(got, warn) {
		t.Errorf("no cell uses the warning colour; thresholds are not reaching the cells")
	}
	if !strings.Contains(got, good) {
		t.Errorf("no cell uses the success colour; thresholds are not reaching the cells")
	}
	if warn == good {
		t.Fatal("the two threshold colours are identical, so this test cannot judge")
	}
}
