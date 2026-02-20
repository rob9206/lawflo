# API Examples - Document Conversion

## REST API Examples

### 1. Convert PPTX to PDF

**Request:**
```bash
curl -X POST http://localhost:5000/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/convert \
  -H "Content-Type: application/json" \
  -d '{
    "format": "pdf"
  }'
```

**Response:**
```json
{
  "format": "pdf",
  "message": "Conversion successful",
  "download_url": "/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/download/858d0255-3a76-4f7d-8adf-ae618ef0d014.pdf"
}
```

### 2. Convert PPTX to PNG Images

**Request:**
```bash
curl -X POST http://localhost:5000/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/convert \
  -H "Content-Type: application/json" \
  -d '{
    "format": "png"
  }'
```

**Response:**
```json
{
  "format": "png",
  "message": "Converted to 15 images",
  "files": [
    "slide_001.png",
    "slide_002.png",
    "slide_003.png",
    "...",
    "slide_015.png"
  ],
  "download_url": "/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/converted/858d0255-3a76-4f7d-8adf-ae618ef0d014_slides"
}
```

### 3. Convert PPTX to Text

**Request:**
```bash
curl -X POST http://localhost:5000/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/convert \
  -H "Content-Type: application/json" \
  -d '{
    "format": "txt"
  }'
```

**Response:**
```json
{
  "format": "txt",
  "message": "Conversion successful",
  "download_url": "/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/download/858d0255-3a76-4f7d-8adf-ae618ef0d014.txt"
}
```

### 4. Convert PPTX to Markdown

**Request:**
```bash
curl -X POST http://localhost:5000/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/convert \
  -H "Content-Type: application/json" \
  -d '{
    "format": "md"
  }'
```

**Response:**
```json
{
  "format": "md",
  "message": "Conversion successful",
  "download_url": "/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/download/858d0255-3a76-4f7d-8adf-ae618ef0d014.md"
}
```

### 5. Download Converted File

**Request:**
```bash
curl -O http://localhost:5000/api/documents/858d0255-3a76-4f7d-8adf-ae618ef0d014/download/858d0255-3a76-4f7d-8adf-ae618ef0d014.pdf
```

**Response:**
```
Binary file download with proper Content-Disposition headers
```

## Python SDK Examples

### Basic Conversion

```python
from api.services.document_converter import convert_document

# Convert to PDF
pdf_path = convert_document(
    input_path="slides.pptx",
    output_format="pdf",
    output_path="slides.pdf"
)
print(f"PDF created: {pdf_path}")

# Convert to images
images_dir = convert_document(
    input_path="slides.pptx",
    output_format="png",
    output_path="slide_images/"
)
print(f"Images saved to: {images_dir}")

# Convert to text
text_path = convert_document(
    input_path="slides.pptx",
    output_format="txt"
    # Auto-generates output path
)
print(f"Text file: {text_path}")

# Convert to markdown
md_path = convert_document(
    input_path="slides.pptx",
    output_format="md"
)
print(f"Markdown file: {md_path}")
```

### Advanced Usage

```python
import os
from api.services.document_converter import (
    convert_pptx_to_pdf,
    convert_pptx_to_images,
    convert_pptx_to_text,
    convert_pptx_to_markdown
)

# Direct function calls for more control
input_file = "lecture_slides.pptx"

# PDF conversion
convert_pptx_to_pdf(input_file, "lecture.pdf")

# Image conversion with custom directory
output_dir = "lecture_slides"
os.makedirs(output_dir, exist_ok=True)
image_paths = convert_pptx_to_images(input_file, output_dir)
print(f"Created {len(image_paths)} images")

# Text extraction
convert_pptx_to_text(input_file, "lecture_notes.txt")

# Markdown conversion
convert_pptx_to_markdown(input_file, "lecture.md")
```

### Batch Conversion

```python
import os
from pathlib import Path
from api.services.document_converter import convert_document

# Convert all PPTX files in a directory to PDF
input_dir = Path("uploads")
output_dir = Path("converted")
output_dir.mkdir(exist_ok=True)

for pptx_file in input_dir.glob("*.pptx"):
    output_file = output_dir / f"{pptx_file.stem}.pdf"
    try:
        convert_document(
            str(pptx_file),
            "pdf",
            str(output_file)
        )
        print(f"✓ Converted: {pptx_file.name}")
    except Exception as e:
        print(f"✗ Failed: {pptx_file.name} - {e}")
```

## JavaScript/TypeScript Examples

### React Component Usage

```typescript
import { useState } from 'react';
import { convertDocument, downloadConvertedFile } from '@/api/converter';

function DocumentConverter({ docId }: { docId: string }) {
  const [converting, setConverting] = useState(false);

  const handleConvert = async (format: 'pdf' | 'png' | 'txt' | 'md') => {
    setConverting(true);
    try {
      const result = await convertDocument(docId, format);
      
      // Extract filename and trigger download
      if (result.download_url) {
        const filename = result.download_url.split('/').pop();
        if (filename) {
          const url = downloadConvertedFile(docId, filename);
          window.open(url, '_blank');
        }
      }
      
      alert(result.message);
    } catch (error: any) {
      alert(`Error: ${error.message}`);
    } finally {
      setConverting(false);
    }
  };

  return (
    <div>
      <button onClick={() => handleConvert('pdf')} disabled={converting}>
        {converting ? 'Converting...' : 'Convert to PDF'}
      </button>
      <button onClick={() => handleConvert('png')} disabled={converting}>
        Convert to Images
      </button>
      <button onClick={() => handleConvert('txt')} disabled={converting}>
        Convert to Text
      </button>
      <button onClick={() => handleConvert('md')} disabled={converting}>
        Convert to Markdown
      </button>
    </div>
  );
}
```

