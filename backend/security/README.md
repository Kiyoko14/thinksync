# Security Module Documentation

Bu modul ThinkSync backend xavfsizligini ta'minlash uchun keng qamrovli vositalarni taqdim etadi.

## Modullar

### 1. validators.py - Input Validation va Sanitization

#### Asosiy funksiyalar:

**`sanitize_command(command: str, allow_operators: bool = False)`**
- Shell buyruqlarini tekshiradi va tozalaydi
- Xavfli buyruqlarni bloklaydi (rm -rf /, mkfs, shutdown, va h.k.)
- Command injection operatorlarini aniqlaydi (;, &&, ||, $(), va h.k.)
- Noto'g'ri sintaksisni aniqlaydi
- Qaytaradi: (is_safe, sanitized_command, error_message)

**`validate_ssh_config(config: Dict)`**
- SSH konfiguratsiyasini to'liq tekshiradi
- Host formatini validatsiya qiladi
- Port raqamini tekshiradi (1-65535)
- Username formatini validatsiya qiladi
- SSH key yoki password mavjudligini tekshiradi
- Qaytaradi: (is_valid, error_message)

**`is_safe_path(path: str)`**
- Fayl yo'llarini xavfsizlikka tekshiradi
- Path traversal hujumlarini bloklaydi (..)
- Null byte ineksiyalarini aniqlaydi
- Maxfiy system papkalariga kirishni oldini oladi
- Qaytaradi: (is_safe, error_message)

**`validate_env_var_name(name: str)`**
- Environment variable nomlarini tekshiradi
- Faqat harflar, raqamlar va pastki chiziqni qabul qiladi
- Injection hujumlarini oldini oladi

**`validate_deployment_script(script: str)`**
- Deployment skriptlarni xavfsizlikka tekshiradi
- Har bir qatorni alohida validatsiya qiladi
- Xavfli operatsiyalarni aniqlaydi
- Qaytaradi: (is_safe, list_of_warnings)

**`sanitize_log_output(output: str, max_length: int = 10000)`**
- Log chiqarishlarni tozalaydi
- Control belgilarni olib tashlaydi
- Juda uzun chiqarishlarni kesib tashlaydi
- Log injection hujumlarini oldini oladi

#### Xavfli buyruqlar ro'yxati:

```python
DANGEROUS_COMMANDS = [
    # File system vayron qilish
    "rm -rf /", "mkfs", "dd if=", "shred",
    
    # Tizimni boshqarish
    "shutdown", "reboot", "halt", "poweroff", "init 0", "init 6",
    
    # Disk operatsiyalari
    "mount", "umount", "fdisk", "parted",
    
    # Foydalanuvchi boshqaruvi
    "passwd", "useradd", "userdel", "usermod",
    
    # Ruxsatlarni o'zgartirish
    "chmod 777 /", "chmod -R 777 /", "chown -R",
    
    # Process o'chirish
    "kill -9 1", "killall init", "pkill systemd",
]
```

### 2. crypto.py - Kriptografiya Utilities

#### Asosiy funksiyalar:

**`encrypt_sensitive_data(data: str)`**
- Maxfiy ma'lumotlarni shifrlaydi (SSH keys, passwords)
- Fernet symmetric encryption ishlatadi
- Base64 encoded format qaytaradi
- Production uchun KMS (Key Management Service) tavsiya etiladi

**`decrypt_sensitive_data(encrypted_data: str)`**
- Shifrlangan ma'lumotlarni deshifrlaydi
- Xatoliklar yuzaga kelganda ValueError raise qiladi

**`mask_sensitive_value(value: str, visible_chars: int = 4)`**
- Maxfiy qiymatlarni maskalaydi
- Oxirgi N ta belgini ko'rsatadi
- Masalan: "my-secret-key-12345" → "***12345"
- Logging va API responslar uchun ishlatiladi

**`mask_ssh_key(key: str)`**
- SSH private keylarni maskalaydi
- Key turini ko'rsatadi (RSA, OPENSSH, EC, DSA)
- Masalan: "***RSA_KEY***"

