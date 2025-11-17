#!/usr/bin/env bash
# Load Proxmox admin SSH key into SSH agent
#
# This script extracts the admin SSH private key from secrets and adds it
# to the user's SSH agent, allowing immediate SSH access to Proxmox servers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SSH_SECRETS_FILE="${REPO_ROOT}/secrets/proxmox/ssh.enc.yaml"
NETWORK_SECRETS_FILE="${REPO_ROOT}/secrets/proxmox/network.enc.yaml"
AGE_KEY_FILE="${REPO_ROOT}/secrets/.age-key.txt"
KNOWN_HOSTS="${HOME}/.ssh/known_hosts"

# Check dependencies
if ! command -v sops &> /dev/null; then
    echo "❌ Error: sops is not installed" >&2
    exit 1
fi

if ! command -v yq &> /dev/null; then
    echo "❌ Error: yq is not installed" >&2
    exit 1
fi

if ! command -v ssh-add &> /dev/null; then
    echo "❌ Error: ssh-add is not installed" >&2
    exit 1
fi

# Check if secrets files exist
if [ ! -f "${SSH_SECRETS_FILE}" ]; then
    echo "❌ Error: SSH secrets file not found: ${SSH_SECRETS_FILE}" >&2
    exit 1
fi

if [ ! -f "${NETWORK_SECRETS_FILE}" ]; then
    echo "❌ Error: Network secrets file not found: ${NETWORK_SECRETS_FILE}" >&2
    exit 1
fi

# Check if age key exists
if [ ! -f "${AGE_KEY_FILE}" ]; then
    echo "❌ Error: Age key not found: ${AGE_KEY_FILE}" >&2
    echo "💡 Run ./scripts/bootstrap-sops.sh first" >&2
    exit 1
fi

# Check if SSH agent is running
if [ -z "${SSH_AUTH_SOCK:-}" ]; then
    echo "❌ Error: SSH agent is not running" >&2
    echo "💡 Start SSH agent with: eval \"\$(ssh-agent)\"" >&2
    exit 1
fi

echo "🔐 Loading admin SSH key from secrets..."

# Create temporary file for the key
TEMP_KEY=$(mktemp "${TMPDIR:-/tmp}/proxmox-admin-key.XXXXXX")
trap "rm -f '${TEMP_KEY}'" EXIT

# Extract the private key
SOPS_AGE_KEY_FILE="${AGE_KEY_FILE}" sops -d "${SSH_SECRETS_FILE}" | \
    yq -r '.ssh.admin.private_key' > "${TEMP_KEY}"

# Verify we got a valid key
if [ ! -s "${TEMP_KEY}" ] || ! grep -q "BEGIN OPENSSH PRIVATE KEY" "${TEMP_KEY}"; then
    echo "❌ Error: Failed to extract valid SSH private key" >&2
    exit 1
fi

# Set proper permissions
chmod 600 "${TEMP_KEY}"

# Add key to SSH agent
if ssh-add "${TEMP_KEY}" 2>/dev/null; then
    echo "✅ SSH key loaded into agent"
    echo ""
    echo "You can now connect to Proxmox servers with:"
    echo "  ssh root@<server-ip>"
else
    echo "❌ Error: Failed to add key to SSH agent" >&2
    exit 1
fi

# List loaded keys
echo ""
echo "Currently loaded keys:"
ssh-add -l

# Add host keys to known_hosts
echo ""
echo "🔑 Adding SSH host keys to known_hosts..."

# Extract server IP (strip CIDR notation if present)
# Try decrypting first (file may be encrypted in production)
SERVER_IP=$(SOPS_AGE_KEY_FILE="${AGE_KEY_FILE}" sops -d "${NETWORK_SECRETS_FILE}" 2>/dev/null | \
    yq -r '.network.nodes.rk1.public.ip' | cut -d'/' -f1 || true)

# If decryption failed or returned null, try reading unencrypted file
if [ -z "${SERVER_IP}" ] || [ "${SERVER_IP}" = "null" ]; then
    SERVER_IP=$(yq -r '.network.nodes.rk1.public.ip' "${NETWORK_SECRETS_FILE}" 2>/dev/null | cut -d'/' -f1 || true)
fi

if [ -z "${SERVER_IP}" ] || [ "${SERVER_IP}" = "null" ]; then
    echo "⚠️  Warning: Could not extract server IP from network secrets" >&2
    echo "💡 You'll need to manually verify host keys on first connection" >&2
else
    # Extract host public keys
    ED25519_PUBLIC=$(SOPS_AGE_KEY_FILE="${AGE_KEY_FILE}" sops -d "${SSH_SECRETS_FILE}" | \
        yq -r '.ssh.host_keys.ed25519.public')
    RSA_PUBLIC=$(SOPS_AGE_KEY_FILE="${AGE_KEY_FILE}" sops -d "${SSH_SECRETS_FILE}" | \
        yq -r '.ssh.host_keys.rsa.public')

    # Ensure ~/.ssh directory exists
    mkdir -p "${HOME}/.ssh"
    touch "${KNOWN_HOSTS}"
    chmod 644 "${KNOWN_HOSTS}"

    # Remove any existing entries for this IP
    ssh-keygen -R "${SERVER_IP}" 2>/dev/null || true

    # Add new entries
    if [ -n "${ED25519_PUBLIC}" ] && [ "${ED25519_PUBLIC}" != "null" ]; then
        echo "${SERVER_IP} ${ED25519_PUBLIC}" >> "${KNOWN_HOSTS}"
        echo "  ✅ Added ed25519 host key for ${SERVER_IP}"
    fi

    if [ -n "${RSA_PUBLIC}" ] && [ "${RSA_PUBLIC}" != "null" ]; then
        echo "${SERVER_IP} ${RSA_PUBLIC}" >> "${KNOWN_HOSTS}"
        echo "  ✅ Added RSA host key for ${SERVER_IP}"
    fi

    echo ""
    echo "You can now connect without host key verification:"
    echo "  ssh root@${SERVER_IP}"
fi
