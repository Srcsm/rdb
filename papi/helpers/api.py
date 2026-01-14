import aiohttp
import logging
from typing import Optional

log = logging.getLogger("red.papi.helpers.api")

class APIHelper:
    def __init__(self, session: aiohttp.ClientSession, config, version: str):
        self.session = session
        self.config = config
        self.ver = version
    
    async def parse_placeholder_via_api(self, placeholder: str, player: Optional[str], settings: dict) -> Optional[dict]:
        """Query PAPIRestAPI to parse a placeholder"""
        debug = settings["debug"]
        api_url = settings["api_url"]
        api_key = settings["api_key"]

        clean_placeholder = placeholder.strip("%")
        
        params = {"placeholder": clean_placeholder}
        if player:
            params["player"] = player
        
        headers = {"X-API-Key": api_key}
        
        if debug:
            log.info(f"Making API request to {api_url}/api/parse with params: {params}")
        
        try:
            async with self.session.get(
                f"{api_url}/api/parse",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if debug:
                    log.info(f"API response status: {resp.status}")
                
                data = await resp.json()
                
                if debug:
                    log.info(f"API response data: {data}")
                
                return data
                
        except aiohttp.ClientError as e:
            log.error(f"API request failed: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error in API request: {e}", exc_info=True)
            return None
    
    @property
    def vzge_headers(self):
        return {
            "User-Agent": (
                f"Red-PAPICog/{self.ver}"
                "(+https://github.com/srcsm/rpd; jayms@duck.com)"
            )
        }
    
    def vzge_url(
        self,
        subject: str,
        render: str = "bust",
        size: int = 128,
        *,
        format: str | None = None, # jxl, webp, png
        no: list[str] | None = None, # ["shadow", "cape", "ears", "helmet", "overlay"]
        y: int | None = None,
        p: int | None = None,
        r: int | None = None, # roll
        model: str | None = None # slim/wide
    ) -> str:
        """
        Build a VZGE URL with optional parameters.
        Example:
            self._vzge_url("unascribed", render="bust", size=256, format="png")
        """
        
        base = f"https://vzge.me/{render}/{size}/{subject}"
        
        # Add format extension
        if format:
            base += f".{format}"
            
        params = []
        
        # Disable features
        if no:
            params.append("no=" + ",".join(no))
            
        # Angles
        if y is not None:
            params.append(f"y={y}")
        if p is not None:
            params.append(f"p={p}")
        if r is not None:
            params.append(f"r={r}")
            
        if model in ("slim", "wide"):
            params.append(model)
            
        if params:
            base += "?" + "&".join(params)
            
        return base