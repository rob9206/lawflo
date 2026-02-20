# PPTX Conversion Architecture

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│                  (DocumentsPage.tsx)                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. User uploads PPTX file                           │   │
│  │  2. User clicks Download icon on PPTX file           │   │
│  │  3. Dropdown menu appears with 4 options:            │   │
│  │     📄 Convert to PDF                                │   │
│  │     🖼️ Convert to Images                             │   │
│  │     📝 Convert to Text                               │   │
│  │     📋 Convert to Markdown                           │   │
│  │  4. User selects format                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   API CLIENT LAYER                           │
│                  (converter.ts)                              │
│                                                              │
│  POST /api/documents/{docId}/convert                        │
│  Body: { "format": "pdf|png|txt|md" }                       │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND API ROUTE                         │
│                 (documents.py)                               │
│                                                              │
│  1. Validate document exists                                │
│  2. Check file_type == "pptx"                               │
│  3. Validate output format                                  │
│  4. Call document_converter service                         │
│  5. Return download URL                                     │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               CONVERSION SERVICE                             │
│            (document_converter.py)                           │
│                                                              │
│  convert_document(input_path, format, output_path)          │
│          │                                                   │
│          ├──► format == "pdf"                                │
│          │    └─► convert_pptx_to_pdf()                     │
│          │        Uses: ReportLab, python-pptx              │
│          │        Output: Single PDF file                   │
│          │                                                   │
│          ├──► format == "png"                                │
│          │    └─► convert_pptx_to_images()                  │
│          │        Uses: PIL/Pillow, python-pptx             │
│          │        Output: Multiple PNG files                │
│          │                                                   │
│          ├──► format == "txt"                                │
│          │    └─► convert_pptx_to_text()                    │
│          │        Uses: python-pptx                         │
│          │        Output: Plain text file                   │
│          │                                                   │
│          └──► format == "md"                                 │
│               └─► convert_pptx_to_markdown()                │
│                   Uses: python-pptx                         │
│                   Output: Markdown file                     │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FILE SYSTEM                                │
│                                                              │
│  Input:  data/uploads/{uuid}.pptx                           │
│  Output: data/uploads/converted/{uuid}.{format}             │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  DOWNLOAD ENDPOINT                           │
│                                                              │
│  GET /api/documents/{docId}/download/{filename}             │
│                                                              │
│  1. Validate document ownership                             │
│  2. Security check: file in converted directory             │
│  3. Send file with proper headers                           │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Browser   │
                    │  Downloads  │
                    │    File     │
                    └─────────────┘
```

## Technology Stack

### Frontend
- **React** - UI components
- **TypeScript** - Type safety
- **TanStack Query** - API state management
- **Axios** - HTTP client
- **Lucide React** - Icons

### Backend
- **Flask** - Web framework
- **SQLAlchemy** - Database ORM
- **python-pptx** - PPTX parsing
- **ReportLab** - PDF generation
- **Pillow (PIL)** - Image processing

## File Structure

```
LawFlow/
├── api/
│   ├── routes/
│   │   └── documents.py           # API endpoints
│   └── services/
│       └── document_converter.py  # Conversion logic
├── frontend/
│   └── src/
│       ├── api/
│       │   └── converter.ts       # API client
│       └── pages/
│           └── DocumentsPage.tsx  # UI with conversion menu
├── data/
│   └── uploads/
│       ├── {uuid}.pptx            # Original files
│       └── converted/             # Converted files
│           ├── {uuid}.pdf
│           ├── {uuid}.txt
│           ├── {uuid}.md
│           └── {uuid}_slides/     # PNG directory
│               ├── slide_001.png
│               ├── slide_002.png
│               └── ...
├── requirements.txt               # Python dependencies
├── CONVERSION_FEATURE.md          # Full documentation
└── CONVERSION_SUMMARY.md          # Quick reference
```

## Conversion Methods

### PDF Conversion
```python
pptx → python-pptx.Presentation
     → Extract text from shapes
     → ReportLab PDF generation
     → Output: PDF file
```

### Image Conversion
```python
pptx → python-pptx.Presentation
     → Extract text from slides
     → PIL.Image.new() for each slide
     → Draw text on image
     → Output: PNG files (one per slide)
```

### Text Conversion
```python
pptx → python-pptx.Presentation
     → Extract text from all shapes
     → Format with slide separators
     → Output: Plain text file
```

### Markdown Conversion
```python
pptx → python-pptx.Presentation
     → Extract text with structure
     → Format with Markdown syntax
     → Preserve headings and tables
     → Output: Markdown file
```

## Error Handling

```
User Action
    │
    ▼
Frontend validation
    │
    ├─► Invalid format → Show error message
    │
    ▼
API validation
    │
    ├─► Document not found → 404 error
    ├─► Not PPTX file → 400 validation error
    ├─► Invalid format → 400 validation error
    │
    ▼
Conversion process
    │
    ├─► File not found → FileNotFoundError
    ├─► Conversion error → Generic exception
    │
    ▼
Success
    │
    └─► Return download URL
```

## Security Measures

1. **Path Validation**: Prevents directory traversal attacks
2. **File Type Check**: Only allows PPTX conversion
3. **Output Directory**: Restricted to `converted/` subdirectory
4. **File Size Limits**: Inherits from document upload limits
5. **Authentication**: Uses existing Flask authentication (if enabled)

## Performance Optimization

- **Async Processing**: Could be added for large files
- **Caching**: Could cache converted files to avoid re-conversion
- **Cleanup**: Could implement automatic cleanup of old converted files
- **Progress Tracking**: Could add WebSocket for real-time progress
