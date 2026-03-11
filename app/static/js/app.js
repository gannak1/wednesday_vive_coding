const pagePayloadNode = document.getElementById("page-payload");
const payload = pagePayloadNode ? JSON.parse(pagePayloadNode.textContent || "{}") : {};
const pageName = document.body.dataset.page;
const WORLD_BOUNDS = [[-60, -180], [85, 180]];
const IMPACT_LABELS = {
    oil: "유가",
    energy: "에너지",
    gold: "금",
    shipping: "해운",
    supply_chain: "공급망",
    supplychain: "공급망",
    transport: "교통",
    industry: "산업",
    fx: "환율",
    rates: "금리",
    equities: "주식시장",
    stocks: "주식시장",
    policy: "정책",
    trade: "무역",
    sentiment: "시장 심리",
    market: "시장",
    inflation: "물가",
    currency: "통화",
    bonds: "채권",
    logistics: "물류",
};

let mapContext = null;

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("map")) {
        mapContext = createMap("map");
    }

    if (pageName === "home") {
        initializeHomePage();
    }
    if (pageName === "category") {
        initializeCategoryPage();
    }
    if (pageName === "my-articles") {
        initializeSavedArticlesPage();
    }
});

function initializeHomePage() {
    renderMarkers(payload.map_pins || [], handleArticleSelection, { fitMode: "world" });
    bindArticleSelection(document.querySelectorAll("#headline-list .article-selectable"));

    const form = document.getElementById("home-search-form");
    if (!form) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const query = document.getElementById("search-query").value.trim();
        if (!query) {
            return;
        }
        const response = await apiFetch(`/api/news/search?q=${encodeURIComponent(query)}`);
        renderSearchResults(response.data.articles || []);
        renderMarkers(response.data.articles || [], handleArticleSelection, { fitMode: "markers" });
    });
}

function initializeCategoryPage() {
    renderMarkers(payload.articles || [], handleCategorySelection, { fitMode: "world" });
    bindArticleSelection(document.querySelectorAll("#category-article-list .article-selectable"), handleCategorySelection);
}

function initializeSavedArticlesPage() {
    bindArticleSelection(document.querySelectorAll("#saved-article-list .saved-card"), handleSavedArticleSelection);
    document.querySelectorAll(".delete-saved-button").forEach((button) => {
        button.addEventListener("click", async (event) => {
            event.stopPropagation();
            const savedId = button.dataset.savedId;
            await apiFetch(`/api/articles/saved/${savedId}`, { method: "DELETE" });
            button.closest(".saved-card")?.remove();
            ensureEmptyState("saved-article-list", "저장된 기사가 없습니다.");
            resetDetailPanel("저장 기사를 선택해 주세요.");
        });
    });
}

function bindArticleSelection(nodes, handler = handleArticleSelection) {
    nodes.forEach((node) => {
        node.addEventListener("click", () => {
            const articleId = node.dataset.articleId;
            if (articleId) {
                handler(articleId);
            }
        });
    });
}

async function handleArticleSelection(articleId) {
    const article = await fetchArticle(articleId);
    renderDetailPanel(article, null, { showSave: true });
}

async function handleCategorySelection(articleId) {
    const [article, analysis] = await Promise.all([fetchArticle(articleId), fetchAnalysis(articleId)]);
    renderDetailPanel(article, analysis, { showSave: true });
}

async function handleSavedArticleSelection(articleId) {
    const [article, analysis] = await Promise.all([fetchArticle(articleId), fetchAnalysis(articleId)]);
    renderDetailPanel(article, analysis, { showSave: false });
}

async function fetchArticle(articleId) {
    const response = await apiFetch(`/api/news/${articleId}`);
    return response.data;
}

async function fetchAnalysis(articleId) {
    const response = await apiFetch(`/api/news/${articleId}/analysis`);
    return response.data;
}

async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    const data = await response.json();
    if (!response.ok || data.success === false) {
        throw new Error(data.message || "요청 처리 중 오류가 발생했습니다.");
    }
    return data;
}

function renderSearchResults(articles) {
    const container = document.getElementById("search-results");
    if (!container) {
        return;
    }

    if (!articles.length) {
        container.innerHTML = '<div class="empty-state">검색 결과가 없습니다.</div>';
        return;
    }

    container.innerHTML = articles
        .map(
            (article) => `
            <article class="list-card article-selectable" data-article-id="${article.id}">
                <div>
                    <p class="meta-row"><span class="badge ${article.category}">${escapeHtml(article.category_label ?? article.category)}</span> ${escapeHtml(article.source ?? "")}</p>
                    <h3>${escapeHtml(article.title)}</h3>
                    <p>${escapeHtml(article.summary ?? "")}</p>
                </div>
                <div class="stat-pill importance-${article.importance}">중요도 ${article.importance ?? "-"}</div>
            </article>
        `,
        )
        .join("");

    bindArticleSelection(container.querySelectorAll(".article-selectable"));
}

