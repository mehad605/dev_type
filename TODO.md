# Performance Improvements

- [x] Lazy-load language scanning on a background thread so the UI is responsive immediately after launch.
- [x] Apply SQLite pragmas and guard database initialisation to reduce connection overhead and duplicate setup work.
- [x] Defer heavy optional imports (PyQtGraph, rich assets, icon loaders) until the relevant feature is used.
- [x] Cache folder/file metadata snapshots and only rescan when folder configuration changes.
- [ ] Buffer per-keystroke stats in memory and flush to SQLite only on pause or completion.
- [ ] Consolidate per-widget styles into a cached QSS stylesheet applied once per theme.
- [ ] Share QFont/QPen/QBrush objects and reuse QPixmap/QIcon instances via a keyed cache.
- [ ] Paginate session history loading instead of fetching all rows at once.
- [ ] Profile `MainWindow.__init__` with `cProfile` and offload slow sections to background threads as needed.
- [ ] Strip redundant debug logging and extra signal emissions during typing sessions.
