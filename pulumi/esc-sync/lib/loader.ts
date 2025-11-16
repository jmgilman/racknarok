/**
 * Configuration and secrets loader
 *
 * Loads config files and SOPS-encrypted secrets, then merges them.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { merge as deepMerge } from 'ts-deepmerge';
import { decryptSopsFile } from './sops';
import { EscMapping, EnvironmentData } from './types';

/**
 * Merge options for ts-deepmerge.
 * mergeArrays: false ensures that arrays are replaced, not concatenated.
 * This allows secrets to completely override config arrays.
 */
const mergeOptions = { mergeArrays: false };

/**
 * Helper function to merge two objects with our configured options.
 */
function merge(target: EnvironmentData, source: EnvironmentData): EnvironmentData {
    return deepMerge.withOptions(mergeOptions, target, source);
}

/**
 * Load the esc-mapping.yaml file
 *
 * @param repoRoot - Path to repository root
 * @returns Parsed ESC mapping configuration
 */
export function loadEscMapping(repoRoot: string): EscMapping {
    const mappingPath = path.join(repoRoot, 'config', 'esc-mapping.yaml');

    if (!fs.existsSync(mappingPath)) {
        throw new Error(`ESC mapping file not found: ${mappingPath}`);
    }

    const content = fs.readFileSync(mappingPath, 'utf-8');
    return yaml.load(content) as EscMapping;
}

/**
 * Load a plain YAML config file
 *
 * @param filePath - Path to the config file (relative to repo root)
 * @param repoRoot - Path to repository root
 * @returns Parsed config data
 */
function loadConfigFile(filePath: string, repoRoot: string): EnvironmentData {
    const absolutePath = path.join(repoRoot, filePath);

    if (!fs.existsSync(absolutePath)) {
        console.warn(`Config file not found (skipping): ${filePath}`);
        return {};
    }

    const content = fs.readFileSync(absolutePath, 'utf-8');
    return yaml.load(content) as EnvironmentData;
}

/**
 * Load and decrypt a SOPS-encrypted secret file
 *
 * @param filePath - Path to the secret file (relative to repo root)
 * @param repoRoot - Path to repository root
 * @returns Decrypted secret data
 */
function loadSecretFile(filePath: string, repoRoot: string): EnvironmentData {
    const absolutePath = path.join(repoRoot, filePath);

    if (!fs.existsSync(absolutePath)) {
        console.warn(`Secret file not found (skipping): ${filePath}`);
        return {};
    }

    return decryptSopsFile(absolutePath);
}

/**
 * Wrap string values in an object with fn::secret
 *
 * ESC only accepts string literals for fn::secret, so we only wrap strings.
 * Numbers, booleans, and other types are left as-is.
 *
 * @param data - Data object
 * @returns Data with string values wrapped in fn::secret
 */
function wrapWithSecrets(data: any): any {
    if (typeof data !== 'object' || data === null) {
        // Leaf value - only wrap strings with fn::secret
        if (typeof data === 'string') {
            return { 'fn::secret': data };
        }
        // Return other primitives (numbers, booleans, null) as-is
        return data;
    }

    if (Array.isArray(data)) {
        // For arrays, recursively process each element
        return data.map(item => wrapWithSecrets(item));
    }

    // For objects, recursively process values
    const wrapped: any = {};
    for (const [key, value] of Object.entries(data)) {
        wrapped[key] = wrapWithSecrets(value);
    }
    return wrapped;
}

/**
 * Load and merge config and secrets for an environment
 *
 * @param envName - Environment name
 * @param mapping - ESC mapping configuration
 * @param repoRoot - Path to repository root
 * @returns Merged environment data
 */
export function loadEnvironmentData(
    envName: string,
    mapping: EscMapping,
    repoRoot: string
): EnvironmentData {
    const envConfig = mapping.environments[envName];

    if (!envConfig) {
        throw new Error(`Environment not found in mapping: ${envName}`);
    }

    let merged: EnvironmentData = {};

    // Load and merge all config files
    if (envConfig.config) {
        console.log(`Loading config files for ${envName}...`);
        for (const configPath of envConfig.config) {
            const data = loadConfigFile(configPath, repoRoot);
            merged = merge(merged, data);
        }
    }

    // Load, decrypt, and merge all secret files
    // Secrets override config values
    if (envConfig.secrets) {
        console.log(`Loading and decrypting secrets for ${envName}...`);
        for (const secretPath of envConfig.secrets) {
            const data = loadSecretFile(secretPath, repoRoot);
            // Wrap secret values with fn::secret
            const wrapped = wrapWithSecrets(data);
            merged = merge(merged, wrapped);
        }
    }

    return merged;
}
