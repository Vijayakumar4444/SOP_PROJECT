import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  timeout: 20_000,
  headers: {
    "Content-Type": "application/json"
  }
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    const detailMessage =
      typeof detail === "object" && detail !== null && "message" in detail
        ? String((detail as { message?: unknown }).message)
        : undefined;
    const message =
      error.response?.data?.message ??
      detailMessage ??
      (typeof detail === "string" ? detail : undefined) ??
      error.message ??
      "The policy simulation service is currently unavailable.";
    const apiError = new Error(message) as Error & { status?: number; detail?: unknown };
    apiError.status = error.response?.status;
    apiError.detail = detail;
    return Promise.reject(apiError);
  }
);

export const useMockApi = import.meta.env.VITE_USE_MOCK_API === "true";
