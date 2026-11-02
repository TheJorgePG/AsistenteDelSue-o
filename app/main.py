from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from app.config import settings
from app.core.database import Base, engine
from app.models.user import UserModel
from app.models.sleep import SleepLogModel
from app.api.routes import router as api_router
from app.api.auth import router as auth_router

# Crea las tablas en PostgreSQL si no existen todavía
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# Registrar routers de la API y Autenticación en la app principal
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)

@app.get("/", response_class=HTMLResponse)
def home_frontend(request: Request):
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Asistente del Sueño - Auth & Gemini</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 h-screen flex flex-col justify-between">

        <!-- Header -->
        <header class="bg-slate-800 border-b border-slate-700 p-4 shadow-md flex justify-between items-center">
            <h1 class="text-xl font-bold flex items-center gap-2">
                🌙 Asistente del Sueño <span class="text-xs bg-indigo-600 text-white px-2 py-0.5 rounded-full font-mono">PostgreSQL + Gemini</span>
            </h1>
            <div id="user-info" class="text-sm text-slate-400 hidden flex items-center gap-3">
                <span id="user-email-display" class="text-indigo-400 font-medium"></span>
                <button onclick="cerrarSesion()" class="bg-red-600/80 hover:bg-red-600 text-white px-3 py-1 rounded-lg text-xs transition">Cerrar Sesión</button>
            </div>
        </header>

        <!-- SECCIÓN 1: PANTALLA DE LOGIN / REGISTRO (Visible si no hay sesión) -->
        <div id="auth-section" class="flex-1 flex items-center justify-center p-4">
            <div class="bg-slate-800 border border-slate-700 p-8 rounded-2xl max-w-md w-full shadow-xl">
                <div class="flex border-b border-slate-700 mb-6">
                    <button id="tab-login" onclick="cambiarTab('login')" class="flex-1 pb-3 text-center font-bold text-indigo-400 border-b-2 border-indigo-500 transition">Iniciar Sesión</button>
                    <button id="tab-register" onclick="cambiarTab('register')" class="flex-1 pb-3 text-center font-medium text-slate-400 hover:text-slate-200 transition">Registrarse</button>
                </div>

                <!-- Formulario -->
                <form id="auth-form" onsubmit="manejarAuth(event)" class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 mb-1 uppercase">Correo electrónico</label>
                        <input type="email" id="auth-email" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-slate-100" placeholder="tu@correo.com">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 mb-1 uppercase">Contraseña</label>
                        <input type="password" id="auth-password" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-slate-100" placeholder="••••••••">
                    </div>
                    <button type="submit" id="auth-btn" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-medium text-sm transition shadow-lg">
                        Iniciar Sesión
                    </button>
                    <p id="auth-error" class="text-red-400 text-xs text-center mt-2 hidden"></p>
                </form>
            </div>
        </div>

        <!-- SECCIÓN 2: APLICACIÓN PRINCIPAL / CHAT (Oculta hasta hacer login) -->
        <div id="app-section" class="flex-1 flex flex-col hidden overflow-hidden">
            <!-- Chat Container -->
            <main id="chat-container" class="flex-1 overflow-y-auto p-4 space-y-4 max-w-3xl w-full mx-auto">
                <div class="flex items-start gap-3">
                    <div class="bg-indigo-600 text-white rounded-full h-8 w-8 flex items-center justify-center font-bold shrink-0">AI</div>
                    <div class="bg-slate-800 p-4 rounded-2xl max-w-lg text-sm shadow border border-slate-700 leading-relaxed">
                        ¡Hola! Has iniciado sesión correctamente. Como tus datos están vinculados a tu cuenta, tus registros y consultas se guardarán de forma segura en PostgreSQL. ¿Cómo has dormido hoy?
                    </div>
                </div>
            </main>

            <!-- Input Area -->
            <footer class="bg-slate-800 border-t border-slate-700 p-4">
                <form id="chat-form" class="max-w-3xl mx-auto flex gap-2" onsubmit="enviarMensaje(event)">
                    <input type="text" id="user-input" placeholder="Ej: Dormí 7 horas y me desperté una vez..." class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-slate-100" required>
                    <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-medium text-sm transition shadow-lg shrink-0">Enviar</button>
                </form>
            </footer>
        </div>

        <!-- Script de Control Visual y de Sesión -->
        <script>
            let modoRegistro = false;
            let usuarioActual = null;

            function cambiarTab(tab) {
                const btnLogin = document.getElementById('tab-login');
                const btnRegister = document.getElementById('tab-register');
                const btnAuth = document.getElementById('auth-btn');
                const errorP = document.getElementById('auth-error');
                errorP.classList.add('hidden');

                if (tab === 'login') {
                    modoRegistro = false;
                    btnLogin.className = "flex-1 pb-3 text-center font-bold text-indigo-400 border-b-2 border-indigo-500 transition";
                    btnRegister.className = "flex-1 pb-3 text-center font-medium text-slate-400 hover:text-slate-200 transition";
                    btnAuth.innerText = "Iniciar Sesión";
                } else {
                    modoRegistro = true;
                    btnRegister.className = "flex-1 pb-3 text-center font-bold text-indigo-400 border-b-2 border-indigo-500 transition";
                    btnLogin.className = "flex-1 pb-3 text-center font-medium text-slate-400 hover:text-slate-200 transition";
                    btnAuth.innerText = "Registrarse";
                }
            }

            async function manejarAuth(e) {
                e.preventDefault();
                const email = document.getElementById('auth-email').value;
                const password = document.getElementById('auth-password').value;
                const errorP = document.getElementById('auth-error');
                errorP.classList.add('hidden');

                const endpoint = modoRegistro ? '/api/v1/auth/register' : '/api/v1/auth/login';

                try {
                    const res = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, password })
                    });
                    const data = await res.json();

                    if (!res.ok) {
                        throw new Error(data.detail || 'Ocurrió un error en la autenticación');
                    }

                    if (modoRegistro) {
                        alert('¡Registro exitoso! Ahora inicia sesión.');
                        cambiarTab('login');
                    } else {
                        usuarioActual = email;
                        document.getElementById('auth-section').classList.add('hidden');
                        document.getElementById('app-section').classList.remove('hidden');
                        document.getElementById('user-info').classList.remove('hidden');
                        document.getElementById('user-email-display').innerText = email;
                    }
                } catch (err) {
                    errorP.innerText = err.message;
                    errorP.classList.remove('hidden');
                }
            }

            function cerrarSesion() {
                usuarioActual = null;
                document.getElementById('app-section').classList.add('hidden');
                document.getElementById('user-info').classList.add('hidden');
                document.getElementById('auth-section').classList.remove('hidden');
                document.getElementById('auth-email').value = '';
                document.getElementById('auth-password').value = '';
            }

            async function enviarMensaje(e) {
                e.preventDefault();
                const input = document.getElementById('user-input');
                const container = document.getElementById('chat-container');
                const text = input.value.trim();
                if(!text) return;

                container.innerHTML += `
                    <div class="flex items-start gap-3 justify-end">
                        <div class="bg-indigo-600 p-3 rounded-2xl max-w-lg text-sm shadow text-white">${text}</div>
                        <div class="bg-slate-700 text-white rounded-full h-8 w-8 flex items-center justify-center font-bold shrink-0">U</div>
                    </div>
                `;
                input.value = '';
                container.scrollTop = container.scrollHeight;

                const loadingId = 'loading-' + Date.now();
                container.innerHTML += `
                    <div id="${loadingId}" class="flex items-start gap-3">
                        <div class="bg-indigo-600 text-white rounded-full h-8 w-8 flex items-center justify-center font-bold shrink-0">AI</div>
                        <div class="bg-slate-800 p-3 rounded-2xl text-sm shadow animate-pulse border border-slate-700 text-indigo-400">Analizando con Gemini y guardando en PostgreSQL...</div>
                    </div>
                `;
                container.scrollTop = container.scrollHeight;

                try {
                    const res = await fetch('/api/v1/ai/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ pregunta: text, sensaciones_diarias: "Usuario: " + usuarioActual })
                    });
                    const data = await res.json();
                    
                    document.getElementById(loadingId).remove();

                    container.innerHTML += `
                        <div class="flex items-start gap-3">
                            <div class="bg-indigo-600 text-white rounded-full h-8 w-8 flex items-center justify-center font-bold shrink-0">AI</div>
                            <div class="bg-slate-800 p-4 rounded-2xl max-w-xl text-sm shadow whitespace-pre-wrap border border-slate-700 leading-relaxed">${data.respuesta_asistente || data.detail}</div>
                        </div>
                    `;
                } catch (err) {
                    document.getElementById(loadingId).remove();
                    container.innerHTML += `<div class="text-red-400 text-sm p-2">Error de conexión.</div>`;
                }
                container.scrollTop = container.scrollHeight;
            }
        </script>
    </body>
    </html>
    """