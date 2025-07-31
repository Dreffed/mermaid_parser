/* ===== static/js/app.js ===== */
class MermaidConverter {
    constructor() {
        this.initializeEventListeners();
        this.loadPlatforms();
        this.setupMermaid();
    }

    setupMermaid() {
        if (typeof mermaid !== 'undefined') {
            mermaid.initialize({
                startOnLoad: false,
                theme: 'default',
                securityLevel: 'loose',
                flowchart: {
                    useMaxWidth: true,
                    htmlLabels: true
                }
            });
        }
    }

    initializeEventListeners() {
        // Parse button
        document.getElementById('parseBtn')?.addEventListener('click', () => {
            this.parseMermaidCode();
        });

        // Preview button
        document.getElementById('previewBtn')?.addEventListener('click', () => {
            this.previewDiagram();
        });

        // Convert button
        document.getElementById('convertBtn')?.addEventListener('click', () => {
            this.convertDiagram();
        });

        // Platform selection
        document.getElementById('targetPlatform')?.addEventListener('change', (e) => {
            const convertBtn = document.getElementById('convertBtn');
            convertBtn.disabled = !e.target.value;
        });

        // Auto-preview checkbox
        document.getElementById('autoPreview')?.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.setupAutoPreview();
            } else {
                this.teardownAutoPreview();
            }
        });

        // Set up auto-preview if enabled by default
        if (document.getElementById('autoPreview')?.checked) {
            this.setupAutoPreview();
        }
    }

    setupAutoPreview() {
        const codeEditor = document.getElementById('mermaidCode');
        if (codeEditor) {
            this.autoPreviewTimeout = null;
            codeEditor.addEventListener('input', () => {
                clearTimeout(this.autoPreviewTimeout);
                this.autoPreviewTimeout = setTimeout(() => {
                    this.previewDiagram();
                }, 1000); // Debounce for 1 second
            });
        }
    }

    teardownAutoPreview() {
        const codeEditor = document.getElementById('mermaidCode');
        if (codeEditor && this.autoPreviewTimeout) {
            clearTimeout(this.autoPreviewTimeout);
            codeEditor.removeEventListener('input', this.setupAutoPreview);
        }
    }

    async loadPlatforms() {
        try {
            const response = await fetch('/api/platforms');
            const data = await response.json();

            const platformSelect = document.getElementById('targetPlatform');
            if (platformSelect) {
                // Clear existing options except the first one
                while (platformSelect.children.length > 1) {
                    platformSelect.removeChild(platformSelect.lastChild);
                }

                // Add available platforms
                data.platforms.forEach(platform => {
                    const option = document.createElement('option');
                    option.value = platform.name;
                    option.textContent = platform.display_name;
                    option.disabled = !platform.configured;

                    if (!platform.configured) {
                        option.textContent += ' (Not Configured)';
                    }

                    platformSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load platforms:', error);
            this.showAlert('Failed to load available platforms', 'danger');
        }
    }

    async parseMermaidCode() {
        const code = document.getElementById('mermaidCode').value;
        const resultDiv = document.getElementById('parseResult');

        if (!code.trim()) {
            this.showParseResult('Please enter some Mermaid code', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/parse', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ code })
            });

            const data = await response.json();

            if (data.success) {
                const message = `
                    <div class="alert alert-success">
                        <h6><i class="fas fa-check-circle me-2"></i>Parsing Successful!</h6>
                        <p class="mb-1"><strong>Diagram Type:</strong> ${data.diagram_type}</p>
                        <p class="mb-1"><strong>Nodes:</strong> ${data.nodes.length}</p>
                        <p class="mb-0"><strong>Edges:</strong> ${data.edges.length}</p>
                    </div>
                `;
                resultDiv.innerHTML = message;
            } else {
                this.showParseResult(`Parsing Error: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showParseResult(`Network Error: ${error.message}`, 'danger');
        }
    }

    async previewDiagram() {
        const code = document.getElementById('mermaidCode').value;
        const previewDiv = document.getElementById('diagramPreview');

        if (!code.trim()) {
            previewDiv.innerHTML = `
                <div class="text-muted">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <p>No code to preview</p>
                </div>
            `;
            return;
        }

        try {
            // Show loading state
            previewDiv.innerHTML = `
                <div class="text-muted">
                    <div class="spinner-border mb-3" role="status"></div>
                    <p>Rendering diagram...</p>
                </div>
            `;

            if (typeof mermaid !== 'undefined') {
                // Clear the preview div and create a new element for mermaid
                previewDiv.innerHTML = '<div id="mermaidRender"></div>';

                const renderDiv = document.getElementById('mermaidRender');

                try {
                    // Generate a unique ID for this render
                    const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);

                    // Render the mermaid diagram
                    const { svg } = await mermaid.render(id, code);
                    renderDiv.innerHTML = svg;

                } catch (mermaidError) {
                    previewDiv.innerHTML = `
                        <div class="text-danger">
                            <i class="fas fa-exclamation-circle fa-3x mb-3"></i>
                            <p>Diagram rendering failed</p>
                            <small>${mermaidError.message}</small>
                        </div>
                    `;
                }
            } else {
                previewDiv.innerHTML = `
                    <div class="text-warning">
                        <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                        <p>Mermaid library not loaded</p>
                        <p class="small">Preview unavailable</p>
                    </div>
                `;
            }
        } catch (error) {
            previewDiv.innerHTML = `
                <div class="text-danger">
                    <i class="fas fa-times-circle fa-3x mb-3"></i>
                    <p>Preview failed</p>
                    <small>${error.message}</small>
                </div>
            `;
        }
    }

    async convertDiagram() {
        const code = document.getElementById('mermaidCode').value;
        const platform = document.getElementById('targetPlatform').value;
        const convertBtn = document.getElementById('convertBtn');

        console.log('=== CONVERT DEBUG ===');
        console.log('Code length:', code.length);
        console.log('Platform:', platform);
        console.log('Code preview:', code.substring(0, 100));

        if (!code.trim()) {
            this.showAlert('Please enter some Mermaid code', 'warning');
            return;
        }

        if (!platform) {
            this.showAlert('Please select a target platform', 'warning');
            return;
        }

        // Show loading state
        const originalText = convertBtn.innerHTML;
        convertBtn.disabled = true;
        convertBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Converting...';

        try {
            const requestData = {
                code: code,
                platform: platform,
                options: {
                    board_name: `Mermaid Conversion - ${new Date().toLocaleString()}`
                }
            };

            console.log('Request data:', requestData);

            const response = await fetch('/api/convert', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers));

            const responseText = await response.text();
            console.log('Response text:', responseText);

            let data;
            try {
                data = JSON.parse(responseText);
            } catch (parseError) {
                console.error('Failed to parse response as JSON:', parseError);
                throw new Error(`Invalid JSON response: ${responseText}`);
            }

            if (data.success) {
                console.log('Conversion successful:', data);
                this.showConversionResult(data);
            } else {
                console.error('Conversion failed:', data);
                this.showAlert(`Conversion failed: ${data.error}`, 'danger');
            }
        } catch (error) {
            console.error('Network/unexpected error:', error);
            this.showAlert(`Network error: ${error.message}`, 'danger');
        } finally {
            // Restore button state
            convertBtn.disabled = false;
            convertBtn.innerHTML = originalText;
        }
    }

    showParseResult(message, type) {
        const resultDiv = document.getElementById('parseResult');
        const alertClass = type === 'success' ? 'alert-success' :
                          type === 'warning' ? 'alert-warning' : 'alert-danger';

        resultDiv.innerHTML = `
            <div class="alert ${alertClass}">
                ${message}
            </div>
        `;
    }

    showConversionResult(data) {
        const resultHTML = `
            <div class="alert alert-success">
                <h6><i class="fas fa-check-circle me-2"></i>${data.message}</h6>
                <p class="mb-2"><strong>Platform:</strong> ${data.platform.charAt(0).toUpperCase() + data.platform.slice(1)}</p>
                <p class="mb-2"><strong>Shapes Created:</strong> ${data.shapes_created || 'N/A'}</p>
                <p class="mb-0"><strong>Connectors Created:</strong> ${data.connectors_created || 'N/A'}</p>
            </div>
        `;

        document.getElementById('conversionResult').innerHTML = resultHTML;

        // Set up the "Open Diagram" button
        const openBtn = document.getElementById('openDiagramBtn');
        openBtn.href = data.url;

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('conversionModal'));
        modal.show();
    }

    showAlert(message, type) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insert at the beginning of main content
        const main = document.querySelector('main');
        main.insertBefore(alertDiv, main.firstChild);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// History functionality
async function showHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        let historyHTML = '';

        if (data.history.length === 0) {
            historyHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-history fa-3x mb-3"></i>
                    <p>No conversion history yet</p>
                </div>
            `;
        } else {
            historyHTML = `
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Platform</th>
                                <th>Status</th>
                                <th>Preview</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            data.history.forEach(item => {
                const date = new Date(item.created_at).toLocaleString();
                const statusBadge = item.status === 'success'
                    ? '<span class="badge bg-success">Success</span>'
                    : '<span class="badge bg-danger">Failed</span>';

                historyHTML += `
                    <tr>
                        <td>${date}</td>
                        <td>${item.platform.charAt(0).toUpperCase() + item.platform.slice(1)}</td>
                        <td>${statusBadge}</td>
                        <td><code class="small">${item.preview}</code></td>
                        <td>
                            ${item.url ?
                                `<a href="${item.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-external-link-alt"></i> Open
                                </a>` :
                                '<span class="text-muted">-</span>'
                            }
                        </td>
                    </tr>
                `;
            });

            historyHTML += '</tbody></table></div>';
        }

        document.getElementById('historyContent').innerHTML = historyHTML;

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('historyModal'));
        modal.show();

    } catch (error) {
        console.error('Failed to load history:', error);
        document.getElementById('historyContent').innerHTML = `
            <div class="alert alert-danger">
                Failed to load conversion history: ${error.message}
            </div>
        `;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MermaidConverter();
});

