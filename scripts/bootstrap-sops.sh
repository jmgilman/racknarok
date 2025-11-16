#!/usr/bin/env bash
# Bootstrap SOPS encryption for the repository
#
# This script manages the age key pair used for SOPS encryption:
# 1. Checks if key exists in Pulumi ESC (source of truth)
# 2. If yes, downloads it locally (if not already present)
# 3. If no, generates new key and uploads to ESC
# 4. Updates .sops.yaml with the public key

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOPS_CONFIG="${REPO_ROOT}/secrets/.sops.yaml"
AGE_KEY_FILE="${REPO_ROOT}/secrets/.age-key.txt"
ESC_ORG="${PULUMI_ORG:-jmgilman}"  # Use PULUMI_ORG env var or default to jmgilman
ESC_PROJECT="${PULUMI_PROJECT:-default}"  # Use PULUMI_PROJECT env var or default
ESC_ENV="ci"
ESC_FULL_PATH="${ESC_ORG}/${ESC_PROJECT}/${ESC_ENV}"  # Full path: org/project/env

echo "🔐 SOPS Bootstrap Script"
echo "========================"
echo ""

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v age &> /dev/null; then
        missing_deps+=("age")
    fi

    if ! command -v yq &> /dev/null; then
        missing_deps+=("yq")
    fi

    if ! command -v esc &> /dev/null; then
        missing_deps+=("esc (Pulumi ESC CLI)")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "❌ Error: Missing required dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        echo ""
        echo "Install missing dependencies:"
        echo "  age: brew install age"
        echo "  yq: brew install yq"
        echo "  esc: brew install pulumi/tap/esc"
        exit 1
    fi
}

# Check if logged into Pulumi ESC
check_esc_auth() {
    echo "🔍 Checking Pulumi/ESC authentication..."

    # ESC uses Pulumi authentication, so check with pulumi whoami
    local whoami_output
    if ! whoami_output=$(pulumi whoami 2>&1); then
        echo "❌ Error: Not authenticated to Pulumi"
        echo ""
        echo "Please log in first:"
        echo "  pulumi login"
        echo "  (or: esc login)"
        echo ""
        exit 1
    fi

    echo "✅ Authenticated as: ${whoami_output}"
    echo "📦 Using ESC path: ${ESC_FULL_PATH}"
    echo ""
}

# Check if key exists in ESC
check_key_in_esc() {
    echo "🔍 Checking if age key exists in ESC (${ESC_FULL_PATH})..."

    # Try to open the environment and check for sops.private_key
    if esc env open "${ESC_FULL_PATH}" --format json 2>/dev/null | jq -e '.sops.private_key' &> /dev/null; then
        echo "✅ Age key found in ESC"
        return 0
    else
        echo "ℹ️  Age key not found in ESC (environment may not exist yet)"
        return 1
    fi
}

# Download key from ESC
download_key_from_esc() {
    echo "📥 Downloading age key from ESC..."

    local private_key
    private_key=$(esc env open "${ESC_FULL_PATH}" --format json | jq -r '.sops.private_key')

    if [ -z "$private_key" ] || [ "$private_key" = "null" ]; then
        echo "❌ Error: Failed to retrieve private key from ESC"
        exit 1
    fi

    # Save to local file
    mkdir -p "$(dirname "${AGE_KEY_FILE}")"
    echo "$private_key" > "${AGE_KEY_FILE}"
    chmod 600 "${AGE_KEY_FILE}"

    echo "✅ Age key downloaded to: ${AGE_KEY_FILE}"
}

# Generate new age key pair
generate_new_key() {
    echo "🔑 Generating new age key pair..."

    mkdir -p "$(dirname "${AGE_KEY_FILE}")"
    age-keygen -o "${AGE_KEY_FILE}"
    chmod 600 "${AGE_KEY_FILE}"

    echo "✅ New age key generated at: ${AGE_KEY_FILE}"
}

# Upload key to ESC
upload_key_to_esc() {
    echo "📤 Uploading age key to ESC..."

    # Check if environment exists by trying to get it
    if ! esc env get "${ESC_FULL_PATH}" &> /dev/null; then
        echo "Creating new ESC environment: ${ESC_FULL_PATH}"
        esc env init "${ESC_FULL_PATH}"
    else
        echo "Environment ${ESC_FULL_PATH} already exists"
    fi

    # Set the private key in the environment as a secret
    # esc env set expects: <env-name> <path> <value>
    echo "Setting sops.private_key in ${ESC_FULL_PATH}..."
    cat "${AGE_KEY_FILE}" | esc env set "${ESC_FULL_PATH}" sops.private_key --secret -f -

    echo "✅ Age key uploaded to ESC (${ESC_FULL_PATH})"
}

# Update .sops.yaml with public key
update_sops_config() {
    echo "📝 Updating .sops.yaml with public key..."

    # Extract public key from private key file
    local public_key
    public_key=$(age-keygen -y "${AGE_KEY_FILE}")

    if [ ! -f "${SOPS_CONFIG}" ]; then
        echo "❌ Error: SOPS config not found at ${SOPS_CONFIG}"
        exit 1
    fi

    # Use yq to update the age key in the YAML
    yq eval ".creation_rules[0].age = \"${public_key}\"" -i "${SOPS_CONFIG}"

    echo "✅ Updated ${SOPS_CONFIG} with public key: ${public_key}"
}

# Main flow
main() {
    check_dependencies
    check_esc_auth

    # Check if key exists in ESC (source of truth)
    if check_key_in_esc; then
        # Key exists in ESC
        if [ -f "${AGE_KEY_FILE}" ]; then
            echo "✅ Age key already exists locally at: ${AGE_KEY_FILE}"

            # Verify local key matches ESC
            local local_key esc_key
            local_key=$(cat "${AGE_KEY_FILE}")
            esc_key=$(esc env open "${ESC_FULL_PATH}" --format json | jq -r '.sops.private_key')

            if [ "$local_key" = "$esc_key" ]; then
                echo "✅ Local key matches ESC"
            else
                echo "⚠️  Warning: Local key differs from ESC"
                read -p "Replace local key with ESC version? (y/N): " -n 1 -r
                echo ""
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    download_key_from_esc
                fi
            fi
        else
            # Key exists in ESC but not locally - download it
            download_key_from_esc
        fi
    else
        # Key doesn't exist in ESC
        if [ -f "${AGE_KEY_FILE}" ]; then
            echo "⚠️  Age key exists locally but not in ESC"
            read -p "Upload existing local key to ESC? (y/N): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                upload_key_to_esc
            else
                echo "⚠️  Generating new key (existing local key will be backed up)"
                cp "${AGE_KEY_FILE}" "${AGE_KEY_FILE}.backup.$(date +%s)"
                generate_new_key
                upload_key_to_esc
            fi
        else
            # No key exists anywhere - generate new one
            generate_new_key
            upload_key_to_esc
        fi
    fi

    # Update .sops.yaml with the public key
    update_sops_config

    echo ""
    echo "🎯 SOPS bootstrap complete!"
    echo ""
    echo "Key locations:"
    echo "  ESC: ${ESC_FULL_PATH}"
    echo "  Local: ${AGE_KEY_FILE}"
    echo ""
    echo "Next steps:"
    echo "  1. You can now encrypt secrets: sops -e secrets/example.yaml > secrets/example.enc.yaml"
    echo "  2. Or edit encrypted files: sops secrets/example.enc.yaml"
    echo "  3. On other machines, just run this script again to download the key from ESC"
    echo ""
}

main
