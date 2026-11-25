"""Encrypt or restore local dzq files and backup photos. Requires cryptography."""

import argparse
from getpass import getpass
from io import BytesIO
from pathlib import Path
from secrets import token_bytes, token_urlsafe
from zipfile import BadZipFile, ZipFile

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


FILES = ("dzq", "dzq.bak")
PHOTO_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
MAGIC = b"DZQ1"
SALT_SIZE = 16
NONCE_SIZE = 12
HEADER_SIZE = len(MAGIC) + SALT_SIZE + NONCE_SIZE


def cipher(password: str, salt: bytes) -> AESGCM:
    kdf = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1)
    return AESGCM(kdf.derive(password.encode("utf-8")))


def write_new(files: list[tuple[Path, bytes]]) -> None:
    created = []
    try:
        for path, data in files:
            with path.open("xb") as stream:
                created.append(path)
                stream.write(data)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def is_photo(name: str) -> bool:
    return not any(char in name for char in "\0/\\:") and Path(name).suffix.lower() in PHOTO_SUFFIXES


def encrypt(directory: Path, archive: Path, password: str, *, photos: bool = False,
            recovery: tuple[Path, bytes] | None = None) -> None:
    names = FILES
    if photos:
        names = tuple(sorted(path.name for path in directory.iterdir()
                             if is_photo(path.name) and path.is_file() and not path.is_symlink()))
        if not names:
            raise ValueError("图片目录里没有可归档的图片")
    with BytesIO() as buffer:
        with ZipFile(buffer, "w") as bundle:
            for name in names:
                bundle.writestr(name, (directory / name).read_bytes())
        payload = buffer.getvalue()

    salt = token_bytes(SALT_SIZE)
    nonce = token_bytes(NONCE_SIZE)
    header = MAGIC + salt + nonce
    encrypted = cipher(password, salt).encrypt(nonce, payload, header)
    outputs = [(archive, header + encrypted)]
    if recovery is not None:
        outputs.append(recovery)
    write_new(outputs)


def read_backup(archive: Path, password: str, *, photos: bool = False) -> dict[str, bytes]:
    data = archive.read_bytes()
    if len(data) < HEADER_SIZE + 16 or not data.startswith(MAGIC):
        raise ValueError("加密文件格式不正确")
    header = data[:HEADER_SIZE]
    salt = header[len(MAGIC):len(MAGIC) + SALT_SIZE]
    nonce = header[-NONCE_SIZE:]
    payload = cipher(password, salt).decrypt(nonce, data[HEADER_SIZE:], header)

    with ZipFile(BytesIO(payload)) as bundle:
        names = bundle.namelist()
        if photos:
            valid_names = bool(names) and len(set(names)) == len(names) and all(map(is_photo, names))
        else:
            valid_names = sorted(names) == sorted(FILES)
        if not valid_names:
            raise ValueError("归档中的文件与预期不符")
        return {name: bundle.read(name) for name in names}


def decrypt(archive: Path, directory: Path, password: str, *, photos: bool = False) -> None:
    restored = read_backup(archive, password, photos=photos)
    directory.mkdir(parents=True, exist_ok=True)
    write_new([(directory / name, data) for name, data in restored.items()])


def windows_backup(action: str, archive: Path, directory: Path, key_file: Path, *, photos: bool = False) -> None:
    try:
        import win32crypt
        from pywintypes import error as WindowsCryptoError
    except ImportError as exc:
        raise ValueError("Windows 恢复密钥模式需要 Windows 和 pywin32") from exc

    ui_forbidden = 1
    try:
        if action == "encrypt" and not photos:
            password = token_urlsafe(32)
            protected_key = win32crypt.CryptProtectData(
                password.encode("ascii"), "dzq archive recovery key", None, None, None, ui_forbidden
            )
            encrypt(directory, archive, password, recovery=(key_file, protected_key))
        else:
            _, key = win32crypt.CryptUnprotectData(key_file.read_bytes(), None, None, None, ui_forbidden)
            password = key.decode("ascii")
            if action == "encrypt":
                encrypt(directory, archive, password, photos=photos)
            else:
                decrypt(archive, directory, password, photos=photos)
    except WindowsCryptoError as exc:
        raise ValueError("Windows 无法处理恢复密钥。请使用创建归档时的 Windows 用户账户。") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="在本地加密或还原 dzq 备份与图片")
    parser.add_argument("action", choices=("encrypt", "decrypt"))
    parser.add_argument("archive", type=Path, help="加密文件路径")
    parser.add_argument("--directory", type=Path, help="原文件或还原文件所在目录")
    parser.add_argument("--photos", action="store_true", help="归档为图片包，默认目录是 constant/photo")
    parser.add_argument("--windows-key", type=Path, help="当前 Windows 用户加密的恢复密钥文件")
    args = parser.parse_args()
    directory = args.directory or Path(__file__).resolve().parent / ("photo" if args.photos else ".")

    try:
        if args.windows_key is not None:
            windows_backup(args.action, args.archive, directory, args.windows_key, photos=args.photos)
            return 0
        password = getpass("密码：")
        if not password:
            raise ValueError("密码不能为空")
        if args.action == "encrypt":
            if password != getpass("确认密码："):
                raise ValueError("两次输入的密码不一致")
            encrypt(directory, args.archive, password, photos=args.photos)
        else:
            decrypt(args.archive, directory, password, photos=args.photos)
    except InvalidTag:
        parser.exit(1, "密码错误或加密文件已损坏\n")
    except (OSError, ValueError, BadZipFile) as exc:
        parser.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
