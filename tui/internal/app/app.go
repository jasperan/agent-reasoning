package app

import (
	"time"

	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/config"

	tea "github.com/charmbracelet/bubbletea"
)

// Messages for async operations handled at the root level.
// Exported so views can react to connection state changes.
type (
	ServerConnectedMsg    struct{}
	ServerDisconnectedMsg struct{}
)

// Model is the root Bubble Tea model. It owns the Router and shared Context,
// handles global concerns (window resize, connection health, quit), and
// delegates everything else to the active View via the Router.
type Model struct {
	ctx    *Context
	router *Router

	quitting bool
}

// New creates a new application model with default config (backward-compatible).
func New() *Model {
	return NewWithConfig(config.DefaultConfig(), "")
}

// NewWithConfig creates a new application model with explicit config and project dir.
func NewWithConfig(cfg config.Config, projectDir string) *Model {
	appCtx := &Context{
		ServerClient: client.NewServerClient(),
		OllamaClient: client.NewOllamaClient(),
		Config:       cfg,
		CurrentModel: cfg.Defaults.Model,
		CurrentAgent: "standard",
		Connected:    false,
		ProjectDir:   projectDir,
		AgentParams:  make(map[string]map[string]float64),
	}

	// The Router starts with no views. Views are registered by the caller
	// (main.go) after they are created with access to the Context.
	router := NewRouter(map[ViewID]View{}, ViewChat)

	return &Model{
		ctx:    appCtx,
		router: router,
	}
}

// Context returns the shared context so callers (main.go) can create views.
func (m *Model) Ctx() *Context {
	return m.ctx
}

// Router returns the router so callers can register views.
func (m *Model) Router() *Router {
	return m.router
}

// Init starts connection health check and enters alt screen.
func (m *Model) Init() tea.Cmd {
	initCmd := m.router.SwitchTo(ViewChat)
	return tea.Batch(
		m.checkConnection(),
		tea.EnterAltScreen,
		initCmd,
	)
}

// checkConnection checks if the server is healthy.
func (m *Model) checkConnection() tea.Cmd {
	return func() tea.Msg {
		if m.ctx.ServerClient.IsHealthy() {
			return ServerConnectedMsg{}
		}
		return ServerDisconnectedMsg{}
	}
}

// Update handles messages. Global concerns are handled here; everything else
// is forwarded to the router (which forwards to the active View).
func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.ctx.Width = msg.Width
		m.ctx.Height = msg.Height
		m.router.SetSize(msg.Width, msg.Height)
		return m, nil

	case ServerConnectedMsg:
		m.ctx.Connected = true
		// Notify the active view so it can update its header.
		cmd := m.router.Update(msg)
		return m, cmd

	case ServerDisconnectedMsg:
		m.ctx.Connected = false
		cmd := m.router.Update(msg)
		retryCmd := tea.Tick(2*time.Second, func(time.Time) tea.Msg {
			return m.checkConnection()()
		})
		return m, tea.Batch(cmd, retryCmd)

	case SwitchViewMsg:
		cmd := m.router.SwitchTo(msg.Target)
		return m, cmd
	}

	// Everything else goes to the active view via the router.
	cmd := m.router.Update(msg)
	return m, cmd
}

// View renders the application. If quitting, show goodbye; otherwise delegate.
func (m *Model) View() string {
	if m.quitting {
		return "Goodbye!\n"
	}
	return m.router.View()
}
