"""Run one TTL cleanup pass for local development."""

import asyncio

from app.tasks.cleanup import run_cleanup_once


if __name__ == "__main__":
    report = asyncio.run(run_cleanup_once())
    print(report)
