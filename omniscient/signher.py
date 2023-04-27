
import sys

from OpenSSL import crypto


def ssl_sign_file(data, cert_path, key_path):
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(cert_path).read())
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(key_path).read())
        signature = crypto.sign(key, data, 'sha256')
    except crypto.Error as e:
        print("Failed to sign file:")
        print(e)
        sys.exit(1)
        
    return signature

def sign_file(file_path, cert_path, key_path):
    with open(file_path, "rb") as fd:
        lines = fd.readlines()

    if len(lines) > 3:
        if lines[0] == "--- SIGNATURE START ---" and lines[2] == "--- SIGNATURE END ---":
            lines = lines[3:]

    data = b"".join(lines)

    signature = ssl_sign_file(data, cert_path, key_path)

    lines.insert(0, b"--- SIGNATURE START ---\n")
    lines.insert(1, signature.hex().encode() + b"\n")
    lines.insert(2, b"--- SIGNATURE END ---\n")

    data = b"".join(lines)
    
    with open(file_path, "w") as fd:
        fd.write(data.decode())

def verify_file(data, file_path, cert_path):
    lines = data.split("\n")
    
    if len(lines) < 3:
        print("File is not signed")
        sys.exit(1)

    if lines[0] != b"--- SIGNATURE START ---\n" or lines[2] != b"--- SIGNATURE END ---\n":
        print("File is not signed")
        sys.exit(1)

    signature = lines[1].strip().decode()
    data = b"".join(lines[3:])

    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(cert_path).read())
        crypto.verify(cert, bytes.fromhex(signature), data, 'sha256')
    except crypto.Error as e:
        return None

    with open(file_path, "w") as fd:
        fd.write(data.decode())

    return True
