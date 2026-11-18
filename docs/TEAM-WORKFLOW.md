# Team workflow

1. Clone the team's repository and follow [SETUP.md](../SETUP.md).
2. Branch from the latest shared main branch, for example `git switch -c feat/core-auth`.
3. Keep `.env`, local database data, build artifacts, and archives out of Git.
4. Coordinate model changes and migration merge order. Do not edit the same migration independently.
5. Run Django checks and tests, verify no model changes lack migrations, and build the frontend before review.
6. Open a pull request with the behavior changed and the checks completed.

Each teammate generates independent local credentials. Never share a populated
`.env` through Git. Add the team's GitHub URL as `origin` before pushing this starter.
