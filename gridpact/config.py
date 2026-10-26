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

# MCP server address. Agents and the smoke client connect here.
PORT = 8765
SERVER_URL = f"http://127.0.0.1:{PORT}/mcp"

N_STEPS = 96          # 15-minute steps in a day
STEP_H = 0.25
OFFER_TTL_ROUNDS = 2  # an offer not answered within this many negotiation rounds expires
