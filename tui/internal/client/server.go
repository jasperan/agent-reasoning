package client

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

const (
	ServerHost = "http://localhost:8080"
)

// ServerClient communicates with server.py
type ServerClient struct {
	baseURL string
	client  *http.Client
}

// GenerateRequest is the request body for /api/generate
type GenerateRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

// GenerateResponse is a single response chunk from /api/generate
type GenerateResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Response  string `json:"response"`
	Done      bool   `json:"done"`
}

// NewServerClient creates a new server client
func NewServerClient() *ServerClient {
	return &ServerClient{
		baseURL: ServerHost,
		client: &http.Client{
			Timeout: 0, // No timeout for streaming
		},
	}
}

// Generate sends a query to the server and returns a channel of response chunks
func (c *ServerClient) Generate(ctx context.Context, model, prompt string) (<-chan GenerateResponse, <-chan error) {
	respChan := make(chan GenerateResponse, 100)
	errChan := make(chan error, 1)

	go func() {
		defer close(respChan)
		defer close(errChan)

		reqBody := GenerateRequest{
			Model:  model,
			Prompt: prompt,
			Stream: true,
		}

		body, err := json.Marshal(reqBody)
		if err != nil {
			errChan <- fmt.Errorf("failed to marshal request: %w", err)
			return
		}

		req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/api/generate", bytes.NewReader(body))
		if err != nil {
			errChan <- fmt.Errorf("failed to create request: %w", err)
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.client.Do(req)
		if err != nil {
			errChan <- fmt.Errorf("failed to send request: %w", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			errChan <- fmt.Errorf("server returned status %d", resp.StatusCode)
			return
		}

		scanner := bufio.NewScanner(resp.Body)
		// Increase buffer size for large responses
		scanner.Buffer(make([]byte, 64*1024), 1024*1024)

		for scanner.Scan() {
			select {
			case <-ctx.Done():
				return
			default:
			}

			line := scanner.Text()
			if line == "" {
				continue
			}

			var genResp GenerateResponse
			if err := json.Unmarshal([]byte(line), &genResp); err != nil {
				// Skip malformed lines
				continue
			}

			respChan <- genResp

			if genResp.Done {
				return
			}
		}

		if err := scanner.Err(); err != nil {
			errChan <- fmt.Errorf("error reading response: %w", err)
		}
	}()

	return respChan, errChan
}

// GenerateSync sends a query and waits for the complete response
func (c *ServerClient) GenerateSync(ctx context.Context, model, prompt string) (string, error) {
	respChan, errChan := c.Generate(ctx, model, prompt)

	var fullResponse string
	for {
		select {
		case resp, ok := <-respChan:
			if !ok {
				return fullResponse, nil
			}
			fullResponse += resp.Response
			if resp.Done {
				return fullResponse, nil
			}
		case err := <-errChan:
			if err != nil {
				return fullResponse, err
			}
		case <-ctx.Done():
			return fullResponse, ctx.Err()
		}
	}
}

// ParameterSchema describes one tunable hyperparameter.
type ParameterSchema struct {
	Type        string  `json:"type"`
	Default     float64 `json:"default"`
	Min         float64 `json:"min"`
	Max         float64 `json:"max"`
	Description string  `json:"description"`
}

// AgentMeta holds metadata for one agent from /api/agents.
type AgentMeta struct {
	ID            string                     `json:"id"`
	Name          string                     `json:"name"`
	Description   string                     `json:"description"`
	Reference     string                     `json:"reference"`
	BestFor       string                     `json:"best_for"`
	Tradeoffs     string                     `json:"tradeoffs"`
	HasVisualizer bool                       `json:"has_visualizer"`
	Parameters    map[string]ParameterSchema `json:"parameters"`
}

// AgentsResponse is the response from GET /api/agents.
type AgentsResponse struct {
	Agents []AgentMeta `json:"agents"`
	Count  int         `json:"count"`
}

// StructuredEvent is one event from /api/generate_structured.
type StructuredEvent struct {
	EventType string                 `json:"event_type"`
	Data      map[string]interface{} `json:"data"`
	IsUpdate  bool                   `json:"is_update"`
}

// ListAgents calls GET /api/agents and returns agent metadata.
func (c *ServerClient) ListAgents() ([]AgentMeta, error) {
	resp, err := c.client.Get(c.baseURL + "/api/agents")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result AgentsResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result.Agents, nil
}

// GenerateStructured calls POST /api/generate_structured and streams StructuredEvent objects.
func (c *ServerClient) GenerateStructured(ctx context.Context, model, prompt string, params map[string]float64) (<-chan StructuredEvent, <-chan error) {
	eventCh := make(chan StructuredEvent, 100)
	errCh := make(chan error, 1)

	go func() {
		defer close(eventCh)
		defer close(errCh)

		body := map[string]interface{}{
			"model":  model,
			"prompt": prompt,
			"stream": true,
		}
		if len(params) > 0 {
			body["parameters"] = params
		}

		jsonBody, err := json.Marshal(body)
		if err != nil {
			errCh <- err
			return
		}

		req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/api/generate_structured", bytes.NewReader(jsonBody))
		if err != nil {
			errCh <- err
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.client.Do(req)
		if err != nil {
			errCh <- err
			return
		}
		defer resp.Body.Close()

		scanner := bufio.NewScanner(resp.Body)
		scanner.Buffer(make([]byte, 1024*1024), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				continue
			}
			var event StructuredEvent
			if err := json.Unmarshal([]byte(line), &event); err != nil {
				continue // skip malformed lines
			}
			select {
			case eventCh <- event:
			case <-ctx.Done():
				return
			}
		}
	}()

	return eventCh, errCh
}

// GenerateWithParams is like Generate but includes hyperparameters.
func (c *ServerClient) GenerateWithParams(ctx context.Context, model, prompt string, params map[string]float64) (<-chan GenerateResponse, <-chan error) {
	respCh := make(chan GenerateResponse, 100)
	errCh := make(chan error, 1)

	go func() {
		defer close(respCh)
		defer close(errCh)

		body := map[string]interface{}{
			"model":  model,
			"prompt": prompt,
			"stream": true,
		}
		if len(params) > 0 {
			body["parameters"] = params
		}

		jsonBody, err := json.Marshal(body)
		if err != nil {
			errCh <- err
			return
		}

		req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/api/generate", bytes.NewReader(jsonBody))
		if err != nil {
			errCh <- err
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.client.Do(req)
		if err != nil {
			errCh <- err
			return
		}
		defer resp.Body.Close()

		scanner := bufio.NewScanner(resp.Body)
		scanner.Buffer(make([]byte, 1024*1024), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				continue
			}
			var genResp GenerateResponse
			if err := json.Unmarshal([]byte(line), &genResp); err != nil {
				continue
			}
			select {
			case respCh <- genResp:
			case <-ctx.Done():
				return
			}
		}
	}()

	return respCh, errCh
}

// IsHealthy checks if the server is responding
func (c *ServerClient) IsHealthy() bool {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "GET", c.baseURL+"/api/tags", nil)
	if err != nil {
		return false
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
