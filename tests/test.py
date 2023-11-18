# pip3 install PyJWT
import jwt
import datetime

# Token data
token_data = {
    "iss": "kubernetes/serviceaccount",
    "kubernetes.io/serviceaccount/namespace": "default",
    "kubernetes.io/serviceaccount/secret.name": "demo-token-custom",
    "kubernetes.io/serviceaccount/service-account.name": "demo",
    "kubernetes.io/serviceaccount/service-account.uid": "demo-sc-uid",
    "sub": "system:serviceaccount:default:my-serviceaccount",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
}

# Create the JWT
private_key = open("private.key", "rb").read()
token = jwt.encode(token_data, private_key, algorithm="RS256")
print(token)

