# dashboard_sdr.py
import streamlit as st
import random
import time
import pandas as pd
from datetime import datetime
import os, io
import numpy as np
import soundfile as sf
from streamlit_mic_recorder import mic_recorder

st.set_page_config(page_title="SDR Training - Pack", layout="wide")

# =======================
# DATA BASE
# =======================
PRICING = {
    "Mentoring individual": "149 €/sesión o 299 €/mes",
    "Coaching individual": "199 €/sesión o 399 €/mes",
    "Group Mentoring/Coaching": "3.490–4.900 €/clase (<=10 personas)",
    "Train the Trainer": "2.900 €/clase (<=10 personas)",
    "Assessment": "90–1.590 € por persona",
}

VALUE_POINTS = [
    "Reduce el coste de rotación (~15.000 € por renuncia).",
    "Mejora engagement, retención y productividad.",
    "Escalable y data-driven (analíticas, reporting, 360° control).",
    "Red de +200 mentores/coaches internacionales, 15+ países.",
    "Cumplimiento GDPR, ISO 9001, infra en la UE/EEE.",
]

OBJECTIONS_BASE = {
    "⏱️ Poco tiempo": [
        "Ahora no puedo, estoy entrando a una reunión.",
        "Dime rápido, ¿qué necesitas?",
        "No tengo tiempo para esto."
    ],
    "❓ Preguntas específicas": [
        "¿Cómo integran con nuestro calendario y herramientas?",
        "¿Cómo medís el impacto y el ROI?",
        "¿Tenéis casos en mi sector?"
    ],
    "💸 Precio/Presupuesto": [
        "No tenemos presupuesto ahora mismo.",
        "Es caro para nosotros.",
        "En este Q no podemos invertir."
    ],
    "🏗️ Ya tenemos proveedor/programa": [
        "Ya tenemos un programa interno de mentoring.",
        "Trabajamos con otro proveedor.",
        "Esto lo maneja nuestra L&D internamente."
    ],
    "🧭 Prioridad/Timing": [
        "No es una prioridad este trimestre.",
        "Vuelve a llamarme en 6 meses.",
        "Estamos en reorg; no es el momento."
    ],
    "👤 No soy la persona": [
        "No soy yo quien decide esto.",
        "Esto lo lleva otra área.",
        "No gestiono este presupuesto."
    ],
    "📨 Mándame info": [
        "Mándame un correo y lo reviso.",
        "Envíame un PDF con precios y lo vemos.",
        "Déjame la info y si me interesa te llamo."
    ],
    "🙅 No interesado": [
        "No me interesa.",
        "No vemos utilidad.",
        "Esto no nos aplica."
    ],
}

OBJECTIONS_BY_INDUSTRY = {
    "General": OBJECTIONS_BASE,
    "Telco": {
        **OBJECTIONS_BASE,
        "❓ Preguntas específicas": OBJECTIONS_BASE["❓ Preguntas específicas"] + [
            "¿Se integra con nuestras plataformas de atención y ticketing?",
            "¿Podemos mapear habilidades para equipos de field/ops?",
        ],
    },
    "Retail": {
        **OBJECTIONS_BASE,
        "🧭 Prioridad/Timing": OBJECTIONS_BASE["🧭 Prioridad/Timing"] + [
            "Estamos en peak season, no podemos distraer al equipo ahora.",
        ],
    },
    "FinServ": {
        **OBJECTIONS_BASE,
        "🏗️ Ya tenemos proveedor/programa": OBJECTIONS_BASE["🏗️ Ya tenemos proveedor/programa"] + [
            "Cumplimos estrictamente con compliance, ¿cómo garantizáis GDPR/ISO?",
        ],
    },
    "IT": {
        **OBJECTIONS_BASE,
        "❓ Preguntas específicas": OBJECTIONS_BASE["❓ Preguntas específicas"] + [
            "¿Tenéis APIs o SSO? ¿Cómo es el provisioning?",
        ],
    },
}