**`mask_connection_string(conn_str: str)`**
- Database connection stringlaridagi parollarni maskalaydi
- Masalan: "postgres://user:pass@host" → "postgres://user:***@host"

**`generate_secure_token(length: int = 32)`**
- Kriptografik xavfsiz tokenlar generatsiya qiladi
- Tasodifiy URL-safe Base64 string qaytaradi

#### Environment Variables:

```bash
# Encryption key (production uchun MAJBURIY)
ENCRYPTION_KEY=your-base64-encoded-key

# Fallback uchun
ENCRYPTION_SALT=your-unique-salt
ENCRYPTION_PASSWORD=your-strong-password
```

#### Production uchun tavsiyalar:

- AWS KMS, Google Cloud KMS yoki Azure Key Vault ishlatish
- Envelope encryption pattern qo'llash
- Regular key rotation amalga oshirish
- Hardware Security Modules (HSM) ishlatish

### 3. audit.py - Security Audit Logging

#### SecurityEventType enum:

Barcha xavfsizlik hodisalari turlari:

```python
# Authentication
AUTH_LOGIN_SUCCESS
AUTH_LOGIN_FAILURE
AUTH_LOGOUT
AUTH_TOKEN_INVALID

# Authorization
AUTHZ_ACCESS_DENIED
AUTHZ_PRIVILEGE_ESCALATION

# Data access
DATA_SENSITIVE_ACCESS
DATA_EXPORT
DATA_DELETION

# Configuration
CONFIG_SERVER_CREATED
CONFIG_SERVER_UPDATED
CONFIG_SERVER_DELETED
CONFIG_SECRET_CREATED
CONFIG_SECRET_UPDATED
CONFIG_SECRET_DELETED

# Commands
COMMAND_EXECUTED
COMMAND_BLOCKED
COMMAND_FAILED

# Deployments
DEPLOYMENT_CREATED
DEPLOYMENT_EXECUTED
DEPLOYMENT_FAILED

# Incidents
INCIDENT_SUSPICIOUS_ACTIVITY
INCIDENT_RATE_LIMIT_EXCEEDED
INCIDENT_INJECTION_ATTEMPT
```

#### Asosiy funksiyalar:

**`log_security_event(event_type, user_id, ...)`**
- Xavfsizlik hodisalarini yozib boradi
- Redis va Supabase ga saqlaydi
- Timestamp va metadata qo'shadi
- Severity (info, warning, error, critical) belgilaydi

**`get_security_events(user_id, limit)`**
- Redisdan oxirgi hodisalarni oladi
- Foydalanuvchi bo'yicha filtrlash

**`get_security_stats()`**
- Hodisalar statistikasini qaytaradi
- Event turlari bo'yicha hisoblanadi

**`check_rate_limit(user_id, action, limit, window)`**
- Rate limiting tekshiruvi
- Redis bilan amalga oshiriladi
- Limitdan oshganda False qaytaradi

## Ishlatish misollari

### Command validation

```python
from security.validators import sanitize_command

# Buyruqni tekshirish
is_safe, clean_cmd, error = sanitize_command("ls -la /home")
if is_safe:
    # Buyruqni bajarish mumkin
    result = await execute(clean_cmd)
else:
    # Xavfli buyruq
    raise HTTPException(400, detail=error)
```

### SSH config validation

```python
from security.validators import validate_ssh_config

config = {
    "host": "example.com",
    "port": 22,
    "username": "ubuntu",
    "ssh_auth_method": "private_key",
    "ssh_key": "-----BEGIN RSA PRIVATE KEY-----..."
}

is_valid, error = validate_ssh_config(config)
if not is_valid:
    raise HTTPException(400, detail=error)
```

### Sensitive data masking

