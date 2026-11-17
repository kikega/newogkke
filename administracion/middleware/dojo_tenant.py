"""
Middleware y utilidades Multi-Tenant para resolución automática de Dojos
por subdominio (<slug>.ogkke.es) o dominio personalizado (ej. karatebudokan.es).
"""
from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from administracion.models import Dojo, normalizar_dominio

DOJO_CUSTOM_DOMAINS_CACHE_KEY = "ogkke_dojo_custom_domains_v1"
DOJO_HOST_MAP_CACHE_PREFIX = "ogkke_dojo_host_"


def invalidate_dojo_domain_cache():
    """Invalida la caché de dominios personalizados de Dojos."""
    try:
        cache.delete(DOJO_CUSTOM_DOMAINS_CACHE_KEY)
    except Exception:
        pass


def get_cached_custom_domains():
    """
    Devuelve el conjunto de dominios personalizados activos registrados por los Dojos.
    Se almacena en caché para evitar consultas repetidas en ALLOWED_HOSTS.
    """
    try:
        domains = cache.get(DOJO_CUSTOM_DOMAINS_CACHE_KEY)
        if domains is not None:
            return domains
    except Exception:
        domains = None

    try:
        raw_domains = (
            Dojo.objects.filter(sitio_activo=True)
            .exclude(dominio_personalizado__isnull=True)
            .exclude(dominio_personalizado="")
            .values_list("dominio_personalizado", flat=True)
        )
        domains = tuple(
             sorted({d.strip().lower() for d in raw_domains if d and d.strip()})
        )
        cache.set(DOJO_CUSTOM_DOMAINS_CACHE_KEY, domains, 300)
        return domains
    except Exception:
        return ()


class DynamicDojoAllowedHosts(list):
    """
    Envuelve ALLOWED_HOSTS para que Django valide en primer lugar los hosts estáticos
    del Core (cortocircuitando sin tocar BD) y, solo si el Host entrante es un dominio
    externo, compruebe los dominios personalizados activos de Dojos en caché.
    """

    def __iter__(self):
        yield from super().__iter__()
        for custom_domain in get_cached_custom_domains():
            yield custom_domain
            yield f".{custom_domain}"


def extract_clean_host(raw_host):
    """Extrae el nombre de host en minúsculas sin puerto ni corchetes IPv6."""
    if not raw_host:
        return ""
    host = raw_host.strip().lower()
    if host.startswith("["):
        return host.split("]")[0] + "]"
    return host.split(":")[0].strip(".")


def is_core_host(clean_host):
    """Indica si el host pertenece al Core Nacional de OGKKE."""
    if not clean_host:
        return True
    base_domain = getattr(settings, "DOJO_BASE_DOMAIN", "ogkke.es").lower()
    core_hosts = {
        h.lower()
        for h in getattr(
            settings,
            "CORE_HOSTS",
            [base_domain, f"www.{base_domain}", "localhost", "127.0.0.1", "testserver"],
        )
    }
    return clean_host in core_hosts


def resolve_dojo_from_host(raw_host):
    """
    Resuelve y devuelve la instancia de Dojo (con sitio_activo=True) correspondiente
    a un subdominio (<slug>.<DOJO_BASE_DOMAIN> o <slug>.localhost) o a un dominio propio.
    Devuelve None si el host pertenece al Core Nacional o no coincide con ningún Dojo activo.
    """
    clean_host = extract_clean_host(raw_host)
    if not clean_host or is_core_host(clean_host):
        return None

    base_domain = getattr(settings, "DOJO_BASE_DOMAIN", "ogkke.es").lower()
    subdomain_slug = None

    for suffix in (f".{base_domain}", ".localhost"):
        if clean_host.endswith(suffix):
            candidate = clean_host[: -len(suffix)]
            if candidate and candidate != "www" and "." not in candidate:
                subdomain_slug = candidate
            break

    if subdomain_slug:
        return Dojo.objects.filter(slug__iexact=subdomain_slug, sitio_activo=True).first()

    normalized = normalizar_dominio(clean_host)
    if not normalized:
        return None

    return Dojo.objects.filter(
        dominio_personalizado__iexact=normalized,
        sitio_activo=True,
    ).first()


class DojoTenantMiddleware:
    """
    Detecta si la petición entra por el dominio/subdominio propio de un Dojo local
    e inyecta `request.current_dojo` y `request.is_dojo_host`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not isinstance(settings.ALLOWED_HOSTS, DynamicDojoAllowedHosts):
            settings.ALLOWED_HOSTS = DynamicDojoAllowedHosts(settings.ALLOWED_HOSTS)

        raw_host = request.META.get("HTTP_X_FORWARDED_HOST") or request.META.get("HTTP_HOST", "")
        if "," in raw_host:
            raw_host = raw_host.split(",")[0].strip()

        dojo = resolve_dojo_from_host(raw_host)
        request.current_dojo = dojo
        request.is_dojo_host = dojo is not None

        return self.get_response(request)


@receiver(post_save, sender=Dojo)
@receiver(post_delete, sender=Dojo)
def _clear_dojo_domains_on_change(sender, **kwargs):
    invalidate_dojo_domain_cache()
