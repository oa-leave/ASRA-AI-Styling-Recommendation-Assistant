import os
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

tmp_dir = tempfile.mkdtemp(prefix="asra_tests_")
database_url = f"sqlite:///{Path(tmp_dir, 'test.db').as_posix()}"
os.environ["DATABASE_URL"] = database_url
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["USE_WEATHER_API"] = "false"
os.environ["VISION_ENABLED"] = "false"
os.environ["LLM_API_KEY"] = ""

alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
alembic_cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
alembic_cfg.set_main_option("sqlalchemy.url", database_url)
command.upgrade(alembic_cfg, "head")
