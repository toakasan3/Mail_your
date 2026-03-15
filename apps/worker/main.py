"""
MailGuard OSS - Worker Main Entry Point
"""
import asyncio
from arq import run_worker
from apps.worker.tasks import WorkerSettings


def main():
    """Run the ARQ worker."""
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()