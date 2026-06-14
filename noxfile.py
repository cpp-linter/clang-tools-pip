import nox


@nox.session
def lint(session: nox.Session) -> None:
    """Run linter"""
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", external=True)


@nox.session
def test(session: nox.Session) -> None:
    """Run tests"""
    session.install("--upgrade", "pip")
    session.install("-e", ".[dev]")
    session.run("coverage", "run", "-m", "pytest", "tests/", external=True)


@nox.session
def docs(session: nox.Session) -> None:
    """Build docs"""
    session.install("--upgrade", "pip")
    session.install(".[docs]")
    session.run("mkdocs", "build", external=True)


@nox.session(name="docs-serve")
def docs_serve(session: nox.Session) -> None:
    """Serve docs with live reload"""
    session.install(".[docs]")
    session.run("mkdocs", "serve", external=True)
