import argparse
from app.ui_main import run_app


def parse_args():
    parser = argparse.ArgumentParser(description="Dev Type - Typing Practice App")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use demo database with fake data for testing the stats page"
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    
    # Set demo mode if flag is passed
    if args.demo:
        from app import demo_data
        demo_data.set_demo_mode(True)
        print("Running in DEMO MODE - using fake statistics data")
    
    run_app()
