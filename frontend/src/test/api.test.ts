import { describe, expect, it } from "vitest";

import { API_BASE_URL, buildApiUrl, getAdminWebSocketUrl } from "@/lib/api";

describe("API URL helpers", () => {
  it("normalizes API paths", () => {
    expect(buildApiUrl("/api/v1/chat")).toBe(`${API_BASE_URL}/api/v1/chat`);
    expect(buildApiUrl("api/v1/chat")).toBe(`${API_BASE_URL}/api/v1/chat`);
  });

  it("builds the admin WebSocket URL", () => {
    const url = new URL(getAdminWebSocketUrl());

    expect(["ws:", "wss:"]).toContain(url.protocol);
    expect(url.pathname).toBe("/ws/admin");
  });
});
