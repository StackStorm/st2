#!/bin/bash
set -eo pipefail

FIXTURE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

cd "${FIXTURE_DIR}/ca"

# regenerate the CA (w/ 15 year duration)
openssl req -new \
    -x509 \
    -key private/ca_private_key.pem \
    -config openssl.cnf \
    -subj '/CN=MyTestCA/' \
    -days $((365*15)) \
    -out ca_certificate_bundle.pem

# convert the PEM format cert to DER format
openssl x509 \
    -outform DER \
    -in ca_certificate_bundle.pem \
    -out ca_certificate_bundle.cer

# update the CA db so that it records that certs have expired.
openssl ca -config openssl.cnf -updatedb

for x in server client; do
    # Regenerate the CSR
    openssl req -new \
        -key ../${x}/private_key.pem \
        -config openssl.cnf \
        -reqexts ${x}_ca_extensions \
        -subj "/CN=localhost/O=${x}/" \
        -out ../${x}/req.pem

    # Create the x509 cert signed by our CA
    openssl ca -batch \
        -config openssl.cnf \
        -in ../${x}/req.pem

    # Copy the cert without the prologue
    openssl x509 \
        -in "certs/$(cat serial.old).pem" \
        -out ../${x}/${x}_certificate.pem

    # Convert the x509 key+cert to a p12/pfx format file.
    # These certificates are only used for tests, so including
    # the plaintext password here is not a problem.
    openssl pkcs12 -export \
        -out ../${x}/${x}_certificate.p12 \
        -inkey ../${x}/private_key.pem \
        -in ../${x}/${x}_certificate.pem \
        -password pass:MySecretPassword
done

sed -i -e 's/notAfter=[^`]*'"/$(openssl x509 -in ca_certificate_bundle.pem -noout -dates | grep notAfter)/" "${FIXTURE_DIR}/README.md"
