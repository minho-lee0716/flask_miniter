import  hashlib

m = hashlib.sha256()
m.update(b"test password")
m.hexdigest()
