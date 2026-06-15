-- Speeds up date-range report filters and common report groupings.
CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at
    ON public.chat_logs USING btree (created_at);

CREATE INDEX IF NOT EXISTS idx_chat_logs_user_id
    ON public.chat_logs USING btree (user_id);

CREATE INDEX IF NOT EXISTS idx_chat_logs_topic_id
    ON public.chat_logs USING btree (topic_id);

CREATE INDEX IF NOT EXISTS idx_feedback_logs_chat_id
    ON public.feedback_logs USING btree (chat_id);

CREATE INDEX IF NOT EXISTS idx_feedback_logs_created_at
    ON public.feedback_logs USING btree (created_at);
