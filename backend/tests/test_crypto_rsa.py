"""اختبارات القبول النهائية لـ crypto_rsa — مسؤولية أيمن.

يجب أن يضيف أيمن اختبارات مستقلة تثبت على الأقل:
1. generate_key_pair ينشئ مفتاح RSA خاص وعام بالحجم المعتمد.
2. public exponent = 65537.
3. تحويل المفتاحين إلى PEM ثم تحميلهما يعيد مفاتيح صالحة.
4. encrypt_small_data ثم decrypt_small_data يعيدان نفس bytes لرسالة قصيرة.
5. مفتاح خاص مختلف يفشل في فك ciphertext القصير.
6. encrypt_file_bytes يعيد RsaFileEnvelope بقيم encrypted_key وnonce وciphertext غير فارغة.
7. nonce داخل الحزمة طوله 12 bytes.
8. encrypt_file_bytes ثم decrypt_file_bytes يعيدان نفس bytes الملف byte-for-byte، لبيانات نصية وثنائية.
9. تشفير المحتوى نفسه مرتين يعطي حزمًا مختلفة بسبب العشوائية.
10. مفتاح RSA خاطئ أو ciphertext معدل يؤدي إلى فشل واضح؛ لا يُعاد محتوى جزئي.
11. اختبار RSA المباشر يكون لبيانات قصيرة فقط؛ لا تختبر ملفًا كبيرًا بتشفير RSA المباشر.
12. هذا الملف لا يعتمد على FastAPI أو أسماء الملفات أو MIME type.

قاعدة القبول: لا تُعدّل اختبارات AES الحالية لإجبارها على المرور.
"""

# أضف الاختبارات هنا بعد تنفيذ الدوال الموجودة في app.crypto_rsa.

"""اختبارات منطق RSA والتشفير الهجين في crypto_rsa.py.

لا تعتمد هذي الاختبارات على FastAPI إطلاقًا - فقط الدوال المصدّرة من crypto_rsa.
"""
import os
import pytest

from app.crypto_rsa import (
    RSA_KEY_SIZE,
    RSA_PUBLIC_EXPONENT,
    RsaFileEnvelope,
    decrypt_file_bytes,
    decrypt_small_data,
    encrypt_file_bytes,
    encrypt_small_data,
    generate_key_pair,
    load_private_key,
    load_public_key,
    private_key_to_pem,
    public_key_to_pem,
)


@pytest.fixture
def key_pair():
    """زوج مفاتيح واحد يُعاد استخدامه في كل الاختبارات بدل توليد مفتاح جديد كل مرة."""
    return generate_key_pair()


@pytest.fixture
def other_key_pair():
    """زوج مفاتيح مختلف تمامًا، لاختبار حالات المفتاح الخاطئ."""
    return generate_key_pair()


# 1. حجم المفتاح وexponent -----------------------------------------------


def test_key_size_and_public_exponent(key_pair):
    private_key, public_key = key_pair

    assert private_key.key_size >= RSA_KEY_SIZE
    assert public_key.public_numbers().e == RSA_PUBLIC_EXPONENT
    assert RSA_PUBLIC_EXPONENT == 65537


# 2. PEM round-trip --------------------------------------------------------


def test_private_key_pem_round_trip(key_pair):
    private_key, _ = key_pair

    pem = private_key_to_pem(private_key)
    assert isinstance(pem, bytes)
    assert b"PRIVATE KEY" in pem

    loaded = load_private_key(pem)
    assert loaded.private_numbers().d == private_key.private_numbers().d


def test_public_key_pem_round_trip(key_pair):
    _, public_key = key_pair

    pem = public_key_to_pem(public_key)
    assert isinstance(pem, bytes)
    assert b"PUBLIC KEY" in pem

    loaded = load_public_key(pem)
    assert loaded.public_numbers().n == public_key.public_numbers().n


def test_load_private_key_rejects_non_rsa_or_garbage():
    with pytest.raises(ValueError):
        load_private_key(b"not a real pem at all")


def test_load_public_key_rejects_non_rsa_or_garbage():
    with pytest.raises(ValueError):
        load_public_key(b"not a real pem at all")


# 3. RSA مباشر لبيانات قصيرة ------------------------------------------------


def test_encrypt_decrypt_small_data_round_trip(key_pair):
    private_key, public_key = key_pair
    message = b"a short secret message"

    ciphertext = encrypt_small_data(message, public_key)
    assert ciphertext != message

    plaintext = decrypt_small_data(ciphertext, private_key)
    assert plaintext == message


# 4. رفض مفتاح خاطئ ---------------------------------------------------------


def test_decrypt_small_data_fails_with_wrong_private_key(key_pair, other_key_pair):
    _, public_key = key_pair
    wrong_private_key, _ = other_key_pair

    ciphertext = encrypt_small_data(b"secret", public_key)

    with pytest.raises(ValueError):
        decrypt_small_data(ciphertext, wrong_private_key)


def test_decrypt_file_bytes_fails_with_wrong_private_key(key_pair, other_key_pair):
    _, public_key = key_pair
    wrong_private_key, _ = other_key_pair

    envelope = encrypt_file_bytes(b"file content here", public_key)

    with pytest.raises(ValueError):
        decrypt_file_bytes(envelope, wrong_private_key)


# 5 و 6. Hybrid round-trip: نصي وثنائي كبير ----------------------------------


def test_hybrid_round_trip_text_data(key_pair):
    private_key, public_key = key_pair
    original = "نص عربي وENGLISH وأرقام 12345".encode("utf-8")

    envelope = encrypt_file_bytes(original, public_key)
    assert isinstance(envelope, RsaFileEnvelope)

    decrypted = decrypt_file_bytes(envelope, private_key)
    assert decrypted == original


def test_hybrid_round_trip_large_binary_data(key_pair):
    """بيانات ثنائية أكبر بكثير من حد الـ190 بايت لـ RSA-OAEP مباشر،
    للتأكد أن AES-GCM هو من يشفر المحتوى فعليًا وليس RSA مباشرة."""
    private_key, public_key = key_pair
    original = os.urandom(50_000)

    envelope = encrypt_file_bytes(original, public_key)
    decrypted = decrypt_file_bytes(envelope, private_key)

    assert decrypted == original


# 7. اختلاف الحزم بين عمليتين لنفس البيانات ----------------------------------


def test_encrypt_file_bytes_produces_different_envelope_each_time(key_pair):
    _, public_key = key_pair
    data = b"same plaintext both times"

    envelope_1 = encrypt_file_bytes(data, public_key)
    envelope_2 = encrypt_file_bytes(data, public_key)

    assert envelope_1.nonce != envelope_2.nonce
    assert envelope_1.ciphertext != envelope_2.ciphertext
    assert envelope_1.encrypted_key != envelope_2.encrypted_key


# 8. فشل ciphertext معدل -----------------------------------------------------


def test_decrypt_file_bytes_fails_on_tampered_ciphertext(key_pair):
    private_key, public_key = key_pair
    envelope = encrypt_file_bytes(b"do not tamper with me", public_key)

    tampered_ciphertext = bytearray(envelope.ciphertext)
    tampered_ciphertext[0] ^= 0xFF  # قلب أول بايت

    tampered_envelope = RsaFileEnvelope(
        encrypted_key=envelope.encrypted_key,
        nonce=envelope.nonce,
        ciphertext=bytes(tampered_ciphertext),
    )

    with pytest.raises(ValueError):
        decrypt_file_bytes(tampered_envelope, private_key)
