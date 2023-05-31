import sys

from OpenSSL import crypto


def ssl_sign_file(data: str, cert_path: str, key_path: str) -> bytes:
    """
    Sign a file using OpenSSL.
    """

    try:
        key = crypto.load_privatekey(
            crypto.FILETYPE_PEM, open(key_path).read())
        signature = crypto.sign(key, data, 'sha256')
    except crypto.Error as e:
        print("Failed to sign file:")
        print(e)
        sys.exit(1)

    return signature


def sign_file(file_path: str, cert_path: str, key_path: str) -> None:
    """
    Sign a file using OpenSSL.
    """

    with open(file_path, "rb") as fd:
        lines = fd.read()

    lines = lines.split(b"\n")

    if len(lines) > 3:
        if lines[0].rstrip() == b"--- SIGNATURE START ---" and lines[2].rstrip() == b"--- SIGNATURE END ---":
            lines = lines[3:]

    data = b"\n".join(lines)

    signature = ssl_sign_file(data, cert_path, key_path)

    lines.insert(0, b"--- SIGNATURE START ---\n")
    lines.insert(1, signature.hex().encode() + b"\n")
    lines.insert(2, b"--- SIGNATURE END ---\n")

    data = b"\n".join(lines)

    with open(file_path, "w") as fd:
        fd.write(data.decode())


def verify_file(data: bytes, file_path: str, cert_path: str) -> bool:
    """
    Verify a file using OpenSSL.
    """

    lines = data.split(b"\n")

    if len(lines) < 3:
        print("File is not signed")
        return False

    if lines[0] != b"--- SIGNATURE START ---" or lines[2] != b"--- SIGNATURE END ---":
        print("File is not signed")
        return False

    signature = lines[1].strip().decode()
    data = b"\n".join(lines[3:])

    try:
        cert = crypto.load_certificate(
            crypto.FILETYPE_PEM, open(cert_path).read())
        crypto.verify(cert, bytes.fromhex(signature), data, 'sha256')
    except crypto.Error as e:
        print(f"Failed to verify file: {e}")
        return None

    with open(file_path, "w") as fd:
        fd.write(data.decode())

    return True
