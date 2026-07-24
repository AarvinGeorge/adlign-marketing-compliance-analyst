"""
meta:
  purpose: One-off: run the independent verifier over EXISTING flags (the seeded
           demo) so the per-flag "reviewers agree / split" signal shows without
           re-running a check. Idempotent (verify_run_flags skips already-verified
           flags). Advisory only: never changes a verdict, score, or state.
           Makes real cross-provider (OpenAI) calls; run it where the OpenAI key
           is set (e.g. inside the prod api container).
  contract: python -m adlign.scripts.backfill_verifier
  deps: config, db.engine, db.models, main.propagate_env, nodes.verify,
        services.verification.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from adlign.config import load_settings
from adlign.db.engine import get_engine, session_factory
from adlign.db.models import Run
from adlign.main import propagate_env
from adlign.pipeline.nodes.verify import production_verify_invoke
from adlign.services.verification import verify_run_flags


async def backfill() -> int:
    settings = load_settings()
    propagate_env(settings)  # export provider keys for langchain
    model_string = settings.model_for("verify")
    invoke = production_verify_invoke(model_string)

    engine = get_engine(settings.database_url)
    total = 0
    async with session_factory(engine)() as session:
        run_ids = (await session.execute(select(Run.id))).scalars().all()
        for run_id in run_ids:
            n = await verify_run_flags(session, run_id, invoke, model_string)
            if n:
                print(f"  run {run_id}: verified {n} flags")
            total += n
    return total


async def _main() -> None:
    n = await backfill()
    print(f"verifier backfill complete: {n} flags verified")


if __name__ == "__main__":
    asyncio.run(_main())
