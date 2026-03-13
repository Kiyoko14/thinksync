import { apiClient, clearToken, User } from "./api";

/**
 * Returns the currently authenticated user by calling the backend session
 * endpoint with the stored Bearer token.  Returns null when no valid session
 * exists (unauthenticated or token expired).
 */
export async function getSession(): Promise<User | null> {
  return apiClient.getSession();
}

/**
 * Logs out the current user: calls the backend logout endpoint and removes the
 * stored token from localStorage.
 */
export async function logout(): Promise<void> {
  return apiClient.logout();
}

export { clearToken };
