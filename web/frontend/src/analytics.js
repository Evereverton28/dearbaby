/* Self-hosted analytics client. Fires a pageview per route change plus the
   funnel events. Visitor id persists across sessions to separate new from
   returning; session id resets when the tab does. */
import api from './api';

function id(key, store) {
  let v = store.getItem(key);
  if (!v) { v = crypto.randomUUID(); store.setItem(key, v); }
  return v;
}
const visitorId = () => id('db_visitor', localStorage);
const sessionId = () => id('db_session', sessionStorage);

export function track(name, path) {
  api.post('/track', {
    name,
    path: path || window.location.pathname,
    referrer: document.referrer || null,
    visitor_id: visitorId(),
    session_id: sessionId(),
  }).catch(() => {});   // analytics must never break the app
}
export const trackPageview = (path) => track('pageview', path);
