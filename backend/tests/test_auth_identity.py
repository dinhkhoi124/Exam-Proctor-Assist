import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

# Load the complete SQLAlchemy model registry without importing the RAG application.
from app.models import chat_log, chat_session, chat_topic, feedback_log, rag_document, user_activity  # noqa: F401

from app.services.auth_service import normalize_email, normalize_username, register_user


class AuthIdentityTests(unittest.TestCase):
    def test_normalizes_email_and_trims_username(self):
        self.assertEqual(normalize_email("  User.Name@FPT.EDU.VN "), "user.name@fpt.edu.vn")
        self.assertEqual(normalize_username("  UserName  "), "UserName")

    @patch("app.services.auth_service.hash_password", return_value="hashed")
    def test_registration_stores_normalized_identity(self, _hash_password):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        user = register_user(db, "  UserName  ", "  User.Name@FPT.EDU.VN ", "secret1")

        self.assertEqual(user.username, "UserName")
        self.assertEqual(user.email, "user.name@fpt.edu.vn")
        db.commit.assert_called_once()

    @patch("app.services.auth_service.hash_password", return_value="hashed")
    def test_concurrent_unique_conflict_returns_409(self, _hash_password):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))

        with self.assertRaises(HTTPException) as raised:
            register_user(db, "UserName", "user.name@fpt.edu.vn", "secret1")

        self.assertEqual(raised.exception.status_code, 409)
        db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
