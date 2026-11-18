const questions = [
  { topic: "Duración", text: "¿Cuántas horas de sueño se recomiendan para una persona adulta?" },
  { topic: "Ambiente", text: "¿Qué temperatura se recomienda para dormir?" },
  { topic: "Hábitos", text: "¿Cuánto tiempo antes de dormir conviene evitar la cafeína?" },
  { topic: "Hábitos", text: "¿Cuándo debería dejar de usar pantallas antes de acostarme?" },
  { topic: "Fases del sueño", text: "¿Qué función tiene la fase REM?" },
  { topic: "Calidad", text: "¿Qué eficiencia del sueño se considera óptima?" },
];
const pageSize = 2;
let currentPage = 0;
let registerMode = false;
let conversationId = null;
let authToken = sessionStorage.getItem("accessToken");

const byId = (id) => document.getElementById(id);
const svgNamespace = "http://www.w3.org/2000/svg";

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  return fetch(url, { ...options, headers });
}

function renderQuestions() {
  const start = currentPage * pageSize;
  const visible = questions.slice(start, start + pageSize);
  const list = byId("question-list");
  list.replaceChildren();
  visible.forEach((question) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "question-card";
    const topic = document.createElement("span");
    topic.textContent = question.topic;
    button.append(topic, document.createTextNode(question.text));
    button.addEventListener("click", () => {
      byId("user-input").value = question.text;
      byId("user-input").focus();
    });
    list.append(button);
  });
  byId("page-label").textContent = `${currentPage + 1} / ${Math.ceil(questions.length / pageSize)}`;
  byId("previous-page").disabled = currentPage === 0;
  byId("next-page").disabled = start + pageSize >= questions.length;
}

function setAuthMode(mode) {
  registerMode = mode === "register";
  byId("tab-login").classList.toggle("active", !registerMode);
  byId("tab-register").classList.toggle("active", registerMode);
  byId("auth-btn").textContent = registerMode ? "Crear cuenta" : "Iniciar sesión";
  byId("auth-error").classList.add("hidden");
}

function addMessage(text, isUser, metadata = null) {
  const article = document.createElement("article");
  article.className = `message ${isUser ? "user-message" : "assistant-message"}`;
  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = isUser ? "T" : "S";
  const content = document.createElement("div");
  content.className = "message-content";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  content.append(paragraph);
  if (metadata) {
    const meta = document.createElement("div");
    meta.className = "message-meta";
    const pages = metadata.paginas_fuente.length
      ? ` · páginas ${metadata.paginas_fuente.join(", ")}`
      : "";
    meta.textContent = `Similitud ${metadata.confianza_similitud.toFixed(1)}% · ${metadata.fragmentos_recuperados} fragmento(s) · ${metadata.tiempos_ms.total.toFixed(0)} ms · traza ${metadata.trace_id.slice(0, 8)}${pages}`;
    content.append(meta);
  }
  article.append(avatar, content);
  byId("chat-container").append(article);
  byId("chat-container").scrollTop = byId("chat-container").scrollHeight;
  return article;
}

