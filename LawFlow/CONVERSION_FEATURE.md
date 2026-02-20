# PPTX Document Conversion Feature

## Overview

LawFlow now supports converting PowerPoint (PPTX) files to multiple formats directly from the Documents page.

## Supported Conversion Formats

### 1. PDF
Converts PowerPoint slides to a multi-page PDF document. Each slide becomes a page in the PDF.

**Use cases:**
- Sharing presentations in a universally accessible format
- Printing slides
- Long-term archival

### 2. PNG Images
Extracts each slide as a separate PNG image file.

**Use cases:**
- Embedding individual slides in web pages
- Creating social media graphics
- Slide-by-slide analysis

### 3. Plain Text (TXT)
Extracts all text content from slides into a plain text file.

**Use cases:**
- Text analysis
- Quick reference
- Feeding content into AI systems

### 4. Markdown (MD)
Converts slides to formatted Markdown with headings and tables preserved.

**Use cases:**
- Documentation
- Version control friendly format
- Easy editing and reuse

## How to Use

### Frontend (Documents Page)

1. Upload a PPTX file to the Documents page
2. Wait for processing to complete
3. Click the **Download** icon next to any PPTX file
4. Select your desired output format:
   - Convert to PDF
   - Convert to Images
   - Convert to Text
   - Convert to Markdown
5. The converted file will download automatically

### API Endpoints

#### Convert Document
```
POST /api/documents/<doc_id>/convert
Content-Type: application/json

{
  "format": "pdf" | "png" | "txt" | "md"
}
```

**Response:**
```json
{
  "format": "pdf",
  "message": "Conversion successful",
  "download_url": "/api/documents/<doc_id>/download/<filename>"
}
```

#### Download Converted File
```
GET /api/documents/<doc_id>/download/<filename>
```

Returns the converted file for download.

## Technical Implementation

### Backend Components

**File:** `api/services/document_converter.py`

Functions:
- `convert_pptx_to_pdf()` - Uses ReportLab to generate PDFs
- `convert_pptx_to_images()` - Uses PIL/Pillow to create PNG images
- `convert_pptx_to_text()` - Extracts plain text
- `convert_pptx_to_markdown()` - Formats as Markdown
- `convert_document()` - Main routing function

**Dependencies:**
```
reportlab==4.2.5   # PDF generation
Pillow==11.0.0     # Image processing
python-pptx==1.0.2 # PPTX parsing (already installed)
```

### Frontend Components

**File:** `frontend/src/api/converter.ts`
- API client for conversion endpoints

**File:** `frontend/src/pages/DocumentsPage.tsx`
- UI with conversion menu dropdown
- Download button for PPTX files
- Progress indicators during conversion

## Configuration

Converted files are stored in:
```
<UPLOAD_DIR>/converted/
```

This directory is created automatically when the first conversion is performed.

## Limitations

1. **Input Format:** Currently only PPTX files can be converted
2. **Image Quality:** PNG conversion uses basic text rendering (not high-fidelity slide images)
3. **Formatting:** Some complex slide layouts may not convert perfectly to PDF
4. **File Size:** Large presentations with many slides may take time to convert

## Future Enhancements

- [ ] Support for DOCX to PDF conversion
- [ ] High-fidelity slide rendering using LibreOffice
- [ ] Batch conversion of multiple files
- [ ] Conversion progress tracking
- [ ] Custom PDF styling options
- [ ] OCR for image-based slides

## Testing

Run the test script to verify the converter is working:

```bash
python api/test_converter.py
```

This will:
- Load the converter module
- Display available functions
- List any PPTX files in the uploads directory

## Example Usage

### Python API

```python
from api.services.document_converter import convert_document

# Convert PPTX to PDF
output_path = convert_document(
    input_path="slides.pptx",
    output_format="pdf",
    output_path="slides.pdf"
)

# Convert PPTX to images (creates directory)
output_dir = convert_document(
    input_path="slides.pptx",
    output_format="png",
    output_path="slides_images/"
)

# Convert PPTX to Markdown
output_path = convert_document(
    input_path="slides.pptx",
    output_format="md"
    # output_path auto-generated if not provided
)
```

### cURL API Examples

```bash
# Convert to PDF
curl -X POST http://localhost:5000/api/documents/<doc_id>/convert \
  -H "Content-Type: application/json" \
  -d '{"format": "pdf"}'

# Download converted file
curl -O http://localhost:5000/api/documents/<doc_id>/download/<filename>
```

## Troubleshooting

### Conversion Fails

**Issue:** "Unsupported input format"
- **Solution:** Only PPTX files are supported. Convert other formats to PPTX first.

**Issue:** "Font not found" errors in logs
- **Solution:** The system will fall back to default fonts. Install Arial or other TrueType fonts for better results.

**Issue:** Large file timeout
- **Solution:** Increase backend timeout settings for very large presentations.

### Download Issues

**Issue:** 404 on download
- **Solution:** Check that the conversion completed successfully. The file may have been cleaned up.

**Issue:** Invalid file path error
- **Solution:** This is a security check. Ensure the filename hasn't been tampered with.

## Security Considerations

- File paths are validated to prevent directory traversal attacks
- Only authenticated users can access conversion functionality
- Converted files are stored in a protected directory
- File size limits prevent DoS attacks

## Performance

Typical conversion times (estimates):
- **PDF:** ~2-5 seconds for 50 slides
- **PNG:** ~3-8 seconds for 50 slides
- **TXT:** ~1-2 seconds for 50 slides
- **MD:** ~1-2 seconds for 50 slides

Times vary based on slide complexity and system resources.
