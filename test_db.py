from app import stats_db
try:
    stats_db.init_stats_tables()
    print("Database initialization successful.")
except Exception as e:
    print(f"Database initialization failed: {e}")
    import traceback
    traceback.print_exc()
