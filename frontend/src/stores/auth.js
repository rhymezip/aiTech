import { writable } from 'svelte/store';

export const user  = writable(null);
export const token = writable(null);

// Always use relative /api — nginx proxies to backend
export const apiUrl = '/api';

export function setAuth(userData, tokenData) {
  user.set(userData);
  token.set(tokenData);
  if (tokenData) {
    localStorage.setItem('token', tokenData);
    localStorage.setItem('user', JSON.stringify(userData));
  }
}

export function clearAuth() {
  user.set(null);
  token.set(null);
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

export function initAuth() {
  const savedToken = localStorage.getItem('token');
  const savedUser  = localStorage.getItem('user');
  if (savedToken && savedUser) {
    try {
      token.set(savedToken);
      user.set(JSON.parse(savedUser));
    } catch {
      clearAuth();
    }
  }
}

export function authFetch(url, options = {}) {
  return authFetchWithCallback(url, options).then((response) => {
    if (response.status === 401) {
      clearAuth();
      window.location.reload();
      return Promise.reject(new Error('Unauthorized'));
    }
    return response;
  });
}

export async function authFetchWithCallback(url, options = {}) {
  const t = localStorage.getItem('token');
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
      ...options.headers,
    },
  });
}
