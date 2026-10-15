import os
import sys
import yaml

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nexus.core.persistence.repository import NexusRepository
from nexus.core.domain.scenario import Scenario

db_url = os.environ.get("DATABASE_URL", "sqlite:///nexus.db")
# Handle postgres:// -> postgresql:// for SQLAlchemy if deployed on Heroku/Render
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()
repo = NexusRepository(db)

scenarios_dir = "scenarios/core_10"
if os.path.exists(scenarios_dir):
    for filename in sorted(os.listdir(scenarios_dir)):
        if filename.endswith(".yaml"):
            with open(os.path.join(scenarios_dir, filename), 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            scenario = Scenario.model_validate(data)
            repo.save_scenario(scenario)
            print(f"Ingested {scenario.scenario_id}")

db.close()
