import os
from pypdf import PdfReader

class PDFParserService:
    def __init__(self, pdf_path: str = "app/data/documento_sueno.pdf"):
        self.pdf_path = pdf_path

    def extract_text(self) -> str:
        """Extrae todo el texto del PDF de recomendaciones de sueño."""
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"No se encontró el archivo PDF en la ruta: {self.pdf_path}")
        
        try:
            reader = PdfReader(self.pdf_path)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            return full_text
        except Exception as e:
            raise RuntimeError(f"Error al procesar el archivo PDF: {str(e)}")