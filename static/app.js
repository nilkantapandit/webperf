const $ = (id) => document.getElementById(id);

async function csrfFetch(url, options = {}) {
  const opts = {...options, headers: {...(options.headers || {})}};
  const token = window.WEBPERF_STATE?.csrfToken;
  if (token) opts.headers["X-CSRFToken"] = token;
  return fetch(url, opts);
}

function refreshIcons(){
  if (window.lucide) window.lucide.createIcons({attrs:{"stroke-width":1.8}});
}

function initScrollReveal(){
  const items = document.querySelectorAll(".reveal-on-scroll");
  if (!items.length) return;
  if (!("IntersectionObserver" in window)) { items.forEach(el => el.classList.add("is-visible")); return; }
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); }
    });
  }, {threshold:0.08, rootMargin:"0px 0px -40px 0px"});
  items.forEach(el => observer.observe(el));
}

function initCookieBanner(){
  const key = "webperf-cookie-notice-v1";
  const banner = $("cookieBanner");
  if (!banner || localStorage.getItem(key)) return;
  banner.classList.remove("hidden");
  const close = () => { localStorage.setItem(key, "seen"); banner.classList.add("hidden"); };
  $("cookieEssentialOnly")?.addEventListener("click", close);
  $("cookieAccept")?.addEventListener("click", close);
}

