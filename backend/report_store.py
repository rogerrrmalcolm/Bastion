from __future__ import annotations

from functools import lru_cache

from psycopg.types.json import Jsonb

from database import get_postgres_pool
from schemas import AnalyzeRequest, InvestmentMemo, ReportPackage


class PostgresReportStore:
    """Persist completed report packages independently of LangGraph checkpoints."""

    def __init__(self, pool=None) -> None:
        self._pool = pool or get_postgres_pool()

    def save(
        self,
        *,
        workflow_run_id: str,
        session_id: str,
        request: AnalyzeRequest,
        investment_memo: InvestmentMemo,
        report: ReportPackage,
    ) -> None:
        with self._pool.connection() as connection:
            connection.execute(
                """
                insert into public.final_reports (
                    workflow_run_id,
                    session_id,
                    title,
                    recommendation,
                    request_payload,
                    investment_memo,
                    report_payload
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                on conflict (workflow_run_id) do update set
                    session_id = excluded.session_id,
                    title = excluded.title,
                    recommendation = excluded.recommendation,
                    request_payload = excluded.request_payload,
                    investment_memo = excluded.investment_memo,
                    report_payload = excluded.report_payload,
                    updated_at = now()
                """,
                (
                    workflow_run_id,
                    session_id,
                    report.title,
                    investment_memo.recommendation,
                    Jsonb(request.model_dump(mode="json")),
                    Jsonb(investment_memo.model_dump(mode="json")),
                    Jsonb(report.model_dump(mode="json")),
                ),
            )

    def get(self, workflow_run_id: str) -> dict | None:
        with self._pool.connection() as connection:
            return connection.execute(
                """
                select workflow_run_id, session_id, title, recommendation,
                       request_payload, investment_memo, report_payload,
                       created_at, updated_at
                from public.final_reports
                where workflow_run_id = %s
                """,
                (workflow_run_id,),
            ).fetchone()


@lru_cache(maxsize=1)
def get_report_store() -> PostgresReportStore:
    return PostgresReportStore()
