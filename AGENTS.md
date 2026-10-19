# AGENTS.md

Panduan singkat untuk agent coding yang bekerja di repo ini (fork **NagramZ**).

## Identitas repo

- **Origin**: `https://github.com/zuher5/NagramZ.git` (branch `dev`) — repo publik, tempat release APK.
- **Upstream**: `https://github.com/HSSkyBoy/NiagramX.git` (branch `dev`) — sumber kode asli, disinkron otomatis.
- **Package id**: `top.nkbe.niagram` (dari `gradle.properties`). **Tidak boleh diubah** — perubahan id = aplikasi terpisah, update in-place mati.
- **Label aplikasi**: `NagramZ`.
- **Target perangkat**: Xiaomi 2201117TY (MIUI 14 / Android 13) — **arm64-v8a**.

## Aturan wajib

1. **Build hanya arm64-v8a.** Release APK yang dipublikasikan hanya varian `arm64-v8a`; jangan menambah target `universal`, `x86_64`, atau `armeabi-v7a` kecuali diminta user. Matrix di `.github/workflows/upstream-sync-release.yml` harus `target: [arm64-v8a]`. Alasannya: waktu native build & menit Actions. *(Berlaku mulai update berikutnya — release yang sedang dibangun masih memakai matrix lama.)*
2. **Branding lewat script, bukan diff di file upstream.** `ci/apply-branding.sh` menyetel `AppName`, `gramName` (nama file APK), dan `rootProject.name` → `NagramZ` saat build. **Jangan** menulis nilai branding langsung ke file milik upstream (`TMessagesProj/src/main/res/values*/strings.xml`, `gramName` di `TMessagesProj/build.gradle`, `rootProject.name` di `settings.gradle`) — upstream rutin mengganti nama produknya dan setiap diff branding di file itu berbentrok saat rebase.
3. **Milik fork (boleh diedit)**: `.github/workflows/upstream-sync-release.yml`, `ci/apply-branding.sh`, `TMessagesProj/release.keystore`, baris exception `!TMessagesProj/release.keystore` di `.gitignore`, aset splash/icon Nagram, dan referensi icon di `TMessagesProj/src/main/AndroidManifest.xml`.
4. **Milik upstream (jangan diedit)**: workflow `release.yml` / `staging.yml` / `pr.yml`, `buildSrc/`, `TMessagesProj/jni/`, dan file sumber lain. Perubahan di sini akan hilang/berbentrok saat sync.
5. **Signing permanen.** Keystore `TMessagesProj/release.keystore` (sudah di-commit, dengan exception `.gitignore`), alias `nagramz`, secret GitHub Actions `KEYSTORE_PASS` / `ALIAS_NAME` / `ALIAS_PASS`. Cert SHA-256: `abc77e8ae8b20436f66b7228bc466b47fc551fae2dc27a5531e7f3c33ff568fc`. **Dilarang mengganti keystore/alias** — signature berbeda = Android menolak update ("signatures do not match") dan pengguna harus uninstall.
6. **Auto-sync tidak boleh menulis ulang isi commit upstream.** Workflow `Upstream Sync & Release` (cron 6 jam) me-rebase `dev` ke `upstream/dev`, lalu build + rilis. Kalau rebase konflik, job **abort dengan aman** — jangan dipaksa `git rebase --skip`/commit tambal, perbaiki manual di lokal lalu push.
7. **Jangan commit secret.** Password keystore hanya lewat GitHub Secrets, tidak pernah di file repo.
8. **Jangan menyentuh `gradle.properties` `APP_PACKAGE`**, dan jangan mengubah nama remote `upstream`.

## Struktur file penting

```text
ci/apply-branding.sh                  Branding NagramZ saat build (label, nama APK, project name)
ci/verify-apk.py                      Cek signature + branding APK (sebelum rilis)
.github/workflows/upstream-sync-release.yml  Cron sync upstream + build + release
TMessagesProj/build.gradle            Signing config (keystore permanen), verCode, gramName
TMessagesProj/release.keystore        Keystore rilis permanen (sudah di-commit)
TMessagesProj/src/main/res/drawable/ic_nagram_animated.xml   Ikon splash Nagram
TMessagesProj/src/main/res/mipmap-*/ic_launcher_nagram*.png    Launcher icon Nagram
```

## Alur kerja upstream sync

```bash
git fetch upstream dev
git rebase upstream/dev        # konflik: ambil versi upstream, branding via ci/apply-branding.sh
git push origin dev --force-with-lease
gh workflow run 358809124 -R zuher5/NagramZ -f force_build=true
```

Setelah rebase, cek apakah branding masih benar: label APK (`AppName`), nama file APK (`gramName`), dan `rootProject.name` — semuanya harus berisi `NagramZ` setelah `ci/apply-branding.sh` jalan.

## Verifikasi sebelum push / sebelum rilis

```bash
# Signature + branding APK rilis (file lokal atau URL)
python ci/verify-apk.py <path-apk-atau-url>

# Signature yang terpasang di HP harus identik dengan cert di atas
adb shell pm path top.nkbe.niagram
adb exec-out cat <path base.apk> > base.apk
python ci/verify-apk.py base.apk
```

Kalau cert APK rilis **tidak** sama dengan `abc77e8ae8b20436f66b7228bc466b47fc551fae2dc27a5531e7f3c33ff568fc`, jangan rilis — itu artinya build jatuh ke debug signing dan update berikutnya akan gagal.