function initLiveCheckCounter(){
  const counter = $("checksLastHour");
  if(!counter) return;
  const target = Math.max(0, Number(counter.dataset.count || 0));
  const duration = Math.min(1600, Math.max(650, target * 8));
  const started = performance.now();
  const tick = now => {
    const progress = Math.min(1, (now - started) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    counter.textContent = Math.round(target * eased).toLocaleString();
    if(progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
let currentReport = null;
let currentFilter = "all";
let openIssueIds = new Set();
const REPORT_STORAGE_KEY = "webperf:last-report-v1";
const PENDING_ANALYSIS_KEY = "webperf:pending-analysis-v1";
function saveReportLocally(report){ try { sessionStorage.setItem(REPORT_STORAGE_KEY, JSON.stringify(report)); } catch {} }
function savePendingAnalysis(){
  const url = currentReport?.finalUrl || currentReport?.url || normalizeUrl($("urlInput")?.value || "");
  if(!url) return;
  try { sessionStorage.setItem(PENDING_ANALYSIS_KEY, JSON.stringify({url, strategy: $("strategy")?.value || "mobile"})); } catch {}
}
function clearPendingAnalysis(){ try { sessionStorage.removeItem(PENDING_ANALYSIS_KEY); } catch {} }
function restoreLocalReport(){
  try{
    const raw = sessionStorage.getItem(REPORT_STORAGE_KEY);
    if(!raw) return false;
    const report = JSON.parse(raw);
    if(report?.url && report?.scores) { renderReport(report); return true; }
  }catch{}
  return false;
}

function scoreClass(score){ if(score == null) return "neutral"; if(score >= 90) return "good"; if(score >= 50) return "warn"; return "poor"; }
function scoreLabel(score){ if(score == null) return "Unavailable"; if(score >= 90) return "Good"; if(score >= 50) return "Needs attention"; return "Needs work"; }
function esc(value){ return String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c])); }
function hostFromUrl(url){ try{return new URL(url).hostname.replace(/^www\./,'')}catch{return url} }

function competitorHost(value){
  const raw = String(value || "").trim();
  if(!raw) return "";
  try{
    const parsed = new URL(/^https?:\/\//i.test(raw) ? raw : `https://${raw}`);
    return parsed.hostname.toLowerCase().replace(/^www\./, "").replace(/\.$/, "");
  }catch{
    return raw.toLowerCase().replace(/^https?:\/\//, "").replace(/^www\./, "").split("/")[0].replace(/\.$/, "");
  }
}

function dedupeCompetitors(list){
  const seen = new Set();
  return (Array.isArray(list) ? list : []).filter(item => {
    const domain = competitorHost(item?.domain || item?.url);
    if(!domain || seen.has(domain)) return false;
    seen.add(domain);
    item.domain = domain;
    return true;
  });
}

function normalizeUrl(value){
  let url = String(value || "").trim();
  if(!url) return "";
  if(!/^https?:\/\//i.test(url)) url = "https://" + url;
  try{
    const parsed = new URL(url);
    return parsed.href.replace(/\/$/, "");
  }catch{return url;}
}

function setTheme(theme){
  document.body.dataset.theme = theme;
  localStorage.setItem("webperf-theme", theme);
  $("themeText").textContent = theme === "dark" ? "Light" : "Dark";
  const icon = $("themeIcon");
  if(icon){ icon.setAttribute("data-lucide", theme === "dark" ? "sun" : "moon"); icon.textContent = ""; }
  refreshIcons();
  window.dispatchEvent(new CustomEvent("webperf-theme-change", {detail:{theme}}));
}
if($("themeToggle")){
  setTheme(localStorage.getItem("webperf-theme") || "dark");
  $("themeToggle").addEventListener("click", () => setTheme(document.body.dataset.theme === "dark" ? "light" : "dark"));
}

let loadingTimer = null;
function setLoading(on){
  document.body.classList.toggle("diagnostic-view", on);
  $("hero").classList.toggle("hidden", on);
  $("loadingState").classList.toggle("hidden", !on);
  $("results").classList.add("hidden");
  $("errorBox").classList.add("hidden");
  $("analyzeBtn").disabled = on;
  const steps = [...document.querySelectorAll(".loading-steps span")];
  if(loadingTimer){ clearInterval(loadingTimer); loadingTimer=null; }
  if(on){
    let current=0;
    const paint=()=>steps.forEach((step,i)=>{step.classList.toggle("active",i===current);step.classList.toggle("complete",i<current);});
    paint();
    loadingTimer=setInterval(()=>{ if(current<steps.length-1){current+=1;paint();} },2600);
  }else{
    steps.forEach((step,i)=>{step.classList.toggle("active",i===steps.length-1);step.classList.toggle("complete",i<steps.length-1);});
  }
}

function setScoreCard(key, score){
  const card = document.querySelector(`[data-card="${key}"]`);
  const scoreEl = $(`${key}Score`); const bar = $(`${key}Bar`); const badge = $(`${key}Badge`);
  card.classList.remove("good","warn","poor");
  const cls = scoreClass(score); card.classList.add(cls);
  scoreEl.textContent = score ?? "—"; badge.textContent = scoreLabel(score);
  bar.style.width = `${score ?? 0}%`;
}

function renderGauge(score){
  const degrees = Math.max(0, Math.min(100, score || 0)) * 3.6;
  const color = score >= 90 ? "var(--good)" : score >= 50 ? "var(--warn)" : "var(--bad)";
  $("gauge").style.background = `conic-gradient(${color} 0deg, ${color} ${degrees}deg, var(--gauge-track) ${degrees}deg)`;
  $("overallScore").textContent = score ?? "—";
  $("overallLabel").textContent = scoreLabel(score);
  $("overallLabel").style.color = color;
  if(score >= 90){
    $("overallHeadline").textContent = "Your website is in good shape.";
    $("overallDescription").textContent = "Most important checks look healthy. The remaining items are opportunities for further improvement.";
  }else if(score >= 50){
    $("overallHeadline").textContent = "There are a few things worth improving.";
    $("overallDescription").textContent = "You don't need to fix everything at once. Start with the items marked as needing attention, then check again.";
  }else{
    $("overallHeadline").textContent = "Your website has some important issues.";
    $("overallDescription").textContent = "Start with the highest-impact items. Improving a few of these can make the site noticeably faster and easier to use.";
  }
}

function renderVitals(vitals){
  const grid = $("vitalsGrid");
  if(!vitals?.length){ grid.innerHTML = `<div class="empty-issues">No speed measurements were returned for this check.</div>`; return; }
  grid.innerHTML = vitals.map(v => {
    const pct = v.score == null ? null : Math.round(v.score * 100);
    const cls = scoreClass(pct);
    return `<article class="vital"><div class="vital-top"><span class="vital-name">${esc(v.title)}</span><span class="vital-score ${cls}">${pct == null ? "Measured" : pct >= 90 ? "Looks good" : pct >= 50 ? "Needs attention" : "Needs work"}</span></div><div class="vital-value">${esc(v.value || "—")}</div><div class="vital-id">${esc(v.id)}</div></article>`;
  }).join("");
}

function issueKey(issue, index){
  return `${issue.category}-${issue.id || index}`;
}

function buildIssueCards(issues, openSet = openIssueIds){
  return issues.map((issue, index) => {
    const key = issueKey(issue, index);
    const open = openSet.has(key);
    const severityText = issue.severity === "high" ? "Fix first" : issue.severity === "medium" ? "Worth improving" : "Small improvement";
    return `<article class="issue-card ${esc(issue.severity)} ${open ? "open" : ""}" data-issue-key="${esc(key)}">
      <button class="issue-toggle" type="button" aria-expanded="${open}">
        <span class="severity-dot ${esc(issue.severity)}"></span>
        <span class="issue-main"><span class="issue-title">${esc(issue.title)}</span><span class="issue-desc">${esc(issue.description || "This check needs a closer look.")}</span></span>
        <span class="severity-label">${severityText}</span><span class="issue-chevron"><i data-lucide="chevron-down" aria-hidden="true"></i></span>
      </button>
      <div class="issue-detail ${open ? "visible" : ""}">
        <div class="plain-detail"><b>What this means</b><p>${esc(issue.description || "This check did not meet the recommended threshold.")}</p></div>
        <div class="plain-detail"><b>Why it happens</b><p>${esc(issue.whyItHappens || "This can happen for several reasons depending on how the website is built.")}</p></div>
        <div class="plain-detail"><b>What you can do</b><p>${esc(issue.howToImprove || "Review this item and run the check again after making a change.")}</p></div>
        <details class="technical-detail"><summary>Technical detail</summary><p>${esc(issue.technicalDescription || issue.id || "Lighthouse audit")}${issue.displayValue ? ` <span>(${esc(issue.displayValue)})</span>` : ""}</p></details>
      </div>
    </article>`;
  }).join("");
}

function renderIssues(){
  const list = $("issuesList");
  const issues = (currentReport?.issues || []).filter(i => currentFilter === "all" || i.category === currentFilter);
  if(!issues.length){ list.innerHTML = `<div class="empty-issues">Nothing needs attention in this area. That's a good sign.</div>`; return; }
  list.innerHTML = buildIssueCards(issues);
  refreshIcons();
}

function getRecommendation(){
  const score = currentReport?.overall ?? 0;
  const high = currentReport?.issueCounts?.critical ?? 0;
  if(score < 30 || high >= 6) return "rebuild";
  if(score < 60 || high >= 3) return "review";
  return "optimize";
}

function updateDecision(){
  const recommendation = getRecommendation();
  document.querySelectorAll(".decision-card").forEach(card => card.classList.remove("recommended"));
  const target = recommendation === "rebuild" ? document.querySelectorAll(".decision-card")[1] : document.querySelectorAll(".decision-card")[0];
  if(target) target.classList.add("recommended");
}

let industryDetectionInFlight = false;
let industryManualOverride = false;
let industryDetectionRequestId = 0;
let industryDetectionController = null;

function resetIndustryDetection(){
  industryManualOverride = false;
  industryDetectionInFlight = false;
  industryDetectionRequestId += 1;
  if(industryDetectionController){
    industryDetectionController.abort();
    industryDetectionController = null;
  }
  const detected = $("detectedIndustry");
  const reason = $("industryReason");
  const confidence = $("industryConfidence");
  const field = $("competitorIndustry");
  const button = $("findCompetitors");
  if(detected) detected.textContent = "Detecting your industry…";
  if(reason) reason.textContent = "We're looking at your website to understand what kind of business it is.";
  if(confidence) confidence.textContent = "";
  if(field){ field.value = ""; field.classList.add("hidden"); }
  if(button) button.disabled = true;
}

function renderReport(data){
  currentReport = data;
  saveReportLocally(data);
  clearPendingAnalysis(); currentFilter = "all"; openIssueIds = new Set();
  competitorResults = []; competitorComparisons = []; showAllCompetitors = false;
  if($("competitorResults")) $("competitorResults").innerHTML = "";
  if($("competitorStatus")) $("competitorStatus").classList.add("hidden");
  if($("comparisonWrap")) $("comparisonWrap").classList.add("hidden");
  resetIndustryDetection();
  $("reportUrl").textContent = hostFromUrl(data.finalUrl || data.url);
  $("reportMeta").textContent = `Google PageSpeed · ${data.strategy === "desktop" ? "Desktop" : "Mobile"}${data.fetchTime ? " · " + new Date(data.fetchTime).toLocaleString() : ""}`;
  setScoreCard("performance", data.scores.performance);
  setScoreCard("accessibility", data.scores.accessibility);
  setScoreCard("bestPractices", data.scores.bestPractices);
  setScoreCard("seo", data.scores.seo);
  renderGauge(data.overall);
  $("criticalCount").textContent = data.issueCounts.critical;
  $("warningCount").textContent = data.issueCounts.warnings;
  $("passedCount").textContent = data.issueCounts.passed;
  $("vitalsAlert").classList.toggle("hidden", !data.coreWebVitalsFailing);
  renderVitals(data.vitals); renderIssues(); updateDecision();
  document.querySelectorAll(".filter").forEach(btn => btn.classList.toggle("active", btn.dataset.filter === "all"));
  document.body.classList.add("diagnostic-view");
  $("hero").classList.add("hidden"); $("loadingState").classList.add("hidden"); $("errorBox").classList.add("hidden"); $("results").classList.remove("hidden");
  window.scrollTo({top:0, behavior:"smooth"});
  if(window.WEBPERF_STATE?.premium){ detectWebsiteIndustry(data.finalUrl || data.url); }
}

async function detectWebsiteIndustry(website){
  const detected = $("detectedIndustry");
  const reason = $("industryReason");
  const confidence = $("industryConfidence");
  const field = $("competitorIndustry");
  const button = $("findCompetitors");
  if(!detected || !reason || !field) return;

  const requestId = ++industryDetectionRequestId;
  if(industryDetectionController) industryDetectionController.abort();
  industryDetectionController = new AbortController();
  const controller = industryDetectionController;

  industryDetectionInFlight = true;
  if(button) button.disabled = true;
  field.classList.add("hidden");
  detected.textContent = "Detecting your industry…";
  reason.textContent = "We're looking at your website to understand what kind of business it is.";
  if(confidence) confidence.textContent = "";

  try{
    const response = await csrfFetch("/api/website-profile", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({website, pageTitle: currentReport?.pageTitle || ""}),
      signal: controller.signal
    });
    const data = await response.json();
    if(requestId !== industryDetectionRequestId) return;
    if(!response.ok) throw new Error(data.error || "Industry detection is unavailable.");

    const confidenceValue = String(data.confidence || "low").toLowerCase();
    const formattedConfidence = confidenceValue === "high" ? "High confidence" : confidenceValue === "medium" ? "Medium confidence" : "Low confidence";

    detected.textContent = data.industry || "General Business";
    reason.textContent = data.reason || "Based on the website's public search results.";
    if(confidence) confidence.textContent = formattedConfidence;

    if(!industryManualOverride){ field.value = data.industry || ""; }
    field.classList.toggle("hidden", !industryManualOverride);
  }catch(error){
    if(error.name === "AbortError" || requestId !== industryDetectionRequestId) return;
    detected.textContent = "We need a little help";
    reason.textContent = "We couldn't confidently identify the business category from the public homepage. Choose Edit if you want to set it manually.";
    if(confidence) confidence.textContent = "Needs input";
    field.value = "";
    field.classList.add("hidden");
  }finally{
    if(requestId !== industryDetectionRequestId) return;
    industryDetectionInFlight = false;
    if(industryDetectionController === controller) industryDetectionController = null;
    if(button) button.disabled = !String(field.value || "").trim();
  }
}

async function analyze(){
  let url = normalizeUrl($("urlInput").value);
  const strategy = $("strategy").value;
  if(!url) return;
  $("urlInput").value = url;
  $("urlNote").textContent = `Checking ${hostFromUrl(url)} securely with Google PageSpeed.`;
  resetIndustryDetection();
  competitorResults = [];
  competitorComparisons = [];
  if($("competitorResults")) $("competitorResults").innerHTML = "";
  if($("competitorStatus")) $("competitorStatus").classList.add("hidden");
  if($("comparisonWrap")) $("comparisonWrap").classList.add("hidden");
  setLoading(true);
  try{
    const response = await csrfFetch("/api/analyze", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({url, strategy})});
    const data = await response.json();
    if(!response.ok) throw new Error(data.error || "Unable to check the website.");
    renderReport(data);
  }catch(error){
    document.body.classList.remove("diagnostic-view");
    $("hero").classList.remove("hidden"); $("loadingState").classList.add("hidden"); $("results").classList.add("hidden"); $("errorBox").classList.remove("hidden"); $("errorText").textContent = error.message;
  }finally{$("analyzeBtn").disabled = false;}
}

$("urlInput").addEventListener("blur", () => {
  const value = $("urlInput").value.trim();
  if(value && !/^https?:\/\//i.test(value)) $("urlInput").value = "https://" + value;
});

$("analyzeForm").addEventListener("submit", e => { e.preventDefault(); analyze(); });
$("newAnalysis").addEventListener("click", () => { try{sessionStorage.removeItem(REPORT_STORAGE_KEY);sessionStorage.removeItem(PENDING_ANALYSIS_KEY);}catch{} $("results").classList.add("hidden"); $("hero").classList.remove("hidden"); $("urlNote").textContent = "You can type example.com — we'll add https:// automatically."; $("urlInput").focus(); window.scrollTo({top:0,behavior:"smooth"}); });
$("errorRetry").addEventListener("click", analyze);

$("filterRow").addEventListener("click", e => {
  const btn=e.target.closest(".filter"); if(!btn) return;
  currentFilter=btn.dataset.filter;
  document.querySelectorAll(".filter").forEach(x=>x.classList.toggle("active",x===btn));
  renderIssues();
});

$("issuesList").addEventListener("click", e => {
  const button = e.target.closest(".issue-toggle");
  if(!button) return;
  const card = button.closest(".issue-card");
  const key = card.dataset.issueKey;
  if(openIssueIds.has(key)) openIssueIds.delete(key);
  else openIssueIds.add(key);
  renderIssues();
});


function buildHtmlReport(){
  if(!currentReport) return;
  const report = $("results").cloneNode(true);
  const reportIssues = report.querySelector("#issuesList");
  if(reportIssues){
    const allIssues = currentReport.issues || [];
    const allOpen = new Set(allIssues.map((issue, index) => issueKey(issue, index)));
    reportIssues.innerHTML = buildIssueCards(allIssues, allOpen);
  }

  // A downloaded report is a record, not an interactive app.
  report.querySelector("#newAnalysis")?.remove();
  report.querySelector("#filterRow")?.remove();
  report.querySelector("#viewVitals")?.remove();
  report.querySelector("#contactButton")?.remove();
  report.querySelectorAll("button").forEach(btn => btn.remove());

  const style = document.createElement("style");
  style.textContent = Array.from(document.styleSheets)
    .map(sheet => { try { return Array.from(sheet.cssRules).map(rule => rule.cssText).join("\n"); } catch { return ""; } })
    .join("\n");

  const meta = currentReport.finalUrl || currentReport.url || "Website report";
  const generated = new Date().toLocaleString();
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Website report — ${esc(hostFromUrl(meta))}</title>${style.outerHTML}</head><body data-theme="${esc(document.body.dataset.theme || "dark")}"><main class="shell report-export"><div class="export-brand"><strong>WebPerf Diagnostics</strong><span>Website report · ${esc(generated)}</span></div>${report.outerHTML}</main></body></html>`;
  const blob = new Blob([html], {type:"text/html;charset=utf-8"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${hostFromUrl(meta).replace(/[^a-z0-9.-]+/gi,"-") || "website"}-website-report.html`;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

$("downloadReport").addEventListener("click", buildHtmlReport);

$("viewVitals").addEventListener("click", () => $("vitals").scrollIntoView({behavior:"smooth", block:"start"}));

function openContact(){
  $("contactModal").classList.remove("hidden");
  $("contactModal").setAttribute("aria-hidden", "false");
  $("contactFormView").classList.remove("hidden");
  $("contactSuccess").classList.add("hidden");
  $("contactError").classList.add("hidden");
  const website = currentReport?.finalUrl || currentReport?.url || $("urlInput").value;
  $("contactWebsite").value = normalizeUrl(website);
  const signedInEmail = window.WEBPERF_STATE?.email || "";
  if(signedInEmail) $("contactEmail").value = signedInEmail;
  document.body.classList.add("modal-open");
  setTimeout(() => $("contactName").focus(), 50);
}
function closeContact(){
  $("contactModal").classList.add("hidden");
  $("contactModal").setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

$("contactButton").addEventListener("click", openContact);
$("contactClose").addEventListener("click", closeContact);
$("contactCancel").addEventListener("click", closeContact);
$("successClose").addEventListener("click", closeContact);
$("contactModal").addEventListener("click", e => { if(e.target === $("contactModal")) closeContact(); });
document.addEventListener("keydown", e => { if(e.key === "Escape" && !$("contactModal").classList.contains("hidden")) closeContact(); });

$("contactForm").addEventListener("submit", async e => {
  e.preventDefault();
  const website = normalizeUrl($("contactWebsite").value);
  $("contactWebsite").value = website;
  const payload = {
    name: $("contactName").value.trim(),
    email: $("contactEmail").value.trim(),
    website,
    helpWith: $("contactHelp").value,
    message: $("contactMessage").value.trim(),
    ageConfirmed: $("contactAge").checked,
  };
  $("contactError").classList.add("hidden");
  $("contactSubmit").disabled = true;
  $("contactSubmit").textContent = "Sending…";
  try{
    const response = await csrfFetch("/api/contact", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
    const data = await response.json();
    if(!response.ok) throw new Error(data.error || "We couldn't send your request.");
    $("contactFormView").classList.add("hidden");
    $("contactSuccess").classList.remove("hidden");
  }catch(error){
    $("contactError").textContent = error.message;
    $("contactError").classList.remove("hidden");
  }finally{
    $("contactSubmit").disabled = false;
    $("contactSubmit").innerHTML = '<i data-lucide="send" aria-hidden="true"></i> Send request'; refreshIcons();
  }
});

const footerYear = document.getElementById("footerYear");
if (footerYear) footerYear.textContent = new Date().getFullYear();

// Premium competitor discovery, comparison and one-time unlock.
let competitorResults = [];
let competitorComparisons = [];

function setCompetitorStatus(message, type = "info"){
  const el = $("competitorStatus");
  if(!el) return;
  el.textContent = message;
  el.className = `competitor-status ${type}`;
  el.classList.remove("hidden");
}

let selectedCompetitorDomains = new Set();
let comparisonInFlight = false;
let showAllCompetitors = false;
const MAX_COMPARATORS = 4;
const INITIAL_COMPETITOR_RESULTS = 6;

function renderCompetitors(results){
  const wrap = $("competitorResults");
  if(!wrap) return;
  const own = competitorHost(currentReport?.finalUrl || currentReport?.url || "");
  const uniqueResults = dedupeCompetitors(results).filter(item => competitorHost(item.domain || item.url) !== own);
  competitorResults = uniqueResults;
  selectedCompetitorDomains = new Set([...selectedCompetitorDomains].filter(d => uniqueResults.some(x => competitorHost(x.domain || x.url) === d)));
  if(!uniqueResults.length){
    wrap.innerHTML = `<div class="competitor-empty"><i data-lucide="search-x" aria-hidden="true"></i><span>We couldn't find likely competitors for that search. Try a more specific industry or region.</span></div>`;
    refreshIcons(); updateCompareBar(); return;
  }
  const visibleResults = showAllCompetitors ? uniqueResults : uniqueResults.slice(0, INITIAL_COMPETITOR_RESULTS);
  const hiddenCount = Math.max(0, uniqueResults.length - visibleResults.length);
  wrap.innerHTML = visibleResults.map((item, index) => {
    const domain = competitorHost(item.domain || item.url);
    const selected = selectedCompetitorDomains.has(domain);
    return `<article class="competitor-card ${selected ? "selected" : ""}">
      <div class="competitor-card-body">
        <div class="competitor-card-top"><span class="competitor-index">${index + 1}</span><span class="competitor-domain">${esc(domain)}</span></div>
        <h3>${esc(item.title)}</h3>
        <p>${esc(item.snippet || item.address || "Business website")}</p>
      </div>
      <div class="competitor-card-actions">
        <a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer"><i data-lucide="external-link" aria-hidden="true"></i> Visit site</a>
        <button type="button" class="compare-competitor${selected ? " added" : ""}" data-domain="${esc(domain)}" data-url="${esc(item.url)}">${selected ? '<i data-lucide="check" aria-hidden="true"></i> Selected' : '<i data-lucide="plus" aria-hidden="true"></i> Select'}</button>
      </div>
    </article>`;
  }).join("");
  if(hiddenCount > 0){
    wrap.insertAdjacentHTML("beforeend", `<div class="competitor-more-wrap"><button type="button" class="competitor-more-btn" id="showMoreCompetitors"><i data-lucide="chevrons-down" aria-hidden="true"></i> Show ${hiddenCount} more result${hiddenCount === 1 ? "" : "s"}</button></div>`);
  }
  refreshIcons(); updateCompareBar();
}

function updateCompareBar(){
  const bar = $("compareSelectionBar");
  const count = selectedCompetitorDomains.size;
  if(!bar) return;
  if(!count){ bar.classList.add("hidden"); return; }
  bar.classList.remove("hidden");
  $("compareSelectionCount").textContent = `${count} of ${MAX_COMPARATORS} selected`;
  const button = $("compareSelectedBtn");
  if(button){
    button.innerHTML = comparisonInFlight
      ? `<span class="comparison-spinner" aria-hidden="true"></span> Comparing…`
      : `<i data-lucide="play" aria-hidden="true"></i> Compare selected (${count})`;
    button.disabled = comparisonInFlight;
  }
  refreshIcons();
}

function updateComparisonProgress(completed, total, domain = "") {
  const panel = $("comparisonProgress");
  if(!panel) return;
  const count = $("comparisonProgressCount");
  const bar = $("comparisonProgressBar");
  const text = $("comparisonProgressText");
  const safeTotal = Math.max(0, Number(total) || 0);
  const safeCompleted = Math.min(Math.max(0, Number(completed) || 0), safeTotal);
  if(count) count.textContent = `${safeCompleted} of ${safeTotal} finished`;
  if(bar) bar.style.width = `${safeTotal ? (safeCompleted / safeTotal) * 100 : 0}%`;
  if(text){
    text.textContent = safeCompleted >= safeTotal && safeTotal > 0
      ? "All selected websites have finished checking. Preparing your comparison…"
      : domain
        ? `Checking ${domain}. ${safeCompleted} of ${safeTotal} finished.`
        : `Checking ${safeTotal} selected website${safeTotal === 1 ? "" : "s"}…`;
  }
}

function showComparisonProgress(total){
  const panel = $("comparisonProgress");
  if(panel) panel.classList.remove("hidden");
  updateComparisonProgress(0, total);
}

function hideComparisonProgress(){
  $("comparisonProgress")?.classList.add("hidden");
}

function toggleCompetitorSelection(button){
  const domain = competitorHost(button.dataset.domain || button.dataset.url);
  if(!domain) return;
  if(selectedCompetitorDomains.has(domain)) selectedCompetitorDomains.delete(domain);
  else {
    if(selectedCompetitorDomains.size >= MAX_COMPARATORS){ setCompetitorStatus(`You can compare up to ${MAX_COMPARATORS} competitors at once.`, "error"); return; }
    selectedCompetitorDomains.add(domain);
  }
  renderCompetitors(competitorResults);
  setCompetitorStatus(`${selectedCompetitorDomains.size} competitor${selectedCompetitorDomains.size === 1 ? "" : "s"} selected. Review your selection, then choose Compare selected.`, "info");
}

function renderComparison(){
  const wrap = $("comparisonWrap"), head = $("comparisonHead"), body = $("comparisonBody");
  if(!wrap || !head || !body || !currentReport || !competitorComparisons.length){ wrap?.classList.add("hidden"); return; }
  const rows = [["Speed","performance"],["SEO","seo"],["Accessibility","accessibility"],["Best practices","bestPractices"]];
  const columns = competitorComparisons.slice(0, MAX_COMPARATORS);
  head.innerHTML = `<th>Metric</th>` + columns.map(c => `<th>${esc(competitorHost(c.domain))}</th>`).join("");
  const own = currentReport.scores || {};
  body.innerHTML = rows.map(([label,key]) => `<tr><th>${label}<small>Your site</small></th>${columns.map(c => {
    const value=c.scores?.[key], base=own[key];
    if(value == null || base == null) return `<td class="neutral"><span class="comparison-score">${value == null ? "—" : value}</span><span class="comparison-delta neutral">No baseline</span></td>`;
    const diff=value-base;
    const cls=diff > 0 ? "higher" : diff < 0 ? "lower" : "same";
    const icon=diff > 0 ? "arrow-up-right" : diff < 0 ? "arrow-down-right" : "minus";
    const labelText=diff === 0 ? "Same score" : `${Math.abs(diff)} pts ${diff > 0 ? "higher" : "lower"}`;
    return `<td><span class="comparison-score">${value}<small>/100</small></span><span class="comparison-delta ${cls}"><i data-lucide="${icon}" aria-hidden="true"></i> ${esc(labelText)} vs your site</span></td>`;
  }).join("")}</tr>`).join("");
  const summary=$("comparisonSummary");
  if(summary){
    summary.innerHTML = columns.map(c => {
      const differences=rows.map(([label,key]) => ({label,diff:(c.scores?.[key] ?? null)-(own[key] ?? null)})).filter(x=>x.diff!==null && Number.isFinite(x.diff));
      const higher=differences.filter(x=>x.diff>0).map(x=>x.label);
      const lower=differences.filter(x=>x.diff<0).map(x=>x.label);
      const siteUrl = c.url || `https://${competitorHost(c.domain)}`;
      return `<div><a class="comparison-site-link" href="${esc(siteUrl)}" target="_blank" rel="noopener noreferrer"><span>${esc(competitorHost(c.domain))}</span><i data-lucide="external-link" aria-hidden="true"></i></a><span>${higher.length ? `<i data-lucide="arrow-up-right" aria-hidden="true"></i> Higher than your site on ${esc(higher.join(", "))}. ` : ""}${lower.length ? `<i data-lucide="arrow-down-right" aria-hidden="true"></i> Lower than your site on ${esc(lower.join(", "))}.` : higher.length ? "" : "Scores are currently the same or unavailable."}</span></div>`;
    }).join("");
  }
  wrap.classList.remove("hidden"); refreshIcons();
}

async function compareSelected(){
  if(!currentReport || !selectedCompetitorDomains.size || comparisonInFlight) return;
  const selected = competitorResults.filter(x => selectedCompetitorDomains.has(competitorHost(x.domain || x.url))).slice(0, MAX_COMPARATORS);
  if(!selected.length) return;
  comparisonInFlight=true;
  competitorComparisons=[];
  $("comparisonWrap")?.classList.add("hidden");
  let completed=0;
  showComparisonProgress(selected.length);
  updateCompareBar();
  setCompetitorStatus(`Comparison started — checking ${selected.length} competitor${selected.length===1?"":"s"} against your site.`, "info");
  const jobs=selected.map(async item => {
    const domain=competitorHost(item.domain || item.url);
    try{
      updateComparisonProgress(completed, selected.length, domain);
      setCompetitorStatus(`Comparing ${domain} — ${completed} of ${selected.length} finished.`, "info");
      const response=await csrfFetch("/api/competitor-analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:item.url,strategy:$("strategy").value})});
      const data=await response.json();
      if(response.status===401){ savePendingAnalysis(); window.location.href=`/login?next=${encodeURIComponent(location.pathname+"#competitors")}`; return; }
      if(response.status===402) throw new Error(data.error || "Unlock competitor analysis first.");
      if(!response.ok) throw new Error(data.error || `We couldn't check ${domain}.`);
      competitorComparisons.push({domain,url:item.url,scores:data.scores});
    }catch(error){ setCompetitorStatus(`${domain}: ${error.message}`, "error"); }
    finally{
      completed += 1;
      updateComparisonProgress(completed, selected.length, completed < selected.length ? domain : "");
      setCompetitorStatus(completed < selected.length ? `Comparison in progress — ${completed} of ${selected.length} finished.` : `Comparison checks finished — preparing your results.`, completed < selected.length ? "info" : "success");
    }
  });
  await Promise.all(jobs);
  comparisonInFlight=false;
  updateComparisonProgress(selected.length, selected.length);
  selectedCompetitorDomains=new Set();
  renderCompetitors(competitorResults);
  if(competitorComparisons.length){
    renderComparison();
    setCompetitorStatus(`Comparison ready — ${competitorComparisons.length} competitor${competitorComparisons.length===1?"":"s"} checked.`, "success");
    $("comparisonWrap")?.scrollIntoView({behavior:"smooth",block:"center"});
  }else if(completed){ setCompetitorStatus("No competitor comparison completed. You can select another competitor and try again.", "error"); }
  updateCompareBar();
  setTimeout(hideComparisonProgress, 650);
}

async function findCompetitors(){
  if(!currentReport) return;
  if(industryDetectionInFlight){ setCompetitorStatus("We're still identifying your website type. Please wait a moment.","info"); return; }
  const region=$("competitorRegion").value.trim(), industry=$("competitorIndustry").value.trim();
  if(region.length<2){ setCompetitorStatus("Enter a market or region first.","error"); $("competitorRegion").focus(); return; }
  if(industry.length<2){ setCompetitorStatus("We couldn't identify the business category yet. Choose Edit beside Website type and enter it once.","error"); $("changeIndustry")?.click(); return; }
  const button=$("findCompetitors"); button.disabled=true; button.innerHTML='<i data-lucide="loader-circle" aria-hidden="true"></i> Finding businesses…'; refreshIcons();
  setCompetitorStatus(`Searching for real ${industry} businesses in ${region}…`,"info");
  $("competitorResults").innerHTML=""; competitorComparisons=[]; selectedCompetitorDomains=new Set(); $("comparisonWrap").classList.add("hidden"); updateCompareBar();
  try{
    const response=await csrfFetch("/api/competitors",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({website:currentReport.finalUrl||currentReport.url,region,industry})});
    const data=await response.json();
    if(response.status===401){ savePendingAnalysis(); window.location.href=`/login?next=${encodeURIComponent(location.pathname+"#competitors")}`; return; }
    if(response.status===402){ setCompetitorStatus(data.error||"Unlock competitor analysis first.","error"); return; }
    if(!response.ok) throw new Error(data.error||"We couldn't find competitors right now.");
    competitorResults=dedupeCompetitors(data.results||[]); renderCompetitors(competitorResults);
    setCompetitorStatus(competitorResults.length ? `Found ${competitorResults.length} business websites. Select up to ${MAX_COMPARATORS} to compare. Nothing runs until you confirm.` : "No likely business competitors were found.", competitorResults.length?"success":"info");
  }catch(error){ setCompetitorStatus(error.message,"error"); }
  finally{ button.disabled=false; button.innerHTML='<i data-lucide="radar" aria-hidden="true"></i> Find my competitors'; refreshIcons(); }
}

function addManualCompetitor(){
  const input=$("manualCompetitor"); if(!input) return;
  const normalized=normalizeUrl(input.value); if(!normalized || !normalized.includes(".")){setCompetitorStatus("Enter a competitor website such as competitor.com.","error");return;}
  const domain=competitorHost(normalized), own=competitorHost(currentReport?.finalUrl||currentReport?.url||"");
  if(domain===own){setCompetitorStatus("That's the website you're already analyzing.","error");return;}
  if(competitorResults.some(x=>competitorHost(x.domain||x.url)===domain)){setCompetitorStatus(`${domain} is already in your competitor list.`,"info");return;}
  competitorResults=dedupeCompetitors([...competitorResults,{domain,url:normalized,title:domain,snippet:"Competitor added by you.",address:"Manually added"}]);
  input.value=""; renderCompetitors(competitorResults);
  setCompetitorStatus(`${domain} was added. Select it and choose Compare selected when you're ready — nothing is checked automatically.`,"success");
}

async function unlockCompetitors(){
  const error=$("premiumPaymentError"); error?.classList.add("hidden");
  if(!window.WEBPERF_STATE?.authenticated){ savePendingAnalysis(); window.location.href=`/register?next=${encodeURIComponent(location.pathname+"#competitors")}`; return; }
  if(window.WEBPERF_STATE?.premium){ restoreLocalReport(); document.getElementById("competitors")?.scrollIntoView({behavior:"smooth"}); return; }
  const button=$("unlockCompetitors"); if(!button) return;
  button.disabled=true; button.innerHTML='<i data-lucide="loader-circle" aria-hidden="true"></i> Preparing secure checkout…'; refreshIcons();
  try{
    const response=await csrfFetch("/api/payment/order",{method:"POST",headers:{"Content-Type":"application/json"}}), data=await response.json();
    if(!response.ok) throw new Error(data.error||"We couldn't start checkout.");
    if(data.alreadyUnlocked){ location.reload(); return; }
    if(!window.Razorpay) throw new Error("Payment checkout is not loaded. Please refresh and try again.");
    savePendingAnalysis();
    const rzp=new Razorpay({key:data.key,amount:data.amount,currency:data.currency,name:data.name,description:data.description,order_id:data.orderId,prefill:{email:data.email},theme:{color:"#5b8cff"},handler:async function(result){
      try{
        const verify=await csrfFetch("/api/payment/verify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(result)}), verifyData=await verify.json();
        if(!verify.ok) throw new Error(verifyData.error||"Payment could not be verified.");
        location.reload();
      }catch(e){ if(error){error.textContent=e.message;error.classList.remove("hidden");} button.disabled=false; button.innerHTML=`<i data-lucide="lock-open" aria-hidden="true"></i> Unlock for ${window.WEBPERF_STATE?.premiumPrice||"premium"}`; refreshIcons(); }
    },modal:{ondismiss:()=>{button.disabled=false;button.innerHTML=`<i data-lucide="lock-open" aria-hidden="true"></i> Unlock for ${window.WEBPERF_STATE?.premiumPrice||"premium"}`;refreshIcons();}}});
    rzp.open();
  }catch(error){ if($("premiumPaymentError")){ $("premiumPaymentError").textContent=error.message; $("premiumPaymentError").classList.remove("hidden"); } button.disabled=false; button.innerHTML=`<i data-lucide="lock-open" aria-hidden="true"></i> Unlock for ${window.WEBPERF_STATE?.premiumPrice||"premium"}`; refreshIcons(); }
}

if($("findCompetitors")) $("findCompetitors").addEventListener("click", findCompetitors);
if($("competitorIndustry")) {
  $("competitorIndustry").addEventListener("keydown", e => { if(e.key === "Enter") findCompetitors(); });
  $("competitorIndustry").addEventListener("input", () => {
    industryManualOverride = true;
    const value = $("competitorIndustry").value.trim();
    const findButton = $("findCompetitors");
    if(findButton) findButton.disabled = !value;
    if(value) {
      $("detectedIndustry").textContent = value;
      $("industryConfidence").textContent = "Manual";
      $("industryReason").textContent = "Using the category you entered for competitor discovery.";
    }
  });
}
if($("changeIndustry")) $("changeIndustry").addEventListener("click", () => {
  const field = $("competitorIndustry");
  if(!field) return;
  field.classList.remove("hidden");
  field.focus();
  field.select();
  industryManualOverride = true;
  const value = field.value.trim();
  const findButton = $("findCompetitors");
  if(findButton) findButton.disabled = !value;
  if(value) {
    $("detectedIndustry").textContent = value;
    $("industryConfidence").textContent = "Manual";
    $("industryReason").textContent = "Using the category you entered for competitor discovery.";
  }
});
if($("competitorResults")) $("competitorResults").addEventListener("click", e => {
  const more=e.target.closest("#showMoreCompetitors");
  if(more){ showAllCompetitors=true; renderCompetitors(competitorResults); return; }
  const button=e.target.closest(".compare-competitor");
  if(button) toggleCompetitorSelection(button);
});
if($("addManualCompetitor")) $("addManualCompetitor").addEventListener("click", addManualCompetitor);
if($("compareSelectedBtn")) $("compareSelectedBtn").addEventListener("click", compareSelected);
if($("clearSelectedBtn")) $("clearSelectedBtn").addEventListener("click", () => { selectedCompetitorDomains=new Set(); renderCompetitors(competitorResults); setCompetitorStatus("Selection cleared. Nothing is being compared.","info"); });
if($("manualCompetitor")) $("manualCompetitor").addEventListener("keydown", e => { if(e.key === "Enter"){ e.preventDefault(); addManualCompetitor(); } });
if($("unlockCompetitors")) $("unlockCompetitors").addEventListener("click", unlockCompetitors);
if($("premiumRegisterLink")) $("premiumRegisterLink").addEventListener("click", savePendingAnalysis);

document.addEventListener("DOMContentLoaded", () => {
  refreshIcons();
  initLiveCheckCounter();
  const restored = restoreLocalReport();
  if(restored && location.hash === "#competitors") document.getElementById("competitors")?.scrollIntoView({behavior:"smooth",block:"start"});
});

refreshIcons();
initScrollReveal();
initCookieBanner();
