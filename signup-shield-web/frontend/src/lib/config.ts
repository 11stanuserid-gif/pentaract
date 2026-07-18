// API base URL — uses Vite proxy in dev, or direct URL in production
const DEV_API = ''; // proxied by Vite
const PROD_API = 'http://127.0.0.1:8000';

export const API_URL = import.meta.env.DEV ? DEV_API : PROD_API;

export const API_BASE = API_URL;
