import json
import os
import hashlib
import qrcode
from io import BytesIO
import base64
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="DIGEMIG - Ecosistema Digital Completo")

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/archivos", StaticFiles(directory="static"), name="archivos")

# ------------------------------------------------------------------
# CONFIGURACIÓN DE LA IA (GROQ)
# ------------------------------------------------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODELO_IA = "llama-3.3-70b-versatile"

# ------------------------------------------------------------------
# VALORES FIJOS DE CONVERSIÓN
# ------------------------------------------------------------------
UFV_A_BS = 2.25
USD_A_BS = 6.96

# ------------------------------------------------------------------
# LISTAS DE PAÍSES POR GRUPO (según normativa DIGEMIG)
# ------------------------------------------------------------------
GRUPO_I = {
    "América": ["Argentina", "Bahamas", "Barbados", "Belice", "Brasil", "Canadá", "Chile", "Colombia", "Costa Rica", "Ecuador", "Estados Unidos", "Puerto Rico", "Jamaica", "México", "Panamá", "Paraguay", "Perú", "República Dominicana", "Uruguay", "Venezuela"],
    "Europa": ["Alemania", "Andorra", "Austria", "Bélgica", "Bulgaria", "Chipre", "Croacia", "Dinamarca", "Eslovaquia", "Eslovenia", "España", "Estonia", "Finlandia", "Francia", "Grecia", "Hungría", "Irlanda", "Islandia", "Italia", "Letonia", "Liechtenstein", "Lituania", "Luxemburgo", "Malta", "Mónaco", "Noruega", "Países Bajos", "Polonia", "Portugal", "Reino Unido", "República Checa", "Rumania", "Suecia", "Suiza", "Turquía", "Vaticano"],
    "Asia/Oceanía/África": ["Australia", "Corea del Sur", "Filipinas", "Israel", "Japón", "Nueva Zelanda", "Palestina", "Sudáfrica"]
}
GRUPO_II = {
    "América": ["Antigua y Barbuda", "Cuba", "Dominica", "El Salvador", "Granada", "Guatemala", "Guyana", "Haití", "Honduras", "San Cristóbal y Nieves", "San Vicente y las Granadinas", "Santa Lucía", "Surinam", "Trinidad y Tobago"],
    "Europa": ["Albania", "Armenia", "Azerbaiyán", "Bielorrusia", "Bosnia y Herzegovina", "Georgia", "Macedonia del Norte", "Montenegro", "Rusia", "Serbia", "Ucrania"],
    "Asia": ["Arabia Saudita", "Baréin", "Bangladés", "Brunéi", "China", "Taiwán", "Emiratos Árabes Unidos", "India", "Kazajistán", "Kirguistán", "Kuwait", "Malasia", "Maldivas", "Mongolia", "Myanmar", "Omán", "Qatar", "Singapur", "Sri Lanka", "Tailandia", "Tayikistán", "Turkmenistán", "Uzbekistán", "Vietnam"],
    "África": ["Argelia", "Benín", "Botsuana", "Burkina Faso", "Burundi", "Cabo Verde", "Camerún", "Comoras", "Costa de Marfil", "Egipto", "Eritrea", "Etiopía", "Gabón", "Gambia", "Ghana", "Guinea", "Guinea-Bisáu", "Guinea Ecuatorial", "Kenia", "Lesoto", "Liberia", "Madagascar", "Malaui", "Mali", "Marruecos", "Mauricio", "Mauritania", "Mozambique", "Namibia", "Níger", "República Centroafricana", "República del Congo", "Ruanda", "Santo Tomé y Príncipe", "Senegal", "Seychelles", "Sierra Leona", "Suazilandia", "Tanzania", "Togo", "Túnez", "Uganda", "Yibuti", "Zambia", "Zimbabue"],
    "Oceanía": ["Fiyi", "Islas Marshall", "Islas Salomón", "Kiribati", "Micronesia", "Nauru", "Palaos", "Papúa Nueva Guinea", "Samoa", "Tonga", "Tuvalu", "Vanuatu"]
}
GRUPO_III = {
    "Asia": ["Afganistán", "Bután", "Camboya", "Irak", "Irán", "Laos", "Líbano", "Nepal", "Pakistán", "Siria", "Yemen", "Corea del Norte"],
    "África": ["Angola", "Chad", "Libia", "Nigeria", "República Democrática del Congo", "Somalia", "Sudán", "Sudán del Sur"]
}

def obtener_grupo_pais(pais: str) -> int:
    pais_lower = pais.lower().strip()
    for sublist in GRUPO_I.values():
        for p in sublist:
            if p.lower() == pais_lower:
                return 1
    for sublist in GRUPO_II.values():
        for p in sublist:
            if p.lower() == pais_lower:
                return 2
    for sublist in GRUPO_III.values():
        for p in sublist:
            if p.lower() == pais_lower:
                return 3
    return 2  # Por defecto Grupo II

