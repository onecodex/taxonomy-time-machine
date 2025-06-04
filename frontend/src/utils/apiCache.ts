// Simple in-memory cache for API GET requests
const apiCache: Record<string, any> = {};

/**
 * Fetches a URL with caching. If the URL has been fetched before, returns the cached result.
 * If the fetch fails, throws the error.
 * Only caches successful responses.
 * @param url The URL to fetch (GET)
 * @returns The parsed JSON response
 */
export async function apiFetchWithCache(url: string): Promise<any> {
  if (apiCache[url]) {
    return apiCache[url];
  }
  const response = await fetch(url, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  const data = await response.json();
  apiCache[url] = data;
  return data;
}