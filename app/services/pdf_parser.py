import os
from pypdf import PdfReader

class PDFParserService:
    def __init__(self, pdf_path: str = "app/data/documento_sueno.pdf"):
        self.pdf_path = pdf_path

    def extract_pages(self) -> list[str]:
        """Extrae el texto página a página para conservar la referencia de origen."""
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"No se encontró el archivo PDF en la ruta: {self.pdf_path}")
        
        try:
            reader = PdfReader(self.pdf_path)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                pages.append(text or "")
            return pages
        except Exception as e:
            raise RuntimeError(f"Error al procesar el archivo PDF: {str(e)}")

    def extract_text(self) -> str:
        """Extrae el texto completo del PDF."""
        return "\n".join(self.extract_pages())