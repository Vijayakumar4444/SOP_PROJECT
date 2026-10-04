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
    const message =
      error.response?.data?.message ??
      (typeof detail === "string" ? detail : undefined) ??
      error.message ??
      "The policy simulation service is currently unavailable.";
    return Promise.reject(new Error(message));
  }
);

export const useMockApi = import.meta.env.VITE_USE_MOCK_API === "true";