MODEL_ANSWERS = {
    "⏱️ Poco tiempo": """Totalmente, te robo solo 20–30 segundos: ayudamos a reducir la rotación (~15k€ por renuncia) con mentoring/coaching data-driven y +200 expertos.
Si tiene sentido, agendamos 20 min esta semana. ¿Te va el jueves 11:30? ¿A qué email te envío la invitación?""",
    "❓ Preguntas específicas": """¡Buena pregunta! Integramos 1-click scheduling y medimos impacto (engagement, NPS, progreso, ROMI/ROCI).
Tengo 2–3 ejemplos de tu sector para mostrarte en 15–20 min. ¿Mañana a las 12:00? ¿Cuál es el mejor correo para la invitación?""",
    "💸 Precio/Presupuesto": """Entiendo el presupuesto. Muchas empresas empiezan pequeño (p.ej. 299 €/mes por persona) y escalan al ver resultados.
Hagamos 20 min para ajustar alcance al presupuesto. ¿Martes 10:30? ¿Tu email para enviarte el calendario?""",
    "🏗️ Ya tenemos proveedor/programa": """¡Genial! Solemos complementar programas internos con red global de mentores y métricas de impacto (no sustituimos, potenciamos).
Vemos encaje en 20 min y cómo convivimos con lo que ya tenéis. ¿Miércoles 16:00? ¿A qué email mando la invitación?""",
    "🧭 Prioridad/Timing": """Perfecto, respeto el timing. Hagamos 15–20 min para mapear casos de uso y dejarlo listo cuando abra la ventana.
¿Jueves 9:30? ¿Cuál es tu mejor correo para el invite?""",
    "👤 No soy la persona": """Gracias por decírmelo. ¿Quién lidera L&D/Talent/HR para incluirle? Propongo 20 min con ambos para valorar encaje.
¿Me facilitas su email y te copio? ¿Viernes 12:00?""",
    "📨 Mándame info": """Encantado. Para enviar algo útil, bloqueamos 15–20 min y lo adapto a tu contexto. Te comparto casos y números.
¿Mañana 11:30? ¿A qué email te envío la invitación?""",
    "🙅 No interesado": """Gracias por la franqueza. Solo por validar: aportamos en rotación y upskilling de managers.
Si no encaja, cierro aquí; si hay curiosidad, 15 min y te muestro datos. ¿Lunes 12:30? ¿Tu email?""",
}

CTA_SNIPPETS = [
    "¿Te va una **discovery** de 20 minutos esta semana?",
    "¿Cuál es el **mejor correo** para enviarte la invitación?",
    "¿Prefieres **martes 10:30** o **jueves 11:30**?",
    "Te envío el **calendario con 2 slots** y lo ajustamos."
]

PERSONA_SCRIPTS = {
    "CFO": [
        "Enfatiza **ROI**, reducción de rotación (15k€/renuncia), productividad.",
        "Propuesta: piloto acotado + métricas de impacto trimestral.",
    ],
    "HR Director": [
        "Enfatiza **engagement**, desarrollo de liderazgo, NPS, experiencia de empleado.",
        "Propuesta: cohortes con analíticas y reporting automatizado para stakeholders.",
    ],
    "Talent Manager": [
        "Enfatiza **upskilling de High Potentials**, sucesión y carrera.",
        "Propuesta: mentoring/coaching con matching por objetivos y KPIs claros.",
    ],
    "Founder": [
        "Enfatiza **velocidad de ejecución**, cultura, excelencia de management.",
        "Propuesta: plan lean con quick wins y tablero de impacto.",
    ],
}

# =======================
# PERSISTENCIA CSV / GSHEETS
# =======================
@st.cache_data
def load_history_from_csv(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        expected = {"timestamp","industry","persona_role","situation","objection","response","score"}
        for m in expected - set(df.columns):
            df[m] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=["timestamp","industry","persona_role","situation","objection","response","score"])

def save_history_to_csv(df: pd.DataFrame, path: str) -> bool:
    try:
        df.to_csv(path, index=False)
        return True
    except Exception:
        return False

# Opcional Google Sheets
import json
def gs_get_credentials_from_secrets():
    sa = st.secrets["gsheets"]["service_account_json"]
    if isinstance(sa, str):
        sa = json.loads(sa)
    return sa, st.secrets["gsheets"]["spreadsheet_id"]

