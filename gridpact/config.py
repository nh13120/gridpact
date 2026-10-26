"""All settings in one place. Values come from .env (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # puts ANTHROPIC_API_KEY and GRIDPACT_DATA_DIR into os.environ

DATA_DIR = Path(os.environ.get("GRIDPACT_DATA_DIR", ROOT / "data"))
DB_PATH = ROOT / "gridpact.db"
TZ = "America/Chicago"  # the dataset's local time; timestamps in the files are UTC

# Price model: sellers earn the wholesale price, buyers pay wholesale + a grid fee.
# This fee is the "import/export spread" that makes a local trade worth doing.
GRID_FEE_USD_MWH = 30.0
