"""
ird_service.py
Core logic for talking to the IRD Nepal Taxpayer Portal.
Only covers: TDS list + PDFs, VAT filing check, date-extension apply/PDF,
and eTax voucher lookup - all scoped to the caller's own PAN/login.
"""
from __future__ import annotations

import json
import re
import time
import zipfile
from io import BytesIO

import pandas as pd
import requests
from bs4 import BeautifulSoup as bs

BASE = "https://taxpayerportal.ird.gov.np"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
STD_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": DEFAULT_UA,
    "Referer": f"{BASE}/taxpayer/app.html",
}


def parse_loose_json(text: str):
    """IRD's handlers return loosely-formatted JS objects. This quotes the
    bare keys and parses as real JSON instead of using eval()."""
    candidates = [text]
    try:
        soup = bs(text, "lxml")
        ps = soup.find_all("p")
        if ps:
            candidates.insert(0, ps[0].text)
    except Exception:
        pass

    key_pattern = re.compile(r'(?<!")\b(root|message|success|total)\b(?!")\s*:')
    for raw in candidates:
        fixed = key_pattern.sub(r'"\1":', raw)
        try:
            return json.loads(fixed)
        except Exception:
            continue
    return None


def df_to_records(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    return json.loads(df.where(pd.notnull(df), None).to_json(orient="records"))


def get_token(session: requests.Session) -> str:
    r = session.get(f"{BASE}/taxpayer/app.html#", headers={"User-Agent": DEFAULT_UA})
    soup = bs(r.text, "html.parser")
    scripts = soup.find_all("script")
    return scripts[1]["src"].replace("app.js?_dc=", "")


def portal_login(session: requests.Session, pan: str, username: str, password: str) -> str:
    header = {"user-agent": DEFAULT_UA}
    token = get_token(session)
    session.get(f"{BASE}/taxpayer/app/model/LoginUser.js?_dc={token}", headers=header)
    session.post(
        f"{BASE}/Handlers/E-SystemServices/Taxpayer/TaxPayerValidLoginHandler.ashx",
        data={
            "pan": pan,
            "TPName": username,
            "TPPassword": password,
            "formToken": "a",
        },
        headers=header,
    )
    return token


def gettds_list_df(session: requests.Session, token: str, pan: str, from_date: str, to_date: str) -> pd.DataFrame:
    url = (
        f"{BASE}/Handlers/TDS/GetTransactionHandler.ashx?method=GetWithholderRecs&_dc={token}"
        f'&objWith=%7B%22WhPan%22%3A%22{pan}%22%2C%22FromDate%22%3A%22{from_date}%22'
        f'%2C%22ToDate%22%3A%22{to_date}%22%7D&page=1&start=0&limit=25'
    )
    r = session.get(url, headers={"User-Agent": DEFAULT_UA})
    parsed = parse_loose_json(r.text)
    if not parsed or "root" not in parsed or not parsed["root"]:
        return pd.DataFrame()
    return pd.DataFrame(parsed["root"])


def get_tds_list(pan: str, username: str, password: str, from_date: str, to_date: str) -> list[dict]:
    session = requests.Session()
    token = portal_login(session, pan, username, password)
    df = gettds_list_df(session, token, pan, from_date, to_date)
    return df_to_records(df)


def download_etds_pdf_bytes(session: requests.Session, tranno) -> bytes:
    r = session.post(
        f"{BASE}/Reporting/TDS/ReportHandlers/TDSSubmissionReportHandler.ashx",
        headers={"user-agent": DEFAULT_UA},
        data={"TranNo": tranno, "Status": "V", "formToken": "a"},
    )
    return r.content


def get_tds_list_pdfs_zip(pan: str, username: str, password: str, from_date: str, to_date: str, output_name: str) -> tuple[bytes, int]:
    session = requests.Session()
    token = portal_login(session, pan, username, password)
    df = gettds_list_df(session, token, pan, from_date, to_date)
    if df.empty:
        return b"", 0

    buf = BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w") as zf:
        for tranno in df["TranNo"]:
            try:
                content = download_etds_pdf_bytes(session, tranno)
                zf.writestr(f"{output_name}_TDS_{from_date}_{to_date}_{tranno}.pdf", content)
                count += 1
            except Exception:
                continue
    return buf.getvalue(), count


def vat_filing_check(pan: str, username: str, password: str, tax_year: str, period: str, pan_list: list[str]) -> list[dict]:
    session = requests.Session()
    portal_login(session, pan, username, password)
    rows = []
    for check_pan in pan_list:
        data = {
            "method": "CheckVatReturnsExists",
            "pan": check_pan,
            "acctType": "00",
            "taxyear": tax_year,
            "fileper": "T",
            "period": period,
            "formToken": "a",
        }
        r = session.post(f"{BASE}/Handlers/VAT/VatUtilitiesHandler.ashx", headers=STD_HEADERS, data=data)
        parsed = parse_loose_json(r.text)
        status = "Unknown / error"
        if parsed:
            status = "Filed" if str(parsed.get("success")).lower() == "true" else "Not filed"
        rows.append({"pan": check_pan, "status": status})
    return rows


def apply_date_extension(pan: str, fiscal_year: str, application_date: str, extended_upto: str, reason: str) -> str:
    login_tbs = {
        "SubmissionNumber": 0,
        "Username": "Self",
        "Password": "Self",
        "ContactNo": None,
        "Emailid": None,
        "submittedFor": "EEXTFD",
        "SubmittedYN": "Y",
        "SubmittedDate": application_date,
        "TranNo": None,
        "Address": None,
        "RegOffice": None,
        "Action": "A",
        "PAN": str(pan),
        "FiscalYear": fiscal_year,
        "ExtensionFilingDate": {
            "SubmissionNo": 0,
            "Pan": str(pan),
            "Accttype": "10",
            "FisicalYear": fiscal_year,
            "ApplicationDate": application_date,
            "ExtensionReason": reason,
            "ExtendedUPTO": extended_upto,
            "ExtendedBy": None,
            "ExtendedName": None,
            "TranDate": application_date,
            "UserName": None,
            "RStatus": "F",
            "OfficeCode": 0,
            "Action": "A",
        },
    }
    data = {"method": "SaveExtensionFilingDateSubNo", "LoginTBS": json.dumps(login_tbs), "formToken": "a"}
    r = requests.post(
        f"{BASE}/Handlers/IncomeTax/ExtensionFillingDate/ExtensionFilingDateSubNoHandler.ashx",
        headers=STD_HEADERS,
        data=data,
    )
    return r.text


def apply_date_extension_single(pan: str, fiscal_year: str, application_date: str, extended_upto: str, reason: str) -> dict:
    try:
        resp_text = apply_date_extension(pan, fiscal_year, application_date, extended_upto, reason)
    except Exception as e:
        resp_text = f"ERROR: {e}"
    return {"pan": pan, "response": resp_text}


def download_date_extension_pdf(pan: str, username: str, password: str, fiscal_year: str, office_code: str = "2501") -> bytes:
    session = requests.Session()
    portal_login(session, pan, username, password)
    data = {
        "FiscalYear": fiscal_year,
        "submissionNo": "undefined",
        "ApplicationDate": "",
        "Extendedupto": "",
        "pan": str(pan),
        "officeCode": office_code,
        "PrintDate": "",
        "formToken": "a",
    }
    r = session.post(
        f"{BASE}/Reporting/ExtensionFillingDate/Handler/ExtensionFilingDateReportByPanHandler.ashx",
        headers={"User-Agent": DEFAULT_UA, "Referer": f"{BASE}/taxpayer/app.html"},
        data=data,
    )
    return r.content


TDSB_BASE = "https://taxpayerportalb.ird.gov.np:8081"


def etds_trans_login(session: requests.Session, sub_no: str, username: str, password: str) -> dict:
    r = session.post(
        f"{TDSB_BASE}/Handlers/TDS/TDSUserLoginHandler.ashx",
        headers=STD_HEADERS,
        data={"tranNo": str(sub_no), "username": username, "password": password, "formToken": "a"},
    )
    parsed = parse_loose_json(r.text)
    root = parsed.get("root") if isinstance(parsed, dict) else None
    return root if isinstance(root, dict) else {}


def etds_download_english_pdf(session: requests.Session, sub_no: str) -> bytes:
    r = session.post(
        f"{TDSB_BASE}/Reporting/TDS/ReportHandlers/TDSSubmissionEngReportHandler.ashx",
        headers=STD_HEADERS,
        data={"TranNo": str(sub_no), "Status": "V", "formToken": "a"},
    )
    return r.content


def etds_transaction_detail(session: requests.Session, sub_no: str) -> list[dict]:
    r = session.post(
        f"{TDSB_BASE}/Handlers/TDS/InsertTransactionHandler.ashx",
        params={"method": "GetTrans"},
        headers=STD_HEADERS,
        data={
            "objIns": json.dumps({"TransNo": int(sub_no), "RecStatus": "V", "FromDate": "1", "ToDate": "236250"}),
            "formToken": "a",
        },
    )
    parsed = parse_loose_json(r.text)
    root = parsed.get("root") if isinstance(parsed, dict) else None
    if not root:
        return []
    return df_to_records(pd.DataFrame(root))


def etds_voucher_detail(session: requests.Session, sub_no: str) -> list[dict]:
    r = session.post(
        f"{TDSB_BASE}/Handlers/TDS/VoucherInformationHandler.ashx",
        params={"method": "GetVouchInfo"},
        headers=STD_HEADERS,
        data={"TranNo": str(sub_no), "status": "V", "formToken": "a"},
    )
    parsed = parse_loose_json(r.text)
    root = parsed.get("root") if isinstance(parsed, dict) else None
    if not root:
        return []
    return df_to_records(pd.DataFrame(root))


def etds_trans_voucher_bulk(submissions: list[str], username: str, password: str) -> dict:
    login_rows, txn_rows, voucher_rows = [], [], []
    for sub_no in submissions:
        session = requests.Session()
        try:
            login_info = etds_trans_login(session, sub_no, username, password)
            login_info = {"TranNo": sub_no, **login_info} if login_info else {"TranNo": sub_no, "error": "login returned no data"}
            login_rows.append(login_info)
            txn_rows.extend(etds_transaction_detail(session, sub_no))
            voucher_rows.extend(etds_voucher_detail(session, sub_no))
        except Exception as e:
            login_rows.append({"TranNo": sub_no, "error": str(e)})
    return {"login": login_rows, "transactions": txn_rows, "vouchers": voucher_rows}


def etds_trans_voucher_excel_zip(submissions: list[str], username: str, password: str, output_name: str) -> tuple[bytes, int]:
    data = etds_trans_voucher_bulk(submissions, username, password)

    xlsx_buf = BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        pd.DataFrame(data["login"]).to_excel(writer, sheet_name="ETDS Details", index=False)
        pd.DataFrame(data["vouchers"]).to_excel(writer, sheet_name="Voucher Details", index=False)
        pd.DataFrame(data["transactions"]).to_excel(writer, sheet_name="TDS Voucher", index=False)

    zip_buf = BytesIO()
    count = 0
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(f"{output_name}_ETDS_Trans_Voucher_Details.xlsx", xlsx_buf.getvalue())
        for sub_no in submissions:
            try:
                session = requests.Session()
                etds_trans_login(session, sub_no, username, password)
                pdf_bytes = etds_download_english_pdf(session, sub_no)
                if pdf_bytes:
                    zf.writestr(f"{sub_no}_ETDS_English.pdf", pdf_bytes)
                    count += 1
            except Exception:
                continue
    return zip_buf.getvalue(), count


def etax_voucher_lookup(pan: str, fiscal_year: str, bearer_token: str) -> list[dict]:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": DEFAULT_UA,
    }
    params = {"panno": pan, "fiscalyear": fiscal_year}
    r = requests.get("https://etax.ird.gov.np:8000/api/Epayment/GetRasVouchers", params=params, headers=headers)
    parsed = parse_loose_json(r.text)
    if isinstance(parsed, list):
        return parsed
    return []
