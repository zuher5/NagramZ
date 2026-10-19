"""Verify a NagramZ APK: signing certificate + brand label.

Usage:
    python ci/verify-apk.py <apk-file-or-url>

Checks:
  1. The APK is signed with the permanent NagramZ release certificate.
  2. The NagramZ brand is present in the packaged resources.

Exit code is 0 only when both checks pass.
"""
import hashlib
import io
import os
import struct
import sys
import urllib.request
import zipfile

from cryptography import x509

EXPECTED_CERT = "abc77e8ae8b20436f66b7228bc466b47fc551fae2dc27a5531e7f3c33ff568fc"
BRAND = b"NagramZ"
V2_ID = 0x7109871A
V3_ID = 0xF05368C0


def load(source):
    if source.startswith("http://") or source.startswith("https://"):
        request = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        print(f"downloading {source}")
        return urllib.request.urlopen(request, timeout=900).read()
    with open(source, "rb") as handle:
        return handle.read()


def signing_block_entries(apk):
    """Return the id -> value map of the APK signing block."""
    eocd = apk.rfind(b"PK\x05\x06")
    if eocd == -1:
        return {}
    central_dir = struct.unpack("<I", apk[eocd + 16:eocd + 20])[0]
    magic_at = apk.rfind(b"APK Sig Block 42", 0, central_dir)
    if magic_at == -1:
        return {}

    end = magic_at - 8
    for start in range(max(0, end - 32768), end + 1):
        pos = start
        entries = {}
        while pos < end:
            if pos + 12 > end:
                break
            length = struct.unpack("<Q", apk[pos:pos + 8])[0]
            if length < 4 or pos + 8 + length > end:
                break
            ident = struct.unpack("<I", apk[pos + 8:pos + 12])[0]
            entries[ident] = apk[pos + 12:pos + 8 + length]
            pos += 8 + length
        if pos == end and (V2_ID in entries or V3_ID in entries):
            return entries
    return {}


def signer_certificates(apk):
    """Extract the signer certificates from the v2 and v3 signing blocks."""
    entries = signing_block_entries(apk)
    certificates = []
    for ident in (V2_ID, V3_ID):
        data = entries.get(ident)
        if not data:
            continue
        pos = 0

        def u32():
            nonlocal pos
            value = struct.unpack("<I", data[pos:pos + 4])[0]
            pos += 4
            return value

        u32()  # length of the signers payload
        while pos < len(data):
            signer_length = u32()
            signer = data[pos:pos + signer_length]
            pos += signer_length

            offset = 0

            def su32():
                nonlocal offset
                value = struct.unpack("<I", signer[offset:offset + 4])[0]
                offset += 4
                return value

            signed_data_length = su32()
            signed_data = signer[offset:offset + signed_data_length]
            offset += signed_data_length

            inner = 0

            def ssu32():
                nonlocal inner
                value = struct.unpack("<I", signed_data[inner:inner + 4])[0]
                inner += 4
                return value

            # Keep the offset in a separate variable: `inner += ssu32()` would
            # load `inner` before the call and lose the 4 bytes consumed.
            digests_length = ssu32()
            inner += digests_length
            certs_start = inner
            certs_length = ssu32()
            certs_end = certs_start + certs_length
            while inner < certs_end:
                item_length = ssu32()
                certificates.append(signed_data[inner:inner + item_length])
                inner += item_length
    return certificates


def main(source):
    apk = load(source)
    print(f"size: {len(apk)} bytes")

    certificates = signer_certificates(apk)
    if not certificates:
        print("signature: NOT FOUND (APK is unsigned or uses an unknown scheme)")
        return 1

    signed_ok = True
    for der in certificates:
        certificate = x509.load_der_x509_certificate(der)
        fingerprint = hashlib.sha256(der).hexdigest()
        matches = fingerprint == EXPECTED_CERT
        signed_ok = signed_ok and matches
        print(f"subject   : {certificate.subject.rfc4514_string()}")
        print(f"sha256    : {fingerprint}")
        print(f"permanent : {matches}")

    with zipfile.ZipFile(io.BytesIO(apk)) as archive:
        arsc = archive.read("resources.arsc")
    branded = BRAND in arsc
    print(f"brand     : {'NagramZ' if branded else 'NOT FOUND'}")

    if not signed_ok:
        print("RESULT: MISMATCH - do not publish, users could not update in place")
        return 1
    if not branded:
        print("RESULT: MISMATCH - branding was not applied")
        return 1
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
