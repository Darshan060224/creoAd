Local royalty-free music assets for Stage B4.

Folder convention:
- Keep tracks as .mp3 or .wav files.
- Include mood in filename when possible (e.g., upbeat_loop.mp3, calm_piano.wav).

Defaults:
- backend/modules/music_generator.py reads from LOCAL_MUSIC_DIR.
- If LOCAL_MUSIC_DIR is not set, it defaults to ./assets/music relative to backend runtime cwd.

Bootstrap starter files:
- Run: python backend/scripts/bootstrap_music_assets.py