def gs_test_connection():
    try:
        sa_dict, spreadsheet_id = gs_get_credentials_from_secrets()
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(sa_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(spreadsheet_id)
        try:
            ws = sh.worksheet("history")
        except Exception:
            ws = sh.add_worksheet(title="history", rows="1000", cols="20")
        ws.update("A1:G1", [["timestamp","industry","persona_role","situation","objection","response","score"]])
        return "✅ Conexión OK y worksheet 'history' preparado."
    except Exception as e:
        return f"❌ Error de conexión: {e}"

def gs_save_history_df(df: pd.DataFrame) -> str:
    try:
        sa_dict, spreadsheet_id = gs_get_credentials_from_secrets()
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(sa_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(spreadsheet_id)
        try:
            ws = sh.worksheet("history")
        except Exception:
            ws = sh.add_worksheet(title="history", rows="1000", cols="20")
        ws.clear()
        ws.update([df.columns.tolist()] + df.values.tolist())
        return "✅ Historial guardado en Google Sheets (worksheet: history)."
    except Exception as e:
        return f"❌ No se pudo guardar en Sheets: {e}"

# =======================
# SESSION STATE
# =======================
if "history" not in st.session_state:
    st.session_state.history = []
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "timer_end" not in st.session_state:
    st.session_state.timer_end = 0
if "current_obj" not in st.session_state:
    st.session_state.current_obj = None

# =======================
# NAV
# =======================
st.title("📊 SDR Training Dashboard – Cold Calling (Pack)")
st.caption("Entrena rapport, manejo de objeciones y **booking de discovery**.")

menu = st.sidebar.radio(
    "Navegación",
    [
        "🎯 Objetivos del Ejercicio",
        "🧑‍💼 Escenarios de Prospectos",
        "🏢 Company Profile (Pack)",
        "💡 Argumentos & Objeciones",
        "⚔️ Entrenador de Objeciones",
        "🎤 Simulador de Pitch",
        "🎙️ Grabador de Voz (beta)",
        "🎧 Audio Check (ligero)",
        "📈 Historial & Persistencia",
        "📚 Guiones por Persona"
    ]
)

# =======================
# PAGES
# =======================
if menu == "🎯 Objetivos del Ejercicio":
    st.header("🎯 Objetivo del Ejercicio")
    st.markdown("""
- **Meta principal**: conseguir una *discovery call* (no vender).
- **Acciones clave**:
  - Mantener la conversación fluida  
  - Manejar objeciones con empatía  
  - **Pedir explícitamente** una reunión  
  - **Solicitar email** para enviar invitación de calendario  
    """)

elif menu == "🧑‍💼 Escenarios de Prospectos":
    st.header("🧑‍💼 Escenarios de Prospects")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Prospecto A – Poco tiempo")
        st.write("- Te corta rápido\n- Quiere ir al grano\n- Sé conciso y directo")
        st.code(
            "“Hola [nombre], soy Nicolás de Pack. Sé que tienes poco tiempo: "
            "¿te robo 20–30 segundos para ver si tiene sentido agendar 20 min?”"
        )
    with col2:
        st.subheader("Prospecto B – Preguntas específicas")
        st.write("- Pide detalles del producto\n- Quiere evidencia\n- Aporta seguridad sin entrar en demo")
        st.code(
            "“Integramos 1-click scheduling y medimos impacto (engagement, NPS, ROMI/ROCI). "
            "¿Vemos 20 min con ejemplos de tu sector?”"
        )

elif menu == "🏢 Company Profile (Pack)":
    st.header("🏢 Perfil de la Empresa – Pack")
    st.markdown("""
**Problema**: ~40% empleados insatisfechos, coste medio de renuncia **~15.000 €**.  
**Solución**: Plataforma de mentoring/coaching con IA, matching gamificado, +200 mentores, analíticas y reporting.  
**Valor**: retención, engagement, productividad; data-driven; cumplimiento GDPR/ISO; servidores UE.  
    """)
    st.subheader("💰 Modelos de Precio (Resumen)")
    for k, v in PRICING.items():
        st.write(f"- **{k}**: {v}")

elif menu == "💡 Argumentos & Objeciones":
    st.header("💡 Argumentos de Valor")
    for v in VALUE_POINTS:
        st.write(f"- {v}")
    st.subheader("✉️ CTAs rápidas")
    for c in CTA_SNIPPETS:
        st.code(c)

    st.subheader("🧱 Objeciones por industria")
    industry = st.selectbox("Industria", list(OBJECTIONS_BY_INDUSTRY.keys()), index=0)
    obj_bank = OBJECTIONS_BY_INDUSTRY[industry]
    for cat, lst in obj_bank.items():
        with st.expander(f"{cat}"):
            for o in lst:
                st.write(f"- {o}")
            st.markdown("**Respuesta sugerida:**")
            st.info(MODEL_ANSWERS.get(cat, "—"))

elif menu == "⚔️ Entrenador de Objeciones":
    st.header("⚔️ Entrenador de Objeciones (cronómetro + scoring)")
    cols = st.columns([1.2, 1, 1])
    industry = cols[0].selectbox("Industria", list(OBJECTIONS_BY_INDUSTRY.keys()), index=0)
    situation = cols[1].selectbox("Situación", list(OBJECTIONS_BY_INDUSTRY[industry].keys()))
    dur = cols[2].number_input("Duración respuesta (seg)", min_value=15, max_value=90, value=30, step=5)
    unique = st.checkbox("Evitar repetir objeciones recientes", value=True)

    obj_pool = OBJECTIONS_BY_INDUSTRY[industry][situation][:]

    def pick_obj():
        pool = obj_pool[:]
        if unique and len(st.session_state.history) > 0:
            recent = [h["objection"] for h in st.session_state.history[-5:]]
            pool = [p for p in pool if p not in recent] or obj_pool[:]
        return random.choice(pool)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎲 Nueva objeción"):
            st.session_state.current_obj = pick_obj()
            st.session_state.timer_running = False
    with c2:
        if st.button("⏱️ Iniciar cronómetro"):
            if st.session_state.current_obj:
                st.session_state.timer_running = True
                st.session_state.timer_end = time.time() + dur

    st.subheader("🗯️ Objeción")
    st.warning(st.session_state.current_obj or "Pulsa **🎲 Nueva objeción** para empezar.")

    timer_box = st.empty()
    if st.session_state.timer_running:
        remaining = int(max(0, st.session_state.timer_end - time.time()))
        timer_box.metric("Tiempo restante", f"{remaining}s")
        if remaining <= 0:
            st.session_state.timer_running = False
            st.success("⏱️ ¡Tiempo!")
        else:
            st.experimental_rerun()

    st.markdown("**💡 Pistas tácticas**")
    tips = {
        "⏱️ Poco tiempo": ["Pide 20–30s + beneficio claro + micro-CTA.", "Cierra con fecha/hora y pide email."],
        "❓ Preguntas específicas": ["Responde alto nivel + prueba social/analytics.", "Invita a 20 min para profundizar."],
        "💸 Precio/Presupuesto": ["Empatiza, entrada pequeña escalable.", "Cierra discovery y pide email."],
        "🏗️ Ya tenemos proveedor/programa": ["Complemento, no sustituto.", "Discovery para mapear convivencia."],
        "🧭 Prioridad/Timing": ["Alinea tiempos, micro-reunión de preparación.", "CTA concreta + email."],
        "👤 No soy la persona": ["Pide referente + email; call conjunta."],
        "📨 Mándame info": ["Convierte envío de info en meeting contextualizado."],
        "🙅 No interesado": ["Agradece, valida hipótesis de valor; ofrece 15 min o cierra cordial."],
    }
    for t in tips.get(situation, []):
        st.write("- " + t)

    with st.expander("🧪 Respuesta modelo (ver después de intentar)"):
        st.info(MODEL_ANSWERS.get(situation, "—"))

    st.subheader("🎙️ Tu respuesta")
    resp = st.text_area("Escribe bullets o tu guion (30–90s).", height=150, placeholder="Hola [nombre]...")

    st.markdown("**🧮 Auto-evaluación (marca si lo hiciste):**")
    cc = st.columns(4)
    crit = [cc[0].checkbox("Ganaste tiempo"),
            cc[1].checkbox("Empatizaste/Valor claro"),
            cc[2].checkbox("Propusiste discovery"),
            cc[3].checkbox("Pediste email")]
    score = sum(crit)

    persona_role = st.selectbox("Persona (rol)", list(PERSONA_SCRIPTS.keys()), index=1)

    save_cols = st.columns([1, 1, 2])
    if save_cols[0].button("💾 Guardar intento"):
        if st.session_state.current_obj:
            st.session_state.history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "industry": industry,
                "persona_role": persona_role,
                "situation": situation,
                "objection": st.session_state.current_obj,
                "response": resp.strip(),
                "score": score
            })
            st.success("Intento guardado ✅")
        else:
            st.error("Genera una objeción antes de guardar.")

    if save_cols[1].button("🧹 Limpiar"):
        st.session_state.current_obj = None

