from .models import AuditLog


def client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(request, action, module, obj=None, details=""):
    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        object_repr=str(obj)[:220] if obj is not None else "",
        details=details,
        ip_address=client_ip(request),
    )
