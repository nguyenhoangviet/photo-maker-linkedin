/**
 * Central API config.
 * - Dev (Vite proxy): VITE_API_BASE_URL is empty, /api/* is proxied to localhost:8000
 * - Production (Vercel): set VITE_API_BASE_URL="" and use vercel.json rewrites instead
 * - Docker compose: VITE_API_BASE_URL=http://localhost:8000
 */
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
