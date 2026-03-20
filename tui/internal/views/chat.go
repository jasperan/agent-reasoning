package views

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/ansi"
)

// Focus represents which component has focus within ChatView.
type Focus int

const (
	FocusSidebar Focus = iota
	FocusInput
)

// Internal message types for streaming.
type (
	streamChunkMsg struct {
		agentID string
		content string
	}
	streamDoneMsg struct {
		agentID  string
		duration float64
	}
	streamErrorMsg struct {
		agentID string
		err     error
	}
	arenaCompleteMsg     struct{}
	benchmarkCompleteMsg struct{ err error }
)

// KeyMap defines the keybindings for ChatView.
type KeyMap struct {
	Up     key.Binding
	Down   key.Binding
	Enter  key.Binding
	Tab    key.Binding
	Escape key.Binding
	Quit   key.Binding
}

func defaultKeyMap() KeyMap {
	return KeyMap{
		Up: key.NewBinding(
			key.WithKeys("up", "k"),
			key.WithHelp("↑/k", "up"),
		),
		Down: key.NewBinding(
			key.WithKeys("down", "j"),
			key.WithHelp("↓/j", "down"),
		),
		Enter: key.NewBinding(
			key.WithKeys("enter"),
			key.WithHelp("enter", "select/submit"),
		),
		Tab: key.NewBinding(
			key.WithKeys("tab"),
			key.WithHelp("tab", "switch focus"),
		),
		Escape: key.NewBinding(
			key.WithKeys("esc"),
			key.WithHelp("esc", "cancel"),
		),
		Quit: key.NewBinding(
			key.WithKeys("ctrl+c", "q"),
			key.WithHelp("q/ctrl+c", "quit"),
		),
	}
}

// ChatView handles the main chat interface: sidebar, input, streaming, arena, model selector.
type ChatView struct {
	ctx *app.Context

	// UI components
	header        *ui.Header
	sidebar       *ui.Sidebar
	chat          *ui.Chat
	input         *ui.Input
	arena         *ui.Arena
	modelSelector *ui.ModelSelector

	// State
	focus        Focus
	currentAgent string
	width        int
	height       int

	// Streaming control
	streamCancel   context.CancelFunc
	streamRespChan <-chan client.GenerateResponse
	streamErrChan  <-chan error
	streamStart    time.Time

	// Keys
	keys KeyMap
}

// NewChatView creates a ChatView wired to the shared Context.
func NewChatView(appCtx *app.Context) *ChatView {
	header := ui.NewHeader()
	header.SetModel(appCtx.CurrentModel)
	header.SetConnected(appCtx.Connected)

	// Build sidebar from server-fetched agents when available, else use defaults.
	var sidebar *ui.Sidebar
	if len(appCtx.Agents) > 0 {
		items := make([]ui.AgentItem, len(appCtx.Agents))
		for i, a := range appCtx.Agents {
			items[i] = ui.AgentItem{ID: a.ID, Name: a.Name}
		}
		sidebar = ui.NewSidebarFromAgents(items)
	} else {
		sidebar = ui.NewSidebar()
	}

	return &ChatView{
		ctx:           appCtx,
		header:        header,
		sidebar:       sidebar,
		chat:          ui.NewChat(),
		input:         ui.NewInput(),
		arena:         ui.NewArena(),
		modelSelector: ui.NewModelSelector(),
		focus:         FocusSidebar,
		currentAgent:  appCtx.CurrentAgent,
		keys:          defaultKeyMap(),
	}
}

// --- app.View interface ---

func (v *ChatView) ID() app.ViewID { return app.ViewChat }

func (v *ChatView) Init() tea.Cmd {
	return nil
}

func (v *ChatView) SetSize(width, height int) {
	v.width = width
	v.height = height
	v.updateSizes()
}

