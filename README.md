# ===== README.md =====
# Mermaid to Miro/Lucid Converter

A Docker-based web application that converts Mermaid diagrams to visual diagrams in platforms like Miro and Lucidchart.

## Features

- **Web Interface**: Clean, modern UI for inputting Mermaid code
- **Mermaid Parser**: Parse and validate Mermaid diagrams with error reporting
- **Optional Preview**: View Mermaid diagrams before conversion
- **Multi-Platform Support**: Currently supports Miro (Lucidchart coming soon)
- **Admin Panel**: Configure API credentials and monitor conversions
- **Conversion History**: Track all conversions with links to results
- **Docker Ready**: Easy deployment with Docker Compose

## Quick Start

1. **Clone and run with Docker Compose:**
   ```bash
   git clone <repository>
   cd mermaid-converter
   docker-compose up -d
   ```

2. **Access the application:**
   - Main app: http://localhost:5000
   - Admin panel: http://localhost:5000/admin (admin/admin)

3. **Configure Miro integration:**
   - Go to admin panel
   - Add your Miro access token
   - Test the connection

## Configuration

### Miro Setup
1. Create a Miro app at https://developers.miro.com/
2. Get your access token
3. Add it in the admin panel under Miro configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: Database connection string
- `FLASK_ENV`: Environment (development/production)

## Supported Diagram Types

Currently supports:
- ✅ Flowcharts (graph/flowchart)
- ✅ Basic Sequence Diagrams
- 🚧 Class Diagrams (coming soon)
- 🚧 State Diagrams (coming soon)

## API Endpoints

- `POST /api/parse` - Parse Mermaid code
- `POST /api/convert` - Convert to target platform
- `GET /api/platforms` - Get available platforms
- `GET /api/history` - Get conversion history

## Development

1. **Local setup:**
   ```bash
   pip install -r requirements.txt
   export FLASK_APP=app.py
   export FLASK_ENV=development
   flask run
   ```

2. **Adding new platforms:**
   - Create converter in `converters/`
   - Inherit from `BaseConverter`
   - Add to platform selection in UI

## License

MIT License - See LICENSE file for details.