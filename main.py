"""
Dev Type - Typing Practice Application

Entry point with instant Tkinter splash for immediate visual feedback.
"""
import argparse


def main():
    # --- Setup Logging ---
    try:
        from app.logging_config import setup_logging
        setup_logging()
    except Exception as e:
        print(f"Failed to setup logging: {e}")

    # --- Argument Parsers ---
    parser = argparse.ArgumentParser(description="Dev Type - Typing Practice App")
    
    # Profile & Mode
    parser.add_argument("--profile", type=str, help="Load a specific profile on startup (creates it if missing)")
    parser.add_argument("--sandbox", action="store_true", help="Run in a temporary sandbox mode (isolated database)")
    parser.add_argument("--demo", action="store_true", help="Alias for --sandbox (Legacy)")

    # Data Generation
    parser.add_argument("--gen-data", action="store_true", help="Generate fake history data for the active profile/sandbox")
    parser.add_argument("--gen-days", type=int, default=365, help="Number of days of history to generate (default: 365)")
    parser.add_argument("--gen-langs", type=str, help="Comma-separated list of languages (e.g. 'Python,Rust')")
    parser.add_argument("--gen-count", type=str, default="3-10", help="Range of sessions per day (e.g. '3-10')")
    parser.add_argument("--year", type=int, help="Specific year for generation (Legacy config)")
    parser.add_argument("--persist", action="store_true", help="Don't overwrite existing sandbox data (Legacy)")

    # Debug / Testing
    parser.add_argument("--debug-indent", action="store_true", help="Enable indent testing mode (formerly --indent_test)")
    parser.add_argument("--indent_test", action="store_true", help="Alias for --debug-indent")

    args = parser.parse_args()
    
    # --- Flag Normalization ---
    indent_mode = args.debug_indent or args.indent_test
    sandbox_mode = args.sandbox or args.demo
    
    # Set indent test mode setting
    from app import settings
    settings.set_indent_test_mode(indent_mode)
    
    # --- Profile Handling ---
    # We handle this BEFORE the splash or heavy imports to ensure the app loads the right config
    active_db_path = None
    
    if args.profile and not sandbox_mode:
        # Manually update global_config.json to switch profile
        # We avoid importing ProfileManager here to keep startup light/safe
        try:
            from app.portable_data import get_data_manager
            import json
            
            dm = get_data_manager()
            shared_dir = dm.get_shared_dir()
            profiles_dir = dm.get_profiles_dir()
            config_path = shared_dir / "global_config.json"
            
            # Ensure profile directory exists
            target_profile_dir = profiles_dir / args.profile
            if not target_profile_dir.exists():
                print(f"[CLI] Creating new profile: {args.profile}")
                target_profile_dir.mkdir(parents=True, exist_ok=True)
                # Create basic metadata
                import time
                with open(target_profile_dir / "profile.json", "w") as f:
                    json.dump({"creation_order": time.time(), "image": None}, f)
            
            # Update config
            data = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    data = json.load(f)
            
            if data.get("active_profile") != args.profile:
                print(f"[CLI] Switching active profile to: {args.profile}")
                data["active_profile"] = args.profile
                shared_dir.mkdir(parents=True, exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(data, f)
            
            # Target DB for generation is this profile's DB
            active_db_path = target_profile_dir / "typing_stats.db"
            
        except Exception as e:
            print(f"[CLI] Error setting profile: {e}")

    # --- Splash Screen ---
    splash = None
    try:
        from app.instant_splash import create_instant_splash
        splash = create_instant_splash()
        if splash:
            splash.update("Starting...", 5)
    except Exception as e:
        print(f"[Splash] Could not create splash: {e}")

    # --- Data Generation / Sandbox Setup ---
    from app import demo_data
    
    if sandbox_mode:
        # Sandbox Mode: Use the isolated demo_stats.db
        if splash: splash.update("Initializing sandbox...", 10)
        demo_data.set_demo_mode(True)
        # Sandbox targets the demo DB
        active_db_path = demo_data.get_demo_db_path()
        print("Running in SANDBOX MODE (Global Demo DB)")

    # Handle Data Generation if requested (or if classic --demo implies it)
    # logic: if --gen-data is explicitly asking, OR if old --demo flag is used (which implies gen)
    should_generate = args.gen_data or (args.demo and not args.gen_data)
    
    if should_generate:
        if splash: splash.update("Generating data...", 20)
        
        # Parse generation options
        langs = args.gen_langs.split(",") if args.gen_langs else None
        
        try:
            min_s, max_s = map(int, args.gen_count.split("-"))
            sessions_range = (min_s, max_s)
        except:
            sessions_range = (3, 10)

        # Call generation
        # If active_db_path is None (e.g. standard run without --profile), 
        # we default to generating for the *currently active* profile found by ProfileManager/Settings later?
        # But we need the path NOW to generate.
        
        if not active_db_path and not sandbox_mode:
            # Resolve current active profile path if not explicitly passed
            from app.portable_data import get_data_manager
            import json
            dm = get_data_manager()
            profiles_dir = dm.get_profiles_dir()
            shared_dir = dm.get_shared_dir()
            config_path = shared_dir / "global_config.json"
            current_profile = "Default"
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        current_profile = json.load(f).get("active_profile", "Default")
                except: pass
            active_db_path = profiles_dir / current_profile / "typing_stats.db"

        print(f"[CLI] Generating data for target DB: {active_db_path}")
        
        # Sandbox Cleanup: If using sandbox and not persisting, delete the file for a fresh start
        if sandbox_mode and not args.persist and active_db_path.exists():
             try:
                active_db_path.unlink()
                print("[CLI] Sandbox DB cleared.")
             except:
                print("[CLI] Warning: Could not clear sandbox DB file.")

        demo_data.generate_data_for_db(
            db_path=active_db_path,
            year=args.year,
            days=args.gen_days,
            sessions_range=sessions_range,
            languages=langs
        )


    # Heavy import - splash visible during this
    if splash:
        splash.update("Loading Qt framework...", 15)
    
    from app.ui_main import run_app_with_splash
    
    # Run the app, passing the splash to close later
    run_app_with_splash(splash)


if __name__ == '__main__':
    main()
