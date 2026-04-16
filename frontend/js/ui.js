/**
 * UI helpers: sidebar, panels, messages, legend filters.
 */

function isMobile() { return window.innerWidth <= 600; }

function toggleSidebar() {
  const isOpen = document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('hamburgerBtn').classList.toggle('open');
  if (isOpen) showPanel('search');
}

function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('hamburgerBtn').classList.add('open');
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('hamburgerBtn').classList.remove('open');
}

function showPanel(name) {
  document.querySelectorAll('.sidebar-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
}

function openAdmin() {
  const managePanel = document.getElementById('panel-manage');
  if (managePanel.classList.contains('active')) {
    showPanel('search');
  } else {
    resetManageForm();
    showPanel('manage');
    if (isMobile()) openSidebar();
  }
}

function showMsg(id, text, type) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = 'msg ' + type;
}

/* ── Legend / filter bar ── */
const filters = { available: true, few: true, empty: true, inactive: true };

function stationCategory(s) {
  if (!s.is_active) return 'inactive';
  const ratio = s.available_bikes / s.total_slots;
  if (ratio === 0) return 'empty';
  if (ratio < 0.3) return 'few';
  return 'available';
}

function toggleFilter(key) {
  filters[key] = !filters[key];
  const el = document.querySelector(`.legend-item[data-filter="${key}"]`);
  el.classList.toggle('off', !filters[key]);
  el.classList.toggle('active', filters[key]);
  loadStations();
}

function passesFilter(s) {
  return filters[stationCategory(s)];
}

/* ── Action filter: both, reserve, return ── */
let actionFilter = 'both';

function setActionFilter(filter) {
  actionFilter = filter;
  document.querySelectorAll('.action-tabs .search-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.action-tabs .search-tab[onclick="setActionFilter('${filter}')"]`).classList.add('active');
  if (currentSearchMode) searchNearby();
}

function passesActionFilter(s) {
  if (actionFilter === 'reserve') return s.available_bikes > 0;
  if (actionFilter === 'return') return s.available_bikes < s.total_slots;
  return true;
}
