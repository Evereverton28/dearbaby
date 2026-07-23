"""
DearBaby backend — start here.

    python app.py

That's it. It creates the database if needed and serves on
http://localhost:5000. Leave this terminal running while you use the app.

(If you've never run it before, do `python seed.py` first to load the
recipes, pregnancy content and demo accounts.)
"""
from dearbaby import create_app

app = create_app()

if __name__ == "__main__":
    print()
    print("  DearBaby API running at http://localhost:5000")
    print("  Now start the frontend in another terminal:")
    print("      cd ../frontend && npm run dev")
    print()
    print("  Press CTRL+C to stop.")
    print()
    app.run(debug=True, port=5000)