function renderDetailPanel(article, analysis, options = { showSave: false }) {
    const panel = document.getElementById("article-detail-panel");
    if (!panel) {
        return;
    }

    const analysisSection = analysis
        ? renderAnalysisSection(analysis)
        : '<div class="analysis-box"><h4>기사 정보</h4><p>홈 화면에서는 기사 기본 상세만 표시됩니다.</p></div>';

    const saveAction = options.showSave
        ? `<button type="button" id="save-article-button" data-article-id="${article.id}">기사 저장</button>`
        : "";

    const contentSection = article.content
        ? `
            <div class="analysis-box">
                <h4>본문</h4>
                <p>${renderParagraphs(article.content)}</p>
            </div>
        `
        : "";

    panel.innerHTML = `
        <div class="detail-card">
            <div class="detail-head">
                <div>
                    <p class="meta-row"><span class="badge ${article.category}">${escapeHtml(article.category_label ?? article.category)}</span> ${escapeHtml(article.source ?? "")}</p>
                    <h2>${escapeHtml(article.title)}</h2>
                </div>
                ${saveAction}
            </div>
            <div class="detail-meta">
                <span>${escapeHtml(article.continent ?? "대륙 미상")}</span>
                <span>${escapeHtml(article.region ?? article.country ?? "지역 미상")}</span>
                <span>${escapeHtml(article.published_at ?? "")}</span>
            </div>
            <div class="analysis-box">
                <h4>요약</h4>
                <p>${renderParagraphs(article.summary ?? "")}</p>
            </div>
            ${contentSection}
            ${analysisSection}
        </div>
    `;

    const saveButton = document.getElementById("save-article-button");
    if (saveButton) {
        saveButton.addEventListener("click", async () => {
            const response = await apiFetch("/api/articles/save", {
                method: "POST",
                body: JSON.stringify({ article_id: article.id }),
            });
            saveButton.textContent = response.data.already_saved ? "이미 저장됨" : "저장됨";
            saveButton.disabled = true;
        });
    }
}

function renderAnalysisSection(analysis) {
    if (analysis.ai_status === "pending") {
        return '<div class="analysis-box"><h4>AI 분석</h4><p>AI 분석 준비 중입니다.</p></div>';
    }

    if (analysis.ai_status === "failed") {
        return '<div class="analysis-box"><h4>AI 분석</h4><p>AI 분석을 불러오지 못했습니다.</p></div>';
    }

    const impacts = normalizeImpactEntries(analysis.impact)
        .map(([label, value]) => `<div><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value)}</span></div>`)
        .join("");

    return `
        <div class="analysis-grid">
            <div class="analysis-box">
                <h4>AI 해석</h4>
                <p>${escapeHtml(analysis.interpretation ?? "")}</p>
            </div>
            <div class="analysis-box">
                <h4>예상 동향</h4>
                <p>${escapeHtml(analysis.prediction ?? "")}</p>
            </div>
            <div class="analysis-box">
                <h4>미치는 영향</h4>
                <div class="impact-list">${impacts || "<p>영향 데이터가 없습니다.</p>"}</div>
            </div>
        </div>
    `;
}

function normalizeImpactEntries(impact) {
    if (!impact || typeof impact !== "object" || Array.isArray(impact)) {
        return [];
    }

    return Object.entries(impact)
        .map(([rawLabel, rawValue]) => {
            const label = localizeImpactLabel(rawLabel);
            const value = normalizeImpactValue(rawValue);
            return label && value ? [label, value] : null;
        })
        .filter(Boolean)
        .slice(0, 3);
}

function localizeImpactLabel(label) {
    if (typeof label !== "string") {
        return "";
    }
    const key = label.trim().toLowerCase().replaceAll("-", "_").replaceAll(" ", "_");
    return IMPACT_LABELS[key] ?? label.trim();
}

function normalizeImpactValue(value) {
    if (typeof value === "string") {
        return value.trim();
    }
    if (typeof value === "number") {
        return String(value);
    }
    if (value && typeof value === "object") {
        for (const key of ["effect", "summary", "description", "value", "impact"]) {
            if (typeof value[key] === "string" && value[key].trim()) {
                return value[key].trim();
            }
        }
    }
    return "";
}

function resetDetailPanel(message) {
    const panel = document.getElementById("article-detail-panel");
    if (!panel) {
        return;
    }
    panel.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function ensureEmptyState(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    if (container.children.length === 0) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    }
}

function createMap(containerId) {
    const map = L.map(containerId, {
        worldCopyJump: true,
        scrollWheelZoom: false,
        zoomSnap: 0.25,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    map.fitBounds(WORLD_BOUNDS, { padding: [8, 8] });

    return {
        map,
        layerGroup: L.layerGroup().addTo(map),
    };
}

function renderMarkers(items, clickHandler, options = {}) {
    if (!mapContext) {
        return;
    }

    const fitMode = options.fitMode ?? "markers";
    mapContext.layerGroup.clearLayers();
    const bounds = [];

    items.filter((item) => item.lat && item.lng).forEach((item) => {
        const marker = L.circleMarker([item.lat, item.lng], {
            radius: markerRadius(item.pin_size),
            color: item.pin_color || "#334155",
            fillColor: item.pin_color || "#334155",
            fillOpacity: 0.82,
            weight: 2,
        });
        marker.bindPopup(`<strong>${escapeHtml(item.title)}</strong>`);
        marker.on("click", () => clickHandler(item.id));
        marker.addTo(mapContext.layerGroup);
        bounds.push([item.lat, item.lng]);
    });

    if (fitMode === "markers" && bounds.length > 0) {
        mapContext.map.fitBounds(bounds, { padding: [40, 40] });
        return;
    }

    mapContext.map.fitBounds(WORLD_BOUNDS, { padding: [8, 8] });
}

function markerRadius(pinSize) {
    if (pinSize === "large") {
        return 12;
    }
    if (pinSize === "medium") {
        return 9;
    }
    return 6;
}

function renderParagraphs(value) {
    return String(value)
        .split(/\n+/)
        .filter((line) => line.trim())
        .map((line) => escapeHtml(line.trim()))
        .join("<br><br>");
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