function setFormStatus(id, message, isError = false) {
  const status = byId(id);
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function setProfileForm(profile) {
  if (!profile) return;
  byId("profile-name").value = profile.display_name;
  byId("profile-age").value = profile.age_range;
  byId("profile-goal").value = profile.sleep_goal_hours;
  byId("profile-timezone").value = profile.timezone;
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(svgNamespace, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function renderSleepChart(logs, targetHours) {
  const chart = byId("sleep-chart");
  chart.replaceChildren();
  const visibleLogs = logs.slice(-14);
  byId("chart-empty").classList.toggle("hidden", visibleLogs.length > 0);
  if (!visibleLogs.length) return;

  const width = 720;
  const height = 290;
  const left = 48;
  const right = 18;
  const chartWidth = width - left - right;
  const hoursTop = 22;
  const hoursBottom = 112;
  const qualityTop = 157;
  const qualityBottom = 239;
  const maxHours = Math.max(10, targetHours + 2);
  const slot = chartWidth / visibleLogs.length;
  const svg = svgElement("svg", {
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": "Gráfico de horas de sueño y calidad percibida de las últimas noches",
  });

  [0, 4, 8, maxHours].forEach((tick) => {
    const y = hoursBottom - (tick / maxHours) * (hoursBottom - hoursTop);
    svg.append(svgElement("line", {
      x1: left, y1: y, x2: width - right, y2: y, class: "chart-grid",
    }));
    const label = svgElement("text", {
      x: left - 9, y: y + 4, "text-anchor": "end", class: "chart-axis-label",
    });
    label.textContent = `${tick}h`;
    svg.append(label);
  });

  const targetY = hoursBottom - (targetHours / maxHours) * (hoursBottom - hoursTop);
  svg.append(svgElement("line", {
    x1: left,
    y1: targetY,
    x2: width - right,
    y2: targetY,
    class: "chart-target",
  }));
  const targetLabel = svgElement("text", {
    x: width - right,
    y: targetY - 5,
    "text-anchor": "end",
    class: "chart-target-label",
  });
  targetLabel.textContent = `Objetivo ${targetHours} h`;
  svg.append(targetLabel);

  const qualityPoints = [];
  visibleLogs.forEach((log, index) => {
    const centerX = left + slot * (index + 0.5);
    const barHeight = (Math.min(log.hours_slept, maxHours) / maxHours)
      * (hoursBottom - hoursTop);
    const bar = svgElement("rect", {
      x: centerX - Math.min(14, slot * 0.28),
      y: hoursBottom - barHeight,
      width: Math.min(28, slot * 0.56),
      height: barHeight,
      rx: 4,
      class: "chart-bar",
    });
    const barTitle = svgElement("title");
    barTitle.textContent = `${log.sleep_date}: ${log.hours_slept} horas`;
    bar.append(barTitle);
    svg.append(bar);

    const qualityY = qualityBottom
      - ((log.quality_score - 1) / 9) * (qualityBottom - qualityTop);
    qualityPoints.push([centerX, qualityY]);
    const dateLabel = svgElement("text", {
      x: centerX, y: 272, "text-anchor": "middle", class: "chart-date-label",
    });
    dateLabel.textContent = log.sleep_date.slice(5).replace("-", "/");
    svg.append(dateLabel);
  });

  [1, 5, 10].forEach((score) => {
    const y = qualityBottom - ((score - 1) / 9) * (qualityBottom - qualityTop);
    svg.append(svgElement("line", {
      x1: left, y1: y, x2: width - right, y2: y, class: "chart-grid",
    }));
    const label = svgElement("text", {
      x: left - 9, y: y + 4, "text-anchor": "end", class: "chart-axis-label",
    });
    label.textContent = String(score);
    svg.append(label);
  });

  const qualityPath = qualityPoints
    .map(([x, y], index) => `${index ? "L" : "M"} ${x} ${y}`)
    .join(" ");
  svg.append(svgElement("path", { d: qualityPath, class: "chart-quality-line" }));
  qualityPoints.forEach(([x, y], index) => {
    const point = svgElement("circle", {
      cx: x, cy: y, r: 4, class: "chart-quality-point",
    });
    const pointTitle = svgElement("title");
    pointTitle.textContent = `Calidad percibida: ${visibleLogs[index].quality_score} de 10`;
    point.append(pointTitle);
    svg.append(point);
  });
  chart.append(svg);
}

function renderBadges(badges) {
  const list = byId("badge-list");
  list.replaceChildren();
  badges.forEach((badge) => {
    const item = document.createElement("article");
    item.className = `badge-card${badge.unlocked ? " unlocked" : ""}`;
    const mark = document.createElement("span");
    mark.className = "badge-mark";
    mark.setAttribute("aria-hidden", "true");
    mark.textContent = badge.unlocked ? "✦" : "·";
    const copy = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = badge.title;
    const description = document.createElement("span");
    description.textContent = badge.unlocked
      ? badge.description
      : `${badge.description} ${badge.progress}/${badge.target}`;
    copy.append(title, description);
    item.append(mark, copy);
    list.append(item);
  });
}

async function loadProgress() {
  const response = await apiFetch("/api/v1/progress");
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "No se pudo cargar tu progreso.");
  setProfileForm(data.profile);
  byId("points-total").textContent = data.gamification.points;
  byId("streak-total").textContent = data.gamification.current_streak;
  byId("streak-unit").textContent = data.gamification.current_streak === 1 ? " día" : " días";
  byId("nights-total").textContent = data.gamification.nights_logged;
  renderBadges(data.gamification.badges);
  renderSleepChart(data.sleep_logs, data.sleep_goal_hours);
}

function showApplication(email) {
  byId("auth-section").classList.add("hidden");
  byId("app-section").classList.remove("hidden");
  byId("user-info").classList.remove("hidden");
  byId("user-email-display").textContent = email || "";
  const today = new Date();
  byId("log-date").value = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");
  loadProgress().catch((error) => setFormStatus("log-status", error.message, true));
}

byId("tab-login").addEventListener("click", () => setAuthMode("login"));
byId("tab-register").addEventListener("click", () => setAuthMode("register"));
byId("previous-page").addEventListener("click", () => {
  currentPage = Math.max(0, currentPage - 1);
  renderQuestions();
});
byId("next-page").addEventListener("click", () => {
  currentPage = Math.min(Math.ceil(questions.length / pageSize) - 1, currentPage + 1);
  renderQuestions();
});
byId("logout-button").addEventListener("click", () => {
  authToken = null;
  sessionStorage.removeItem("accessToken");
  sessionStorage.removeItem("userEmail");
  byId("app-section").classList.add("hidden");
  byId("user-info").classList.add("hidden");
  byId("auth-section").classList.remove("hidden");
  byId("auth-form").reset();
  byId("chat-container").replaceChildren();
  byId("profile-form").reset();
  byId("sleep-log-form").reset();
  byId("sleep-chart").replaceChildren();
  byId("badge-list").replaceChildren();
  conversationId = null;
});

byId("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = byId("auth-error");
  error.classList.add("hidden");
  const endpoint = registerMode ? "/api/v1/auth/register" : "/api/v1/auth/login";
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: byId("auth-email").value,
        password: byId("auth-password").value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "No se pudo completar el acceso.");
    if (registerMode) {
      setAuthMode("login");
      byId("auth-password").value = "";
      error.textContent = "Cuenta creada. Ya puedes iniciar sesión.";
      error.classList.remove("hidden");
      error.classList.remove("notice-error");
      return;
    }
    authToken = data.access_token;
    sessionStorage.setItem("accessToken", authToken);
    sessionStorage.setItem("userEmail", byId("auth-email").value);
    conversationId = crypto.randomUUID();
    showApplication(byId("auth-email").value);
  } catch (requestError) {
    error.textContent = requestError.message;
    error.classList.remove("hidden");
    error.classList.add("notice-error");
  }
});

