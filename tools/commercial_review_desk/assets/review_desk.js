(function () {
  "use strict";

  const VIEW_SCHEMA = "termivar-analyst-review-desk-view/v1";
  const DRAFT_SCHEMA = "termivar-analyst-decision-draft/v1";
  const DEMO_LABEL = "DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED";
  const MAX_BYTES = 256 * 1024;
  const MAX_TEXT_BYTES = 128 * 1024;
  const REVIEW = [
    ["unreviewed", "İncelenmedi", "Henüz insan inceleme kararı bulunmuyor."],
    ["needs_manual_review", "İnsan incelemesi gerekiyor", "Ek insan incelemesi gerekiyor; doğrulanmış bulgu değildir."],
    ["informational_only", "Yalnız bilgilendirme", "Bilgi amaçlı insan sınıflandırması; otomatik zafiyet değildir."],
    ["inconclusive", "Sonuçlandırılamadı", "Mevcut bilgiyle kesin sonuç çıkarılamıyor."],
    ["excluded_with_reason", "Gerekçeyle hariç", "Açık gerekçeyle müşteri çıktısı dışında; kaynak kaydı silinmez."],
    ["reviewed_for_delivery", "Teslim açısından incelendi", "Bağımsız teknik doğrulama veya gerçek teslim izni değildir."]
  ];
  const SCOPE = [
    ["unknown", "Bilinmiyor"], ["in_scope", "Kapsam içinde (beyan)"], ["out_of_scope", "Kapsam dışında (beyan)"]
  ];
  const INCLUSION = [
    ["pending_decision", "Karar bekliyor"], ["include_with_limits", "Sınırlarıyla dahil et (beyan)"],
    ["exclude_with_reason", "Gerekçeyle hariç tut"]
  ];
  const DISPOSITION = {
    informational: "Bilgilendirici kaynak gözlemi", needs_review: "Kaynak inceleme adayı",
    confirmed: "Kaynağın confirmed etiketi; bağımsız onay değil"
  };
  const REQUIREMENTS = {
    human_review_required: "Gerçek insan incelemesi gerekiyor.",
    scope_basis_required: "Kapsam dayanağı belirlenmeli.",
    evidence_access_and_limitations_required: "Kanıt erişimi ve sınırlamaları incelenmeli.",
    client_inclusion_decision_required: "Müşteri dahil etme kararı ayrıca verilmeli.",
    safe_wording_review_required: "Müşteriye yönelik metin ayrıca incelenmeli."
  };
  const BLOCKERS = {
    demo_only_not_for_delivery: "Yalnız demo; müşteri teslimine uygun değil.",
    human_review_not_verified: "İnsan incelemesi bağımsız doğrulanmadı.",
    producer_not_verified: "Üretici kimliği doğrulanmadı.",
    authorization_not_verified: "Çalışma yetkisi doğrulanmadı.",
    data_handling_pending_decision: "Veri işleme kararları bekliyor.",
    release_not_authorized: "Teslim veya yayın yetkisi verilmedi."
  };
  const TEXT_FIELDS = [
    ["safe_summary", "Güvenli müşteri özeti", 2048],
    ["reason", "İç karar gerekçesi", 2048],
    ["missing_evidence", "Eksik kanıt açıklaması", 1024],
    ["follow_up", "Gelecekteki takip notu", 1024]
  ];
  const app = document.getElementById("desk-app");
  if (!app) return;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function button(text, className, action) {
    const node = element("button", className || "button button-secondary", text);
    node.type = "button";
    node.addEventListener("click", action);
    return node;
  }
  function hasExactKeys(value, names) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value);
    return keys.length === names.length && names.every(function (key) { return Object.hasOwn(value, key); });
  }
  function fullMatch(expression, value) {
    if (typeof value !== "string") return false;
    const match = expression.exec(value);
    return match !== null && match[0] === value;
  }
  function enumHas(options, value) { return options.some(function (entry) { return entry[0] === value; }); }
  function enumLabel(options, value) {
    const option = options.find(function (entry) { return entry[0] === value; });
    return option ? option[1] : "Mevcut sonuçta bulunmuyor";
  }
  function shortFingerprint(value) { return value.slice(0, 19) + "…" + value.slice(-10); }

  function readProjection() {
    const dataNode = document.getElementById("desk-data");
    if (!dataNode) throw new Error("desk_data_missing");
    const encoded = dataNode.textContent.trim();
    if (!encoded || encoded.length > Math.ceil(MAX_BYTES / 3) * 4 + 4 || !fullMatch(/^[A-Za-z0-9+/]*={0,2}$/, encoded)) {
      throw new Error("desk_data_invalid");
    }
    const binary = atob(encoded);
    if (binary.length > MAX_BYTES) throw new Error("desk_data_size");
    const bytes = Uint8Array.from(binary, function (c) { return c.charCodeAt(0); });
    const value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    const keys = ["schema_version", "review_packet_digest", "source_assessment_digest", "demo_label", "source",
      "observations", "review_requirements", "delivery_blockers", "demo_only", "human_review_verified", "producer_verified", "release_authorized"];
    if (!hasExactKeys(value, keys) || value.schema_version !== VIEW_SCHEMA || value.demo_label !== DEMO_LABEL || value.demo_only !== true ||
        value.human_review_verified !== false || value.producer_verified !== false || value.release_authorized !== false ||
        !fullMatch(/^[a-f0-9]{64}$/, value.review_packet_digest) || !fullMatch(/^[a-f0-9]{64}$/, value.source_assessment_digest) ||
        !hasExactKeys(value.source, ["profile", "status", "item_count", "manifest_status", "source_verification"]) ||
        value.source.profile !== "web-review" || value.source.status !== "complete" || value.source.source_verification !== "phase17_file_binding_only" ||
        !["not_provided", "partial_json_entry_match"].includes(value.source.manifest_status) ||
        !Array.isArray(value.observations) || value.observations.length > 256 ||
        !Number.isSafeInteger(value.source.item_count) || value.source.item_count !== value.observations.length) throw new Error("desk_projection_invalid");
    const ids = new Set();
    const sourceKeys = new Set();
    value.observations.forEach(function (row, index) {
      if (!hasExactKeys(row, ["observation_id", "observation_key", "source_json_pointer", "fingerprint", "capability_id", "source_disposition", "review_status", "scope_status", "client_inclusion"]) ||
          !fullMatch(/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/, row.observation_id) || row.source_json_pointer !== "/items/" + index ||
          row.observation_key !== "sha256:" + value.source_assessment_digest + "#" + row.source_json_pointer ||
          !fullMatch(/^sha256:[a-f0-9]{64}$/, row.fingerprint) || !fullMatch(/^[A-Za-z0-9._@-]{1,128}$/, row.capability_id) ||
          !Object.hasOwn(DISPOSITION, row.source_disposition) || row.review_status !== "unreviewed" || row.scope_status !== "unknown" ||
          row.client_inclusion !== "pending_decision" || ids.has(row.observation_id) || sourceKeys.has(row.observation_key)) throw new Error("desk_observation_invalid");
      ids.add(row.observation_id);
      sourceKeys.add(row.observation_key);
      Object.freeze(row);
    });
    if (!Array.isArray(value.review_requirements) || !value.review_requirements.every(function (code) { return Object.hasOwn(REQUIREMENTS, code); }) ||
        !Array.isArray(value.delivery_blockers) || !value.delivery_blockers.every(function (code) { return Object.hasOwn(BLOCKERS, code); })) throw new Error("desk_limits_invalid");
    Object.freeze(value.source);
    Object.freeze(value.observations);
    Object.freeze(value.review_requirements);
    Object.freeze(value.delivery_blockers);
    return Object.freeze(value);
  }

  let view;
  try { view = readProjection(); }
  catch (_) {
    app.replaceChildren(element("p", "error-note", "İnceleme verisi açılamadı. Bu belgede karar oluşturulmadı; orijinal packet ile yeniden hazırlayın."));
    return;
  }

  const byKey = new Map(view.observations.map(function (row) { return [row.observation_key, row]; }));
  const drafts = new Map();
  const objectUrls = new Set();
  const encoder = new TextEncoder();
  let selectedKey = view.observations.length ? view.observations[0].observation_key : null;
  let baseline = null;
  let dirty = false;
  let fullFingerprint = false;
  let clearRequested = false;
  const fields = {};
  const counters = {};

  const toolbar = element("section", "desk-toolbar");
  toolbar.setAttribute("aria-label", "Bellekteki karar taslağı");
  const draftCount = element("p", "draft-summary");
  const exportButton = button("Karar taslağını indir", "button button-primary", exportDraft);
  const clearButton = button("Bellekteki taslağı temizle", "button button-secondary", requestClear);
  const toolbarActions = element("div", "actions");
  toolbarActions.append(exportButton, clearButton);
  toolbar.append(draftCount, toolbarActions);
  const notice = element("p", "status-note", "Hiçbir karar oluşturulmadı. Boş taslak indirilebilir.");
  notice.setAttribute("role", "status");
  notice.setAttribute("aria-live", "polite");
  const boundaryNote = element("p", "field-hint", "İndirilen JSON yalnız karar taslağıdır. Tarayıcı denetimleri kullanım yardımıdır; Python finalize_desk.py orijinal packet ve manifest ile nihai sözleşme/bağlama kontrolünü yeniden yapar. Bu sayfa overlay digest'i veya inceleme onayı üretmez.");
  const confirmClear = element("section", "warning-note");
  confirmClear.hidden = true;
  const clearActions = element("div", "actions");
  clearActions.append(button("Belleği temizlemeyi onayla", "button button-danger", function () {
    if (!clearRequested) return;
    resetWorkspace("Bu sayfadaki taslak temizlendi. İndirilmiş dosyalar değişmez; güvenli silme yapıldığı anlamına gelmez.");
  }), button("Vazgeç", "button button-secondary", function () { clearRequested = false; confirmClear.hidden = true; }));
  confirmClear.append(element("p", "", "Kaydedilmemiş alanlar ve bu sayfadaki bütün taslak kayıtları kaldırılacak. Bu işlem indirilmiş dosyaları silmez."), clearActions);
  const grid = element("div", "desk-grid");

  function panel(className, title) {
    const node = element("section", "desk-panel " + className);
    const heading = element("div", "panel-heading");
    heading.append(element("h2", "", title));
    node.append(heading);
    return node;
  }
  const listPanel = panel("observation-panel", "Kaynak gözlemler");
  const filterArea = element("div", "panel-body");
  const searchField = element("div", "field");
  const searchLabel = element("label", "field-label", "Kaynak metadata'sında ara");
  searchLabel.htmlFor = "desk-search";
  const search = element("input", "field-control");
  search.id = "desk-search";
  search.type = "search";
  search.maxLength = 128;
  search.autocomplete = "off";
  search.placeholder = "ID, capability veya fingerprint";
  searchField.append(searchLabel, search);
  const filterField = element("div", "field");
  const filterLabel = element("label", "field-label", "İnsan durumu (taslak dahil)");
  filterLabel.htmlFor = "desk-filter";
  const filter = element("select", "field-control");
  filter.id = "desk-filter";
  const allOption = element("option", "", "Tüm durumlar");
  allOption.value = "all";
  filter.append(allOption);
  REVIEW.forEach(function (option) {
    const node = element("option", "", option[1] + " · " + option[0]);
    node.value = option[0];
    filter.append(node);
  });
  filterField.append(filterLabel, filter);
  const listCount = element("p", "list-meta");
  filterArea.append(searchField, filterField, listCount);
  const list = element("ul", "observation-list panel-scroll");
  const listButtons = new Map();
  list.setAttribute("aria-label", "Kaynak gözlem listesi");
  listPanel.append(filterArea, list);

  const detailPanel = panel("detail-panel", "Salt okunur kaynak ayrıntısı");
  const detailBody = element("div", "panel-body panel-scroll");
  detailPanel.append(detailBody);
  const editorPanel = panel("editor-panel", "Karar taslağı editörü");
  const editorBody = element("div", "panel-body");
  const editorName = element("p", "selected-name");
  const editorHint = element("p", "field-hint", "Kaynak alanları değişmez. Bir durum seçmek diğer alanlara karar vermez; bu sayfa reviewer veya zaman üretmez.");
  const form = element("form", "editor-form");
  form.autocomplete = "off";
  form.addEventListener("submit", function (event) { event.preventDefault(); });

  function addSelect(name, label, options) {
    const wrapper = element("div", "field");
    const title = element("label", "field-label", label);
    title.htmlFor = "editor-" + name;
    const control = element("select", "field-control");
    control.id = title.htmlFor;
    options.forEach(function (entry) {
      const option = element("option", "", entry[1] + " · " + entry[0]);
      option.value = entry[0];
      control.append(option);
    });
    control.addEventListener("change", refreshDirty);
    wrapper.append(title, control);
    fields[name] = control;
    form.append(wrapper);
  }
  addSelect("review_status", "İnsan inceleme durumu", REVIEW);
  addSelect("scope_status", "Kapsam durumu — ayrı beyan", SCOPE);
  addSelect("client_inclusion", "Müşteri dahil etme — ayrı karar", INCLUSION);
  TEXT_FIELDS.forEach(function (entry) {
    const wrapper = element("div", "field");
    const title = element("label", "field-label", entry[1]);
    title.htmlFor = "editor-" + entry[0];
    const control = element("textarea", "field-control");
    control.id = title.htmlFor;
    control.rows = entry[0] === "safe_summary" ? 4 : 3;
    // Native control limit counts UTF-16 units; the exact code-point limit is
    // checked separately before any row can be added or exported.
    control.maxLength = entry[2] * 2;
    control.spellcheck = false;
    const hint = element("p", "field-hint");
    hint.id = control.id + "-hint";
    control.setAttribute("aria-describedby", hint.id);
    control.addEventListener("input", refreshDirty);
    wrapper.append(title, control, hint);
    fields[entry[0]] = control;
    counters[entry[0]] = hint;
    form.append(wrapper);
  });
  const formError = element("p", "field-error");
  formError.setAttribute("role", "alert");
  formError.hidden = true;
  const editorStatus = element("p", "status-note");
  const applyButton = button("Taslağa ekle", "button button-primary", applyDraft);
  const revertButton = button("Alanları geri al", "button button-secondary", function () {
    loadEditor();
    announce("Alanlar bu gözlemin son taslağına veya paket başlangıcına döndürüldü.");
  });
  const removeButton = button("Bu gözlemin taslağını kaldır", "button button-secondary", function () {
    if (dirty) { announce("Önce kaydedilmemiş alanları geri alın veya taslağı güncelleyin.", true); return; }
    drafts.delete(selectedKey);
    loadEditor(); renderList(); refreshToolbar();
    announce("Bu gözlemin taslak kaydı kaldırıldı; kaynak gözlem değişmedi.");
  });
  const editActions = element("div", "actions editor-footer");
  editActions.append(applyButton, revertButton, removeButton);
  form.append(formError, editorStatus, editActions);
  const meanings = element("section", "review-meanings");
  meanings.append(element("h3", "", "İnsan durumları ne anlama gelir?"));
  const meaningsList = element("dl", "metadata-list");
  REVIEW.forEach(function (entry) { meaningsList.append(element("dt", "mono", entry[0]), element("dd", "", entry[2])); });
  meanings.append(meaningsList, element("p", "field-hint", "Termivar NeedsReview ve KnowledgeOnly bu insan kararlarının yerine geçmez. Dahil etme tercihi her zaman ayrıdır."));
  editorBody.append(editorName, editorHint, form, meanings,
    element("p", "warning-note", "Serbest metinlerde otomatik redaksiyon veya sır taraması yoktur. Gerçek müşteri verisi, credential, token veya ham kanıt girmeyin."));
  editorPanel.append(editorBody);
  grid.append(listPanel, detailPanel, editorPanel);
  app.replaceChildren(toolbar, notice, boundaryNote, confirmClear, grid);

  function announce(message, warning) {
    notice.className = warning ? "warning-note" : "status-note";
    notice.textContent = message;
  }
  function defaultForm(row) {
    return { review_status: row.review_status, scope_status: row.scope_status, client_inclusion: row.client_inclusion,
      safe_summary: "", reason: "", missing_evidence: "", follow_up: "" };
  }
  function captureForm() {
    return { review_status: fields.review_status.value, scope_status: fields.scope_status.value,
      client_inclusion: fields.client_inclusion.value, safe_summary: fields.safe_summary.value,
      reason: fields.reason.value, missing_evidence: fields.missing_evidence.value, follow_up: fields.follow_up.value };
  }
  function loadEditor() {
    const row = byKey.get(selectedKey);
    const saved = drafts.get(selectedKey);
    baseline = row ? (saved ? {
      review_status: saved.review_status, scope_status: saved.scope_status, client_inclusion: saved.client_inclusion,
      safe_summary: saved.safe_summary === null ? "" : saved.safe_summary,
      reason: saved.reason === null ? "" : saved.reason,
      missing_evidence: saved.missing_evidence === null ? "" : saved.missing_evidence,
      follow_up: saved.follow_up === null ? "" : saved.follow_up
    } : defaultForm(row)) : null;
    Object.keys(fields).forEach(function (name) {
      fields[name].disabled = !row;
      fields[name].value = baseline ? baseline[name] : (name === "review_status" ? "unreviewed" : name === "scope_status" ? "unknown" : name === "client_inclusion" ? "pending_decision" : "");
    });
    editorName.textContent = row ? "Seçili kaynak: " + row.observation_id : "Seçili kaynak yok";
    formError.hidden = true;
    formError.textContent = "";
    dirty = false;
    refreshDirty();
  }
  function refreshDirty() {
    dirty = baseline !== null && JSON.stringify(captureForm()) !== JSON.stringify(baseline);
    TEXT_FIELDS.forEach(function (entry) {
      counters[entry[0]].textContent = Array.from(fields[entry[0]].value).length + " / " + entry[2] + " karakter · en fazla 16 satır · boş bırakılırsa null";
    });
    applyButton.textContent = drafts.has(selectedKey) ? "Taslağı güncelle" : "Taslağa ekle";
    applyButton.disabled = !selectedKey || !dirty;
    revertButton.disabled = !dirty;
    removeButton.disabled = !drafts.has(selectedKey) || dirty;
    editorStatus.textContent = dirty ? "Kaydedilmemiş düzenleme var. İndirme ve gözlem değiştirme kapalı." :
      drafts.has(selectedKey) ? "Bu gözlem için yalnız sayfa belleğinde taslak var." : "Bu gözlem için karar taslağı oluşturulmadı.";
    refreshToolbar();
  }
  function refreshToolbar() {
    draftCount.textContent = "Bellekte " + drafts.size + " karar taslağı · " + view.observations.length + " kaynak gözlem · doğrulanmış insan kararı yok";
    exportButton.disabled = dirty;
    clearButton.disabled = !dirty && drafts.size === 0;
  }
  function visibleRows() {
    const query = search.value.toLocaleLowerCase("tr");
    return view.observations.filter(function (row) {
      const draft = drafts.get(row.observation_key);
      const humanStatus = draft ? draft.review_status : row.review_status;
      const haystack = [row.observation_id, row.observation_key, row.capability_id, row.fingerprint,
        row.source_disposition, humanStatus, row.client_inclusion].join(" ").toLocaleLowerCase("tr");
      return (filter.value === "all" || humanStatus === filter.value) && (!query || haystack.includes(query));
    });
  }
  function renderList() {
    const rows = visibleRows();
    listCount.textContent = rows.length + " / " + view.observations.length + " kaynak gözlem gösteriliyor";
    list.replaceChildren();
    listButtons.clear();
    if (!rows.length) list.append(element("li", "empty-state", "Bu arama ve durum filtresiyle eşleşen kaynak gözlem yok."));
    rows.forEach(function (row) {
      const item = element("li");
      const choose = button("", "observation-button", function () {
        if (row.observation_key === selectedKey) return;
        if (dirty) { announce("Kaydedilmemiş alanlar var. Önce taslağa ekleyin veya alanları geri alın; kaynak seçimi değişmedi.", true); return; }
        selectedKey = row.observation_key;
        fullFingerprint = false;
        renderList(); renderDetails(); loadEditor();
        listButtons.get(row.observation_key).focus({ preventScroll: true });
        announce(row.observation_id + " seçildi. Kaynak alanları salt okunurdur.");
      });
      choose.setAttribute("aria-pressed", String(row.observation_key === selectedKey));
      listButtons.set(row.observation_key, choose);
      choose.append(element("strong", "", row.observation_id), element("span", "mono", row.capability_id),
        element("span", "source-badge", DISPOSITION[row.source_disposition] + " · " + row.source_disposition),
        element("span", "mono", shortFingerprint(row.fingerprint)),
        element("span", "list-meta", "Paket: " + row.review_status + " · " + row.client_inclusion),
        element("span", "list-meta", "Eksik: uzman incelemesi ve dahil etme kararı"));
      const draft = drafts.get(row.observation_key);
      if (draft) choose.append(element("span", "badge", "Taslak: " + enumLabel(REVIEW, draft.review_status) + " · " + draft.client_inclusion));
      item.append(choose); list.append(item);
    });
  }
  function metadata(rows) {
    const node = element("dl", "metadata-list");
    rows.forEach(function (row) { node.append(element("dt", "", row[0]), element("dd", "mono", row[1])); });
    return node;
  }
  function renderDetails(focusFingerprint) {
    const row = byKey.get(selectedKey);
    detailBody.replaceChildren();
    if (!row) { detailBody.append(element("p", "empty-state", "Bu packet'ta seçilebilecek gözlem yok.")); return; }
    detailBody.append(element("p", "selected-name", row.observation_id),
      element("p", "source-badge", "KAYNAK METADATA'SI · DÜZENLENEMEZ"),
      metadata([["Capability", row.capability_id], ["Category", "Mevcut sonuçta bulunmuyor"],
        ["Native disposition", row.source_disposition], ["Kaynak JSON pointer", row.source_json_pointer],
        ["Ayrıntılı kaynak kanıtı", "Mevcut sonuçta bulunmuyor"],
        ["Kaynak assessment SHA256", view.source_assessment_digest], ["Kalıcı kaynak anahtarı", row.observation_key],
        ["Review packet SHA256", view.review_packet_digest]]));
    const fingerprintBox = element("div", "fingerprint-box");
    fingerprintBox.append(element("p", "field-label", "Kaynak fingerprint — kaynak anahtarından ayrı"),
      element("p", "mono", fullFingerprint ? row.fingerprint : shortFingerprint(row.fingerprint)));
    const reveal = button(fullFingerprint ? "Fingerprint'i kısalt" : "Tam fingerprint'i göster", "button button-secondary", function () {
      fullFingerprint = !fullFingerprint; renderDetails(true);
    });
    reveal.setAttribute("aria-expanded", String(fullFingerprint));
    fingerprintBox.append(reveal);
    detailBody.append(fingerprintBox, metadata([["Profil", view.source.profile], ["Kaynak tamamlanma etiketi", view.source.status],
      ["Packet'taki kaynak öğe sayısı", String(view.source.item_count)], ["Manifest ilişkisi", view.source.manifest_status],
      ["Kaynak doğrulama kapsamı", view.source.source_verification], ["Paket insan durumu", row.review_status],
      ["Paket kapsam durumu", row.scope_status], ["Paket dahil etme kararı", row.client_inclusion]]),
      element("p", "warning-note", "Complete, eksiksiz kapsam veya güvenli sistem değildir. JSON-entry manifest ilişkisi tam bundle/üretici doğrulaması değildir. Hash ve fingerprint insan kararını veya bulgu doğruluğunu kanıtlamaz; aynı fingerprint farklı pointer'ları birleştirmez."));
    detailBody.append(element("h3", "", "İnceleme gereksinimleri"));
    const requirements = element("ul");
    view.review_requirements.forEach(function (code) { requirements.append(element("li", "", REQUIREMENTS[code])); });
    detailBody.append(requirements, element("h3", "", "Açık teslim engelleri"));
    const blockers = element("ul");
    view.delivery_blockers.forEach(function (code) { blockers.append(element("li", "", BLOCKERS[code])); });
    detailBody.append(blockers);
    if (focusFingerprint) reveal.focus({ preventScroll: true });
  }
  function validUnicode(value) {
    for (let index = 0; index < value.length; index += 1) {
      const code = value.charCodeAt(index);
      if (code >= 0xd800 && code <= 0xdbff) {
        index += 1;
        const next = value.charCodeAt(index);
        if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
      } else if (code >= 0xdc00 && code <= 0xdfff) return false;
    }
    return true;
  }
  function nullableText(value, maximum, label) {
    if (value === "") return null;
    if (!validUnicode(value) || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/u.test(value)) throw new Error(label + ": geçersiz Unicode veya kontrol karakteri.");
    if (/^[\t\n\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/u.test(value)) throw new Error(label + ": yalnız boşluk kullanmayın; alanı tamamen boş bırakın.");
    if (Array.from(value).length > maximum) throw new Error(label + ": karakter sınırı aşıldı.");
    if (value.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n").length > 16) throw new Error(label + ": en fazla 16 satır kullanılabilir.");
    return value;
  }
  function decisionFromForm() {
    if (!byKey.has(selectedKey)) throw new Error("Geçerli kaynak gözlem seçilmedi.");
    const current = captureForm();
    if (!enumHas(REVIEW, current.review_status) || !enumHas(SCOPE, current.scope_status) || !enumHas(INCLUSION, current.client_inclusion)) throw new Error("İzinli durum değerlerini seçin.");
    const decision = { observation_key: selectedKey, review_status: current.review_status, scope_status: current.scope_status,
      client_inclusion: current.client_inclusion, safe_summary: null, reason: null, missing_evidence: null, follow_up: null };
    TEXT_FIELDS.forEach(function (entry) { decision[entry[0]] = nullableText(current[entry[0]], entry[2], entry[1]); });
    if (decision.client_inclusion === "include_with_limits" &&
        (!["informational_only", "reviewed_for_delivery"].includes(decision.review_status) || decision.scope_status !== "in_scope" || decision.safe_summary === null)) {
      throw new Error("Dahil etme için uygun insan durumu, açık kapsam içi beyanı ve müşteri özeti ayrı ayrı gerekir. Hiçbiri otomatik seçilmez.");
    }
    if ((decision.review_status === "excluded_with_reason" || decision.client_inclusion === "exclude_with_reason") && decision.reason === null) throw new Error("Hariç bırakma için açık gerekçe gerekir.");
    return Object.freeze(decision);
  }
  function draftDocument(candidate) {
    return { schema_version: DRAFT_SCHEMA, review_packet_digest: view.review_packet_digest,
      source_assessment_digest: view.source_assessment_digest,
      decisions: view.observations.map(function (row) { return candidate.get(row.observation_key); }).filter(function (row) { return row !== undefined; }) };
  }
  function checkedDraftJson(value) {
    const stack = [{ value: value, depth: 1 }];
    let nodes = 0;
    let textBytes = 0;
    while (stack.length) {
      const entry = stack.pop();
      nodes += 1;
      if (nodes > 10000 || entry.depth > 12) throw new Error("Taslak düğüm veya derinlik sınırını aşıyor; kayıtlar kesilmedi.");
      if (typeof entry.value === "string") {
        if (!validUnicode(entry.value) || Array.from(entry.value).length > 8192) throw new Error("Taslak metni sınırı aşıyor veya geçersiz Unicode içeriyor.");
        textBytes += encoder.encode(entry.value).length;
        if (textBytes > MAX_TEXT_BYTES) throw new Error("Taslak toplam 128 KiB metin bütçesini aşıyor; kayıtlar kesilmedi.");
      } else if (Array.isArray(entry.value)) {
        entry.value.forEach(function (item) { stack.push({ value: item, depth: entry.depth + 1 }); });
      } else if (entry.value !== null && typeof entry.value === "object") {
        Object.keys(entry.value).forEach(function (key) {
          stack.push({ value: key, depth: entry.depth + 1 });
          stack.push({ value: entry.value[key], depth: entry.depth + 1 });
        });
      }
    }
    const serialized = JSON.stringify(value, null, 2) + "\n";
    if (encoder.encode(serialized).length > MAX_BYTES) throw new Error("Taslak 256 KiB dosya sınırını aşıyor; kayıtlar kesilmedi.");
    return serialized;
  }
  function applyDraft() {
    if (!dirty) return;
    try {
      const decision = decisionFromForm();
      const candidate = new Map(drafts);
      candidate.set(selectedKey, decision);
      checkedDraftJson(draftDocument(candidate));
      drafts.set(selectedKey, decision);
      loadEditor(); renderList(); refreshToolbar();
      formError.hidden = true;
      announce("Karar taslağı yalnız sayfa belleğine eklendi. İnceleme veya teslim onayı değildir.");
    } catch (error) {
      formError.textContent = error.message;
      formError.hidden = false;
      announce("Taslağa eklenmedi. İşaretlenen alanları düzeltin; kaynak kayıt değişmedi.", true);
    }
  }
  function exportDraft() {
    if (dirty) { announce("Kaydedilmemiş alanlar varken indirme yapılmaz. Taslağa ekleyin veya alanları geri alın.", true); return; }
    try {
      const serialized = checkedDraftJson(draftDocument(drafts));
      const blob = new Blob([serialized], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      objectUrls.add(url);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "termivar-decision-draft.json";
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(function () { URL.revokeObjectURL(url); objectUrls.delete(url); }, 1000);
      announce("İndirme isteği oluşturuldu; dosyanın kaydedildiğini tarayıcıdan kontrol edin. Bu JSON taslaktır, Phase18 overlay'i değildir.");
    } catch (_) { announce("İndirme isteği oluşturulamadı. Sayfa belleğindeki kayıtlar korunuyor; kayıt işlemi doğrulanmadı.", true); }
  }
  function requestClear() { clearRequested = true; confirmClear.hidden = false; }
  function resetWorkspace(message) {
    drafts.clear();
    objectUrls.forEach(function (url) { URL.revokeObjectURL(url); });
    objectUrls.clear();
    selectedKey = view.observations.length ? view.observations[0].observation_key : null;
    fullFingerprint = false;
    clearRequested = false;
    confirmClear.hidden = true;
    search.value = "";
    filter.value = "all";
    renderList(); renderDetails(); loadEditor(); refreshToolbar();
    announce(message);
  }
  search.addEventListener("input", renderList);
  filter.addEventListener("change", renderList);
  window.addEventListener("beforeunload", function (event) {
    if (dirty || drafts.size) { event.preventDefault(); event.returnValue = ""; }
  });
  window.addEventListener("pagehide", function () { resetWorkspace("Yeni sayfa oturumunda önceki karar taslakları otomatik yüklenmez."); });
  renderList(); renderDetails(); loadEditor(); refreshToolbar();
}());
