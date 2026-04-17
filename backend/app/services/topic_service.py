def classify_topic(question: str) -> str:
    if not question:
        return "General Guidance"

    q = question.lower()

    if any(k in q for k in ["đăng nhập", "login", "mật khẩu"]):
        return "Login & Account Issues"

    if any(k in q for k in ["lỗi hệ thống", "crash", "không load", "treo web"]):
        return "Exam System Errors"

    if any(k in q for k in ["nộp bài", "submit", "không nộp được"]):
        return "Submission Problems"

    if any(k in q for k in ["mạng", "wifi", "disconnect", "lag"]):
        return "Network & Connection Issues"

    if any(k in q for k in ["máy", "bàn phím", "chuột", "camera"]):
        return "Device & Hardware Issues"

    if any(k in q for k in ["gian lận", "vi phạm", "quy chế"]):
        return "Exam Regulations & Violations"

    if any(k in q for k in ["giám sát", "camera", "theo dõi"]):
        return "Proctoring & Monitoring"

    if any(k in q for k in ["mất điện", "khẩn cấp", "sự cố"]):
        return "Emergency Situations"

    return "General Guidance"