def calcular_costo_ingreso(pais: str, tipo_ingreso: str = "terrestre") -> dict:
    grupo = obtener_grupo_pais(pais)
    tasa_ufv = 30 if tipo_ingreso == "terrestre" else 100
    tasa_bs = tasa_ufv * UFV_A_BS
    if grupo == 1:
        arancel_ufv = 0
        arancel_bs = 0
        arancel_usd = 0
        desc = "No requiere visa, ingreso libre. Solo paga tasa administrativa en frontera."
    elif grupo == 2:
        arancel_ufv = 300
        arancel_bs = arancel_ufv * UFV_A_BS
        arancel_usd = round(arancel_bs / USD_A_BS, 2)
        desc = "Visa on arrival (paga en frontera). Arancel: 300 UFV."
    else:
        arancel_ufv = 90
        arancel_bs = arancel_ufv * UFV_A_BS
        arancel_usd = round(arancel_bs / USD_A_BS, 2)
        desc = "Visa consular obligatoria (aprobación previa de DIGEMIG). Costo de solicitud: 30 USD (aprox 208.80 Bs). Además paga tasa en frontera."
    total_bs = arancel_bs + tasa_bs
    total_usd = round(total_bs / USD_A_BS, 2)
    return {
        "grupo": grupo,
        "arancel_ufv": arancel_ufv,
        "arancel_bs": round(arancel_bs, 2),
        "arancel_usd": arancel_usd,
        "tasa_ufv": tasa_ufv,
        "tasa_bs": round(tasa_bs, 2),
        "total_bs": round(total_bs, 2),
        "total_usd": total_usd,
        "descripcion": desc
    }

def calcular_costo_salida(tipo_usuario: str) -> dict:
    if tipo_usuario == "boliviano":
        total_bs = 26.0
        total_usd = round(total_bs / USD_A_BS, 2)
        desc = "Tasa de salida para ciudadano boliviano: 26 Bs (fijo)."
    else:
        ufv = 70
        total_bs = ufv * UFV_A_BS
        total_usd = round(total_bs / USD_A_BS, 2)
        desc = f"Tasa de salida para residente extranjero legal: {ufv} UFV = {total_bs:.2f} Bs = {total_usd:.2f} USD."
    return {"total_bs": total_bs, "total_usd": total_usd, "descripcion": desc}

# ------------------------------------------------------------------
# FUNCIONES DE TRÁMITES (costos directos)
# ------------------------------------------------------------------
def tramite_pasaporte():
    total_bs = 200.0 + (155 * UFV_A_BS)
    total_usd = round(total_bs / USD_A_BS, 2)
    return {"total_bs": total_bs, "total_usd": total_usd, "costo_bs": 200.0, "costo_ufv": 155}

def tramite_tripulante():
    total_bs = 100 * UFV_A_BS
    total_usd = round(total_bs / USD_A_BS, 2)
    return {"total_bs": total_bs, "total_usd": total_usd}

def tramite_arraigo():
    total_bs = 110 * UFV_A_BS
    total_usd = round(total_bs / USD_A_BS, 2)
    return {"total_bs": total_bs, "total_usd": total_usd}

# ------------------------------------------------------------------
# BASE DE DATOS DE EXPEDIENTES (5 ciudadanos ejemplo)
# ------------------------------------------------------------------
DB_SISTEMA = {
    "ARG123": {"nombres": "Carlos", "apellidos": "Mendizabal Ortega", "pais": "ARGENTINA", "grupo": "Grupo 1", "tramite": "Radicatoria Temporal", "arancel": 0.0, "tasa": 30.0, "pdf": "/archivos/Expediente_ARG123.pdf"},
    "USA999": {"nombres": "Michael", "apellidos": "Smith Johnson", "pais": "ESTADOS UNIDOS", "grupo": "Grupo 3", "tramite": "Visa de Turismo", "arancel": 1113.60, "tasa": 30.0, "pdf": "/archivos/Expediente_USA999.pdf"},
    "ESP444": {"nombres": "Javier", "apellidos": "Gomez Ruiz", "pais": "ESPANA", "grupo": "Grupo 1", "tramite": "Ingreso Aero", "arancel": 0.0, "tasa": 100.0, "pdf": "/archivos/Expediente_ESP444.pdf"},
    "BRA222": {"nombres": "Luciana", "apellidos": "Silva Ferreira", "pais": "BRASIL", "grupo": "Grupo 1", "tramite": "Residencia Mercosur", "arancel": 0.0, "tasa": 30.0, "pdf": "/archivos/Expediente_BRA222.pdf"},
    "CHI333": {"nombres": "Diego", "apellidos": "Valdes Jara", "pais": "CHILE", "grupo": "Grupo 1", "tramite": "Transito Vecinal", "arancel": 0.0, "tasa": 30.0, "pdf": "/archivos/Expediente_CHI333.pdf"}
}

