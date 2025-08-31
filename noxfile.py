import nox

# Default tag for docker images
TAG = "latest"


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
    session.run("sphinx-build", "-b", "html", "docs/", "docs/_build/html")


@nox.session(name="docs-live")
def docs_live(session: nox.Session) -> None:
    session.install(".[docs]")
    session.run("sphinx-autobuild", "docs/", "docs/_build/html", external=True)
