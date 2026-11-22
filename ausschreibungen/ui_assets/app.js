"use strict";

const el = id => document.getElementById(id);
const countryNames = {
  DEU: "Deutschland", AUT: "Österreich", CHE: "Schweiz", BEL: "Belgien", BGR: "Bulgarien",
  DNK: "Dänemark", EST: "Estland", FIN: "Finnland", FRA: "Frankreich", GRC: "Griechenland",
  IRL: "Irland", ITA: "Italien", HRV: "Kroatien", LVA: "Lettland", LTU: "Litauen",
  LUX: "Luxemburg", MLT: "Malta", NLD: "Niederlande", POL: "Polen", PRT: "Portugal",
  ROU: "Rumänien", SWE: "Schweden", SVK: "Slowakei", SVN: "Slowenien", ESP: "Spanien",
  CZE: "Tschechien", HUN: "Ungarn", CYP: "Zypern"
};
const numeric = ["days_back", "max_results", "report_limit", "timeout_seconds"];
const textual = ["name", "country_field", "scope", "language"];
let saved;
let selected = [];
let busy = false;

function node(tag, text, className) {
  const item = document.createElement(tag);
  if (text !== undefined) item.textContent = text;
  if (className) item.className = className;
  return item;
}

function button(text, action) {
  const item = node("button", text);
  item.type = "button";
  item.onclick = action;
  return item;
}

function field(title, input) {
  const label = node("label", title);
  label.append(input);
  return label;
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)
  };
  const response = await fetch("/api/" + path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Die Anfrage ist fehlgeschlagen.");
  return data;
}

function error(message) {
  el("error").textContent = message;
  el("error").hidden = !message;
  if (message) el("error").scrollIntoView({block: "center"});
}

function summary() {
  const profile = saved.search;
  el("profile-name").textContent = profile.name;
  const countries = profile.countries.map(code => countryNames[code] || code).join(", ");
  const where = profile.country_field === "buyer-country" ? "Sitz des Auftraggebers" : "Leistungsort";
  const region = countries ? where + ": " + countries : "Alle Länder";
  const period = profile.days_back === 1 ? "Heute" : "Letzte " + profile.days_back + " Tage";
  el("scope").value = profile.scope;
  el("coverage").textContent = ["TED", el("scope").selectedOptions[0].text, region, period].join(" · ");
  el("cpv-filter").hidden = !profile.cpv_codes.length;
  el("cpv-filter").textContent = profile.cpv_codes.length ? "CPV-Filter: " + profile.cpv_codes.join(", ") : "";
  el("company-text").textContent = saved.analysis.company_profile;
  el("summary").replaceChildren();
  for (const query of profile.queries) {
    const block = node("details");
    const groups = node("ul", undefined, "term-groups");
    for (const terms of query.term_groups) {
      groups.append(node("li", terms.join(", ")));
    }
    block.append(node("summary", query.name), groups);
    el("summary").append(block);
  }
}

function drawCountries() {
  el("selected-countries").replaceChildren();
  if (!selected.length) el("selected-countries").append(node("span", "Alle Länder"));
  for (const code of selected) {
    const chip = button((countryNames[code] || code) + " ×", () => {
      selected = selected.filter(item => item !== code);
      drawCountries();
    });
    chip.setAttribute("aria-label", (countryNames[code] || code) + " entfernen");
    el("selected-countries").append(chip);
  }
}

function addCountry() {
  const input = el("country");
  const value = input.value.trim();
  if (!value) return true;
  const code = Object.keys(countryNames).find(k => countryNames[k].toLowerCase() === value.toLowerCase()) || value.toUpperCase();
  if (!/^[A-Z]{3}$/.test(code)) {
    input.setCustomValidity("Bitte wähle ein Land oder gib einen dreistelligen TED-Ländercode ein.");
    input.reportValidity();
    return false;
  }
  if (!selected.includes(code)) selected.push(code);
  input.value = "";
  drawCountries();
  return true;
}

function addGroup(container, terms) {
  const row = node("div", undefined, "group");
  const input = node("textarea");
  input.rows = Math.min(5, Math.max(2, terms.length));
  input.value = terms.join("\n");
  input.required = true;
  const remove = button("Gruppe entfernen", () => row.remove());
  row.append(field("Begriffe · eine Alternative pro Zeile", input), remove);
  container.append(row);
}