byId("profile-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setFormStatus("profile-status", "Guardando…");
  try {
    const response = await apiFetch("/api/v1/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        display_name: byId("profile-name").value,
        age_range: byId("profile-age").value,
        sleep_goal_hours: Number(byId("profile-goal").value),
        timezone: byId("profile-timezone").value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "No se pudo guardar el perfil.");
    setProfileForm(data.profile);
    await loadProgress();
    setFormStatus("profile-status", "Perfil guardado.");
  } catch (error) {
    setFormStatus("profile-status", error.message, true);
  }
});

byId("sleep-log-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setFormStatus("log-status", "Guardando…");
  try {
    const response = await apiFetch("/api/v1/sleep-logs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sleep_date: byId("log-date").value,
        hours_slept: Number(byId("log-hours").value),
        quality_score: Number(byId("log-quality").value),
        awakenings: Number(byId("log-awakenings").value),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "No se pudo guardar la noche.");
    byId("log-hours").value = "";
    byId("log-quality").value = "";
    byId("log-awakenings").value = "0";
    await loadProgress();
    setFormStatus("log-status", "Noche guardada: has sumado 10 puntos.");
  } catch (error) {
    setFormStatus("log-status", error.message, true);
  }
});

byId("download-report").addEventListener("click", async () => {
  const button = byId("download-report");
  button.disabled = true;
  try {
    const response = await apiFetch("/api/v1/reports/progress.pdf");
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "No se pudo generar el informe.");
    }
    const pdf = await response.blob();
    const link = document.createElement("a");
    const downloadUrl = URL.createObjectURL(pdf);
    link.href = downloadUrl;
    link.download = "mi-progreso-sueno.pdf";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
  } catch (error) {
    setFormStatus("profile-status", error.message, true);
  } finally {
    button.disabled = false;
  }
});

byId("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = byId("user-input");
  const question = input.value.trim();
  if (!question) return;
  addMessage(question, true);
  input.value = "";
  byId("send-button").disabled = true;
  const loading = addMessage("Estoy consultando la guía…", false);
  try {
    const response = await apiFetch("/api/v1/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta: question, conversation_id: conversationId }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "No se pudo completar la consulta.");
    loading.remove();
    addMessage(data.respuesta_asistente, false, data);
  } catch (requestError) {
    loading.remove();
    addMessage(requestError.message, false);
  } finally {
    byId("send-button").disabled = false;
    input.focus();
  }
});

renderQuestions();
if (authToken) showApplication(sessionStorage.getItem("userEmail"));
