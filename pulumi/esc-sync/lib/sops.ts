/**
 * SOPS decryption wrapper
 *
 * Uses subprocess to call the sops CLI for decrypting files.
 */

import { execFileSync } from 'child_process';
import * as yaml from 'js-yaml';
import { SopsOptions, EnvironmentData } from './types';

/**
 * Decrypt a SOPS-encrypted file
 *
 * @param filePath - Path to the encrypted file
 * @param options - SOPS options
 * @returns Decrypted data as object
 */
export function decryptSopsFile(
    filePath: string,
    options: SopsOptions = {}
): EnvironmentData {
    const { inputType = 'yaml', outputType = 'yaml' } = options;

    try {
        // Run sops -d --input-type yaml --output-type yaml <file>
        const args = [
            '-d',
            '--input-type', inputType,
            '--output-type', outputType,
            filePath,
        ];

        const decrypted = execFileSync('sops', args, {
            encoding: 'utf-8',
            maxBuffer: 10 * 1024 * 1024, // 10MB buffer
        });

        // Parse the decrypted YAML
        return yaml.load(decrypted) as EnvironmentData;
    } catch (error) {
        if (error instanceof Error) {
            throw new Error(`Failed to decrypt ${filePath}: ${error.message}`);
        }
        throw error;
    }
}

/**
 * Check if SOPS is available in PATH
 *
 * @returns true if sops is available
 */
export function isSopsAvailable(): boolean {
    try {
        execFileSync('which', ['sops'], { encoding: 'utf-8' });
        return true;
    } catch {
        return false;
    }
}
