# ACEest Fitness & Gym

ACEest Fitness & Gym is a small Flask web application for the DevOps Assignment 1. It provides a coach workspace for client management, training programs, workout logging, membership status, and weekly adherence tracking. The project demonstrates a quality-gated delivery path using Python, Pytest, Docker, Jenkins, and GitHub Actions.

## Assignment objective

The application converts the supplied fitness-management concepts into a maintainable browser-based Flask service. SQLite keeps local development portable, deterministic rules power the program generator, and every important workflow is accessible through Flask's test client.

## Technology stack

- Python 3.12 and Flask 3.1
- SQLite with a local database created automatically at first run
- Pytest and Ruff for testing and quality checks
- Docker with Gunicorn for the runtime image
- Declarative Jenkins Pipeline and GitHub Actions

## Features

- Staff login with a hashed demonstration password (`admin` / `admin`)
- Dashboard with client, membership, program, and workout summaries
- Client create, view, update, and delete operations
- Fat Loss, Muscle Gain, and Beginner programs with calorie factors 22, 35, and 26
- Rule-based weekly program generation for beginner, intermediate, and advanced levels
- Workout logging for Strength, Hypertrophy, Cardio, and Mobility
- Weekly adherence records and membership end dates
- JSON health endpoint at `/health`

## Architecture and structure

`app.py` contains the application factory, routes, SQLite schema initialization, and domain helpers such as `calculate_calories`. Templates provide the web views, while the test fixture creates a fresh database for every test.

```text
.
├── app.py
├── requirements.txt
├── Dockerfile
├── Jenkinsfile
├── pytest.ini
├── .github/workflows/main.yml
├── templates/
├── static/css/style.css
├── tests/
└── instance/                   # Runtime SQLite data, ignored by Git
```

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. The database initializes automatically. The demonstration login is `admin` / `admin`; set `DEMO_USERNAME`, `DEMO_PASSWORD`, and `SECRET_KEY` environment variables for a different local configuration. These defaults are for assessment demonstration only.

## Tests and quality checks

```bash
python -m compileall -q .
python -m ruff check app.py tests
python -m pytest -q
```

The suite covers startup, health, authentication, database initialization, client CRUD, invalid input, calorie calculation, program generation, workouts, and progress validation. A normal virtual environment also supports the requested `pytest -q` command.

## Docker

```bash
docker build -t aceest-fitness-devops .
docker run --rm -p 5000:5000 aceest-fitness-devops
curl http://127.0.0.1:5000/health
# {"status":"healthy"}
```

The service listens on `0.0.0.0:5000`. The image contains the test suite so CI can run `python -m pytest -q` inside the container. Runtime databases are not committed.

## GitHub Actions

`.github/workflows/main.yml` runs for every push and pull request:

1. **Build and lint** checks out source, installs dependencies, compiles Python, runs Ruff, and runs Pytest.
2. **Docker image assembly** builds the tagged application image.
3. **Container tests** builds a test image, runs Pytest inside it, and starts the service to verify `/health`.

```text
Developer -> Git commit -> GitHub push / pull request -> Actions
-> Build & Lint -> Pytest -> Docker build -> Containerized tests
-> Jenkins secondary quality validation
```

## Jenkins

`Jenkinsfile` is a declarative pipeline with Checkout, dependency installation, syntax check, unit tests, Docker build, and container test stages. Any failed stage stops the build. Jenkins requires a node with Python, pip, and Docker access.

To configure a job:

1. Create a Pipeline job in Jenkins.
2. Select **Pipeline script from SCM**, choose Git, and enter the GitHub repository URL.
3. Select the branch, such as `*/main`, and use script path `Jenkinsfile`.
4. Add a GitHub webhook at `https://your-jenkins-host/github-webhook/`, or enable polling.
5. Run the job and review the stage results. Use Jenkins credentials for private repositories; none are stored here.

Jenkins execution is represented and documented here; it is not claimed to have run inside this Codespace.

## Security considerations

The demo account exists only for evaluation. Passwords are hashed, but a real deployment should use a secret manager, rotate `SECRET_KEY`, replace the demo account, use HTTPS, and add stronger authorization and CSRF protection. Do not commit `.env` files, database files, credentials, tokens, or personal client information.

## Troubleshooting

- If port 5000 is occupied, use another host port such as `-p 5050:5000`.
- Remove `instance/aceest.db` to reset the local database.
- If bare `pytest` uses a system environment, activate the project virtual environment or use `python -m pytest -q`.
- Docker must be installed and its daemon available for image and Jenkins stages.

## Conclusion

This repository provides a focused, testable Flask fitness application and reproducible CI/CD demonstration. The gates catch syntax, lint, unit-test, image-build, and container-startup regressions before delivery.

## First meaningful commit and push

```bash
git add .
git commit -m "Build ACEest Fitness CI/CD assignment"
git push origin main
```