func (v *ChatView) Update(msg tea.Msg) (app.View, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		// When focused on input but not streaming, j/k and mouse-wheel scroll
		// the chat viewport. Key handling still runs first so Enter submits.
		if v.focus == FocusInput && !v.chat.IsStreaming() && !v.modelSelector.IsActive() && !v.arena.IsActive() {
			_, scrollCmd := v.chat.Update(msg)
			if scrollCmd != nil {
				cmds = append(cmds, scrollCmd)
			}
		}
		view, cmd := v.handleKeyMsg(msg)
		if cmd != nil {
			cmds = append(cmds, cmd)
		}
		return view, tea.Batch(cmds...)

	case tea.MouseMsg:
		// Always forward mouse events to the chat viewport so scroll wheel works.
		if !v.arena.IsActive() && !v.modelSelector.IsActive() {
			_, scrollCmd := v.chat.Update(msg)
			if scrollCmd != nil {
				cmds = append(cmds, scrollCmd)
			}
		}

	case streamChunkMsg:
		if v.arena.IsActive() {
			v.arena.AppendCellContent(msg.agentID, msg.content)
		} else {
			v.chat.AppendStreaming(msg.content)
		}
		cmds = append(cmds, v.nextStreamChunk(msg.agentID))

	case streamDoneMsg:
		if v.arena.IsActive() {
			v.arena.SetCellStatus(msg.agentID, ui.ArenaDone)
			v.arena.SetCellDuration(msg.agentID, msg.duration)
		} else {
			v.chat.FinishStreaming()
		}

	case streamErrorMsg:
		if v.arena.IsActive() {
			v.arena.SetCellError(msg.agentID, msg.err.Error())
		} else {
			v.chat.AppendStreaming(fmt.Sprintf("\n\n[Error: %v]", msg.err))
			v.chat.FinishStreaming()
		}

	case app.ServerConnectedMsg:
		v.header.SetConnected(true)

	case app.ServerDisconnectedMsg:
		v.header.SetConnected(false)

	case modelsLoadedMsg:
		v.modelSelector.SetModels(msg.models)

	case modelsErrorMsg:
		v.modelSelector.SetError(msg.err.Error())

	case arenaCompleteMsg:
		// Arena run finished; nothing extra needed.

	case benchmarkCompleteMsg:
		// Returned from benchmark CLI.
	}

	return v, tea.Batch(cmds...)
}

func (v *ChatView) View() string {
	// Arena mode view
	if v.arena.IsActive() {
		return lipgloss.JoinVertical(lipgloss.Left,
			v.header.View(),
			v.arena.View(),
		)
	}

	// Normal view
	header := v.header.View()
	sidebar := v.sidebar.View()
	chat := v.chat.View()
	input := v.input.View()

	mainContent := lipgloss.JoinHorizontal(lipgloss.Top, sidebar, chat)
	view := lipgloss.JoinVertical(lipgloss.Left, header, mainContent, input)

	// Overlay model selector if active
	if v.modelSelector.IsActive() {
		selectorView := v.modelSelector.View()
		x := (v.width - 50) / 2
		y := (v.height - 20) / 2
		view = placeOverlay(x, y, selectorView, view)
	}

	return view
}

// SyncFromContext pulls shared state that may have been changed externally
// (e.g., connection status updated by the root model).
func (v *ChatView) SyncFromContext() {
	v.header.SetConnected(v.ctx.Connected)
	if v.ctx.CurrentModel != "" {
		v.header.SetModel(v.ctx.CurrentModel)
	}
}

// --- Key handling ---

func (v *ChatView) handleKeyMsg(msg tea.KeyMsg) (app.View, tea.Cmd) {
	// Model selector overlay intercepts everything when active
	if v.modelSelector.IsActive() {
		return v.handleModelSelectorKey(msg)
	}

	// Arena mode intercepts everything when active
	if v.arena.IsActive() {
		return v.handleArenaKey(msg)
	}

	// Global keys
	switch {
	case key.Matches(msg, v.keys.Quit):
		if !v.chat.IsStreaming() {
			return v, tea.Quit
		}
		// Cancel streaming on first quit attempt
		if v.streamCancel != nil {
			v.streamCancel()
		}
		v.chat.CancelStreaming()
		return v, nil

	case key.Matches(msg, v.keys.Escape):
		if v.chat.IsStreaming() {
			if v.streamCancel != nil {
				v.streamCancel()
			}
			v.chat.CancelStreaming()
		}
		return v, nil

	case key.Matches(msg, v.keys.Tab):
		v.toggleFocus()
		return v, nil
	}

	// Route to focused component
	if v.focus == FocusSidebar {
		return v.handleSidebarKey(msg)
	}
	return v.handleInputKey(msg)
}

