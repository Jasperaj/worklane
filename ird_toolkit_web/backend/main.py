"""
FastAPI app - exposes 5 IRD toolkit features as REST endpoints under /api/*,
and serves the static frontend (../static) at /.
"""
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import ird_service as svc

app = FastAPI(title="IRD Nepal Toolkit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class TdsListRequest(BaseModel):
    pan: str
    username: str
    password: str
    from_date: str
    to_date: str


class TdsListPdfsRequest(TdsListRequest):
    output_name: str = "output"


class VatCheckRequest(BaseModel):
    pan: str
    username: str
    password: str
    tax_year: str
    period: str
    pan_list: List[str]


class DateExtensionApplyRequest(BaseModel):
    pan: str
    fiscal_year: str
    application_date: str
    extended_upto: str
    reason: str


class DateExtensionPdfRequest(BaseModel):
    pan: str
    username: str
    password: str
    fiscal_year: str
    office_code: str = "2501"


class EtaxVoucherRequest(BaseModel):
    pan: str
    fiscal_year: str
    bearer_token: str


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tds-list")
def api_tds_list(body: TdsListRequest):
    rows = _wrap(svc.get_tds_list, body.pan, body.username, body.password, body.from_date, body.to_date)
    return {"rows": rows}


@app.post("/api/tds-list/pdfs")
def api_tds_list_pdfs(body: TdsListPdfsRequest):
    zip_bytes, count = _wrap(
        svc.get_tds_list_pdfs_zip, body.pan, body.username, body.password, body.from_date, body.to_date, body.output_name
    )
    if count == 0:
        raise HTTPException(status_code=404, detail="No TDS records / PDFs found for this PAN and date range.")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{body.output_name}_ETDS_Returns.zip"'},
    )


@app.post("/api/vat-check")
def api_vat_check(body: VatCheckRequest):
    rows = _wrap(svc.vat_filing_check, body.pan, body.username, body.password, body.tax_year, body.period, body.pan_list)
    return {"rows": rows}


@app.post("/api/date-extension/apply")
def api_date_extension_apply(body: DateExtensionApplyRequest):
    result = _wrap(
        svc.apply_date_extension_single, body.pan, body.fiscal_year, body.application_date, body.extended_upto, body.reason
    )
    return {"result": result}


@app.post("/api/date-extension/pdf")
def api_date_extension_pdf(body: DateExtensionPdfRequest):
    content = _wrap(svc.download_date_extension_pdf, body.pan, body.username, body.password, body.fiscal_year, body.office_code)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{body.pan}_date_extension.pdf"'},
    )


@app.post("/api/etax-voucher")
def api_etax_voucher(body: EtaxVoucherRequest):
    rows = _wrap(svc.etax_voucher_lookup, body.pan, body.fiscal_year, body.bearer_token)
    return {"rows": rows}


@app.get("/api/health")
def health():
    return {"status": "ok"}


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
