# DropOff — Case Study 7

**Student:** Beren Dogar
**Repository:** https://github.com/Berendogar/DropOff
**Hosted URL:** https://dropoff-beren-dogar.onrender.com

```text
Browser -> FastAPI + Jinja
              |
              +-- SQLite data/dropoff.db    who owns which file
              +-- data/uploads/             the bytes
              +-- data/private/             not a student file
```

The session cookie holds the user id. The home page lists that user's rows only. It does not scan the folder.

After the first request, `data/` has `dropoff.db`, `uploads/lab1-maya.txt`, and `private/grader.txt`. Maya sees her lab. Devon sees an empty list, even though Maya's file is on disk. `grader.txt` never gets a row.

An upload used to land at `data/uploads/<original name>`, and that same name was saved on the row. Download was `GET /download?name=...`. The handler joined `name` onto the uploads folder and did not check the session.

## Bug

`..` leaves the uploads folder. Nobody has to be signed in.

`GET /download?name=../private/grader.txt` returned the TA note. `name=lab1-maya.txt` returned Maya's lab with no cookie.

Upload did the same join. Signed in as devon, a file named `../private/planted.txt` was written under `data/private/`.

## Patch

Download is `/download/<id>` and requires a session. The lookup uses the id and the current user, so Devon cannot open Maya's row. The path is refused if it is outside `data/uploads`.

New files go to `data/uploads/<user id>/<random name>`. The original name stays in SQLite and is the name the browser saves. A name that contains `/` or `\` is rejected.

Maya's sample still downloads. Its stored name, `lab1-maya.txt`, is already inside `uploads/`.

`pytest -q`: 6 passed.

The free Render instance sleeps when idle and drops the database. A cold start creates the demo accounts and Maya's sample again. `maya` / `devon`, password `campus123`.
