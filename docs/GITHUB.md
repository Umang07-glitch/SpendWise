# GitHub repository contents

The repository contains application source, dependency definitions, database migrations,
automated tests, Docker configuration, example data and setup documentation.

Local account databases, session data, installed dependencies, downloaded runtimes,
environment secrets, generated financial screenshots and personalized academic reports
are excluded by `.gitignore`. The original local files remain in the workspace.

## Fresh clone

Follow the Docker or native Windows setup in `README.md`. A new clone does not contain
existing local accounts or their financial records. Run the explicit seed command to
create the fictional demonstration account, or register an empty new account.

## Verification status

See `VERIFICATION.md` for the checks performed and their limits. The Android folder is
an unfinished WebView extension; a working APK is not included. GitHub Actions is
configured to check the web application, but a successful remote CI run must be verified
after publication.

## Publishing

Choose public visibility to share source with anyone, or private visibility to restrict
access to invited collaborators. Uploading source does not deploy the application or
make a local development server publicly available. Review staged files before every
push, and never commit a personal database, `.env` secrets or signing keys.