func (v *ChatView) handleSidebarKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Up):
		v.sidebar.MoveUp()
	case key.Matches(msg, v.keys.Down):
		v.sidebar.MoveDown()
	case key.Matches(msg, v.keys.Enter):
		return v.handleSidebarSelect()
	}
	return v, nil
}

func (v *ChatView) handleSidebarSelect() (app.View, tea.Cmd) {
	selected := v.sidebar.Selected()

	switch selected {
	case "arena":
		// Switch to arena mode - focus input for query
		v.focus = FocusInput
		v.input.Focus()
		v.sidebar.SetFocused(false)
		v.currentAgent = "arena"
		return v, nil

	case "benchmark":
		return v, v.runBenchmarkCLI()

	case "model":
		v.modelSelector.Show()
		v.modelSelector.SetLoading(true)
		return v, v.loadModels()

	default:
		// Select an agent
		v.currentAgent = selected
		item := v.sidebar.SelectedItem()
		v.chat.SetAgent(selected, item.Label)
		v.chat.Clear()
		// Focus input
		v.focus = FocusInput
		v.input.Focus()
		v.sidebar.SetFocused(false)
	}

	return v, nil
}

func (v *ChatView) handleInputKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Enter):
		query := v.input.Value()
		if query == "" {
			return v, nil
		}

		if v.currentAgent == "arena" {
			v.arena.Start(query)
			v.input.Reset()
			return v, v.startArenaRun(query)
		}

		// Normal chat mode
		v.chat.AddUserMessage(query)
		v.chat.StartStreaming()
		v.input.Reset()

		return v, v.startStream(v.currentAgent, query)

	default:
		var cmd tea.Cmd
		v.input, cmd = v.input.Update(msg)
		return v, cmd
	}
}

func (v *ChatView) handleModelSelectorKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Up):
		v.modelSelector.MoveUp()
	case key.Matches(msg, v.keys.Down):
		v.modelSelector.MoveDown()
	case key.Matches(msg, v.keys.Enter):
		selected := v.modelSelector.Selected()
		if selected != "" {
			v.ctx.CurrentModel = selected
			v.header.SetModel(selected)
		}
		v.modelSelector.Hide()
	case key.Matches(msg, v.keys.Escape):
		v.modelSelector.Hide()
	}
	return v, nil
}

func (v *ChatView) handleArenaKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Escape):
		v.arena.Stop()
		if v.streamCancel != nil {
			v.streamCancel()
		}
	case key.Matches(msg, v.keys.Quit):
		v.arena.Stop()
		if v.streamCancel != nil {
			v.streamCancel()
		}
		return v, tea.Quit
	}
	return v, nil
}

// --- Focus ---

func (v *ChatView) toggleFocus() {
	if v.focus == FocusSidebar {
		v.focus = FocusInput
		v.sidebar.SetFocused(false)
		v.input.Focus()
	} else {
		v.focus = FocusSidebar
		v.sidebar.SetFocused(true)
		v.input.Blur()
	}
}

// --- Sizing ---

func (v *ChatView) updateSizes() {
	headerHeight := 3
	inputHeight := 3
	sidebarWidth := ui.SidebarWidth + 2

	contentHeight := v.height - headerHeight - inputHeight
	chatWidth := v.width - sidebarWidth

	v.header.SetWidth(v.width)
	v.sidebar.SetHeight(contentHeight)
	v.chat.SetSize(chatWidth, contentHeight)
	v.input.SetWidth(v.width)
	v.arena.SetSize(v.width, v.height-headerHeight)
	v.modelSelector.SetSize(50, 20)
}

// --- Streaming ---

// startStream initiates a new streaming request.
func (v *ChatView) startStream(agentID, query string) tea.Cmd {
	ctx, cancel := context.WithCancel(context.Background())
	v.streamCancel = cancel
	v.streamStart = time.Now()

	modelWithStrategy := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, agentID)
	v.streamRespChan, v.streamErrChan = v.ctx.ServerClient.Generate(ctx, modelWithStrategy, query)

	return v.nextStreamChunk(agentID)
}