def calcular_hash_pdf(ruta_relativa):
    ruta_fisica = ruta_relativa.lstrip("/")
    if os.path.exists(ruta_fisica):
        with open(ruta_fisica, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    return "NO_DISPONIBLE (crea el PDF)"

hashes_pdf = {doc_id: calcular_hash_pdf(info["pdf"]) for doc_id, info in DB_SISTEMA.items()}

# ------------------------------------------------------------------
# HTML DEL PORTAL (operador)
# ------------------------------------------------------------------
HTML_PORTAL = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DIGEMIG - Monitor de Control Interno</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-100 font-sans min-h-screen flex flex-col">
    <header class="bg-gray-800 border-b border-gray-700 p-4 shadow-lg">
        <div class="container mx-auto flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <div class="bg-blue-600 p-2 rounded text-white font-bold text-sm tracking-widest">DIGEMIG</div>
                <h1 class="text-xl font-semibold tracking-tight text-gray-200">Ecosistema de Gestion Documental e Integridad Financiera</h1>
            </div>
            <div class="space-x-4">
                <a href="/" class="text-xs bg-blue-700 hover:bg-blue-600 px-3 py-1.5 rounded font-bold transition">Ventanilla de Control</a>
                <a href="/chatbot" class="text-xs bg-green-700 hover:bg-green-600 px-3 py-1.5 rounded font-bold transition">Abrir Portal Pre-Registro (IA)</a>
            </div>
        </div>
    </header>
    <main class="flex-grow container mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="space-y-6 lg:col-span-1">
            <div class="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
                <h2 class="text-sm font-bold text-blue-400 mb-4 uppercase tracking-widest">Consulta de Repositorio Retrospectivo</h2>
                <form action="/buscar" method="post" class="space-y-4">
                    <input type="text" name="documento" placeholder="Ej: ARG123" required class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-gray-200 font-mono">
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 rounded-lg text-sm transition">BUSCAR REGISTRO MIGRATORIO</button>
                </form>
            </div>
            <div class="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
                <h2 class="text-sm font-bold text-yellow-500 mb-4 uppercase tracking-widest">Escaner de Validacion Inmutable (QR)</h2>
                <form action="/escanear-qr" method="post" class="space-y-4">
                    <textarea name="qr_payload" rows="4" required class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-[11px] font-mono text-green-400">{{"nacionalidad": "S/D", "arancel_visa_bs": 0.0, "total_autorizado_bs": 0.0, "estado": "NO COMPROBADO"}}</textarea>
                    <button type="submit" class="w-full bg-yellow-600 hover:bg-yellow-700 text-gray-900 font-bold py-2.5 rounded-lg text-sm transition">VALIDAR INTEGRIDAD ARANCELARIA</button>
                </form>
            </div>
        </div>
        <div class="lg:col-span-2 space-y-6">
            {alerta_sistema}
            <div class="bg-gray-800 border border-gray-700 rounded-xl p-8 min-h-[440px]">
                <div class="border-b border-gray-700 pb-4 mb-6 flex justify-between">
                    <h2 class="text-xl font-bold text-gray-100">Monitor de Control en Fronteras</h2>
                    <span class="text-[10px] px-3 py-1 rounded-full font-mono font-bold {status_color_bg} {status_color_text}">{status_texto}</span>
                </div>
                {contenido_dinamico}
            </div>
        </div>
    </main>
</body>
</html>
"""

# ------------------------------------------------------------------
# HTML DEL CHATBOT (con Enter, clip, y QR automático)
# ------------------------------------------------------------------
HTML_CHATBOT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DIGEMIG - Portal de Pre-Registro Movil</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-800 h-screen flex justify-center items-center font-sans">
    <div class="w-full max-w-md bg-white h-[92vh] rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col border-[8px] border-gray-900 relative">
        <div class="bg-[#0b5345] text-white p-5 pt-8 flex items-center space-x-3 shadow-md">
            <div class="w-10 h-10 bg-white rounded-full flex items-center justify-center text-[#0b5345] font-black text-xl">D</div>
            <div>
                <h2 class="font-bold leading-tight text-sm">DIGEMIG - Pre-Registro Fronterizo</h2>
                <p class="text-[10px] text-green-200 uppercase tracking-widest">Asistente Migratorio IA</p>
            </div>
        </div>
        <div id="chat-box" class="flex-grow bg-[#ece5dd] p-4 overflow-y-auto space-y-4"></div>
        <div class="p-3 bg-gray-100 border-t border-gray-300 flex items-center space-x-2">
            <button onclick="simularCargaDocumentos()" class="text-gray-500 hover:text-[#0b5345] transition p-2 bg-gray-200 rounded-full cursor-pointer">
                <svg class="w-5 h-5 transform rotate-45" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
            </button>
            <button onclick="generarQRManual()" class="text-gray-500 hover:text-blue-700 transition p-2 bg-gray-200 rounded-full cursor-pointer">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
            </button>
            <input type="text" id="user-input" placeholder="Escribe tu consulta..." class="flex-grow bg-white border border-gray-300 rounded-full px-4 py-2 text-sm outline-none focus:border-[#0b5345]">
            <button onclick="enviarMensajeServidor()" class="bg-[#0b5345] w-10 h-10 rounded-full flex justify-center items-center text-white hover:bg-[#0e6655] shadow-md">
                <svg class="w-4 h-4 transform rotate-45 -mt-1 -mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
            </button>
        </div>
    </div>
    <script>
        window.onload = () => {
            agregarMensaje("👋 ¡Hola! Soy el asistente digital de DIGEMIG. Dime tu nacionalidad (boliviano o extranjero) para ayudarte mejor.", 'bot');
            document.getElementById("user-input").addEventListener("keypress", function(e) {
                if (e.key === "Enter") {
                    e.preventDefault();
                    enviarMensajeServidor();
                }
            });
        };
        async function enviarMensajeServidor() {
            const input = document.getElementById("user-input");
            const txt = input.value.trim();
            if (!txt) return;
            agregarMensaje(txt, 'user');
            input.value = '';
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: new URLSearchParams({'mensaje': txt})
                });
                const data = await response.json();
                agregarMensaje(data.respuesta, 'bot');
            } catch(e) { agregarMensaje("❌ Error de conexión. Intenta de nuevo.", 'bot'); }
        }
        function agregarMensaje(text, sender) {
            const chatBox = document.getElementById("chat-box");
            const div = document.createElement("div");
            div.className = sender === 'user' ? "flex justify-end w-full" : "flex justify-start w-full";
            const bubble = sender === 'user' ? "bg-[#0b5345] text-white p-3 rounded-xl max-w-[85%] text-sm" : "bg-white border p-3 rounded-xl max-w-[85%] text-sm whitespace-pre-wrap";
            div.innerHTML = `<div class="${bubble}">${text}</div>`;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        function simularCargaDocumentos() {
            const input = document.getElementById("user-input");
            input.value = "Adjunto mis documentos escaneados (simulación)";
            enviarMensajeServidor();
        }
        async function generarQRManual() {
            // Obtener el último mensaje del bot en el chat
            const chatBox = document.getElementById("chat-box");
            const botMessages = chatBox.querySelectorAll(".flex.justify-start .whitespace-pre-wrap");
            if (botMessages.length === 0) {
                agregarMensaje("❌ No hay información para generar el QR. Primero conversa con el asistente.", 'bot');
                return;
            }
            const lastBotMessage = botMessages[botMessages.length - 1].innerText;
            
            // Extraer nacionalidad y monto del texto
            let nacionalidad = "";
            let monto = 0;
            
            // Buscar nacionalidad (prioriza "boliviano")
            if (lastBotMessage.match(/\\bboliviano\\b/i)) {
                nacionalidad = "Bolivia";
            } else {
                const matchNac = lastBotMessage.match(/(?:de|de la|desde)\\s+([A-Za-záéíóúñü\\s]+?)(?:\\s|,|\\.|$)/i);
                if (matchNac && matchNac[1]) {
                    nacionalidad = matchNac[1].trim();
                } else {
                    nacionalidad = prompt("No detecté tu nacionalidad. Escríbela:", "Bolivia");
                    if (!nacionalidad) return;
                }
            }
            
            // Buscar monto (números seguidos de "Bs", "bolivianos", etc.)
            const matchMonto = lastBotMessage.match(/(\\d+(?:\\.\\d+)?)\\s*(?:Bs|bolivianos|USD|dólares)/i);
            if (matchMonto) {
                monto = parseFloat(matchMonto[1]);
            } else {
                monto = parseFloat(prompt("¿Cuál es el monto total en Bs? (puedes poner 0)", "0"));
                if (isNaN(monto)) monto = 0;
            }
            
            // Llamar al backend para generar el QR
            const formData = new FormData();
            formData.append("nacionalidad", nacionalidad);
            formData.append("tramite", "Trámite migratorio");
            formData.append("monto", monto.toString());
            
            try {
                const response = await fetch("/generar-qr", { method: "POST", body: formData });
                const data = await response.json();
                if (data.qr_image) {
                    agregarMensaje(`<img src="data:image/png;base64,${data.qr_image}" class="w-40 h-40 mx-auto my-2 border-2 border-black rounded-lg"/>`, 'bot');
                    agregarMensaje(`📱 Código QR generado para ${nacionalidad} (${monto} Bs). Preséntalo en ventanilla con tus documentos originales.`, 'bot');
                } else {
                    agregarMensaje("❌ Error generando QR", 'bot');
                }
            } catch(e) {
                agregarMensaje("❌ Error de red. Intenta de nuevo.", 'bot');
            }
        }
    </script>
</body>
</html>
"""

# ------------------------------------------------------------------
# MEMORIA DE CONVERSACIÓN (para mantener contexto)
# ------------------------------------------------------------------
conversacion_por_sesion = {}

# ------------------------------------------------------------------
# PROMPT DEL SISTEMA (con referencias a las listas y reglas)
# ------------------------------------------------------------------
PROMPT_SISTEMA = f"""
Eres el asistente virtual oficial de DIGEMIG Bolivia. Tu trabajo es mantener una conversación natural, inteligente y útil.

INSTRUCCIONES CLAVE:

1. **Nacionalidad del usuario**: Presta atención cuando el usuario diga "soy de La Paz", "soy boliviano", "soy ciudadano boliviano", "soy de Bolivia", etc. Eso significa que es BOLIVIANO. No lo confundas con un extranjero aunque mencione otro país después.

2. **Si el usuario es boliviano**:
   - **SALIDA DE BOLIVIA**: Si quiere viajar al exterior (concierto, turismo, etc.), solo debes informar la **tasa de salida de Bolivia**, que es de **26 Bs (fijo, no se expresa en UFV)**. NO menciones tasas de ingreso de otros países (como Chile, Argentina, Perú, etc.). Esas las cobra el otro país y no son competencia de DIGEMIG.
   - **FRONTERAS RECOMENDADAS** (solo orientación): hacia Chile → Colchane o Tambo Quemado; hacia Perú → Desaguadero o Copacabana; hacia Argentina → Villazón o La Quiaca; hacia Brasil → Puerto Suárez o Cobija.
   - **TRÁMITES DENTRO DE BOLIVIA** (pasaporte, arraigo, tripulante): 
     * Pasaporte: 200 Bs + 155 UFV (1 UFV = 2.25 Bs) = 548.75 Bs ≈ 78.84 USD.
     * Tripulante terrestre: primera vez 100 UFV = 225 Bs ≈ 32.33 USD; renovación sin costo.
     * Arraigo: 110 UFV = 247.50 Bs ≈ 35.56 USD.
   - **PROCESO DIGITAL**: Puede hacer pre-registro subiendo su cédula escaneada con el botón de clip. En 24h se genera un QR. Luego solo presenta su cédula original y el QR en la frontera para verificación rápida (sin filas).
   - Siempre ofrece generar el QR con el botón "+" al final.

3. **Si el usuario es extranjero** (dice "soy de China", "soy de Chile", etc.):
   - Clasifica según las listas de GRUPO I, II, III (ver más abajo).
   - Solo informas los costos de **ingreso a Bolivia** (arancel + tasa administrativa), que se expresan en UFV y su equivalente en Bs y USD.
   - Si pregunta por presupuesto de estadía o lugares turísticos, puedes dar estimados generales (800-1200 USD para 2 semanas, alojamiento 30-60 USD/noche, comidas 10-20 USD/día, entradas 5-15 USD, Carnaval de Oruro entrada 50-150 USD).
   - Recomienda lugares: Salar de Uyuni, Lago Titicaca, Tiwanaku, La Paz (teleférico), Potosí, Sucre, Santa Cruz.
   - El proceso digital para extranjeros es el mismo: subir documentos escaneados (pasaporte, vacuna, solvencia) con el botón de clip, 24h → QR, luego solo presenta originales en frontera.
   - Siempre ofrece generar el QR con el botón "+".

4. **Formato de respuesta**: Usa un tono amable, cercano y profesional. No uses respuestas prefabricadas. Adáptate a la pregunta. Si no entiendes algo, pide aclaración.

5. **Listas de grupos para extranjeros (ingreso a Bolivia)**:
   - GRUPO I (exentos de visa, solo pagan tasa): {list(GRUPO_I.values())}
   - GRUPO II (visa on arrival, arancel 300 UFV + tasa): {list(GRUPO_II.values())}
   - GRUPO III (visa consular previa, arancel 90 UFV + tasa): {list(GRUPO_III.values())}

6. **REQUISITOS DETALLADOS PARA CIUDADANOS BOLIVIANOS AL VIAJAR A LOS PAÍSES DEL MERCOSUR Y CAN** (información completa, similar al nivel de detalle de Chile):

   **🇨🇱 CHILE**
   - Documento de identidad: Cédula de identidad boliviana vigente (suficiente). Si viajas con pasaporte, este debe tener al menos 6 meses de validez.
   - Declaración Jurada SAG: Obligatoria en línea para declarar productos de origen vegetal o animal.
   - Pasaje de regreso: Fundamental contar con un pasaje de salida de Chile (hacia Bolivia u otro país).
   - Solvencia económica: Debes poder demostrar que cuentas con los medios económicos para tu estadía (aprox. $45 USD por día).
   - Alojamiento: Útil tener una reserva de hotel o una carta de invitación notariada.
   - Nota: Si tu viaje incluye una escala en un país fuera del Mercosur, el pasaporte será obligatorio.

   **🇦🇷 ARGENTINA**
   - Documento de identidad: Cédula de identidad boliviana vigente (suficiente). El pasaporte no es necesario.
   - Visa: No requiere visa para turismo (estadía hasta 90 días, prorrogable).
   - Seguro médico: OBLIGATORIO desde mediados de 2025 (debes contratar un seguro de viaje con cobertura médica internacional para toda la estadía).
   - Pasaje de regreso: Exigen comprobante de salida de Argentina (boleto de avión, bus, etc.).
   - Solvencia económica: Demostrar medios económicos (aproximadamente $50 USD por día o su equivalente en pesos argentinos).
   - Alojamiento: Reserva de hotel o carta de invitación (si es de un residente, debe estar certificada ante escribano argentino).
   - Vacunas: No se exige ninguna vacuna específica para ingresar desde Bolivia, pero se recomienda tener la fiebre amarilla si se viaja a zonas selváticas.

   **🇧🇷 BRASIL**
   - Documento de identidad: Cédula de identidad boliviana vigente (suficiente). El pasaporte no es necesario.
   - Visa: No requiere visa para turismo (hasta 90 días, prorrogable).
   - Pasaje de regreso: Obligatorio presentar boleto de salida de Brasil.
   - Solvencia económica: Se recomienda llevar comprobantes (efectivo, tarjeta, extracto bancario). Estimado $40-50 USD por día.
   - Alojamiento: Reserva de hotel o carta de invitación (no es estrictamente obligatoria, pero ayuda).
   - Vacunas: La fiebre amarilla es obligatoria si visitas estados como Amazonas, Mato Grosso, etc. Debes llevar el certificado internacional.
   - Registro migratorio: Al ingresar, se te entregará un comprobante de entrada (Tarjeta de Entrada y Salida). Consérvalo para salir.

   **🇵🇾 PARAGUAY**
   - Documento de identidad: Cédula de identidad boliviana vigente (suficiente).
   - Visa: No requiere visa para turismo (hasta 90 días).
   - Vacuna fiebre amarilla: OBLIGATORIA para todos los viajeros que ingresen por vía terrestre o aérea. Debes presentar el Certificado Internacional de Vacunación.
   - Pasaje de regreso: Exigen comprobante de salida.
   - Solvencia económica: Se pide demostrar medios económicos (efectivo, tarjeta). Estimado $35-45 USD por día.
   - Alojamiento: Reserva de hotel o carta de invitación (recomendable).
   - Seguro médico: No es obligatorio, pero se sugiere.

   **🇺🇾 URUGUAY**
   - Documento de identidad: Cédula de identidad boliviana vigente (suficiente).
   - Visa: No requiere visa para turismo (hasta 90 días).
   - Pasaje de regreso: Obligatorio.
   - Solvencia económica: Demostrar medios económicos. Estimado $50-60 USD por día.
   - Alojamiento: Reserva de hotel o carta de invitación notariada (si es de un residente).
   - Vacunas: No se exigen vacunas específicas, pero se recomienda fiebre amarilla si se viaja desde zona de riesgo.
   - Seguro médico: No obligatorio, pero recomendable.

   **🇨🇴 COLOMBIA**
   - Documento de identidad: Cédula de identidad boliviana vigente (suficiente, gracias a la CAN).
   - Visa: No requiere visa para turismo (hasta 90 días).
   - Declaración de ingreso: Debes llenar el formulario de migración online "Check-Mig" dentro de las 24 horas previas al vuelo (obligatorio).
   - Pasaje de regreso: Exigen comprobante de salida.
   - Solvencia económica: Se recomienda demostrar medios económicos (al menos $500 USD para la estadía).
   - Alojamiento: Reserva de hotel o carta de invitación.
   - Vacunas: La fiebre amarilla es obligatoria si visitas parques naturales o zonas selváticas (Amazonas, Leticia, etc.). Lleva el certificado.
   - Seguro médico: No obligatorio, pero muy recomendado.

   **🇪🇨 ECUADOR**
   - Documento de identidad: Cédula de identidad boliviana vigente (suficiente, gracias a la CAN).
   - Visa: No requiere visa (estadía hasta 90 días).
   - Declaración jurada: Debes llenar el formulario "Declaración de Salud del Viajero" (DSV) online antes del viaje.
   - Pasaje de regreso: Obligatorio.
   - Solvencia económica: Demostrar medios económicos (aproximadamente $50 USD por día).
   - Alojamiento: Reserva de hotel o carta de invitación.
   - Vacunas: La fiebre amarilla es obligatoria si visitas la Amazonía o zonas de riesgo. Presentar certificado.
   - Seguro médico: No obligatorio, pero recomendable.
   - Nota especial: A partir de septiembre 2025, Ecuador exige visa de tránsito a ciudadanos que requieren visa para ingresar, pero los bolivianos siguen exentos.

   **🇵🇪 PERÚ**
   - Documento de identidad: Cédula de identidad boliviana vigente (suficiente, gracias a la CAN).
   - Visa: No requiere visa (hasta 90 días).
   - Declaración jurada: Pueden pedir el formulario "Declaración Jurada de Salud y Aduanas" (online o al llegar).
   - Pasaje de regreso: Exigen comprobante de salida, especialmente si viajas por avión.
   - Solvencia económica: Se recomienda llevar efectivo o tarjeta. Estimado $40 USD por día.
   - Alojamiento: Reserva de hotel o carta de invitación.
   - Vacunas: La fiebre amarilla es obligatoria si visitas la selva (Iquitos, Madre de Dios). Lleva el certificado.
   - Seguro médico: No obligatorio, pero útil.

   **🇬🇾 GUYANA** y **🇸🇷 SURINAM** (Estados Asociados del MERCOSUR)
   - Visa: No necesitan visa para turismo (estadía hasta 90 días).
   - Documento de identidad: Se recomienda llevar **pasaporte** (aunque la cédula es válida en teoría, es más seguro usar pasaporte por seguridad). Consulta con la embajada antes de viajar.
   - Pasaje de regreso: Obligatorio.
   - Solvencia económica: Demostrar medios económicos (aproximadamente $60-80 USD por día en Guyana, $50-70 USD en Surinam).
   - Alojamiento: Reserva de hotel.
   - Vacunas: Fiebre amarilla obligatoria para ambos países. Presentar certificado internacional.
   - Seguro médico: Recomendable.

   **🇻🇪 VENEZUELA** (Mercosur suspendido)
   - Históricamente no requería visa para bolivianos (estadía hasta 90 días), pero la situación política puede cambiar. SIEMPRE consultar con el consulado venezolano antes de viajar.
   - Documento de identidad: Pasaporte vigente (la cédula no es aceptada internacionalmente fuera de los acuerdos activos).
   - Pasaje de regreso: Obligatorio.
   - Solvencia económica: Demostrar medios económicos.
   - Seguro médico: Muy recomendable.

7. **Si el usuario pregunta por un país que no está en estas listas** (ej. México, EE.UU., Europa, etc.), responde: "Para viajar a [país], te recomiendo consultar la página oficial de su consulado o revisar los acuerdos de visados. ¿Necesitas ayuda con el pre-registro digital para tu salida de Bolivia?"

Recuerda: toda la información de requisitos de la sección 6 es solo para ciudadanos bolivianos que SALEN de Bolivia. Los costos y requisitos de ingreso a Bolivia para extranjeros ya están cubiertos por las listas de grupos (sección 5).
"""

# ------------------------------------------------------------------
# RESPUESTA LOCAL MINIMAL (solo preguntas cerradas de costos)
# ------------------------------------------------------------------
def responder_local(mensaje: str) -> str | None:
    m = mensaje.lower()
    if "pasaporte" in m and ("cuánto" in m or "costo" in m or "precio" in m or "cuesta" in m):
        t = tramite_pasaporte()
        return f"📘 Pasaporte boliviano: {t['costo_bs']} Bs + {t['costo_ufv']} UFV = {t['total_bs']:.2f} Bs (≈ {t['total_usd']} USD). ¿Necesitas el QR?"
    if "tripulante" in m and ("cuánto" in m or "costo" in m or "precio" in m or "cuesta" in m):
        t = tramite_tripulante()
        return f"🚛 Libreta de Tripulante Terrestre: primera vez {t['total_bs']:.2f} Bs (≈ {t['total_usd']} USD). Renovación sin costo. ¿QR?"
    if "arraigo" in m and ("cuánto" in m or "costo" in m or "precio" in m or "cuesta" in m):
        t = tramite_arraigo()
        return f"⚖️ Arraigo: {t['total_bs']:.2f} Bs (≈ {t['total_usd']} USD). ¿Deseas generar el QR?"
    return None

# ------------------------------------------------------------------
# RUTAS
# ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PORTAL.format(
        alerta_sistema="",
        contenido_dinamico='<div class="text-center py-24 text-gray-500">ESPERANDO ACCION...</div>',
        status_color_bg="bg-gray-800",
        status_color_text="text-gray-500",
        status_texto="STANDBY"
    )

