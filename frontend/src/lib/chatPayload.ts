export type ChatInputType = "text" | "image" | "voice";

export function buildChatRequestPayload(
  content: string,
  type: ChatInputType,
  imageUrl: string | undefined,
  sessionId: string | null,
) {
  return {
    message: content,
    image: imageUrl || null,
    session_id: sessionId,
    input_type: type,
  };
}
