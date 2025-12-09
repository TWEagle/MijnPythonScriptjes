#!/usr/bin/env python3
import importlib
import subprocess
import sys

# 📦 Vereiste packages
REQUIRED_LIBS = [
    "pandas",
    "dns.resolver",
    "whois",
    "requests",
    "ipwhois",
    "openpyxl",
]

def install_package(pkg):
    """Installeer ontbrekende package via pip"""
    base_pkg = pkg.split(".")[0]  # Voor dns.resolver → dns
    print(f"⚙️ Controleren: {base_pkg} ...", end=" ")
    try:
        importlib.import_module(base_pkg)
        print("✅ aanwezig")
    except ImportError:
        print("❌ ontbreekt → installeren...")
        subprocess.run([sys.executable, "-m", "pip", "install", base_pkg], check=False)

def main():
    print("\n🔍 Controleer en installeer vereiste libraries...\n")
    for lib in REQUIRED_LIBS:
        install_package(lib)
    print("\n✅ Alle dependencies zijn up-to-date!\n")

if __name__ == "__main__":
    main()