@app.get("/chatbot", response_class=HTMLResponse)
async def chatbot_page():
    return HTML_CHATBOT

@app.post("/api/chat")
async def api_chat(mensaje: str = Form(...)):
    # 1. Respuesta local solo para costos directos
    resp_local = responder_local(mensaje)
    if resp_local:
        return JSONResponse(content={"respuesta": resp_local})
    
    # 2. Obtener historial de esta "sesión"
    historial = conversacion_por_sesion.get("historial", [])
    
    # 3. Construir mensajes para Groq
    messages = [
        {"role": "system", "content": PROMPT_SISTEMA}
    ]
    # Añadir historial (últimos 6 mensajes)
    for msg in historial[-6:]:
        messages.append(msg)
    # Añadir mensaje actual
    messages.append({"role": "user", "content": mensaje})
    
    try:
        completion = client.chat.completions.create(
            model=MODELO_IA,
            messages=messages,
            temperature=0.3,
        )
        respuesta = completion.choices[0].message.content
        # Guardar en historial
        historial.append({"role": "user", "content": mensaje})
        historial.append({"role": "assistant", "content": respuesta})
        conversacion_por_sesion["historial"] = historial
        return JSONResponse(content={"respuesta": respuesta})
    except Exception as e:
        print(e)
        return JSONResponse(content={"respuesta": "⚠️ El sistema está congestionado. Por favor, intenta de nuevo más tarde o usa el botón '+' para generar tu QR manualmente."})

