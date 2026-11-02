import os
import google.generativeai as genai
from app.services.pdf_parser import PDFParserService

class AIAssistantService:
    def __init__(self):
        # Configurar la API key de Gemini desde las variables de entorno
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        
        # Cargar el texto del PDF para inyectarlo como contexto (RAG)
        try:
            parser = PDFParserService(pdf_path="app/data/documento_sueno.pdf")
            self.pdf_context = parser.extract_text()
        except Exception:
            self.pdf_context = "Información básica sobre higiene del sueño y descanso óptimo."

        self.model = genai.GenerativeModel("gemini-3.8-flash")

    def consultar_asistente(self, pregunta_usuario: str, datos_sueno_usuario: str = "") -> str:
        """
        Genera una respuesta utilizando Gemini basada en el PDF y el estado del usuario.
        """
        prompt = f"""
        Eres un asistente inteligente y entrenador personal experto en salud del sueño.
        Tu objetivo es ayudar al usuario a mejorar su descanso, analizar sus hábitos, 
        prevenir fatiga o síntomas de enfermedad y ofrecer pautas basadas en la siguiente guía científica:
        
        --- INICIO DE LA GUÍA DE REFERENCIA (PDF) ---
        {self.pdf_context}
        --- FIN DE LA GUÍA ---

        Datos del usuario / sensaciones diarias: {datos_sueno_usuario}
        Pregunta del usuario: {pregunta_usuario}

        Responde de manera empática, profesional, directa y personalizada en español.
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error al conectar con la Inteligencia Artificial de Gemini: {str(e)}"