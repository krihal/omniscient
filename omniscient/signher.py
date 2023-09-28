import sys

from OpenSSL import crypto


def ssl_sign(data: str, key_path: str) -> bytes:
    with open(key_path, "r") as fd:
        key = fd.read()

    try:
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key)
        signature = crypto.sign(key, data, "sha256")
    except crypto.Error as e:
        print(f"Failed to sign file: {e}")
        sys.exit(1)

    return signature


def ssl_verify(data: str, signature: str, cert_path: str) -> bool:
    with open(cert_path, "r") as fd:
        cert = fd.read()

    try:
        crypt = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
        crypto.verify(crypt, bytes.fromhex(signature), data, "sha256")
    except crypto.Error as e:
        print(f"Failed to verify file: {e}")
        return False

    return True


def sign_file(file_path: str, sign_path: str, key_path: str) -> None:
    """
    Sign a file using OpenSSL.
    """
    with open(file_path, "r") as fd:
        file_data = fd.read()

    signature = ssl_sign(file_data, key_path)

    with open(sign_path, "w") as fd:
        fd.write(signature.hex())


def verify_file(file_path: str, sign_path: str, cert_path: str) -> bool:
    """
    Verify a file using OpenSSL.
    """
    try:
        with open(file_path, "rb") as fd:
            file_data = fd.read()

        with open(sign_path, "rb") as fd:
            sign_data = fd.read()
    except IOError as e:
        print("Failed to read file: ")
        print(e)
        sys.exit(1)

    return ssl_verify(file_data, sign_data.decode(), cert_path)