elif menu == "🎤 Simulador de Pitch":
    st.header("🎤 Practica tu Pitch")
    script = st.text_area("Escribe tu pitch (30–45s):", height=200,
                          placeholder="Hola [nombre], soy Nicolás de Pack. Sé que tienes poco tiempo, ¿te robo 20–30 segundos...?")
    st.subheader("📌 Plantilla sugerida")
    st.write("""
1) **Inicio (ganar tiempo)**: “¿Te robo 20–30 segundos?”  
2) **Dolor**: rotación cara (~15k€), managers sin upskilling  
3) **Valor**: mentoring/coaching con IA, +200 expertos, métricas  
4) **Cierre**: “¿Agendamos 20 min?”  
5) **CTA email**: “¿Cuál es el mejor correo?”  
    """)
    if st.button("💾 Guardar Notas"):
        st.success("✅ Notas guardadas (sesión actual).")

elif menu == "🎙️ Grabador de Voz (beta)":
    # === Grabador con transcripción opcional Faster-Whisper ===
    import os, io
    import numpy as np
    import soundfile as sf
    from streamlit_mic_recorder import mic_recorder

    st.header("🎙️ Grabador de Voz (beta)")
    st.caption("Pulsa **Start recording** → habla → **Stop**. Guarda el WAV y (opcional) transcribe con Faster-Whisper.")

    os.makedirs("recordings", exist_ok=True)

    st.write("**Graba tu respuesta (30–90s):**")
    audio_dict = mic_recorder(
        start_prompt="Start recording",
        stop_prompt="Stop",
        just_once=False,
        format="wav",
        key="mic1"
    )

    meta_col1, meta_col2, meta_col3 = st.columns(3)
    saved_path = st.empty()

    def _save_wav_and_info(wav_bytes: bytes) -> dict:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = f"recordings/rec_{ts}.wav"
        data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        sf.write(path, data, sr)
        duration_sec = round(len(data) / sr, 2)
        return {"path": path, "samplerate": sr, "duration": duration_sec}

    latest_wav = None
    if audio_dict and "bytes" in audio_dict and audio_dict["bytes"] is not None:
        try:
            info = _save_wav_and_info(audio_dict["bytes"])
            latest_wav = info["path"]
            meta_col1.metric("Duración", f"{info['duration']} s")
            meta_col2.metric("Sample rate", f"{info['samplerate']} Hz")
            meta_col3.success("Grabación OK")
            saved_path.markdown(f"💾 Archivo guardado: **`{info['path']}`**")
            st.audio(audio_dict["bytes"], format="audio/wav")
        except Exception as e:
            st.error(f"No se pudo procesar el audio: {e}")

    st.markdown("---")
    st.subheader("📝 Transcript")
    st.caption("Pega/edita manualmente o intenta transcribir con Faster-Whisper (opcional).")
    prefill = st.session_state.get("auto_transcript", "")
    transcript = st.text_area("Transcript", height=160, value=prefill, placeholder="Pega o escribe aquí tu respuesta…")

    col_t1, col_t2 = st.columns([1.2, 2])
    try_transcribe = col_t1.button("🤖 Transcribir (Faster-Whisper)")
    whisper_status = col_t2.empty()

    st.markdown("### ⏭️ Enviar Transcript a **Audio Check**")
    if st.button("➡️ Enviar a Audio Check"):
        st.session_state["audio_check_transcript"] = transcript
        st.success("Transcript copiado. Ve a **🎧 Audio Check (ligero)**")

