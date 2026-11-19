/**
 * Public runtime config. Only NEXT_PUBLIC values belong here.
 */
const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

function readApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (value && value.length > 0) {
    return value;
  }
  return DEFAULT_API_BASE_URL;
}

export const config = {
  apiBaseUrl: readApiBaseUrl(),
};
