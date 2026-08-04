import base64
import json
import secrets
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


_metadata_cache = {}


class SsoError(Exception):
    pass


def _b64url_decode(value):
    value += "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value.encode("ascii"))


def _json_get(url):
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_form(url, data):
    body = urlencode(data).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def microsoft_metadata(tenant_id):
    if tenant_id not in _metadata_cache:
        url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
        _metadata_cache[tenant_id] = _json_get(url)
    return _metadata_cache[tenant_id]


def build_authorization_url(auth_settings, redirect_uri):
    metadata = microsoft_metadata(auth_settings.tenant_id)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    params = {
        "client_id": auth_settings.client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",
    }
    return f"{metadata['authorization_endpoint']}?{urlencode(params)}", state, nonce


def exchange_code_for_tokens(auth_settings, code, redirect_uri):
    metadata = microsoft_metadata(auth_settings.tenant_id)
    return _post_form(
        metadata["token_endpoint"],
        {
            "client_id": auth_settings.client_id,
            "client_secret": auth_settings.get_client_secret(),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
        },
    )


def _public_key_from_jwk(jwk):
    exponent = int.from_bytes(_b64url_decode(jwk["e"]), "big")
    modulus = int.from_bytes(_b64url_decode(jwk["n"]), "big")
    return rsa.RSAPublicNumbers(exponent, modulus).public_key()


def verify_id_token(auth_settings, id_token, expected_nonce):
    try:
        header_part, payload_part, signature_part = id_token.split(".")
        header = json.loads(_b64url_decode(header_part))
        claims = json.loads(_b64url_decode(payload_part))
    except (ValueError, json.JSONDecodeError) as exc:
        raise SsoError("Token SSO invalido.") from exc

    if header.get("alg") != "RS256":
        raise SsoError("Algoritmo de firma SSO no permitido.")

    metadata = microsoft_metadata(auth_settings.tenant_id)
    jwks = _json_get(metadata["jwks_uri"])
    jwk = next((key for key in jwks.get("keys", []) if key.get("kid") == header.get("kid")), None)
    if not jwk:
        raise SsoError("No se encontro la llave publica para validar el token SSO.")

    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = _b64url_decode(signature_part)
    _public_key_from_jwk(jwk).verify(
        signature,
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    now = int(time.time())
    leeway_seconds = 60
    if claims.get("aud") != auth_settings.client_id:
        raise SsoError("El token SSO no pertenece a esta aplicacion.")
    if claims.get("iss") != metadata["issuer"]:
        raise SsoError("Emisor SSO invalido.")
    if claims.get("exp", 0) + leeway_seconds < now:
        raise SsoError("Token SSO expirado.")
    if claims.get("nbf", 0) - leeway_seconds > now:
        raise SsoError("Token SSO aun no valido.")
    if claims.get("nonce") != expected_nonce:
        raise SsoError("Nonce SSO invalido.")
    return claims


def user_from_claims(auth_settings, claims):
    email = (
        claims.get("preferred_username")
        or claims.get("email")
        or claims.get("upn")
        or ""
    ).strip().lower()
    if not email:
        raise SsoError("Microsoft no entrego correo del usuario.")

    allowed_domain = (auth_settings.allowed_domain or "").strip().lower()
    if allowed_domain and not email.endswith(f"@{allowed_domain}"):
        raise SsoError("El dominio del usuario no esta autorizado para ingresar.")

    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first() or User.objects.filter(username__iexact=email).first()
    if not user:
        if not auth_settings.auto_create_users:
            raise SsoError("Usuario no existe en el portal y la creacion automatica esta desactivada.")
        name_parts = (claims.get("name") or "").split()
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name_parts[0] if name_parts else "",
            last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",
        )
        if auth_settings.default_role:
            group, _created = Group.objects.get_or_create(name=auth_settings.default_role)
            user.groups.add(group)
    if not user.is_active:
        raise SsoError("Usuario inactivo en el portal.")
    return user
