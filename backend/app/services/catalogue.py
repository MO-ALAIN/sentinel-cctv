"""Source catalogue: preserve provenance, never fabricate cameras or register accounts."""
import logging
import httpx
from urllib.parse import urlsplit, urlunsplit, quote
from app.config import get_settings
from app.services.sighting_repository import sighting_repo
from app.paths import MEDIA_DIR, contained_file

logger = logging.getLogger(__name__)

class CatalogueService:
    def __init__(self):
        self.settings = get_settings()
        self._session = None
        self.last_error = None

    async def fetch_catalogue(self, force_refresh=False):
        if force_refresh:
            try:
                if self._session is None or self._session.is_closed:
                    self._session = httpx.AsyncClient(timeout=15,follow_redirects=True)
                response = await self._session.get(self.settings.CATALOGUE_URL)
                if 'json' not in response.headers.get('content-type','') and self.settings.SENTINEL_PASSWORD:
                    if not self.settings.SENTINEL_EMAIL:
                        raise ValueError('Configure both organizer email and password')
                    await self._session.post('https://cctv.corp8.cloud/auth/login',data={'email':self.settings.SENTINEL_EMAIL,'password':self.settings.SENTINEL_PASSWORD})
                    response = await self._session.get(self.settings.CATALOGUE_URL)
                response.raise_for_status()
                raw = response.json()
                raw = raw.get('cameras',[]) if isinstance(raw,dict) else raw
                if not isinstance(raw,list):
                    raise ValueError('Catalogue must contain a camera list')
                from app.api.registry_tools import CameraCreate
                rows = []
                for cam in raw:
                    cid = str(cam.get('id',''))
                    existing = sighting_repo.get_camera(cid)
                    if existing:
                        continue  # Preserve operator-verified coordinates and source configuration.
                    urls = cam.get('urls') or {}
                    source_url = cam.get('rtsp_url') or cam.get('rtsp') or urls.get('rtsp') or cam.get('hls_url') or urls.get('hls')
                    # The authenticated deployment's own /resource guide explicitly
                    # supplies this pattern for its id/name-only cameras.json manifest.
                    catalogue = urlsplit(self.settings.CATALOGUE_URL)
                    if not source_url and catalogue.hostname == 'cctv.corp8.cloud' and catalogue.path == '/cameras.json':
                        source_url = self.settings.RTSP_BASE_URL.rstrip('/')+'/'+quote(cid,safe='')
                    if not source_url:
                        raise ValueError('Catalogue entry has no explicit RTSP or HLS URL')
                    row = {'id':cid, 'name':cam.get('name') or cid,
                           'location':cam.get('location') or cam.get('name') or '',
                           'department':cam.get('department') or '', 'district':cam.get('district') or '',
                           'source_type':'GOVERNMENT_REPLAY', 'source_system':cam.get('source_system') or 'Organizer catalogue',
                           'rtsp_url':source_url,
                           'stream_codec':cam.get('codec') or '',
                           'stream_width':cam.get('width'), 'stream_height':cam.get('height'),
                           'declared_fps':cam.get('fps'), 'catalogue_live':cam.get('live')}
                    # Coordinates require explicit source attribution; no illustrative city substitution.
                    if cam.get('lat') is not None and cam.get('lon') is not None:
                        row.update(lat=cam['lat'],lon=cam['lon'],geo_source='REPRESENTATIVE')
                    rows.append(CameraCreate(**row).model_dump())
                sighting_repo.save_cameras(rows,'catalogue import')
                self.last_error = None
            except Exception as exc:
                self.last_error = 'Catalogue unavailable; check authorized access and endpoint configuration'
                logger.warning('Catalogue refresh failed (%s)',type(exc).__name__)
        return sighting_repo.list_cameras()

    async def get_camera_by_id(self,camera_id):
        cam = sighting_repo.get_camera(camera_id)
        if cam and cam.get('source_type') == 'RECORDED' and cam.get('rtsp_url'):
            cam['rtsp_url'] = str(contained_file(MEDIA_DIR,cam['rtsp_url']))
        elif cam and cam.get('source_type') == 'GOVERNMENT_REPLAY' and cam.get('rtsp_url'):
            source, organizer = urlsplit(cam['rtsp_url']), urlsplit(self.settings.RTSP_BASE_URL)
            if source.scheme == 'rtsp' and source.hostname == organizer.hostname and source.port == organizer.port and not source.username:
                if self.settings.SENTINEL_EMAIL and self.settings.SENTINEL_PASSWORD:
                    authority = quote(self.settings.SENTINEL_EMAIL,safe='')+':'+quote(self.settings.SENTINEL_PASSWORD,safe='')+'@'+source.netloc
                    cam['rtsp_url'] = urlunsplit((source.scheme,authority,source.path,source.query,''))
        return cam

    async def close(self):
        if self._session:
            await self._session.aclose()

catalogue_service = CatalogueService()