```python
from security.crypto import mask_ssh_key, mask_sensitive_value

# SSH keyni maskalash
masked_key = mask_ssh_key(ssh_private_key)
# "***RSA_KEY***"

# API keyni maskalash
masked_api_key = mask_sensitive_value(api_key, visible_chars=4)
# "***xyz9"
```

### Security event logging

```python
from security.audit import log_security_event, SecurityEventType

# Login muvaffaqiyatli
log_security_event(
    SecurityEventType.AUTH_LOGIN_SUCCESS,
    user_id=user["id"],
    details={"email": user["email"]},
    ip_address=client_ip,
    severity="info",
)

# Xavfli buyruq bloklandi
log_security_event(
    SecurityEventType.COMMAND_BLOCKED,
    user_id=user["id"],
    details={"command": "***REDACTED***", "reason": "dangerous operation"},
    ip_address=client_ip,
    severity="warning",
)
```

### Rate limiting

```python
from security.audit import check_rate_limit

# Foydalanuvchi limitni tekshirish
if not check_rate_limit(user_id, "command_execution", limit=30, window=60):
    raise HTTPException(429, detail="Too many requests")
```

## Integration

### ExecutionSandbox da ishlatish

```python
from security.validators import sanitize_command, validate_ssh_config
from security.audit import log_security_event, SecurityEventType

# Command validatsiya
is_safe, clean_cmd, error = sanitize_command(command)
if not is_safe:
    log_security_event(
        SecurityEventType.COMMAND_BLOCKED,
        user_id=user_id,
        details={"reason": error},
        severity="warning",
    )
    return {"status": "blocked", "reason": error}

# SSH config validatsiya
is_valid, error = validate_ssh_config(server_config)
if not is_valid:
    return {"status": "error", "reason": error}
```

## Testing

Security modullarni test qilish:

```python
# Test command validation
def test_dangerous_command():
    is_safe, _, error = sanitize_command("rm -rf /")
    assert not is_safe
    assert "dangerous" in error.lower()

# Test path validation
def test_path_traversal():
    is_safe, error = is_safe_path("../../etc/passwd")
    assert not is_safe
    assert "traversal" in error.lower()

# Test SSH config validation
def test_invalid_ssh_config():
    config = {"host": "example;rm -rf", "username": "user"}
    is_valid, error = validate_ssh_config(config)
    assert not is_valid
```

## Monitoring

### Redis keys

Security audit logs Redis da saqlanadi:

- `security:events:{user_id}` - Foydalanuvchi hodisalari (oxirgi 1000)
- `security:counters:{event_type}` - Event turlari hisobi (1 soatlik window)
- `rate_limit:{user_id}:{action}` - Rate limiting hisoblagichlari

### Supabase tables

Muhim hodisalar Supabase ga ham saqlanadi:

- `security_audit_log` - Barcha critical/error hodisalar
- Columns: timestamp, event_type, user_id, resource_type, resource_id, details, ip_address, severity

## Best Practices

1. **Har doim input validatsiya qilish**
   - Hech qachon trust qilmaslik user inputga
   - Server-side validation majburiy

2. **Maxfiy ma'lumotlarni shifrlash**
   - SSH keys, passwords shifrlangan holda saqlash
   - Log va API responselarda maskalab ko'rsatish

3. **Xavfsizlik hodisalarini yozib borish**
   - Har bir muhim amaliyotni log qilish
   - Monitoring va alerting sozlash

4. **Rate limiting qo'llash**
   - API abuse oldini olish
   - DDoS hujumlaridan himoyalanish

5. **Regular security audit**
   - Security logslarni muntazam ko'rib chiqish
   - Suspicious activity uchun alertlar sozlash

## Qo'shimcha yaxshilashlar

Kelajakda qo'shilishi kerak:

- [ ] IP whitelist/blacklist
- [ ] 2FA (Two-factor authentication)
- [ ] JWT token rotation
- [ ] Session management improvements
- [ ] Intrusion detection system
- [ ] Automated threat response
- [ ] SIEM integration
- [ ] Compliance reporting (SOC 2, ISO 27001)