function addQuery(query) {
  const card = node("div", undefined, "query");
  const name = node("input");
  name.required = true;
  name.value = query.name;
  const header = node("div", undefined, "query-heading");
  header.append(field("Name des Suchblocks", name), button("Block entfernen", () => card.remove()));
  const groups = node("div", undefined, "groups");
  query.term_groups.forEach(terms => addGroup(groups, terms));
  card.append(header, groups, button("+ Begriffsgruppe", () => addGroup(groups, [])));
  el("queries").append(card);
}

function openSettings() {
  for (const key of [...numeric, ...textual]) el(key).value = saved.search[key];
  for (const key of ["company_profile", "model"]) el(key).value = saved.analysis[key];
  el("cpv_codes").value = saved.search.cpv_codes.join(", ");
  el("country").value = "";
  el("country").setCustomValidity("");
  selected = [...saved.search.countries];
  drawCountries();
  el("queries").replaceChildren();
  saved.search.queries.forEach(addQuery);
  error("");
  el("settings").hidden = false;
  el("home").hidden = true;
  el("name").focus();
}

function home() {
  el("settings").hidden = true;
  el("home").hidden = false;
  window.scrollTo(0, 0);
  el("edit").focus();
}

function settings() {
  const search = {};
  for (const key of textual) search[key] = el(key).value.trim();
  for (const key of numeric) search[key] = el(key).valueAsNumber;
  search.countries = selected;
  search.cpv_codes = el("cpv_codes").value.split(",").map(s => s.trim()).filter(Boolean);
  search.queries = [...el("queries").children].map(card => ({
    name: card.querySelector("input").value.trim(),
    term_groups: [...card.querySelectorAll("textarea")].map(input =>
      input.value.split("\n").map(s => s.trim()).filter(Boolean))
  }));
  return {search, analysis: {company_profile: el("company_profile").value.trim(), model: el("model").value.trim()}};
}

async function status() {
  const state = await api("status");
  busy = state.status === "running";
  el("edit").disabled = el("start").disabled = !saved || busy;
  el("result").hidden = state.status === "idle";
  const titles = {running: "Recherche läuft …", complete: "Bericht fertig", incomplete: "Bericht mit offenen Punkten", failed: "Bericht fehlgeschlagen"};
  el("result-title").textContent = titles[state.status] || "";
  el("latest").textContent = state.status === "incomplete" ? "Einzelne Schritte sind unvollständig. Hinweise stehen im PDF und in den Laufdetails." : busy || state.status === "failed" ? state.messages.at(-1) || "" : "";
  el("log").replaceChildren(...state.messages.map(line => node("li", line)));
  el("pdf").hidden = !state.pdf;
  if (state.pdf) el("pdf").href = state.pdf;
  if (busy) setTimeout(poll, 1000);
}

async function poll() {
  try { await status(); }
  catch {
    el("latest").textContent = "Verbindung unterbrochen. Bitte das Startfenster prüfen.";
    setTimeout(poll, 3000);
  }
}

el("edit").onclick = openSettings;
el("cancel").onclick = () => { error(""); home(); };
el("add-query").onclick = () => addQuery({name: "", term_groups: [[]]});
el("add-country").onclick = addCountry;
el("country").oninput = () => el("country").setCustomValidity("");
el("country").onkeydown = event => {
  if (event.key === "Enter") { event.preventDefault(); addCountry(); }
};
for (const [code, name] of Object.entries(countryNames)) {
  const option = node("option", code);
  option.value = name;
  el("countries").append(option);
}
el("form").onsubmit = async event => {
  event.preventDefault();
  if (!addCountry()) return;
  el("save").disabled = true;
  try {
    await api("settings", {base: saved, settings: settings()});
    saved = await api("settings");
    summary();
    error("");
    home();
  } catch (e) { error(e.message); }
  finally { el("save").disabled = false; }
};
el("start").onclick = async () => {
  if (busy) return;
  busy = true;
  el("edit").disabled = el("start").disabled = true;
  error("");
  try { await api("report", {base: saved}); }
  catch (e) { error(e.message); }
  await poll();
};

async function init() {
  try {
    saved = await api("settings");
    summary();
    await status();
  } catch (e) { error("Oberfläche konnte nicht geladen werden. " + e.message); }
}
init();
