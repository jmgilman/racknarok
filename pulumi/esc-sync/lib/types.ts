/**
 * Type definitions for ESC sync project
 */

/**
 * Structure of the esc-mapping.yaml file
 */
export interface EscMapping {
    environments: {
        [envName: string]: {
            config?: string[];
            secrets?: string[];
        };
    };
}

/**
 * Merged configuration data for an environment
 */
export interface EnvironmentData {
    [key: string]: any;
}

/**
 * Options for SOPS decryption
 */
export interface SopsOptions {
    inputType?: 'yaml' | 'json';
    outputType?: 'yaml' | 'json';
}
