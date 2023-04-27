# openssl req -x509 -newkey rsa:2048 -keyout private.key -out public.cert -days 365
import sys

from omniscient.signher import sign_file, verify_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python signer.py <op> <file_path> <cert_path> [<key_path>]")
        sys.exit(1)

    op = sys.argv[1]

    if op == "sign":
        if len(sys.argv) < 5:
            print("Usage: python signer.py sign <file_path> <cert_path> <key_path>")
            sys.exit(1)
        sign_file(sys.argv[2], sys.argv[3], sys.argv[4])
    elif op == "verify":
        if len(sys.argv) < 4:
            print("Usage: python signer.py verify <file_path> <cert_path>")
            sys.exit(1)

        with open(sys.argv[2], "rb") as f:
            data = f.read()

        if verify_file(data, "/dev/null", sys.argv[3]):
            print("Signature verified.")
        else:
            print("Signature verification failed.")

    else:
        print("I have no idea what you want to do.")
