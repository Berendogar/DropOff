# DropOff — Case Study 7

**Student:** Beren Dogar
**Repository:** https://github.com/Berendogar/DropOff
**Hosted URL:** https://dropoff-beren-dogar.onrender.com

I ran the starter on my machine and walked sign-in, the file list, upload, and download before changing the code.

## How it fits together

```text
Browser
  login, upload, list, download
        |
        v
FastAPI  +  Jinja pages  +  static/style.css
        |
        +-- SQLite  data/dropoff.db     users, and which file belongs to whom
        +-- disk    data/uploads/       the actual bytes
                    data/private/       not a student drop
```

The signed-in user id sits in the session cookie. The home page does not scan the folder. It selects `files` rows for that user id only.

After the first request, `data/` has three things the app created itself:

- `dropoff.db` — maya, devon, and one file row for maya
- `uploads/lab1-maya.txt` — Maya's sample lab
- `private/grader.txt` — a TA note. It is not a submission and it never gets a row in `files`

So Maya's home page shows her lab, and Devon's is empty, even though `lab1-maya.txt` is sitting in the folder. A file that is only on disk does not show up in the list.

Where an upload used to land: the original filename, straight under `data/uploads/`. `lab2.txt` became `data/uploads/lab2.txt`, and that same string was saved on the row.

How a download became a path: the link was `/download?name=<stored name>`. The handler joined that string onto the uploads folder and returned the file. It did not look at the session, and it did not check that the path stayed inside `uploads/`.

## The bug

`os.path.join` will follow `..`. Nobody has to be signed in.

```text
GET /download?name=../private/grader.txt
```

That came back 200 with the TA note from `data/private/grader.txt`. The same request with `name=lab1-maya.txt` downloads Maya's lab with no cookie.

Upload does the same join. Signed in as devon, I posted a file whose name was `../private/planted.txt`. It was written to `data/private/planted.txt`, not under `uploads/`.

## What I changed

Download is now `/download/<id>`, and you have to be signed in. The lookup is `id` and `user_id` together, so guessing Maya's id as Devon does not return her file. The stored path is resolved and refused if it is not inside `data/uploads`.

New uploads go to `data/uploads/<user id>/<random name>`. The original filename stays in SQLite and is the name the browser gets back, so a normal download is still `lab2.txt`. A filename that contains `/` or `\` is rejected and nothing is written.

Maya's old sample still downloads. Its stored name is `lab1-maya.txt`, which is already inside `uploads/`.

`pytest -q` — 6 passed. That covers `/health`, a signed-out download, the old `../private/grader.txt` URL, another user's id, a normal upload that keeps the original name, and an upload named with `..`.

Hosted at https://dropoff-beren-dogar.onrender.com. The free instance sleeps when nobody is using it, and the disk does not stick around, so a cold start builds `data/` again (demo users, Maya's sample, the private TA note). Demo accounts are unchanged: `maya` / `devon`, password `campus123`.
