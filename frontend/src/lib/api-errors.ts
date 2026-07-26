import axios from "axios";

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function getApiErrorPayload(error: unknown): Record<string, unknown> | undefined {
  if (!axios.isAxiosError(error) || !isRecord(error.response?.data)) {
    return undefined;
  }

  return error.response.data;
}

export function getApiErrorDetail(error: unknown): unknown {
  return getApiErrorPayload(error)?.detail;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const payload = getApiErrorPayload(error);
  const detail = payload?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .filter(isRecord)
      .map((item) => item.msg)
      .filter((message): message is string => typeof message === "string");

    if (messages.length > 0) {
      return messages.join(" | ");
    }
  }

  return typeof payload?.message === "string" ? payload.message : fallback;
}
