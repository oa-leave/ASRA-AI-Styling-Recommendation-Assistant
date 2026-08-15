const API_BASE = "";

const state = {
  accessToken: localStorage.getItem("asra_access_token") || "",
  refreshToken: localStorage.getItem("asra_refresh_token") || "",
  sessionId: localStorage.getItem("asra_session_id") || "",
  username: localStorage.getItem("asra_username") || "",
  profileMode: "create",
  recommendData: null,
  recognitionTask: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function splitTags(value) {
  return String(value || "")
    .split(/[,，、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function refreshIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function showToast(message, type = "info") {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.style.background = type === "error" ? "var(--danger)" : "var(--sidebar)";
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add("hidden"), 3200);
}

function setBusy(button, busy, busyText = "处理中") {
  if (busy) {
    button.dataset.originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span>${esc(busyText)}</span>`;
  } else {
    button.disabled = false;
    if (button.dataset.originalHtml) {
      button.innerHTML = button.dataset.originalHtml;
      delete button.dataset.originalHtml;
    }
  }
  refreshIcons();
}

async function api(path, options = {}) {
  const {
    method = "GET",
    json,
    form,
    formData,
    headers = {},
    retry = false,
  } = options;
  const headersObj = new Headers(headers);
  let body;

  if (json !== undefined) {
    headersObj.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  } else if (form) {
    headersObj.set("Content-Type", "application/x-www-form-urlencoded");
    body = new URLSearchParams(form).toString();
  } else if (formData) {
    body = formData;
  }

  if (state.accessToken) {
    headersObj.set("Authorization", `Bearer ${state.accessToken}`);
  }

  const response = await fetch(API_BASE + path, {
    method,
    headers: headersObj,
    body,
  });

  if (response.status === 401 && state.refreshToken && !retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return api(path, { ...options, retry: true });
    }
  }

  return response;
}

async function refreshAccessToken() {
  const response = await fetch(API_BASE + "/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: state.refreshToken }),
  });
  if (!response.ok) {
    logoutLocal();
    return false;
  }
  const data = await response.json();
  saveTokens(data);
  return true;
}

async function requestJson(path, options) {
  const response = await api(path, options);
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (_) {
      data = null;
    }
  }
  if (!response.ok) {
    const detail = data && data.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `请求失败 (${response.status})`;
    throw Object.assign(new Error(message), { status: response.status });
  }
  return data;
}

function saveTokens(data) {
  state.accessToken = data.access_token;
  state.refreshToken = data.refresh_token;
  localStorage.setItem("asra_access_token", state.accessToken);
  localStorage.setItem("asra_refresh_token", state.refreshToken);
}

function logoutLocal() {
  state.accessToken = "";
  state.refreshToken = "";
  state.sessionId = "";
  state.username = "";
  localStorage.removeItem("asra_access_token");
  localStorage.removeItem("asra_refresh_token");
  localStorage.removeItem("asra_session_id");
  localStorage.removeItem("asra_username");
  showAuth();
}

async function logout() {
  if (state.refreshToken) {
    try {
      await api("/auth/logout", {
        method: "POST",
        json: { refresh_token: state.refreshToken },
      });
    } catch (_) {
      // Local cleanup still happens when the server is unavailable.
    }
  }
  logoutLocal();
}

function showAuth() {
  $("#auth-view").classList.remove("hidden");
  $("#app-view").classList.add("hidden");
}

function showApp() {
  $("#auth-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  $("#sidebar-user").textContent = state.username ? `用户：${state.username}` : "ASRA";
  switchView("chat");
}

const viewMeta = {
  chat: ["穿搭助手", "根据天气、场景和偏好生成穿搭方案"],
  recommend: ["智能推荐", "基于衣柜和画像生成 Top N 穿搭"],
  wardrobe: ["数字衣柜", "管理衣物、标签和图片识别结果"],
  profile: ["用户画像", "维护风格、颜色、版型和场景偏好"],
  history: ["推荐历史", "查看历史推荐与用户记忆信号"],
};

function switchView(name) {
  $$(".view").forEach((view) => view.classList.remove("active"));
  $$(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === name);
  });
  const view = $(`#view-${name}`);
  if (view) {
    view.classList.add("active");
  }
  const [title, subtitle] = viewMeta[name] || ["", ""];
  $("#view-title").textContent = title;
  $("#view-subtitle").textContent = subtitle;

  if (name === "chat") {
    ensureWelcome();
    loadChatHistory();
  } else if (name === "recommend") {
    loadRecommend();
  } else if (name === "wardrobe") {
    loadWardrobe();
  } else if (name === "profile") {
    loadProfile();
  } else if (name === "history") {
    loadHistory();
  }
  refreshIcons();
}

function renderEmpty(container, message) {
  container.innerHTML = `<div class="empty-state">${esc(message)}</div>`;
}

function ensureWelcome() {
  const container = $("#chat-messages");
  if (!container.children.length) {
    container.innerHTML = `
      <div class="message assistant">
        <span class="message-meta">ASRA</span>
        <span class="message-content">你好，我是 ASRA 穿搭助手。告诉我城市、场景和风格，我会给出穿搭建议。</span>
      </div>`;
    refreshIcons();
  }
}

function formatWeather(weather) {
  if (!weather) return "未获取";
  return `${weather.city || ""} ${weather.temperature ?? ""}℃ ${weather.weather || ""} · ${weather.season || ""}`.trim();
}

function formalityLabel(level) {
  const labels = ["极休闲", "休闲", "商务休闲", "正式", "高正式"];
  return labels[level] || "";
}

function activityLabel(level) {
  const labels = ["静态", "低强度", "中等强度", "高强度"];
  return labels[level] || "";
}

function appendMessage(role, text) {
  const container = $("#chat-messages");
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.innerHTML = `
    <span class="message-meta">${role === "user" ? "我" : "ASRA"}</span>
    <span class="message-content">${esc(text)}</span>`;
  container.appendChild(node);
  container.scrollTop = container.scrollHeight;
}

function messageContentText(content) {
  if (typeof content === "string") return content;
  const data = content || {};
  if (data.text) return data.text;
  return JSON.stringify(data, null, 2);
}

function renderChatMessages(messages) {
  const container = $("#chat-messages");
  container.innerHTML = "";
  (messages || []).forEach((message) => {
    appendMessage(message.role, messageContentText(message.content));
  });
  if (!container.children.length) {
    ensureWelcome();
  }
}

function renderChatContext(reply) {
  const blocks = [
    ["城市 / 场景", `${reply?.city || ""} · ${reply?.occasion || ""}`],
    ["天气", formatWeather(reply?.weather)],
    [
      "场景解析",
      reply?.scene
        ? `${reply.scene.style || ""} / ${(reply.scene.occasion_tags || []).join(", ")}`
        : "",
    ],
    ["场景类型", reply?.scene?.scene_type || ""],
    ["正式程度", formalityLabel(reply?.scene?.formality)],
    ["活动量", activityLabel(reply?.scene?.activity_level)],
    ["工具计划", (reply?.tool_plan || []).join(" → ")],
    [
      "推荐摘要",
      (reply?.recommendation?.summary || []).join("，"),
    ],
    ["推荐单品", (reply?.recommendation?.items || []).map((item) => item.name).join("、")],
    [
      "场景提示",
      reply?.recommendation?.scene_feedback?.warning || "",
    ],
    [
      "建议补充",
      (reply?.recommendation?.scene_feedback?.suggestions || []).join("、"),
    ],
    ["历史 ID", reply?.history_id],
  ];
  const html = blocks
    .filter(([, value]) => value)
    .map(
      ([label, value]) => `
        <div class="context-block">
          <strong>${esc(label)}</strong>
          <span>${esc(value)}</span>
        </div>`,
    )
    .join("");
  $("#chat-context").innerHTML = html || `<div class="empty-state">暂无上下文</div>`;
}

async function loadChatHistory() {
  if (!state.sessionId) return;
  try {
    const data = await requestJson(
      `/chat/conversations/${encodeURIComponent(state.sessionId)}`,
    );
    renderChatMessages(data.messages);
  } catch (error) {
    if (error.status !== 404) {
      showToast(error.message, "error");
    }
  }
}

async function sendChat(event) {
  event.preventDefault();
  const input = $("#chat-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  appendMessage("user", message);

  const button = event.submitter || $("#chat-form button[type='submit']");
  setBusy(button, true, "思考中");
  try {
    const data = await requestJson("/chat/", {
      method: "POST",
      json: {
        session_id: state.sessionId || null,
        message,
      },
    });
    state.sessionId = data.session_id;
    localStorage.setItem("asra_session_id", state.sessionId);
    renderChatMessages(data.messages);
    renderChatContext(data.reply);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function loadRecommend() {
  const container = $("#recommend-results");
  container.innerHTML = `<div class="empty-state">正在生成推荐...</div>`;
  try {
    const data = await requestJson("/recommend/");
    state.recommendData = data;
    renderRecommendations(data);
  } catch (error) {
    renderEmpty(container, error.message);
  }
}

async function resetTestData() {
  if (!confirm("确认清空当前用户的对话、点赞和点踩记录？")) return;
  try {
    await requestJson("/feedback/", { method: "DELETE" });
    await requestJson("/chat/conversations", { method: "DELETE" });
    state.sessionId = "";
    localStorage.removeItem("asra_session_id");
    state.recommendData = null;
    const chatMessages = $("#chat-messages");
    if (chatMessages) {
      chatMessages.innerHTML = "";
    }
    ensureWelcome();
    loadRecommend();
    showToast("已重置对话和踩赞记录");
  } catch (error) {
    showToast(error.message || "重置失败", "error");
  }
}

function colorValue(name) {
  const map = {
    白色: "#f5f2ea",
    黑色: "#27221d",
    灰色: "#8a8a86",
    蓝色: "#3974b8",
    红色: "#c84a3a",
    绿色: "#3d7a4a",
    黄色: "#e4b83b",
    粉色: "#e59c9f",
    紫色: "#7d5d9c",
    橙色: "#d97a3c",
    棕色: "#7b5237",
    米色: "#d8c3a2",
  };
  return map[name] || "#c9c5bb";
}

function renderRecommendations(data) {
  const container = $("#recommend-results");
  const recommendations =
    data.recommendations && data.recommendations.length
      ? data.recommendations
      : [
          {
            outfit_score: data.recommendation?.outfit_score,
            items: data.recommendation?.items || [],
            summary: data.recommendation?.summary || [],
          },
        ];

  if (!recommendations.length) {
    renderEmpty(container, "暂无可用推荐");
    return;
  }

  container.innerHTML = recommendations
    .map(
      (recommendation, index) => `
        <article class="result-card">
          <div class="result-card-head">
            <strong>方案 ${index + 1}</strong>
            <span class="score-pill">${recommendation.outfit_score ?? 0} 分</span>
          </div>
          <div class="result-body">
            <div class="tag-row">
              ${(recommendation.summary || []).map((item) => `<span class="tag">${esc(item)}</span>`).join("")}
            </div>
            ${
              recommendation.scene_feedback?.warning
                ? `<div class="scene-warning">${esc(recommendation.scene_feedback.warning)}</div>`
                : ""
            }
            ${
              (recommendation.scene_feedback?.suggestions || []).length
                ? `<div class="tag-row">${recommendation.scene_feedback.suggestions.map((item) => `<span class="tag suggestion-tag">${esc(item)}</span>`).join("")}</div>`
                : ""
            }
            ${(recommendation.items || [])
              .map(
                (item) => `
                  <div class="outfit-item">
                    <span class="color-dot" style="background:${colorValue(item.color)}"></span>
                    <span>${esc(item.name || "未命名")} · ${esc(item.slot || "")}</span>
                  </div>`,
              )
              .join("")}
          </div>
          <div class="card-actions">
            <button type="button" class="secondary" data-feedback="like" data-index="${index}">
              <i data-lucide="thumbs-up"></i>
              <span>喜欢</span>
            </button>
            <button type="button" class="subtle" data-feedback="dislike" data-index="${index}">
              <i data-lucide="thumbs-down"></i>
              <span>不喜欢</span>
            </button>
          </div>
        </article>`,
    )
    .join("");
  refreshIcons();
}

async function sendFeedback(event) {
  const button = event.target.closest("[data-feedback]");
  if (!button || !state.recommendData) return;
  const index = Number(button.dataset.index || 0);
  const recommendations =
    state.recommendData.recommendations && state.recommendData.recommendations.length
      ? state.recommendData.recommendations
      : [state.recommendData.recommendation];
  const recommendation = recommendations[index] || recommendations[0];
  setBusy(button, true, "记录中");
  try {
    await requestJson("/feedback/", {
      method: "POST",
      json: {
        feedback_type: button.dataset.feedback,
        outfit_score: recommendation?.outfit_score || 0,
        outfit_snapshot: {
          items: (recommendation?.items || []).map((item) => item.name),
        },
        reason: recommendation?.summary || [],
      },
    });
    showToast(button.dataset.feedback === "like" ? "已记录喜欢" : "已记录不喜欢");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function loadWardrobe() {
  const container = $("#wardrobe-list");
  container.innerHTML = `<div class="empty-state">正在读取衣柜...</div>`;
  try {
    const items = await requestJson("/wardrobe/");
    if (!items.length) {
      renderEmpty(container, "衣柜还没有衣物");
      return;
    }
    container.innerHTML = items
      .map(
        (item) => `
          <div class="wardrobe-item">
            <span class="color-dot" style="background:${colorValue(item.color)}"></span>
            <div>
              <strong>${esc(item.name)}</strong>
              <small>${esc(item.category)} · ${esc(item.style)} · ${esc(item.season)} · ${esc(item.recognition_status || "manual")}</small>
              <div class="tag-row">
                ${(item.color_tags || []).map((tag) => `<span class="tag">${esc(tag)}</span>`).join("")}
                ${(item.occasion_tags || []).map((tag) => `<span class="tag">${esc(tag)}</span>`).join("")}
              </div>
            </div>
            <button type="button" class="subtle" data-delete-wardrobe="${item.id}">
              <i data-lucide="trash-2"></i>
            </button>
          </div>`,
      )
      .join("");
  } catch (error) {
    renderEmpty(container, error.message);
  }
  refreshIcons();
}

async function addWardrobe(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const payload = {
    name: data.get("name"),
    category: data.get("category"),
    color: data.get("color"),
    season: data.get("season"),
    style: data.get("style"),
    color_tags: splitTags(data.get("tags")),
    style_tags: splitTags(data.get("tags")),
    fit_tags: [],
    occasion_tags: [],
  };
  const button = form.querySelector("button[type='submit']");
  setBusy(button, true, "添加中");
  try {
    await requestJson("/wardrobe/add", { method: "POST", json: payload });
    form.reset();
    showToast("衣物已加入衣柜");
    await loadWardrobe();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function uploadWardrobe(event) {
  event.preventDefault();
  const fileInput = $("#wardrobe-file");
  if (!fileInput.files.length) return;
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  const button = event.submitter;
  setBusy(button, true, "识别中");
  try {
    const data = await requestJson("/wardrobe/analyze-image", {
      method: "POST",
      formData,
    });
    state.recognitionTask = {
      task_id: data.task_id,
      candidate: data.candidate,
    };
    showRecognitionConfirm(data.candidate);
    showToast("识别完成，请确认后入库");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function showRecognitionConfirm(candidate) {
  const form = $("#recognition-confirm-form");
  form.elements.name.value = candidate.name || "";
  form.elements.category.value = candidate.category || "";
  form.elements.color.value = candidate.color || "";
  form.elements.season.value = candidate.season || "";
  form.elements.style.value = candidate.style || "";
  form.elements.tags.value = [
    ...(candidate.color_tags || []),
    ...(candidate.style_tags || []),
    ...(candidate.fit_tags || []),
    ...(candidate.occasion_tags || []),
  ].join(", ");
  $("#recognition-confirm").classList.remove("hidden");
}

async function confirmRecognition(event) {
  event.preventDefault();
  if (!state.recognitionTask) return;
  const form = event.currentTarget;
  const data = new FormData(form);
  const payload = {
    name: data.get("name"),
    category: data.get("category"),
    color: data.get("color"),
    season: data.get("season"),
    style: data.get("style"),
    color_tags: splitTags(data.get("tags")),
    style_tags: [],
    fit_tags: [],
    occasion_tags: [],
  };
  const button = form.querySelector("button[type='submit']");
  setBusy(button, true, "保存中");
  try {
    await requestJson(`/wardrobe/task/${state.recognitionTask.task_id}`, {
      method: "PUT",
      json: payload,
    });
    await requestJson(`/wardrobe/confirm-task/${state.recognitionTask.task_id}`, {
      method: "POST",
    });
    $("#recognition-confirm").classList.add("hidden");
    $("#wardrobe-file").value = "";
    state.recognitionTask = null;
    showToast("已确认入库");
    await loadWardrobe();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function deleteWardrobe(event) {
  const button = event.target.closest("[data-delete-wardrobe]");
  if (!button) return;
  if (!window.confirm("确定删除这件衣物吗？")) return;
  setBusy(button, true, "删除中");
  try {
    await requestJson(`/wardrobe/${button.dataset.deleteWardrobe}`, {
      method: "DELETE",
    });
    showToast("衣物已删除");
    await loadWardrobe();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function fillProfile(data) {
  const form = $("#profile-form");
  form.elements.style.value = data.style || "";
  form.elements.favorite_color.value = data.favorite_color || "";
  form.elements.body_type.value = data.body_type || "";
  form.elements.season.value = data.season || "";
  form.elements.favorite_colors.value = (data.favorite_colors || []).join(", ");
  form.elements.style_tags.value = (data.style_tags || []).join(", ");
  form.elements.fit_tags.value = (data.fit_tags || []).join(", ");
  form.elements.avoid_colors.value = (data.avoid_colors || []).join(", ");
  form.elements.occasion_preferences.value = (data.occasion_preferences || []).join(", ");
}

async function loadProfile() {
  try {
    const data = await requestJson("/profile/me");
    state.profileMode = "update";
    fillProfile(data);
  } catch (error) {
    if (error.status === 404) {
      state.profileMode = "create";
      $("#profile-form").reset();
    } else {
      showToast(error.message, "error");
    }
  }
}

async function saveProfile(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const payload = {
    style: data.get("style"),
    favorite_color: data.get("favorite_color"),
    body_type: data.get("body_type"),
    season: data.get("season"),
    favorite_colors: splitTags(data.get("favorite_colors")),
    style_tags: splitTags(data.get("style_tags")),
    fit_tags: splitTags(data.get("fit_tags")),
    avoid_colors: splitTags(data.get("avoid_colors")),
    occasion_preferences: splitTags(data.get("occasion_preferences")),
  };
  const button = $("#profile-submit");
  setBusy(button, true, "保存中");
  try {
    if (state.profileMode === "create") {
      await requestJson("/profile/create", { method: "POST", json: payload });
      state.profileMode = "update";
    } else {
      await requestJson("/profile/me", { method: "PUT", json: payload });
    }
    showToast("画像已保存");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function memoryText(memory) {
  if (!memory) return "暂无记忆数据";
  const profile = memory.profile || {};
  const signals = memory.preference_signals || {};
  const feedback = memory.feedback_summary || {};
  const parts = [];
  if (profile.style) parts.push(`风格：${profile.style}`);
  if ((profile.favorite_colors || []).length) {
    parts.push(`喜欢颜色：${profile.favorite_colors.join("、")}`);
  }
  if ((signals.favorite_styles || []).length) {
    parts.push(`偏好信号：${signals.favorite_styles.join("、")}`);
  }
  if (feedback.like_count || feedback.dislike_count) {
    parts.push(`点赞 ${feedback.like_count || 0} / 点踩 ${feedback.dislike_count || 0}`);
  }
  return parts.length ? parts.join(" · ") : "暂无明确偏好信号";
}

async function loadHistory() {
  const container = $("#history-list");
  const memoryContainer = $("#memory-summary");
  container.innerHTML = `<div class="empty-state">正在读取历史...</div>`;
  memoryContainer.textContent = "正在读取记忆...";
  try {
    const [history, memory] = await Promise.all([
      requestJson("/history/"),
      requestJson("/memory/").catch(() => null),
    ]);
    memoryContainer.textContent = memoryText(memory);
    if (!history.length) {
      renderEmpty(container, "暂无推荐历史");
      return;
    }
    container.innerHTML = history
      .map(
        (item) => `
          <article class="history-card">
            <div class="result-card-head">
              <strong>历史 #${item.id}</strong>
              <span class="tag">${esc(item.request_context?.source || "recommend")}</span>
            </div>
            <div class="history-body">
              <div class="tag-row">
                ${(item.response_snapshot?.summary || []).map((summary) => `<span class="tag">${esc(summary)}</span>`).join("")}
              </div>
              ${(item.response_snapshot?.items || [])
                .map(
                  (entry) => `
                    <div class="outfit-item">
                      <span class="color-dot" style="background:${colorValue(entry.color)}"></span>
                      <span>${esc(entry.name || entry)}</span>
                    </div>`,
                )
                .join("")}
              <small style="color:var(--muted)">${esc(item.created_at || "")}</small>
            </div>
          </article>`,
      )
      .join("");
  } catch (error) {
    renderEmpty(container, error.message);
    memoryContainer.textContent = "记忆读取失败";
  }
}

function bindAuthTabs() {
  $$("[data-auth-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$("[data-auth-tab]").forEach((item) => item.classList.toggle("active", item === tab));
      const mode = tab.dataset.authTab;
      $("#login-form").classList.toggle("hidden", mode !== "login");
      $("#register-form").classList.toggle("hidden", mode !== "register");
    });
  });
}

async function login(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type='submit']");
  const data = new FormData(form);
  setBusy(button, true, "登录中");
  try {
    const tokens = await requestJson("/auth/login", {
      method: "POST",
      form: {
        username: data.get("username"),
        password: data.get("password"),
      },
    });
    saveTokens(tokens);
    state.username = data.get("username");
    localStorage.setItem("asra_username", state.username);
    showApp();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function register(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type='submit']");
  const data = new FormData(form);
  setBusy(button, true, "创建中");
  try {
    await requestJson("/user/register", {
      method: "POST",
      json: {
        email: data.get("email"),
        username: data.get("username"),
        password: data.get("password"),
      },
    });
    const tokens = await requestJson("/auth/login", {
      method: "POST",
      form: {
        username: data.get("username"),
        password: data.get("password"),
      },
    });
    saveTokens(tokens);
    state.username = data.get("username");
    localStorage.setItem("asra_username", state.username);
    showApp();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function refreshCurrentView() {
  const active = $(".nav-item.active");
  if (active) {
    switchView(active.dataset.view);
  }
}

function init() {
  bindAuthTabs();
  $("#login-form").addEventListener("submit", login);
  $("#register-form").addEventListener("submit", register);
  $("#logout-btn").addEventListener("click", logout);
  $("#refresh-btn").addEventListener("click", refreshCurrentView);
  $$(".nav-item").forEach((item) => {
    item.addEventListener("click", () => switchView(item.dataset.view));
  });
  $("#chat-form").addEventListener("submit", sendChat);
  $("#recommend-btn").addEventListener("click", loadRecommend);
  $("#reset-test-btn").addEventListener("click", resetTestData);
  $("#recommend-results").addEventListener("click", sendFeedback);
  $("#wardrobe-add-form").addEventListener("submit", addWardrobe);
  $("#wardrobe-upload-form").addEventListener("submit", uploadWardrobe);
  $("#recognition-confirm-form").addEventListener("submit", confirmRecognition);
  $("#wardrobe-list").addEventListener("click", deleteWardrobe);
  $("#profile-form").addEventListener("submit", saveProfile);

  if (state.accessToken) {
    showApp();
  } else {
    showAuth();
  }
  refreshIcons();
}

document.addEventListener("DOMContentLoaded", init);
