import os
import tempfile


_test_database = tempfile.TemporaryDirectory(prefix="asistente-sueno-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_database.name}/test.db"
os.environ["GEMINI_API_KEY"] = ""
os.environ["JWT_SECRET_KEY"] = "tests-only-signing-secret"


def pytest_sessionfinish(session, exitstatus):
    _test_database.cleanup()
