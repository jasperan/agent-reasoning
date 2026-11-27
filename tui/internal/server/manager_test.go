package server

import (
	"os"
	"path/filepath"
	"testing"
)

func TestPythonForPrefersProjectVenv(t *testing.T) {
	dir := t.TempDir()
	if got := pythonFor(dir); got != "python" {
		t.Fatalf("without a venv: got %q, want python", got)
	}

	venvPython := filepath.Join(dir, ".venv", "bin", "python")
	if err := os.MkdirAll(filepath.Dir(venvPython), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(venvPython, nil, 0o755); err != nil {
		t.Fatal(err)
	}
	if got := pythonFor(dir); got != venvPython {
		t.Fatalf("with a venv: got %q, want %q", got, venvPython)
	}
}
