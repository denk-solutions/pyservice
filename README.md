# pyservice

![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)
![Build Status](https://github.com/denk-solutions/pyservice/workflows/test/badge.svg)

Opinionated template for building Python services powered by PostgreSQL. Has authentication, logging and database migrations set up.

Under the hood, pyservice uses FastAPI for request processing, SQLAlchemy, asyncpg and alembic for interacting with the database.