// nextStreamChunk reads the next chunk from stored channels.
func (v *ChatView) nextStreamChunk(agentID string) tea.Cmd {
	respChan := v.streamRespChan
	errChan := v.streamErrChan
	startTime := v.streamStart

	return func() tea.Msg {
		if respChan == nil {
			return streamDoneMsg{agentID: agentID, duration: 0}
		}
		for {
			select {
			case resp, ok := <-respChan:
				if !ok {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
				if resp.Response != "" {
					return streamChunkMsg{agentID: agentID, content: resp.Response}
				}
				if resp.Done {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
			case err := <-errChan:
				if err != nil {
					return streamErrorMsg{agentID: agentID, err: err}
				}
			}
		}
	}
}

// --- Arena ---

func (v *ChatView) startArenaRun(query string) tea.Cmd {
	agents := ui.DefaultAgents()

	return func() tea.Msg {
		ctx, cancel := context.WithCancel(context.Background())
		v.streamCancel = cancel

		type arenaResult struct {
			agentID  string
			content  string
			duration float64
			err      error
		}
		results := make(chan arenaResult, len(agents))

		for _, agent := range agents {
			go func(agentID string) {
				modelWithStrategy := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, agentID)
				startTime := time.Now()

				v.arena.SetCellStatus(agentID, ui.ArenaRunning)

				content, err := v.ctx.ServerClient.GenerateSync(ctx, modelWithStrategy, query)
				duration := time.Since(startTime).Seconds()

				results <- arenaResult{
					agentID:  agentID,
					content:  content,
					duration: duration,
					err:      err,
				}
			}(agent.ID)
		}

		for i := 0; i < len(agents); i++ {
			result := <-results
			if result.err != nil {
				v.arena.SetCellError(result.agentID, result.err.Error())
			} else {
				v.arena.SetCellContent(result.agentID, result.content)
				v.arena.SetCellStatus(result.agentID, ui.ArenaDone)
				v.arena.SetCellDuration(result.agentID, result.duration)
			}
		}

		return arenaCompleteMsg{}
	}
}

// --- Model loading ---

func (v *ChatView) loadModels() tea.Cmd {
	return func() tea.Msg {
		models, err := v.ctx.OllamaClient.ListModels()
		if err != nil {
			return modelsErrorMsg{err: err}
		}
		return modelsLoadedMsg{models: models}
	}
}

// modelsLoadedMsg / modelsErrorMsg are handled internally within ChatView.Update.
type modelsLoadedMsg struct{ models []string }
type modelsErrorMsg struct{ err error }

// --- Benchmark ---

func (v *ChatView) runBenchmarkCLI() tea.Cmd {
	c := exec.Command("python", "agent_cli.py", "--benchmark")
	return tea.ExecProcess(c, func(err error) tea.Msg {
		return benchmarkCompleteMsg{err: err}
	})
}

// --- Overlay helper ---

// ansiDropLeft returns the visible tail of s after skipping n visible columns,
// preserving ANSI escape sequences. It works by truncating a reversed-width
// view: get the full string width, then truncate from the right to (width-n).
func ansiDropLeft(s string, n int) string {
	total := lipgloss.Width(s)
	if n <= 0 {
		return s
	}
	if n >= total {
		return ""
	}
	// Truncate the full string to `total` keeps everything; we want the
	// right (total-n) columns. Achieve this by stripping the left n columns:
	// first build a prefix of exactly n cols, then remove it from the raw
	// string byte-wise (safe because Truncate preserves escape sequences and
	// we only strip the prefix bytes it produced).
	prefix := ansi.Truncate(s, n, "")
	return s[len(prefix):]
}

func placeOverlay(x, y int, overlay, background string) string {
	bgLines := strings.Split(background, "\n")
	overlayLines := strings.Split(overlay, "\n")

	for i, line := range overlayLines {
		bgY := y + i
		if bgY < 0 || bgY >= len(bgLines) {
			continue
		}
		bgLine := bgLines[bgY]
		bgWidth := lipgloss.Width(bgLine)
		if x < 0 || x >= bgWidth {
			continue
		}

		// ANSI-safe left portion (before the overlay).
		before := ansi.Truncate(bgLine, x, "")

		// ANSI-safe right portion (after the overlay).
		endX := x + lipgloss.Width(line)
		after := ""
		if endX < bgWidth {
			after = ansiDropLeft(bgLine, endX)
		}

		bgLines[bgY] = before + line + after
	}

	return strings.Join(bgLines, "\n")
}
