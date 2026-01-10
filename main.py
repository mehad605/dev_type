"""
Dev Type - Typing Practice Application

Entry point with instant Tkinter splash for immediate visual feedback.
"""
import argparse


def main():
    parser = argparse.ArgumentParser(description="Dev Type - Typing Practice App")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use demo database with fake data for testing the stats page"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Generate fake data for a specific year (e.g., 2025). Only relevant with --demo."
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist demo data between runs. If not set, data is regenerated each time. Only relevant with --demo."
    )
    args = parser.parse_args()
    
    # Show instant splash BEFORE heavy imports
    splash = None
    try:
        from app.instant_splash import create_instant_splash
        splash = create_instant_splash()
            
        if splash:
            splash.update("Starting...", 5)
    except Exception as e:
        print(f"[Splash] Could not create splash: {e}")
    
    # Set demo mode if requested
    if args.demo:
        if splash:
            splash.update("Enabling demo mode...", 10)
        from app import demo_data
        demo_data.set_demo_mode(True)
        demo_data.setup_demo_data(year=args.year, persist=args.persist)
        print("Running in DEMO MODE - using fake statistics data")
    
    # Heavy import - splash visible during this
    if splash:
        splash.update("Loading Qt framework...", 15)
    
    from app.ui_main import run_app_with_splash
    
    # Run the app, passing the splash to close later
    run_app_with_splash(splash)


if __name__ == '__main__':
    main()
