# DearBaby backend

## Run it

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed.py                     # once — loads content + demo accounts
python app.py                      # starts the server on port 5000
```

Leave `python app.py` running. Open a second terminal for the frontend.

## Layout

```
backend/
├── app.py             <- run this
├── seed.py            <- run once, first
├── requirements.txt
├── dearbaby/          <- the application package
│   ├── __init__.py      create_app() — blueprints registered here
│   ├── models.py        every database table
│   ├── roles.py         permissions + hierarchy (single source of truth)
│   ├── decorators.py    login_required, permission_required
│   ├── helpers.py       ownership checks, pagination, premium gate
│   ├── content.py       pregnancy weeks, milestone types, recipes
│   └── <feature>/routes.py   one folder per feature area
└── tests/
```

`app.py` is the file you run. `dearbaby/` is the code it runs. They're
separate so the package can be imported by tests and by a production server
without starting a web server as a side effect.

## Tests

```bash
python -m pytest tests/ -v         # 31 tests
```
