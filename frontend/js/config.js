/**
 * Global configuration and API setup.
 */
const API_KEY = 'mibici-dev-key';
const API_HEADERS = { 'X-API-Key': API_KEY };
const GDL = [20.674, -103.344];

/* ── Rate-limit interceptor ── */
let rateToastTimer = null;
let rateCountdown = null;

function showRateLimit() {
  const el = document.getElementById('rate-toast');
  el.classList.add('show');
  clearTimeout(rateToastTimer);
  clearInterval(rateCountdown);
  let secs = 60;
  el.textContent = `Haz excedido el numero de peticiones, por favor espera ${secs}s`;
  rateCountdown = setInterval(() => {
    secs--;
    if (secs <= 0) {
      clearInterval(rateCountdown);
      el.classList.remove('show');
    } else {
      el.textContent = `Haz excedido el numero de peticiones, por favor espera ${secs}s`;
    }
  }, 1000);
}

const _fetch = window.fetch;
window.fetch = async function (...args) {
  const resp = await _fetch(...args);
  if (resp.status === 429) { showRateLimit(); throw new Error('rate_limit'); }
  return resp;
};
