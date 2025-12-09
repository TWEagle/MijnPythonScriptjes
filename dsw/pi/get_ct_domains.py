import requests, pandas as pd, datetime, time, os, subprocess

REPO = "TWEagle/dns-scanner-webapp"
TOKEN_FILE = os.path.expanduser("~/.github_token")
RESULT_DIR = "results/domains"


def get_domains_from_ct(tlds):
    all_domains = set()
    for tld in tlds:
        print(f"Haal domeinen op voor .{tld}...")
        url = f"https://crt.sh/?q=%25.{tld}&output=json"
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                for e in resp.json():
                    domain = e.get("name_value", "").lower()
                    if domain and not domain.startswith("*"):
                        all_domains.add(domain)
        except Exception as ex:
            print(f"Fout bij .{tld}: {ex}")
        time.sleep(5)
    return sorted(all_domains)


def save_and_upload(domains):
    today = datetime.date.today().strftime("%Y-%m-%d")
    fname = f"domeinen_auto_{today}.xlsx"
    pd.DataFrame(domains, columns=["domein"]).to_excel(fname, index=False)
    print(f"{len(domains)} domeinen → {fname}")

    token = open(TOKEN_FILE).read().strip()
    os.system("git config user.name 'pi-bot'")
    os.system("git config user.email 'info@tweagle.eu'")
    os.system(f"git clone https://{token}@github.com/{REPO}.git repo")
    os.chdir("repo")
    os.makedirs(RESULT_DIR, exist_ok=True)
    os.replace(f"../{fname}", f"{RESULT_DIR}/{fname}")
    os.system("git add .")
    os.system(f"git commit -m 'CT update {today}' || true")
    os.system("git push origin main")
    print("✅ Upload voltooid naar GitHub.")


if __name__ == "__main__":
    tlds = ["be", "eu", "gent", "vlaanderen", "brussels"]
    domains = get_domains_from_ct(tlds)
    save_and_upload(domains)
