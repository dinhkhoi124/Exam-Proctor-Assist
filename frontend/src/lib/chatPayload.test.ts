import { describe, expect, it } from "vitest";
import { buildChatRequestPayload } from "./chatPayload";

describe("buildChatRequestPayload", () => {
  it("marks voice messages explicitly", () => {
    expect(buildChatRequestPayload("nội quy", "voice", undefined, "session-1")).toEqual({
      message: "nội quy",
      image: null,
      session_id: "session-1",
      input_type: "voice",
    });
  });

  it("preserves image payload type", () => {
    expect(buildChatRequestPayload("xem ảnh", "image", "base64", null).input_type).toBe(
      "image",
    );
  });
});
