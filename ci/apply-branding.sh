#!/usr/bin/env bash
# NagramZ branding override.
#
# Branding is applied at build time instead of being committed as a diff on
# upstream-owned files. Upstream renames its own product regularly, and every
# committed branding change turns into a rebase conflict during upstream sync.
# Applying the brand here keeps the sync conflicts limited to README.md.
set -euo pipefail

BRAND="NagramZ"
cd "$(dirname "$0")/.."

# 1. Application label: launcher name and app name shown in the UI.
label_count=0
while IFS= read -r file; do
    sed -i "s|<string name=\"AppName\">[^<]*</string>|<string name=\"AppName\">${BRAND}</string>|" "$file"
    label_count=$((label_count + 1))
done < <(find TMessagesProj/src/main/res -name 'strings.xml')

if [ "$label_count" -eq 0 ]; then
    echo "::error::No strings.xml found, NagramZ branding was not applied" >&2
    exit 1
fi

if ! grep -q "<string name=\"AppName\">${BRAND}</string>" TMessagesProj/src/main/res/values/strings.xml; then
    echo "::error::AppName label was not applied, refusing to build an unbranded APK" >&2
    exit 1
fi

# 2. APK output file name.
sed -i "s|String gramName = '[^']*'|String gramName = '${BRAND}'|" TMessagesProj/build.gradle

# 3. Gradle project name.
sed -i "s|rootProject.name = .*|rootProject.name = \"${BRAND}\"|" settings.gradle

echo "Applied ${BRAND} branding to ${label_count} resource files"