elif menu == "🎧 Audio Check (ligero)":
    st.header("🎧 Audio Check (sin dependencias pesadas)")
    st.caption("Analiza ritmo (WPM), muletillas y pausas usando tu transcript + duración.")

    col = st.columns(2)
    duration_sec = col[0].number_input("Duración del pitch (segundos)", min_value=10, max_value=300, value=45, step=5)
    prefill = st.session_state.get("audio_check_transcript", "")
    transcript = col[1].text_area("Transcript (pega tu texto)", height=180, value=prefill, placeholder="Hola... (tu texto)")

    filler_words = [
        "eh", "ehh", "mmm", "este", "esto", "o sea", "vale", "ok", "tipo",
        "digamos", "¿vale?", "¿ok?", "em", "eeeh", "nada", "bueno"
    ]
    pause_markers = ["(pausa)", "[pausa]", "...", "— —"]

    if st.button("Analizar"):
        words = transcript.strip().split()
        n_words = len(words)
        wpm = round((n_words / duration_sec) * 60, 1) if duration_sec > 0 else 0.0
        text_low = transcript.lower()
        filler_counts = {fw: text_low.count(fw) for fw in filler_words}
        total_fillers = sum(filler_counts.values())
        total_pauses = sum(text_low.count(p) for p in pause_markers)
        pauses_per_min = round((total_pauses / duration_sec) * 60, 2) if duration_sec else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Palabras", n_words)
        c2.metric("Ritmo (WPM)", wpm)
        c3.metric("Muletillas", total_fillers)
        c4.metric("Pausas/min", pauses_per_min)

        with st.expander("🔎 Detalle muletillas"):
            st.write(pd.DataFrame([filler_counts]).T.rename(columns={0: "conteo"}))

        tips = []
        if wpm < 110: tips.append("Ritmo bajo: sube a ~130–160 WPM.")
        if wpm > 170: tips.append("Ritmo alto: baja a ~130–160 WPM.")
        if total_fillers >= 5: tips.append("Reduce muletillas (practica silencios breves).")
        if pauses_per_min > 6: tips.append("Demasiadas pausas: estructura mejor tus frases.")
        if not tips:
            tips = ["Buen ritmo y control de muletillas/pausas. ✅"]
        st.success(" · ".join(tips))

