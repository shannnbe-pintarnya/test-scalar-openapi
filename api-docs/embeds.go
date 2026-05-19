package docsapi

import "embed"

// do not change these comments, they are used by the go:embed directive
//go:embed internal/index.html
var DocsFS embed.FS