### Axios Direct Usage

```typescript
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

// Convert document
async function convertDoc(docId: string, format: string) {
  const response = await axios.post(
    `${API_BASE}/documents/${docId}/convert`,
    { format }
  );
  return response.data;
}

// Download converted file
async function downloadFile(docId: string, filename: string) {
  const url = `${API_BASE}/documents/${docId}/download/${filename}`;
  
  // Option 1: Open in new tab
  window.open(url, '_blank');
  
  // Option 2: Download with fetch
  const response = await fetch(url);
  const blob = await response.blob();
  const downloadUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(downloadUrl);
}

// Usage
(async () => {
  const docId = '858d0255-3a76-4f7d-8adf-ae618ef0d014';
  
  const result = await convertDoc(docId, 'pdf');
  console.log(result.message);
  
  const filename = result.download_url.split('/').pop();
  await downloadFile(docId, filename);
})();
```

## Error Handling Examples

### Python Error Handling

```python
from api.services.document_converter import convert_document

try:
    output = convert_document("presentation.pptx", "pdf")
    print(f"Success: {output}")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except ValueError as e:
    print(f"Invalid format or file type: {e}")
except Exception as e:
    print(f"Conversion error: {e}")
```

### API Error Responses

**Invalid Format:**
```json
{
  "error": "Invalid format. Allowed: pdf, png, txt, md",
  "status": 400
}
```

**Document Not Found:**
```json
{
  "error": "Document not found",
  "status": 404
}
```

**Unsupported File Type:**
```json
{
  "error": "Only PPTX files can be converted currently",
  "status": 400
}
```

**Conversion Failed:**
```json
{
  "error": "Conversion failed: [specific error message]",
  "status": 400
}
```

## Testing Examples

### Unit Test for Converter

```python
import unittest
import os
from api.services.document_converter import convert_document

class TestDocumentConverter(unittest.TestCase):
    def setUp(self):
        self.test_pptx = "test_slides.pptx"
        
    def test_convert_to_pdf(self):
        output = convert_document(self.test_pptx, "pdf", "test.pdf")
        self.assertTrue(os.path.exists(output))
        os.remove(output)
        
    def test_convert_to_images(self):
        output = convert_document(self.test_pptx, "png", "test_imgs/")
        self.assertTrue(os.path.isdir(output))
        # Cleanup
        for f in os.listdir(output):
            os.remove(os.path.join(output, f))
        os.rmdir(output)
        
    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            convert_document(self.test_pptx, "invalid")
            
    def test_invalid_file_type(self):
        with self.assertRaises(ValueError):
            convert_document("test.pdf", "pdf")

if __name__ == '__main__':
    unittest.main()
```

### Integration Test with Flask

```python
import unittest
import json
from api.app import app

class TestConversionAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.doc_id = "858d0255-3a76-4f7d-8adf-ae618ef0d014"
        
    def test_convert_to_pdf(self):
        response = self.client.post(
            f'/api/documents/{self.doc_id}/convert',
            data=json.dumps({'format': 'pdf'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['format'], 'pdf')
        self.assertIn('download_url', data)
        
    def test_invalid_format(self):
        response = self.client.post(
            f'/api/documents/{self.doc_id}/convert',
            data=json.dumps({'format': 'invalid'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
    def test_document_not_found(self):
        response = self.client.post(
            '/api/documents/invalid-id/convert',
            data=json.dumps({'format': 'pdf'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
```

## Performance Benchmarks

Approximate conversion times for a 50-slide presentation:

| Format | Size | Time | Notes |
|--------|------|------|-------|
| PDF | 1.2 MB | 2-3s | Depends on text amount |
| PNG | 15 files @ 100KB each | 5-7s | Basic text rendering |
| TXT | 50 KB | 1s | Fast extraction |
| MD | 60 KB | 1s | Fast with formatting |

## Tips and Best Practices

1. **Use appropriate format for your use case:**
   - PDF for sharing/printing
   - PNG for web display
   - TXT for analysis
   - MD for documentation

2. **Handle errors gracefully:**
   - Check file existence before conversion
   - Validate format parameters
   - Provide user feedback

3. **Clean up converted files periodically:**
   ```python
   import os
   import time
   
   converted_dir = "data/uploads/converted"
   max_age_days = 7
   
   for filename in os.listdir(converted_dir):
       filepath = os.path.join(converted_dir, filename)
       if os.path.isfile(filepath):
           age_days = (time.time() - os.path.getmtime(filepath)) / 86400
           if age_days > max_age_days:
               os.remove(filepath)
   ```

4. **Implement caching for repeated conversions:**
   ```python
   import hashlib
   
   def get_cache_key(file_path, format):
       with open(file_path, 'rb') as f:
           file_hash = hashlib.md5(f.read()).hexdigest()
       return f"{file_hash}_{format}"
   ```

5. **Add progress tracking for large files:**
   ```python
   from tqdm import tqdm
   
   # Wrap slide processing with progress bar
   for slide in tqdm(prs.slides, desc="Converting slides"):
       # Process slide
       pass
   ```
