from database.db_manager import DBManager
from dotenv import load_dotenv
load_dotenv()
db = DBManager()
df = db.fetch("SELECT * FROM cv_job_matches LIMIT 5")
print(df)