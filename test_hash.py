import  hashlib

print(dir(hashlib))
sh = hashlib.sha256()

a = sh.update(b"test password")
print(sh)
print(a)

b = sh.hexdigest()
print(b)
