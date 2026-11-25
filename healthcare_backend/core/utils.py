from django.conf import settings


def get_client_ip(request):
    """Client IP, honouring REST_FRAMEWORK['NUM_PROXIES'] the same way DRF throttling does."""
    meta = request.META
    remote = meta.get("REMOTE_ADDR")
    num_proxies = settings.REST_FRAMEWORK.get("NUM_PROXIES") or 0
    xff = meta.get("HTTP_X_FORWARDED_FOR")
    if not num_proxies or not xff:
        return remote
    addrs = [a.strip() for a in xff.split(",")]
    return addrs[-min(num_proxies, len(addrs))]
