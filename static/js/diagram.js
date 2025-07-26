// ===== static/js/diagram.js =====
// Additional diagram-specific functionality can go here
// This file is loaded after the main app.js on the index page

// Example: Custom Mermaid themes or additional parsing logic
const DiagramHelpers = {
    // Sample Mermaid diagrams for quick testing
    samples: {
        flowchart: `flowchart TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E`,

        sequence: `sequenceDiagram
    participant A as Alice
    participant B as Bob
    A->>B: Hello Bob!
    B-->>A: Hello Alice!
    A->>B: How are you?
    B-->>A: I'm good, thanks!`,

        complex: `flowchart TD
    A[Start] --> B[Process Input]
    B --> C{Valid Input?}
    C -->|Yes| D[Process Data]
    C -->|No| E[Show Error]
    D --> F{Save Success?}
    F -->|Yes| G[Send Confirmation]
    F -->|No| H[Log Error]
    E --> I[Return to Input]
    G --> J[End]
    H --> I
    I --> B`
    },

    // Insert sample diagram
    insertSample(type) {
        const codeEditor = document.getElementById('mermaidCode');
        if (codeEditor && this.samples[type]) {
            codeEditor.value = this.samples[type];

            // Trigger auto-preview if enabled
            if (document.getElementById('autoPreview')?.checked) {
                setTimeout(() => {
                    document.getElementById('previewBtn')?.click();
                }, 100);
            }
        }
    },

    // Format mermaid code (basic formatting)
    formatCode() {
        const codeEditor = document.getElementById('mermaidCode');
        if (!codeEditor) return;

        let code = codeEditor.value;

        // Basic formatting rules
        code = code
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .join('\n');

        codeEditor.value = code;
    }
};

// Add sample diagram buttons to the interface
document.addEventListener('DOMContentLoaded', () => {
    // You could add quick sample buttons here if desired
    // For now, this is just a placeholder for additional diagram functionality
});
