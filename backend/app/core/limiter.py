from slowapi import Limiter
from slowapi.util import get_remote_address

# 使用客戶端 IP 作為識別鍵
limiter = Limiter(key_func=get_remote_address)
