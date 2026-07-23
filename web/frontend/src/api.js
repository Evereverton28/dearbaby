import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

let accessToken = localStorage.getItem('db_access') || null;
let refreshToken = localStorage.getItem('db_refresh') || null;

export function setTokens(access, refresh) {
  accessToken = access; refreshToken = refresh;
  if (access) localStorage.setItem('db_access', access); else localStorage.removeItem('db_access');
  if (refresh) localStorage.setItem('db_refresh', refresh); else localStorage.removeItem('db_refresh');
}
export const getAccessToken = () => accessToken;

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

/* On 401, try the refresh token once, then replay the original request.
   If refresh also fails the session is genuinely gone (expired, or the
   account was deactivated server-side) so we clear and let the router
   bounce to login. */
let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    if (status === 401 && refreshToken && !original._retried) {
      original._retried = true;
      try {
        refreshing = refreshing || axios.post('/api/auth/refresh', {}, {
          headers: { Authorization: `Bearer ${refreshToken}` },
        });
        const { data } = await refreshing;
        refreshing = null;
        setTokens(data.access_token, data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch (e) {
        refreshing = null;
        setTokens(null, null);
        window.dispatchEvent(new Event('db:signed-out'));
      }
    }
    return Promise.reject(error);
  },
);

/* Every caller gets a readable message instead of "Request failed with 401". */
export function errorMessage(err, fallback = 'Something went wrong. Try again.') {
  return err?.response?.data?.error || fallback;
}

export default api;
