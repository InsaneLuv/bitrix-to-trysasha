from functools import lru_cache

from app.core.settings.production import ProdAppSettings


@lru_cache
def get_app_settings() -> ProdAppSettings:
    app_env = ProdAppSettings
    return app_env()
