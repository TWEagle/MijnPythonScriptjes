#!/usr/bin/env python3
import argparse
import time
import json
from pathlib import Path

import jwt
import requests
import pyperclip
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from jwcrypto import jwk

DEFAULT_EXP_OFFSET = 300  # 5 minuten


def load_private_key(path: Path, password: str = None):
    ext = path.suffix.lower()
    if ext in [".jwk", ".json"]:
        data_text = path.read_text(encoding="utf-8")
        key = jwk.JWK.from_json(data_text)
        pem_key_bytes = key.export_to_pem(private_key=True, password=None)
        return load_pem_private_key(pem_key_bytes, password=None)
    if ext in [".pem", ".key"]:
        pwd = password.encode("utf-8") if password else None
        return load_pem_private_key(path.read_bytes(), password=pwd)
    if ext in [".pfx", ".p12"]:
        pwd = password.encode("utf-8") if password else None
        key, cert, addl = load_key_and_certificates(path.read_bytes(), pwd)
        if key is None:
            raise ValueError("Geen private key gevonden in PKCS#12.")
        return key
    raise ValueError("Onbekend sleuteltype: gebruik .jwk/.json, .pem/.key of .pfx/.p12")


def build_jwt(iss_sub: str, aud: str, key, alg="RS256", kid=None):
    now = int(time.time())
    claims = {
        "iss": iss_sub,
        "sub": iss_sub,
        "aud": aud,
        "iat": now,
        "exp": now + DEFAULT_EXP_OFFSET,
    }
    headers = {"typ": "JWT", "alg": alg}
    if kid:
        headers["kid"] = kid

    token = jwt.encode(
        payload=claims,
        key=key,
        algorithm=alg,
        headers=headers
    )
    return token


def request_access_token(jwt_token: str, audience: str):
    url = "https://authenticatie-ti.vlaanderen.be/op/v1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": jwt_token,
        "audience": audience,
    }
    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    token_data = resp.json()
    return token_data.get("access_token", "")


def main():
    p = argparse.ArgumentParser(description="Genereer JWT en access_token (silent mode)")
    p.add_argument("--key", required=True, help="Pad naar private key (.jwk/.json/.pem/.pfx/.p12)")
    p.add_argument("--iss", required=True, help="Issuer (iss & sub)")
    p.add_argument("--aud", required=True, help="Audience claim in JWT")
    p.add_argument("--token-audience", help="Audience voor token endpoint (fallback: iss)", default=None)
    p.add_argument("--kid", help="Optional kid header", default=None)
    p.add_argument("--password", help="Key password (optioneel)", default=None)
    p.add_argument("--save", action="store_true", help="Sla JWT en access_token ook naar bestanden")
    p.add_argument("--clip", action="store_true", help="Kopieer access_token ook naar klembord")
    args = p.parse_args()

    key_path = Path(args.key)
    if not key_path.exists():
        raise FileNotFoundError(f"Key file niet gevonden: {key_path}")

    key = load_private_key(key_path, args.password)

    # Stap 1: JWT maken
    jwt_token = build_jwt(args.iss, args.aud, key, kid=args.kid)
    print("\n=== JWT (client_assertion) ===\n")
    print(jwt_token)

    # Stap 2: Access token aanvragen
    audience = args.token_audience or args.iss
    try:
        access_token = request_access_token(jwt_token, audience)
        print("\n=== Access Token ===\n")
        print(access_token)
    except Exception as e:
        print("\n[FOUT] Access token aanvraag mislukt:", str(e))
        access_token = ""

    # Stap 3: Optioneel wegschrijven
    if args.save:
        outdir = key_path.parent
        jwt_file = outdir / "jwt.txt"
        token_file = outdir / "access_token.txt"

        jwt_file.write_text(jwt_token, encoding="utf-8")
        print(f"[INFO] JWT opgeslagen naar {jwt_file}")

        if access_token:
            token_file.write_text(access_token, encoding="utf-8")
            print(f"[INFO] Access token opgeslagen naar {token_file}")

    # Stap 4: Optioneel kopiëren naar klembord
    if args.clip and access_token:
        pyperclip.copy(access_token)
        print("[INFO] Access token gekopieerd naar klembord")


if __name__ == "__main__":
    main()
