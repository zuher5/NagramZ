# AGENTS.md

Panduan singkat untuk agent coding yang bekerja di repo ini (fork **NagramZ**).

## Identitas repo

- **Origin**: `https://github.com/zuher5/NagramZ.git` (branch `dev`) — repo publik, tempat release APK.
- **Upstream**: `https://github.com/HSSkyBoy/NiagramX.git` (branch `dev`) — sumber kode asli, disinkron otomatis.
- **Package id**: `top.nkbe.niagram` (dari `gradle.properties`). **Tidak boleh diubah** — perubahan id = aplikasi terpisah, update in-place mati.
- **Label aplikasi**: `NagramZ`.
- **Target perangkat**: Xiaomi 2201117TY (MIUI 14 / Android 13) — **arm64-v8a**.

## Aturan wajib

1. **Build hanya arm64-v8a.** Release APK yang dipublikasikan hanya varian `arm64-v8a`; jangan menambah target `universal`, `x86_64`, atau `armeabi-v7a` kecuali diminta user. Matrix di `.github/workflows/upstream-sync-release.yml` = `target: [arm64-v8a]`. Alasannya: waktu native build & menit Actions.
2. **Branding lewat script, bukan diff di file upstream.** `ci/apply-branding.sh` menyetel `AppName`, `gramName` (nama file APK), dan `rootProject.name` → `NagramZ` saat build. **Jangan** menulis nilai branding langsung ke file milik upstream (`TMessagesProj/src/main/res/values*/strings.xml`, `gramName` di `TMessagesProj/build.gradle`, `rootProject.name` di `settings.gradle`) — upstream rutin mengganti nama produknya dan setiap diff branding di file itu berbentrok saat rebase.
3. **Milik fork (boleh diedit)**: `.github/workflows/upstream-sync-release.yml`, `ci/apply-branding.sh`, `TMessagesProj/release.keystore`, baris exception `!TMessagesProj/release.keystore` di `.gitignore`, aset splash/icon Nagram, dan referensi icon di `TMessagesProj/src/main/AndroidManifest.xml`.
4. **Milik upstream (jangan diedit)**: workflow `release.yml` / `staging.yml` / `pr.yml`, `buildSrc/`, `TMessagesProj/jni/`, dan file sumber lain. Perubahan di sini akan hilang/berbentrok saat sync.
5. **Signing permanen.** Keystore `TMessagesProj/release.keystore` (sudah di-commit, dengan exception `.gitignore`), alias `nagramz`, secret GitHub Actions `KEYSTORE_PASS` / `ALIAS_NAME` / `ALIAS_PASS`. Cert SHA-256: `abc77e8ae8b20436f66b7228bc466b47fc551fae2dc27a5531e7f3c33ff568fc`. **Dilarang mengganti keystore/alias** — signature berbeda = Android menolak update ("signatures do not match") dan pengguna harus uninstall.
6. **Auto-sync berjalan penuh tanpa intervensi.** Workflow `Upstream Sync & Release` (cron 6 jam) me-merge `upstream/dev` ke `dev` dengan `git merge -X ours` → hunk yang bentrok memakai versi fork, hunk lain memakai versi upstream. Kalau masih ada path yang belum ter-resolve, workflow otomatis memakai versi fork untuk path itu. Setelah merge, **guardrail** dicek (package id, keystore, konfigurasi signing, script branding); kalau gagal, tidak ada yang di-push dan job jadi merah. Sebelum release, `ci/verify-apk.py` memastikan signature & branding APK benar — kalau tidak, release dibatalkan.
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

Pipeline sudah otomatis penuh (`merge -X ours` → guardrail → build arm64 → verifikasi APK → release). Kalau run merah:

```bash
# 1. Lihat log yang gagal
gh run list -R zuher5/NagramZ --limit 5
gh run view <run-id> -R zuher5/NagramZ --log-failed

# 2. Reproduksi merge secara lokal
git fetch upstream dev
git merge --no-edit -X ours upstream/dev
#   hunk bentrok -> versi fork; hunk lain -> versi upstream
git diff --name-only --diff-filter=U        # sisa conflict, take ours per path
```

Untuk perbaikan manual (jarang dipakai): `git checkout --ours -- <path>` lalu `git add <path>`, commit, lalu
`git push origin dev -o ci.skip` (flag `-o ci.skip` supaya workflow upstream tidak ikut jalan).

Workflow `Dev build` milik upstream sudah dinonaktifkan (repo setting) karena duplikat build kita.

## Yang masih butuh manusia/AI

Hanya 1: **upstream mengubah API yang dipakai fitur kita** → build merah. Di sinilah AI/insight berguna
(baca log build, telusuri, bikin patch). Semua tahap lain berjalan tanpa penilaian.

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