@app.post("/generar-qr")
async def generar_qr(nacionalidad: str = Form(""), tramite: str = Form(""), monto: float = Form(0.0)):
    payload = {"nacionalidad": nacionalidad, "tramite": tramite, "monto_total_bs": monto, "estado": "pre-registro"}
    json_payload = json.dumps(payload)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return JSONResponse(content={"qr_image": img_base64, "payload": json_payload})

@app.post("/buscar", response_class=HTMLResponse)
async def buscar(documento: str = Form(...)):
    doc_id = documento.strip().upper()
    if doc_id in DB_SISTEMA:
        data = DB_SISTEMA[doc_id]
        total_bs = data["arancel"] + data["tasa"]
        qr_json = {"nacionalidad": data["pais"], "total_autorizado_bs": total_bs, "estado": "PRE-PAGADO"}
        hash_val = hashes_pdf.get(doc_id, "ERROR")
        alerta = f'<div class="bg-blue-900 border border-blue-600 text-blue-200 p-4 rounded-xl">EXPEDIENTE DIGITAL AUTORIZADO</div>'
        contenido = f"""
        <div class='text-white p-4 bg-gray-800 rounded-xl'>
            <p class='text-2xl font-bold'>{data['nombres']} {data['apellidos']}</p>
            <p>{data['pais']} — {data['grupo']}</p>
            <p class='mt-2'>{data['tramite']}</p>
            <div class="bg-gray-900 p-4 border border-gray-700 rounded-xl mt-4">
                <p class="text-[10px] text-gray-500 uppercase">Integridad (SHA-256)</p>
                <p class="text-[9px] font-mono text-green-400 break-all">{hash_val}</p>
                <a href="{data['pdf']}" target="_blank" class="text-blue-400 text-sm">Abrir PDF</a>
            </div>
        </div>
        <script>document.getElementsByName('qr_payload')[0].value = '{json.dumps(qr_json)}';</script>
        """
        return HTML_PORTAL.format(alerta_sistema=alerta, contenido_dinamico=contenido, status_color_bg="bg-blue-900", status_color_text="text-blue-200", status_texto="ENCONTRADO")
    else:
        return HTML_PORTAL.format(alerta_sistema='<div class="bg-red-900 p-4 rounded">NO ENCONTRADO</div>', contenido_dinamico="404", status_color_bg="bg-red-900", status_color_text="text-red-200", status_texto="NOT FOUND")

@app.post("/escanear-qr", response_class=HTMLResponse)
async def escanear(qr_payload: str = Form(...)):
    try:
        data = json.loads(qr_payload)
        total = data.get("total_autorizado_bs", 0.0)
        contenido = f"<div class='bg-gray-900 p-6 rounded-2xl text-white'>Monto total: {total:.2f} Bs<br>Estado: {data.get('estado')}</div>"
        return HTML_PORTAL.format(alerta_sistema="<div class='bg-green-900 p-4 rounded'>QR VALIDADO</div>", contenido_dinamico=contenido, status_color_bg="bg-green-900", status_color_text="text-green-200", status_texto="VALIDO")
    except:
        return HTML_PORTAL.format(alerta_sistema="ERROR", contenido_dinamico="", status_color_bg="bg-red-900", status_color_text="text-red-200", status_texto="ERROR")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)