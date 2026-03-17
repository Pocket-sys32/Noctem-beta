import os
import httpx
from pydantic import BaseModel


BASE_URL = "https://mobile.fmcsa.dot.gov/qc/services"


class CarrierInfo(BaseModel):
    mc_number: str
    dot_number: str | None = None
    legal_name: str | None = None
    dba_name: str | None = None
    allowed_to_operate: bool = False
    out_of_service: bool = False
    out_of_service_date: str | None = None
    city: str | None = None
    state: str | None = None
    telephone: str | None = None


def _yn(value) -> bool:
    return str(value).upper() == "Y" if value is not None else False


class FMCSAClient:
    def __init__(self):
        self.web_key = os.environ["FMCSA_WEB_KEY"]
        self._http = httpx.AsyncClient(timeout=10.0)

    async def aclose(self):
        await self._http.aclose()

    async def lookup_mc(self, mc_number: str) -> CarrierInfo | None:
        url = f"{BASE_URL}/carriers/docket-number/{mc_number}/"
        resp = await self._http.get(url, params={"webKey": self.web_key})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

        content = data.get("content", data)
        # API returns content as a list; empty list means no carrier found
        if isinstance(content, list):
            if not content:
                return None
            # Each item wraps the carrier under a "carrier" key
            carrier = content[0].get("carrier", content[0])
        else:
            carrier = content.get("carrier", content)
        if not carrier:
            return None

        dot = carrier.get("dotNumber")
        return CarrierInfo(
            mc_number=mc_number,
            dot_number=str(dot) if dot else None,
            legal_name=carrier.get("legalName"),
            dba_name=carrier.get("dbaName"),
            allowed_to_operate=_yn(carrier.get("allowedToOperate")),
            out_of_service=carrier.get("oosDate") is not None,
            out_of_service_date=carrier.get("oosDate"),
            city=carrier.get("phyCity"),
            state=carrier.get("phyState"),
            telephone=carrier.get("telephone"),
        )