elif menu == "📈 Historial & Persistencia":
    st.header("📈 Historial de intentos")
    if len(st.session_state.history) == 0:
        st.info("Aún no hay intentos guardados. Ve a **Entrenador de Objeciones**.")
    else:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True)

        dl = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar CSV", data=dl, file_name="sdr_history.csv", mime="text/csv")

        st.subheader("💾 Guardar en disco")
        save_path = st.text_input("Ruta (ej: history.csv)", value="history.csv")
        if st.button("Guardar CSV"):
            ok = save_history_to_csv(df, save_path)
            st.success("Historial guardado en CSV ✅" if ok else "No se pudo guardar el CSV ❌")

        st.subheader("☁️ Guardar en Google Sheets (opcional)")
        st.caption("Requiere `st.secrets['gsheets']` con `service_account_json` y `spreadsheet_id`.")
        cols = st.columns(2)
        if cols[0].button("🔌 Probar conexión Google Sheets"):
            st.info(gs_test_connection())
        if cols[1].button("☁️ Guardar historial en Google Sheets"):
            st.info(gs_save_history_df(df))

    st.subheader("📤 Cargar historial desde CSV")
    up = st.file_uploader("Sube un CSV exportado", type=["csv"])
    if up is not None:
        new_df = pd.read_csv(up)
        for _, row in new_df.iterrows():
            st.session_state.history.append({
                "timestamp": str(row.get("timestamp","")),
                "industry": str(row.get("industry","")),
                "persona_role": str(row.get("persona_role","")),
                "situation": str(row.get("situation","")),
                "objection": str(row.get("objection","")),
                "response": str(row.get("response","")),
                "score": int(row.get("score",0))
            })
        st.success("Historial cargado y fusionado ✅")

elif menu == "📚 Guiones por Persona":
    st.header("📚 Guiones por Persona (rol decisor)")
    role = st.selectbox("Persona (rol)", list(PERSONA_SCRIPTS.keys()))
    for bullet in PERSONA_SCRIPTS[role]:
        st.write("- " + bullet)

# ======= FOOTER =======
st.markdown("---")
st.caption("Foco: rapport, claridad, **discovery**, email. Grabación + transcripción (opcional), CSV/Sheets, audio-check.")
