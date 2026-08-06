import os
import tempfile
from pathlib import Path


tmp_dir = tempfile.mkdtemp(prefix="asra_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp_dir, 'test.db').as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["USE_WEATHER_API"] = "false"
